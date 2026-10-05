# Guion del video demo (5–7 minutos)

**Objetivo (lineamientos):** mostrar el flujo completo del sistema y explicar el valor para
la empresa. Duración total: **6:30 aprox.**

**Preparación antes de grabar**
- Reinstalar los datos de prueba para empezar limpio: `docker compose down -v && ./scripts/inicializar.sh`.
- Dos ventanas: computadora (administrador) y teléfono o vista de teléfono del navegador
  (F12 → modo dispositivo) para el encargado.
- Tener abierto http://localhost:8025 (buzón de correo de prueba).
- Grabar a 1080p, con el zoom del navegador al 110 %.
- Reemplazar *[Integrante X]* por quien narra cada parte (son 4 integrantes: una parte cada uno).

---

| Tiempo | Pantalla | Qué se dice / hace |
|---|---|---|
| **0:00 – 0:40** | Portada (logo UDB + Grupo La Roca) → foto o esquema de WhatsApp | *[Integrante 1]* "Grupo La Roca administra varias gasolineras. Hoy las sucursales piden productos por WhatsApp: la información queda dispersa y no se sabe qué llevar a cada una. Construimos un sistema web, sobre Odoo Community, que centraliza el inventario y organiza el abastecimiento." |
| **0:40 – 1:10** | Diagrama de arquitectura (Figura 3 del documento) o `README.md` | *[Integrante 1]* "Usamos Odoo 18 con PostgreSQL en Docker. Aprovechamos el inventario nativo de Odoo y desarrollamos un módulo propio en Python, `laroca_inventario`, con gasolineras, roles, alertas, entregas, panel y reportes." |
| **1:10 – 2:20** | **Teléfono, encargado** (`encargado.norte`) | *[Integrante 2]* Iniciar sesión → **Mi gasolinera**: su panel propio, con botones grandes y lo que se le está acabando. Tocar **Vender**, intentar vender 99 llaveros → alerta roja **"Stock insuficiente"**; corregir a 5 → **Registrar venta** → alerta **"¡Venta registrada!"**. Tocar **Pedir productos**, escribir 50 llaveros → **Enviar pedido** → alerta **"¡Tu pedido se realizó!"**. "El encargado ya no manda WhatsApp: vende y pide aquí, y el sistema avisa solo." |
| **2:20 – 3:00** | **Computadora, administrador** (`administrador`) | *[Integrante 3]* **Panel del administrador** (distinto al del encargado): tarjetas, seguimiento de gasolineras, gráfico (mostrar que la gasolinera del encargado cambió). Abrir el globo de Conversaciones → canal **Alertas de abastecimiento** con el mensaje recién llegado. Mostrar el correo en http://localhost:8025. |
| **3:00 – 4:10** | Pedido → Entrega → PDF | *[Integrante 3]* **Pedidos por atender**: abrir el pedido de 50 llaveros → **Aprobar y preparar entrega** → **Confirmar y enviar** → **Imprimir hoja** (mostrar la hoja con gasolinera, lugar y pedido). Después, **Preparar entrega** del panel: "hoy les llevo llaveros extra" → − y + → **Generar PDF** / **Generar Excel**. Mencionar **Sugerencias**: "el sistema también calcula cuánto llevar aunque nadie lo pida". |
| **4:10 – 4:50** | **Teléfono, encargado** | *[Integrante 2]* Abrir la entrega en camino → botón verde **Confirmar recepción** → bajar 1 unidad de un producto (llegó incompleto) → confirmar. Volver al inventario: stock actualizado, estado en verde. |
| **4:50 – 5:40** | Computadora, administrador | *[Integrante 4]* Panel → **Actualizar**: el abastecimiento del mes subió. **Historial de abastecimientos** (tabla dinámica). **Reportes → Imprimir reportes → Productos con poca existencia** (PDF). Mencionar **Importar desde Excel** para cargar los datos reales. |
| **5:40 – 6:30** | Pantalla final con resumen | *[Integrante 4]* "Valor para la empresa: información centralizada y en tiempo real; alertas automáticas en lugar de mensajes; cantidades sugeridas para cada visita; historial y reportes para decidir. Funciona en computadora y teléfono." Mencionar el enlace del sistema y el repositorio de GitHub. Cierre. |

---

## Frases clave para la explicación técnica (defensa)
- **Gasolinera = almacén nativo de Odoo** (`stock.warehouse`): reutiliza ubicaciones y movimientos.
- **Acceso por gasolinera** con reglas de registro (`ir.rule`): el encargado no puede ver
  otras sucursales ni escribiendo la URL.
- **Cada cambio de stock es un ajuste de inventario nativo**: queda en el historial.
- **Alertas** (`laroca.alerta`): se crean, escalan y resuelven solas; tarea programada de respaldo cada hora y resumen diario.
- **Entregas** = transferencias internas nativas: reservan stock en bodega y lo mueven al confirmar la recepción.
- **Panel**: vista de Odoo + componente OWL (framework de Odoo, no React) con Chart.js.
- **Calidad**: 56 pruebas automáticas (`./scripts/pruebas.sh`).

## Checklist después de grabar
- [ ] Duración entre 5 y 7 minutos.
- [ ] Se ve el flujo completo: actualizar → alerta → sugerencia → entrega → recepción → reporte.
- [ ] Audio claro; sin datos reales ni contraseñas visibles.
- [ ] Subir el video y poner el enlace en `README.md`.
