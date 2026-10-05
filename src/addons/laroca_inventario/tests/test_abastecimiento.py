from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'laroca')
class TestLarocaAbastecimiento(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.laroca_porcentaje_critico = 50
        Warehouse = cls.env['stock.warehouse']
        cls.g1 = Warehouse.create({'name': 'Abasto Uno', 'code': 'AB1', 'laroca_es_gasolinera': True})
        cls.g2 = Warehouse.create({'name': 'Abasto Dos', 'code': 'AB2', 'laroca_es_gasolinera': True})
        cls.bodega = cls.env.company._laroca_bodega_central()
        cls.producto = cls.env['product.product'].create({
            'name': 'Lentes abasto', 'type': 'consu', 'is_storable': True,
            'laroca_stock_minimo': 10, 'laroca_stock_objetivo': 20,
        })
        cls.encargado = new_test_user(
            cls.env, login='encargado_abasto', groups='laroca_inventario.group_laroca_encargado',
            laroca_gasolinera_ids=[(6, 0, cls.g1.ids)])
        cls.admin = new_test_user(cls.env, login='admin_abasto', groups='laroca_inventario.group_laroca_admin')
        Inventario = cls.env['laroca.inventario']
        cls.linea = Inventario.search([('gasolinera_id', '=', cls.g1.id), ('product_id', '=', cls.producto.id)])
        cls.linea_g2 = Inventario.search([('gasolinera_id', '=', cls.g2.id), ('product_id', '=', cls.producto.id)])
        cls.canal = cls.env.ref('laroca_inventario.canal_alertas_abastecimiento')

    def _actualizar(self, linea, cantidad, user=None):
        wizard = self.env['laroca.actualizar.stock'].with_user(user or self.admin).create(
            {'linea_id': linea.id, 'cantidad_nueva': cantidad, 'motivo': 'conteo'})
        return wizard.action_confirmar()

    def _alertas(self, linea, estado='abierta'):
        return self.env['laroca.alerta'].search([('linea_id', '=', linea.id), ('estado', '=', estado)])

    def _mensajes_canal(self):
        return self.env['mail.message'].search_count([('model', '=', 'discuss.channel'), ('res_id', '=', self.canal.id)])

    # --- Niveles y estados ------------------------------------------------
    def test_niveles_por_defecto_del_producto(self):
        self.assertEqual(self.linea.stock_minimo, 10)
        self.assertEqual(self.linea.stock_objetivo, 20)

    def test_estados_segun_mockup(self):
        """Ejemplos del mockup 10.2: 12/10 suficiente, 7/10 bajo, 4/10 crítico."""
        casos = [(12, 'suficiente'), (10, 'suficiente'), (7, 'bajo'), (6, 'bajo'), (5, 'critico'), (4, 'critico'), (0, 'critico')]
        for cantidad, esperado in casos:
            with self.subTest(cantidad=cantidad):
                self._actualizar(self.linea, cantidad)
                self.assertEqual(self.linea.estado, esperado)

    def test_sin_minimo(self):
        self.linea.stock_minimo = 0
        self.assertEqual(self.linea.estado, 'sin_minimo')
        self.assertEqual(self.linea.cantidad_sugerida, 0)

    def test_cantidad_sugerida(self):
        self._actualizar(self.linea, 4)
        self.assertEqual(self.linea.cantidad_sugerida, 16)  # objetivo 20 - 4
        self.linea.stock_objetivo = 0                         # sin objetivo: doble del mínimo
        self.assertEqual(self.linea.cantidad_sugerida, 16)
        self._actualizar(self.linea, 15)
        self.assertEqual(self.linea.cantidad_sugerida, 0)     # suficiente: nada que llevar

    def test_umbral_critico_configurable(self):
        self._actualizar(self.linea, 7)
        self.assertEqual(self.linea.estado, 'bajo')
        self.env.company.laroca_porcentaje_critico = 70
        self.assertEqual(self.linea.estado, 'critico')
        self.assertEqual(self._alertas(self.linea).nivel, 'critico')
        with self.assertRaises(ValidationError):
            self.env.company.laroca_porcentaje_critico = 150

    def test_objetivo_menor_que_minimo(self):
        with self.assertRaises(ValidationError):
            self.linea.write({'stock_minimo': 10, 'stock_objetivo': 5})

    def test_encargado_no_cambia_minimo(self):
        with self.assertRaises(AccessError):
            self.linea.with_user(self.encargado).write({'stock_minimo': 1})

    def test_aplicar_niveles_a_todas(self):
        self.producto.product_tmpl_id.write({'laroca_stock_minimo': 6, 'laroca_stock_objetivo': 12})
        self.producto.product_tmpl_id.with_user(self.admin).action_laroca_aplicar_niveles()
        self.assertEqual((self.linea | self.linea_g2).mapped('stock_minimo'), [6, 6])

    # --- Alertas automáticas ----------------------------------------------
    def test_alerta_se_crea_notifica_escala_y_resuelve(self):
        self._actualizar(self.linea, 12)
        self.assertFalse(self._alertas(self.linea))
        mensajes = self._mensajes_canal()

        accion = self._actualizar(self.linea, 7)               # baja del mínimo → alerta "bajo"
        alerta = self._alertas(self.linea)
        self.assertEqual(len(alerta), 1)
        self.assertEqual(alerta.nivel, 'bajo')
        self.assertTrue(alerta.name.startswith('ALR-'))
        self.assertEqual(self._mensajes_canal(), mensajes + 1)
        self.assertEqual(accion['tag'], 'display_notification')  # aviso al encargado

        self._actualizar(self.linea, 6)                        # sigue bajo: no duplica ni notifica
        self.assertEqual(self._alertas(self.linea), alerta)
        self.assertEqual(self._mensajes_canal(), mensajes + 1)

        self._actualizar(self.linea, 3)                        # pasa a crítico: escala y notifica
        self.assertEqual(alerta.nivel, 'critico')
        self.assertEqual(self._mensajes_canal(), mensajes + 2)

        self._actualizar(self.linea, 25)                       # reabastecido: se resuelve sola
        self.assertEqual(alerta.estado, 'resuelta')
        self.assertTrue(alerta.fecha_resolucion)
        self.assertFalse(self._alertas(self.linea))

    def test_movimiento_nativo_genera_alerta(self):
        """Una entrada o salida por cualquier vía de Odoo también evalúa las alertas."""
        self.env['stock.quant']._update_available_quantity(self.producto, self.g2.lot_stock_id, 3)
        self.assertEqual(self._alertas(self.linea_g2).nivel, 'critico')

    def test_encargado_solo_ve_alertas_de_su_gasolinera(self):
        self._actualizar(self.linea, 2)
        self._actualizar(self.linea_g2, 2, user=self.admin)
        visibles = self.env['laroca.alerta'].with_user(self.encargado).search([])
        self.assertEqual(visibles.gasolinera_id, self.g1)
        todas = self.env['laroca.alerta'].with_user(self.admin).search([])
        self.assertIn(self.g2, todas.gasolinera_id)

    def test_linea_nueva_sin_stock_nace_con_alerta(self):
        self.assertEqual(self._alertas(self.linea).nivel, 'critico')

    def test_cron_sincroniza_alertas_faltantes(self):
        self._actualizar(self.linea, 12)
        self.linea.with_context(laroca_sin_alertas=True).write({'stock_minimo': 50, 'stock_objetivo': 60})
        self.assertFalse(self._alertas(self.linea))
        self.env['laroca.alerta']._cron_sincronizar_alertas()
        self.assertTrue(self._alertas(self.linea))

    def test_resumen_diario(self):
        self._actualizar(self.linea, 2)
        mensajes = self._mensajes_canal()
        self.env['laroca.alerta']._cron_resumen_diario()
        self.assertEqual(self._mensajes_canal(), mensajes + 1)

    def test_conteos_por_gasolinera(self):
        self._actualizar(self.linea, 2)
        self.assertGreaterEqual(self.g1.laroca_critico_count, 1)
        self.assertGreaterEqual(self.g1.laroca_pendiente_count, 1)

    def test_disponible_en_bodega(self):
        self.env['stock.quant']._update_available_quantity(self.producto, self.bodega.lot_stock_id, 40)
        self.assertEqual(self.linea.disponible_bodega, 40)

    def test_alerta_envia_correo_a_administradores(self):
        self.admin.email = 'admin.abasto@laroca.test'
        self._actualizar(self.linea, 12)
        Mail = self.env['mail.mail']
        antes = Mail.search([('subject', 'ilike', '[La Roca]')])
        self._actualizar(self.linea, 7)
        correo = Mail.search([('subject', 'ilike', '[La Roca]')]) - antes
        self.assertEqual(len(correo), 1)
        self.assertIn('admin.abasto@laroca.test', correo.email_to)
        self.assertIn('Lentes abasto', correo.body_html)
        # Desactivado en Parámetros: no se envía
        self.env.company.laroca_enviar_correos = False
        self._actualizar(self.linea, 12)
        antes = Mail.search([('subject', 'ilike', '[La Roca]')])
        self._actualizar(self.linea, 3)
        self.assertFalse(Mail.search([('subject', 'ilike', '[La Roca]')]) - antes)
