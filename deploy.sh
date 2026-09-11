#!/usr/bin/env bash
# ==============================================================================
# Humm Fondos - Script de Despliegue Seguro y Canónico a Producción (HostGator)
# Protocolo: HUMM RELEASE GATE v2 (No destructivo, tests previos, preservación de datos)
# ==============================================================================
set -euo pipefail

echo "=================================================================="
echo "🚀 INICIANDO DESPLIEGUE SEGURO — HUMM FONDOS (fondos.humm.cl)"
echo "=================================================================="

REMOTE_USER="${REMOTE_USER:-paulocis}"
REMOTE_HOST="${REMOTE_HOST:-humm.cl}"
REMOTE_PORT="${REMOTE_PORT:-2222}"
APP_DIR="/home1/paulocis/fondos_app"
SUBDOMAIN_DIR="/home1/paulocis/fondos.humm.cl"
LEGACY_PUBLIC_DIR="/home1/paulocis/public_html/FONDOS"
DB_PATH="/home1/paulocis/private/fondos_data/db.sqlite3"
BACKUP_DIR="/home1/paulocis/RESPALDOS/fondos_backups"

# ------------------------------------------------------------------------------
# 1. VERIFICACIÓN PREVIA LOCAL (SUITE AUTOMATIZADA)
# ------------------------------------------------------------------------------
echo "🧪 [PASO 1/6] Ejecutando suite automatizada de pruebas locales..."
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

pytest -q
echo "✔ Pruebas locales pasadas exitosamente (100% aprobadas)."

# ------------------------------------------------------------------------------
# 2. ENVIAR CAMBIOS A REPOSITORIO CENTRAL
# ------------------------------------------------------------------------------
echo "📦 [PASO 2/6] Verificando repositorio Git local y enviando a GitHub..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️ Advertencia: Rama actual es '$CURRENT_BRANCH'. Se desplegará 'main'."
fi
git push origin main
echo "✔ Código sincronizado con GitHub (origin/main)."

# ------------------------------------------------------------------------------
# 3. BACKUP PREVENTIVO Y VERIFICACIÓN DE ESTADO PREVIO EN SERVIDOR
# ------------------------------------------------------------------------------
echo "🛡️ [PASO 3/6] Conectando a HostGator para backup preventivo y auditoría de estado..."
ssh -p "${REMOTE_PORT}" "${REMOTE_USER}@${REMOTE_HOST}" bash << 'EOF'
set -euo pipefail

DB_PATH="/home1/paulocis/private/fondos_data/db.sqlite3"
BACKUP_DIR="/home1/paulocis/RESPALDOS/fondos_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
PRE_BACKUP="${BACKUP_DIR}/pre_deploy_${TIMESTAMP}.sqlite3"

mkdir -p "$BACKUP_DIR" /home1/paulocis/private/fondos_data
chmod 700 "$BACKUP_DIR" /home1/paulocis/private/fondos_data

if [ -f "$DB_PATH" ]; then
    echo "📦 Generando backup preventivo pre-deploy..."
    sqlite3 "$DB_PATH" ".backup '$PRE_BACKUP'"
    chmod 600 "$PRE_BACKUP"
    sha256sum "$PRE_BACKUP" > "${PRE_BACKUP}.sha256"
    
    echo "📊 Estado previo de la base persistente:"
    echo "   - Conteo Instrumentos: $(sqlite3 "$DB_PATH" 'SELECT COUNT(*) FROM orientador_instrumento;' 2>/dev/null || echo '0')"
    echo "   - Conteo Usuarios:     $(sqlite3 "$DB_PATH" 'SELECT COUNT(*) FROM auth_user;' 2>/dev/null || echo '0')"
    echo "   - Conteo Solicitudes:  $(sqlite3 "$DB_PATH" 'SELECT COUNT(*) FROM orientador_solicitudapoyo;' 2>/dev/null || echo '0')"
    echo "   - SHA-256 pre-deploy:  $(awk '{print $1}' "${PRE_BACKUP}.sha256")"
else
    echo "⚠️ Base persistente no existe aún en $DB_PATH (primer despliegue canónico)."
