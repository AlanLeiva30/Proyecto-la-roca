from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class LarocaActualizarStock(models.TransientModel):
    """Asistente para que el encargado registre la nueva existencia de un producto.

    No modifica el stock "a mano": crea un ajuste de inventario nativo de Odoo
    (stock.move), por lo que cada cambio queda en el historial de movimientos.
    """
    _name = 'laroca.actualizar.stock'
    _description = 'Actualizar existencias de una gasolinera'

    linea_id = fields.Many2one('laroca.inventario', string='Línea de inventario', required=True, ondelete='cascade')
    gasolinera_id = fields.Many2one(related='linea_id.gasolinera_id')
    product_id = fields.Many2one(related='linea_id.product_id')
    stock_actual = fields.Float(related='linea_id.stock_actual')
    cantidad_nueva = fields.Float('Nueva existencia', digits='Product Unit of Measure', required=True)
    diferencia = fields.Float('Diferencia', digits='Product Unit of Measure', compute='_compute_diferencia')
    motivo = fields.Selection([
        ('conteo', 'Conteo físico'),
        ('venta', 'Ventas / salidas'),
        ('recepcion', 'Recepción de producto'),
        ('danio', 'Producto dañado o perdido'),
        ('otro', 'Otro'),
    ], string='Motivo', required=True, default='conteo')
    nota = fields.Char('Nota')

    @api.depends('cantidad_nueva', 'stock_actual')
    def _compute_diferencia(self):
        for wizard in self:
            wizard.diferencia = wizard.cantidad_nueva - wizard.stock_actual

    @api.constrains('cantidad_nueva')
    def _check_cantidad_nueva(self):
        for wizard in self:
            if wizard.cantidad_nueva < 0:
                raise ValidationError(_('La existencia no puede ser negativa.'))

    def action_confirmar(self):
        self.ensure_one()
        linea = self.linea_id
        gasolinera, producto = linea.gasolinera_id, linea.product_id
        motivo = dict(self._fields['motivo'].selection)[self.motivo]
        referencia = f'{gasolinera.code}: {motivo}' + (f' - {self.nota}' if self.nota else '')
        self.env['laroca.inventario']._ajustar_existencias({linea: self.cantidad_nueva}, referencia)
        cerrar = {'type': 'ir.actions.act_window_close'}
        estado = linea.sudo().estado
        if estado not in ('bajo', 'critico'):
            return cerrar
        # Aviso al encargado: el producto quedó pendiente y el administrador ya fue notificado.
        etiqueta = dict(linea._fields['estado'].selection)[estado]
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Stock %s', etiqueta.lower()),
                'message': _('%(producto)s quedó por debajo del mínimo (%(minimo)s). '
                             'Se generó una alerta de abastecimiento para el administrador.',
                             producto=producto.display_name, minimo=f'{linea.stock_minimo:g}'),
                'type': 'danger' if estado == 'critico' else 'warning',
                'sticky': False,
                'next': cerrar,
            },
        }
