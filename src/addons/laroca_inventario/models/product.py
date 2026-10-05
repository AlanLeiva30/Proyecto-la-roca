from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    laroca_stock_minimo = fields.Float(
        'Stock mínimo por gasolinera', digits='Product Unit of Measure', default=0.0,
        help='Valor inicial del stock mínimo cuando el producto se agrega a una gasolinera.')
    laroca_stock_objetivo = fields.Float(
        'Stock objetivo por gasolinera', digits='Product Unit of Measure', default=0.0,
        help='Valor inicial del stock objetivo (hasta dónde se repone). 0 = doble del mínimo.')
    # Existencias en la Bodega Central (las ven todos; las modifica el administrador)
    laroca_stock_bodega = fields.Float('En bodega', digits='Product Unit of Measure', compute='_compute_laroca_bodega')
    laroca_reservado_bodega = fields.Float('Reservado', digits='Product Unit of Measure', compute='_compute_laroca_bodega',
                                           help='Apartado para entregas que van en camino.')
    laroca_disponible_bodega = fields.Float('Disponible', digits='Product Unit of Measure',
                                            compute='_compute_laroca_bodega',
                                            help='Lo que se puede llevar: en bodega menos lo reservado.')
    laroca_valor_bodega = fields.Monetary('Valor en bodega', compute='_compute_laroca_bodega',
                                          currency_field='currency_id')
    laroca_sugerido_gasolineras = fields.Float(
        'Necesitan las gasolineras', digits='Product Unit of Measure', compute='_compute_laroca_bodega',
        help='Suma de lo sugerido para reponer en todas las gasolineras.')
    laroca_faltante_bodega = fields.Float(
        'Conviene comprar', digits='Product Unit of Measure', compute='_compute_laroca_bodega',
        help='Lo que falta en bodega para cubrir lo que necesitan las gasolineras.')

    def _compute_laroca_bodega(self):
        # sudo: los encargados no tienen acceso a la bodega central, pero pueden ver cuánto hay
        bodega = self.env.company._laroca_bodega_central()
        datos = {}
        if bodega:
            grupos = self.env['stock.quant'].sudo()._read_group(
                [('product_id.product_tmpl_id', 'in', self.ids), ('location_id', 'child_of', bodega.lot_stock_id.id)],
                ['product_id'], ['quantity:sum', 'reserved_quantity:sum'])
            for producto, cantidad, reservado in grupos:
                anterior = datos.get(producto.product_tmpl_id.id, (0.0, 0.0))
                datos[producto.product_tmpl_id.id] = (anterior[0] + cantidad, anterior[1] + reservado)
        sugeridos = {}
        for producto, sugerido in self.env['laroca.inventario'].sudo()._read_group(
                [('product_id.product_tmpl_id', 'in', self.ids)], ['product_id'], ['cantidad_sugerida:sum']):
            sugeridos[producto.product_tmpl_id.id] = sugeridos.get(producto.product_tmpl_id.id, 0.0) + sugerido
        for template in self:
            cantidad, reservado = datos.get(template.id, (0.0, 0.0))
            template.laroca_sugerido_gasolineras = sugeridos.get(template.id, 0.0)
            template.laroca_faltante_bodega = max(sugeridos.get(template.id, 0.0) - (cantidad - reservado), 0.0)
            template.laroca_stock_bodega = cantidad
            template.laroca_reservado_bodega = reservado
            template.laroca_disponible_bodega = cantidad - reservado
            template.laroca_valor_bodega = cantidad * template.standard_price

    def write(self, vals):
        res = super().write(vals)
        # Si un producto pasa a ser "inventariable", se agrega a todas las gasolineras.
        if vals.get('is_storable'):
            self.env['laroca.inventario']._generar_lineas(productos=self.product_variant_ids)
        return res

    def action_laroca_aplicar_niveles(self):
        """Copia el mínimo y el objetivo del producto a todas las gasolineras."""
        for template in self:
            lineas = self.env['laroca.inventario'].search([('product_id', 'in', template.product_variant_ids.ids)])
            lineas.write({
                'stock_minimo': template.laroca_stock_minimo,
                'stock_objetivo': template.laroca_stock_objetivo,
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Niveles aplicados',
                'message': 'Se actualizaron el mínimo y el objetivo en todas las gasolineras.',
                'type': 'success',
            },
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        inventariables = products.filtered('is_storable')
        if inventariables:
            self.env['laroca.inventario']._generar_lineas(productos=inventariables)
        return products
