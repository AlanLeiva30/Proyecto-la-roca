import base64
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import file_open

# Existencias FICTICIAS por producto:
#   código: (bodega central, [Centro, Norte, Sur, Oriente, Occidente])
EXISTENCIAS = {
    'LEN-001': (120, [4, 12, 9, 2, 15]),
    'LEN-002': (80, [6, 3, 10, 8, 0]),
    'LLA-001': (200, [12, 20, 5, 18, 25]),
    'LLA-002': (150, [8, 2, 14, 11, 9]),
    'SOM-001': (60, [7, 5, 1, 9, 6]),
    'SOM-002': (90, [10, 14, 6, 3, 12]),
    'JUG-001': (100, [18, 7, 11, 4, 20]),
    'JUG-002': (250, [30, 25, 8, 15, 40]),
    'ADI-001': (80, [3, 9, 12, 5, 7]),
    'ACE-001': (150, [20, 16, 4, 22, 18]),
    'ACE-002': (100, [9, 2, 15, 6, 11]),
    'ARO-001': (300, [6, 22, 18, 3, 30]),
    'ARO-002': (300, [15, 4, 20, 10, 2]),
}
# Niveles FICTICIOS por producto (basados en el mockup 10.2): código: (mínimo, objetivo)
NIVELES = {
    'LEN-001': (10, 20), 'LEN-002': (8, 16),
    'LLA-001': (10, 25), 'LLA-002': (8, 16),
    'SOM-001': (10, 15), 'SOM-002': (8, 16),
    'JUG-001': (12, 24), 'JUG-002': (15, 30),
    'ADI-001': (8, 16),
    'ACE-001': (15, 30), 'ACE-002': (10, 20),
    'ARO-001': (10, 25), 'ARO-002': (10, 25),
}

IMAGENES_VERSION = '2'  # 2 = fotos reales (antes: solo ilustraciones)

# Descripciones FICTICIAS de los productos (se ven en el catálogo)
DESCRIPCIONES = {
    'LEN-001': 'Lentes de sol de estilo clásico con marco negro y protección UV400. Livianos y resistentes, '
               'ideales para manejar de día. Incluyen bolsita de tela.',
    'LEN-002': 'Lentes deportivos envolventes con lente polarizado que reduce el reflejo del asfalto y del agua. '
               'Varillas antideslizantes para moto, bicicleta o deporte.',
    'LLA-001': 'Llavero de metal cromado con argolla reforzada y dije decorativo. Resistente al uso diario; '
               'recuerdo económico para los clientes.',
    'LLA-002': 'Llavero de peluche suave en forma de osito, con cadena y argolla metálica. Muy buscado por niños '
               'y como detalle de regalo.',
    'SOM-001': 'Sombrero de palma tejido a mano, de ala ancha para proteger del sol. Fresco y liviano, '
               'ideal para viajes a la playa.',
    'SOM-002': 'Gorra de algodón con visera curva y cierre ajustable. Logo de La Roca bordado al frente; talla única.',
    'JUG-001': 'Carrito de juguete de metal y plástico con ruedas de goma. Para niños de 3 años en adelante; '
               'buen producto de compra rápida junto a la caja.',
    'JUG-002': 'Pelota saltarina de hule de 3 cm en colores surtidos. Rebota muy alto; se vende por unidad. '
               'No apta para menores de 3 años.',
    'ADI-001': 'Aditivo limpiador para gasolina, botella de 350 ml. Ayuda a mantener limpios los inyectores; '
               'una botella rinde hasta 60 litros de combustible.',
    'ACE-001': 'Aceite multigrado 15W-40 para motores a gasolina y diésel, envase de 1 litro. Protege contra '
               'el desgaste en clima cálido.',
    'ACE-002': 'Aceite para motores de 2 tiempos (motocicletas, motosierras y lanchas), envase de 1 litro. '
               'Se mezcla con la gasolina según indique el fabricante del motor.',
    'ARO-001': 'Aromatizante colgante para carro con aroma a pino. Dura de 3 a 4 semanas; incluye cordón '
               'para colgar del retrovisor.',
    'ARO-002': 'Aromatizante colgante para carro con aroma a vainilla. Dura de 3 a 4 semanas; incluye cordón '
               'para colgar del retrovisor.',
}

GASOLINERAS = [
    'laroca_datos_prueba.gasolinera_centro',
    'laroca_datos_prueba.gasolinera_norte',
    'laroca_datos_prueba.gasolinera_sur',
    'laroca_datos_prueba.gasolinera_oriente',
    'laroca_datos_prueba.gasolinera_occidente',
]


