from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'laroca')
class TestLarocaPanelReportes(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.laroca_porcentaje_critico = 50
        Warehouse = cls.env['stock.warehouse']
        cls.g1 = Warehouse.create({'name': 'Panel Uno', 'code': 'PA1', 'laroca_es_gasolinera': True})
        cls.g2 = Warehouse.create({'name': 'Panel Dos', 'code': 'PA2', 'laroca_es_gasolinera': True})
        cls.bodega = cls.env.company._laroca_bodega_central()
        cls.producto = cls.env['product.product'].create({
            'name': 'Llavero Panel', 'default_code': 'PAN-1', 'type': 'consu', 'is_storable': True,
            'laroca_stock_minimo': 10, 'laroca_stock_objetivo': 20})
        Quant = cls.env['stock.quant']
        Quant._update_available_quantity(cls.producto, cls.bodega.lot_stock_id, 100)
        Quant._update_available_quantity(cls.producto, cls.g1.lot_stock_id, 2)    # crítico
        Quant._update_available_quantity(cls.producto, cls.g2.lot_stock_id, 15)   # suficiente
        cls.encargado = new_test_user(
            cls.env, login='encargado_panel', groups='laroca_inventario.group_laroca_encargado',
            laroca_gasolinera_ids=[(6, 0, cls.g2.ids)])
        cls.admin = new_test_user(cls.env, login='admin_panel', groups='laroca_inventario.group_laroca_admin')

    def _panel(self, user):
        accion = self.env['laroca.panel'].with_user(user).action_abrir_panel()
        return self.env['laroca.panel'].with_user(user).browse(accion['res_id'])

    def _entregar(self):
        linea = self.env['laroca.inventario'].search([('gasolinera_id', '=', self.g1.id), ('product_id', '=', self.producto.id)])
        entrega = self.env['laroca.entrega'].browse(linea.with_user(self.admin).action_crear_entregas()['res_id'])
        entrega.with_user(self.admin).action_confirmar()
        entrega.with_user(self.admin)._registrar_recepcion({})
        return entrega

    def test_panel_administrador(self):
        panel = self._panel(self.admin)
        Inventario = self.env['laroca.inventario']
        self.assertEqual(panel.kpi_gasolineras, self.env['stock.warehouse'].search_count([('laroca_es_gasolinera', '=', True)]))
        self.assertEqual(panel.kpi_stock_bajo, Inventario.search_count([('estado', 'in', ('bajo', 'critico'))]))
        self.assertEqual(panel.kpi_criticos, Inventario.search_count([('estado', '=', 'critico')]))
        self.assertIn(self.g1, panel.gasolinera_atencion_ids)
        self.assertNotIn(self.g2, panel.gasolinera_atencion_ids)
        # Ordenadas por cantidad de críticos (de mayor a menor)
        criticos = panel.gasolinera_atencion_ids.mapped('laroca_critico_count')
        self.assertEqual(criticos, sorted(criticos, reverse=True))

    def test_panel_abastecimientos_del_mes(self):
        antes = self._panel(self.admin).kpi_abastecimientos_mes
        entrega = self._entregar()
        panel = self._panel(self.admin)
        self.assertEqual(panel.kpi_abastecimientos_mes, antes + 1)
        self.assertGreaterEqual(panel.kpi_unidades_mes, entrega.total_entregado)
        # Una entrega del mes pasado no cuenta
        entrega.fecha_entrega = fields.Datetime.now() - timedelta(days=40)
        self.assertEqual(self._panel(self.admin).kpi_abastecimientos_mes, antes)

    def test_panel_encargado_limitado(self):
        panel = self._panel(self.encargado)
        self.assertEqual(panel.kpi_gasolineras, 1)
        self.assertNotIn(self.g1, panel.gasolinera_atencion_ids)
        self.assertEqual(panel.nombre_usuario, self.encargado.name.split()[0])

    def test_panel_distinto_por_rol(self):
        """El administrador y el encargado abren pantallas distintas del panel."""
        vista_admin = self.env.ref('laroca_inventario.view_laroca_panel_form')
        vista_encargado = self.env.ref('laroca_inventario.view_laroca_panel_encargado_form')
        accion = self.env['laroca.panel'].with_user(self.admin).action_abrir_panel()
        self.assertEqual(accion['views'][0][0], vista_admin.id)
        self.assertEqual(accion['name'], 'Panel del administrador')
        accion = self.env['laroca.panel'].with_user(self.encargado).action_abrir_panel()
        self.assertEqual(accion['views'][0][0], vista_encargado.id)
        self.assertEqual(accion['name'], 'Mi gasolinera')

    def test_panel_encargado_datos_propios(self):
        panel = self._panel(self.encargado)
        self.assertFalse(panel.es_admin)
        self.assertEqual(panel.nombre_gasolineras, self.g2.name)
        self.assertEqual(panel.kpi_suficientes, 1)
        self.assertFalse(panel.producto_pendiente_ids)  # g2 está bien abastecida
        self.assertFalse(panel.alerta_reciente_ids)
        self.assertEqual(panel.kpi_valor_bodega, 0)
        # Si baja el stock de su gasolinera, el producto aparece en "se están acabando"
        self.env['stock.quant']._update_available_quantity(self.producto, self.g2.lot_stock_id, -10)
        panel = self._panel(self.encargado)
        self.assertEqual(panel.producto_pendiente_ids.gasolinera_id, self.g2)
        self.assertTrue(panel.ultimo_conteo)

    def test_panel_administrador_seguimiento(self):
        panel = self._panel(self.admin)
        self.assertTrue(panel.es_admin)
        self.assertIn(self.g1, panel.gasolinera_seguimiento_ids)
        self.assertIn(self.g2, panel.gasolinera_seguimiento_ids)
        self.assertFalse(panel.producto_pendiente_ids)
        # Ninguna línea de las gasolineras de prueba se actualizó a mano: cuentan como "sin actualizar"
        sin_conteo = panel.action_ver_sin_conteo()
        self.assertEqual(panel.kpi_sin_conteo, len(sin_conteo['domain'][0][2]))
        datos = self.env['laroca.panel'].with_user(self.encargado).get_datos_graficos()
        self.assertEqual(sum(datos['totales'].values()), 1)

    def test_acciones_del_panel(self):
        panel = self._panel(self.admin)
        for metodo in ['action_ver_gasolineras', 'action_ver_productos', 'action_ver_stock_bajo', 'action_ver_criticos',
                       'action_ver_abastecimientos_mes', 'action_ver_en_camino', 'action_ver_alertas',
                       'action_ver_inventario', 'action_reportes', 'action_ver_suficientes', 'action_ver_bajos',
                       'action_ver_entregas', 'action_ver_usuarios', 'action_importar', 'action_ver_sin_conteo',
                       'action_vender', 'action_pedir', 'action_pedir_faltantes', 'action_ver_pedidos',
                       'action_ver_ventas', 'action_ver_ventas_hoy']:
            with self.subTest(metodo=metodo):
                self.assertIn('res_model', getattr(panel, metodo)())

    def _html(self, user, **vals):
        reporte = self.env['laroca.reporte'].with_user(user).create(vals)
        reporte.action_imprimir()  # valida parámetros
        html, _tipo = self.env['ir.actions.report'].with_user(user)._render_qweb_html(
            'laroca_inventario.report_laroca_general', reporte.ids)
        return html.decode()

    def test_reporte_stock_bajo(self):
        html = self._html(self.admin, tipo='stock_bajo', gasolinera_ids=[(6, 0, (self.g1 | self.g2).ids)])
        self.assertIn('Panel Uno', html)
        self.assertIn('Llavero Panel', html)
        self.assertNotIn('Panel Dos', html)  # sin pendientes: no aparece

    def test_reporte_inventario_encargado(self):
        html = self._html(self.encargado, tipo='inventario')
        self.assertIn('Panel Dos', html)
        self.assertNotIn('Panel Uno', html)  # no es su gasolinera

    def test_reporte_abastecimientos(self):
        self._entregar()
        hoy = fields.Date.context_today(self.env['laroca.reporte'])
        html = self._html(self.admin, tipo='abastecimientos', fecha_desde=hoy - timedelta(days=1), fecha_hasta=hoy)
        self.assertIn('Panel Uno', html)
        self.assertIn('Llavero Panel', html)
        html = self._html(self.admin, tipo='abastecimientos',
                          fecha_desde=hoy - timedelta(days=60), fecha_hasta=hoy - timedelta(days=30))
        self.assertIn('No hubo entregas', html)

    def test_reporte_fechas_invertidas(self):
        hoy = fields.Date.context_today(self.env['laroca.reporte'])
        reporte = self.env['laroca.reporte'].create(
            {'tipo': 'abastecimientos', 'fecha_desde': hoy, 'fecha_hasta': hoy - timedelta(days=5)})
        with self.assertRaises(UserError):
            reporte.action_imprimir()

    def test_valor_del_inventario(self):
        self.producto.standard_price = 2.5
        linea = self.env['laroca.inventario'].search([('gasolinera_id', '=', self.g2.id), ('product_id', '=', self.producto.id)])
        self.assertEqual(linea.valor_stock, 15 * 2.5)
        self.assertEqual(self.g2.laroca_valor_stock, 15 * 2.5)
        entrega = self._entregar()  # 18 unidades a la gasolinera 1
        self.assertEqual(entrega.valor_total, entrega.total_entregado * 2.5)
        panel = self._panel(self.admin)
        self.assertGreaterEqual(panel.kpi_valor_mes, entrega.valor_total)
        self.assertGreater(panel.kpi_valor_bodega, 0)
        self.assertEqual(self._panel(self.encargado).kpi_valor_bodega, 0)  # el encargado no ve la bodega

    def test_datos_graficos(self):
        self._entregar()
        datos = self.env['laroca.panel'].with_user(self.admin).get_datos_graficos()
        indice = datos['estados']['ids'].index(self.g1.id)
        series = {s['key']: s['data'][indice] for s in datos['estados']['series']}
        self.assertEqual(sum(series.values()), self.env['laroca.inventario'].search_count([('gasolinera_id', '=', self.g1.id)]))
        self.assertEqual(len(datos['entregas']['labels']), 6)
        self.assertGreater(datos['entregas']['unidades'][-1], 0)  # mes actual
        datos_enc = self.env['laroca.panel'].with_user(self.encargado).get_datos_graficos()
        self.assertEqual(datos_enc['estados']['ids'], self.g2.ids)
        self.assertFalse(datos_enc['es_admin'])
