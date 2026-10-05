# Despliegue (publicar el sistema en internet)

> **En línea:** <https://laroca.34-121-143-44.sslip.io> — Google Cloud, Compute Engine `e2-small`
> (us-central1-a), Ubuntu 24.04, IP fija `34.121.143.44`. Actualizar: `./scripts/desplegar.sh 34.121.143.44 laroca`

El sistema se publica en un **servidor virtual con Ubuntu** en la nube (**Azure for Students**;
también funciona igual en DigitalOcean u otro proveedor) con **Docker**, tal como se planificó en la
Fase 1 (servidor self-hosted + certificado HTTPS gratuito de Let's Encrypt).

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

## Paso a paso con Azure for Students (la primera vez)

### 1. Activar Azure for Students
Entrar a <https://azure.microsoft.com/free/students> con el correo de la UDB. Da **$100 de crédito
sin tarjeta**; cuando se acaba, la máquina se apaga y **no cobra nada**.

### 2. Crear la máquina virtual
En el portal (<https://portal.azure.com>): **Máquinas virtuales → Crear → Máquina virtual de Azure**:
- **Grupo de recursos**: nuevo, `laroca`.
- **Nombre**: `laroca-servidor`. **Región**: la que el portal permita (por ejemplo *East US 2*;
  las cuentas de estudiante solo admiten algunas regiones).
- **Imagen**: **Ubuntu Server 24.04 LTS – x64 Gen2**.
- **Tamaño**: **B1ms** (1 vCPU, 2 GB RAM, ≈ $15/mes) o **B2s** (2 vCPU, 4 GB) si sobra crédito.
- **Autenticación**: **Clave pública SSH**. Usuario: `laroca`. Origen: *Usar clave pública existente*
  → pegar `cat ~/.ssh/laroca_digitalocean.pub`.
- **Puertos de entrada públicos**: permitir **SSH (22), HTTP (80) y HTTPS (443)**.
- **Discos**: SSD estándar, 30 GB está bien. → **Revisar y crear → Crear**.
- Copiar la **dirección IP pública** de la máquina.

### 3. Publicar
```bash
./scripts/desplegar.sh 20.115.4.10 laroca      # IP de la máquina y usuario "laroca"
```

## Paso a paso con Google Cloud

1. Crear la cuenta en <https://cloud.google.com/free> (prueba gratis de **$300 por 90 días**; pide
   tarjeta para verificar, pero no cobra si no se activa la cuenta de pago).
2. **Compute Engine → Instancias de VM → Crear instancia**:
   - **Nombre**: `laroca-servidor`. **Región**: `us-central1` o `us-east1`.
   - **Tipo de máquina**: **e2-small** (2 vCPU compartidas, 2 GB, ≈ $13/mes) o e2-medium (4 GB).
   - **Disco de arranque**: **Ubuntu 24.04 LTS (x86/64)**, 30 GB, disco persistente balanceado.
   - **Firewall**: marcar **Permitir tráfico HTTP** y **Permitir tráfico HTTPS**.
   - **Redes → Interfaz de red → Dirección IPv4 externa**: **Reservar dirección IP estática**
     (si no, la IP cambia al reiniciar y cambiaría la dirección web).
   - **Seguridad → Administrar acceso → Agregar elemento (Claves SSH)**: pegar la llave pública
     terminada en ` laroca` (Google usa esa última palabra como nombre de usuario).
   - **Crear** y copiar la **IP externa**.
3. Publicar:
```bash
./scripts/desplegar.sh 34.123.45.67 laroca
```

## Paso a paso con DigitalOcean (alternativa)

### 1. Crear la cuenta (lo hace una persona del equipo)
1. *(Opcional, recomendado)* Pedir el **GitHub Student Developer Pack** (<https://education.github.com/pack>)
   con el correo de la UDB: incluye **$200 de crédito en DigitalOcean**, así el servidor no cuesta nada.
2. Crear la cuenta en <https://www.digitalocean.com> (pide tarjeta o PayPal para verificar).

### 2. Crear el servidor ("Droplet")
En DigitalOcean: **Create → Droplets**:
- **Región**: New York o San Francisco (las más cercanas a El Salvador).
- **Imagen**: **Ubuntu 24.04 (LTS) x64**.
- **Tamaño**: Basic → Regular → **2 GB RAM / 1 CPU** (≈ $12/mes).
- **Autenticación**: **SSH Key** → *New SSH Key* → pegar la llave pública de la computadora que
  publica (`cat ~/.ssh/laroca_digitalocean.pub`).
- **Nombre**: `laroca-servidor` → **Create Droplet**. Copiar la **IP** que aparece.

### 3. Publicar
En la carpeta del proyecto:
```bash
./scripts/desplegar.sh 157.230.1.2      # usar la IP del Droplet
```
Tarda unos 5–10 minutos la primera vez. Al final muestra la dirección, por ejemplo
`https://laroca.157-230-1-2.sslip.io`, y guarda las claves en **`produccion/credenciales.txt`**
(solo en tu computadora; esa carpeta no se sube a GitHub).

La dirección usa **sslip.io**: un servicio gratuito que convierte la IP en un nombre, para que
Let's Encrypt pueda dar el certificado HTTPS sin comprar un dominio.

## Actualizar después de cambiar el código
```bash
./scripts/desplegar.sh 20.115.4.10 laroca      # Azure (en DigitalOcean: solo la IP)
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
ssh -i ~/.ssh/laroca_digitalocean laroca@20.115.4.10 "sudo cat /opt/laroca/backups/\$(sudo ls -t /opt/laroca/backups | grep sql | head -1)" > respaldo.sql.gz
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
