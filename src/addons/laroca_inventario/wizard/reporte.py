from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

TIPOS = [
    ('inventario', 'Inventario por gasolinera'),
    ('stock_bajo', 'Productos con poca existencia'),
    ('abastecimientos', 'Abastecimientos por período'),
]


class LarocaReporte(models.TransientModel):
    """Asistente de reportes en PDF.

    Los datos se leen con los permisos del usuario: un encargado solo obtiene reportes
    de sus gasolineras.
    """
    _name = 'laroca.reporte'
    _description = 'Reportes de inventario y abastecimiento'

    tipo = fields.Selection(TIPOS, 'Reporte', required=True, default='stock_bajo')
    gasolinera_ids = fields.Many2many(
        'stock.warehouse', string='Gasolineras', domain=[('laroca_es_gasolinera', '=', True)],
        help='Vacío = todas las gasolineras a las que tenés acceso.')
    fecha_desde = fields.Date('Desde', default=lambda self: fields.Date.context_today(self) - timedelta(days=30))
    fecha_hasta = fields.Date('Hasta', default=fields.Date.context_today)

    def _gasolineras(self):
        return self.gasolinera_ids or self.env['stock.warehouse'].search(
            [('laroca_es_gasolinera', '=', True)], order='name')

    def _titulo(self):
        return dict(TIPOS)[self.tipo]

    def _periodo_utc(self):
        """Rango de fechas del usuario convertido a UTC."""
        zona = pytz.timezone(self.env.user.tz or 'UTC')
        desde = zona.localize(datetime.combine(self.fecha_desde, time.min)).astimezone(pytz.UTC)
        hasta = zona.localize(datetime.combine(self.fecha_hasta, time.max)).astimezone(pytz.UTC)
        return desde.replace(tzinfo=None), hasta.replace(tzinfo=None)

    # --- Datos para cada reporte ------------------------------------------
    def _datos_inventario(self, solo_pendientes=False):
        """[(gasolinera, líneas, resumen por estado)]"""
        dominio = [('gasolinera_id', 'in', self._gasolineras().ids)]
        if solo_pendientes:
            dominio.append(('estado', 'in', ('bajo', 'critico')))
        lineas = self.env['laroca.inventario'].search(dominio, order='gasolinera_id, prioridad, default_code')
        resultado = []
        for gasolinera in self._gasolineras():
            propias = lineas.filtered(lambda l: l.gasolinera_id == gasolinera)
            if solo_pendientes and not propias:
                continue
            resumen = defaultdict(int)
            for linea in propias:
                resumen[linea.estado] += 1
            resultado.append((gasolinera, propias, resumen))
        return resultado

    def _datos_abastecimientos(self):
        """Entregas recibidas en el período: (entregas, totales por gasolinera, totales por producto)"""
        desde, hasta = self._periodo_utc()
        entregas = self.env['laroca.entrega'].search([
            ('estado', '=', 'entregada'),
            ('gasolinera_id', 'in', self._gasolineras().ids),
            ('fecha_entrega', '>=', desde), ('fecha_entrega', '<=', hasta),
        ], order='fecha_entrega')
        por_gasolinera = defaultdict(lambda: {'entregas': 0, 'unidades': 0.0, 'valor': 0.0})
        por_producto = defaultdict(float)
        for entrega in entregas:
            por_gasolinera[entrega.gasolinera_id]['entregas'] += 1
            por_gasolinera[entrega.gasolinera_id]['unidades'] += entrega.total_entregado
            por_gasolinera[entrega.gasolinera_id]['valor'] += entrega.valor_total
            for linea in entrega.linea_ids:
                por_producto[linea.product_id] += linea.cantidad_entregada
        productos = sorted(por_producto.items(), key=lambda item: -item[1])
        return entregas, dict(por_gasolinera), productos

    # --- Acción -----------------------------------------------------------
    def action_imprimir(self):
        self.ensure_one()
        if self.tipo == 'abastecimientos' and (not self.fecha_desde or not self.fecha_hasta):
            raise UserError(_('Indicá el período (desde y hasta).'))
        if self.fecha_desde and self.fecha_hasta and self.fecha_desde > self.fecha_hasta:
            raise UserError(_('La fecha "desde" no puede ser posterior a "hasta".'))
        return self.env.ref('laroca_inventario.action_report_laroca_general').report_action(self)

    @api.model
    def _fmt(self, cantidad):
        return f'{cantidad:g}'
