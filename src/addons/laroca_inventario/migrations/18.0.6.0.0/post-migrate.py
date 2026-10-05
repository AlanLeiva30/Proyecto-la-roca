"""Migración a 18.0.6.0.0 (pulido de pantallas): cantidades sin decimales.

Todos los productos de Grupo La Roca se cuentan por unidad, así que la precisión
"Product Unit of Measure" pasa de 2 a 0 decimales ("20" en lugar de "20,00").
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('product.decimal_product_uom').digits = 0
