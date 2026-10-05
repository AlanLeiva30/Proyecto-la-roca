from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

ROLES = [('encargado', 'Encargado de gasolinera'), ('admin', 'Administrador')]
LARGO_MINIMO_CLAVE = 8


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Relación usuario <-> gasolineras. La misma tabla se usa desde stock.warehouse
    # (campo laroca_encargado_ids), así se puede asignar desde cualquiera de los dos lados.
    laroca_gasolinera_ids = fields.Many2many(
        'stock.warehouse', 'laroca_gasolinera_encargado_rel', 'user_id', 'warehouse_id',
        string='Gasolineras asignadas',
        domain=[('laroca_es_gasolinera', '=', True)],
        help='Gasolineras cuyo inventario puede consultar y actualizar este usuario '
             'cuando tiene el rol "Encargado de gasolinera".',
    )
    # Rol simplificado: traduce los grupos de Odoo a una sola opción fácil de entender.
    laroca_rol = fields.Selection(
        ROLES, string='Rol', compute='_compute_laroca_rol', inverse='_inverse_laroca_rol', search='_search_laroca_rol',
        help='Encargado: ve y actualiza solo sus gasolineras. Administrador: ve todo y configura el sistema.')
    # Contraseña inicial (solo al crear el usuario desde la pantalla de La Roca).
    laroca_clave = fields.Char(
        'Contraseña', compute='_compute_laroca_clave', inverse='_inverse_laroca_clave',
        help=f'Mínimo {LARGO_MINIMO_CLAVE} caracteres. Se guarda cifrada; nadie puede verla después.')

    # ------------------------------------------------------------------
    # Rol
    # ------------------------------------------------------------------
    @api.depends('groups_id')
    def _compute_laroca_rol(self):
        admin = self.env.ref('laroca_inventario.group_laroca_admin')
        encargado = self.env.ref('laroca_inventario.group_laroca_encargado')
        for user in self:
            grupos = user.groups_id
            user.laroca_rol = 'admin' if admin in grupos else 'encargado' if encargado in grupos else False

    def _search_laroca_rol(self, operator, value):
        if operator != '=' or value not in ('admin', 'encargado'):
            raise UserError(_('Búsqueda por rol no soportada.'))
        admin = self.env.ref('laroca_inventario.group_laroca_admin').id
        if value == 'admin':
            return [('groups_id', 'in', [admin])]
        return [('groups_id', 'in', [self.env.ref('laroca_inventario.group_laroca_encargado').id]),
                ('groups_id', 'not in', [admin])]

    def _inverse_laroca_rol(self):
        self._laroca_check_puede_gestionar()
        ref = self.env.ref
        for user in self:
            if not user.laroca_rol:
                continue
            if user == self.env.user and user.laroca_rol != 'admin' and not self.env.su:
                raise UserError(_('No podés quitarte a vos mismo el rol de administrador.'))
            if user.laroca_rol == 'admin':
                comandos = [(4, ref('base.group_user').id), (4, ref('laroca_inventario.group_laroca_admin').id)]
            else:
                # Al bajar de administrador se quitan también los permisos que ese rol agregaba.
                comandos = [(4, ref('base.group_user').id), (4, ref('laroca_inventario.group_laroca_encargado').id),
                            (3, ref('laroca_inventario.group_laroca_admin').id),
                            (3, ref('stock.group_stock_manager').id), (3, ref('base.group_erp_manager').id)]
            user.write({'groups_id': comandos})
        self.env.registry.clear_cache()

    # ------------------------------------------------------------------
    # Contraseñas
    # ------------------------------------------------------------------
    def _compute_laroca_clave(self):
        for user in self:
            user.laroca_clave = False

    def _inverse_laroca_clave(self):
        for user in self.filtered('laroca_clave'):
            user._laroca_cambiar_clave(user.laroca_clave)

    def _laroca_cambiar_clave(self, clave):
        """Cambia la contraseña de otro usuario (administrador de La Roca)."""
        self.ensure_one()
        self._laroca_check_puede_gestionar()
        if self == self.env.user and not self.env.su:
            raise UserError(_('Para cambiar tu propia contraseña usá tu menú de usuario '
                              '(arriba a la derecha) → Mi perfil → Cambiar contraseña.'))
        if not clave or len(clave) < LARGO_MINIMO_CLAVE:
            raise UserError(_('La contraseña debe tener al menos %s caracteres.', LARGO_MINIMO_CLAVE))
        # sudo: el cambio ya fue autorizado arriba; Odoo la guarda cifrada y cierra las sesiones abiertas.
        self.sudo().password = clave

    def action_laroca_cambiar_clave(self):
        self.ensure_one()
        self._laroca_check_puede_gestionar()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cambiar contraseña de %s', self.name),
            'res_model': 'laroca.cambiar.clave',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_user_id': self.id},
        }

    # ------------------------------------------------------------------
    # Permisos para gestionar usuarios
    # ------------------------------------------------------------------
    def _laroca_check_puede_gestionar(self):
        """Solo el administrador de La Roca gestiona usuarios, y nunca a los administradores
        técnicos de Odoo (usuario "admin"), salvo que lo haga otro administrador técnico."""
        if self.env.su:
            return
        if not self.env.user.has_group('laroca_inventario.group_laroca_admin'):
            raise AccessError(_('Solo el administrador puede gestionar usuarios.'))
        if not self.env.user.has_group('base.group_system'):
            sistema = self.env.ref('base.group_system')
            if any(sistema in user.sudo().groups_id for user in self):
                raise AccessError(_('Este es un usuario técnico de Odoo; solo puede modificarlo el usuario técnico "admin".'))

    # ------------------------------------------------------------------
    # Caché de reglas al cambiar gasolineras
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        if any('laroca_gasolinera_ids' in vals for vals in vals_list):
            users._laroca_tras_cambiar_gasolineras()
        return users

    def write(self, vals):
        res = super().write(vals)
        if 'laroca_gasolinera_ids' in vals:
            self._laroca_tras_cambiar_gasolineras()
        return res

    def _laroca_tras_cambiar_gasolineras(self):
        """Las reglas de acceso (ir.rule) se guardan en caché por usuario.
        Al cambiar las gasolineras asignadas hay que limpiar esa caché para que
        el nuevo acceso se aplique de inmediato."""
        self.env.registry.clear_cache()
