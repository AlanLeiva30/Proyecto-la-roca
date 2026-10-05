#!/usr/bin/env bash
# Publica (o actualiza) el sistema en el servidor de la nube. Se ejecuta en TU computadora.
#   Uso: ./scripts/desplegar.sh <IP> [usuario]
#        ./scripts/desplegar.sh 34.121.143.44 laroca   (Google Cloud: usuario "laroca")
# La primera vez: prepara el servidor, genera claves nuevas, instala con datos de ejemplo y
# activa HTTPS. Las siguientes veces: sube el código nuevo y actualiza sin perder datos.
# Las claves quedan en produccion/credenciales.txt (en tu computadora, NO se sube a GitHub).
set -euo pipefail
cd "$(dirname "$0")/.."

IP="${1:-}"
USUARIO="${2:-root}"
[ -n "$IP" ] || { echo "Uso: ./scripts/desplegar.sh <IP del servidor> [usuario]"; exit 1; }
LLAVE="${LAROCA_LLAVE:-$HOME/.ssh/laroca_servidor}"
SSH=(ssh -i "$LLAVE" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "$USUARIO@$IP")
# Con un usuario que no es root (Google Cloud) todo se ejecuta con sudo
SUDO=""
[ "$USUARIO" = root ] || SUDO="sudo"
DESTINO=/opt/laroca

echo ">> 1/5 Preparando el servidor $IP"
"${SSH[@]}" "$SUDO bash -s" < deploy/preparar_servidor.sh

echo ">> 2/5 Subiendo el código"
rsync -az --delete -e "ssh -i $LLAVE" --rsync-path="$SUDO rsync" \
    --exclude '.env' --exclude 'backups/' --exclude 'produccion/' --exclude '.odoo_fuente/' \
    --exclude 'docs/' --exclude '.vscode/' --exclude '__pycache__/' --exclude '.DS_Store' \
    ./ "$USUARIO@$IP:$DESTINO/"

echo ">> 3/5 Configuración del servidor (.env con claves nuevas, solo la primera vez)"
"${SSH[@]}" "$SUDO env IP=$IP bash -s" <<'REMOTO'
set -euo pipefail
cd /opt/laroca
if [ ! -f .env ]; then
    clave() { openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 20; }
    DOMINIO="laroca.$(echo "$IP" | tr '.' '-').sslip.io"
    CORREO_CLAVE=$(clave)
    HASH=$(docker run --rm caddy:2 caddy hash-password --plaintext "$CORREO_CLAVE")
    cat > .env <<ENV
COMPOSE_FILE=docker-compose.prod.yml
DOMINIO=$DOMINIO
POSTGRES_PASSWORD=$(clave)
ODOO_ADMIN_PASSWORD=$(clave)
ODOO_DB=laroca
DEMO_CLAVE=$(clave | head -c 12)
CORREO_USUARIO=laroca
CORREO_CLAVE=$CORREO_CLAVE
CORREO_CLAVE_HASH='$HASH'
ENV
    chmod 600 .env
    echo "   .env creado para https://$DOMINIO"
fi
REMOTO

echo ">> 4/5 Instalando o actualizando Odoo"
"${SSH[@]}" "$SUDO bash -s" <<'REMOTO'
set -euo pipefail
cd /opt/laroca
set -a; source .env; set +a
docker compose up -d --wait db
if docker compose exec -T db psql -U odoo -lqt | cut -d'|' -f1 | grep -qw laroca; then
    ./scripts/actualizar.sh laroca_inventario,laroca_datos_prueba
else
    ./scripts/inicializar.sh
    docker compose run --rm -T -e DOMINIO -e DEMO_CLAVE odoo sh -c \
        'odoo shell -d "$ODOO_DB" --no-http --db_host="$HOST" --db_user="$USER" --db_password="$PASSWORD"' \
        < deploy/configurar_produccion.py
fi
# Levanta todo (Caddy y el buzón incluidos); se reintenta por si la primera descarga de imágenes falla
docker compose up -d || { sleep 10; docker compose up -d; }
# Respaldo diario a las 3:00
( crontab -l 2>/dev/null | grep -v laroca/deploy/respaldo.sh; echo "0 3 * * * /opt/laroca/deploy/respaldo.sh >> /opt/laroca/backups/respaldo.log 2>&1" ) | crontab -
REMOTO

echo ">> 5/5 Guardando las credenciales en produccion/credenciales.txt (solo en tu computadora)"
mkdir -p produccion
"${SSH[@]}" "$SUDO env IP=$IP USUARIO=$USUARIO bash -s" > produccion/credenciales.txt <<'REMOTO'
cd /opt/laroca && . ./.env
cat <<TXT
Grupo La Roca - credenciales de PRODUCCIÓN (no compartir, no subir a GitHub)
Sistema:            https://$DOMINIO
Usuarios de prueba: administrador, encargado.centro, encargado.norte, encargado.sur
Contraseña de esos usuarios: $DEMO_CLAVE
Buzón de correos:   https://correo.$DOMINIO  (usuario: $CORREO_USUARIO, clave: $CORREO_CLAVE)
Usuario técnico de Odoo: admin / $ODOO_ADMIN_PASSWORD
Servidor:           ssh -i ~/.ssh/laroca_servidor $USUARIO@$IP
TXT
REMOTO
chmod 600 produccion/credenciales.txt
DOMINIO=$(grep '^Sistema:' produccion/credenciales.txt | awk '{print $2}')
echo ">> Listo: $DOMINIO  (claves en produccion/credenciales.txt)"
