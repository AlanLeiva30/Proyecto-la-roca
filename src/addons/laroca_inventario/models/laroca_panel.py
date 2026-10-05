from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models


DIAS_SIN_CONTEO = 7


class LarocaPanel(models.TransientModel):
    """Panel general (mockup 10.1).

    No guarda datos: cada vez que se abre calcula los indicadores con los permisos del
    usuario. Hay dos pantallas para el mismo modelo:
    - Panel del administrador: todas las gasolineras, valores en $, seguimiento y alertas.
    - Mi gasolinera (encargado): lo que tiene que hacer hoy en su(s) gasolinera(s).
    """
    _name = 'laroca.panel'
    _description = 'Panel general'

    nombre_usuario = fields.Char(compute='_compute_panel')
    es_admin = fields.Boolean(compute='_compute_panel')
    nombre_gasolineras = fields.Char('Mis gasolineras', compute='_compute_panel')
    ultimo_conteo = fields.Datetime('Última actualización', compute='_compute_panel')
    kpi_suficientes = fields.Integer('Productos con stock suficiente', compute='_compute_panel')
    kpi_bajos = fields.Integer('Productos en estado bajo', compute='_compute_panel')
    kpi_sin_conteo = fields.Integer(f'Gasolineras sin actualizar en {DIAS_SIN_CONTEO} días', compute='_compute_panel')
    kpi_gasolineras = fields.Integer('Gasolineras', compute='_compute_panel')
    kpi_productos = fields.Integer('Productos', compute='_compute_panel')
    kpi_stock_bajo = fields.Integer('Productos con stock bajo', compute='_compute_panel')
    kpi_criticos = fields.Integer('En estado crítico', compute='_compute_panel')
    kpi_abastecimientos_mes = fields.Integer('Abastecimientos este mes', compute='_compute_panel')
    kpi_unidades_mes = fields.Integer('Unidades entregadas este mes', compute='_compute_panel')
    kpi_en_camino = fields.Integer('N.º de entregas en camino', compute='_compute_panel')
    kpi_alertas = fields.Integer('Alertas pendientes', compute='_compute_panel')
    currency_id = fields.Many2one('res.currency', compute='_compute_panel')
    kpi_valor_gasolineras = fields.Monetary('Valor en gasolineras', compute='_compute_panel')
    kpi_valor_bodega = fields.Monetary('Valor en bodega central', compute='_compute_panel')
    kpi_valor_mes = fields.Monetary('Valor entregado este mes', compute='_compute_panel')
    gasolinera_atencion_ids = fields.Many2many(
        'stock.warehouse', string='Gasolineras que requieren atención', compute='_compute_panel')
    entrega_en_camino_ids = fields.Many2many(
        'laroca.entrega', string='Entregas en camino', compute='_compute_panel')
    kpi_pedidos = fields.Integer('Pedidos pendientes', compute='_compute_panel',
                                 help='Administrador: pedidos por atender. Encargado: sus pedidos en curso.')
    kpi_ventas_hoy = fields.Monetary('Vendido hoy', compute='_compute_panel')
    kpi_unidades_vendidas_hoy = fields.Integer('Unidades vendidas hoy', compute='_compute_panel')
    kpi_ventas_mes = fields.Monetary('Vendido este mes', compute='_compute_panel')
    pedido_ids = fields.Many2many('laroca.pedido', string='Pedidos', compute='_compute_panel')
    # Solo administrador
    gasolinera_seguimiento_ids = fields.Many2many(
        'stock.warehouse', string='Seguimiento de gasolineras', compute='_compute_panel')
    alerta_reciente_ids = fields.Many2many('laroca.alerta', string='Alertas recientes', compute='_compute_panel')
    # Solo encargado
    producto_pendiente_ids = fields.Many2many(
        'laroca.inventario', string='Productos que se están acabando', compute='_compute_panel')

    @api.depends_context('uid')
    def _compute_display_name(self):
        for panel in self:
            panel.display_name = self._titulo()

    @api.model
    def _es_admin(self):
        return self.env.user.has_group('laroca_inventario.group_laroca_admin')

    @api.model
    def _titulo(self):
        return 'Panel del administrador' if self._es_admin() else 'Mi gasolinera'

    @api.model
    def _inicio_del_mes_utc(self):
        """Primer instante del mes según la zona horaria del usuario, en UTC (como guarda Odoo)."""
        hoy = fields.Date.context_today(self)
        zona = pytz.timezone(self.env.user.tz or 'UTC')
        inicio_local = zona.localize(datetime.combine(hoy.replace(day=1), time.min))
        return inicio_local.astimezone(pytz.UTC).replace(tzinfo=None)

    @api.model
    def _inicio_del_dia_utc(self):
        hoy = fields.Date.context_today(self)
        zona = pytz.timezone(self.env.user.tz or 'UTC')
        return zona.localize(datetime.combine(hoy, time.min)).astimezone(pytz.UTC).replace(tzinfo=None)

    @api.depends_context('uid')
    def _compute_panel(self):
        Inventario = self.env['laroca.inventario']
        Entrega = self.env['laroca.entrega']
        gasolineras = self.env['stock.warehouse'].search([('laroca_es_gasolinera', '=', True)])
        entregadas_mes = Entrega.search([
            ('estado', '=', 'entregada'), ('fecha_entrega', '>=', self._inicio_del_mes_utc())])
        en_camino = Entrega.search([('estado', '=', 'en_camino')], order='fecha_programada, id')
        # Gasolineras con productos pendientes: primero las de más críticos
        atencion = gasolineras.filtered('laroca_pendiente_count').sorted(
            key=lambda g: (-g.laroca_critico_count, -g.laroca_bajo_count, g.name))
        valor_gasolineras = Inventario._read_group([], [], ['valor_stock:sum'])[0][0] or 0.0
        es_admin = self._es_admin()
        valor_bodega = 0.0
        if es_admin:
            bodega = self.env.company._laroca_bodega_central()
            quants = self.env['stock.quant'].search([('location_id', 'child_of', bodega.lot_stock_id.id)]) if bodega else []
            valor_bodega = sum(q.quantity * q.product_id.standard_price for q in quants)
        # Seguimiento: todas las gasolineras, primero las que necesitan algo
        seguimiento = gasolineras.sorted(
            key=lambda g: (-g.laroca_critico_count, -g.laroca_bajo_count, g.name))
        limite_conteo = fields.Datetime.now() - timedelta(days=DIAS_SIN_CONTEO)
        sin_conteo = gasolineras.filtered(
            lambda g: not g.laroca_ultimo_conteo or g.laroca_ultimo_conteo < limite_conteo)
        estados = dict((estado, total) for estado, total in Inventario._read_group([], ['estado'], ['__count']))
        Venta, Pedido = self.env['laroca.venta'], self.env['laroca.pedido']
        ventas_hoy = Venta.search([('estado', '=', 'confirmada'), ('fecha', '>=', self._inicio_del_dia_utc())])
        ventas_mes = Venta._read_group([('estado', '=', 'confirmada'), ('fecha', '>=', self._inicio_del_mes_utc())],
                                       [], ['total:sum'])[0][0] or 0.0
        # Administrador: lo que tiene que atender. Encargado: sus pedidos en curso.
        dominio_pedidos = [('estado', '=', 'enviado')] if es_admin else \
            [('estado', 'in', ('borrador', 'enviado', 'aprobado', 'en_camino'))]
        pedidos = Pedido.search(dominio_pedidos, order='fecha_envio desc, id desc')
        valores = {
            'nombre_usuario': self.env.user.name.split()[0],
            'es_admin': es_admin,
            'nombre_gasolineras': ', '.join(gasolineras.mapped('name')),
            'ultimo_conteo': Inventario._read_group([], [], ['ultima_actualizacion:max'])[0][0],
            'kpi_suficientes': estados.get('suficiente', 0),
            'kpi_bajos': estados.get('bajo', 0),
            'kpi_sin_conteo': len(sin_conteo),
            'kpi_pedidos': len(pedidos),
            'kpi_ventas_hoy': sum(ventas_hoy.mapped('total')),
            'kpi_unidades_vendidas_hoy': round(sum(ventas_hoy.mapped('total_unidades'))),
            'kpi_ventas_mes': ventas_mes,
            'pedido_ids': pedidos[:8],
            'gasolinera_seguimiento_ids': seguimiento if es_admin else False,
            'alerta_reciente_ids': self.env['laroca.alerta'].search(
                [('estado', 'in', ('abierta', 'en_proceso'))], order='fecha_alerta desc', limit=6) if es_admin else False,
            'producto_pendiente_ids': Inventario.search(
                [('estado', 'in', ('bajo', 'critico'))], order='prioridad, product_id', limit=20) if not es_admin else False,
            'currency_id': self.env.company.currency_id,
            'kpi_valor_gasolineras': valor_gasolineras,
            'kpi_valor_bodega': valor_bodega,
            'kpi_valor_mes': sum(entregadas_mes.mapped('valor_total')),
            'kpi_gasolineras': len(gasolineras),
            'kpi_productos': self.env['product.template'].search_count([('is_storable', '=', True)]),
            'kpi_stock_bajo': Inventario.search_count([('estado', 'in', ('bajo', 'critico'))]),
            'kpi_criticos': Inventario.search_count([('estado', '=', 'critico')]),
            'kpi_abastecimientos_mes': len(entregadas_mes),
            'kpi_unidades_mes': round(sum(entregadas_mes.mapped('total_entregado'))),
            'kpi_en_camino': len(en_camino),
            'kpi_alertas': self.env['laroca.alerta'].search_count([('estado', 'in', ('abierta', 'en_proceso'))]),
            'gasolinera_atencion_ids': atencion,
            'entrega_en_camino_ids': en_camino,
        }
        for panel in self:
            panel.update(valores)

    # ------------------------------------------------------------------
    # Datos para los gráficos del panel (los dibuja el componente OWL
    # static/src/panel_graficos/panel_graficos.js con Chart.js)
    # ------------------------------------------------------------------
    MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

    @api.model
    def get_datos_graficos(self):
        gasolineras = self.env['stock.warehouse'].search([('laroca_es_gasolinera', '=', True)], order='name')
        grupos = self.env['laroca.inventario']._read_group(
            [('gasolinera_id', 'in', gasolineras.ids)], ['gasolinera_id', 'estado'], ['__count'])
        conteo = {(g.id, estado): total for g, estado, total in grupos}
        etiquetas_estado = dict(self.env['laroca.inventario']._fields['estado'].selection)
        estados = {
            'ids': gasolineras.ids,
            'labels': gasolineras.mapped('name'),
            'series': [{
                'key': estado,
                'label': etiquetas_estado[estado],
                'data': [conteo.get((g.id, estado), 0) for g in gasolineras],
            } for estado in ('critico', 'bajo', 'suficiente')],
        }
        # Unidades entregadas en los últimos 6 meses
        hoy = fields.Date.context_today(self)
        meses = []
        anio, mes = hoy.year, hoy.month
        for _i in range(6):
            meses.insert(0, (anio, mes))
            anio, mes = (anio, mes - 1) if mes > 1 else (anio - 1, 12)
        inicio = datetime(meses[0][0], meses[0][1], 1)
        grupos = self.env['laroca.entrega.linea']._read_group(
            [('estado', '=', 'entregada'), ('fecha_entrega', '>=', inicio)],
            ['fecha_entrega:month'], ['cantidad_entregada:sum', 'valor:sum'])
        por_mes = {(fecha.year, fecha.month): (unidades, valor) for fecha, unidades, valor in grupos}
        entregas = {
            'labels': [f'{self.MESES[m - 1]} {a}' for a, m in meses],
            'unidades': [por_mes.get(am, (0, 0))[0] for am in meses],
            'valor': [round(por_mes.get(am, (0, 0))[1], 2) for am in meses],
        }
        totales = {serie['key']: sum(serie['data']) for serie in estados['series']}
        return {'estados': estados, 'entregas': entregas, 'totales': totales, 'es_admin': self._es_admin()}

    # ------------------------------------------------------------------
    # Navegación desde las tarjetas
    # ------------------------------------------------------------------
    @api.model
    def action_abrir_panel(self):
        """Abre el panel que corresponde al rol: administrador o encargado."""
        vista = 'view_laroca_panel_form' if self._es_admin() else 'view_laroca_panel_encargado_form'
        panel = self.create({})
        # Al crear, Odoo deja las listas calculadas vacías en caché; se limpian para calcularlas al leer.
        panel.invalidate_recordset()
        return {
            'type': 'ir.actions.act_window',
            'name': self._titulo(),
            'res_model': 'laroca.panel',
            'res_id': panel.id,
            'view_mode': 'form',
            'views': [(self.env.ref(f'laroca_inventario.{vista}').id, 'form')],
            'target': 'current',
        }

    def action_refrescar(self):
        # Al volver de un botón, Odoo recarga el formulario y los indicadores se recalculan.
        return True

    def _accion(self, xmlid, domain=None, context=None):
        action = self.env['ir.actions.actions']._for_xml_id(xmlid)
        if domain is not None:
            action['domain'] = domain
        if context is not None:
            action['context'] = context
        return action

    def action_ver_gasolineras(self):
        return self._accion('laroca_inventario.action_laroca_gasolineras')

    def action_ver_productos(self):
        return self._accion('laroca_inventario.action_laroca_productos')

    def action_ver_stock_bajo(self):
        action = self._accion('laroca_inventario.action_laroca_inventario',
                              domain=[('estado', 'in', ('bajo', 'critico'))], context={})
        action['name'] = 'Productos con stock bajo'
        return action

    def action_ver_suficientes(self):
        return self._accion('laroca_inventario.action_laroca_inventario',
                            context={'searchpanel_default_estado': 'suficiente'})

    def action_ver_bajos(self):
        return self._accion('laroca_inventario.action_laroca_inventario',
                            context={'searchpanel_default_estado': 'bajo'})

    def action_ver_criticos(self):
        return self._accion('laroca_inventario.action_laroca_inventario',
                            context={'searchpanel_default_estado': 'critico'})

    def action_ver_abastecimientos_mes(self):
        return self._accion('laroca_inventario.action_laroca_entregas',
                            domain=[('estado', '=', 'entregada'), ('fecha_entrega', '>=', fields.Datetime.to_string(self._inicio_del_mes_utc()))],
                            context={})

    def action_ver_en_camino(self):
        return self._accion('laroca_inventario.action_laroca_entregas', context={'searchpanel_default_estado': 'en_camino'})

    def action_ver_alertas(self):
        return self._accion('laroca_inventario.action_laroca_alertas')

    def action_vender(self):
        return self._accion('laroca_inventario.action_laroca_vender')

    def action_pedir(self):
        return self._accion('laroca_inventario.action_laroca_pedir')

    def action_pedir_faltantes(self):
        """Abre "Pedir productos" con lo que se está acabando ya completado."""
        pendientes = self.env['laroca.inventario'].search([('estado', 'in', ('bajo', 'critico'))], order='prioridad')
        contexto = {'dialog_size': 'extra-large', 'default_completar_sugerido': True}
        if pendientes:
            contexto['default_gasolinera_id'] = pendientes[0].gasolinera_id.id
        return self._accion('laroca_inventario.action_laroca_pedir', context=contexto)

    def action_ver_pedidos(self):
        contexto = {'searchpanel_default_estado': 'enviado'} if self._es_admin() else {}
        return self._accion('laroca_inventario.action_laroca_pedidos', context=contexto)

    def action_ver_ventas(self):
        return self._accion('laroca_inventario.action_laroca_ventas')

    def action_ver_ventas_hoy(self):
        return self._accion('laroca_inventario.action_laroca_ventas',
                            domain=[('fecha', '>=', fields.Datetime.to_string(self._inicio_del_dia_utc()))],
                            context={'searchpanel_default_estado': 'confirmada'})

    def action_conteo(self):
        return self._accion('laroca_inventario.action_laroca_conteo')

    def action_recibir_mercaderia(self):
        return self._accion('laroca_inventario.action_laroca_bodega_recibir')

    def action_ver_bodega(self):
        return self.env['laroca.panel.bodega'].action_abrir_panel()

    def action_preparar_entrega(self):
        return self._accion('laroca_inventario.action_laroca_preparar_entrega')

    def action_ver_sugerencias(self):
        return self._accion('laroca_inventario.action_laroca_sugerencias')

    def action_ver_inventario(self):
        return self._accion('laroca_inventario.action_laroca_inventario')

    def action_ver_entregas(self):
        return self._accion('laroca_inventario.action_laroca_entregas')

    def action_ver_usuarios(self):
        return self._accion('laroca_inventario.action_laroca_usuarios')

    def action_importar(self):
        return self._accion('laroca_inventario.action_laroca_importar')

    def action_ver_sin_conteo(self):
        limite = fields.Datetime.now() - timedelta(days=DIAS_SIN_CONTEO)
        ids = self.env['stock.warehouse'].search([('laroca_es_gasolinera', '=', True)]).filtered(
            lambda g: not g.laroca_ultimo_conteo or g.laroca_ultimo_conteo < limite).ids
        action = self._accion('laroca_inventario.action_laroca_gasolineras', domain=[('id', 'in', ids)])
        action['name'] = f'Gasolineras sin actualizar en {DIAS_SIN_CONTEO} días'
        return action

    def action_reportes(self):
        return self._accion('laroca_inventario.action_laroca_reporte_wizard')
