# Uso de inteligencia artificial

## Declaración

Usamos **Claude Code** (asistente de programación de Anthropic; en esta sesión, el modelo
Claude Opus 5.5) para generar buena parte del código base del módulo de Odoo, los datos de
prueba, las pruebas automáticas y el borrador de la documentación. Nosotros definimos qué hacer
en cada paso, probamos el sistema en el navegador y pedimos correcciones cuando algo no
funcionaba o no nos gustaba. También usamos **ChatGPT/Codex** para revisar el repositorio.

La IA no decidió el alcance: las funciones salen de la Fase 1 y de lo que fuimos pidiendo. Antes
de la defensa cada integrante debe revisar y poder explicar el código de su parte; esa revisión
todavía no está completa y se anota abajo a medida que se hace.

## Quién decidió qué

**Decisiones del equipo** (pedidas por nosotros y aceptadas después de verlas funcionando):
- Panel distinto para administrador y encargado.
- Ventas en la gasolinera y pedidos del encargado al administrador; el encargado no corrige el
  stock a mano ni cambia un pedido ya enviado.
- Alertas grandes ("¡Tu pedido se realizó!", "Stock insuficiente", cerrar sesión).
- Contador − / + en las cantidades y "quedan" en tiempo real al vender.
- Filtros simples en lugar del editor de condiciones de Odoo.
- Pantalla "Preparar entrega" con hoja en PDF o Excel; los pedidos de los encargados se atienden
  como antes y los envíos propios del administrador quedan en Pedidos.
- Bodega central visible para todos y editable solo por el administrador, con su panel.
- Publicarlo en Google Cloud.

**Decisiones técnicas que propuso Claude** (revisables): estructura del módulo y modelos,
reglas de acceso por gasolinera, uso del inventario nativo de Odoo, cálculo de cantidades
sugeridas, alerta hecha con OWL en lugar de la librería SweetAlert, dirección gratuita sslip.io
y la configuración del servidor.

## Correcciones que hicimos al revisar

Al usar el sistema encontramos problemas y pedimos cambios. Los principales:

| Lo que encontramos | Qué se cambió |
|---|---|
| En el celular y en pantallas angostas el botón **+** quedaba escondido | Contador del mismo tamaño en todas las pantallas y columnas de ancho fijo |
| "Completar con lo sugerido" no llenaba las cantidades | Se corrigió (el interruptor guardaba sin recalcular) |
| El filtro "Modificar condición" de Odoo confundiría al cliente | Se quitó y se pusieron opciones simples a la izquierda en todas las listas |
| Los pedidos de los encargados no debían cambiar de flujo | Volvió el botón "Aprobar y preparar entrega"; "Preparar entrega" quedó para envíos propios |
| El nuevo administrador del servidor veía "Error de acceso" al imprimir | El diseño de los PDF queda configurado automáticamente |
| Aparecían "Errores en el correo" en el servidor | Los avisos salen desde la dirección del sistema; se reintentaron los correos pendientes |
| Faltaba marcar a mano una entrega como recibida | Botón "Entregado ✓" para administrador y encargado |
| Probando pedidos en Centro quedaron borradores vacíos | Mensaje más claro cuando no hay productos por acabarse |
| Al probar con datos reales, "En bodega" mostraba de más | Ahora muestra lo disponible (sin lo reservado para otras entregas) |

## Pruebas: qué reportó la IA y qué confirmamos nosotros

| Evidencia | Estado |
|---|---|
| **Reportado por Claude**: 89 pruebas automáticas correctas (`./scripts/pruebas.sh`) y capturas de pantalla automáticas sin errores | Lo informó la IA |
| **Probado por Alan en el navegador** (local y en el servidor): usuarios y cambio de contraseña, pedidos, ventas, filtros, contador, impresión de PDF, entregas | Hecho; de ahí salieron las correcciones de arriba |
| **Ejecutar nosotros las pruebas automáticas** y anotar el resultado | Pendiente |
| Sistema publicado en <https://laroca.34-121-143-44.sslip.io> | Abierto y usado por Alan |

## Revisión por etapa

Cada integrante quedó a cargo de revisar una parte y poder explicarla en la defensa. Lo que dice
*pendiente* se completa cuando esa persona termine su revisión.

| Parte | Responsable | Qué probó | Resultado | Cambios pedidos |
|---|---|---|---|---|
| 1. Base: usuarios, gasolineras, catálogo, inventario por sucursal | Kelly Abigail Vásquez Rodríguez | _pendiente_ | _pendiente_ | _pendiente_ |
| 2. Stock mínimo, estados, alertas y sugerencias | Kennard David Pineda Aguilar | _pendiente_ | _pendiente_ | _pendiente_ |
| 3. Entregas, recepción, historial y hoja PDF/Excel | Luis Eduardo Cañas Santos | _pendiente_ | _pendiente_ | _pendiente_ |
| 4. Paneles por rol y reportes | Alan Anderson Vásquez Leiva | Paneles de administrador y encargado, impresión de PDF | Funciona | Panel distinto por rol; error de acceso al imprimir |
| Mejoras: ventas, pedidos, bodega, contador, alertas, filtros | Alan Anderson Vásquez Leiva | Uso en navegador y celular | Funciona | Ver "Correcciones que hicimos al revisar" |
| Publicación en Google Cloud | Alan Anderson Vásquez Leiva | Acceso al enlace, inicio de sesión, impresión | Funciona | Errores de correo y de impresión (corregidos) |
| Documentación (README, manual, esta declaración) | Kelly Abigail Vásquez Rodríguez | _pendiente_ | _pendiente_ | _pendiente_ |
| Pruebas automáticas (`./scripts/pruebas.sh`) | Kennard David Pineda Aguilar | _pendiente_ | _pendiente_ | _pendiente_ |
| Video demo | Luis Eduardo Cañas Santos | _pendiente_ | _pendiente_ | _pendiente_ |

