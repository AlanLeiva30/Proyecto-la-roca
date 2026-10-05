from odoo import api, fields, models


class LarocaPanelBodega(models.TransientModel):
    """Panel de la Bodega Central: cuánto hay, qué conviene comprar y accesos para agregar
    productos (recibir mercadería, producto nuevo, contar, importar). Los encargados lo ven;
    los botones para modificar son solo del administrador."""
    _name = 'laroca.panel.bodega'
    _description = 'Panel de la bodega central'

    nombre_bodega = fields.Char(compute='_compute_panel')
    currency_id = fields.Many2one('res.currency', compute='_compute_panel')
    kpi_productos = fields.Integer('Productos con stock', compute='_compute_panel')
    kpi_unidades = fields.Integer('Unidades en bodega', compute='_compute_panel')
    kpi_reservado = fields.Integer('Reservado para entregas', compute='_compute_panel')
    kpi_valor = fields.Monetary('Valor de la bodega', compute='_compute_panel')
    kpi_sin_stock = fields.Integer('Productos sin stock', compute='_compute_panel')
    kpi_comprar = fields.Integer('Productos que conviene comprar', compute='_compute_panel')
    comprar_ids = fields.Many2many('product.template', string='Conviene comprar', compute='_compute_panel')
    recepcion_ids = fields.Many2many('stock.picking', string='Últimas recepciones', compute='_compute_panel')

    @api.depends_context('uid')
    def _compute_display_name(self):
        for panel in self:
            panel.display_name = 'Bodega central'

    @api.depends_context('uid')
    def _compute_panel(self):
        bodega = self.env.company._laroca_bodega_central()
        productos = self.env['product.template'].search([('is_storable', '=', True)])
        comprar = productos.filtered(lambda p: p.laroca_faltante_bodega > 0).sorted(
            key=lambda p: -p.laroca_faltante_bodega)
        recepciones = self.env['stock.picking'].sudo().search([
            ('picking_type_id', '=', bodega.in_type_id.id), ('state', '=', 'done')],
            order='date_done desc', limit=6) if bodega else self.env['stock.picking']
        valores = {
            'nombre_bodega': bodega.name or 'Bodega central',
            'currency_id': self.env.company.currency_id,
            'kpi_productos': len(productos.filtered(lambda p: p.laroca_stock_bodega > 0)),
            'kpi_unidades': round(sum(productos.mapped('laroca_stock_bodega'))),
            'kpi_reservado': round(sum(productos.mapped('laroca_reservado_bodega'))),
            'kpi_valor': sum(productos.mapped('laroca_valor_bodega')),
            'kpi_sin_stock': len(productos.filtered(lambda p: p.laroca_disponible_bodega <= 0)),
            'kpi_comprar': len(comprar),
            'comprar_ids': comprar,
            'recepcion_ids': recepciones,
        }
        for panel in self:
            panel.update(valores)

    @api.model
    def action_abrir_panel(self):
        panel = self.create({})
        panel.invalidate_recordset()  # que las listas se calculen al leerlas (ver laroca.panel)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bodega central',
            'res_model': self._name,
            'res_id': panel.id,
            'view_mode': 'form',
            'views': [(self.env.ref('laroca_inventario.view_laroca_panel_bodega_form').id, 'form')],
            'target': 'current',
        }

    def action_refrescar(self):
        return True

    def _accion(self, xmlid, context=None, domain=None):
        accion = self.env['ir.actions.actions']._for_xml_id(xmlid)
        if context is not None:
            accion['context'] = context
        if domain is not None:
            accion['domain'] = domain
        return accion

    def action_recibir(self):
        return self._accion('laroca_inventario.action_laroca_bodega_recibir')

    def action_contar(self):
        return self._accion('laroca_inventario.action_laroca_bodega_recibir',
                            context={'dialog_size': 'extra-large', 'default_modo': 'contar'})

    def action_producto_nuevo(self):
        return self._accion('laroca_inventario.action_laroca_producto_nuevo')

    def action_importar(self):
        return self._accion('laroca_inventario.action_laroca_importar')

    def action_ver_productos(self):
        return self._accion('laroca_inventario.action_laroca_bodega')

    def action_ver_sin_stock(self):
        ids = self.env['product.template'].search([('is_storable', '=', True)]).filtered(
            lambda p: p.laroca_disponible_bodega <= 0).ids
        return self._accion('laroca_inventario.action_laroca_bodega', domain=[('id', 'in', ids)])

    def action_ver_comprar(self):
        return self._accion('laroca_inventario.action_laroca_bodega', domain=[('id', 'in', self.comprar_ids.ids)])

    def action_comprar_recibir(self):
        """Recibir mercadería con solo los productos que conviene comprar."""
        accion = self._accion('laroca_inventario.action_laroca_bodega_recibir')
        accion['context'] = {'dialog_size': 'extra-large',
                             'laroca_productos': self.comprar_ids.product_variant_ids.ids}
        return accion
