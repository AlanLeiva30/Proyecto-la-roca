from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..utils import accion_alerta, remitente_sistema

ESTADOS_PEDIDO = [
    ('borrador', 'Borrador'),
    ('enviado', 'Enviado'),
    ('aprobado', 'En preparación'),
    ('en_camino', 'En camino'),
    ('entregado', 'Entregado'),
    ('rechazado', 'Rechazado'),
]


class LarocaPedido(models.Model):
    """Pedido de productos del encargado al administrador ("necesito 50 llaveros").

    Flujo:
      Borrador ──Enviar──▶ Enviado ──Aprobar──▶ En preparación ──(entrega confirmada)──▶ En camino ──▶ Entregado
                              └──Rechazar──▶ Rechazado
    Al aprobar se crea una entrega (laroca.entrega) con los productos pedidos; desde ahí
    sigue el flujo normal de abastecimiento. Una vez enviado, el pedido ya no se puede
    modificar: si hace falta más, el encargado hace otro pedido.
    """
    _name = 'laroca.pedido'
    _description = 'Pedido de productos de una gasolinera'
    _inherit = ['mail.thread']
    _order = 'fecha_envio desc, id desc'

    name = fields.Char('Referencia', required=True, readonly=True, copy=False, default='Nuevo')
    gasolinera_id = fields.Many2one(
        'stock.warehouse', 'Gasolinera', required=True, index=True, tracking=True,
        domain=[('laroca_es_gasolinera', '=', True)],
        default=lambda self: self.env['stock.warehouse'].search(
            [('laroca_es_gasolinera', '=', True)], limit=1, order='name'))
    company_id = fields.Many2one(related='gasolinera_id.company_id', store=True)
    solicitante_id = fields.Many2one('res.users', 'Pedido por', default=lambda self: self.env.user, readonly=True)
    origen = fields.Selection([
        ('encargado', 'Pedido del encargado'),
        ('administrador', 'Envío del administrador'),
    ], 'Origen', default='encargado', required=True, readonly=True, index=True,
        help='Envío del administrador: productos que el administrador decidió llevar sin que se los pidieran.')
    estado = fields.Selection(ESTADOS_PEDIDO, 'Estado', default='borrador', required=True, readonly=True,
                              tracking=True, index=True, copy=False)
    fecha_envio = fields.Datetime('Fecha del pedido', readonly=True, copy=False)
    nota = fields.Text('Comentario', help='Por ejemplo: "para el fin de semana largo".')
    motivo_rechazo = fields.Text('Motivo del rechazo', readonly=True, copy=False)
    entrega_id = fields.Many2one('laroca.entrega', 'Entrega', readonly=True, copy=False)
    linea_ids = fields.One2many('laroca.pedido.linea', 'pedido_id', string='Productos', copy=True)
    total_productos = fields.Integer('N.º de productos', compute='_compute_totales', store=True)
    total_unidades = fields.Float('Unidades pedidas', digits='Product Unit of Measure',
                                  compute='_compute_totales', store=True)

    @api.depends('linea_ids.cantidad')
    def _compute_totales(self):
        for pedido in self:
            pedido.total_productos = len(pedido.linea_ids)
            pedido.total_unidades = sum(pedido.linea_ids.mapped('cantidad'))

    # ------------------------------------------------------------------
    # Un pedido enviado no se modifica
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code('laroca.pedido') or 'Nuevo'
        return super().create(vals_list)

    def write(self, vals):
        # Los cambios de estado los hacen los botones (con sudo); a mano solo se edita el borrador.
        if not self.env.su:
            self._check_editable()
        return super().write(vals)

    def _check_editable(self):
        if any(pedido.estado != 'borrador' for pedido in self):
            raise UserError(_('El pedido ya fue enviado y no se puede modificar. '
                              'Si necesitás más productos, hacé un pedido nuevo.'))

    @api.ondelete(at_uninstall=False)
    def _unlink_solo_borrador(self):
        if any(pedido.estado != 'borrador' for pedido in self):
            raise UserError(_('Solo se pueden eliminar pedidos en borrador.'))

    # ------------------------------------------------------------------
    # Encargado
    # ------------------------------------------------------------------
    def action_agregar_faltantes(self):
        """Agrega los productos bajos y críticos con la cantidad sugerida por el sistema."""
        self.ensure_one()
        self._check_editable()
        ya_pedidos = self.linea_ids.product_id
        pendientes = self.env['laroca.inventario'].search([
            ('gasolinera_id', '=', self.gasolinera_id.id), ('estado', 'in', ('bajo', 'critico')),
            ('product_id', 'not in', ya_pedidos.ids)])
        if not pendientes:
            raise UserError(_('En %s no hay productos bajos o críticos. '
                              'Agregá los productos que necesitás con "Agregar una línea".', self.gasolinera_id.name))
        self.write({'linea_ids': [(0, 0, {'product_id': linea.product_id.id,
                                          'cantidad': linea.cantidad_sugerida or linea.stock_objetivo or 1})
                                  for linea in pendientes]})

    def action_enviar(self):
        for pedido in self:
            pedido._check_editable()
            pedido.check_access('write')
            if not pedido.linea_ids.filtered(lambda l: l.cantidad > 0):
                raise UserError(_('Agregá al menos un producto con cantidad mayor que cero.'))
            pedido.linea_ids.filtered(lambda l: l.cantidad <= 0).unlink()
            pedido.sudo().write({'estado': 'enviado', 'fecha_envio': fields.Datetime.now()})
            pedido._avisar_administradores()
        if len(self) == 1:
            return self._alerta_realizado()
        return True

    def _alerta_realizado(self, cerrar=False):
        return accion_alerta(
            'success', _('¡Tu pedido se realizó!'),
            _('%(pedido)s · %(unidades)s unidades. El administrador ya recibió el aviso; '
              'te avisaremos cuando lo apruebe.', pedido=self.name, unidades=f'{self.total_unidades:g}'),
            [f'{l.cantidad:g} × {l.product_id.with_context(display_default_code=False).display_name}'
             for l in self.linea_ids],
            cerrar=cerrar)

    def _avisar_administradores(self):
        filas = Markup('').join(
            Markup('<li>%s: <b>%s</b></li>') % (l.product_id.display_name, f'{l.cantidad:g}') for l in self.linea_ids)
        nota = Markup('<p><i>"%s"</i></p>') % self.nota if self.nota else Markup('')
        cuerpo = Markup('<p>📦 <b>%s</b> pide productos para <b>%s</b> (%s):</p><ul>%s</ul>%s') % (
            self.solicitante_id.name, self.gasolinera_id.name, self._get_html_link(self.name), filas, nota)
        Alerta = self.env['laroca.alerta']
        Alerta._publicar_en_canal(cuerpo)
        Alerta._enviar_correo_admins(
            _('Pedido %(pedido)s de %(gasolinera)s', pedido=self.name, gasolinera=self.gasolinera_id.name),
            cuerpo, accion='laroca_inventario.action_laroca_pedidos', boton=_('Ver pedidos en el sistema'))

    # ------------------------------------------------------------------
    # Administrador
    # ------------------------------------------------------------------
    def _check_admin(self):
        if not self.env.user.has_group('laroca_inventario.group_laroca_admin'):
            raise AccessError(_('Solo el administrador puede atender pedidos.'))

    def action_aprobar(self):
        """Crea una entrega en borrador con lo pedido; el administrador la revisa y la envía."""
        self.ensure_one()
        self._check_admin()
        if self.estado != 'enviado':
            raise UserError(_('Solo se pueden aprobar pedidos enviados.'))
        entrega = self.env['laroca.entrega'].create({
            'gasolinera_id': self.gasolinera_id.id,
            'linea_ids': [(0, 0, {'product_id': l.product_id.id, 'cantidad': l.cantidad,
                                  'cantidad_sugerida': l.cantidad}) for l in self.linea_ids],
        })
        self._vincular_entrega(entrega)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'laroca.entrega',
            'res_id': entrega.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def _vincular_entrega(self, entrega):
        """El pedido pasa a "En preparación" con esta entrega y se avisa al encargado."""
        self.ensure_one()
        self._check_admin()
        nota = _('Pedido %(pedido)s de %(persona)s', pedido=self.name, persona=self.solicitante_id.name)
        entrega.write({'pedido_id': self.id,
                       'notas': '\n'.join(filter(None, [entrega.notas, nota, self.nota]))})
        self.sudo().write({'estado': 'aprobado', 'entrega_id': entrega.id})
        self._avisar_solicitante(Markup('<p>✅ Tu pedido <b>%s</b> fue aprobado. El administrador está preparando '
                                        'la entrega <b>%s</b>.</p>') % (self.name, entrega.name))

    def action_abrir_rechazo(self):
        self.ensure_one()
        self._check_admin()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rechazar pedido %s', self.name),
            'res_model': 'laroca.pedido.rechazo',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_pedido_id': self.id},
        }

    def _rechazar(self, motivo):
        self.ensure_one()
        self._check_admin()
        if self.estado != 'enviado':
            raise UserError(_('Solo se pueden rechazar pedidos enviados.'))
        self.sudo().write({'estado': 'rechazado', 'motivo_rechazo': motivo})
        self._avisar_solicitante(Markup('<p>❌ Tu pedido <b>%s</b> fue rechazado.</p><p>Motivo: %s</p>') % (
            self.name, motivo))

    def _avisar_solicitante(self, cuerpo):
        """Mensaje en el pedido que le llega al encargado (bandeja de Odoo)."""
        pedido = self.sudo()
        pedido.message_subscribe(partner_ids=pedido.solicitante_id.partner_id.ids)
        pedido.message_post(body=cuerpo, message_type='comment', subtype_xmlid='mail.mt_comment',
                            partner_ids=pedido.solicitante_id.partner_id.ids, email_from=remitente_sistema(self.env))

    # Llamado desde laroca.entrega cuando la entrega cambia de estado
    def _entrega_actualizada(self, estado_entrega):
        if not self:
            return
        pedido = self.sudo()
        if estado_entrega == 'en_camino':
            pedido.estado = 'en_camino'
        elif estado_entrega == 'entregada':
            pedido.estado = 'entregado'
        elif estado_entrega == 'cancelada':
            # La entrega se canceló: el pedido vuelve a quedar pendiente de atender.
            pedido.write({'estado': 'enviado', 'entrega_id': False})
            pedido.message_post(body=_('La entrega se canceló; el pedido vuelve a estar pendiente.'),
                                message_type='comment', subtype_xmlid='mail.mt_note')

    def action_ver_entrega(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'laroca.entrega',
            'res_id': self.entrega_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }


