from odoo.exceptions import AccessError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'laroca')
class TestLarocaBodega(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.g1 = cls.env['stock.warehouse'].create({'name': 'Bod Uno', 'code': 'BO1', 'laroca_es_gasolinera': True})
        cls.bodega = cls.env.company._laroca_bodega_central()
        cls.llavero = cls.env['product.product'].create({
            'name': 'Llavero Bodega', 'default_code': 'BOD-1', 'type': 'consu', 'is_storable': True,
            'standard_price': 2, 'laroca_stock_minimo': 5})
        cls.env['stock.quant']._update_available_quantity(cls.llavero, cls.bodega.lot_stock_id, 10)
        cls.encargado = new_test_user(cls.env, login='enc_bod', groups='laroca_inventario.group_laroca_encargado',
                                      laroca_gasolinera_ids=[(6, 0, cls.g1.ids)])
        cls.admin = new_test_user(cls.env, login='adm_bod', groups='laroca_inventario.group_laroca_admin')

    def _movimiento(self, modo, cantidad):
        form = Form(self.env['laroca.bodega.movimiento'].with_user(self.admin))
        form.modo = modo
        form.buscar = 'Llavero Bodega'
        with form.linea_ids.edit(0) as linea:
            self.assertEqual(linea.product_id, self.llavero)
            linea.cantidad = cantidad
        return form.save().action_guardar()

    def test_recibir_suma_y_encargado_lo_ve(self):
        form = Form(self.env['laroca.bodega.movimiento'].with_user(self.admin))
        form.proveedor = 'Distribuidora Ficticia'
        form.buscar = 'Llavero Bodega'
        with form.linea_ids.edit(0) as linea:
            self.assertEqual(linea.en_bodega, 10)
            linea.cantidad = 25
            self.assertEqual(linea.queda, 35)
        resultado = form.save().action_guardar()
        self.assertEqual(resultado['params']['titulo'], '¡Mercadería recibida!')
        self.assertEqual(self.llavero.product_tmpl_id.laroca_stock_bodega, 35)
        recepcion = self.env['stock.picking'].search([('origin', '=', 'Distribuidora Ficticia')])
        self.assertEqual(recepcion.state, 'done')
        # El encargado ve cuánto hay en la bodega (en el catálogo y en su inventario)
        self.assertEqual(self.llavero.product_tmpl_id.with_user(self.encargado).laroca_disponible_bodega, 35)
        linea = self.env['laroca.inventario'].with_user(self.encargado).search([('product_id', '=', self.llavero.id)])
        self.assertEqual(linea.disponible_bodega, 35)

    def test_contar_deja_cantidad_exacta(self):
        resultado = self._movimiento('contar', 4)
        self.assertEqual(resultado['params']['titulo'], 'Bodega actualizada')
        self.assertEqual(self.llavero.product_tmpl_id.laroca_stock_bodega, 4)
        self.assertEqual(self.llavero.product_tmpl_id.laroca_valor_bodega, 8)

    def test_reservado_y_permisos(self):
        linea = self.env['laroca.inventario'].search([('gasolinera_id', '=', self.g1.id), ('product_id', '=', self.llavero.id)])
        entrega = self.env['laroca.entrega'].with_user(self.admin).create({
            'gasolinera_id': self.g1.id, 'linea_ids': [(0, 0, {'product_id': self.llavero.id, 'cantidad': 6})]})
        entrega.action_confirmar()  # aparta 6 en bodega
        plantilla = self.llavero.product_tmpl_id
        self.assertEqual(plantilla.laroca_reservado_bodega, 6)
        self.assertEqual(plantilla.laroca_disponible_bodega, 4)
        self.assertEqual(linea.disponible_bodega, 4)
        with self.assertRaises(AccessError):
            self.env['laroca.bodega.movimiento'].with_user(self.encargado).create({'modo': 'recibir'})
        # Sin cantidades: aviso, no se crea nada
        self.assertEqual(self._movimiento('recibir', 0)['params']['tipo'], 'warning')

    def test_producto_nuevo_con_unidades(self):
        form = Form(self.env['laroca.producto.nuevo'].with_user(self.admin))
        form.name = 'Llavero de silicona'
        form.categ_id = self.env.ref('product.product_category_all')
        form.default_code = 'BOD-NUEVO'
        form.list_price = 3
        form.standard_price = 1.5
        form.laroca_stock_minimo = 5
        form.cantidad = 40
        form.proveedor = 'Proveedor Ficticio'
        resultado = form.save().action_crear()
        self.assertEqual(resultado['params']['titulo'], '¡Producto agregado!')
        plantilla = self.env['product.template'].search([('default_code', '=', 'BOD-NUEVO')])
        self.assertTrue(plantilla.is_storable)
        self.assertEqual(plantilla.laroca_stock_bodega, 40)
        # Ya está en las gasolineras, con su mínimo
        linea = self.env['laroca.inventario'].search([('gasolinera_id', '=', self.g1.id),
                                                      ('product_id', '=', plantilla.product_variant_id.id)])
        self.assertEqual(linea.stock_minimo, 5)
        # Código repetido: aviso, no se crea otro
        repetido = self.env['laroca.producto.nuevo'].with_user(self.admin).create(
            {'name': 'Otro', 'default_code': 'BOD-NUEVO',
             'categ_id': self.env.ref('product.product_category_all').id}).action_crear()
        self.assertEqual(repetido['params']['tipo'], 'warning')
        with self.assertRaises(AccessError):
            self.env['laroca.producto.nuevo'].with_user(self.encargado).create({'name': 'No'})

    def test_panel_bodega(self):
        # La gasolinera necesita llaveros (0 en la gasolinera, mínimo 5) y la bodega tiene 10
        panel_modelo = self.env['laroca.panel.bodega'].with_user(self.encargado)
        panel = panel_modelo.browse(panel_modelo.action_abrir_panel()['res_id'])
        plantilla = self.llavero.product_tmpl_id
        self.assertGreaterEqual(panel.kpi_unidades, 10)
        self.assertNotIn(plantilla, panel.comprar_ids)
        # Si la bodega se vacía, aparece en "Conviene comprar"
        self._movimiento('contar', 0)
        panel = panel_modelo.browse(panel_modelo.action_abrir_panel()['res_id'])
        self.assertIn(plantilla, panel.comprar_ids)
        self.assertEqual(plantilla.laroca_faltante_bodega, plantilla.laroca_sugerido_gasolineras)
        recibir = panel.with_user(self.admin).action_comprar_recibir()
        self.assertIn(self.llavero.id, recibir['context']['laroca_productos'])
        for metodo in ('action_recibir', 'action_contar', 'action_producto_nuevo', 'action_importar',
                       'action_ver_productos', 'action_ver_sin_stock', 'action_ver_comprar'):
            self.assertIn('res_model', getattr(panel, metodo)())

