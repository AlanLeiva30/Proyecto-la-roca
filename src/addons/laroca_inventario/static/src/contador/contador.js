/** @odoo-module **/
/**
 * Campos numéricos con botones − y + (contador).
 *
 * Uso en las vistas:
 *   <field name="cantidad" widget="laroca_contador"/>
 *   <field name="cantidad" widget="laroca_contador" options="{'maximo': 'disponible'}"/>
 *       → no deja pasar de lo que hay y avisa "¡Ya no hay más!"
 *   <field name="cantidad" widget="laroca_contador" options="{'siempre': true}"/>
 *       → en las pantallas rápidas: los botones se ven en todos los renglones, sin tener que
 *         tocar primero el renglón (Odoo muestra como "solo lectura" los que no se están editando)
 *   <field name="cantidad_sugerida" widget="laroca_usar_sugerido" options="{'destino': 'cantidad'}"/>
 *       → el número se puede tocar y se copia en la columna "destino"
 */
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FloatField, floatField } from "@web/views/fields/float/float_field";
import { LarocaAlerta } from "../alerta/alerta";
import { formatFloat } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class LarocaContador extends FloatField {
    static template = "laroca_inventario.Contador";
    static props = {
        ...FloatField.props,
        maximo: { type: String, optional: true },
        paso: { type: Number, optional: true },
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialog = useService("dialog");
    }

    /** Al escribir un número mayor a lo que hay: alerta grande y se deja lo máximo posible. */
    parse(texto) {
        const valor = super.parse(texto);
        const tope = this.tope;
        if (tope !== null && valor > tope) {
            this.alertaSinStock(valor);
            return tope;
        }
        return valor < 0 ? 0 : valor;
    }

    alertaSinStock(pedido) {
        const producto = this.nombreProducto;
        this.dialog.add(LarocaAlerta, {
            tipo: "warning",
            titulo: _t("¡No hay más stock!"),
            texto: producto
                ? _t("Querés %(pedido)s, pero solo hay %(hay)s de %(producto)s.", { pedido, hay: this.tope, producto })
                : _t("Querés %(pedido)s, pero solo hay %(hay)s.", { pedido, hay: this.tope }),
            detalle: [_t("Se dejó la cantidad en %s, lo máximo que hay.", this.tope)],
            boton: _t("Entendido"),
        });
    }

    get tope() {
        return this.props.maximo ? this.props.record.data[this.props.maximo] || 0 : null;
    }

    get nombreProducto() {
        const producto = this.props.record.data.product_id;
        return producto ? producto.display_name || producto[1] || "" : "";
    }

    avisarSinStock() {
        const producto = this.nombreProducto;
        this.notification.add(
            producto
                ? _t("Solo hay %(cantidad)s de %(producto)s.", { cantidad: this.tope, producto })
                : _t("Solo hay %s.", this.tope),
            { title: _t("¡Ya no hay más!"), type: "warning" }
        );
    }

    async sumar(signo) {
        const paso = this.props.paso || 1;
        const actual = this.value || 0;
        let nuevo = Math.max(0, actual + signo * paso);
        const tope = this.tope;
        if (tope !== null && nuevo > tope) {
            this.alertaSinStock(nuevo);
            if (actual >= tope) {
                return;
            }
            nuevo = tope;
        }
        await this.props.record.update({ [this.props.name]: nuevo });
        if (tope !== null && signo > 0 && nuevo === tope) {
            this.avisarSinStock();
        }
    }
}

registry.category("fields").add("laroca_contador", {
    ...floatField,
    component: LarocaContador,
    displayName: _t("Contador con − y +"),
    extractProps: (fieldInfo, dynamicInfo) => {
        const props = {
            ...floatField.extractProps(fieldInfo, dynamicInfo),
            maximo: fieldInfo.options.maximo,
            paso: fieldInfo.options.paso,
        };
        if (fieldInfo.options.siempre) {
            // Solo lectura únicamente si la vista lo pide (no por "renglón sin editar")
            props.readonly = dynamicInfo.readonly;
        }
        return props;
    },
});

/** Número sugerido que, al tocarlo, se copia en otra columna (por ejemplo "Pido"). */
export class LarocaUsarSugerido extends Component {
    static template = "laroca_inventario.UsarSugerido";
    static props = { ...standardFieldProps, destino: { type: String } };

    get valor() {
        return this.props.record.data[this.props.name] || 0;
    }

    get texto() {
        return formatFloat(this.valor, { digits: [16, 0] });
    }

    get usado() {
        return this.valor > 0 && this.props.record.data[this.props.destino] === this.valor;
    }

    usar() {
        this.props.record.update({ [this.props.destino]: this.valor });
    }
}

registry.category("fields").add("laroca_usar_sugerido", {
    component: LarocaUsarSugerido,
    displayName: _t("Sugerido que se puede tocar"),
    supportedTypes: ["float"],
    extractProps: ({ options }) => ({ destino: options.destino }),
});
