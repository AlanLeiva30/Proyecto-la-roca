# Uso de inteligencia artificial

## Declaración

Usamos **Claude Code** (asistente de programación de Anthropic; en esta sesión, el modelo
Claude Opus 5.5) para generar buena parte del código base del módulo de Odoo, los datos de
prueba, las pruebas automáticas y el borrador de la documentación. Nosotros definimos qué hacer
en cada paso, probamos el sistema en el navegador y pedimos correcciones cuando algo no
funcionaba o no nos gustaba.

La IA no decidió el alcance: las funciones salen de la Fase 1 y de lo que fuimos pidiendo. Antes
de la defensa cada integrante revisa y debe poder explicar el código de su parte.

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

## Participación del equipo

Las ideas y mejoras se decidieron en equipo; Alan las fue planteando a la IA y probando el
resultado.

| Integrante | Aporte |
|---|---|
| Alan Anderson Vásquez Leiva | Planteó los pedidos a la IA, probó cada cambio en el navegador y el celular, pidió las correcciones y publicó el sistema en Google Cloud |
| Kelly Abigail Vásquez Rodríguez | Aportó ideas y mejoras para el sistema (paneles, pedidos, ventas y diseño) |
| Kennard David Pineda Aguilar | Aportó ideas y mejoras para el sistema (inventario, alertas y bodega) |
| Luis Eduardo Cañas Santos | Aportó ideas y mejoras para el sistema (entregas, reportes y filtros) |

Los prompts utilizados están en el anexo [PROMPTS_IA.md](anexos/PROMPTS_IA.md).