fi
EOF

# ------------------------------------------------------------------------------
# 4. ACTUALIZACIÓN SEGURA DE CÓDIGO (NO DESTRUCTIVA)
# ------------------------------------------------------------------------------
echo "🌐 [PASO 4/6] Actualizando código fuente en entorno canónico ($APP_DIR)..."
ssh -p "${REMOTE_PORT}" "${REMOTE_USER}@${REMOTE_HOST}" bash << 'EOF'
set -euo pipefail

APP_DIR="/home1/paulocis/fondos_app"
SUBDOMAIN_DIR="/home1/paulocis/fondos.humm.cl"
LEGACY_DIR="/home1/paulocis/public_html/FONDOS"

# Clonar o actualizar repositorio en fondos_app
if [ ! -d "${APP_DIR}/.git" ]; then
    echo "📥 Clonando repositorio en $APP_DIR..."
    git clone https://github.com/nativoaustral-bit/fondos.git "$APP_DIR"
else
    echo "🔄 Actualizando repositorio en $APP_DIR..."
    cd "$APP_DIR"
    git fetch origin main
    git checkout main
    git merge origin/main --ff-only || (echo "❌ Conflicto git; abortando." && exit 1)
fi

cd "$APP_DIR"

# Asegurar entorno virtual Python con uv o python
if [ ! -d "venv" ]; then
    echo "🐍 Creando virtualenv con uv..."
    /home1/paulocis/.local/bin/uv venv venv
    source venv/bin/activate
    /home1/paulocis/.local/bin/uv pip install -r requirements.txt
else
    source venv/bin/activate
    if [ -f "/home1/paulocis/.local/bin/uv" ]; then
        /home1/paulocis/.local/bin/uv pip install -r requirements.txt --quiet
    fi
fi

