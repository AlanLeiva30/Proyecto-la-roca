from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    """Parámetros de abastecimiento de Grupo La Roca (uno por empresa)."""
    _inherit = 'res.company'

    laroca_porcentaje_critico = fields.Integer(
        'Umbral crítico (%)', default=50,
        help='Un producto está en estado CRÍTICO cuando su stock es menor o igual a este '
             'porcentaje del stock mínimo. Ej.: mínimo 10 y umbral 50 % → crítico con 5 o menos.')
    laroca_enviar_correos = fields.Boolean(
        'Enviar alertas por correo', default=True,
        help='Además del canal de Conversaciones, envía las alertas y el resumen diario por '
             'correo a los administradores (requiere un servidor de correo configurado).')
    laroca_bodega_central_id = fields.Many2one(
        'stock.warehouse', 'Bodega central',
        domain="[('laroca_es_gasolinera', '=', False), ('company_id', '=', id)]",
        help='Almacén desde donde se abastece a las gasolineras.')

    @api.constrains('laroca_porcentaje_critico')
    def _check_laroca_porcentaje_critico(self):
        for company in self:
            if not 1 <= company.laroca_porcentaje_critico <= 99:
                raise ValidationError(_('El umbral crítico debe estar entre 1 y 99 %.'))

    def _laroca_bodega_central(self):
        """Bodega central configurada o, si no hay, el primer almacén que no es gasolinera."""
        self.ensure_one()
        return self.sudo().laroca_bodega_central_id or self.env['stock.warehouse'].sudo().search(
            [('company_id', '=', self.id), ('laroca_es_gasolinera', '=', False)], limit=1)

    def write(self, vals):
        res = super().write(vals)
        if 'laroca_porcentaje_critico' in vals:
            # Los estados se recalculan solos; aquí se abren o cierran las alertas que correspondan.
            lineas = self.env['laroca.inventario'].sudo().search([('company_id', 'in', self.ids)])
            lineas._sincronizar_alertas()
        return res

    def action_laroca_abrir_parametros(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Parámetros de abastecimiento',
            'res_model': 'res.company',
            'res_id': self.env.company.id,
            'view_mode': 'form',
            'views': [(self.env.ref('laroca_inventario.view_laroca_parametros_form').id, 'form')],
            'target': 'current',
        }

    @api.model
    def _laroca_configurar_diseno_documentos(self):
        """Diseño de los PDF ya elegido: si falta, Odoo abre un asistente al imprimir que solo
        puede usar el usuario técnico, y el administrador de La Roca vería un error de acceso."""
        estandar = self.env.ref('web.external_layout_standard', raise_if_not_found=False)
        if estandar:
            self.sudo().search([('external_report_layout_id', '=', False)]).write(
                {'external_report_layout_id': estandar.id})
