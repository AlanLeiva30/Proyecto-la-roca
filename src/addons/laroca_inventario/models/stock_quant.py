from odoo import api, models


class StockQuant(models.Model):
    """stock.quant guarda las existencias reales por ubicación (tabla nativa de Odoo).
    Cada vez que cambia una cantidad, actualizamos el "stock actual" de las
    líneas de inventario por gasolinera afectadas."""
    _inherit = 'stock.quant'

    def _laroca_refrescar_inventario(self):
        quants = self.sudo().filtered(lambda q: q.location_id.usage == 'internal' and q.location_id.warehouse_id)
        if quants:
            self.env['laroca.inventario']._refrescar_por_producto_gasolinera(
                quants.product_id, quants.location_id.warehouse_id)

    @api.model_create_multi
    def create(self, vals_list):
        quants = super().create(vals_list)
        quants._laroca_refrescar_inventario()
        return quants

    def write(self, vals):
        if 'location_id' in vals or 'product_id' in vals:
            self._laroca_refrescar_inventario()  # estado anterior
        res = super().write(vals)
        if {'quantity', 'location_id', 'product_id'} & set(vals):
            self._laroca_refrescar_inventario()
        return res

    def unlink(self):
        sudo_self = self.sudo()
        productos, gasolineras = sudo_self.product_id, sudo_self.location_id.warehouse_id
        res = super().unlink()
        if gasolineras:
            self.env['laroca.inventario']._refrescar_por_producto_gasolinera(productos, gasolineras)
        return res
