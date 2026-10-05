from odoo import _, fields, models
from odoo.exceptions import UserError

from ..utils import accion_alerta


class LarocaProductoNuevo(models.TransientModel):
    """Agregar un producto nuevo al catálogo y cargarle las unidades que llegaron a la bodega
    central, todo en un paso (administrador)."""
    _name = 'laroca.producto.nuevo'
    _description = 'Agregar un producto nuevo a la bodega'

    name = fields.Char('Nombre', required=True)
    default_code = fields.Char('Código', help='Por ejemplo: LLA-003')
    categ_id = fields.Many2one('product.category', 'Categoría', required=True,
                               help='Accesorios, Juguetes, Lubricantes…')
    image_1920 = fields.Image('Foto', max_width=1920, max_height=1920)
    description_sale = fields.Text('Descripción')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    list_price = fields.Monetary('Precio de venta')
    standard_price = fields.Monetary('Costo')
    laroca_stock_minimo = fields.Float('Mínimo por gasolinera', digits='Product Unit of Measure')
    laroca_stock_objetivo = fields.Float('Objetivo por gasolinera', digits='Product Unit of Measure')
    cantidad = fields.Float('Unidades que llegaron', digits='Product Unit of Measure',
                            help='Se suman a la bodega central. Puede ser 0 si todavía no llegó.')
    proveedor = fields.Char('Proveedor')
    referencia = fields.Char('Factura / referencia')

    def action_crear(self):
        self.ensure_one()
        self.env['laroca.entrega']._check_admin()
        if self.default_code and self.env['product.template'].search_count([('default_code', '=', self.default_code)]):
            return accion_alerta('warning', _('Ese código ya existe'),
                                 _('Ya hay un producto con el código %s. Usá otro código o, si es el mismo '
                                   'producto, cargá las unidades con "Recibir mercadería".', self.default_code))
        if self.cantidad < 0:
            raise UserError(_('La cantidad no puede ser negativa.'))
        plantilla = self.env['product.template'].create({
            'name': self.name,
            'default_code': self.default_code,
            'categ_id': self.categ_id.id,
            'image_1920': self.image_1920,
            'description_sale': self.description_sale,
            'list_price': self.list_price,
            'standard_price': self.standard_price,
            'type': 'consu',
            'is_storable': True,
            'laroca_stock_minimo': self.laroca_stock_minimo,
            'laroca_stock_objetivo': self.laroca_stock_objetivo,
        })
        texto = _('Se agregó al catálogo y a todas las gasolineras.')
        if self.cantidad > 0:
            bodega = self.env.company._laroca_bodega_central()
            if not bodega:
                raise UserError(_('No hay una bodega central configurada (La Roca → Configuración → Parámetros).'))
            self.env['laroca.bodega.movimiento']._recibir_productos(
                bodega, {plantilla.product_variant_id: self.cantidad},
                ' - '.join(filter(None, [self.proveedor, self.referencia])))
            texto = _('Se agregó al catálogo y a todas las gasolineras, con %s unidades en la bodega central.',
                      f'{self.cantidad:g}')
        return accion_alerta('success', _('¡Producto agregado!'), texto, [plantilla.display_name], cerrar=True)