class LarocaInventario(models.Model):
    _inherit = 'laroca.inventario'

    @api.model
    def _datos_prueba_cargar_existencias(self):
        """Carga las existencias iniciales con un ajuste de inventario nativo,
        igual que lo haría un usuario, para que quede en el historial."""
        Quant = self.env['stock.quant'].sudo()
        bodega = self.env.ref('stock.warehouse0')
        gasolineras = [self.env.ref(xmlid) for xmlid in GASOLINERAS]
        quants = Quant.browse()
        for codigo, (central, por_gasolinera) in EXISTENCIAS.items():
            producto = self.env['product.product'].search([('default_code', '=', codigo)], limit=1)
            if not producto:
                continue
            for almacen, cantidad in [(bodega, central)] + list(zip(gasolineras, por_gasolinera)):
                ubicacion = almacen.lot_stock_id
                quant = Quant._gather(producto, ubicacion, strict=True)[:1] or Quant.create(
                    {'product_id': producto.id, 'location_id': ubicacion.id})
                if quant.quantity == cantidad:
                    continue
                quant.inventory_quantity = cantidad
                quants |= quant
        quants.with_context(
            inventory_name='Carga inicial (datos de prueba)', laroca_sin_alertas=True)._apply_inventory()

    @api.model
    def _datos_prueba_cargar_niveles(self):
        """Asigna mínimos y objetivos ficticios SOLO donde aún no hay mínimo
        (no pisa los valores que el administrador haya cambiado)."""
        Lineas = self.sudo().with_context(laroca_sin_alertas=True)
        for codigo, (minimo, objetivo) in NIVELES.items():
            plantilla = self.env['product.template'].search([('default_code', '=', codigo)], limit=1)
            if not plantilla:
                continue
            if not plantilla.laroca_stock_minimo:
                plantilla.write({'laroca_stock_minimo': minimo, 'laroca_stock_objetivo': objetivo})
            Lineas.search([
                ('product_id', 'in', plantilla.product_variant_ids.ids), ('stock_minimo', '=', 0),
            ]).write({'stock_minimo': minimo, 'stock_objetivo': objetivo})
        # Alertas iniciales sin un mensaje por producto: se publica un solo resumen.
        nuevas = self.sudo().search([])._sincronizar_alertas(notificar=False)
        if nuevas:
            self.env['laroca.alerta']._cron_resumen_diario()

    @api.model
    def _datos_prueba_cargar_entregas(self):
        """Entregas ficticias (solo si todavía no hay ninguna):
        Norte y Oriente ya recibidas (historial) y Centro en camino (para probar la recepción)."""
        Entrega = self.env['laroca.entrega']
        if Entrega.search_count([]):
            return
        hoy = fields.Date.context_today(self)
        plan = [
            ('laroca_datos_prueba.gasolinera_norte', 5, 'recibida'),
            ('laroca_datos_prueba.gasolinera_oriente', 2, 'recibida'),
            ('laroca_datos_prueba.gasolinera_centro', 0, 'en_camino'),
        ]
        for xmlid, dias_atras, estado in plan:
            gasolinera = self.env.ref(xmlid)
            lineas = self.search([('gasolinera_id', '=', gasolinera.id), ('estado', 'in', ('bajo', 'critico'))])
            accion = lineas.action_crear_entregas()
            entrega = Entrega.browse(accion.get('res_id'))
            if not entrega:
                continue
            fecha = hoy - timedelta(days=dias_atras)
            entrega.write({
                'fecha_programada': fecha,
                'responsable_id': self.env.ref('laroca_datos_prueba.usuario_administrador').id,
                'notas': 'Entrega ficticia (datos de prueba).',
            })
            entrega.action_confirmar()
            if estado == 'recibida':
                entrega._registrar_recepcion({})
                entrega.write({
                    'fecha_entrega': fields.Datetime.to_datetime(fecha) + timedelta(hours=16),
                    'recibido_por_id': gasolinera.laroca_encargado_ids[:1].id or entrega.responsable_id.id,
                })

    @api.model
    def _datos_prueba_cargar_ventas_pedidos(self):
        """Ventas y pedidos ficticios (solo si todavía no hay ventas). Se registran con el
        usuario de cada encargado, como si las hubiera hecho desde su panel."""
        Venta = self.env['laroca.venta']
        if Venta.search_count([]):
            return
        ref = self.env.ref
        Producto = self.env['product.product']
        ahora = fields.Datetime.now()
        # (encargado, gasolinera, días atrás, {código: unidades})
        ventas = [
            ('usuario_encargado_centro', 'gasolinera_centro', 2, {'JUG-002': 4, 'ACE-001': 2}),
            ('usuario_encargado_centro', 'gasolinera_centro', 1, {'ARO-002': 3, 'LLA-001': 2}),
            ('usuario_encargado_centro', 'gasolinera_centro', 0, {'JUG-002': 3, 'SOM-002': 1, 'ACE-001': 1}),
            ('usuario_encargado_norte', 'gasolinera_norte', 1, {'ARO-001': 5, 'LLA-001': 3}),
            ('usuario_encargado_norte', 'gasolinera_norte', 0, {'JUG-002': 2, 'ACE-001': 2}),
            ('usuario_encargado_sur', 'gasolinera_sur', 0, {'ARO-002': 4, 'JUG-001': 1}),
        ]
        for usuario, gasolinera, dias, productos in ventas:
            usuario, gasolinera = ref(f'laroca_datos_prueba.{usuario}'), ref(f'laroca_datos_prueba.{gasolinera}')
            cantidades = {}
            for codigo, unidades in productos.items():
                producto = Producto.search([('default_code', '=', codigo)], limit=1)
                linea = self.search([('gasolinera_id', '=', gasolinera.id), ('product_id', '=', producto.id)])
                if producto and linea.stock_actual >= unidades:
                    cantidades[producto] = unidades
            if cantidades:
                venta = Venta.with_user(usuario)._registrar(gasolinera, cantidades)
                venta.sudo().fecha = ahora - timedelta(days=dias, hours=1)
        # Pedidos: Sur pide 50 llaveros (por atender) y Norte ya recibió el suyo.
        Pedido = self.env['laroca.pedido']
        admin = ref('laroca_datos_prueba.usuario_administrador')
        pedidos = [
            ('usuario_encargado_sur', 'gasolinera_sur', {'LLA-001': 50, 'SOM-001': 10},
             'Se acercan las vacaciones y los llaveros se venden mucho.', 'enviado'),
            ('usuario_encargado_norte', 'gasolinera_norte', {'ACE-002': 12},
             'Pedido ficticio (datos de prueba).', 'entregado'),
        ]
        for usuario, gasolinera, productos, nota, estado in pedidos:
            usuario, gasolinera = ref(f'laroca_datos_prueba.{usuario}'), ref(f'laroca_datos_prueba.{gasolinera}')
            pedido = Pedido.with_user(usuario).create({
                'gasolinera_id': gasolinera.id,
                'nota': nota,
                'linea_ids': [(0, 0, {'product_id': Producto.search([('default_code', '=', c)], limit=1).id,
                                      'cantidad': n}) for c, n in productos.items()],
            })
            pedido.action_enviar()
            if estado == 'entregado':
                entrega = self.env['laroca.entrega'].browse(pedido.with_user(admin).action_aprobar()['res_id'])
                entrega.with_user(admin).action_confirmar()
                entrega.with_user(usuario)._registrar_recepcion({})

    @api.model
    def _datos_prueba_cargar_imagenes(self):
        """Fotos reales con licencia libre (static/img/productos_fotos, ver CREDITOS.md) o,
        si un producto no tiene foto, su ilustración. También completa las descripciones.

        Al cambiar IMAGENES_VERSION se reemplazan las imágenes de prueba anteriores una vez.
        """
        parametros = self.env['ir.config_parameter'].sudo()
        reemplazar = parametros.get_param('laroca_datos_prueba.imagenes_version') != IMAGENES_VERSION
        for codigo in NIVELES:
            plantilla = self.env['product.template'].search([('default_code', '=', codigo)], limit=1)
            if not plantilla:
                continue
            if not plantilla.description_sale and codigo in DESCRIPCIONES:
                plantilla.description_sale = DESCRIPCIONES[codigo]
            if plantilla.image_1920 and not reemplazar:
                continue
            for ruta in (f'laroca_datos_prueba/static/img/productos_fotos/{codigo}.jpg',
                         f'laroca_datos_prueba/static/img/productos/{codigo}.png'):
                try:
                    with file_open(ruta, 'rb') as imagen:
                        plantilla.image_1920 = base64.b64encode(imagen.read())
                    break
                except FileNotFoundError:
                    continue
        parametros.set_param('laroca_datos_prueba.imagenes_version', IMAGENES_VERSION)
