from odoo import api, fields, models


class ReporteGeneral(models.AbstractModel):
    """Prepara los datos que usa la plantilla QWeb de los reportes PDF."""
    _name = 'report.laroca_inventario.report_laroca_general'
    _description = 'Reportes de La Roca (datos)'

    @api.model
    def _get_report_values(self, docids, data=None):
        reportes = self.env['laroca.reporte'].browse(docids)
        datos = {}
        for reporte in reportes:
            if reporte.tipo == 'abastecimientos':
                entregas, por_gasolinera, por_producto = reporte._datos_abastecimientos()
                datos[reporte.id] = {
                    'entregas': entregas,
                    'por_gasolinera': por_gasolinera,
                    'por_producto': por_producto,
                    'total_entregas': len(entregas),
                    'total_unidades': sum(entregas.mapped('total_entregado')),
                    'total_valor': sum(entregas.mapped('valor_total')),
                }
            else:
                datos[reporte.id] = {
                    'grupos': reporte._datos_inventario(solo_pendientes=reporte.tipo == 'stock_bajo'),
                }
        return {
            'doc_ids': docids,
            'doc_model': 'laroca.reporte',
            'docs': reportes,
            'datos': datos,
            'titulos': {r.id: r._titulo() for r in reportes},
            'generado': fields.Datetime.context_timestamp(self, fields.Datetime.now()),
            'usuario': self.env.user,
            'estados': dict(self.env['laroca.inventario']._fields['estado'].selection),
            'colores': {'critico': '#dc3545', 'bajo': '#e8890c', 'suficiente': '#198754', 'sin_minimo': '#6c757d'},
            'fmt': lambda cantidad: f'{cantidad:g}',
            'dinero': lambda valor: f'$ {valor:,.2f}',
        }
