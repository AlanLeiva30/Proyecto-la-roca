"""Genera ilustraciones FICTICIAS de los productos de prueba (sin fotos de terceros).
Se ejecuta dentro del contenedor de Odoo (tiene Pillow):
  docker run --rm -i -u root -v "$PWD/src/addons:/addons" --entrypoint python3 odoo:18.0 - < scripts/generar_imagenes_productos.py
"""
import glob
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 1024  # se dibuja grande y se reduce para suavizar bordes
SALIDA = '/addons/laroca_datos_prueba/static/img/productos/'
FUENTE = (glob.glob('/usr/share/fonts/**/DejaVuSans-Bold.ttf', recursive=True) or [None])[0]


def lienzo(fondo):
    img = Image.new('RGB', (S, S), fondo)
    d = ImageDraw.Draw(img)
    d.ellipse([140, 820, 884, 920], fill=tuple(max(c - 25, 0) for c in fondo))  # sombra
    return img, d


def texto(d, xy, t, tam, color):
    f = ImageFont.truetype(FUENTE, tam) if FUENTE else ImageFont.load_default()
    w = d.textlength(t, font=f)
    d.text((xy[0] - w / 2, xy[1]), t, font=f, fill=color)


def guardar(img, codigo):
    img.resize((512, 512), Image.LANCZOS).save(SALIDA + codigo + '.png')


def lentes(codigo, marco, cristal, deportivo=False):
    img, d = lienzo((236, 242, 250))
    if deportivo:
        d.rounded_rectangle([170, 380, 854, 600], radius=120, fill=cristal, outline=marco, width=26)
        d.line([512, 380, 512, 600], fill=marco, width=14)
    else:
        d.rounded_rectangle([170, 390, 470, 610], radius=70, fill=cristal, outline=marco, width=28)
        d.rounded_rectangle([554, 390, 854, 610], radius=70, fill=cristal, outline=marco, width=28)
        d.arc([450, 400, 574, 500], 200, 340, fill=marco, width=26)
    d.line([170, 430, 90, 400], fill=marco, width=26)
    d.line([854, 430, 934, 400], fill=marco, width=26)
    d.polygon([(220, 430), (300, 430), (240, 520)], fill=(255, 255, 255, 90))
    guardar(img, codigo)


def llavero(codigo, peluche=False):
    img, d = lienzo((245, 240, 230))
    d.ellipse([400, 120, 624, 344], outline=(150, 150, 160), width=34)
    d.line([512, 340, 512, 420], fill=(150, 150, 160), width=20)
    if peluche:
        d.ellipse([352, 400, 672, 720], fill=(176, 120, 72))        # cabeza
        d.ellipse([330, 380, 440, 490], fill=(176, 120, 72))
        d.ellipse([584, 380, 694, 490], fill=(176, 120, 72))
        d.ellipse([450, 560, 574, 680], fill=(230, 200, 160))
        d.ellipse([440, 500, 480, 540], fill=(40, 30, 20))
        d.ellipse([544, 500, 584, 540], fill=(40, 30, 20))
        d.ellipse([492, 585, 532, 620], fill=(40, 30, 20))
    else:
        d.rounded_rectangle([352, 420, 672, 780], radius=60, fill=(190, 195, 205), outline=(120, 125, 135), width=12)
        d.ellipse([482, 440, 542, 500], fill=(245, 240, 230))
        texto(d, (512, 560), 'LR', 150, (11, 61, 145))
    guardar(img, codigo)


def sombrero(codigo):
    img, d = lienzo((250, 244, 228))
    d.ellipse([110, 520, 914, 760], fill=(222, 190, 120), outline=(180, 145, 80), width=10)
    d.rounded_rectangle([300, 300, 724, 640], radius=140, fill=(232, 202, 135), outline=(180, 145, 80), width=10)
    d.rectangle([300, 540, 724, 600], fill=(120, 60, 30))
    for x in range(330, 700, 40):
        d.line([x, 320, x - 20, 530], fill=(205, 170, 100), width=4)
    guardar(img, codigo)


