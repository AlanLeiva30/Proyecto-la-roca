# Guía técnica (para el equipo de desarrollo)

> Para el uso del sistema, ver el [README](../README.md) y el [manual de usuario](MANUAL_USUARIO.md).
> Este documento es para quien va a **modificar o explicar el código**.

## Tecnología

| Pieza | Versión | Para qué |
|---|---|---|
| Odoo Community | 18.0 (imagen oficial `odoo:18.0`, arm64/amd64) | ERP base: usuarios, inventario, vistas, reportes |
| Python | 3.12 (dentro de la imagen) | Lógica del módulo propio |
| PostgreSQL | 16 | Base de datos |
| Docker Compose | v2+ | Levanta Odoo, PostgreSQL y Mailpit |
| Mailpit | latest | Buzón de correo **de prueba** (no envía a internet) |
| OWL + Chart.js | incluidos en Odoo | Gráficos del panel, alerta estilo SweetAlert, contador − / + y buscador simple (único JavaScript propio) |

## Módulos propios (`src/addons/`)

| Módulo | Contenido |
|---|---|
| `laroca_inventario` | Todo el sistema: gasolineras, inventario por sucursal, estados, alertas, entregas, panel, reportes, conteo rápido, importación desde Excel, roles y reglas de acceso |
| `laroca_datos_prueba` | Datos **ficticios**: empresa, 5 gasolineras, bodega central, 13 productos con fotos y descripciones, usuarios, existencias, mínimos, entregas de ejemplo, servidor de correo de prueba. **No instalar en producción.** |

### Modelos principales (`laroca_inventario/models/`)

| Modelo | Archivo | Qué representa |
|---|---|---|
| `stock.warehouse` (heredado) | `stock_warehouse.py` | Gasolinera (campos `laroca_*`) o Bodega Central |
| `laroca.inventario` | `laroca_inventario.py` | Una línea por gasolinera × producto: stock, mínimo, objetivo, estado, sugerencia, valor |
| `laroca.alerta` | `laroca_alerta.py` | Alerta de abastecimiento (abierta → en proceso → resuelta), notificaciones y tareas programadas |
| `laroca.entrega` / `laroca.entrega.linea` | `laroca_entrega.py` | Entrega desde la bodega central (usa transferencias internas nativas `stock.picking`) |
| `laroca.pedido` / `laroca.pedido.linea` | `laroca_pedido.py` | Pedido del encargado (borrador → enviado → en preparación → en camino → entregado / rechazado). Enviado, no se modifica. Al aprobar crea una `laroca.entrega` (campo `pedido_id`) |
| `laroca.venta` / `laroca.venta.linea` | `laroca_venta.py` | Venta en una gasolinera: salida nativa `stock.picking` (gasolinera → clientes) validada al instante; el administrador la anula con una devolución |
| `laroca.panel` | `laroca_panel.py` | Panel (modelo transitorio, indicadores calculados con los permisos del usuario). Dos vistas: administrador y encargado ("Mi gasolinera"); `action_abrir_panel` elige según el grupo |
| `res.company` / `res.users` / `product.template` / `stock.quant` (heredados) | varios | Parámetros, gasolineras del usuario, niveles por defecto, actualización automática del stock |

Asistentes (`wizard/`): vender, pedir productos (pedido rápido), rechazar pedido / anular venta, actualizar stock y conteo rápido (solo administrador),
recepción de entrega, reportes PDF, importación desde Excel, cambiar contraseña.

### Seguridad
- Grupos: `group_laroca_encargado` y `group_laroca_admin` (`security/laroca_security.xml`).
- Reglas de registro (`ir.rule`): el encargado solo ve registros de `user.laroca_gasolinera_ids`;
  el administrador tiene reglas "ver todo". Cubren inventario, alertas, entregas, almacenes,
  ubicaciones, existencias, movimientos y transferencias.
- Permisos por modelo: `security/ir.model.access.csv`.
- El encargado **no corrige existencias**: `_ajustar_existencias` exige el grupo administrador
  (salvo `sudo`); el stock del encargado cambia solo con ventas (`laroca.venta._registrar`) y entregas.

## Comandos

| Acción | Comando |
|---|---|
| Primera instalación (con datos de prueba) | `./scripts/inicializar.sh` |
| Instalación sin datos de prueba | `./scripts/inicializar.sh --sin-datos` |
| Iniciar / detener | `docker compose up -d` / `docker compose stop` |
| Ver registros | `docker compose logs -f odoo` |
| Aplicar cambios del código | `./scripts/actualizar.sh laroca_inventario,laroca_datos_prueba` |
| Pruebas automáticas (base temporal) | `./scripts/pruebas.sh` — **88 pruebas** |
| Respaldo de la base | `docker compose exec -T db pg_dump -U odoo laroca > respaldo.sql` |
| Borrar todo y empezar de cero | `docker compose down -v && ./scripts/inicializar.sh` |
| Regenerar ilustraciones de productos | ver encabezado de `scripts/generar_imagenes_productos.py` |

Datos persistentes en los volúmenes `laroca_laroca-db-data` (PostgreSQL) y
`laroca_laroca-odoo-data` (adjuntos y sesiones). Solo `docker compose down -v` los borra.

## Visual Studio Code
- Tareas (`Cmd+Shift+P → Tasks: Run Task`): iniciar (también `Cmd+Shift+B`), detener, logs,
  aplicar cambios, pruebas, instalar desde cero, abrir el buzón de prueba.
- Extensiones recomendadas: Python, XML, Container Tools, DotENV (`.vscode/extensions.json`).
- Autocompletado de Odoo: `./scripts/fuente_odoo.sh` copia los `.py` de Odoo a `.odoo_fuente/`.

## Migraciones (actualizar sin perder datos)
Al subir la versión del módulo (`__manifest__.py`), Odoo ejecuta los scripts de `migrations/<versión>/`:
- `18.0.5.0.0`: completa el costo de entregas creadas antes de existir el campo.
- `18.0.6.0.0`: cantidades sin decimales.

## Estructura del repositorio

```
├── docker-compose.yml          Odoo 18 + PostgreSQL 16 + Mailpit
├── config/odoo.conf            Configuración de Odoo (sin contraseñas)
├── .env.example                Claves (copiar a .env; .env no se sube a GitHub)
├── scripts/                    inicializar, actualizar, pruebas, fuente_odoo, imágenes
├── src/addons/
│   ├── laroca_inventario/      models/ wizard/ views/ report/ security/ data/ static/ tests/ migrations/
│   └── laroca_datos_prueba/    data/ models/ static/img/
├── docs/                       Etapas, manual, guion, capturas, ejemplos de reportes, uso de IA
├── DEPLOY.md                   Instalación local y plan para la nube
└── README.md                   Explicación general (para cualquier persona)
```

## Documentación por etapa
Cada documento de etapa tiene una parte en lenguaje sencillo y, al final, un **anexo técnico**
con los archivos y las pruebas: [Etapa 1](ETAPA_1.md) · [Etapa 2](ETAPA_2.md) ·
[Etapa 3](ETAPA_3.md) · [Etapa 4](ETAPA_4.md) · [Mejoras](MEJORAS.md).
