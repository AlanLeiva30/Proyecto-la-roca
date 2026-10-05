from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LarocaConteo(models.TransientModel):
    """Conteo rápido: el encargado registra todas las existencias de su gasolinera
    en una sola pantalla. Se guarda como un único ajuste de inventario de Odoo."""
    _name = 'laroca.conteo'
    _description = 'Conteo rápido de inventario'

    gasolinera_id = fields.Many2one(
        'stock.warehouse', 'Gasolinera', required=True,
        domain=[('laroca_es_gasolinera', '=', True)],
        default=lambda self: self._gasolinera_por_defecto())
    categ_id = fields.Many2one('product.category', 'Solo la categoría', help='Vacío = todos los productos.')
    solo_pendientes = fields.Boolean('Solo bajos y críticos')
    motivo = fields.Selection([
        ('conteo', 'Conteo físico'),
        ('venta', 'Ventas / salidas del día'),
        ('recepcion', 'Recepción de producto'),
        ('otro', 'Otro'),
    ], 'Motivo', required=True, default='conteo')
    linea_ids = fields.One2many('laroca.conteo.linea', 'conteo_id', string='Productos')
    total_cambios = fields.Integer('Productos con cambios', compute='_compute_total_cambios')

    @api.model
    def _gasolinera_por_defecto(self):
        gasolinera_id = self.env.context.get('default_gasolinera_id')
        if gasolinera_id:
            return gasolinera_id
        return self.env['stock.warehouse'].search([('laroca_es_gasolinera', '=', True)], limit=1, order='name')

    @api.depends('linea_ids.diferencia')
    def _compute_total_cambios(self):
        for conteo in self:
            conteo.total_cambios = len(conteo.linea_ids.filtered('diferencia'))

    @api.onchange('gasolinera_id', 'categ_id', 'solo_pendientes')
    def _onchange_cargar_productos(self):
        comandos = [(5, 0, 0)]
        if self.gasolinera_id:
            dominio = [('gasolinera_id', '=', self.gasolinera_id.id)]
            if self.categ_id:
                dominio.append(('categ_id', 'child_of', self.categ_id.id))
            if self.solo_pendientes:
                dominio.append(('estado', 'in', ('bajo', 'critico')))
            for linea in self.env['laroca.inventario'].search(dominio, order='categ_id, default_code, id'):
                comandos.append((0, 0, {
                    'inventario_id': linea.id,
                    'stock_sistema': linea.stock_actual,
                    'cantidad_contada': linea.stock_actual,
                }))
        self.linea_ids = comandos

    def action_guardar(self):
        self.ensure_one()
        if not self.linea_ids:
            raise UserError(_('No hay productos para guardar.'))
        motivo = dict(self._fields['motivo'].selection)[self.motivo]
        cantidades = {l.inventario_id: l.cantidad_contada for l in self.linea_ids}
        cambiadas = self.env['laroca.inventario']._ajustar_existencias(
            cantidades, f'{self.gasolinera_id.code}: Conteo rápido ({motivo})')
        lineas = self.linea_ids.inventario_id.sudo()
        pendientes = lineas.filtered(lambda l: l.estado in ('bajo', 'critico'))
        mensaje = _('%(total)s productos revisados, %(cambios)s con cambios.',
                    total=len(lineas), cambios=len(cambiadas))
        if pendientes:
            mensaje += ' ' + _('%s quedaron bajo el mínimo: el administrador tiene las alertas.', len(pendientes))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Conteo guardado - %s', self.gasolinera_id.name),
                'message': mensaje,
                'type': 'warning' if pendientes else 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


class LarocaConteoLinea(models.TransientModel):
    _name = 'laroca.conteo.linea'
    _description = 'Producto del conteo rápido'

    conteo_id = fields.Many2one('laroca.conteo', required=True, ondelete='cascade')
    inventario_id = fields.Many2one('laroca.inventario', required=True)
    product_id = fields.Many2one(related='inventario_id.product_id', string='Producto')
    default_code = fields.Char(related='inventario_id.default_code', string='Código')
    stock_minimo = fields.Float(related='inventario_id.stock_minimo', string='Mínimo')
    stock_sistema = fields.Float('En sistema', digits='Product Unit of Measure', readonly=True)
    cantidad_contada = fields.Float('Contado', digits='Product Unit of Measure')
    diferencia = fields.Float('Diferencia', digits='Product Unit of Measure', compute='_compute_diferencia')

    @api.depends('cantidad_contada', 'stock_sistema')
    def _compute_diferencia(self):
        for linea in self:
            linea.diferencia = linea.cantidad_contada - linea.stock_sistema