## Revisión con ChatGPT/Codex

Usamos ChatGPT/Codex para revisar el repositorio. Nos sugirió completar esta declaración
(revisión por etapa, separar lo que reportó la IA de lo que confirmamos y aclarar el modelo
usado) y preparó un parche con cambios. **Ese parche todavía no se aplicó.**

## Anexo: prompts utilizados (textuales)

**Prompt inicial (1 de octubre):**

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

| Fecha | Tema | Prompt |
|---|---|---|
| 1 oct | Etapas 2, 3 y 4 (continuar) | sigue trabajando · dale · y ahora |
| 1 oct | Mejoras (eligió las 8 propuestas) | okaay eso lo dejmos para el final ahora vamos hacer mejoras |
| 1 oct | Diseño, fotos reales y documentación sencilla | vaya me gusta ahora quiero que hagas la app mas amigable y bonita para el usuario y uses en el caso del catalgo imagenes reales de internete y les pongas descricioones y en reame lo hagas para que cualquier persona lo entienda aun si no sabe programar y igual en las fases que hyicimos |
| 2 oct | Gestión de usuarios | vaya quiero que hagas lo siguiente quiero que el admi agrege y modifique a los usuarios tanto las contrasenas como otras cosas podrias??? |
| 2 oct | Panel distinto por rol | quiero que el admistrador tengo un panel distinto al de encargado  se podria eso |
| 2 oct | Ventas y pedidos | vaya quiero algo hoy que vos podes pedir producto al admistrador tipo nesecito 50 llaveros y el te los mande y que el encargado pueda pedir mas no modificar y tambien vender esos protuctos que tenga el sistema de venta en un panel tipo vende 5 llevaros y se vaya restando y que pueda pedir eso al admistrador |
| 2 oct | Alertas y pedido rápido | vaya cuando pida quiero quedia su pedio se arrealizado y que cuando venda y el sock es infiente tire una swith alert y igual cuando se realiza el pedido que sea rapido y sencillo esa parte |
| 2 oct | Contador − / + y "quedan" | vaya en el caso de lo sugerido quiero que al precionarlo se ponga la cantia en automaitoco en el otro lado y el boton de los numero tengo como un contador de mas y menos para agregar o quitar eso de los numero lo quiero en todos lo que tenga numero para poder quitar o poner y que cuando pongas algo en el canso de ventas se vaya como quitan por ejemplo ay 20 de un prodcuto y pongo 5  quiero que esos 5 se reste del total tipo ay 20 llevo 5 y quedan 15 pero eso en tiempo real y cuando el producto llegue a 0 diga ya no hay mas un mensaje asi |
| 2 oct | Contador uniforme | me gusta pe el boton queda de mas queda escodido que quede uniforme todo y que al poner numero te tire un alterta que no hay ma stock |
| 2 oct | Filtros simples | no me gusta ese filtro quitalo y solo pon opciones mas simples y no asi siento que el cliente se confundira · en todos los que salga con ese filtro modificalo |
| 2 oct | Preparar entrega (PDF/Excel) | en el admistrador quiero que hagas una panel que sea para agregar productos que el entregara y que se genere un pdf o excel que diga que productos llevara el tipo agrega tanto llaveros, tantas gorras y asi pero que se interetivo genere el pdf y que en ese pdf diga para que gasolinera, luegar y pedido |
| 3 oct | Bodega central | agrega lo que te dije y quiero tambien que a los demas de las gasolinara le salga el sock de bogena y que yo pueda modificar eso como admistrador cuando yo resiva mis proyectos |
| 3 oct | Pedidos como antes / envíos propios | vaya cuando sean pedidos solicitados eso si dejalos como antes que yo los envios y cuando sean que enviare tipo hoy voy a llevarles llaveros extras |
| 3 oct | Panel de bodega | y como agrego yo los productos ala boga central · haz un panel para el |
| 3–4 oct | Publicación en internet | vaya ahora lo vamos a publicar en internet · lo voy hacer con google · toma el control de mi pc para ayudarme |
| 5 oct | Error de acceso al imprimir | por que le sale esto al nuevo admistrador |
| 5 oct | Envíos del administrador en Pedidos | quiero que los pedidos realizados por mi que yo entregare con una lista aprescan tipo asi pedios entregador por el admistrador y con lista algo asi para le entrega |
| 5 oct | Entregado manual y cierre de sesión | estos de aqui te digo quiero que aprescan como entregados pero son lo que seasen con un pdf y se manda ala gasolinera por ejemplo cuando ya lo resive el admistrador o el de la gasolinera puede decir entregado pero este es el que sea hade manual y tambien agrega un alert de cerra sesion |
| 5 oct | Esta declaración | con respecto ala declaracion de la ia nesecito que modifique esto y lo dejes simple sin tanta declaracion y tambien has que se ve natural y tambien mencionales las correciones que hice |

El detalle técnico de lo que se generó en cada paso está en [MEJORAS.md](MEJORAS.md) y en los
documentos de cada etapa.
