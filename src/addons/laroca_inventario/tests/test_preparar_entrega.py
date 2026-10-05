import base64
import io
import zipfile

from odoo.exceptions import AccessError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'laroca')
class TestLarocaPrepararEntrega(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.laroca_porcentaje_critico = 50
        cls.g1 = cls.env['stock.warehouse'].create({
            'name': 'Prep Uno', 'code': 'PR1', 'laroca_es_gasolinera': True,
            'laroca_direccion': 'Carretera al Puerto km 5', 'laroca_municipio': 'La Libertad'})
        cls.bodega = cls.env.company._laroca_bodega_central()
        Product = cls.env['product.product']
        cls.llavero = Product.create({'name': 'Llavero Prep', 'default_code': 'PRE-1', 'type': 'consu',
                                      'is_storable': True, 'laroca_stock_minimo': 10, 'laroca_stock_objetivo': 20})
        cls.gorra = Product.create({'name': 'Gorra Prep', 'default_code': 'PRE-2', 'type': 'consu',
                                    'is_storable': True, 'laroca_stock_minimo': 5, 'laroca_stock_objetivo': 10})
        Quant = cls.env['stock.quant']
        Quant._update_available_quantity(cls.llavero, cls.bodega.lot_stock_id, 100)
        Quant._update_available_quantity(cls.gorra, cls.bodega.lot_stock_id, 30)
        Quant._update_available_quantity(cls.gorra, cls.g1.lot_stock_id, 8)  # llavero en 0: crítico
        cls.encargado = new_test_user(cls.env, login='enc_prep', groups='laroca_inventario.group_laroca_encargado',
                                      laroca_gasolinera_ids=[(6, 0, cls.g1.ids)])
        cls.admin = new_test_user(cls.env, login='adm_prep', groups='laroca_inventario.group_laroca_admin')

    def _form(self, **contexto):
        form = Form(self.env['laroca.preparar.entrega'].with_user(self.admin).with_context(**contexto))
        if not form.gasolinera_id:
            form.gasolinera_id = self.g1
        return form

    def _poner(self, form, cantidades):
        for indice in range(len(form.linea_ids)):
            with form.linea_ids.edit(indice) as linea:
                producto = linea.inventario_id.product_id
                if producto in cantidades:
                    linea.cantidad = cantidades[producto]

    def test_preparar_y_generar_pdf(self):
        form = self._form()
        self.assertIn('Carretera al Puerto', form.lugar)
        self._poner(form, {self.llavero: 50, self.gorra: 6})
        self.assertEqual(form.total_unidades, 56)
        self.assertIn('50 Llavero Prep', form.resumen)
        accion = form.save().action_generar_pdf()
        # El diseño de documentos ya viene configurado: imprime directo (sin asistente ni error de acceso)
        reporte = accion
        self.assertEqual(reporte['type'], 'ir.actions.report')
        self.assertEqual(reporte['report_name'], 'laroca_inventario.report_laroca_entrega')
        entrega = self.env['laroca.entrega'].search([('gasolinera_id', '=', self.g1.id)])
        self.assertEqual(entrega.estado, 'en_camino')  # "Enviar ahora" viene marcado
        self.assertEqual(sorted(entrega.linea_ids.mapped('cantidad')), [6, 50])
        html = self.env['ir.actions.report']._render_qweb_html(
            'laroca_inventario.report_laroca_entrega', entrega.ids)[0].decode()
        for texto in ('Prep Uno', 'Carretera al Puerto km 5', 'envío del administrador', '50 Llavero Prep'):
            self.assertIn(texto, html)

    def test_envio_extra_genera_excel_en_borrador(self):
        """Envío propio del administrador ("llaveros extra"), sin pedido, guardado en borrador."""
        form = self._form()
        self._poner(form, {self.llavero: 40})
        form.enviar = False
        accion = form.save().action_generar_excel()
        self.assertEqual(accion['type'], 'ir.actions.act_url')
        entrega = self.env['laroca.entrega'].search([('gasolinera_id', '=', self.g1.id)])
        self.assertEqual(entrega.estado, 'borrador')
        # Queda en Pedidos como "Envío del administrador", con su lista
        self.assertEqual(entrega.pedido_id.origen, 'administrador')
        self.assertEqual(entrega.pedido_id.linea_ids.cantidad, 40)
        self.assertIn(entrega.pedido_id, self.env['laroca.pedido'].with_user(self.encargado).search([]))
        adjunto = self.env['ir.attachment'].browse(int(accion['url'].split('/')[3].split('?')[0]))
        contenido = zipfile.ZipFile(io.BytesIO(base64.b64decode(adjunto.datas))).read('xl/sharedStrings.xml').decode()
        for texto in ('Prep Uno', 'Carretera al Puerto', 'envío del administrador', 'Llavero Prep'):
            self.assertIn(texto, contenido)

    def test_pedido_se_atiende_como_antes(self):
        """Los pedidos de los encargados: Aprobar → entrega con lo pedido; su hoja muestra el pedido."""
        pedido = self.env['laroca.pedido'].with_user(self.encargado).create({
            'gasolinera_id': self.g1.id, 'linea_ids': [(0, 0, {'product_id': self.llavero.id, 'cantidad': 30})]})
        pedido.action_enviar()
        entrega = self.env['laroca.entrega'].browse(pedido.with_user(self.admin).action_aprobar()['res_id'])
        self.assertEqual(entrega.linea_ids.cantidad, 30)
        self.assertEqual(pedido.estado, 'aprobado')
        entrega.with_user(self.admin).action_confirmar()
        self.assertEqual(pedido.estado, 'en_camino')
        html = self.env['ir.actions.report']._render_qweb_html(
            'laroca_inventario.report_laroca_entrega', entrega.ids)[0].decode()
        self.assertIn(pedido.name, html)

    def test_no_llevar_mas_que_bodega(self):
        wizard = self._form().save()
        wizard.linea_ids.filtered(lambda l: l.product_id == self.gorra).cantidad = 40  # en bodega hay 30
        resultado = wizard.action_generar_pdf()
        self.assertEqual(resultado['params']['tipo'], 'error')
        self.assertIn('en bodega hay 30', resultado['params']['detalle'][0])
        self.assertFalse(self.env['laroca.entrega'].search([('gasolinera_id', '=', self.g1.id)]))

    def test_sugerido_vacio_y_permisos(self):
        form = self._form()
        form.completar_sugerido = True
        self.assertEqual(form.total_unidades, 20)  # llavero crítico: sugerido 20 (hay 100 en bodega)
        form.completar_sugerido = False
        self.assertEqual(form.total_unidades, 0)
        resultado = form.save().action_generar_pdf()
        self.assertEqual(resultado['tag'], 'laroca_alerta')  # sin productos: aviso, sin entrega
        self.assertFalse(self.env['laroca.entrega'].search([('gasolinera_id', '=', self.g1.id)]))
        with self.assertRaises(AccessError):
            self.env['laroca.preparar.entrega'].with_user(self.encargado).create({'gasolinera_id': self.g1.id})

    def test_entregado_rapido(self):
        """Envío del administrador: el encargado toca "Entregado ✓" y todo queda recibido."""
        form = self._form()
        self._poner(form, {self.llavero: 10})
        form.save().action_generar_pdf()
        entrega = self.env['laroca.entrega'].search([('gasolinera_id', '=', self.g1.id)])
        self.assertEqual(entrega.estado, 'en_camino')
        resultado = entrega.with_user(self.encargado).action_marcar_entregada()
        self.assertEqual(resultado['params']['titulo'], '¡Entregado!')
        self.assertEqual(entrega.estado, 'entregada')
        self.assertEqual(entrega.pedido_id.estado, 'entregado')
        linea = self.env['laroca.inventario'].search([('gasolinera_id', '=', self.g1.id), ('product_id', '=', self.llavero.id)])
        self.assertEqual(linea.stock_actual, 10)
