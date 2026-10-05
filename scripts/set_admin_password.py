# Se ejecuta dentro de "odoo shell": cambia la clave del usuario técnico "admin"
# por la definida en ODOO_ADMIN_PASSWORD (archivo .env).
import os

clave = os.environ.get('ODOO_ADMIN_PASSWORD')
if clave:
    env.ref('base.user_admin').password = clave  # noqa: F821 (env lo provee odoo shell)
    env.cr.commit()  # noqa: F821
    print('Clave del usuario admin actualizada.')
else:
    print('ODOO_ADMIN_PASSWORD vacío: no se cambió la clave de admin.')
