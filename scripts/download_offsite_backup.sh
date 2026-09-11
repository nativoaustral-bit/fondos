#!/usr/bin/env bash
# ==============================================================================
# Humm Fondos - Sincronización Automatizada de Respaldos Off-Site
# Ubicación de ejecución: Entorno local / Infraestructura externa controlada por Humm
# Objetivo: Descargar automáticamente respaldos diarios desde HostGator y verificar SHA-256
# ==============================================================================
set -euo pipefail

REMOTE_USER="${REMOTE_USER:-paulocis}"
REMOTE_HOST="${REMOTE_HOST:-humm.cl}"
REMOTE_PORT="${REMOTE_PORT:-2222}"
REMOTE_BACKUP_DIR="${REMOTE_BACKUP_DIR:-/home1/paulocis/RESPALDOS/fondos_backups}"

# Directorio local seguro fuera del control de versiones
LOCAL_BACKUP_DIR="${LOCAL_BACKUP_DIR:-${HOME}/.humm_backups/fondos}"
mkdir -p "$LOCAL_BACKUP_DIR"
chmod 700 "$LOCAL_BACKUP_DIR"

echo "📡 [$(date +'%Y-%m-%d %H:%M:%S')] Consultando respaldos en HostGator (${REMOTE_HOST})..."

# 1. Obtener el nombre del archivo de backup más reciente en el servidor
LATEST_BACKUP=$(ssh -o BatchMode=yes -p "$REMOTE_PORT" "${REMOTE_USER}@${REMOTE_HOST}" "ls -1t ${REMOTE_BACKUP_DIR}/fondos_backup_*.sqlite3.gz 2>/dev/null | head -n 1" || true)

if [ -z "$LATEST_BACKUP" ]; then
    echo "⚠️ No se encontraron archivos de respaldo en ${REMOTE_BACKUP_DIR}. Generando uno ahora de forma remota..."
    ssh -o BatchMode=yes -p "$REMOTE_PORT" "${REMOTE_USER}@${REMOTE_HOST}" "/home1/paulocis/scripts/backup_sqlite.sh"
    LATEST_BACKUP=$(ssh -o BatchMode=yes -p "$REMOTE_PORT" "${REMOTE_USER}@${REMOTE_HOST}" "ls -1t ${REMOTE_BACKUP_DIR}/fondos_backup_*.sqlite3.gz 2>/dev/null | head -n 1")
fi

BACKUP_FILENAME=$(basename "$LATEST_BACKUP")
SHA256_FILENAME="${BACKUP_FILENAME%.sqlite3.gz}.sha256"

LOCAL_BACKUP_FILE="${LOCAL_BACKUP_DIR}/${BACKUP_FILENAME}"
LOCAL_SHA_FILE="${LOCAL_BACKUP_DIR}/${SHA256_FILENAME}"

echo "📥 Descargando respaldo más reciente: ${BACKUP_FILENAME}..."
scp -P "$REMOTE_PORT" "${REMOTE_USER}@${REMOTE_HOST}:${LATEST_BACKUP}" "$LOCAL_BACKUP_FILE"
scp -P "$REMOTE_PORT" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BACKUP_DIR}/${SHA256_FILENAME}" "$LOCAL_SHA_FILE" 2>/dev/null || true

chmod 600 "$LOCAL_BACKUP_FILE"

# 2. Verificación de integridad local
if [ -f "$LOCAL_SHA_FILE" ]; then
    chmod 600 "$LOCAL_SHA_FILE"
    EXPECTED_SHA=$(awk '{print $1}' "$LOCAL_SHA_FILE")
    ACTUAL_SHA=$(sha256sum "$LOCAL_BACKUP_FILE" | awk '{print $1}')
    if [ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]; then
        echo "❌ Error: La firma SHA-256 no coincide en la copia descargada." >&2
        rm -f "$LOCAL_BACKUP_FILE"
        exit 1
    fi
    echo "✔ Integridad SHA-256 verificada localmente: $ACTUAL_SHA"
else
    echo "ℹ️ Archivo .sha256 no disponible en remoto; verificando consistencia gzip..."
    gunzip -t "$LOCAL_BACKUP_FILE"
fi

# 3. Política de retención local (conservar últimos 30 días)
find "$LOCAL_BACKUP_DIR" -name "fondos_backup_*.sqlite3.gz" -mtime +30 -delete 2>/dev/null || true
find "$LOCAL_BACKUP_DIR" -name "fondos_backup_*.sha256" -mtime +30 -delete 2>/dev/null || true

echo "🎉 [$(date +'%Y-%m-%d %H:%M:%S')] Respaldo off-site sincronizado exitosamente en: ${LOCAL_BACKUP_DIR}"
