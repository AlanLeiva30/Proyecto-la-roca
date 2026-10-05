from odoo import _, api, fields, models

from ..utils import accion_alerta


class LarocaPedir(models.TransientModel):
    """Pantalla rápida "Pedir productos": el encargado escribe cuánto necesita de cada
    producto (o completa con lo sugerido) y envía el pedido con un solo botón."""
    _name = 'laroca.pedir'
    _description = 'Pedir productos al administrador'

    gasolinera_id = fields.Many2one(
        'stock.warehouse', 'Gasolinera', required=True,
        domain=[('laroca_es_gasolinera', '=', True)],
        default=lambda self: self.env['stock.warehouse'].search(
            [('laroca_es_gasolinera', '=', True)], limit=1, order='name'))
    buscar = fields.Char('Buscar producto')
    categ_id = fields.Many2one('product.category', 'Categoría', help='Vacío = todas.')
    linea_ids = fields.One2many('laroca.pedir.linea', 'pedir_id', string='Productos')
    completar_sugerido = fields.Boolean(
        'Completar con lo sugerido',
        help='Escribe al instante la cantidad sugerida en los productos bajos y críticos. '
             'Al apagarlo, esas cantidades vuelven a 0.')
    nota = fields.Char('Comentario', help='Opcional, por ejemplo: "para el fin de semana largo".')
    total_unidades = fields.Float('Unidades', digits='Product Unit of Measure', compute='_compute_total')

    @api.depends('linea_ids.cantidad')
    def _compute_total(self):
        for wizard in self:
            wizard.total_unidades = sum(wizard.linea_ids.mapped('cantidad'))

    @api.onchange('gasolinera_id', 'categ_id', 'buscar')
    def _onchange_cargar_productos(self):
        # Se conservan las cantidades ya escritas; desde "Pedir estos productos" se completa lo sugerido.
        anteriores = {l.inventario_id.id: l.cantidad for l in self.linea_ids if l.cantidad}
        sugerir = self.completar_sugerido
        comandos = [(5, 0, 0)]
        if self.gasolinera_id:
            Inventario = self.env['laroca.inventario']
            dominio = [('gasolinera_id', '=', self.gasolinera_id.id)]
            if self.categ_id:
                dominio.append(('categ_id', 'child_of', self.categ_id.id))
            if self.buscar:
                dominio.append(('product_id', 'ilike', self.buscar))
            # Lo que más falta, primero
            lineas = Inventario.search(dominio, order='prioridad, categ_id, default_code, id')
            lineas |= Inventario.browse(list(anteriores)).filtered(lambda l: l.gasolinera_id == self.gasolinera_id)
            for linea in lineas:
                cantidad = anteriores.get(linea.id, 0)
                if sugerir and not cantidad and linea.estado in ('bajo', 'critico'):
                    cantidad = linea.cantidad_sugerida
                comandos.append((0, 0, {'inventario_id': linea.id, 'cantidad': cantidad}))
        self.linea_ids = comandos

    @api.onchange('completar_sugerido')
    def _onchange_completar_sugerido(self):
        for linea in self.linea_ids.filtered(lambda l: l.estado in ('bajo', 'critico') and l.cantidad_sugerida > 0):
            if self.completar_sugerido and not linea.cantidad:
                linea.cantidad = linea.cantidad_sugerida
            elif not self.completar_sugerido and linea.cantidad == linea.cantidad_sugerida:
                linea.cantidad = 0

    def _reabrir(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pedir productos'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'dialog_size': 'extra-large'},
        }

    def action_completar_sugerido(self):
        """Escribe la cantidad sugerida en los productos bajos y críticos."""
        self.ensure_one()
        pendientes = self.linea_ids.filtered(lambda l: l.estado in ('bajo', 'critico') and l.cantidad_sugerida > 0)
        if not pendientes:
            return accion_alerta('info', _('Todo bien'),
                                 _('No hay productos por acabarse. Escribí a mano cuánto necesitás.'))
        for linea in pendientes:
            linea.cantidad = linea.cantidad_sugerida
        return self._reabrir()

    def action_enviar(self):
        self.ensure_one()
        lineas = self.linea_ids.filtered(lambda l: l.cantidad > 0)
        if not lineas:
            return accion_alerta('warning', _('¿Qué necesitás?'),
                                 _('Escribí cuántas unidades necesitás de al menos un producto, '
                                   'o tocá "Completar con lo sugerido".'))
        cantidades = {}
        for linea in lineas:
            cantidades[linea.product_id] = cantidades.get(linea.product_id, 0) + linea.cantidad
        pedido = self.env['laroca.pedido'].create({
            'gasolinera_id': self.gasolinera_id.id,
            'nota': self.nota,
            'linea_ids': [(0, 0, {'product_id': p.id, 'cantidad': c}) for p, c in cantidades.items()],
        })
        pedido.action_enviar()
        return pedido._alerta_realizado(cerrar=True)


class LarocaPedirLinea(models.TransientModel):
    _name = 'laroca.pedir.linea'
    _description = 'Producto en la pantalla de pedido'

    pedir_id = fields.Many2one('laroca.pedir', 'Pantalla de pedido', required=True, ondelete='cascade')
    inventario_id = fields.Many2one('laroca.inventario', required=True)
    product_id = fields.Many2one(related='inventario_id.product_id', string='Producto')
    image_128 = fields.Image(related='inventario_id.image_128')
    estado = fields.Selection(related='inventario_id.estado')
    stock_actual = fields.Float(related='inventario_id.stock_actual', string='Tengo')
    stock_minimo = fields.Float(related='inventario_id.stock_minimo', string='Mínimo')
    cantidad_sugerida = fields.Float(related='inventario_id.cantidad_sugerida', string='Sugerido')
    disponible_bodega = fields.Float(related='inventario_id.disponible_bodega', string='En bodega')
    cantidad = fields.Float('Pido', digits='Product Unit of Measure')
