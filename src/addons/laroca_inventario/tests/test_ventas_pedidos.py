from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'laroca')
class TestLarocaVentasPedidos(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.laroca_porcentaje_critico = 50
        Warehouse = cls.env['stock.warehouse']
        cls.g1 = Warehouse.create({'name': 'Venta Uno', 'code': 'VE1', 'laroca_es_gasolinera': True})
        cls.g2 = Warehouse.create({'name': 'Venta Dos', 'code': 'VE2', 'laroca_es_gasolinera': True})
        cls.bodega = cls.env.company._laroca_bodega_central()
        cls.llavero = cls.env['product.product'].create({
            'name': 'Llavero Venta', 'default_code': 'VEN-1', 'type': 'consu', 'is_storable': True,
            'list_price': 2.5, 'standard_price': 1, 'laroca_stock_minimo': 10, 'laroca_stock_objetivo': 30})
        Quant = cls.env['stock.quant']
        Quant._update_available_quantity(cls.llavero, cls.g1.lot_stock_id, 20)
        Quant._update_available_quantity(cls.llavero, cls.bodega.lot_stock_id, 100)
        cls.encargado = new_test_user(
            cls.env, login='encargado_venta', groups='laroca_inventario.group_laroca_encargado',
            laroca_gasolinera_ids=[(6, 0, cls.g1.ids)])
        cls.otro = new_test_user(
            cls.env, login='otro_venta', groups='laroca_inventario.group_laroca_encargado',
            laroca_gasolinera_ids=[(6, 0, cls.g2.ids)])
        cls.admin = new_test_user(cls.env, login='admin_venta', groups='laroca_inventario.group_laroca_admin')
        cls.linea = cls.env['laroca.inventario'].search(
            [('gasolinera_id', '=', cls.g1.id), ('product_id', '=', cls.llavero.id)])

    # ------------------------------------------------------------------
    # Ventas
    # ------------------------------------------------------------------
    def _vender(self, cantidad, user=None):
        form = Form(self.env['laroca.vender'].with_user(user or self.encargado))
        self.assertEqual(form.gasolinera_id, self.g1)
        for indice in range(len(form.linea_ids)):
            with form.linea_ids.edit(indice) as linea:
                if linea.inventario_id == self.linea:
                    linea.cantidad = cantidad
        wizard = form.save()
        return wizard, wizard.action_vender()

    def test_vender_descuenta_stock(self):
        wizard, resultado = self._vender(5)
        self.assertEqual(wizard.total, 12.5)
        self.assertEqual(resultado['tag'], 'laroca_alerta')
        self.assertEqual(resultado['params']['tipo'], 'success')
        self.assertEqual(resultado['params']['next']['type'], 'ir.actions.act_window_close')
        venta = self.env['laroca.venta'].search([('gasolinera_id', '=', self.g1.id)])
        self.assertEqual(len(venta), 1)
        self.assertEqual(venta.total, 12.5)
        self.assertEqual(venta.vendedor_id, self.encargado)
        self.assertEqual(self.linea.stock_actual, 15)
        # Salida nativa de Odoo hacia el cliente
        self.assertEqual(venta.picking_id.state, 'done')
        self.assertEqual(venta.picking_id.location_dest_id, self.env.ref('stock.stock_location_customers'))
        # Vender 6 más: queda en 9, bajo el mínimo, y se crea la alerta sola
        self._vender(6)
        self.assertEqual(self.linea.stock_actual, 9)
        self.assertEqual(self.linea.estado, 'bajo')
        self.assertTrue(self.linea.alerta_abierta_count)

    def test_no_vender_mas_de_lo_que_hay(self):
        """Stock insuficiente: alerta roja, el asistente queda abierto y no se vende nada."""
        _wizard, resultado = self._vender(21)
        self.assertEqual(resultado['tag'], 'laroca_alerta')
        self.assertEqual(resultado['params']['tipo'], 'error')
        self.assertEqual(resultado['params']['titulo'], 'Stock insuficiente')
        self.assertIn('hay 20', resultado['params']['detalle'][0])
        self.assertNotIn('next', resultado['params'])
        self.assertEqual(self.linea.stock_actual, 20)
        self.assertFalse(self.env['laroca.venta'].search([('gasolinera_id', '=', self.g1.id)]))
        # La verificación también está en el modelo (por si dos ventas llegan a la vez)
        with self.assertRaises(UserError):
            self.env['laroca.venta'].with_user(self.encargado)._registrar(self.g1, {self.llavero: 21})
        # Sin cantidades: alerta de aviso
        _wizard, resultado = self._vender(0)
        self.assertEqual(resultado['params']['tipo'], 'warning')

    def test_venta_solo_en_su_gasolinera(self):
        with self.assertRaises(AccessError):
            self.env['laroca.venta'].with_user(self.otro)._registrar(self.g1, {self.llavero: 1})
        self._vender(2)
        self.assertFalse(self.env['laroca.venta'].with_user(self.otro).search([]))

    def test_venta_no_se_modifica_y_admin_anula(self):
        self._vender(5)
        venta = self.env['laroca.venta'].search([('gasolinera_id', '=', self.g1.id)])
        with self.assertRaises(AccessError):
            venta.with_user(self.encargado).write({'estado': 'anulada'})
        with self.assertRaises(AccessError):
            venta.with_user(self.encargado)._anular('error')
        with self.assertRaises(UserError):
            venta.unlink()
        anulacion = self.env['laroca.venta.anulacion'].with_user(self.admin).create(
            {'venta_id': venta.id, 'motivo': 'Se registró dos veces'})
        anulacion.action_confirmar()
        self.assertEqual(venta.estado, 'anulada')
        self.assertEqual(self.linea.stock_actual, 20)

    # ------------------------------------------------------------------
    # Pedidos
    # ------------------------------------------------------------------
    def _pedido(self, cantidad=50, user=None):
        form = Form(self.env['laroca.pedido'].with_user(user or self.encargado))
        with form.linea_ids.new() as linea:
            linea.product_id = self.llavero
            linea.cantidad = cantidad
        form.nota = 'Para el fin de semana'
        return form.save()

    def test_pedido_completo_hasta_la_entrega(self):
        pedido = self._pedido(50)
        self.assertEqual(pedido.gasolinera_id, self.g1)
        self.assertEqual(pedido.linea_ids.stock_gasolinera, 20)
        canal = self.env.ref('laroca_inventario.canal_alertas_abastecimiento')
        mensajes = self.env['mail.message'].search_count([('model', '=', 'discuss.channel'), ('res_id', '=', canal.id)])
        pedido.action_enviar()
        self.assertEqual(pedido.estado, 'enviado')
        self.assertEqual(
            self.env['mail.message'].search_count([('model', '=', 'discuss.channel'), ('res_id', '=', canal.id)]),
            mensajes + 1)
        # El administrador aprueba: se crea la entrega con lo pedido
        accion = pedido.with_user(self.admin).action_aprobar()
        entrega = self.env['laroca.entrega'].browse(accion['res_id'])
        self.assertEqual(pedido.estado, 'aprobado')
        self.assertEqual(entrega.pedido_id, pedido)
        self.assertEqual(entrega.linea_ids.cantidad, 50)
        self.assertIn(self.encargado.partner_id, pedido.message_partner_ids)  # encargado avisado
        entrega.with_user(self.admin).action_confirmar()
        self.assertEqual(pedido.estado, 'en_camino')
        entrega.with_user(self.encargado)._registrar_recepcion({})
        self.assertEqual(pedido.estado, 'entregado')
        self.assertEqual(self.linea.stock_actual, 70)

    def test_pedido_enviado_no_se_modifica(self):
        pedido = self._pedido(50)
        pedido.action_enviar()
        with self.assertRaises(UserError):
            pedido.with_user(self.encargado).write({'nota': 'Mejor 100'})
        with self.assertRaises(UserError):
            pedido.linea_ids.with_user(self.encargado).write({'cantidad': 100})
        with self.assertRaises(UserError):
            pedido.with_user(self.encargado).unlink()
        # Si necesita más, hace otro pedido
        otro = self._pedido(30)
        otro.action_enviar()
        self.assertEqual(otro.estado, 'enviado')

    def test_rechazo_y_permisos(self):
        pedido = self._pedido(50)
        with self.assertRaises(AccessError):
            pedido.with_user(self.encargado).action_aprobar()
        self.assertFalse(self.env['laroca.pedido'].with_user(self.otro).search([('id', '=', pedido.id)]))
        with self.assertRaises(AccessError):
            self.env['laroca.pedido'].with_user(self.otro).create({'gasolinera_id': self.g1.id})
        pedido.action_enviar()
        rechazo = self.env['laroca.pedido.rechazo'].with_user(self.admin).create(
            {'pedido_id': pedido.id, 'motivo': 'No hay en bodega'})
        rechazo.action_confirmar()
        self.assertEqual(pedido.estado, 'rechazado')
        self.assertEqual(pedido.motivo_rechazo, 'No hay en bodega')

    def test_entrega_cancelada_devuelve_pedido(self):
        pedido = self._pedido(50)
        pedido.action_enviar()
        entrega = self.env['laroca.entrega'].browse(pedido.with_user(self.admin).action_aprobar()['res_id'])
        entrega.with_user(self.admin).action_cancelar()
        self.assertEqual(pedido.estado, 'enviado')
        self.assertFalse(pedido.entrega_id)

    def test_pedir_rapido(self):
        """Pantalla rápida: escribir 50 llaveros y enviar → pedido enviado y alerta "se realizó"."""
        form = Form(self.env['laroca.pedir'].with_user(self.encargado))
        self.assertEqual(form.gasolinera_id, self.g1)
        for indice in range(len(form.linea_ids)):
            with form.linea_ids.edit(indice) as linea:
                if linea.inventario_id == self.linea:
                    self.assertEqual(linea.stock_actual, 20)
                    linea.cantidad = 50
        form.nota = 'Vacaciones'
        resultado = form.save().action_enviar()
        self.assertEqual(resultado['tag'], 'laroca_alerta')
        self.assertEqual(resultado['params']['titulo'], '¡Tu pedido se realizó!')
        self.assertIn('next', resultado['params'])  # cierra la pantalla
        pedido = self.env['laroca.pedido'].search([('gasolinera_id', '=', self.g1.id)])
        self.assertEqual(pedido.estado, 'enviado')
        self.assertEqual(pedido.solicitante_id, self.encargado)
        self.assertEqual(pedido.linea_ids.cantidad, 50)
        self.assertEqual(pedido.nota, 'Vacaciones')
        self.assertIn(pedido.name, resultado['params']['texto'])
        # Sin cantidades: aviso y no se crea nada
        vacio = Form(self.env['laroca.pedir'].with_user(self.encargado)).save()
        self.assertEqual(vacio.action_enviar()['params']['tipo'], 'warning')
        self.assertEqual(self.env['laroca.pedido'].search_count([('gasolinera_id', '=', self.g1.id)]), 1)

    def test_interruptor_sugerido_y_quedan(self):
        """"Completar con lo sugerido" llena y vacía las cantidades al instante; al vender se ve
        cuánto queda y el aviso "¡Ya no hay más!"."""
        self._vender(15)  # queda en 5: crítico
        form = Form(self.env['laroca.pedir'].with_user(self.encargado))
        self.assertEqual(form.total_unidades, 0)
        form.completar_sugerido = True
        self.assertEqual(form.total_unidades, self.linea.cantidad_sugerida)
        form.completar_sugerido = False
        self.assertEqual(form.total_unidades, 0)
        venta = Form(self.env['laroca.vender'].with_user(self.encargado))
        for indice in range(len(venta.linea_ids)):
            with venta.linea_ids.edit(indice) as linea:
                if linea.inventario_id == self.linea:
                    linea.cantidad = 2
                    self.assertEqual(linea.quedan, 3)
                    self.assertFalse(linea.aviso)
                    linea.cantidad = 5
                    self.assertEqual(linea.quedan, 0)
                    self.assertEqual(linea.aviso, '¡Ya no hay más!')
                    linea.cantidad = 6
                    self.assertIn('No alcanza', linea.aviso)

    def test_agregar_faltantes_y_panel(self):
        self._vender(15)  # queda en 5: crítico
        panel = self.env['laroca.panel'].with_user(self.encargado).browse(
            self.env['laroca.panel'].with_user(self.encargado).action_abrir_panel()['res_id'])
        self.assertEqual(panel.kpi_ventas_hoy, 37.5)
        self.assertEqual(panel.kpi_unidades_vendidas_hoy, 15)
        # "Pedir estos productos" abre la pantalla rápida con lo sugerido ya escrito
        accion = panel.action_pedir_faltantes()
        self.assertEqual(accion['res_model'], 'laroca.pedir')
        form = Form(self.env['laroca.pedir'].with_user(self.encargado).with_context(**accion['context']))
        self.assertEqual(form.total_unidades, self.linea.cantidad_sugerida)
        wizard = form.save()
        # "Completar con lo sugerido" también funciona después de borrar la cantidad
        wizard.linea_ids.cantidad = 0
        self.assertEqual(wizard.action_completar_sugerido()['res_id'], wizard.id)
        self.assertEqual(wizard.total_unidades, self.linea.cantidad_sugerida)
        wizard.action_enviar()
        pedido = self.env['laroca.pedido'].search([('gasolinera_id', '=', self.g1.id)])
        self.assertEqual(pedido.linea_ids.product_id, self.llavero)
        panel_admin = self.env['laroca.panel'].with_user(self.admin).browse(
            self.env['laroca.panel'].with_user(self.admin).action_abrir_panel()['res_id'])
        self.assertIn(pedido, panel_admin.pedido_ids)
        self.assertGreaterEqual(panel_admin.kpi_ventas_mes, 37.5)
