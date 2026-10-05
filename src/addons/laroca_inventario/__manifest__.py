{
    'name': 'La Roca - Inventario por gasolinera',
    'version': '18.0.7.0.0',
    'summary': 'Gasolineras, catálogo e inventario por sucursal para Grupo La Roca',
    'description': """
Etapa 1 del sistema de inventario y abastecimiento de Grupo La Roca.

* Gasolineras (extiende stock.warehouse de Odoo).
* Roles: Encargado de sucursal y Administrador.
* Inventario por sucursal con acceso limitado a las gasolineras asignadas.
* Actualización de existencias mediante ajustes de inventario nativos de Odoo
  (cada cambio queda como movimiento de stock).
* Etapa 2: stock mínimo y objetivo, estados suficiente / bajo / crítico,
  alertas automáticas y sugerencias de abastecimiento.
* Etapa 3: entregas desde la bodega central (transferencias nativas),
  confirmación de recepción, hoja de entrega en PDF e historial de abastecimientos.
* Etapa 4: panel general con indicadores y reportes (PDF, gráficos y tablas dinámicas).
""",
    'author': 'Equipo Grupo La Roca - UDB',
    'category': 'Inventory',
    'license': 'LGPL-3',
    'depends': ['stock', 'mail', 'digest'],
    'data': [
        'security/laroca_security.xml',
        'security/ir.model.access.csv',
        'data/laroca_data.xml',
        'data/laroca_alertas_data.xml',
        'wizard/conteo_views.xml',
        'wizard/preparar_entrega_views.xml',
        'views/laroca_inventario_views.xml',
        'views/stock_warehouse_views.xml',
        'views/product_views.xml',
        'wizard/bodega_movimiento_views.xml',
        'views/bodega_views.xml',
        'views/res_users_views.xml',
        'wizard/actualizar_stock_views.xml',
        'views/abastecimiento_views.xml',
        'report/entrega_report.xml',
        'views/entrega_views.xml',
        'report/reporte_general.xml',
        'views/pedido_views.xml',
        'views/venta_views.xml',
        'views/panel_reportes_views.xml',
        'wizard/importar_views.xml',
        'views/login_templates.xml',
        'views/menus.xml',
    ],
    'assets': {
        # Colores de Grupo La Roca (antes de las variables de Odoo, que usan !default)
        'web._assets_primary_variables': [
            ('before', 'web/static/src/scss/primary_variables.scss',
             'laroca_inventario/static/src/scss/primary_variables.scss'),
        ],
        'web.assets_frontend': [
            'laroca_inventario/static/src/scss/login.scss',
        ],
        # Componente OWL de los gráficos del panel (único JavaScript propio del módulo) y estilos
        'web.assets_backend': [
            'laroca_inventario/static/src/scss/laroca.scss',
            'laroca_inventario/static/src/panel_graficos/panel_graficos.js',
            'laroca_inventario/static/src/panel_graficos/panel_graficos.xml',
            'laroca_inventario/static/src/panel_graficos/panel.scss',
            'laroca_inventario/static/src/alerta/alerta.js',
            'laroca_inventario/static/src/alerta/alerta.xml',
            'laroca_inventario/static/src/alerta/alerta.scss',
            'laroca_inventario/static/src/contador/contador.js',
            'laroca_inventario/static/src/contador/contador.xml',
            'laroca_inventario/static/src/contador/contador.scss',
            'laroca_inventario/static/src/busqueda_simple/busqueda_simple.js',
            'laroca_inventario/static/src/busqueda_simple/busqueda_simple.xml',
            'laroca_inventario/static/src/ver_clave/ver_clave.js',
            'laroca_inventario/static/src/ver_clave/ver_clave.xml',
        ],
    },
    'application': True,
    'installable': True,
}
