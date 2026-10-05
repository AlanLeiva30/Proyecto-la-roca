from odoo import fields, models


class LarocaPedidoRechazo(models.TransientModel):
    _name = 'laroca.pedido.rechazo'
    _description = 'Rechazar un pedido'

    pedido_id = fields.Many2one('laroca.pedido', required=True, readonly=True)
    motivo = fields.Text('Motivo', required=True, help='El encargado lo verá en su pedido.')

    def action_confirmar(self):
        self.ensure_one()
        self.pedido_id._rechazar(self.motivo)
        return {'type': 'ir.actions.act_window_close'}


class LarocaVentaAnulacion(models.TransientModel):
    _name = 'laroca.venta.anulacion'
    _description = 'Anular una venta'

    venta_id = fields.Many2one('laroca.venta', required=True, readonly=True)
    motivo = fields.Char('Motivo', required=True)

    def action_confirmar(self):
        self.ensure_one()
        self.venta_id._anular(self.motivo)
        return {'type': 'ir.actions.act_window_close'}
