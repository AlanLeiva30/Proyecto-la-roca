from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'laroca')
class TestLarocaInventario(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Warehouse = cls.env['stock.warehouse']
        cls.g1 = Warehouse.create({'name': 'Prueba Uno', 'code': 'PU1', 'laroca_es_gasolinera': True})
        cls.g2 = Warehouse.create({'name': 'Prueba Dos', 'code': 'PU2', 'laroca_es_gasolinera': True})
        cls.bodega = Warehouse.create({'name': 'Bodega Prueba', 'code': 'BPR'})
        cls.producto = cls.env['product.product'].create({
            'name': 'Lentes de prueba', 'default_code': 'TEST-001', 'type': 'consu', 'is_storable': True,
        })
        cls.encargado = new_test_user(
            cls.env, login='encargado_prueba', groups='laroca_inventario.group_laroca_encargado',
            laroca_gasolinera_ids=[(6, 0, cls.g1.ids)])
        cls.admin = new_test_user(cls.env, login='admin_prueba', groups='laroca_inventario.group_laroca_admin')
        Inventario = cls.env['laroca.inventario']
        cls.linea_g1 = Inventario.search([('gasolinera_id', '=', cls.g1.id), ('product_id', '=', cls.producto.id)])
        cls.linea_g2 = Inventario.search([('gasolinera_id', '=', cls.g2.id), ('product_id', '=', cls.producto.id)])

    def _actualizar(self, linea, cantidad, user=None):
        Wizard = self.env['laroca.actualizar.stock']
        if user:
            Wizard = Wizard.with_user(user)
        wizard = Wizard.create({'linea_id': linea.id, 'cantidad_nueva': cantidad, 'motivo': 'conteo'})
        return wizard.action_confirmar()

    # --- Generación automática de líneas -------------------------------
    def test_lineas_creadas_por_gasolinera(self):
        self.assertEqual(len(self.linea_g1), 1)
        self.assertEqual(len(self.linea_g2), 1)
        lineas_bodega = self.env['laroca.inventario'].search([('gasolinera_id', '=', self.bodega.id)])
        self.assertFalse(lineas_bodega, 'La bodega central no es gasolinera: no lleva líneas')

    def test_producto_nuevo_se_agrega_a_gasolineras(self):
        nuevo = self.env['product.product'].create({'name': 'Llavero', 'type': 'consu', 'is_storable': True})
        lineas = self.env['laroca.inventario'].search([('product_id', '=', nuevo.id)])
        self.assertIn(self.g1, lineas.gasolinera_id)
        self.assertIn(self.g2, lineas.gasolinera_id)

    def test_gasolinera_archivada_oculta_lineas(self):
        self.g2.action_archive()
        self.assertFalse(self.linea_g2.active)
        self.assertNotIn(self.linea_g2, self.env['laroca.inventario'].search([]))
        self.g2.action_unarchive()
        self.assertTrue(self.linea_g2.active)

    def test_servicio_no_se_agrega(self):
        servicio = self.env['product.product'].create({'name': 'Lavado', 'type': 'service'})
        self.assertFalse(self.env['laroca.inventario'].search([('product_id', '=', servicio.id)]))

    # --- Acceso por rol ------------------------------------------------
    def test_encargado_solo_ve_su_gasolinera(self):
        lineas = self.env['laroca.inventario'].with_user(self.encargado).search([])
        self.assertEqual(lineas.gasolinera_id, self.g1)
        gasolineras = self.env['stock.warehouse'].with_user(self.encargado).search([])
        self.assertEqual(gasolineras, self.g1)
        with self.assertRaises(AccessError):
            self.linea_g2.with_user(self.encargado).read(['stock_actual'])

    def test_admin_ve_todas(self):
        lineas = self.env['laroca.inventario'].with_user(self.admin).search([])
        self.assertIn(self.g1, lineas.gasolinera_id)
        self.assertIn(self.g2, lineas.gasolinera_id)

    def test_asignar_gasolinera_da_acceso_inmediato(self):
        Inventario = self.env['laroca.inventario'].with_user(self.encargado)
        self.assertNotIn(self.g2, Inventario.search([]).gasolinera_id)
        self.g2.laroca_encargado_ids = [(4, self.encargado.id)]
        self.assertIn(self.g2, Inventario.search([]).gasolinera_id)

    def test_encargado_no_modifica_catalogo(self):
        with self.assertRaises(AccessError):
            self.env['product.template'].with_user(self.encargado).create({'name': 'No permitido'})
        with self.assertRaises(AccessError):
            self.env['stock.warehouse'].with_user(self.encargado).create({'name': 'X', 'code': 'XX'})

    # --- Actualización de existencias ---------------------------------
    def test_administrador_corrige_stock(self):
        self._actualizar(self.linea_g1, 15, user=self.admin)
        self.assertEqual(self.linea_g1.stock_actual, 15)
        self.assertEqual(self.linea_g1.ultima_actualizacion_por, self.admin)
        self._actualizar(self.linea_g1, 4, user=self.admin)
        self.assertEqual(self.linea_g1.stock_actual, 4)
        # Stock nativo de Odoo coherente con la línea
        qty = self.producto.with_context(warehouse_id=self.g1.id).qty_available
        self.assertEqual(qty, 4)
        # Cada ajuste queda como movimiento (historial)
        movimientos = self.linea_g1.with_user(self.encargado).movimiento_ids
        self.assertEqual(len(movimientos), 2)
        self.assertIn('PU1', movimientos[0].reference)
        # La otra gasolinera no cambia
        self.assertEqual(self.linea_g2.stock_actual, 0)

    def test_encargado_no_corrige_stock(self):
        """El encargado no modifica existencias a mano: vende y pide (ni en su gasolinera ni en otra)."""
        for linea in (self.linea_g1, self.linea_g2):
            with self.assertRaises(AccessError):
                self._actualizar(linea, 10, user=self.encargado)
            with self.assertRaises(AccessError):
                self.env['laroca.inventario'].with_user(self.encargado)._ajustar_existencias({linea: 10}, 'X')
        self.assertEqual(self.linea_g2.stock_actual, 0)
        self.assertEqual(self.linea_g1.stock_actual, 0)

    def test_cantidad_negativa(self):
        with self.assertRaises(ValidationError):
            self._actualizar(self.linea_g1, -3, user=self.admin)

    def test_movimiento_nativo_actualiza_linea(self):
        """Si el stock cambia por cualquier vía nativa de Odoo (p. ej. una
        transferencia), la línea de la gasolinera se actualiza sola."""
        self.env['stock.quant']._update_available_quantity(self.producto, self.g2.lot_stock_id, 7)
        self.assertEqual(self.linea_g2.stock_actual, 7)
