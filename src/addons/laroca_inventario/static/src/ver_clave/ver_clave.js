/** @odoo-module **/
/**
 * Ojito para ver u ocultar la contraseña en todos los campos de contraseña del sistema
 * (crear usuario, cambiar contraseña, "Mi perfil").
 */
import { useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { CharField } from "@web/views/fields/char/char_field";

patch(CharField.prototype, {
    setup() {
        super.setup(...arguments);
        this.larocaClave = useState({ ver: false });
    },
    larocaAlternarClave() {
        this.larocaClave.ver = !this.larocaClave.ver;
    },
});
