# Etapa 3 — Entregas desde la bodega e historial

> **En pocas palabras:** el administrador prepara una **entrega** con lo que necesita una
> gasolinera, imprime una **hoja** para el repartidor y, cuando llega, el encargado
> **confirma lo que recibió**. El inventario se actualiza solo y queda el historial.

![Una entrega en camino](capturas/10_entrega.png)

## Cómo funciona una entrega

```
 Sugerencias  →  Borrador  →  En camino  →  Entregada
 (qué llevar)    (se ajusta)   (se envía)    (el encargado confirma)
```

1. **Crear**: desde *Sugerencias* se eligen productos y se pulsa **Crear entrega**.
2. **Revisar**: se pueden cambiar cantidades, fecha y responsable.
3. **Confirmar y enviar**: el sistema verifica que haya productos en la bodega, los
   **aparta** para esa entrega y **avisa al encargado**.
4. **Imprimir hoja**: un PDF con la lista de productos y espacio para firmas.
5. **Confirmar recepción**: el encargado revisa lo que llegó. Si faltó algo, lo corrige y
   el sistema lo vuelve a sugerir para la próxima entrega.

## ¿Para qué le sirve a Grupo La Roca?
Cada visita queda **planificada y registrada**: qué se llevó, a dónde, cuándo y quién lo
recibió. Se acabaron las dudas de "¿eso ya se mandó?".

## ¿Cómo probarlo?
1. Entrá como **`encargado.sur`** (desde el celular si podés).
2. **Abastecimiento → Entregas** → abrí **ENT-00004** (está en camino).
3. Tocá el botón verde **Confirmar recepción**, bajá la cantidad de un producto y confirmá.
4. Mirá el **Inventario**: las cantidades subieron.
5. Como **`administrador`**: **Sugerencias** → marcá productos → **Crear entrega** →
   **Confirmar y enviar** → **Imprimir hoja**.
6. **Abastecimiento → Historial de abastecimientos**: todo lo entregado.

![Entrega en el celular](capturas/22_movil_entrega.png)

## ¿Qué comprobamos?
- 9 pruebas automáticas nuevas (37 en total en esa etapa), todas correctas: entregas
  completas y parciales, cancelaciones, permisos y la hoja en PDF.
- Una prueba encontró un **error que podía duplicar entregas** y se corrigió.

## ¿Qué falta o hay que confirmar con la empresa?
- No se manejan rutas ni vehículos; el repartidor firma la hoja impresa.
- Si el encargado debe poder **rechazar productos dañados** (hoy registra que recibió menos).

---

## Anexo técnico (para el equipo de desarrollo)

> Esta parte usa términos técnicos: es para quien programa o explica el código en la defensa.
> Se escribió durante la etapa; algunos pendientes que figuran aquí ya se resolvieron
> (ver "Actualizaciones posteriores" y [Mejoras](MEJORAS.md)).

**Fecha:** 1 de octubre de 2026 · **Estado:** lista para revisión del equipo.

