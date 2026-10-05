# Declaración y registro del uso de inteligencia artificial

Según los lineamientos del proyecto (sección 3), se declara el uso de IA y se anexan
los prompts utilizados.

## Declaración

El equipo usó **Claude (Anthropic), mediante Claude Code**, como asistente de
programación para analizar los documentos del proyecto, generar el código base de los
módulos de Odoo, los scripts de Docker, las pruebas automáticas y un primer borrador de
la documentación. **El equipo debe revisar, probar y adaptar todo el código** y ser capaz
de explicarlo en la defensa. La IA no reemplaza las entrevistas con la empresa ni las
decisiones del equipo.

> Antes de entregar, cada integrante debe revisar los archivos de su área y anotar abajo
> qué cambió o validó (columna "Revisión del equipo").

## Registro por etapa

### Etapa 1 — Entorno y base funcional (1 de octubre de 2026)

**Herramienta:** Claude Code (modelo Claude Opus 5.5), con acceso a la carpeta del proyecto y a la terminal.

**Prompt utilizado (textual):**

> Leé los dos PDF adjuntos y ayudame a implementar el sistema de inventario y
> abastecimiento de Grupo La Roca usando Odoo Community, Python, PostgreSQL y Docker.
> Quiero que construyás una base funcional que yo pueda revisar y probar. Después te
> iré indicando qué modificar, corregir o agregar. Trabajá por etapas y esperá mis
> observaciones antes de pasar a la siguiente.
> Tengo una Mac M4 con Docker instalado. Si tenés acceso al proyecto y a la terminal,
> creá los archivos y ejecutá los comandos necesarios. Si no, indicame exactamente qué
> debo hacer.
> Primero prepará el entorno y una base con:
> * Inicio de sesión.
> * Administrador y encargado de sucursal.
> * Registro de gasolineras.
> * Catálogo de productos.
> * Inventario por sucursal, con acceso limitado según el usuario.
>
> Aprovechá las funciones nativas de Odoo y usá módulos personalizados para lo que haga
> falta. No agregués React ni Node.js. Conservá los datos con volúmenes de Docker y usá
> datos ficticios para las pruebas.
> Cuando esa base funcione y yo la revise, continuaremos con stock mínimo, alertas
> automáticas, sugerencias de abastecimiento, entregas, historial, panel y reportes,
> siguiendo los PDF.
> Explicame brevemente qué hiciste en cada etapa, dónde está el código y cómo probarlo,
> para que pueda entenderlo y decidir los cambios. Registrá el uso de IA y distinguí lo
> probado de lo pendiente.
> Empezá revisando los documentos y comprobando el entorno.
>
> Trabajá de forma autónoma hasta dejar la base funcional y probada. Resolvé las
> decisiones técnicas rutinarias y preguntame únicamente cuando falte información
> indispensable. Al terminar, indicame cómo abrir el sistema, qué funciona y qué queda
> pendiente. Yo probaré la base y te indicaré las modificaciones.

Archivos adjuntos al prompt: `docs/referencias/Fase1_Grupo_La_Roca.pdf` y
`docs/referencias/Lineamientos_proyecto_2026.pdf`.

**Qué generó la IA:**

| Elemento | Archivos | Revisión del equipo |
|---|---|---|
| Entorno Docker y configuración | `docker-compose.yml`, `config/odoo.conf`, `.env.example`, `scripts/*.sh` | _pendiente_ |
| Módulo principal | `src/addons/laroca_inventario/` (modelos, seguridad, vistas, asistente) | _pendiente_ |
| Pruebas automáticas | `src/addons/laroca_inventario/tests/test_inventario.py` | _pendiente_ |
| Datos ficticios | `src/addons/laroca_datos_prueba/` | _pendiente_ |
| Ícono y logo ficticio | `static/description/icon.png`, `static/img/logo.png` (generados con Python/Pillow) | _pendiente_ |
| Documentación | `README.md`, `DEPLOY.md`, `docs/ETAPA_1.md`, este archivo | _pendiente_ |

