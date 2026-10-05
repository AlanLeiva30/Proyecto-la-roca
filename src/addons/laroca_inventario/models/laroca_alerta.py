from collections import defaultdict

from markupsafe import Markup

from odoo import api, fields, models

NIVELES = [('bajo', 'Bajo'), ('critico', 'Crítico')]


class LarocaAlerta(models.Model):
    """Alerta de abastecimiento.

    Se crea automáticamente cuando el stock de un producto en una gasolinera queda por
    debajo del mínimo, sube de nivel si pasa a crítico y se cierra sola cuando el stock
    vuelve a ser suficiente. Cada alerta nueva se notifica en el canal
    "Alertas de abastecimiento" (Conversaciones) de los administradores.
    """
    _name = 'laroca.alerta'
    _description = 'Alerta de abastecimiento'
    _inherit = ['mail.thread']
    _order = 'estado, nivel desc, fecha_alerta desc'

    name = fields.Char('Referencia', required=True, readonly=True, copy=False, default='Nueva')
    linea_id = fields.Many2one('laroca.inventario', 'Línea de inventario', required=True,
                               ondelete='cascade', index=True, readonly=True)
    gasolinera_id = fields.Many2one(related='linea_id.gasolinera_id', store=True, index=True)
    product_id = fields.Many2one(related='linea_id.product_id', store=True, index=True)
    categ_id = fields.Many2one(related='linea_id.categ_id', store=True)
    company_id = fields.Many2one(related='linea_id.company_id', store=True)
    nivel = fields.Selection(NIVELES, 'Nivel', required=True, readonly=True, tracking=True)
    estado = fields.Selection([
        ('abierta', 'Abierta'),
        ('en_proceso', 'En proceso'),
        ('resuelta', 'Resuelta'),
    ], 'Estado', default='abierta', required=True, readonly=True, tracking=True, index=True,
        help='Abierta: pendiente de abastecer. En proceso: hay una entrega en camino. '
             'Resuelta: el stock volvió a ser suficiente.')
    entrega_id = fields.Many2one('laroca.entrega', 'Entrega', readonly=True, tracking=True,
                                 help='Entrega que está atendiendo (o atendió) esta alerta.')
    fecha_alerta = fields.Datetime('Fecha de la alerta', default=fields.Datetime.now, readonly=True)
    fecha_resolucion = fields.Datetime('Fecha de resolución', readonly=True)
    stock_al_alertar = fields.Float('Stock al alertar', digits='Product Unit of Measure', readonly=True)
    stock_minimo_al_alertar = fields.Float('Mínimo al alertar', digits='Product Unit of Measure', readonly=True)
    # Valores actuales de la línea (cambian con el inventario)
    stock_actual = fields.Float(related='linea_id.stock_actual')
    stock_minimo = fields.Float(related='linea_id.stock_minimo')
    cantidad_sugerida = fields.Float(related='linea_id.cantidad_sugerida')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nueva') == 'Nueva':
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code('laroca.alerta') or 'Nueva'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Notificaciones
    # ------------------------------------------------------------------
    @api.model
    def _canal_alertas(self):
        return self.env.ref('laroca_inventario.canal_alertas_abastecimiento', raise_if_not_found=False)

    @api.model
    def _publicar_en_canal(self, cuerpo):
        canal = self._canal_alertas()
        if canal:
            canal.sudo().message_post(
                body=cuerpo, message_type='comment', subtype_xmlid='mail.mt_comment',
                author_id=self.env.ref('base.partner_root').id)

    @api.model
    def _enviar_correo_admins(self, asunto, cuerpo, accion='laroca_inventario.action_laroca_alertas',
                              boton='Ver alertas en el sistema'):
        """Envía un correo a los administradores con correo electrónico.
        Odoo lo pone en la cola de envío (mail.mail) y lo despacha en segundo plano."""
        company = self.env.company
        if not company.laroca_enviar_correos:
            return self.env['mail.mail']
        admins = self.env.ref('laroca_inventario.group_laroca_admin').sudo().users.filtered(
            lambda u: u.email and u.active and not u.share and u != self.env.ref('base.user_root'))
        if not admins:
            return self.env['mail.mail']
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        html = Markup(
            '<div style="font-family: Arial, sans-serif; font-size: 14px;">'
            '<h2 style="color:#0B3D91; margin-bottom:8px;">Grupo La Roca · %s</h2>%s'
            '<p style="margin-top:16px;"><a href="%s/odoo/action-%s" '
            'style="background:#0B3D91;color:#fff;padding:8px 14px;border-radius:4px;text-decoration:none;">'
            '%s</a></p>'
            '<p style="color:#888;font-size:12px;">Correo automático del sistema de inventario. '
            'Se puede desactivar en La Roca → Configuración → Parámetros.</p></div>') % (asunto, cuerpo, url, accion, boton)
        return self.env['mail.mail'].sudo().create({
            'subject': f'[La Roca] {asunto}',
            'body_html': html,
            'email_from': company.email_formatted or self.env.user.email_formatted,
            'email_to': ','.join(admins.mapped('email_formatted')),
            'auto_delete': False,
        })

    def _notificar(self, titulo):
        """Publica un mensaje por gasolinera con las alertas recibidas."""
        por_gasolinera = defaultdict(lambda: self.browse())
        for alerta in self:
            por_gasolinera[alerta.gasolinera_id] |= alerta
        for gasolinera, alertas in por_gasolinera.items():
            filas = Markup('').join(
                Markup('<li>%s %s: <b>%s</b> de mínimo %s → sugerido llevar <b>%s</b> (%s)</li>') % (
                    '🔴' if a.nivel == 'critico' else '🟠',
                    a.product_id.display_name,
                    _fmt(a.stock_actual), _fmt(a.stock_minimo), _fmt(a.cantidad_sugerida),
                    a._get_html_link(a.name),
                ) for a in alertas)
            self._publicar_en_canal(
                Markup('<p><b>%s — %s</b></p><ul>%s</ul>') % (titulo, gasolinera.name, filas))
            self._enviar_correo_admins(f'{titulo} — {gasolinera.name}', Markup('<ul>%s</ul>') % filas)

    # ------------------------------------------------------------------
    # Tareas programadas (ir.cron)
    # ------------------------------------------------------------------
    @api.model
    def _cron_sincronizar_alertas(self):
        """Respaldo: revisa todas las líneas por si algún cambio no generó su alerta."""
        self.env['laroca.inventario'].sudo().search([])._sincronizar_alertas()

    @api.model
    def _cron_resumen_diario(self):
        """Publica cada mañana el resumen de gasolineras que requieren atención."""
        grupos = self.sudo()._read_group(
            [('estado', 'in', ('abierta', 'en_proceso'))], ['gasolinera_id', 'nivel'], ['__count'])
        if not grupos:
            self._publicar_en_canal(Markup('<p><b>Resumen diario:</b> ✅ todas las gasolineras tienen stock suficiente.</p>'))
            return
        conteo = defaultdict(lambda: {'critico': 0, 'bajo': 0})
        for gasolinera, nivel, total in grupos:
            conteo[gasolinera][nivel] = total
        ordenadas = sorted(conteo.items(), key=lambda item: (-item[1]['critico'], -item[1]['bajo']))
        filas = Markup('').join(
            Markup('<li><b>%s</b>: %s crítico(s), %s bajo(s)</li>') % (g.name, c['critico'], c['bajo'])
            for g, c in ordenadas)
        cuerpo = Markup('<p><b>Resumen diario de abastecimiento</b> — gasolineras que requieren atención:</p><ul>%s</ul>') % filas
        self._publicar_en_canal(cuerpo)
        self._enviar_correo_admins('Resumen diario de abastecimiento', cuerpo)


def _fmt(cantidad):
    return f'{cantidad:g}'