Cubre el paso 6 del flujo propuesto ("al realizar la entrega, se registra el abastecimiento
y se actualiza el historial") y los carriles "Administrador" y "Personal de entrega" del
BPMN propuesto (Figura 2): revisar sugerencias, confirmar productos y cantidades, organizar
la entrega, preparar, trasladar, entregar y confirmar.

---

### 1. Qué se hizo

#### Flujo de una entrega

```
 Sugerencias ──Crear entrega──▶ Borrador ──Confirmar y enviar──▶ En camino ──Confirmar recepción──▶ Entregada
 (administrador)               (ajustar cantidades)  (administrador)          (encargado o administrador)
                                     └──────────────── Cancelar ─────────────────┘
```

1. **Crear**: desde **Abastecimiento → Sugerencias** se seleccionan productos y se pulsa
   **Crear entrega** (una entrega por gasolinera), o desde la ficha de la gasolinera con
   **Preparar entrega**. Las cantidades salen de la cantidad sugerida y se pueden ajustar.
   Lo que ya está en otra entrega no se vuelve a sugerir (columna "Ya en entrega").
2. **Confirmar y enviar** (administrador):
   - Valida que haya stock suficiente en la Bodega Central.
   - Crea una **transferencia interna nativa de Odoo** (Bodega Central → Gasolinera), que **reserva** el stock.
   - Las alertas de esos productos pasan a **En proceso**.
   - Avisa al **encargado** en su bandeja de Odoo con la lista de productos.
3. **Imprimir hoja** (PDF): productos, cantidades, casilla "Preparado ✓" y firmas de quien
   entrega y quien recibe.
4. **Confirmar recepción** (encargado de esa gasolinera o administrador):
   - Asistente con lo enviado; si falta algo se corrige la cantidad recibida.
   - Se valida la transferencia de Odoo, el stock de la gasolinera sube y el de la bodega baja.
   - Las alertas se **resuelven solas**. Si la entrega fue parcial y sigue bajo, la alerta vuelve a "Abierta".
   - Se publica un mensaje en el canal del administrador.
5. **Cancelar** (administrador): libera la reserva en bodega y las alertas vuelven a "Abierta".

#### Historial
- **Abastecimiento → Entregas**: todas las entregas con filtros por estado, fecha y
  gasolinera, y vista de **calendario** por fecha programada.
- **Abastecimiento → Historial de abastecimientos**: producto por producto lo entregado, con
  vista de **tabla dinámica** (gasolinera × mes). Es la base de los reportes de la Etapa 4.
- Cada entrega tiene su propio historial (chatter): quién la confirmó, cambios de estado y mensajes.
- La gasolinera muestra el botón **Entregas** y cada producto conserva sus **Movimientos**.

#### Permisos

| Acción | Encargado | Administrador |
|---|---|---|
| Ver entregas | Solo de sus gasolineras | Todas |
| Crear, editar, confirmar, cancelar | No | Sí |
| Confirmar recepción | Solo de sus gasolineras | Sí |
| Ver la transferencia nativa de Odoo | No | Sí |

---

### 2. Dónde está el código

| Archivo | Contenido |
|---|---|
| `models/laroca_entrega.py` | Modelos `laroca.entrega` y `laroca.entrega.linea`: flujo, transferencia nativa, permisos, avisos |
| `wizard/recepcion.py` | Asistente "Confirmar recepción" |
| `models/laroca_inventario.py` | `cantidad_en_entrega` y `action_crear_entregas` (desde sugerencias) |
| `models/laroca_alerta.py` | Nuevo estado "En proceso" y vínculo con la entrega |
| `models/stock_warehouse.py` | Botones "Preparar entrega" y "Entregas" de la gasolinera |
| `views/entrega_views.xml` | Lista, formulario, calendario, búsqueda, historial (lista y tabla dinámica), asistente |
| `report/entrega_report.xml` | Hoja de entrega en PDF |
| `tests/test_entregas.py` | 9 pruebas de esta etapa |
| `laroca_datos_prueba/models/datos_prueba.py` | Entregas ficticias (`_datos_prueba_cargar_entregas`) |

---

### 3. Cómo probarlo

En tu base ya hay entregas de ejemplo:

| Entrega | Gasolinera | Estado |
|---|---|---|
| ENT-00001 | La Roca Norte | Entregada (historial) |
| ENT-00002 | La Roca Oriente | Entregada (historial) |
| ENT-00003 | La Roca Centro | Entregada (la recibí al probar, como `encargado.centro`) |
| ENT-00004 | La Roca Sur | **En camino**: lista para que la recibas |

1. **Encargado** `encargado.sur`: en la bandeja de Conversaciones está el aviso de ENT-00004.
   Abrir **Abastecimiento → Entregas → ENT-00004 → Confirmar recepción**, bajar la cantidad
   de un producto (recepción parcial) y confirmar. Revisar en Inventario que el stock subió
   y en Alertas qué quedó resuelto y qué volvió a "Abierta".
2. **Administrador** `administrador`:
   - **Abastecimiento → Sugerencias**: marcar algunos productos → **Crear entrega**.
     Ajustar una cantidad → **Confirmar y enviar** → **Imprimir hoja**.
   - Probar a pedir más de lo que hay en bodega: muestra el error con el detalle.
   - **Cancelar** una entrega en camino: las alertas vuelven a "Abierta".
   - **Historial de abastecimientos** → vista de tabla dinámica.
   - Botón **Transferencia** en una entrega: la operación nativa de Odoo que hay detrás.
3. Pruebas automáticas: `./scripts/pruebas.sh` (37 pruebas en total).

---

### 4. Qué se probó y qué falta

#### Probado (1 de octubre de 2026)
**Automático** (37 pruebas, 0 fallos; 9 nuevas):
- Crear desde sugerencias con las cantidades sugeridas; no se duplica lo que ya está en una entrega.
- Flujo completo:
  - La transferencia nativa sale de la bodega y llega a la gasolinera, y reserva el stock.
  - Las alertas pasan a "en proceso" y el encargado queda notificado.
  - La recepción la hace el encargado: el stock de la gasolinera y el de la bodega quedan correctos y las alertas se resuelven.
- Recepción parcial: sin pedido pendiente (backorder) y la alerta vuelve a "Abierta".
- Sin stock en bodega, la confirmación se rechaza; al cancelar se libera la reserva y se reabren las alertas.
- Permisos: el encargado no confirma ni crea entregas, otro encargado no ve ni recibe la
  entrega ajena, no se puede recibir más de lo enviado ni borrar una entrega entregada.
- La hoja de entrega se genera.

**Sobre la base real (con RPC, como la interfaz)**:
- Actualización sin perder datos; entregas de ejemplo creadas.
- `encargado.centro` recibió ENT-00003: sus 6 productos pendientes pasaron a suficiente, se
  publicó el mensaje en el canal y no pudo confirmar entregas (solo el administrador).
- PDF real generado con wkhtmltopdf y revisado (1 página, logo, tabla y firmas).
- Instalación desde cero en una base temporal: correcta.

**Corregido durante la etapa:** el campo "Ya en entrega" quedaba guardado en memoria con un
valor viejo dentro de la misma operación, lo que podía **duplicar entregas**. Ahora se
recalcula cada vez que cambia una entrega (lo detectó una prueba automática).

#### No probado / pendiente
- **Revisión visual en el navegador** (el panel de la herramienta siguió oculto): revisar
  el formulario de entrega, el asistente de recepción y el calendario.
- Las entregas no manejan rutas ni vehículos; el "personal de entrega" se registra como
  "Responsable" (usuario de Odoo). Si el repartidor no tiene usuario, firma la hoja impresa.
- No hay notificación por correo ni WhatsApp (solo dentro de Odoo).
- Pendiente de confirmar con la empresa: si el encargado puede rechazar productos dañados
  (hoy solo registra menos cantidad recibida) y cada cuánto se hacen las rutas de entrega.

#### Próximas etapas
4. **Panel general** (mockup 10.1): gasolineras, productos, productos con stock bajo,
   abastecimientos del mes y alertas críticas; **reportes** (inventario por gasolinera,
   productos con poca existencia, abastecimientos por período).
5. Despliegue en la nube, manual de usuario y pruebas integrales.
