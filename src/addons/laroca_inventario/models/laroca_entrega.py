import base64
import io

import xlsxwriter
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

from ..utils import accion_alerta, remitente_sistema


class LarocaEntrega(models.Model):
    """Entrega (abastecimiento) de productos desde la Bodega Central a una gasolinera.

    Flujo (BPMN propuesto, carriles "Administrador" y "Personal de entrega"):
      Borrador ──Confirmar──▶ En camino ──Confirmar recepción──▶ Entregada
         └──────────────Cancelar────────────┘
    Al confirmar se crea una transferencia interna nativa de Odoo (stock.picking) que
    reserva el stock en bodega; al confirmar la recepción se valida esa transferencia,
    el stock de la gasolinera sube y las alertas se resuelven solas.
    """
    _name = 'laroca.entrega'
    _description = 'Entrega de abastecimiento'
    _inherit = ['mail.thread']
    _order = 'fecha_programada desc, id desc'

    name = fields.Char('Referencia', required=True, readonly=True, copy=False, default='Nueva')
    gasolinera_id = fields.Many2one(
        'stock.warehouse', 'Gasolinera', required=True, index=True, tracking=True,
        domain=[('laroca_es_gasolinera', '=', True)])
    bodega_id = fields.Many2one(
        'stock.warehouse', 'Bodega de origen', required=True,
        default=lambda self: self.env.company._laroca_bodega_central(),
        domain=[('laroca_es_gasolinera', '=', False)])
    company_id = fields.Many2one(related='gasolinera_id.company_id', store=True)
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('en_camino', 'En camino'),
        ('entregada', 'Entregada'),
        ('cancelada', 'Cancelada'),
    ], 'Estado', default='borrador', required=True, readonly=True, tracking=True, index=True, copy=False)
    fecha_programada = fields.Date('Fecha programada', default=fields.Date.context_today, required=True, tracking=True)
    fecha_entrega = fields.Datetime('Fecha de entrega', readonly=True, copy=False)
    responsable_id = fields.Many2one('res.users', 'Responsable de la entrega', default=lambda self: self.env.user,
                                     domain=[('share', '=', False)], tracking=True)
    recibido_por_id = fields.Many2one('res.users', 'Recibido por', readonly=True, copy=False)
    notas = fields.Text('Notas')
    linea_ids = fields.One2many('laroca.entrega.linea', 'entrega_id', string='Productos', copy=True)
    picking_id = fields.Many2one('stock.picking', 'Transferencia de Odoo', readonly=True, copy=False)
    alerta_ids = fields.One2many('laroca.alerta', 'entrega_id', string='Alertas atendidas')
    pedido_id = fields.Many2one('laroca.pedido', 'Pedido de la gasolinera', readonly=True, copy=False, index=True)
    total_productos = fields.Integer('Cantidad de productos', compute='_compute_totales', store=True)
    total_unidades = fields.Float('Unidades enviadas', digits='Product Unit of Measure', compute='_compute_totales', store=True)
    total_entregado = fields.Float('Unidades entregadas', digits='Product Unit of Measure', compute='_compute_totales', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    valor_total = fields.Monetary('Valor (costo)', compute='_compute_totales', store=True,
                                  help='Costo de lo enviado (o de lo entregado, si ya se recibió).')

    @api.depends('linea_ids.cantidad', 'linea_ids.cantidad_entregada', 'linea_ids.valor')
    def _compute_totales(self):
        for entrega in self:
            entrega.total_productos = len(entrega.linea_ids)
            entrega.total_unidades = sum(entrega.linea_ids.mapped('cantidad'))
            entrega.total_entregado = sum(entrega.linea_ids.mapped('cantidad_entregada'))
            entrega.valor_total = sum(entrega.linea_ids.mapped('valor'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nueva') == 'Nueva':
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code('laroca.entrega') or 'Nueva'
        entregas = super().create(vals_list)
        _invalidar_en_entrega(self.env)
        return entregas

    def write(self, vals):
        res = super().write(vals)
        if 'estado' in vals or 'gasolinera_id' in vals:
            _invalidar_en_entrega(self.env)
        return res

    @api.constrains('gasolinera_id', 'bodega_id')
    def _check_origen_destino(self):
        for entrega in self:
            if entrega.gasolinera_id == entrega.bodega_id:
                raise ValidationError(_('La bodega de origen y la gasolinera no pueden ser la misma.'))

    @api.ondelete(at_uninstall=False)
    def _unlink_solo_borrador(self):
        if any(e.estado not in ('borrador', 'cancelada') for e in self):
            raise UserError(_('Solo se pueden eliminar entregas en borrador o canceladas.'))

    # ------------------------------------------------------------------
    # Permisos
    # ------------------------------------------------------------------
    def _es_admin(self):
        return self.env.user.has_group('laroca_inventario.group_laroca_admin')

    def _check_admin(self):
        if not self._es_admin():
            raise AccessError(_('Solo el administrador puede realizar esta acción.'))

    def _check_puede_recibir(self):
        """El administrador o un encargado de la gasolinera destino."""
        self.check_access('read')
        for entrega in self:
            if not (self._es_admin() or self.env.user in entrega.gasolinera_id.sudo().laroca_encargado_ids):
                raise AccessError(_('Solo el administrador o el encargado de %s puede confirmar la recepción.',
                                    entrega.gasolinera_id.name))

    # ------------------------------------------------------------------
    # Flujo
    # ------------------------------------------------------------------
    def action_confirmar(self):
        """Administrador aprueba la entrega: se reserva el stock en bodega."""
        self._check_admin()
        for entrega in self:
            if entrega.estado != 'borrador':
                raise UserError(_('%s no está en borrador.', entrega.name))
            lineas = entrega.linea_ids.filtered(lambda l: l.cantidad > 0)
            if not lineas:
                raise UserError(_('Agregá al menos un producto con cantidad mayor que cero.'))
            faltantes = [
                _('%(producto)s: se envían %(pedido)s, en bodega hay %(disponible)s',
                  producto=l.product_id.display_name, pedido=f'{l.cantidad:g}', disponible=f'{l.disponible_bodega:g}')
                for l in lineas
                if float_compare(l.cantidad, l.disponible_bodega, precision_rounding=l.uom_id.rounding) > 0
            ]
            if faltantes:
                raise UserError(_('No hay suficiente stock en %(bodega)s:\n%(detalle)s',
                                  bodega=entrega.bodega_id.name, detalle='\n'.join(faltantes)))
            picking = entrega._crear_transferencia(lineas)
            for linea in lineas:  # por defecto se espera recibir todo lo enviado
                linea.cantidad_entregada = linea.cantidad
            entrega.write({'estado': 'en_camino', 'picking_id': picking.id})
            entrega.pedido_id._entrega_actualizada('en_camino')
            entrega._vincular_alertas()
            entrega._avisar_encargados()

    def _crear_transferencia(self, lineas):
        """Transferencia interna nativa: Bodega Central / Existencias → Gasolinera / Existencias."""
        self.ensure_one()
        origen = self.bodega_id.lot_stock_id
        destino = self.gasolinera_id.lot_stock_id
        picking = self.env['stock.picking'].sudo().create({
            'picking_type_id': self.bodega_id.int_type_id.id,
            'location_id': origen.id,
            'location_dest_id': destino.id,
            'origin': self.name,
            'scheduled_date': fields.Datetime.to_datetime(self.fecha_programada),
            'move_ids': [(0, 0, {
                'name': linea.product_id.display_name,
                'product_id': linea.product_id.id,
                'product_uom_qty': linea.cantidad,
                'product_uom': linea.uom_id.id,
                'location_id': origen.id,
                'location_dest_id': destino.id,
            }) for linea in lineas],
        })
        picking.action_confirm()
        picking.action_assign()
        return picking

    def _vincular_alertas(self):
        alertas = self.env['laroca.alerta'].sudo().search([
            ('gasolinera_id', '=', self.gasolinera_id.id),
            ('product_id', 'in', self.linea_ids.product_id.ids),
            ('estado', '=', 'abierta'),
        ])
        alertas.write({'estado': 'en_proceso', 'entrega_id': self.id})

    def _avisar_encargados(self):
        """Notifica a los encargados de la gasolinera (bandeja de Odoo)."""
        encargados = self.gasolinera_id.sudo().laroca_encargado_ids
        if not encargados:
            return
        self.sudo().message_subscribe(partner_ids=encargados.partner_id.ids)
        filas = Markup('').join(
            Markup('<li>%s: <b>%s</b></li>') % (l.product_id.display_name, f'{l.cantidad:g}')
            for l in self.linea_ids if l.cantidad > 0)
        self.sudo().message_post(
            body=Markup('<p>🚚 La entrega <b>%s</b> va en camino a <b>%s</b> (programada para %s):</p><ul>%s</ul>'
                        '<p>Al recibirla, confirmá las cantidades con el botón <b>Confirmar recepción</b>.</p>') % (
                self.name, self.gasolinera_id.name, self.fecha_programada.strftime('%d/%m/%Y'), filas),
            email_from=remitente_sistema(self.env),
            message_type='comment', subtype_xmlid='mail.mt_comment',
            partner_ids=encargados.partner_id.ids)

    def action_marcar_entregada(self):
        """Recepción rápida: llegó todo lo enviado (administrador o encargado de la gasolinera).
        Si faltó algo, usar "Confirmar recepción" para corregir las cantidades."""
        for entrega in self:
            entrega._registrar_recepcion({})
        nombres = ', '.join(self.mapped('name'))
        return accion_alerta('success', _('¡Entregado!'),
                             _('%s quedó como entregada y el inventario de la gasolinera ya se actualizó.', nombres))

    def action_abrir_recepcion(self):
        self.ensure_one()
        self._check_puede_recibir()
        if self.estado != 'en_camino':
            raise UserError(_('Solo se puede recibir una entrega que está en camino.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Confirmar recepción - %s', self.name),
            'res_model': 'laroca.recepcion',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_entrega_id': self.id},
        }

    def _registrar_recepcion(self, cantidades):
        """Valida la transferencia con las cantidades recibidas.
        :param cantidades: {laroca.entrega.linea id: cantidad recibida}
        """
        self.ensure_one()
        self._check_puede_recibir()
        if self.estado != 'en_camino':
            raise UserError(_('Solo se puede recibir una entrega que está en camino.'))
        entrega = self.sudo()
        for linea in entrega.linea_ids:
            recibida = cantidades.get(linea.id, linea.cantidad_entregada)
            if recibida < 0 or float_compare(recibida, linea.cantidad, precision_rounding=linea.uom_id.rounding) > 0:
                raise UserError(_('%(producto)s: la cantidad recibida debe estar entre 0 y %(max)s.',
                                  producto=linea.product_id.display_name, max=f'{linea.cantidad:g}'))
            linea.cantidad_entregada = recibida
        if float_is_zero(sum(entrega.linea_ids.mapped('cantidad_entregada')), precision_digits=4):
            raise UserError(_('No se recibió ningún producto. Si la entrega no llegó, el administrador puede cancelarla.'))

        picking = entrega.picking_id
        for move in picking.move_ids:
            linea = entrega.linea_ids.filtered(lambda l: l.product_id == move.product_id)[:1]
            move.quantity = linea.cantidad_entregada if linea else 0.0
            move.picked = True
        resultado = picking.with_context(
            skip_backorder=True, picking_ids_not_to_backorder=picking.ids, skip_sms=True,
        ).button_validate()
        if isinstance(resultado, dict):  # Odoo pidió un asistente: no debería ocurrir
            raise UserError(_('Odoo no pudo validar la transferencia %s automáticamente.', picking.name))

        entrega.write({
            'estado': 'entregada',
            'fecha_entrega': fields.Datetime.now(),
            'recibido_por_id': self.env.uid,
        })
        # Alertas que siguen sin resolverse (entrega parcial) vuelven a quedar abiertas.
        entrega.alerta_ids.filtered(lambda a: a.estado == 'en_proceso').write({'estado': 'abierta'})
        entrega.pedido_id._entrega_actualizada('entregada')
        entrega._publicar_recepcion()
        return True

    def _publicar_recepcion(self):
        incompletas = self.linea_ids.filtered(lambda l: l.cantidad_entregada < l.cantidad)
        detalle = Markup('')
        if incompletas:
            detalle = Markup('<p>⚠️ Recibido incompleto:</p><ul>%s</ul>') % Markup('').join(
                Markup('<li>%s: %s de %s</li>') % (l.product_id.display_name, f'{l.cantidad_entregada:g}', f'{l.cantidad:g}')
                for l in incompletas)
        cuerpo = Markup('<p>✅ Entrega %s recibida en <b>%s</b> por %s: %s unidades.</p>%s') % (
            self._get_html_link(self.name), self.gasolinera_id.name, self.env.user.name,
            f'{self.total_entregado:g}', detalle)
        self.env['laroca.alerta']._publicar_en_canal(cuerpo)
        self.message_post(body=cuerpo, message_type='comment', subtype_xmlid='mail.mt_note')

    def action_cancelar(self):
        self._check_admin()
        for entrega in self:
            if entrega.estado == 'entregada':
                raise UserError(_('%s ya fue entregada; no se puede cancelar.', entrega.name))
            if entrega.picking_id and entrega.picking_id.state not in ('done', 'cancel'):
                entrega.picking_id.sudo().action_cancel()
            entrega.alerta_ids.filtered(lambda a: a.estado == 'en_proceso').sudo().write(
                {'estado': 'abierta', 'entrega_id': False})
            entrega.estado = 'cancelada'
            if entrega.pedido_id:
                entrega.pedido_id._entrega_actualizada('cancelada')
                entrega.pedido_id = False

    def action_volver_borrador(self):
        self._check_admin()
        self.filtered(lambda e: e.estado == 'cancelada').write({'estado': 'borrador', 'picking_id': False})

    # ------------------------------------------------------------------
    # Hoja de entrega en Excel (la versión PDF está en report/entrega_report.xml)
    # ------------------------------------------------------------------
    def _datos_hoja(self):
        """Datos de la hoja: para qué gasolinera, el lugar, el pedido y qué llevar."""
        self.ensure_one()
        entrega = self.sudo()
        g = entrega.gasolinera_id
        lineas = entrega.linea_ids.filtered(lambda l: l.cantidad > 0)
        return {
            'gasolinera': g.name,
            'lugar': ', '.join(filter(None, [g.laroca_direccion, g.laroca_municipio, g.laroca_departamento])),
            'telefono': g.laroca_telefono or '',
            'encargado': ', '.join(g.laroca_encargado_ids.mapped('name')),
            'pedido': entrega.pedido_id.name or '',
            'pedido_por': entrega.pedido_id.solicitante_id.name or '',
            'envio_admin': entrega.pedido_id.origen == 'administrador',
            'lineas': [(l.default_code or '', l.product_id.with_context(display_default_code=False).display_name,
                        l.cantidad) for l in lineas],
            'resumen': ', '.join(f'{l.cantidad:g} {l.product_id.name}' for l in lineas),
        }

    def action_descargar_excel(self):
        self.ensure_one()
        datos = self._datos_hoja()
        salida = io.BytesIO()
        libro = xlsxwriter.Workbook(salida, {'in_memory': True})
        hoja = libro.add_worksheet('Entrega')
        titulo = libro.add_format({'bold': True, 'font_size': 16, 'font_color': '#0B3D91'})
        etiqueta = libro.add_format({'bold': True, 'bg_color': '#E8EEF8', 'border': 1})
        celda = libro.add_format({'border': 1, 'text_wrap': True, 'valign': 'top'})
        cabecera = libro.add_format({'bold': True, 'bg_color': '#0B3D91', 'font_color': '#FFFFFF', 'border': 1})
        numero = libro.add_format({'border': 1, 'num_format': '0', 'bold': True})
        hoja.set_column('A:A', 14)
        hoja.set_column('B:B', 44)
        hoja.set_column('C:D', 14)
        hoja.write('A1', f'Hoja de entrega {self.name} — Grupo La Roca', titulo)
        filas = [
            ('Gasolinera', datos['gasolinera']),
            ('Lugar', datos['lugar']),
            ('Teléfono', datos['telefono']),
            ('Encargado', datos['encargado']),
            ('Pedido', f"{datos['pedido']} (envío del administrador)" if datos['envio_admin']
             else f"{datos['pedido']} ({datos['pedido_por']})" if datos['pedido'] else 'Sin pedido (entrega del administrador)'),
            ('Fecha de entrega', self.fecha_programada.strftime('%d/%m/%Y')),
            ('Lleva la entrega', self.responsable_id.name or ''),
            ('Llevar', datos['resumen']),
        ]
        for indice, (nombre, valor) in enumerate(filas, start=2):
            hoja.write(indice, 0, nombre, etiqueta)
            hoja.merge_range(indice, 1, indice, 3, valor, celda)
        inicio = len(filas) + 3
        for columna, texto in enumerate(['Código', 'Producto', 'Cantidad', 'Recibido ✓']):
            hoja.write(inicio, columna, texto, cabecera)
        for indice, (codigo, producto, cantidad) in enumerate(datos['lineas'], start=inicio + 1):
            hoja.write(indice, 0, codigo, celda)
            hoja.write(indice, 1, producto, celda)
            hoja.write_number(indice, 2, cantidad, numero)
            hoja.write(indice, 3, '', celda)
        total = inicio + 1 + len(datos['lineas'])
        hoja.write(total, 1, 'Total de unidades', etiqueta)
        hoja.write_number(total, 2, sum(c for _a, _b, c in datos['lineas']), numero)
        hoja.write(total + 3, 0, 'Entregado por: ____________________')
        hoja.write(total + 3, 2, 'Recibido por: ____________________')
        libro.close()
        adjunto = self.env['ir.attachment'].sudo().create({
            'name': f'Entrega {self.name}.xlsx',
            'datas': base64.b64encode(salida.getvalue()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {'type': 'ir.actions.act_url', 'url': f'/web/content/{adjunto.id}?download=true', 'target': 'download',
                'close': True}

    def action_ver_transferencia(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
        }


class LarocaEntregaLinea(models.Model):
    _name = 'laroca.entrega.linea'
    _description = 'Producto de una entrega'
    _order = 'entrega_id, id'

    entrega_id = fields.Many2one('laroca.entrega', 'Entrega', required=True, ondelete='cascade', index=True)
    gasolinera_id = fields.Many2one(related='entrega_id.gasolinera_id', store=True, index=True)
    estado = fields.Selection(related='entrega_id.estado', store=True)
    fecha_programada = fields.Date(related='entrega_id.fecha_programada', store=True)
    fecha_entrega = fields.Datetime(related='entrega_id.fecha_entrega', store=True)
    company_id = fields.Many2one(related='entrega_id.company_id', store=True)
    product_id = fields.Many2one('product.product', 'Producto', required=True,
                                 domain=[('is_storable', '=', True)])
    default_code = fields.Char(related='product_id.default_code', string='Código')
    categ_id = fields.Many2one(related='product_id.categ_id', store=True, string='Categoría')
    uom_id = fields.Many2one(related='product_id.uom_id', string='Unidad')
    cantidad = fields.Float('Cantidad a enviar', digits='Product Unit of Measure', required=True, default=1.0)
    cantidad_sugerida = fields.Float('Sugerida', digits='Product Unit of Measure', readonly=True,
                                     help='Cantidad sugerida por el sistema al crear la entrega.')
    cantidad_entregada = fields.Float('Cantidad entregada', digits='Product Unit of Measure', readonly=True, copy=False)
    currency_id = fields.Many2one(related='entrega_id.currency_id')
    costo_unitario = fields.Float('Costo unitario', digits='Product Price',
                                  help='Costo del producto al crear la entrega (queda fijo para el historial).')
    valor = fields.Monetary('Valor', compute='_compute_valor', store=True)
    stock_gasolinera = fields.Float('Stock en gasolinera', compute='_compute_existencias',
                                    digits='Product Unit of Measure')
    disponible_bodega = fields.Float('Disponible en bodega', compute='_compute_existencias',
                                     digits='Product Unit of Measure')

    _sql_constraints = [
        ('producto_uniq', 'unique(entrega_id, product_id)', 'El producto ya está en esta entrega.'),
        ('cantidad_positiva', 'CHECK(cantidad >= 0)', 'La cantidad no puede ser negativa.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'costo_unitario' not in vals and vals.get('product_id'):
                vals['costo_unitario'] = self.env['product.product'].browse(vals['product_id']).standard_price
        lineas = super().create(vals_list)
        _invalidar_en_entrega(self.env)
        return lineas

    @api.depends('cantidad', 'cantidad_entregada', 'costo_unitario', 'entrega_id.estado')
    def _compute_valor(self):
        for linea in self:
            cantidad = linea.cantidad_entregada if linea.entrega_id.estado == 'entregada' else linea.cantidad
            linea.valor = cantidad * linea.costo_unitario

    def write(self, vals):
        res = super().write(vals)
        if 'cantidad' in vals or 'product_id' in vals:
            _invalidar_en_entrega(self.env)
        return res

    def unlink(self):
        res = super().unlink()
        _invalidar_en_entrega(self.env)
        return res

    @api.depends('product_id', 'entrega_id.gasolinera_id', 'entrega_id.bodega_id')
    def _compute_existencias(self):
        Quant = self.env['stock.quant'].sudo()
        for linea in self:
            linea.stock_gasolinera = linea.disponible_bodega = 0.0
            if not linea.product_id:
                continue
            # sudo: el encargado no tiene acceso a la bodega central, pero puede ver cuánto hay
            entrega = linea.entrega_id.sudo()
            gasolinera, bodega = entrega.gasolinera_id, entrega.bodega_id
            if gasolinera:
                linea.stock_gasolinera = sum(Quant.search([
                    ('product_id', '=', linea.product_id.id),
                    ('location_id', 'child_of', gasolinera.lot_stock_id.id)]).mapped('quantity'))
            if bodega:
                # Disponible = existencias - reservado (lo apartado para otras entregas en camino).
                quants = Quant.search([
                    ('product_id', '=', linea.product_id.id),
                    ('location_id', 'child_of', bodega.lot_stock_id.id)])
                linea.disponible_bodega = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))


def _invalidar_en_entrega(env):
    """'En entrega' del inventario se calcula al vuelo; si cambian las entregas
    hay que descartar el valor guardado en memoria."""
    env['laroca.inventario'].invalidate_model(['cantidad_en_entrega'])
