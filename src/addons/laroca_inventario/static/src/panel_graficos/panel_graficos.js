/** @odoo-module **/
/**
 * Gráficos del Panel general de La Roca.
 *
 * Componente OWL (el framework de interfaz propio de Odoo) que se usa en la vista
 * de los paneles con <widget name="laroca_panel_graficos" modo="admin|encargado"/>.
 * Pide los datos al servidor
 * (método Python laroca.panel.get_datos_graficos) y los dibuja con Chart.js, la
 * misma librería que usan los gráficos nativos de Odoo.
 */
import { Component, onMounted, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const COLORES = { critico: "#dc3545", bajo: "#f0ad4e", suficiente: "#28a745" };

export class LarocaPanelGraficos extends Component {
    static template = "laroca_inventario.PanelGraficos";
    static props = { ...standardWidgetProps, modo: { type: String, optional: true } };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.lienzoEstados = useRef("estados");
        this.lienzoEntregas = useRef("entregas");
        this.graficos = [];
        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            this.datos = await this.orm.call("laroca.panel", "get_datos_graficos", []);
        });
        onMounted(() => this.dibujar());
        onWillUnmount(() => this.graficos.forEach((grafico) => grafico.destroy()));
    }

    get esEncargado() {
        return this.props.modo === "encargado";
    }

    get hayEntregas() {
        return this.datos.entregas.unidades.some((valor) => valor > 0);
    }

    dibujar() {
        const { entregas } = this.datos;
        // 1) Estado del inventario: dona para el encargado, barras por gasolinera para el administrador
        this.graficos.push(this.esEncargado ? this.graficoDona() : this.graficoPorGasolinera());
        // 2) Unidades entregadas por mes
        if (this.lienzoEntregas.el) {
            this.graficos.push(
                new window.Chart(this.lienzoEntregas.el, {
                    type: "bar",
                    data: {
                        labels: entregas.labels,
                        datasets: [{
                            label: this.esEncargado ? "Unidades recibidas" : "Unidades entregadas",
                            data: entregas.unidades,
                            backgroundColor: "#0B3D91",
                        }],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
                        plugins: { legend: { display: false } },
                    },
                })
            );
        }
    }

    graficoDona() {
        const { estados, totales } = this.datos;
        return new window.Chart(this.lienzoEstados.el, {
            type: "doughnut",
            data: {
                labels: estados.series.map((serie) => serie.label),
                datasets: [{
                    data: estados.series.map((serie) => totales[serie.key]),
                    backgroundColor: estados.series.map((serie) => COLORES[serie.key]),
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: "bottom" } },
                // Clic en un color: abre los productos en ese estado
                onClick: (_evento, elementos) => {
                    if (elementos.length) {
                        this.abrirPorEstado(estados.series[elementos[0].index].key);
                    }
                },
            },
        });
    }

    graficoPorGasolinera() {
        const { estados } = this.datos;
        return new window.Chart(this.lienzoEstados.el, {
            type: "bar",
            data: {
                labels: estados.labels,
                datasets: estados.series.map((serie) => ({
                    label: serie.label,
                    data: serie.data,
                    backgroundColor: COLORES[serie.key],
                })),
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { x: { stacked: true }, y: { stacked: true, ticks: { precision: 0 } } },
                plugins: { legend: { position: "bottom" } },
                // Clic en una barra: abre el inventario de esa gasolinera
                onClick: (_evento, elementos) => {
                    if (elementos.length) {
                        this.abrirInventario(estados.ids[elementos[0].index]);
                    }
                },
            },
        });
    }

    abrirPorEstado(estado) {
        const filtros = { critico: "criticos", bajo: "bajos", suficiente: "suficientes" };
        this.action.doAction("laroca_inventario.action_laroca_inventario", {
            additionalContext: { [`search_default_${filtros[estado]}`]: 1 },
        });
    }

    abrirInventario(gasolineraId) {
        this.action.doAction("laroca_inventario.action_laroca_inventario", {
            additionalContext: { search_default_gasolinera_id: gasolineraId, search_default_pendientes: 1 },
        });
    }
}

registry.category("view_widgets").add("laroca_panel_graficos", {
    component: LarocaPanelGraficos,
    extractProps: ({ attrs }) => ({ modo: attrs.modo || "admin" }),
});
