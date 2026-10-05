from odoo import _, fields, models
from odoo.exceptions import UserError


class LarocaCambiarClave(models.TransientModel):
    """El administrador asigna una contraseña nueva a un usuario (por ejemplo, si la olvidó)."""
    _name = 'laroca.cambiar.clave'
    _description = 'Cambiar contraseña de un usuario'

    user_id = fields.Many2one('res.users', 'Usuario', required=True, readonly=True)
    clave = fields.Char('Nueva contraseña', required=True)
    confirmar = fields.Char('Repetir contraseña', required=True)

    def action_confirmar(self):
        self.ensure_one()
        if self.clave != self.confirmar:
            raise UserError(_('Las dos contraseñas no coinciden. Escribilas de nuevo.'))
        self.user_id._laroca_cambiar_clave(self.clave)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Contraseña actualizada'),
                'message': _('Comunicale la nueva contraseña a %s. Si tenía la sesión abierta, '
                             'deberá volver a entrar.', self.user_id.name),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
