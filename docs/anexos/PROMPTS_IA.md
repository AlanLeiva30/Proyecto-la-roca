# Anexo: prompts utilizados (textuales)

Prompts tal como se escribieron a Claude Code durante el proyecto (los lineamientos piden anexarlos).

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

El detalle técnico de lo que se generó en cada paso está en [MEJORAS.md](../MEJORAS.md) y en los
documentos de cada etapa.
