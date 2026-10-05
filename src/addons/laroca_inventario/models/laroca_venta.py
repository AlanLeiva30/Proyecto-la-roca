from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_compare


class LarocaVenta(models.Model):
    """Venta registrada en una gasolinera ("vendí 5 llaveros").

    Se crea desde la pantalla "Vender" (asistente laroca.vender) y descuenta el stock con
    una salida nativa de Odoo (stock.picking de tipo entrega, de la gasolinera al cliente).
    Una venta no se modifica: si hubo un error, el administrador la anula y el stock vuelve.
    """
    _name = 'laroca.venta'
    _description = 'Venta de una gasolinera'
    _inherit = ['mail.thread']
    _order = 'fecha desc, id desc'

    name = fields.Char('Referencia', required=True, readonly=True, copy=False, default='Nueva')
    gasolinera_id = fields.Many2one('stock.warehouse', 'Gasolinera', required=True, readonly=True, index=True)
    company_id = fields.Many2one(related='gasolinera_id.company_id', store=True)
    vendedor_id = fields.Many2one('res.users', 'Vendido por', readonly=True, default=lambda self: self.env.user)
    fecha = fields.Datetime('Fecha', readonly=True, default=fields.Datetime.now, index=True)
    estado = fields.Selection([('confirmada', 'Confirmada'), ('anulada', 'Anulada')], 'Estado',
                              default='confirmada', required=True, readonly=True, tracking=True, index=True)
    linea_ids = fields.One2many('laroca.venta.linea', 'venta_id', string='Productos', readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    total_unidades = fields.Float('Unidades', digits='Product Unit of Measure', compute='_compute_totales', store=True)
    total = fields.Monetary('Total', compute='_compute_totales', store=True)
    picking_id = fields.Many2one('stock.picking', 'Salida de Odoo', readonly=True, copy=False)
    picking_anulacion_id = fields.Many2one('stock.picking', 'Devolución de Odoo', readonly=True, copy=False)
    motivo_anulacion = fields.Char('Motivo de la anulación', readonly=True)

    @api.depends('linea_ids.cantidad', 'linea_ids.subtotal')
    def _compute_totales(self):
        for venta in self:
            venta.total_unidades = sum(venta.linea_ids.mapped('cantidad'))
            venta.total = sum(venta.linea_ids.mapped('subtotal'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nueva') == 'Nueva':
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code('laroca.venta') or 'Nueva'
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_nunca(self):
        raise UserError(_('Las ventas no se eliminan. El administrador puede anularlas.'))

    # ------------------------------------------------------------------
    # Registrar una venta
    # ------------------------------------------------------------------
    @api.model
    def _registrar(self, gasolinera, cantidades):
        """Registra una venta y descuenta el stock.

        :param gasolinera: stock.warehouse donde se vende (debe ser del usuario)
        :param cantidades: {product.product: cantidad vendida}
        :return: laroca.venta creada
        """
        gasolinera = gasolinera.with_env(self.env)  # se verifica con los permisos de quien vende
        gasolinera.check_access('read')  # reglas: el encargado solo vende en sus gasolineras
        if not gasolinera.laroca_es_gasolinera:
            raise UserError(_('Solo se puede vender en una gasolinera.'))
        cantidades = {p: c for p, c in cantidades.items() if c > 0}
        if not cantidades:
            raise UserError(_('Escribí cuántas unidades vendiste de al menos un producto.'))
        faltantes = self._faltantes(gasolinera, cantidades)
        if faltantes:
            raise UserError(_('No hay suficientes unidades en %(gasolinera)s:\n%(detalle)s',
                              gasolinera=gasolinera.name, detalle='\n'.join(faltantes)))
        # sudo: el encargado no crea registros de inventario directamente; ya se validó todo arriba.
        venta = self.sudo().create({
            'gasolinera_id': gasolinera.id,
            'vendedor_id': self.env.uid,
            'linea_ids': [(0, 0, {'product_id': p.id, 'cantidad': c, 'precio_unitario': p.lst_price})
                          for p, c in cantidades.items()],
        })
        origen = gasolinera.lot_stock_id
        destino = self.env.ref('stock.stock_location_customers')
        venta.picking_id = venta._mover_stock(gasolinera.out_type_id, origen, destino, venta.name)
        return venta.with_env(self.env)

    @api.model
    def _faltantes(self, gasolinera, cantidades):
        """Productos de los que se quiere vender más de lo que hay.
        :return: lista de textos, por ejemplo "Llavero: querés vender 25 y hay 17"
        """
        Quant = self.env['stock.quant'].sudo()
        faltantes = []
        for producto, cantidad in cantidades.items():
            hay = Quant._get_available_quantity(producto, gasolinera.lot_stock_id)
            if float_compare(cantidad, hay, precision_rounding=producto.uom_id.rounding) > 0:
                faltantes.append(_('%(producto)s: querés vender %(cantidad)s y hay %(hay)s',
                                   producto=producto.with_context(display_default_code=False).display_name,
                                   cantidad=f'{cantidad:g}', hay=f'{hay:g}'))
        return faltantes

    def _mover_stock(self, tipo, origen, destino, referencia):
        """Crea y valida una transferencia nativa de Odoo con los productos de la venta."""
        self.ensure_one()
        picking = self.env['stock.picking'].sudo().create({
            'picking_type_id': tipo.id,
            'location_id': origen.id,
            'location_dest_id': destino.id,
            'origin': referencia,
            'move_ids': [(0, 0, {
                'name': linea.product_id.display_name,
                'product_id': linea.product_id.id,
                'product_uom_qty': linea.cantidad,
                'product_uom': linea.product_id.uom_id.id,
                'location_id': origen.id,
                'location_dest_id': destino.id,
            }) for linea in self.linea_ids],
        })
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        resultado = picking.with_context(skip_backorder=True, picking_ids_not_to_backorder=picking.ids,
                                         skip_sms=True).button_validate()
        if isinstance(resultado, dict):  # Odoo pidió un asistente: no debería ocurrir
            raise UserError(_('Odoo no pudo validar la transferencia %s automáticamente.', picking.name))
        return picking

    # ------------------------------------------------------------------
    # Anular (solo administrador)
    # ------------------------------------------------------------------
    def action_abrir_anulacion(self):
        self.ensure_one()
        self._check_admin()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Anular venta %s', self.name),
            'res_model': 'laroca.venta.anulacion',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_venta_id': self.id},
        }

    def _check_admin(self):
        if not self.env.user.has_group('laroca_inventario.group_laroca_admin'):
            raise AccessError(_('Solo el administrador puede anular ventas.'))

    def _anular(self, motivo):
        """Devuelve los productos al stock de la gasolinera."""
        self.ensure_one()
        self._check_admin()
        if self.estado != 'confirmada':
            raise UserError(_('La venta %s ya está anulada.', self.name))
        venta = self.sudo()
        tipo = venta.gasolinera_id.in_type_id
        devolucion = venta._mover_stock(tipo, self.env.ref('stock.stock_location_customers'),
                                        venta.gasolinera_id.lot_stock_id, _('Anulación de %s', venta.name))
        venta.write({'estado': 'anulada', 'picking_anulacion_id': devolucion.id, 'motivo_anulacion': motivo})
        venta.message_post(body=Markup('<p>Venta anulada por %s. Motivo: %s</p>') % (self.env.user.name, motivo),
                           message_type='comment', subtype_xmlid='mail.mt_note')


class LarocaVentaLinea(models.Model):
    _name = 'laroca.venta.linea'
    _description = 'Producto vendido'
    _order = 'venta_id, id'

    venta_id = fields.Many2one('laroca.venta', 'Venta', required=True, ondelete='cascade', index=True)
    gasolinera_id = fields.Many2one(related='venta_id.gasolinera_id', store=True, index=True)
    fecha = fields.Datetime(related='venta_id.fecha', store=True)
    estado = fields.Selection(related='venta_id.estado', store=True)
    vendedor_id = fields.Many2one(related='venta_id.vendedor_id', store=True)
    company_id = fields.Many2one(related='venta_id.company_id', store=True)
    product_id = fields.Many2one('product.product', 'Producto', required=True, readonly=True)
    categ_id = fields.Many2one(related='product_id.categ_id', store=True, string='Categoría')
    cantidad = fields.Float('Cantidad', digits='Product Unit of Measure', readonly=True)
    currency_id = fields.Many2one(related='venta_id.currency_id')
    precio_unitario = fields.Monetary('Precio', readonly=True,
                                      help='Precio de venta del catálogo al momento de la venta.')
    subtotal = fields.Monetary('Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('cantidad', 'precio_unitario')
    def _compute_subtotal(self):
        for linea in self:
            linea.subtotal = linea.cantidad * linea.precio_unitario
