from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..utils import accion_alerta


class LarocaBodegaMovimiento(models.TransientModel):
    """Bodega Central: el administrador registra la mercadería que recibe ("llegaron 100 llaveros")
    o corrige las existencias después de contar. Los encargados solo ven el resultado."""
    _name = 'laroca.bodega.movimiento'
    _description = 'Recibir mercadería o contar la bodega central'

    modo = fields.Selection([
        ('recibir', 'Recibí mercadería (se suma)'),
        ('contar', 'Conté la bodega (queda la cantidad exacta)'),
    ], 'Qué hacés', required=True, default='recibir')
    proveedor = fields.Char('Proveedor', help='Opcional: de quién llegó la mercadería.')
    referencia = fields.Char('Factura / referencia', help='Opcional: número de factura o nota de envío.')
    buscar = fields.Char('Buscar producto')
    categ_id = fields.Many2one('product.category', 'Categoría', help='Vacío = todas.')
    linea_ids = fields.One2many('laroca.bodega.movimiento.linea', 'movimiento_id', string='Productos')
    total_unidades = fields.Float('Unidades', digits='Product Unit of Measure', compute='_compute_total')

    @api.depends('linea_ids.cantidad', 'linea_ids.en_bodega', 'modo')
    def _compute_total(self):
        for wizard in self:
            if wizard.modo == 'recibir':
                wizard.total_unidades = sum(wizard.linea_ids.mapped('cantidad'))
            else:
                wizard.total_unidades = sum(abs(l.cantidad - l.en_bodega) for l in wizard.linea_ids)

    @api.onchange('categ_id', 'buscar', 'modo')
    def _onchange_cargar_productos(self):
        # Se conservan las cantidades escritas (salvo al cambiar de modo)
        cambio_modo = self.linea_ids and self.linea_ids[:1].modo_linea != self.modo
        anteriores = {} if cambio_modo else {l.product_id.id: l.cantidad for l in self.linea_ids
                                             if l.cantidad != (l.en_bodega if self.modo == 'contar' else 0)}
        dominio = [('is_storable', '=', True)]
        if self.env.context.get('laroca_productos'):
            dominio.append(('id', 'in', self.env.context['laroca_productos']))
        if self.categ_id:
            dominio.append(('categ_id', 'child_of', self.categ_id.id))
        if self.buscar:
            dominio += ['|', ('name', 'ilike', self.buscar), ('default_code', 'ilike', self.buscar)]
        Producto = self.env['product.product']
        productos = Producto.search(dominio, order='categ_id, default_code, id') | Producto.browse(list(anteriores))
        comandos = [(5, 0, 0)]
        for producto in productos:
            en_bodega = producto.product_tmpl_id.laroca_stock_bodega
            inicial = en_bodega if self.modo == 'contar' else 0
            comandos.append((0, 0, {'product_id': producto.id, 'en_bodega': en_bodega,
                                    'cantidad': anteriores.get(producto.id, inicial), 'modo_linea': self.modo}))
        self.linea_ids = comandos

    def action_guardar(self):
        self.ensure_one()
        self.env['laroca.entrega']._check_admin()
        bodega = self.env.company._laroca_bodega_central()
        if not bodega:
            raise UserError(_('No hay una bodega central configurada (La Roca → Configuración → Parámetros).'))
        if self.modo == 'recibir':
            lineas = self.linea_ids.filtered(lambda l: l.cantidad > 0)
            if not lineas:
                return accion_alerta('warning', _('¿Qué llegó?'),
                                     _('Escribí con − y + cuántas unidades recibiste de al menos un producto.'))
            picking = self._recibir_productos(
                bodega, {l.product_id: l.cantidad for l in lineas},
                ' - '.join(filter(None, [self.proveedor, self.referencia])))
            detalle = [f'+{l.cantidad:g} {l.product_id.with_context(display_default_code=False).display_name}'
                       for l in lineas]
            return accion_alerta('success', _('¡Mercadería recibida!'),
                                 _('%(ref)s · %(unidades)s unidades sumadas a la bodega central.',
                                   ref=picking.name, unidades=f'{sum(lineas.mapped("cantidad")):g}'),
                                 detalle, cerrar=True)
        lineas = self.linea_ids.filtered(lambda l: l.cantidad != l.en_bodega)
        if not lineas:
            return accion_alerta('info', _('Sin cambios'), _('Las cantidades contadas son iguales a las del sistema.'))
        if any(l.cantidad < 0 for l in lineas):
            raise UserError(_('Las cantidades no pueden ser negativas.'))
        self._contar(bodega, lineas)
        detalle = [f'{l.product_id.with_context(display_default_code=False).display_name}: '
                   f'{l.en_bodega:g} → {l.cantidad:g}' for l in lineas]
        return accion_alerta('success', _('Bodega actualizada'), _('Se corrigieron %s productos.', len(lineas)),
                             detalle, cerrar=True)

    @api.model
    def _recibir_productos(self, bodega, cantidades, texto=''):
        """Entrada nativa de Odoo: proveedores → Bodega Central / Existencias.
        :param cantidades: {product.product: cantidad recibida}
        """
        origen = self.env.ref('stock.stock_location_suppliers')
        destino = bodega.lot_stock_id
        picking = self.env['stock.picking'].sudo().create({
            'picking_type_id': bodega.in_type_id.id,
            'location_id': origen.id,
            'location_dest_id': destino.id,
            'origin': texto or _('Mercadería recibida'),
            'move_ids': [(0, 0, {
                'name': producto.display_name, 'product_id': producto.id,
                'product_uom_qty': cantidad, 'product_uom': producto.uom_id.id,
                'location_id': origen.id, 'location_dest_id': destino.id,
            }) for producto, cantidad in cantidades.items()],
        })
        picking.action_confirm()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        resultado = picking.with_context(skip_backorder=True, skip_sms=True).button_validate()
        if isinstance(resultado, dict):
            raise UserError(_('Odoo no pudo validar la recepción %s automáticamente.', picking.name))
        return picking

    def _contar(self, bodega, lineas):
        """Ajuste de inventario nativo en la Bodega Central (queda en el historial)."""
        Quant = self.env['stock.quant'].sudo()
        quants = Quant.browse()
        for linea in lineas:
            quant = Quant._gather(linea.product_id, bodega.lot_stock_id, strict=True)[:1] or Quant.create(
                {'product_id': linea.product_id.id, 'location_id': bodega.lot_stock_id.id})
            quant.inventory_quantity = quant.quantity + (linea.cantidad - linea.en_bodega)
            quants |= quant
        quants.with_context(inventory_name=_('Conteo de bodega (%s)', self.env.user.name))._apply_inventory()


class LarocaBodegaMovimientoLinea(models.TransientModel):
    _name = 'laroca.bodega.movimiento.linea'
    _description = 'Producto en Recibir mercadería'

    movimiento_id = fields.Many2one('laroca.bodega.movimiento', 'Pantalla', required=True, ondelete='cascade')
    modo_linea = fields.Char()
    product_id = fields.Many2one('product.product', 'Producto', required=True)
    default_code = fields.Char(related='product_id.default_code', string='Código')
    image_128 = fields.Image(related='product_id.image_128')
    en_bodega = fields.Float('En bodega', digits='Product Unit of Measure', readonly=True)
    cantidad = fields.Float('Cantidad', digits='Product Unit of Measure')
    queda = fields.Float('Quedará', digits='Product Unit of Measure', compute='_compute_queda',
                         help='Cuánto habrá en bodega después de guardar.')

    @api.depends('cantidad', 'en_bodega', 'movimiento_id.modo')
    def _compute_queda(self):
        for linea in self:
            linea.queda = linea.en_bodega + linea.cantidad if linea.movimiento_id.modo == 'recibir' else linea.cantidad
