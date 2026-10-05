# Se ejecuta dentro de "odoo shell" en el servidor, después de instalar.
# - Dirección pública (para enlaces de correos y PDF).
# - Contraseñas NUEVAS para los usuarios de prueba (no LaRoca2026, porque está en internet).
import os

dominio = os.environ['DOMINIO']
clave_demo = os.environ.get('DEMO_CLAVE')
Param = env['ir.config_parameter'].sudo()  # noqa: F821 (env lo provee odoo shell)
Param.set_param('web.base.url', f'https://{dominio}')
Param.set_param('web.base.url.freeze', 'True')
# wkhtmltopdf (PDF) pide las hojas de estilo al propio Odoo, dentro del contenedor
Param.set_param('report.url', 'http://127.0.0.1:8069')
if clave_demo:
    usuarios = env['res.users'].search([('login', 'in', ['administrador', 'encargado.centro',  # noqa: F821
                                                          'encargado.norte', 'encargado.sur'])])
    for usuario in usuarios:
        usuario.password = clave_demo
    print(f'Contraseña nueva para {len(usuarios)} usuarios de prueba.')
env.cr.commit()  # noqa: F821
print(f'Dirección pública: https://{dominio}')