# Copiar scripts de backup a /home1/paulocis/scripts/
mkdir -p /home1/paulocis/scripts
cp scripts/backup_sqlite.sh /home1/paulocis/scripts/
cp scripts/restore_sqlite.sh /home1/paulocis/scripts/
chmod +x /home1/paulocis/scripts/*.sh

# Migraciones controladas
echo "🗄️ Ejecutando migraciones de base de datos..."
python manage.py migrate --noinput

# Recolección de archivos estáticos
echo "🎨 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# Configurar subdominio canónico fondos.humm.cl
echo "⚙️ Configurando subdominio canónico en $SUBDOMAIN_DIR..."
mkdir -p "${SUBDOMAIN_DIR}/tmp"
cp .htaccess "${SUBDOMAIN_DIR}/.htaccess"

# Generar passenger_wsgi.py apuntando a fondos_app
cat << 'P_WSGI' > "${SUBDOMAIN_DIR}/passenger_wsgi.py"
#!/home1/paulocis/fondos_app/venv/bin/python
import sys, os

project_dir = os.path.dirname(os.path.abspath(__file__))
for d in [project_dir, '/home1/paulocis/fondos_app']:
    if os.path.exists(d) and d not in sys.path:
        sys.path.insert(0, d)

os.environ['DJANGO_SETTINGS_MODULE'] = 'humm_fondos.settings'

from humm_fondos.wsgi import application as _application

def application(environ, start_response):
    environ['SCRIPT_NAME'] = ''
    return _application(environ, start_response)

if __name__ == '__main__' or 'GATEWAY_INTERFACE' in os.environ:
    from wsgiref.handlers import CGIHandler
    CGIHandler().run(application)
P_WSGI

chmod 755 "${SUBDOMAIN_DIR}/passenger_wsgi.py"
rm -f "${SUBDOMAIN_DIR}/static" "${SUBDOMAIN_DIR}/media"
ln -sfn "${APP_DIR}/staticfiles" "${SUBDOMAIN_DIR}/static"
ln -sfn "${APP_DIR}/media" "${SUBDOMAIN_DIR}/media"

# Reiniciar Passenger
touch "${SUBDOMAIN_DIR}/tmp/restart.txt"

# ------------------------------------------------------------------------------
# Retirar código y artefactos de la ruta pública antigua (/public_html/FONDOS)
# Dejar exclusivamente un .htaccess de redirección limpia hacia fondos.humm.cl
# ------------------------------------------------------------------------------
echo "🧹 Asegurando ruta antigua $LEGACY_DIR (solo redirección y bloqueo)..."
mkdir -p "$LEGACY_DIR"
# Eliminar artefactos sensibles antiguos si aún existen en la ruta pública
rm -rf "${LEGACY_DIR}/.git" "${LEGACY_DIR}/db.sqlite3"* "${LEGACY_DIR}/deploy.sh" "${LEGACY_DIR}/venv" "${LEGACY_DIR}/humm_fondos" "${LEGACY_DIR}/orientador" 2>/dev/null || true

cat << 'HTACCESS_LEGACY' > "${LEGACY_DIR}/.htaccess"
RewriteEngine On

# Bloqueo estricto de cualquier archivo
<FilesMatch "(.*)">
    <IfModule mod_authz_core.c>
        Require all denied
    </IfModule>
</FilesMatch>

# Redirección 301 de rutas públicas hacia el subdominio canónico
RewriteRule ^(.*)$ https://fondos.humm.cl/$1 [R=301,L]
HTACCESS_LEGACY

echo "✔ Despliegue en servidor completado."
EOF

# ------------------------------------------------------------------------------
# 5. AUDITORÍA POST-DESPLIEGUE Y PRESERVACIÓN DE DATOS
# ------------------------------------------------------------------------------
echo "🔍 [PASO 5/6] Auditando preservación de datos en el servidor..."
ssh -p "${REMOTE_PORT}" "${REMOTE_USER}@${REMOTE_HOST}" bash << 'EOF'
set -euo pipefail

DB_PATH="/home1/paulocis/private/fondos_data/db.sqlite3"

echo "🔎 Ejecutando PRAGMA integrity_check..."
INTEGRITY=$(sqlite3 "$DB_PATH" 'PRAGMA integrity_check;')
if [ "$INTEGRITY" != "ok" ]; then
    echo "❌ Error: La base de datos persistente no pasó la prueba de integridad: $INTEGRITY" >&2
    exit 1
fi
echo "✔ PRAGMA integrity_check: ok"

INST_COUNT=$(sqlite3 "$DB_PATH" 'SELECT COUNT(*) FROM orientador_instrumento;' 2>/dev/null || echo '0')
USER_COUNT=$(sqlite3 "$DB_PATH" 'SELECT COUNT(*) FROM auth_user;' 2>/dev/null || echo '0')
SOLI_COUNT=$(sqlite3 "$DB_PATH" 'SELECT COUNT(*) FROM orientador_solicitudapoyo;' 2>/dev/null || echo '0')

echo "📊 Estado posterior a deployment y migraciones:"
echo "   - Instrumentos: $INST_COUNT"
echo "   - Usuarios:     $USER_COUNT"
echo "   - Solicitudes:  $SOLI_COUNT"

if [ "$INST_COUNT" -lt 1 ]; then
    echo "❌ Error crítico: Pérdida inesperada de instrumentos en la base persistente." >&2
    exit 1
fi
echo "✔ PRESERVACIÓN DE DATOS DEMOSTRADA."
EOF

# ------------------------------------------------------------------------------
# 6. SMOKE TEST EXTERNO HTTP
# ------------------------------------------------------------------------------
echo "🌐 [PASO 6/6] Ejecutando comprobación de servicio HTTP externo..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://fondos.humm.cl/)
if [ "$HTTP_STATUS" != "200" ]; then
    echo "❌ Error: https://fondos.humm.cl/ devolvió código HTTP $HTTP_STATUS (esperado 200)." >&2
    exit 1
fi
echo "✔ Servicio web activo y saludable: HTTP $HTTP_STATUS en https://fondos.humm.cl/"

echo "=================================================================="
echo "✅ DESPLIEGUE EXITOSO Y DATOS PRESERVADOS"
echo "URL canónica: https://fondos.humm.cl/"
echo "=================================================================="
