"""Funciones de ayuda compartidas por los modelos y asistentes de La Roca."""


def accion_alerta(tipo, titulo, texto='', detalle=None, cerrar=False):
    """Acción que muestra la alerta grande estilo "SweetAlert" (static/src/alerta/).

    :param tipo: 'success', 'error', 'warning' o 'info' (color e ícono)
    :param detalle: lista de renglones opcionales debajo del texto
    :param cerrar: True para cerrar antes el asistente desde donde se llamó
    """
    params = {'tipo': tipo, 'titulo': titulo, 'texto': texto, 'detalle': list(detalle or [])}
    if cerrar:
        params['next'] = {'type': 'ir.actions.act_window_close'}
    return {'type': 'ir.actions.client', 'tag': 'laroca_alerta', 'params': params}


def remitente_sistema(env):
    """Dirección de los avisos automáticos (notificaciones@<dominio>). Así el correo sale aunque
    la persona que hizo la acción no tenga correo cargado."""
    return (env['ir.mail_server'].sudo()._get_default_from_address()
            or env.ref('base.partner_root').email_formatted)
