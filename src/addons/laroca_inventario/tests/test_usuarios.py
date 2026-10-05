from ast import literal_eval

from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'laroca')
class TestLarocaUsuarios(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.g1 = cls.env['stock.warehouse'].create({'name': 'Usuarios Uno', 'code': 'US1', 'laroca_es_gasolinera': True})
        cls.g2 = cls.env['stock.warehouse'].create({'name': 'Usuarios Dos', 'code': 'US2', 'laroca_es_gasolinera': True})
        cls.admin = new_test_user(cls.env, login='admin_usuarios', groups='laroca_inventario.group_laroca_admin')
        cls.encargado = new_test_user(cls.env, login='enc_usuarios', groups='laroca_inventario.group_laroca_encargado',
                                      laroca_gasolinera_ids=[(6, 0, cls.g1.ids)])
        cls.vista = 'laroca_inventario.view_laroca_usuario_form'
        cls.env['product.product'].create({'name': 'Producto usuarios', 'type': 'consu', 'is_storable': True})

    def _puede_entrar(self, user, clave):
        try:
            self.env['res.users'].with_user(user)._check_credentials(
                {'login': user.login, 'password': clave, 'type': 'password'}, {'interactive': False})
            return True
        except AccessDenied:
            return False

    def _crear_encargado(self):
        form = Form(self.env['res.users'].with_user(self.admin), view=self.vista)
        form.name = 'Ana Gómez'
        form.login = 'ana.gomez'
        form.laroca_clave = 'ClaveSegura1'
        form.laroca_rol = 'encargado'
        form.laroca_gasolinera_ids.add(self.g2)
        return form.save()

    def test_admin_crea_encargado_que_puede_entrar(self):
        usuario = self._crear_encargado()
        self.assertEqual(usuario.laroca_rol, 'encargado')
        self.assertTrue(usuario.has_group('base.group_user'))
        self.assertTrue(self._puede_entrar(usuario, 'ClaveSegura1'))
        self.assertFalse(self._puede_entrar(usuario, 'otra-clave'))
        lineas = self.env['laroca.inventario'].with_user(usuario).search([])
        self.assertEqual(lineas.gasolinera_id, self.g2)  # solo su gasolinera

    def test_cambiar_contrasena(self):
        usuario = self._crear_encargado()
        wizard = self.env['laroca.cambiar.clave'].with_user(self.admin).create(
            {'user_id': usuario.id, 'clave': 'NuevaClave22', 'confirmar': 'NuevaClave22'})
        wizard.action_confirmar()
        self.assertTrue(self._puede_entrar(usuario, 'NuevaClave22'))
        self.assertFalse(self._puede_entrar(usuario, 'ClaveSegura1'))

    def test_validaciones_de_contrasena(self):
        Wizard = self.env['laroca.cambiar.clave'].with_user(self.admin)
        with self.assertRaises(UserError):  # no coinciden
            Wizard.create({'user_id': self.encargado.id, 'clave': 'Abcdefgh1', 'confirmar': 'Abcdefgh2'}).action_confirmar()
        with self.assertRaises(UserError):  # muy corta
            Wizard.create({'user_id': self.encargado.id, 'clave': 'corta', 'confirmar': 'corta'}).action_confirmar()
        with self.assertRaises(UserError):  # la propia se cambia desde "Mi perfil"
            Wizard.create({'user_id': self.admin.id, 'clave': 'Abcdefgh1', 'confirmar': 'Abcdefgh1'}).action_confirmar()

    def test_cambiar_rol_y_datos(self):
        form = Form(self.encargado.with_user(self.admin), view=self.vista)
        form.laroca_rol = 'admin'
        form.email = 'nuevo@laroca.test'
        usuario = form.save()
        self.assertTrue(usuario.has_group('laroca_inventario.group_laroca_admin'))
        self.assertTrue(usuario.has_group('stock.group_stock_manager'))
        self.assertEqual(usuario.email, 'nuevo@laroca.test')
        # Vuelve a encargado: pierde los permisos de administrador
        form = Form(usuario.with_user(self.admin), view=self.vista)
        form.laroca_rol = 'encargado'
        form.save()
        self.assertFalse(usuario.has_group('laroca_inventario.group_laroca_admin'))
        self.assertFalse(usuario.has_group('stock.group_stock_manager'))
        self.assertFalse(usuario.has_group('base.group_erp_manager'))
        self.assertEqual(self.env['laroca.inventario'].with_user(usuario).search([]).gasolinera_id, self.g1)

    def test_desactivar_impide_entrar(self):
        usuario = self._crear_encargado()
        usuario.with_user(self.admin).action_archive()
        self.assertFalse(usuario.active)
        # El inicio de sesión de Odoo solo busca usuarios activos: ya no lo encuentra.
        self.assertFalse(self.env['res.users'].search([('login', '=', 'ana.gomez')]))
        usuario.with_user(self.admin).action_unarchive()
        self.assertEqual(self.env['res.users'].search([('login', '=', 'ana.gomez')]), usuario)

    def test_protecciones(self):
        with self.assertRaises(AccessError):  # el encargado no gestiona usuarios
            self.encargado.with_user(self.encargado).action_laroca_cambiar_clave()
        with self.assertRaises(AccessError):  # el usuario técnico "admin" no se toca
            self.env.ref('base.user_admin').with_user(self.admin)._laroca_cambiar_clave('Hackeada123')
        with self.assertRaises(UserError):  # no puede quitarse su propio rol
            self.admin.with_user(self.admin).laroca_rol = 'encargado'

    def test_lista_no_muestra_usuarios_tecnicos(self):
        accion = self.env['ir.actions.actions']._for_xml_id('laroca_inventario.action_laroca_usuarios')
        usuarios = self.env['res.users'].with_user(self.admin).search(literal_eval(accion['domain']))
        self.assertIn(self.encargado, usuarios)
        self.assertNotIn(self.env.ref('base.user_admin'), usuarios)
        self.assertEqual(self.env['res.users'].search([('laroca_rol', '=', 'admin'), ('id', '=', self.admin.id)]), self.admin)
