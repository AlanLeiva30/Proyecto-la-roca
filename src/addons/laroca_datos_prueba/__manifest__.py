{
    'name': 'La Roca - Datos de prueba',
    'version': '18.0.7.0.0',
    'summary': 'Datos ficticios para probar el sistema (gasolineras, productos, usuarios y existencias)',
    'description': """
Carga datos FICTICIOS para pruebas y demostraciones:
5 gasolineras, bodega central, 13 productos en 4 categorías,
1 administrador, 3 encargados, existencias iniciales, stock mínimo/objetivo, entregas, ventas y pedidos de ejemplo.
No instalar en producción.
""",
    'author': 'Equipo Grupo La Roca - UDB',
    'category': 'Inventory',
    'license': 'LGPL-3',
    'depends': ['laroca_inventario'],
    'data': [
        'data/empresa.xml',
        'data/correo.xml',
        'data/gasolineras.xml',
        'data/productos.xml',
        'data/imagenes.xml',
        'data/usuarios.xml',
        'data/existencias.xml',
        'data/niveles.xml',
        'data/entregas.xml',
        'data/ventas_pedidos.xml',
    ],
    'installable': True,
}
