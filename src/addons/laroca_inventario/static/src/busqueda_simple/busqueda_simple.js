/** @odoo-module **/
/**
 * Buscador simple para los usuarios de La Roca.
 *
 * Odoo permite "editar" un filtro tocándolo (abre el editor de condiciones) y crear filtros
 * personalizados. Para encargados y administradores de La Roca eso confunde: se desactiva y
 * los filtros quedan como etiquetas que solo se quitan con la ✕. Las opciones simples están
 * en el panel de la izquierda (Estado, Gasolinera...).
 * El usuario técnico de Odoo ("admin") y el modo desarrollador conservan todo.
 */
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";

function busquedaAvanzada(env) {
    return Boolean(user.isSystem || env.debug);
}

patch(SearchBar.prototype, {
    onFacetLabelClick(target, facet) {
        if (busquedaAvanzada(this.env)) {
            return super.onFacetLabelClick(...arguments);
        }
    },
});

patch(SearchBarMenu.prototype, {
    get larocaAvanzado() {
        return busquedaAvanzada(this.env);
    },
    async onAddCustomFilterClick() {
        if (busquedaAvanzada(this.env)) {
            return super.onAddCustomFilterClick(...arguments);
        }
    },
});
