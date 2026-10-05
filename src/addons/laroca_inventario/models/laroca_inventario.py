from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

ESTADOS = [
    ('critico', 'Crítico'),
    ('bajo', 'Bajo'),
    ('suficiente', 'Suficiente'),
    ('sin_minimo', 'Sin mínimo'),
]
# Orden para mostrar primero lo más urgente
PRIORIDAD = {'critico': 1, 'bajo': 2, 'suficiente': 3, 'sin_minimo': 4}


class LarocaInventario(models.Model):
    """Una línea por cada combinación (gasolinera, producto).

    El stock real vive en stock.quant (nativo de Odoo). Este modelo es la "vista de
    trabajo" de cada sucursal: muestra el stock actual de cada producto del catálogo,
    incluso cuando está en cero, y es la base para el stock mínimo, los estados
    (suficiente / bajo / crítico) y las sugerencias de abastecimiento de las
    siguientes etapas.
    """
    _name = 'laroca.inventario'
    _description = 'Inventario por gasolinera'
    _order = 'gasolinera_id, categ_id, product_id'
    _rec_names_search = ['product_id', 'default_code', 'gasolinera_id']

    gasolinera_id = fields.Many2one(
        'stock.warehouse', string='Gasolinera', required=True, index=True, ondelete='cascade',
        domain=[('laroca_es_gasolinera', '=', True)])
    product_id = fields.Many2one(
        'product.product', string='Producto', required=True, index=True, ondelete='cascade',
        domain=[('is_storable', '=', True)])
    company_id = fields.Many2one(related='gasolinera_id.company_id', store=True)
    active = fields.Boolean(
        compute='_compute_active', store=True,
        help='La línea se oculta si el producto o la gasolinera están archivados.')
    default_code = fields.Char(related='product_id.default_code', string='Código', store=True)
    categ_id = fields.Many2one(related='product_id.categ_id', string='Categoría', store=True)
    image_128 = fields.Image(related='product_id.image_128')
    image_512 = fields.Image(related='product_id.image_512')
    descripcion = fields.Text(related='product_id.description_sale', string='Descripción')
    uom_id = fields.Many2one(related='product_id.uom_id', string='Unidad')

    stock_actual = fields.Float(
        'Stock actual', digits='Product Unit of Measure', readonly=True, default=0.0,
        help='Existencias en la ubicación de stock de la gasolinera. '
             'Se calcula a partir de los movimientos de inventario de Odoo.')
    # --- Etapa 2: niveles, estado y sugerencia ---------------------------
    stock_minimo = fields.Float(
        'Stock mínimo', digits='Product Unit of Measure', default=0.0,
        help='Por debajo de este nivel el producto queda pendiente de abastecimiento.')
    stock_objetivo = fields.Float(
        'Stock objetivo', digits='Product Unit of Measure', default=0.0,
        help='Cantidad hasta la que se repone al abastecer. Si es 0 se usa el doble del mínimo.')
    estado = fields.Selection(
        ESTADOS, 'Estado', compute='_compute_estado', store=True, index=True,
        help='Suficiente: stock ≥ mínimo. Bajo: por debajo del mínimo. '
             'Crítico: igual o menor al umbral crítico (% del mínimo, ver Parámetros).')
    prioridad = fields.Integer('Prioridad', compute='_compute_estado', store=True)
    cantidad_sugerida = fields.Float(
        'Cantidad sugerida', digits='Product Unit of Measure', compute='_compute_estado', store=True,
        help='Cantidad a llevar para llegar al stock objetivo (solo si está bajo o crítico).')
    disponible_bodega = fields.Float(
        'Disponible en bodega', digits='Product Unit of Measure', compute='_compute_disponible_bodega',
        help='Lo que se puede llevar de la bodega central: existencias menos lo reservado para entregas en camino.')
    cantidad_en_entrega = fields.Float(
        'En entrega', digits='Product Unit of Measure', compute='_compute_cantidad_en_entrega',
        help='Cantidad incluida en entregas en borrador o en camino hacia esta gasolinera.')
    alerta_ids = fields.One2many('laroca.alerta', 'linea_id', string='Alertas')
    alerta_abierta_count = fields.Integer('Alertas abiertas', compute='_compute_alerta_abierta_count')

    # --- Valor del inventario ----------------------------------------------
    currency_id = fields.Many2one(related='company_id.currency_id')
    costo_unitario = fields.Float(related='product_id.standard_price', string='Costo unitario')
    valor_stock = fields.Monetary(
        'Valor (costo)', compute='_compute_valor', store=True,
        help='Stock actual × costo del producto.')
    valor_venta = fields.Monetary(
        'Valor (precio de venta)', compute='_compute_valor', store=True,
        help='Stock actual × precio de venta del producto.')

    ultima_actualizacion = fields.Datetime('Última actualización', readonly=True)
    ultima_actualizacion_por = fields.Many2one('res.users', 'Actualizado por', readonly=True)
    movimiento_ids = fields.Many2many(
        'stock.move.line', string='Movimientos recientes', compute='_compute_movimiento_ids')

    _sql_constraints = [
        ('gasolinera_producto_uniq', 'unique(gasolinera_id, product_id)',
         'Este producto ya está registrado en esa gasolinera.'),
    ]

    @api.depends('product_id.active', 'gasolinera_id.active')
    def _compute_active(self):
        for linea in self:
            linea.active = linea.product_id.active and linea.gasolinera_id.active

    @api.constrains('stock_minimo', 'stock_objetivo')
    def _check_niveles(self):
        for linea in self:
            if linea.stock_minimo < 0 or linea.stock_objetivo < 0:
                raise ValidationError(_('Los niveles de stock no pueden ser negativos.'))
            if linea.stock_objetivo and linea.stock_objetivo < linea.stock_minimo:
                raise ValidationError(_(
                    '%(producto)s en %(gasolinera)s: el stock objetivo no puede ser menor que el mínimo.',
                    producto=linea.product_id.display_name, gasolinera=linea.gasolinera_id.name))

    @api.depends('stock_actual', 'stock_minimo', 'stock_objetivo', 'company_id.laroca_porcentaje_critico')
    def _compute_estado(self):
        for linea in self:
            linea.estado = linea._calcular_estado()
            linea.prioridad = PRIORIDAD[linea.estado]
            if linea.estado in ('bajo', 'critico'):
                objetivo = linea.stock_objetivo or linea.stock_minimo * 2
                linea.cantidad_sugerida = max(objetivo - linea.stock_actual, 0.0)
            else:
                linea.cantidad_sugerida = 0.0

    @api.depends('stock_actual', 'product_id.standard_price', 'product_id.list_price')
    def _compute_valor(self):
        for linea in self:
            producto = linea.product_id.with_company(linea.company_id or self.env.company)
            linea.valor_stock = linea.stock_actual * producto.standard_price
            linea.valor_venta = linea.stock_actual * producto.list_price

    def _calcular_estado(self):
        """Regla de negocio (documento, sección 5):
        - sin mínimo definido            → sin_minimo
        - stock ≥ mínimo                 → suficiente
        - stock ≤ mínimo × umbral (%)     → crítico
        - en otro caso (debajo del mínimo) → bajo
        """
        self.ensure_one()
        if self.stock_minimo <= 0:
            return 'sin_minimo'
        if self.stock_actual >= self.stock_minimo:
            return 'suficiente'
        porcentaje = (self.company_id or self.env.company).laroca_porcentaje_critico or 50
        if self.stock_actual <= self.stock_minimo * porcentaje / 100.0:
            return 'critico'
        return 'bajo'

    def _compute_disponible_bodega(self):
        Quant = self.env['stock.quant'].sudo()
        for company in self.company_id:
            lineas = self.filtered(lambda l: l.company_id == company)
            bodega = company._laroca_bodega_central()
            cantidades = {}
            if bodega:
                grupos = Quant._read_group(
                    [('product_id', 'in', lineas.product_id.ids),
                     ('location_id', 'child_of', bodega.lot_stock_id.id)],
                    ['product_id'], ['quantity:sum', 'reserved_quantity:sum'])
                # Disponible = existencias - lo reservado para entregas en camino
                cantidades = {producto.id: cantidad - reservado for producto, cantidad, reservado in grupos}
            for linea in lineas:
                linea.disponible_bodega = cantidades.get(linea.product_id.id, 0.0)
        (self - self.filtered('company_id')).disponible_bodega = 0.0

    def _compute_cantidad_en_entrega(self):
        grupos = self.env['laroca.entrega.linea'].sudo()._read_group(
            [('entrega_id.estado', 'in', ('borrador', 'en_camino')),
             ('entrega_id.gasolinera_id', 'in', self.gasolinera_id.ids),
             ('product_id', 'in', self.product_id.ids)],
            ['gasolinera_id', 'product_id'], ['cantidad:sum'])
        cantidades = {(g.id, p.id): total for g, p, total in grupos}
        for linea in self:
            linea.cantidad_en_entrega = cantidades.get((linea.gasolinera_id.id, linea.product_id.id), 0.0)

    def action_crear_entregas(self):
        """Crea una entrega en borrador por gasolinera con las cantidades sugeridas
        de las líneas seleccionadas (descontando lo que ya está en otra entrega)."""
        Entrega = self.env['laroca.entrega']
        entregas = Entrega.browse()
        pendientes = self.filtered(lambda l: l.estado in ('bajo', 'critico'))
        for gasolinera in pendientes.gasolinera_id:
            lineas_vals = []
            for linea in pendientes.filtered(lambda l: l.gasolinera_id == gasolinera):
                cantidad = linea.cantidad_sugerida - linea.cantidad_en_entrega
                if cantidad > 0:
                    lineas_vals.append((0, 0, {
                        'product_id': linea.product_id.id,
                        'cantidad': cantidad,
                        'cantidad_sugerida': linea.cantidad_sugerida,
                    }))
            if lineas_vals:
                entregas |= Entrega.create({'gasolinera_id': gasolinera.id, 'linea_ids': lineas_vals})
        if not entregas:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Nada que preparar'),
                    'message': _('Los productos seleccionados no necesitan abastecimiento '
                                 'o ya están incluidos en otra entrega.'),
                    'type': 'warning',
                },
            }
        action = self.env['ir.actions.actions']._for_xml_id('laroca_inventario.action_laroca_entregas')
        if len(entregas) == 1:
            action.update({'res_id': entregas.id, 'views': [(False, 'form')], 'view_mode': 'form'})
        else:
            action['domain'] = [('id', 'in', entregas.ids)]
            action['context'] = {}
        return action

    def _compute_alerta_abierta_count(self):
        grupos = self.env['laroca.alerta']._read_group(
            [('linea_id', 'in', self.ids), ('estado', 'in', ('abierta', 'en_proceso'))], ['linea_id'], ['__count'])
        conteo = {linea.id: total for linea, total in grupos}
        for linea in self:
            linea.alerta_abierta_count = conteo.get(linea.id, 0)

    def write(self, vals):
        res = super().write(vals)
        if {'stock_actual', 'stock_minimo', 'stock_objetivo', 'active'} & set(vals):
            self._sincronizar_alertas()
        return res

    # ------------------------------------------------------------------
    # Alertas automáticas
    # ------------------------------------------------------------------
    def _sincronizar_alertas(self, notificar=True):
        """Deja las alertas coherentes con el estado de cada línea:
        - bajo/crítico sin alerta abierta → crea alerta y notifica
        - alerta "bajo" que pasa a crítico → sube el nivel y notifica
        - stock suficiente (o línea archivada) → cierra la alerta
        """
        if self.env.context.get('laroca_sin_alertas'):
            return
        Alerta = self.env['laroca.alerta'].sudo()
        lineas = self.sudo().with_context(active_test=False).exists()
        abiertas = {a.linea_id.id: a for a in Alerta.search(
            [('linea_id', 'in', lineas.ids), ('estado', 'in', ('abierta', 'en_proceso'))])}
        nuevas, escaladas = Alerta.browse(), Alerta.browse()
        for linea in lineas:
            alerta = abiertas.get(linea.id)
            pendiente = linea.active and linea.estado in ('bajo', 'critico')
            if pendiente and not alerta:
                nuevas |= Alerta.create({
                    'linea_id': linea.id,
                    'nivel': linea.estado,
                    'stock_al_alertar': linea.stock_actual,
                    'stock_minimo_al_alertar': linea.stock_minimo,
                })
            elif pendiente and alerta.nivel != linea.estado:
                if linea.estado == 'critico':
                    escaladas |= alerta
                alerta.nivel = linea.estado
            elif not pendiente and alerta:
                alerta.write({'estado': 'resuelta', 'fecha_resolucion': fields.Datetime.now()})
        if notificar:
            nuevas._notificar(_('Nueva alerta de abastecimiento'))
            escaladas._notificar(_('Stock CRÍTICO'))
        return nuevas | escaladas

    def action_ver_alertas(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('laroca_inventario.action_laroca_alertas')
        action['domain'] = [('linea_id', '=', self.id)]
        action['context'] = {'search_default_abiertas': 0}
        return action

    @api.depends('product_id', 'gasolinera_id')
    def _compute_display_name(self):
        for linea in self:
            linea.display_name = f'{linea.product_id.display_name} - {linea.gasolinera_id.name}'

    def _compute_movimiento_ids(self):
        MoveLine = self.env['stock.move.line']
        for linea in self:
            ubicacion = linea.gasolinera_id.view_location_id
            linea.movimiento_ids = MoveLine.search([
                ('product_id', '=', linea.product_id.id),
                ('state', '=', 'done'),
                '|', ('location_id', 'child_of', ubicacion.id),
                     ('location_dest_id', 'child_of', ubicacion.id),
            ], order='date desc, id desc', limit=10) if ubicacion else MoveLine

    # ------------------------------------------------------------------
    # Cálculo del stock actual
    # ------------------------------------------------------------------
    def _refrescar_stock(self):
        """Recalcula stock_actual sumando los quants de la ubicación de stock
        de cada gasolinera (incluye sub-ubicaciones)."""
        Quant = self.env['stock.quant'].sudo()
        lineas_todas = self.sudo()
        cambiadas = self.browse()
        for gasolinera in lineas_todas.gasolinera_id:
            lineas = lineas_todas.filtered(lambda l: l.gasolinera_id == gasolinera)
            grupos = Quant._read_group(
                [('product_id', 'in', lineas.product_id.ids),
                 ('location_id', 'child_of', gasolinera.lot_stock_id.id)],
                ['product_id'], ['quantity:sum'])
            cantidades = {producto.id: cantidad for producto, cantidad in grupos}
            for linea in lineas:
                nueva = cantidades.get(linea.product_id.id, 0.0)
                rounding = linea.uom_id.rounding or 0.01
                if float_compare(nueva, linea.stock_actual, precision_rounding=rounding):
                    # Las alertas se procesan juntas al final (un solo mensaje por gasolinera).
                    linea.with_context(laroca_sin_alertas=True).write({
                        'stock_actual': nueva,
                        'ultima_actualizacion': fields.Datetime.now(),
                        'ultima_actualizacion_por': self.env.uid,
                    })
                    cambiadas |= linea
        cambiadas._sincronizar_alertas()

    @api.model
    def _refrescar_por_producto_gasolinera(self, productos, gasolineras):
        lineas = self.sudo().with_context(active_test=False).search([
            ('product_id', 'in', productos.ids),
            ('gasolinera_id', 'in', gasolineras.ids),
        ])
        lineas._refrescar_stock()

    # ------------------------------------------------------------------
    # Generación de líneas (gasolinera x producto)
    # ------------------------------------------------------------------
    @api.model
    def _generar_lineas(self, gasolineras=None, productos=None):
        """Crea las líneas que falten para que cada gasolinera tenga todos los
        productos inventariables del catálogo. Es seguro llamarlo varias veces."""
        Warehouse = self.env['stock.warehouse'].sudo()
        Product = self.env['product.product'].sudo()
        gasolineras = (gasolineras.sudo() if gasolineras is not None
                       else Warehouse.search([('laroca_es_gasolinera', '=', True)]))
        productos = (productos.sudo() if productos is not None
                     else Product.search([('is_storable', '=', True)]))
        gasolineras = gasolineras.filtered('laroca_es_gasolinera')
        productos = productos.filtered('is_storable')
        if not gasolineras or not productos:
            return self.browse()
        existentes = {
            (linea.gasolinera_id.id, linea.product_id.id)
            for linea in self.sudo().with_context(active_test=False).search([
                ('gasolinera_id', 'in', gasolineras.ids),
                ('product_id', 'in', productos.ids),
            ])
        }
        vals_list = [
            {
                'gasolinera_id': gasolinera.id,
                'product_id': producto.id,
                'stock_minimo': producto.laroca_stock_minimo,
                'stock_objetivo': producto.laroca_stock_objetivo,
            }
            for gasolinera in gasolineras for producto in productos
            if (gasolinera.id, producto.id) not in existentes
        ]
        lineas = self.sudo().create(vals_list)
        lineas._refrescar_stock()
        lineas._sincronizar_alertas()
        return lineas

    @api.model
    def action_sincronizar_catalogo(self):
        """Acción manual (menú Configuración) para crear líneas faltantes y
        recalcular el stock de todas las gasolineras."""
        self._generar_lineas()
        lineas = self.sudo().with_context(active_test=False).search([])
        lineas._refrescar_stock()
        lineas._sincronizar_alertas()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Inventario sincronizado',
                'message': 'Se revisaron todas las gasolineras y productos del catálogo.',
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    # ------------------------------------------------------------------
    # Botones
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Ajuste de existencias (lo usan "Actualizar stock" y "Conteo rápido")
    # ------------------------------------------------------------------
    @api.model
    def _ajustar_existencias(self, cantidades, referencia):
        """Aplica nuevas existencias con un ajuste de inventario nativo de Odoo.

        :param cantidades: {laroca.inventario: nueva cantidad}
        :param referencia: texto que queda en el historial de movimientos
        :return: líneas cuya cantidad cambió
        """
        if not self.env.su and not self.env.user.has_group('laroca_inventario.group_laroca_admin'):
            # El encargado no corrige existencias: el stock baja con las ventas y sube con las entregas.
            raise AccessError(_('Solo el administrador puede corregir existencias. '
                                'Para descontar lo vendido usá "Vender"; si te falta algo, hacé un pedido.'))
        Quant = self.env['stock.quant']
        lineas = self.browse([linea.id for linea in cantidades])
        lineas.check_access('read')  # reglas: solo gasolineras asignadas
        quants, cambiadas = Quant.browse(), self.browse()
        for linea, nueva in cantidades.items():
            if nueva < 0:
                raise ValidationError(_('%s: la existencia no puede ser negativa.', linea.product_id.display_name))
            rounding = linea.uom_id.rounding or 0.01
            diferencia = nueva - linea.stock_actual
            if float_is_zero(diferencia, precision_rounding=rounding):
                continue
            ubicacion = linea.gasolinera_id.lot_stock_id
            quant = Quant._gather(linea.product_id, ubicacion, strict=True)[:1]
            if not quant:
                quant = Quant.create({'product_id': linea.product_id.id, 'location_id': ubicacion.id})
            nueva_quant = quant.quantity + diferencia
            if float_compare(nueva_quant, 0, precision_rounding=rounding) < 0:
                raise UserError(_('%s: la cantidad resultante sería negativa.', linea.product_id.display_name))
            quant.write({'inventory_quantity': nueva_quant, 'user_id': self.env.uid})
            quants |= quant
            cambiadas |= linea
        if quants:
            # Un solo ajuste para todos los productos; las alertas se evalúan juntas al final.
            quants.with_context(inventory_name=referencia, laroca_sin_alertas=True)._apply_inventory()
        # Se registra la fecha también en los productos sin cambios (conteo confirmado).
        lineas.sudo().write({'ultima_actualizacion': fields.Datetime.now(), 'ultima_actualizacion_por': self.env.uid})
        lineas.sudo()._sincronizar_alertas()
        return cambiadas

    def action_actualizar_stock(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Actualizar stock',
            'res_model': 'laroca.actualizar.stock',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_linea_id': self.id, 'default_cantidad_nueva': self.stock_actual},
        }

    def action_ver_movimientos(self):
        self.ensure_one()
        ubicacion = self.gasolinera_id.view_location_id
        return {
            'type': 'ir.actions.act_window',
            'name': f'Movimientos - {self.display_name}',
            'res_model': 'stock.move.line',
            'view_mode': 'list,form',
            'views': [(self.env.ref('laroca_inventario.view_laroca_move_line_list').id, 'list'), (False, 'form')],
            'domain': [
                ('product_id', '=', self.product_id.id), ('state', '=', 'done'),
                '|', ('location_id', 'child_of', ubicacion.id),
                     ('location_dest_id', 'child_of', ubicacion.id),
            ],
            'context': {'create': False},
        }
