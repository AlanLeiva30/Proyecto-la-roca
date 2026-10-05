from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'laroca')
class TestLarocaConteo(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.laroca_porcentaje_critico = 50
        cls.g1 = cls.env['stock.warehouse'].create({'name': 'Conteo Uno', 'code': 'CO1', 'laroca_es_gasolinera': True})
        cls.g2 = cls.env['stock.warehouse'].create({'name': 'Conteo Dos', 'code': 'CO2', 'laroca_es_gasolinera': True})
        Product = cls.env['product.product']
        cls.p1 = Product.create({'name': 'Conteo A', 'type': 'consu', 'is_storable': True, 'laroca_stock_minimo': 10})
        cls.p2 = Product.create({'name': 'Conteo B', 'type': 'consu', 'is_storable': True, 'laroca_stock_minimo': 10})
        Quant = cls.env['stock.quant']
        Quant._update_available_quantity(cls.p1, cls.g1.lot_stock_id, 20)
        Quant._update_available_quantity(cls.p2, cls.g1.lot_stock_id, 20)
        cls.encargado = new_test_user(cls.env, login='encargado_conteo', groups='laroca_inventario.group_laroca_encargado',
                                      laroca_gasolinera_ids=[(6, 0, cls.g1.ids)])
        cls.admin = new_test_user(cls.env, login='admin_conteo', groups='laroca_inventario.group_laroca_admin')
        cls.canal = cls.env.ref('laroca_inventario.canal_alertas_abastecimiento')

    def _linea(self, producto):
        return self.env['laroca.inventario'].search([('gasolinera_id', '=', self.g1.id), ('product_id', '=', producto.id)])

    def test_conteo_rapido_varios_productos(self):
        mensajes = self.env['mail.message'].search_count([('model', '=', 'discuss.channel'), ('res_id', '=', self.canal.id)])
        form = Form(self.env['laroca.conteo'].with_user(self.admin).with_context(default_gasolinera_id=self.g1.id))
        self.assertEqual(form.gasolinera_id, self.g1)
        nuestras = {self.p1: 3, self.p2: 7}
        for indice in range(len(form.linea_ids)):
            with form.linea_ids.edit(indice) as linea:
                producto = linea.inventario_id.product_id
                if producto in nuestras:
                    linea.cantidad_contada = nuestras[producto]
        conteo = form.save()
        self.assertEqual(conteo.total_cambios, 2)
        resultado = conteo.action_guardar()
        self.assertEqual(resultado['tag'], 'display_notification')
        self.assertEqual(self._linea(self.p1).stock_actual, 3)
        self.assertEqual(self._linea(self.p2).stock_actual, 7)
        self.assertEqual(self._linea(self.p1).estado, 'critico')
        self.assertEqual(self._linea(self.p2).estado, 'bajo')
        # Un solo mensaje al administrador con los dos productos
        nuevos = self.env['mail.message'].search_count([('model', '=', 'discuss.channel'), ('res_id', '=', self.canal.id)])
        self.assertEqual(nuevos, mensajes + 1)
        movimientos = self.env['stock.move'].search([('reference', 'ilike', 'CO1: Conteo rápido')])
        self.assertEqual(len(movimientos), 2)

    def test_filtros_del_conteo(self):
        self.env['stock.quant']._update_available_quantity(self.p1, self.g1.lot_stock_id, -15)  # queda en 5: crítico
        form = Form(self.env['laroca.conteo'].with_user(self.admin).with_context(default_gasolinera_id=self.g1.id))
        form.solo_pendientes = True
        productos = {form.linea_ids.edit(i).__enter__().inventario_id.product_id for i in range(len(form.linea_ids))}
        self.assertIn(self.p1, productos)
        self.assertNotIn(self.p2, productos)

    def test_encargado_no_hace_conteos(self):
        """El conteo rápido corrige existencias: queda solo para el administrador."""
        from odoo.exceptions import AccessError
        with self.assertRaises(AccessError):
            self.env['laroca.conteo'].with_user(self.encargado).create({'gasolinera_id': self.g1.id})
