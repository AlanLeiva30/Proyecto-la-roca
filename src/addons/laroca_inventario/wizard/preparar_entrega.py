from markupsafe import Markup

from odoo import _, api, fields, models

from ..utils import accion_alerta


class LarocaPrepararEntrega(models.TransientModel):
    """Pantalla "Preparar entrega" del administrador, para sus envíos propios
    ("hoy les llevo llaveros extra"). Los pedidos de los encargados se atienden desde el pedido
    (botón "Aprobar y preparar entrega").

    Se elige la gasolinera, se agregan los productos con − / + y se genera la hoja en PDF o Excel.
    Al generarla se crea la entrega (laroca.entrega) y, si se marca "Enviar ahora", queda
    En camino y se avisa al encargado.
    """
    _name = 'laroca.preparar.entrega'
    _description = 'Preparar una entrega'

    gasolinera_id = fields.Many2one(
        'stock.warehouse', 'Gasolinera', required=True,
        domain=[('laroca_es_gasolinera', '=', True)])
    lugar = fields.Char('Lugar', compute='_compute_lugar')
    encargados = fields.Char('Encargado', compute='_compute_lugar')
    fecha_programada = fields.Date('Fecha de entrega', required=True, default=fields.Date.context_today)
    responsable_id = fields.Many2one('res.users', 'Lleva la entrega', default=lambda self: self.env.user,
                                     domain=[('share', '=', False)])
    notas = fields.Char('Notas', help='Indicaciones para quien lleva la entrega.')
    enviar = fields.Boolean('Enviar ahora (queda "En camino" y se avisa al encargado)', default=True)
    completar_sugerido = fields.Boolean(
        'Completar con lo sugerido',
        help='Escribe la cantidad sugerida en los productos bajos y críticos (sin pasar de lo que hay en bodega).')
    buscar = fields.Char('Buscar producto')
    categ_id = fields.Many2one('product.category', 'Categoría', help='Vacío = todas.')
    linea_ids = fields.One2many('laroca.preparar.entrega.linea', 'preparar_id', string='Productos')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    total_unidades = fields.Float('Unidades', digits='Product Unit of Measure', compute='_compute_totales')
    total_productos = fields.Integer('N.º de productos', compute='_compute_totales')
    resumen = fields.Char('Llevar', compute='_compute_totales')

    @api.depends('gasolinera_id')
    def _compute_lugar(self):
        for wizard in self:
            g = wizard.gasolinera_id.sudo()
            wizard.lugar = ', '.join(filter(None, [g.laroca_direccion, g.laroca_municipio, g.laroca_departamento]))
            wizard.encargados = ', '.join(g.laroca_encargado_ids.mapped('name')) or _('Sin encargado asignado')

    @api.depends('linea_ids.cantidad')
    def _compute_totales(self):
        for wizard in self:
            lineas = wizard.linea_ids.filtered(lambda l: l.cantidad > 0)
            wizard.total_unidades = sum(lineas.mapped('cantidad'))
            wizard.total_productos = len(lineas)
            wizard.resumen = ', '.join(
                f'{l.cantidad:g} {l.product_id.with_context(display_default_code=False).display_name}'
                for l in lineas)

    @api.onchange('gasolinera_id', 'categ_id', 'buscar')
    def _onchange_cargar_productos(self):
        # Se conservan las cantidades ya escritas (por ejemplo, al buscar otro producto)
        anteriores = {l.inventario_id.id: l.cantidad for l in self.linea_ids
                      if l.cantidad and l.inventario_id.gasolinera_id == self.gasolinera_id}
        comandos = [(5, 0, 0)]
        if self.gasolinera_id:
            Inventario = self.env['laroca.inventario']
            dominio = [('gasolinera_id', '=', self.gasolinera_id.id)]
            if self.categ_id:
                dominio.append(('categ_id', 'child_of', self.categ_id.id))
            if self.buscar:
                dominio.append(('product_id', 'ilike', self.buscar))
            lineas = Inventario.search(dominio, order='prioridad, categ_id, default_code, id')
            # Lo que más falta, primero
            lineas |= Inventario.browse(list(anteriores)).filtered(lambda l: l.gasolinera_id == self.gasolinera_id)
            for linea in lineas:
                cantidad = anteriores.get(linea.id, 0)
                if self.completar_sugerido and not cantidad and linea.estado in ('bajo', 'critico'):
                    cantidad = min(linea.cantidad_sugerida, max(linea.disponible_bodega, 0))
                comandos.append((0, 0, {'inventario_id': linea.id, 'cantidad': cantidad}))
        self.linea_ids = comandos

    @api.onchange('completar_sugerido')
    def _onchange_completar_sugerido(self):
        for linea in self.linea_ids.filtered(lambda l: l.estado in ('bajo', 'critico') and l.cantidad_sugerida > 0):
            sugerida = min(linea.cantidad_sugerida, max(linea.disponible_bodega, 0))
            if self.completar_sugerido and not linea.cantidad:
                linea.cantidad = sugerida
            elif not self.completar_sugerido and linea.cantidad == sugerida:
                linea.cantidad = 0

    # ------------------------------------------------------------------
    # Generar la entrega y la hoja
    # ------------------------------------------------------------------
    def _crear_entrega(self):
        self.ensure_one()
        self.env['laroca.entrega']._check_admin()
        cantidades = {}
        for linea in self.linea_ids.filtered(lambda l: l.cantidad > 0):
            cantidades[linea.product_id] = cantidades.get(linea.product_id, 0) + linea.cantidad
        if not cantidades:
            return None
        entrega = self.env['laroca.entrega'].create({
            'gasolinera_id': self.gasolinera_id.id,
            'fecha_programada': self.fecha_programada,
            'responsable_id': self.responsable_id.id,
            'notas': self.notas,
            'linea_ids': [(0, 0, {'product_id': p.id, 'cantidad': c}) for p, c in cantidades.items()],
        })
        # Queda también en "Pedidos" como envío del administrador, con su lista de productos
        pedido = self.env['laroca.pedido'].sudo().create({
            'gasolinera_id': self.gasolinera_id.id,
            'solicitante_id': self.env.uid,
            'origen': 'administrador',
            'nota': self.notas,
            'linea_ids': [(0, 0, {'product_id': p.id, 'cantidad': c}) for p, c in cantidades.items()],
        })
        pedido.write({'estado': 'aprobado', 'fecha_envio': fields.Datetime.now(), 'entrega_id': entrega.id})
        entrega.pedido_id = pedido
        if self.enviar:
            entrega.action_confirmar()  # reserva en bodega (avisa si no alcanza) y avisa al encargado
        return entrega

    def _faltantes_bodega(self):
        """Productos de los que se quiere llevar más de lo que hay en bodega."""
        return [_('%(producto)s: querés llevar %(cantidad)s y en bodega hay %(hay)s',
                  producto=l.product_id.with_context(display_default_code=False).display_name,
                  cantidad=f'{l.cantidad:g}', hay=f'{max(l.disponible_bodega, 0):g}')
                for l in self.linea_ids if l.cantidad > max(l.disponible_bodega, 0)]

    def _verificar(self):
        """None si se puede generar; si no, la alerta que explica qué falta."""
        if not self.linea_ids.filtered(lambda l: l.cantidad > 0):
            return self._sin_productos()
        faltantes = self._faltantes_bodega()
        if faltantes:
            return accion_alerta('error', _('No alcanza lo que hay en bodega'),
                                 _('Bajá estas cantidades (el resto queda como está):'), faltantes)
        return None

    def _sin_productos(self):
        return accion_alerta('warning', _('¿Qué vas a llevar?'),
                             _('Agregá al menos un producto con − y +, o encendé "Completar con lo sugerido".'))

    def action_generar_pdf(self):
        alerta = self._verificar()
        if alerta:
            return alerta
        entrega = self._crear_entrega()
        accion = self.env.ref('laroca_inventario.action_report_laroca_entrega').report_action(entrega)
        accion['close_on_report_download'] = True
        return accion

    def action_generar_excel(self):
        alerta = self._verificar()
        if alerta:
            return alerta
        entrega = self._crear_entrega()
        return entrega.action_descargar_excel()


class LarocaPrepararEntregaLinea(models.TransientModel):
    _name = 'laroca.preparar.entrega.linea'
    _description = 'Producto en la pantalla Preparar entrega'

    preparar_id = fields.Many2one('laroca.preparar.entrega', 'Pantalla', required=True, ondelete='cascade')
    inventario_id = fields.Many2one('laroca.inventario', required=True)
    product_id = fields.Many2one(related='inventario_id.product_id', string='Producto')
    image_128 = fields.Image(related='inventario_id.image_128')
    estado = fields.Selection(related='inventario_id.estado')
    stock_actual = fields.Float(related='inventario_id.stock_actual', string='En gasolinera')
    cantidad_sugerida = fields.Float(related='inventario_id.cantidad_sugerida', string='Sugerido')
    disponible_bodega = fields.Float(related='inventario_id.disponible_bodega', string='En bodega')
    cantidad = fields.Float('Llevar', digits='Product Unit of Measure')
