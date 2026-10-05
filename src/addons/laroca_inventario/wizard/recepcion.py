from odoo import api, fields, models


class LarocaRecepcion(models.TransientModel):
    """Asistente para que el encargado (o el administrador) confirme lo que llegó."""
    _name = 'laroca.recepcion'
    _description = 'Confirmar recepción de una entrega'

    entrega_id = fields.Many2one('laroca.entrega', required=True, ondelete='cascade')
    gasolinera_id = fields.Many2one(related='entrega_id.gasolinera_id')
    linea_ids = fields.One2many('laroca.recepcion.linea', 'recepcion_id', string='Productos')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        entrega = self.env['laroca.entrega'].browse(res.get('entrega_id'))
        if entrega:
            res['linea_ids'] = [(0, 0, {
                'entrega_linea_id': linea.id,
                'product_id': linea.product_id.id,
                'cantidad_enviada': linea.cantidad,
                'cantidad_recibida': linea.cantidad,
            }) for linea in entrega.linea_ids if linea.cantidad > 0]
        return res

    def action_confirmar(self):
        self.ensure_one()
        cantidades = {l.entrega_linea_id.id: l.cantidad_recibida for l in self.linea_ids}
        self.entrega_id._registrar_recepcion(cantidades)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Recepción registrada',
                'message': f'{self.entrega_id.name}: el inventario de {self.gasolinera_id.name} se actualizó.',
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


class LarocaRecepcionLinea(models.TransientModel):
    _name = 'laroca.recepcion.linea'
    _description = 'Producto recibido'

    recepcion_id = fields.Many2one('laroca.recepcion', required=True, ondelete='cascade')
    entrega_linea_id = fields.Many2one('laroca.entrega.linea', required=True)
    product_id = fields.Many2one('product.product', 'Producto', readonly=True)
    cantidad_enviada = fields.Float('Enviada', digits='Product Unit of Measure', readonly=True)
    cantidad_recibida = fields.Float('Recibida', digits='Product Unit of Measure')