**Qué verificó la IA** (detalle en `docs/ETAPA_1.md`, sección 4): instalación limpia,
12 pruebas automáticas sin fallos, pruebas manuales en navegador con ambos roles y
verificación por RPC de menús y permisos.

**Errores encontrados y corregidos durante la etapa:**
- Un campo (`property_warehouse_id`) que no existe en Odoo 18 sin el módulo de ventas → eliminado.
- Una llamada a la activación del idioma con argumentos incorrectos → reemplazada por `--load-language`.
- El script de inicialización no pasaba la conexión a la base en `odoo shell` → corregido.
- Odoo traía el **registro público de cuentas** activo y el menú "Aplicaciones" visible
  para encargados → desactivado y oculto.
- La actualización del módulo de datos podía **sobrescribir existencias** → datos marcados `noupdate`.

### Etapa 2 — Stock mínimo, estados, alertas y sugerencias (1 de octubre de 2026)

**Herramienta:** Claude Code (modelo Claude Opus 5.5).

**Prompts utilizados (textuales):**

> sigue trabajando

(Contexto previo en la misma sesión: el prompt de la Etapa 1, que define las etapas
siguientes: "stock mínimo, alertas automáticas, sugerencias de abastecimiento, entregas,
historial, panel y reportes, siguiendo los PDF".)

**Qué generó la IA:**

| Elemento | Archivos | Revisión del equipo |
|---|---|---|
| Niveles, estados y sugerencia | `models/laroca_inventario.py`, `models/product.py`, `models/res_company.py` | _pendiente_ |
| Alertas y notificaciones | `models/laroca_alerta.py`, `data/laroca_alertas_data.xml` | _pendiente_ |
| Pantallas | `views/abastecimiento_views.xml` y cambios en vistas existentes | _pendiente_ |
| Pruebas | `tests/test_abastecimiento.py` | _pendiente_ |
| Datos ficticios de mínimos | `laroca_datos_prueba/models/datos_prueba.py`, `data/niveles.xml` | _pendiente_ |
| Documentación | `docs/ETAPA_2.md` | _pendiente_ |

**Decisiones tomadas por la IA (revisables por el equipo):**
- Umbral crítico = 50 % del mínimo (deducido de los ejemplos del mockup 10.2).
- Si no hay stock objetivo, se repone hasta el doble del mínimo.
- Notificaciones por el canal de Conversaciones de Odoo (no requiere servidor de correo).
- Mínimos y objetivos guardados en el modelo propio en lugar de las reglas de
  reabastecimiento nativas de Odoo, para evitar que el planificador de Odoo genere
  órdenes automáticas no deseadas.

**Errores encontrados y corregidos:** dos pruebas escritas con supuestos incorrectos
(objetivo menor que el mínimo; línea nueva sin stock que ya nace con alerta). El código
del sistema se comportaba bien; se corrigieron las pruebas.

### Etapa 3 — Entregas e historial de abastecimientos (1 de octubre de 2026)

**Herramienta:** Claude Code (modelo Claude Opus 5.5).

**Prompts utilizados (textuales):** `que has hecho` (pedido de resumen) y luego `dale`
(autorización para continuar con la siguiente etapa del plan: entregas e historial).

**Qué generó la IA:**

| Elemento | Archivos | Revisión del equipo |
|---|---|---|
| Entregas y recepción | `models/laroca_entrega.py`, `wizard/recepcion.py` | _pendiente_ |
| Integración con sugerencias, alertas y gasolineras | `models/laroca_inventario.py`, `models/laroca_alerta.py`, `models/stock_warehouse.py` | _pendiente_ |
| Pantallas e informe PDF | `views/entrega_views.xml`, `report/entrega_report.xml` | _pendiente_ |
| Pruebas | `tests/test_entregas.py` | _pendiente_ |
| Entregas ficticias | `laroca_datos_prueba/models/datos_prueba.py`, `data/entregas.xml` | _pendiente_ |
| Documentación | `docs/ETAPA_3.md` | _pendiente_ |

**Decisiones tomadas por la IA (revisables):**
- Cada entrega usa una transferencia interna nativa de Odoo (reserva y movimiento real de stock).
- Recepción parcial sin "pedido pendiente" (backorder): lo que no llegó se vuelve a sugerir.
- Solo el administrador crea/confirma/cancela; el encargado solo confirma la recepción.

**Errores encontrados y corregidos:** caché del campo "Ya en entrega" (podía duplicar
entregas en una misma operación), detectado por una prueba automática.

### Etapa 4 — Panel general y reportes (1 de octubre de 2026)

**Herramienta:** Claude Code (modelo Claude Opus 5.5).

**Prompt utilizado (textual):** `y ahora` (interpretado como continuar con la siguiente
etapa del plan: panel y reportes).

**Qué generó la IA:**

| Elemento | Archivos | Revisión del equipo |
|---|---|---|
| Panel general | `models/laroca_panel.py`, `views/panel_reportes_views.xml` | _pendiente_ |
| Reportes PDF | `wizard/reporte.py`, `report/reporte_general.py`, `report/reporte_general.xml` | _pendiente_ |
| Gráficos y tablas dinámicas | `views/panel_reportes_views.xml` | _pendiente_ |
| Pruebas | `tests/test_panel_reportes.py` | _pendiente_ |
| Ejemplos de reportes | `docs/ejemplos_reportes/*.pdf` | _pendiente_ |
| Documentación | `docs/ETAPA_4.md` | _pendiente_ |

**Decisiones tomadas por la IA (revisables):**
- Panel con vistas nativas (sin JavaScript propio) para que el equipo pueda explicarlo.
- Tres reportes PDF basados en las preguntas de la sección 7 del documento
  ("¿Qué reportes o alertas serían más útiles?"): conviene validarlos con la empresa.

**Errores encontrados y corregidos:** etiquetas de estado invisibles en el PDF;
receptor "OdooBot" en las entregas de ejemplo.

### Mejoras — 8 mejoras elegidas por el equipo (1 de octubre de 2026)

**Herramienta:** Claude Code (modelo Claude Opus 5.5).

**Prompts utilizados (textuales):** `okaay eso lo dejmos para el final ahora vamos hacer mejoras`.
La IA propuso una lista de mejoras y el usuario seleccionó todas: conteo rápido, pulir
pantallas, fotos de productos, avisos por correo, gráficos en el panel, importar desde
Excel, valor del inventario, manual y guion de video.

**Qué generó la IA:** ver la tabla de `docs/MEJORAS.md` (todos los archivos, *revisión del
equipo pendiente*). Las ilustraciones de productos fueron generadas con código Python
(Pillow) por la IA; no se usaron imágenes de terceros. Las capturas de `docs/capturas/` se
tomaron automáticamente del sistema con datos ficticios.

**Decisiones tomadas por la IA (revisables):**
- Correo de prueba con Mailpit (no envía a internet); correo real pendiente de una cuenta.
- Gráficos con OWL (framework de Odoo) y Chart.js (incluido en Odoo): es el único JavaScript propio.
- Cantidades sin decimales (todos los productos se cuentan por unidad).
- Revisión visual con Chromium en Docker porque el navegador integrado de la herramienta
  no podía dibujar las pantallas.

**Errores encontrados y corregidos:** ver la tabla "Pulido de pantallas" de `docs/MEJORAS.md`.
El más importante: el encargado no podía abrir el formulario de una entrega (detectado en
la revisión visual, no por las pruebas; se agregó una prueba automática).

### Segunda ronda de mejoras: diseño, fotos reales y documentación sencilla (1 de octubre de 2026)

**Prompt utilizado (textual):**

> vaya me gusta ahora quiero que hagas la app mas amigable y bonita para el usuario y uses en el
> caso del catalgo imagenes reales de internete y les pongas descricioones y en reame lo hagas
> para que cualquier persona lo entienda aun si no sabe programar y igual en las fases que hyicimos

**Qué hizo la IA:**
- Diseño: colores de la marca, login más claro, accesos rápidos, tarjetas con color por estado,
  catálogo con foto grande y descripción (detalle en el anexo de `docs/MEJORAS.md`).
- **Imágenes reales**: buscó imágenes con **licencia libre que permite uso comercial** en
  Wikimedia Commons y Flickr (con Openverse), **pidió autorización al usuario antes de
  descargar**, eligió 9, las recortó y registró autores y licencias en `docs/CREDITOS_IMAGENES.md`.
  4 productos conservan su ilustración porque las fotos libres tenían marcas visibles.
  *Nota:* se descargaron 37 MB de candidatas (más que los ~4 MB estimados, porque 4 imágenes
  vinieron en tamaño original); se borraron después de elegir.
- Descripciones ficticias de los 13 productos.
- README y documentos de etapa reescritos para personas sin conocimientos técnicos; el detalle
  técnico quedó en anexos y en `docs/GUIA_TECNICA.md`.

**Revisión del equipo:** _pendiente_ (revisar textos, que las fotos sean adecuadas y los créditos).

### Gestión de usuarios por el administrador (2 de octubre de 2026)

**Prompt utilizado (textual):**

> vaya quiero que hagas lo siguiente quiero que el admi agrege y modifique a los usuarios tanto
> las contrasenas como otras cosas podrias???

**Qué generó la IA:** pantalla sencilla de usuarios (crear, modificar, rol, gasolineras,
contraseña inicial, cambiar contraseña, desactivar/reactivar) con protecciones de seguridad
y 7 pruebas automáticas (detalle en el anexo de `docs/MEJORAS.md`). Las 4 pruebas que fallaron
al principio tenían errores en la propia prueba (no en el sistema) y se corrigieron.

**Decisiones tomadas por la IA (revisables):** contraseña mínima de 8 caracteres; el
administrador de La Roca no puede modificar al usuario técnico `admin` ni quitarse su rol;
los usuarios se desactivan en lugar de borrarse, para conservar el historial.

**Revisión del equipo:** _pendiente_.

### Panel distinto para administrador y encargado (2 de octubre de 2026)

**Prompt utilizado (textual):**

> quiero que el admistrador tengo un panel distinto al de encargado  se podria eso

**Qué generó la IA:** dos pantallas de panel según el rol: "Panel del administrador" (centro de
control de todas las gasolineras, con seguimiento, alertas recientes y gasolineras sin
actualizar) y "Mi gasolinera" para el encargado (botones grandes, productos que se están
acabando, entregas por recibir, gráfico de dona). 3 pruebas nuevas; detalle en el anexo de
`docs/MEJORAS.md`.

**Decisiones tomadas por la IA (revisables):** qué mostrar en cada panel; el umbral de **7
días** para considerar una gasolinera "sin actualizar"; colores azul (administrador) y verde (encargado).

**Revisión del equipo:** _pendiente_.

### Ventas y pedidos del encargado (2 de octubre de 2026)

**Prompt utilizado (textual):**

> vaya quiero algo hoy que vos podes pedir producto al admistrador tipo nesecito 50 llaveros y el
> te los mande y que el encargado pueda pedir mas no modificar y tambien vender esos protuctos que
> tenga el sistema de venta en un panel tipo vende 5 llevaros y se vaya restando y que pueda pedir
> eso al admistrador

**Aclaración pedida por la IA:** qué no debe modificar el encargado. Respuesta del equipo:
"las dos cosas": ni el pedido una vez enviado ni el stock a mano.

**Qué generó la IA:** pedidos del encargado al administrador (con aprobación que crea la
entrega), pantalla de ventas que descuenta el stock, restricción de los conteos y correcciones
al administrador, paneles y reportes actualizados, datos ficticios y 10 pruebas nuevas
(detalle en el anexo de `docs/MEJORAS.md`).

**Decisiones tomadas por la IA (revisables):** el precio de venta es el del catálogo y el
encargado no lo cambia; no se registra forma de pago; las ventas no se borran (el administrador
las anula y el stock vuelve); el administrador también puede vender; un pedido rechazado no se
reabre (se hace otro).

**Revisión del equipo:** _pendiente_.

### Alertas estilo SweetAlert y pedido rápido (2 de octubre de 2026)

**Prompt utilizado (textual):**

> vaya cuando pida quiero quedia su pedio se arrealizado y que cuando venda y el sock es infiente
> tire una swith alert y igual cuando se realiza el pedido que sea rapido y sencillo esa parte

**Qué generó la IA:** alerta grande estilo SweetAlert hecha con OWL (sin librería externa),
usada en "¡Tu pedido se realizó!", "¡Venta registrada!" y "Stock insuficiente"; pantalla rápida
de pedido con "Completar con lo sugerido" y envío en un paso; pruebas y capturas (detalle en
`docs/MEJORAS.md`). Al verificar en pantalla encontró y corrigió un error de guardado en el celular.

**Decisiones tomadas por la IA (revisables):** no descargar SweetAlert (se imitó su estilo con
las herramientas de Odoo para no agregar dependencias); los pedidos ya no se arman como
borrador desde la lista (todo pasa por la pantalla rápida).

**Revisión del equipo:** _pendiente_.

### Contador − / +, "quedan" en tiempo real y sugerido (2 de octubre de 2026)

**Prompt utilizado (textual, con una captura de "Pedir productos"):**

> vaya en el caso de lo sugerido quiero que al precionarlo se ponga la cantia en automaitoco en el
> otro lado y el boton de los numero tengo como un contador de mas y menos para agregar o quitar eso
> de los numero lo quiero en todos lo que tenga numero para poder quitar o poner y que cuando pongas
> algo en el canso de ventas se vaya como quitan por ejemplo ay 20 de un prodcuto y pongo 5  quiero
> que esos 5 se reste del total tipo ay 20 llevo 5 y quedan 15 pero eso en tiempo real y cuando el
> producto llegue a 0 diga ya no hay mas un mensaje asi

**Qué generó la IA:** contador − / + para las cantidades, sugerido que se copia con un toque,
interruptor "Completar con lo sugerido" instantáneo, columna "Quedan" y aviso "¡Ya no hay más!"
al vender, 1 prueba nueva (detalle en `docs/MEJORAS.md`). Al probar en pantalla encontró por qué
"Completar con lo sugerido" no llenaba las cantidades (el interruptor de Odoo guardaba sin
recalcular) y lo corrigió.

**Decisiones tomadas por la IA (revisables):** el aviso al llegar a 0 es un mensaje en la esquina
y un texto en el renglón (no la alerta grande, para no interrumpir cada vez); en la lista de
mínimos el contador aparece al tocar el renglón.

**Revisión del equipo:** _pendiente_.

### Contador uniforme y alerta "no hay más stock" (2 de octubre de 2026)

**Prompt utilizado (textual):**

> me gusta pe el boton queda de mas queda escodido que quede uniforme todo y que al poner numero te
> tire un alterta que no hay ma stock

**Qué generó la IA:** reprodujo el problema a 1000 px de ancho (el "+" quedaba cortado), unificó el
tamaño del contador y los anchos de columna, y agregó la alerta grande al escribir más de lo que
hay (la cantidad queda en el máximo). Detalle en `docs/MEJORAS.md`.

**Decisiones tomadas por la IA (revisables):** al escribir de más, la cantidad se ajusta sola al
máximo disponible en lugar de borrarse.

**Revisión del equipo:** _pendiente_.

### Filtros simples (2 de octubre de 2026)

**Prompt utilizado (textual, con una captura del cuadro "Modificar condición"):**

> no me gusta ese filtro quitalo y solo pon opciones mas simples y no asi siento que el cliente se
> confundira

**Qué generó la IA:** desactivó el editor de condiciones y los filtros personalizados para los
usuarios de La Roca, y agregó opciones simples (Estado y Gasolinera) a la izquierda de las listas.
Detalle en `docs/MEJORAS.md`.

**Decisiones tomadas por la IA (revisables):** el usuario técnico `admin` y el modo desarrollador
siguen viendo las opciones avanzadas; las listas de Entregas, Pedidos y Ventas abren mostrando
"Todos"; Alertas abre en "Abierta".

**Revisión del equipo:** _pendiente_.

**Prompt de seguimiento (textual):**

> en todos los que salga con ese filtro modificalo

**Qué generó la IA:** revisó todas las pantallas, quitó los filtros y agrupaciones que venían
puestos, agregó el panel simple a historial, análisis y productos, y un buscador simple para
Movimientos. Encontró que los filtros viejos seguían guardados en la base y los limpió.

### Preparar entrega con hoja en PDF o Excel (2 de octubre de 2026)

**Prompt utilizado (textual):**

> en el admistrador quiero que hagas una panel que sea para agregar productos que el entregara y que
> se genere un pdf o excel que diga que productos llevara el tipo agrega tanto llaveros, tantas
> gorras y asi pero que se interetivo genere el pdf y que en ese pdf diga para que gasolinera,
> luegar y pedido

**Qué generó la IA:** pantalla "Preparar entrega" con contador, pedido opcional y sugeridos;
hoja PDF rediseñada y hoja Excel; 4 pruebas. Al probar con el pedido de ejemplo encontró que
"En bodega" no descontaba lo reservado para otras entregas y lo corrigió.

**Decisiones tomadas por la IA (revisables):** generar la hoja crea la entrega y, con "Enviar
ahora" (marcado por defecto), la deja En camino y avisa al encargado; las cantidades de un pedido
se limitan a lo disponible en bodega.

**Revisión del equipo:** _pendiente_.

### Bodega central visible y editable (3 de octubre de 2026)

**Prompt utilizado (textual):**

> agrega lo que te dije y quiero tambien que a los demas de las gasolinara le salga el sock de bogena
> y que yo pueda modificar eso como admistrador cuando yo resiva mis proyectos

**Qué generó la IA:** columna "En bodega" para los encargados, lista "Bodega central" y pantalla
para recibir mercadería o contar la bodega (solo administrador), 3 pruebas (detalle en
`docs/MEJORAS.md`).

**Decisiones tomadas por la IA (revisables):** los encargados ven lo **disponible** (descontando
lo reservado para otras entregas); recibir mercadería se registra como recepción de proveedor y
contar como ajuste de inventario, ambos visibles en Movimientos.

**Revisión del equipo:** _pendiente_.

**Prompt de seguimiento (textual):**

> vaya cuando sean pedidos solicitados eso si dejalos como antes que yo los envios y cuando sean que
> enviare tipo hoy voy a llevarles llaveros extras

**Qué generó la IA:** volvió el botón "Aprobar y preparar entrega" en los pedidos y dejó
"Preparar entrega" solo para envíos propios (sin pedido); pruebas actualizadas.

**Prompts de seguimiento (textuales):**

> y como agrego yo los productos ala boga central

> haz un panel para el

**Qué generó la IA:** explicó los pasos y luego hizo el panel de la bodega central con
"Producto nuevo" (crear y cargar unidades en un paso) y "Conviene comprar"; 2 pruebas.

**Decisiones tomadas por la IA (revisables):** "conviene comprar" compara lo disponible en bodega
con la suma de lo sugerido para todas las gasolineras; los encargados ven el panel sin botones
ni valores en dinero.
