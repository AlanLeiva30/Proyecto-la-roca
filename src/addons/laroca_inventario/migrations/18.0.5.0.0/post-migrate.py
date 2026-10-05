"""Migración a la versión 18.0.5.0.0 (mejoras: valor del inventario).

Las entregas creadas antes de esta versión no tenían "costo unitario". Se completa con
el costo actual del producto para que su valor no quede en $0.
Odoo ejecuta este archivo automáticamente al actualizar el módulo desde una versión anterior.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    lineas = env['laroca.entrega.linea'].search([('costo_unitario', '=', 0)])
    for linea in lineas:
        linea.costo_unitario = linea.product_id.standard_price