def gorra(codigo):
    img, d = lienzo((235, 240, 248))
    d.pieslice([230, 260, 790, 820], 180, 360, fill=(11, 61, 145))
    d.ellipse([480, 250, 544, 300], fill=(9, 45, 110))
    d.polygon([(560, 540), (930, 560), (900, 640), (560, 600)], fill=(9, 45, 110))
    d.rectangle([230, 530, 790, 560], fill=(9, 45, 110))
    texto(d, (500, 380), 'LR', 110, (255, 196, 0))
    guardar(img, codigo)


def carrito(codigo):
    img, d = lienzo((240, 246, 240))
    d.rounded_rectangle([170, 470, 860, 660], radius=50, fill=(220, 40, 40))
    d.polygon([(320, 470), (400, 340), (650, 340), (740, 470)], fill=(200, 30, 30))
    d.polygon([(350, 465), (415, 365), (515, 365), (515, 465)], fill=(180, 220, 245))
    d.polygon([(540, 465), (540, 365), (635, 365), (705, 465)], fill=(180, 220, 245))
    for cx in (330, 700):
        d.ellipse([cx - 85, 590, cx + 85, 760], fill=(40, 40, 40))
        d.ellipse([cx - 40, 635, cx + 40, 715], fill=(190, 190, 190))
    d.rectangle([800, 520, 860, 560], fill=(255, 220, 80))
    guardar(img, codigo)


def pelota(codigo):
    img, d = lienzo((248, 240, 250))
    d.ellipse([262, 262, 762, 762], fill=(255, 80, 120))
    d.chord([262, 262, 762, 762], 200, 340, fill=(80, 170, 255))
    d.chord([262, 262, 762, 762], 20, 160, fill=(255, 210, 60))
    d.ellipse([340, 330, 430, 400], fill=(255, 255, 255))
    guardar(img, codigo)


def botella(codigo, cuerpo, etiqueta, titulo, subtitulo, galon=False):
    img, d = lienzo((242, 244, 240))
    if galon:
        d.rounded_rectangle([290, 300, 734, 820], radius=50, fill=cuerpo)
        d.rounded_rectangle([600, 220, 690, 320], radius=20, fill=(30, 30, 30))
        d.rounded_rectangle([320, 250, 560, 330], radius=30, outline=cuerpo, width=34)
    else:
        d.rounded_rectangle([380, 300, 644, 820], radius=60, fill=cuerpo)
        d.rectangle([450, 230, 574, 310], fill=cuerpo)
        d.rounded_rectangle([430, 170, 594, 240], radius=16, fill=(30, 30, 30))
    x0, x1 = (330, 694) if galon else (400, 624)
    d.rounded_rectangle([x0, 470, x1, 720], radius=20, fill=etiqueta)
    texto(d, (512, 510), titulo, 70 if galon else 44, (11, 61, 145))
    texto(d, (512, 610), subtitulo, 44 if galon else 34, (60, 60, 60))
    guardar(img, codigo)


def aromatizante(codigo, color, sub):
    img, d = lienzo((238, 248, 240))
    d.line([512, 90, 512, 220], fill=(230, 180, 40), width=10)
    d.ellipse([487, 200, 537, 250], outline=(230, 180, 40), width=10)
    d.polygon([(512, 240), (300, 520), (420, 520), (250, 760), (774, 760), (604, 520), (724, 520)], fill=color)
    d.rectangle([472, 760, 552, 840], fill=color)
    texto(d, (512, 600), sub, 52, (255, 255, 255))
    guardar(img, codigo)


lentes('LEN-001', (25, 25, 25), (60, 60, 70))
lentes('LEN-002', (11, 61, 145), (60, 140, 200), deportivo=True)
llavero('LLA-001')
llavero('LLA-002', peluche=True)
sombrero('SOM-001')
gorra('SOM-002')
carrito('JUG-001')
pelota('JUG-002')
botella('ADI-001', (30, 140, 70), (255, 255, 255), 'ADITIVO', '350 ml')
botella('ACE-001', (230, 170, 30), (255, 255, 255), '15W-40', 'Aceite 1 L', galon=True)
botella('ACE-002', (40, 110, 200), (255, 255, 255), '2T', 'Aceite 1 L')
aromatizante('ARO-001', (20, 120, 50), 'PINO')
aromatizante('ARO-002', (225, 185, 90), 'VAINILLA')
print('Imágenes generadas:', len(glob.glob(SALIDA + '*.png')))
