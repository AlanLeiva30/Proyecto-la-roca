from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'laroca')
class TestLarocaEntregas(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.laroca_porcentaje_critico = 50
        Warehouse = cls.env['stock.warehouse']
        cls.g1 = Warehouse.create({'name': 'Entrega Uno', 'code': 'EN1', 'laroca_es_gasolinera': True})
        cls.g2 = Warehouse.create({'name': 'Entrega Dos', 'code': 'EN2', 'laroca_es_gasolinera': True})
        cls.bodega = cls.env.company._laroca_bodega_central()
        Product = cls.env['product.product']
        cls.lentes = Product.create({'name': 'Lentes E', 'type': 'consu', 'is_storable': True,
                                     'laroca_stock_minimo': 10, 'laroca_stock_objetivo': 20})
        cls.gorra = Product.create({'name': 'Gorra E', 'type': 'consu', 'is_storable': True,
                                    'laroca_stock_minimo': 5, 'laroca_stock_objetivo': 10})
        Quant = cls.env['stock.quant']
        Quant._update_available_quantity(cls.lentes, cls.bodega.lot_stock_id, 100)
        Quant._update_available_quantity(cls.gorra, cls.bodega.lot_stock_id, 100)
        Quant._update_available_quantity(cls.lentes, cls.g1.lot_stock_id, 4)    # crítico → sugerido 16
        Quant._update_available_quantity(cls.gorra, cls.g1.lot_stock_id, 4)     # bajo → sugerido 6
        cls.encargado = new_test_user(
            cls.env, login='encargado_entrega', groups='laroca_inventario.group_laroca_encargado',
            laroca_gasolinera_ids=[(6, 0, cls.g1.ids)])
        cls.otro_encargado = new_test_user(
            cls.env, login='otro_encargado', groups='laroca_inventario.group_laroca_encargado',
            laroca_gasolinera_ids=[(6, 0, cls.g2.ids)])
        cls.admin = new_test_user(cls.env, login='admin_entrega', groups='laroca_inventario.group_laroca_admin')
        cls.Inventario = cls.env['laroca.inventario']

    def _linea(self, gasolinera, producto):
        return self.Inventario.search([('gasolinera_id', '=', gasolinera.id), ('product_id', '=', producto.id)])

    def _crear_entrega(self):
        lineas = self.Inventario.with_user(self.admin).search(
            [('gasolinera_id', '=', self.g1.id), ('estado', 'in', ('bajo', 'critico'))])
        accion = lineas.action_crear_entregas()
        return self.env['laroca.entrega'].browse(accion['res_id'])

    def _recibir(self, entrega, user, cantidades=None):
        recepcion = self.env['laroca.recepcion'].with_user(user).with_context(
            default_entrega_id=entrega.id).create({})
        for linea in recepcion.linea_ids:
            if cantidades and linea.product_id in cantidades:
                linea.cantidad_recibida = cantidades[linea.product_id]
        return recepcion.action_confirmar()

    def test_crear_desde_sugerencias(self):
        entrega = self._crear_entrega()
        self.assertEqual(entrega.estado, 'borrador')
        self.assertEqual(entrega.gasolinera_id, self.g1)
        self.assertEqual(entrega.bodega_id, self.bodega)
        self.assertTrue(entrega.name.startswith('ENT-'))
        cantidades = {l.product_id: l.cantidad for l in entrega.linea_ids}
        self.assertEqual(cantidades, {self.lentes: 16, self.gorra: 6})
        # No se duplica: lo ya incluido en una entrega no se vuelve a sugerir
        self.assertEqual(self._linea(self.g1, self.lentes).cantidad_en_entrega, 16)
        accion = self.Inventario.search([('gasolinera_id', '=', self.g1.id)]).action_crear_entregas()
        self.assertEqual(accion['tag'], 'display_notification')

    def test_flujo_completo(self):
        entrega = self._crear_entrega()
        entrega.with_user(self.admin).action_confirmar()
        self.assertEqual(entrega.estado, 'en_camino')
        picking = entrega.picking_id
        self.assertEqual(picking.picking_type_id, self.bodega.int_type_id)
        self.assertEqual(picking.location_id, self.bodega.lot_stock_id)
        self.assertEqual(picking.location_dest_id, self.g1.lot_stock_id)
        self.assertEqual(picking.state, 'assigned')  # stock reservado en bodega
        alertas = self.env['laroca.alerta'].search([('gasolinera_id', '=', self.g1.id), ('estado', '!=', 'resuelta')])
        self.assertEqual(set(alertas.mapped('estado')), {'en_proceso'})
        self.assertIn(self.encargado.partner_id, entrega.message_partner_ids)  # encargado notificado

        self._recibir(entrega, self.encargado)
        self.assertEqual(entrega.estado, 'entregada')
        self.assertEqual(entrega.recibido_por_id, self.encargado)
        self.assertEqual(picking.state, 'done')
        self.assertEqual(self._linea(self.g1, self.lentes).stock_actual, 20)
        self.assertEqual(self._linea(self.g1, self.gorra).stock_actual, 10)
        self.assertEqual(self._linea(self.g1, self.lentes).estado, 'suficiente')
        self.assertEqual(self.lentes.with_context(warehouse_id=self.bodega.id).qty_available, 84)
        self.assertEqual(set(alertas.mapped('estado')), {'resuelta'})
        self.assertEqual(alertas.entrega_id, entrega)

    def test_recepcion_parcial(self):
        entrega = self._crear_entrega()
        entrega.with_user(self.admin).action_confirmar()
        self._recibir(entrega, self.encargado, {self.lentes: 3})  # llegan 3 de 16
        self.assertEqual(entrega.estado, 'entregada')
        linea = self._linea(self.g1, self.lentes)
        self.assertEqual(linea.stock_actual, 7)
        self.assertEqual(linea.estado, 'bajo')
        self.assertFalse(self.env['stock.picking'].search([('backorder_id', '=', entrega.picking_id.id)]))
        alerta = self.env['laroca.alerta'].search([('linea_id', '=', linea.id), ('estado', '!=', 'resuelta')])
        self.assertEqual(alerta.estado, 'abierta')  # vuelve a quedar pendiente

    def test_sin_stock_en_bodega(self):
        entrega = self._crear_entrega()
        entrega.linea_ids.filtered(lambda l: l.product_id == self.lentes).cantidad = 500
        with self.assertRaises(UserError):
            entrega.with_user(self.admin).action_confirmar()
        self.assertEqual(entrega.estado, 'borrador')

    def test_cancelar(self):
        entrega = self._crear_entrega()
        entrega.with_user(self.admin).action_confirmar()
        entrega.with_user(self.admin).action_cancelar()
        self.assertEqual(entrega.estado, 'cancelada')
        self.assertEqual(entrega.picking_id.state, 'cancel')
        alertas = self.env['laroca.alerta'].search([('gasolinera_id', '=', self.g1.id), ('estado', '!=', 'resuelta')])
        self.assertEqual(set(alertas.mapped('estado')), {'abierta'})
        self.assertEqual(self._linea(self.g1, self.lentes).cantidad_en_entrega, 0)

    def test_permisos(self):
        entrega = self._crear_entrega()
        with self.assertRaises(AccessError):
            entrega.with_user(self.encargado).action_confirmar()          # solo admin confirma
        with self.assertRaises(AccessError):
            self.env['laroca.entrega'].with_user(self.encargado).create({'gasolinera_id': self.g1.id})
        entrega.with_user(self.admin).action_confirmar()
        with self.assertRaises(AccessError):
            self._recibir(entrega, self.otro_encargado)                    # otra gasolinera
        self.assertFalse(self.env['laroca.entrega'].with_user(self.otro_encargado).search([('id', '=', entrega.id)]))
        self.assertEqual(self.env['laroca.entrega'].with_user(self.encargado).search([('id', '=', entrega.id)]), entrega)

    def test_no_recibir_mas_de_lo_enviado(self):
        entrega = self._crear_entrega()
        entrega.with_user(self.admin).action_confirmar()
        with self.assertRaises(UserError):
            self._recibir(entrega, self.encargado, {self.lentes: 99})

    def test_no_borrar_entregada(self):
        entrega = self._crear_entrega()
        entrega.with_user(self.admin).action_confirmar()
        self._recibir(entrega, self.encargado)
        with self.assertRaises(UserError):
            entrega.with_user(self.admin).unlink()

    def test_preparar_desde_gasolinera_y_hoja_pdf(self):
        accion = self.g1.with_user(self.admin).action_laroca_preparar_entrega()
        entrega = self.env['laroca.entrega'].browse(accion['res_id'])
        self.assertEqual(len(entrega.linea_ids), 2)
        html, _tipo = self.env['ir.actions.report']._render_qweb_html(
            'laroca_inventario.report_laroca_entrega', entrega.ids)
        self.assertIn(entrega.name.encode(), html)

    def test_encargado_abre_formulario_de_entrega(self):
        """El encargado debe poder ver su entrega (incluye datos calculados de la bodega central)."""
        entrega = self._crear_entrega()
        entrega.with_user(self.admin).action_confirmar()
        vista = self.env['laroca.entrega'].with_user(self.encargado)
        datos = vista.browse(entrega.id).web_read({
            'name': {}, 'estado': {}, 'gasolinera_id': {'fields': {'display_name': {}}},
            'linea_ids': {'fields': {'product_id': {'fields': {'display_name': {}}}, 'stock_gasolinera': {},
                                     'disponible_bodega': {}, 'cantidad': {}, 'cantidad_entregada': {}}},
        })
        self.assertEqual(datos[0]['name'], entrega.name)
        self.assertTrue(all(linea['disponible_bodega'] >= 0 for linea in datos[0]['linea_ids']))