class LarocaPedidoLinea(models.Model):
    _name = 'laroca.pedido.linea'
    _description = 'Producto de un pedido'
    _order = 'pedido_id, id'

    pedido_id = fields.Many2one('laroca.pedido', 'Pedido', required=True, ondelete='cascade', index=True)
    gasolinera_id = fields.Many2one(related='pedido_id.gasolinera_id', store=True, index=True)
    estado = fields.Selection(related='pedido_id.estado', store=True)
    product_id = fields.Many2one('product.product', 'Producto', required=True,
                                 domain=[('is_storable', '=', True)])
    image_128 = fields.Image(related='product_id.image_128')
    uom_id = fields.Many2one(related='product_id.uom_id', string='Unidad')
    cantidad = fields.Float('Cantidad', digits='Product Unit of Measure', required=True, default=1.0)
    stock_gasolinera = fields.Float('Tengo', digits='Product Unit of Measure', compute='_compute_existencias')
    disponible_bodega = fields.Float('En bodega', digits='Product Unit of Measure', compute='_compute_existencias')

    _sql_constraints = [
        ('producto_uniq', 'unique(pedido_id, product_id)', 'El producto ya está en este pedido.'),
        ('cantidad_positiva', 'CHECK(cantidad >= 0)', 'La cantidad no puede ser negativa.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            self.env['laroca.pedido'].browse({vals['pedido_id'] for vals in vals_list})._check_editable()
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            self.pedido_id._check_editable()
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            self.pedido_id._check_editable()
        return super().unlink()

    @api.depends('product_id', 'pedido_id.gasolinera_id')
    def _compute_existencias(self):
        Quant = self.env['stock.quant'].sudo()
        bodega = self.env.company._laroca_bodega_central()
        for linea in self:
            linea.stock_gasolinera = linea.disponible_bodega = 0.0
            if not linea.product_id:
                continue
            gasolinera = linea.pedido_id.sudo().gasolinera_id
            if gasolinera:
                linea.stock_gasolinera = sum(Quant.search([
                    ('product_id', '=', linea.product_id.id),
                    ('location_id', 'child_of', gasolinera.lot_stock_id.id)]).mapped('quantity'))
            if bodega:
                # sudo: el encargado no ve la bodega central, pero puede saber cuánto hay
                quants = Quant.search([('product_id', '=', linea.product_id.id),
                                       ('location_id', 'child_of', bodega.lot_stock_id.id)])
                linea.disponible_bodega = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
