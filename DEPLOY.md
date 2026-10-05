# Despliegue (publicar el sistema en internet)

> **En línea:** <https://laroca.34-121-143-44.sslip.io> — Google Cloud, Compute Engine `e2-small`
> (us-central1-a), Ubuntu 24.04, IP fija `34.121.143.44`. Actualizar: `./scripts/desplegar.sh 34.121.143.44 laroca`

El sistema está publicado en un **servidor virtual de Google Cloud** (Compute Engine) con **Docker**,
tal como se planificó en la Fase 1 (servidor self-hosted + certificado HTTPS gratuito de Let's Encrypt).

```
Internet ──HTTPS──▶ Caddy (certificado automático) ──▶ Odoo 18 (2 workers) ──▶ PostgreSQL 16
                        └── correo.<dominio> (con clave) ──▶ Mailpit (buzón de prueba)
```

| Pieza | Para qué |
|---|---|
| `docker-compose.prod.yml` | Los servicios de producción: PostgreSQL, Odoo, Caddy y Mailpit |
| `deploy/Caddyfile` | HTTPS automático y entrada al sistema y al buzón de prueba |
| `config/odoo.prod.conf` | Odoo para producción: detrás de proxy, 2 workers, límites de memoria |
| `deploy/preparar_servidor.sh` | Prepara el servidor: Docker, firewall, swap y actualizaciones automáticas |
| `deploy/configurar_produccion.py` | Dirección pública y **contraseñas nuevas** para los usuarios de prueba |
| `deploy/respaldo.sh` | Respaldo diario (base de datos + fotos/archivos), guarda 7 días |
| `scripts/desplegar.sh` | Hace todo lo anterior desde tu computadora con **un solo comando** |

## Paso a paso con Google Cloud (proveedor usado)

### 1. Cuenta y facturación
- Crear la cuenta en <https://cloud.google.com> y activar la facturación. Google ofrece una prueba
  con crédito para cuentas nuevas, pero **pide tarjeta** y, según el país y la cuenta, **puede pedir
  un pago anticipado (prepago)** al activar la facturación. Antes de crear el servidor conviene
  revisar en **Facturación** qué modalidad quedó (crédito de prueba, prepago o pago posterior).
- El servidor **e2-small** cuesta aproximadamente **$13–15 al mes**; se descuenta del crédito o del
  saldo según esa modalidad. Para no gastar: detener o borrar la instancia cuando no se use.

### 2. Crear el servidor
Así se creó, desde **Cloud Shell** (la terminal de la consola de Google Cloud), en el proyecto con
Compute Engine habilitado:
```bash
gcloud compute addresses create laroca-ip --region=us-central1
gcloud compute firewall-rules create laroca-web --allow=tcp:80,tcp:443 --target-tags=laroca-web
gcloud compute instances create laroca-servidor --zone=us-central1-a --machine-type=e2-small \
  --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB --boot-disk-type=pd-balanced --address=laroca-ip --tags=laroca-web \
  --metadata=ssh-keys="laroca:$(awk '{print $1, $2}' ~/.ssh/laroca_servidor.pub) laroca"
```
- **IP fija** (`laroca-ip`): si no se reserva, la IP cambia al reiniciar y cambiaría la dirección web.
- **Firewall**: abre la web (80 y 443); SSH (22) ya viene abierto en la red por defecto.
- **Llave SSH**: la pública de la computadora que publica; `laroca` es el usuario del servidor.

También se puede hacer desde la consola: **Compute Engine → Instancias de VM → Crear instancia**
con los mismos datos (Ubuntu 24.04, e2-small, permitir HTTP/HTTPS, IP estática y la llave SSH).

### 3. Publicar
En la carpeta del proyecto:
```bash
./scripts/desplegar.sh 34.121.143.44 laroca
```
Tarda unos 5–10 minutos la primera vez. Al final muestra la dirección y guarda las claves en
**`produccion/credenciales.txt`** (solo en tu computadora; esa carpeta no se sube a GitHub).

La dirección usa **sslip.io**: un servicio gratuito que convierte la IP en un nombre
(`laroca.34-121-143-44.sslip.io`), para que Let's Encrypt pueda dar el certificado HTTPS sin
comprar un dominio.

## Actualizar después de cambiar el código
```bash
./scripts/desplegar.sh 34.121.143.44 laroca
```
El mismo comando: sube el código nuevo y actualiza los módulos **sin perder datos**.

## Datos, contraseñas y correo
- Se publica con los **datos ficticios** (para la demostración y el video). Las contraseñas de los
  usuarios de prueba **no** son `LaRoca2026`: se generan nuevas y están en `produccion/credenciales.txt`.
- Los correos que envía el sistema llegan al **buzón de prueba** en `https://correo.<dominio>`
  (pide usuario y clave). Para correo real: Ajustes → Técnico → Servidores de correo saliente.
- Para usarlo con datos reales: instalar en un servidor nuevo cambiando `./scripts/inicializar.sh`
  por `./scripts/inicializar.sh --sin-datos` en `scripts/desplegar.sh`.

## Respaldos
Todos los días a las 3:00 se guarda la base y los archivos en `/opt/laroca/backups` (últimos 7 días).
Copiar un respaldo a tu computadora:
```bash
ssh -i ~/.ssh/laroca_servidor laroca@34.121.143.44 "sudo cat /opt/laroca/backups/\$(sudo ls -t /opt/laroca/backups | grep sql | head -1)" > respaldo.sql.gz
```

## Seguridad aplicada
HTTPS obligatorio · firewall (solo 22, 80 y 443) · Odoo y PostgreSQL no expuestos a internet ·
gestor de bases de datos desactivado (`list_db = False`) · claves aleatorias · acceso al servidor solo
con llave SSH · actualizaciones de seguridad automáticas · respaldos diarios.

## Verificado
La configuración de producción se probó completa en una copia aislada (HTTPS, inicio de sesión con
la clave nueva, rechazo de la clave vieja, PDF con estilos, buzón protegido con clave).

## Local (desarrollo)
```bash
cp .env.example .env          # y cambiar las claves
./scripts/inicializar.sh      # primera vez: crea la base, instala módulos y datos ficticios
```
Sistema en <http://localhost:8069>; detalles en la [guía técnica](docs/GUIA_TECNICA.md).
