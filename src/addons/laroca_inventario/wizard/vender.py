from odoo import _, api, fields, models

from ..utils import accion_alerta


class LarocaVender(models.TransientModel):
    """Pantalla "Vender": el encargado escribe cuántas unidades vendió de cada producto
    y el sistema registra la venta (laroca.venta) y descuenta el stock."""
    _name = 'laroca.vender'
    _description = 'Registrar una venta'

    gasolinera_id = fields.Many2one(
        'stock.warehouse', 'Gasolinera', required=True,
        domain=[('laroca_es_gasolinera', '=', True)],
        default=lambda self: self.env['stock.warehouse'].search(
            [('laroca_es_gasolinera', '=', True)], limit=1, order='name'))
    buscar = fields.Char('Buscar producto')
    categ_id = fields.Many2one('product.category', 'Categoría', help='Vacío = todas.')
    linea_ids = fields.One2many('laroca.vender.linea', 'vender_id', string='Productos')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    total_unidades = fields.Float('Unidades', digits='Product Unit of Measure', compute='_compute_total')
    total = fields.Monetary('Total a cobrar', compute='_compute_total')

    @api.depends('linea_ids.cantidad', 'linea_ids.subtotal')
    def _compute_total(self):
        for wizard in self:
            wizard.total_unidades = sum(wizard.linea_ids.mapped('cantidad'))
            wizard.total = sum(wizard.linea_ids.mapped('subtotal'))

    @api.onchange('gasolinera_id', 'categ_id', 'buscar')
    def _onchange_cargar_productos(self):
        # Se conservan las cantidades ya escritas de los productos que siguen en la lista.
        anteriores = {l.inventario_id.id: l.cantidad for l in self.linea_ids if l.cantidad}
        comandos = [(5, 0, 0)]
        if self.gasolinera_id:
            dominio = [('gasolinera_id', '=', self.gasolinera_id.id), ('stock_actual', '>', 0)]
            if self.categ_id:
                dominio.append(('categ_id', 'child_of', self.categ_id.id))
            if self.buscar:
                dominio.append(('product_id', 'ilike', self.buscar))
            lineas = self.env['laroca.inventario'].search(dominio, order='categ_id, default_code, id')
            if self.gasolinera_id == self._origin.gasolinera_id or not self._origin:
                # Lo que ya se escribió sigue en la venta aunque no coincida con la búsqueda.
                lineas |= self.env['laroca.inventario'].browse(list(anteriores)).filtered(
                    lambda l: l.gasolinera_id == self.gasolinera_id)
            for linea in lineas:
                comandos.append((0, 0, {
                    'inventario_id': linea.id,
                    'disponible': linea.stock_actual,
                    'cantidad': anteriores.get(linea.id, 0),
                }))
        self.linea_ids = comandos

    def action_vender(self):
        self.ensure_one()
        cantidades = {}
        for linea in self.linea_ids.filtered(lambda l: l.cantidad > 0):
            cantidades[linea.product_id] = cantidades.get(linea.product_id, 0) + linea.cantidad
        if not cantidades:
            return accion_alerta('warning', _('¿Qué vendiste?'),
                                 _('Escribí cuántas unidades vendiste de al menos un producto.'))
        Venta = self.env['laroca.venta']
        faltantes = Venta._faltantes(self.gasolinera_id, cantidades)
        if faltantes:
            # El asistente queda abierto para corregir la cantidad.
            return accion_alerta('error', _('Stock insuficiente'),
                                 _('No hay suficientes unidades para completar la venta. Corregí la cantidad:'),
                                 faltantes)
        venta = Venta._registrar(self.gasolinera_id, cantidades)
        bajos = self.env['laroca.inventario'].sudo().search([
            ('gasolinera_id', '=', self.gasolinera_id.id), ('product_id', 'in', [p.id for p in cantidades]),
            ('estado', 'in', ('bajo', 'critico'))])
        texto = _('%(venta)s · %(unidades)s unidades · Total %(total)s', venta=venta.name,
                  unidades=f'{venta.total_unidades:g}', total=f'{venta.currency_id.symbol} {venta.total:,.2f}')
        detalle = [_('Se está acabando: %s. Podés pedirlo con "Pedir productos".', nombre)
                   for nombre in bajos.product_id.mapped('name')]
        return accion_alerta('success', _('¡Venta registrada!'), texto, detalle, cerrar=True)


class LarocaVenderLinea(models.TransientModel):
    _name = 'laroca.vender.linea'
    _description = 'Producto en la pantalla de venta'

    vender_id = fields.Many2one('laroca.vender', 'Pantalla de venta', required=True, ondelete='cascade')
    inventario_id = fields.Many2one('laroca.inventario', required=True)
    product_id = fields.Many2one(related='inventario_id.product_id', string='Producto')
    default_code = fields.Char(related='inventario_id.default_code', string='Código')
    image_128 = fields.Image(related='inventario_id.image_128')
    currency_id = fields.Many2one(related='vender_id.currency_id')
    precio = fields.Float(related='product_id.lst_price', string='Precio')
    disponible = fields.Float('Hay', digits='Product Unit of Measure', readonly=True)
    cantidad = fields.Float('Vender', digits='Product Unit of Measure')
    quedan = fields.Float('Quedan', digits='Product Unit of Measure', compute='_compute_quedan',
                          help='Lo que queda en la gasolinera después de esta venta (se actualiza al escribir).')
    aviso = fields.Char('Aviso', compute='_compute_quedan')
    subtotal = fields.Monetary('Subtotal', compute='_compute_subtotal')

    @api.depends('cantidad', 'precio')
    def _compute_subtotal(self):
        for linea in self:
            linea.subtotal = linea.cantidad * linea.precio

    @api.depends('cantidad', 'disponible')
    def _compute_quedan(self):
        for linea in self:
            linea.quedan = linea.disponible - linea.cantidad
            if linea.quedan < 0:
                linea.aviso = _('No alcanza: solo hay %s', f'{linea.disponible:g}')
            elif linea.cantidad and not linea.quedan:
                linea.aviso = _('¡Ya no hay más!')
            else:
                linea.aviso = False
