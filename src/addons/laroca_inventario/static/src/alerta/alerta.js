/** @odoo-module **/
/**
 * Alerta grande al estilo "SweetAlert" (ícono animado, título, texto y un botón).
 *
 * Se abre desde Python devolviendo la acción:
 *   {'type': 'ir.actions.client', 'tag': 'laroca_alerta',
 *    'params': {'tipo': 'success'|'error'|'warning'|'info', 'titulo': ..., 'texto': ...,
 *               'detalle': [...], 'next': <acción opcional, p. ej. cerrar el asistente>}}
 * Ver laroca_inventario/utils.py (función accion_alerta).
 */
import { Component, onMounted, useRef } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const ICONOS = { success: "fa-check", error: "fa-times", warning: "fa-exclamation", info: "fa-info" };

export class LarocaAlerta extends Component {
    static template = "laroca_inventario.Alerta";
    static components = { Dialog };
    static props = {
        tipo: String,
        titulo: String,
        texto: { type: String, optional: true },
        detalle: { type: Array, optional: true },
        boton: { type: String, optional: true },
        close: Function,
    };

    setup() {
        this.boton = useRef("boton");
        // Enter cierra la alerta, como en SweetAlert
        onMounted(() => this.boton.el?.focus());
    }

    get icono() {
        return ICONOS[this.props.tipo] || ICONOS.info;
    }
}

registry.category("actions").add("laroca_alerta", async (env, action) => {
    const params = action.params || {};
    if (params.next) {
        await env.services.action.doAction(params.next);
    }
    env.services.dialog.add(LarocaAlerta, {
        tipo: params.tipo || "success",
        titulo: params.titulo || "",
        texto: params.texto || "",
        detalle: params.detalle || [],
        boton: params.boton || "Aceptar",
    });
});

/** Misma alerta, con dos botones (confirmar / cancelar). */
export class LarocaConfirmar extends LarocaAlerta {
    static template = "laroca_inventario.Confirmar";
    static props = {
        ...LarocaAlerta.props,
        botonCancelar: { type: String, optional: true },
        onConfirmar: Function,
    };

    confirmar() {
        this.props.close();
        this.props.onConfirmar();
    }
}

// "Cerrar sesión" pregunta antes de salir
registry.category("user_menuitems").add(
    "log_out",
    (env) => {
        let ruta = "/web/session/logout";
        if (env.services.pwa?.isScopedApp) {
            ruta += `?redirect=${encodeURIComponent(env.services.pwa.startUrl)}`;
        }
        return {
            type: "item",
            id: "logout",
            description: _t("Cerrar sesión"),
            callback: () => {
                env.services.dialog.add(LarocaConfirmar, {
                    tipo: "warning",
                    titulo: _t("¿Cerrar sesión?"),
                    texto: _t("Vas a salir del sistema. Para volver a entrar necesitás tu usuario y contraseña."),
                    detalle: [],
                    boton: _t("Sí, cerrar sesión"),
                    botonCancelar: _t("Cancelar"),
                    onConfirmar: () => {
                        browser.location.href = ruta;
                    },
                });
            },
            sequence: 70,
        };
    },
    { force: true }
);
