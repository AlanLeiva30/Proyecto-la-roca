from odoo import api, fields, models


class StockWarehouse(models.Model):
    """Cada gasolinera es un almacén (stock.warehouse) nativo de Odoo.
    Así reutilizamos sus ubicaciones, movimientos y transferencias."""
    _inherit = 'stock.warehouse'

    laroca_es_gasolinera = fields.Boolean(
        'Es gasolinera', default=False, index=True,
        help='Marcar si el almacén es una gasolinera (sucursal). '
             'La bodega central no es gasolinera.')
    laroca_direccion = fields.Char('Dirección')
    laroca_municipio = fields.Char('Municipio')
    laroca_departamento = fields.Char('Departamento')
    laroca_telefono = fields.Char('Teléfono')
    laroca_notas = fields.Text('Notas')
    laroca_encargado_ids = fields.Many2many(
        'res.users', 'laroca_gasolinera_encargado_rel', 'warehouse_id', 'user_id',
        string='Encargados', domain=[('share', '=', False)],
        help='Usuarios que pueden ver y actualizar el inventario de esta gasolinera.')
    laroca_inventario_ids = fields.One2many('laroca.inventario', 'gasolinera_id', string='Inventario')
    laroca_producto_count = fields.Integer('Productos', compute='_compute_laroca_conteos')
    laroca_critico_count = fields.Integer('Críticos', compute='_compute_laroca_conteos')
    laroca_bajo_count = fields.Integer('Bajos', compute='_compute_laroca_conteos')
    laroca_pendiente_count = fields.Integer('Pendientes de abastecer', compute='_compute_laroca_conteos')
    laroca_ultimo_conteo = fields.Datetime('Última actualización', compute='_compute_laroca_conteos',
                                           help='Última vez que cambió o se contó algún producto de esta gasolinera.')
    laroca_currency_id = fields.Many2one(related='company_id.currency_id')
    laroca_valor_stock = fields.Monetary('Valor del inventario', currency_field='laroca_currency_id',
                                         compute='_compute_laroca_valor')

    def _compute_laroca_valor(self):
        grupos = self.env['laroca.inventario']._read_group(
            [('gasolinera_id', 'in', self.ids)], ['gasolinera_id'], ['valor_stock:sum'])
        valores = {gasolinera.id: total for gasolinera, total in grupos}
        for warehouse in self:
            warehouse.laroca_valor_stock = valores.get(warehouse.id, 0.0)

    def _compute_laroca_conteos(self):
        grupos = self.env['laroca.inventario']._read_group(
            [('gasolinera_id', 'in', self.ids)], ['gasolinera_id', 'estado'], ['__count'])
        conteo = {}
        for gasolinera, estado, total in grupos:
            conteo.setdefault(gasolinera.id, {})[estado] = total
        ultimos = {gasolinera.id: fecha for gasolinera, fecha in self.env['laroca.inventario']._read_group(
            [('gasolinera_id', 'in', self.ids)], ['gasolinera_id'], ['ultima_actualizacion:max'])}
        for warehouse in self:
            warehouse.laroca_ultimo_conteo = ultimos.get(warehouse.id)
            datos = conteo.get(warehouse.id, {})
            warehouse.laroca_producto_count = sum(datos.values())
            warehouse.laroca_critico_count = datos.get('critico', 0)
            warehouse.laroca_bajo_count = datos.get('bajo', 0)
            warehouse.laroca_pendiente_count = datos.get('critico', 0) + datos.get('bajo', 0)

    @api.model_create_multi
    def create(self, vals_list):
        warehouses = super().create(vals_list)
        gasolineras = warehouses.filtered('laroca_es_gasolinera')
        if gasolineras:
            self.env['laroca.inventario']._generar_lineas(gasolineras=gasolineras)
        if any('laroca_encargado_ids' in vals for vals in vals_list):
            warehouses.laroca_encargado_ids._laroca_tras_cambiar_gasolineras()
        return warehouses

    def write(self, vals):
        encargados_antes = self.laroca_encargado_ids
        res = super().write(vals)
        if vals.get('laroca_es_gasolinera'):
            self.env['laroca.inventario']._generar_lineas(gasolineras=self)
        if 'laroca_encargado_ids' in vals:
            (encargados_antes | self.laroca_encargado_ids)._laroca_tras_cambiar_gasolineras()
        return res

    def action_laroca_ver_inventario(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('laroca_inventario.action_laroca_inventario')
        action['domain'] = [('gasolinera_id', '=', self.id)]
        action['context'] = {'default_gasolinera_id': self.id, 'searchpanel_default_gasolinera_id': self.id}
        action['name'] = f'Inventario - {self.name}'
        return action

    laroca_entrega_count = fields.Integer('Entregas', compute='_compute_laroca_entrega_count')

    def _compute_laroca_entrega_count(self):
        grupos = self.env['laroca.entrega']._read_group(
            [('gasolinera_id', 'in', self.ids), ('estado', '!=', 'cancelada')], ['gasolinera_id'], ['__count'])
        conteo = {gasolinera.id: total for gasolinera, total in grupos}
        for warehouse in self:
            warehouse.laroca_entrega_count = conteo.get(warehouse.id, 0)

    def action_laroca_ver_entregas(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('laroca_inventario.action_laroca_entregas')
        action['domain'] = [('gasolinera_id', '=', self.id)]
        action['context'] = {'default_gasolinera_id': self.id}
        return action

    def action_laroca_preparar_entrega(self):
        """Crea una entrega con todo lo pendiente de esta gasolinera."""
        self.ensure_one()
        lineas = self.env['laroca.inventario'].search(
            [('gasolinera_id', '=', self.id), ('estado', 'in', ('bajo', 'critico'))])
        return lineas.action_crear_entregas()

    def action_laroca_ver_pendientes(self):
        action = self.action_laroca_ver_inventario()
        action['domain'] = action['domain'] + [('estado', 'in', ('bajo', 'critico'))]
        action['name'] = f'Pendientes - {self.name}'
        return action
