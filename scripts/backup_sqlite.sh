#!/usr/bin/env bash
# ==============================================================================
# Humm Fondos - Script de Respaldo Automatizado de Base de Datos SQLite
# Ubicación de ejecución: Servidor HostGator (cron o manual)
# Principio: SQLite Online .backup + compresión gzip + SHA-256 + retención 14 días
# ==============================================================================
set -euo pipefail

DB_PATH="${DB_PATH:-/home1/paulocis/private/fondos_data/db.sqlite3}"
BACKUP_DIR="${BACKUP_DIR:-/home1/paulocis/RESPALDOS/fondos_backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEMP_BACKUP="${BACKUP_DIR}/temp_${TIMESTAMP}.sqlite3"
BACKUP_FILENAME="fondos_backup_${TIMESTAMP}.sqlite3.gz"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_FILENAME}"
SHA256_FILE="${BACKUP_DIR}/fondos_backup_${TIMESTAMP}.sha256"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "❌ Error: No se encontró la base de datos en: $DB_PATH" >&2
    exit 1
fi

echo "📦 [$(date +'%Y-%m-%d %H:%M:%S')] Iniciando respaldo consistente de Humm Fondos ($DB_PATH)..."

# 1. Respaldo consistente utilizando la API .backup de SQLite (no copia directa en caliente)
sqlite3 "$DB_PATH" ".backup '$TEMP_BACKUP'"
chmod 600 "$TEMP_BACKUP"

# 2. Verificación de integridad SQLite previa a la compresión
INTEGRITY=$(sqlite3 "$TEMP_BACKUP" "PRAGMA integrity_check;")
if [ "$INTEGRITY" != "ok" ]; then
    echo "❌ Error: La verificación de integridad falló en el archivo temporal: $INTEGRITY" >&2
    rm -f "$TEMP_BACKUP"
    exit 1
fi

# 3. Compresión gzip nivel 9
gzip -9 -c "$TEMP_BACKUP" > "$BACKUP_FILE"
rm -f "$TEMP_BACKUP"
chmod 600 "$BACKUP_FILE"

# 4. Verificación de integridad del archivo comprimido
if ! gunzip -t "$BACKUP_FILE"; then
    echo "❌ Error: El archivo comprimido generado está corrupto." >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi

# 5. Cálculo y guardado de checksum SHA-256
cd "$BACKUP_DIR"
sha256sum "$BACKUP_FILENAME" > "$SHA256_FILE"
chmod 600 "$SHA256_FILE"

FILE_SIZE=$(ls -lh "$BACKUP_FILENAME" | awk '{print $5}')
SHA_VAL=$(awk '{print $1}' "$SHA256_FILE")

echo "✔ Respaldo consistente generado con éxito:"
echo "   - Archivo: ${BACKUP_FILENAME} (${FILE_SIZE})"
echo "   - SHA-256: ${SHA_VAL}"
echo "   - Destino: ${BACKUP_DIR}"

# 6. Política de retención: conservar últimos 14 días
DELETED_COUNT=$(find "$BACKUP_DIR" -name "fondos_backup_*.sqlite3.gz" -mtime +14 -delete -print 2>/dev/null | wc -l || echo 0)
find "$BACKUP_DIR" -name "fondos_backup_*.sha256" -mtime +14 -delete 2>/dev/null || true

echo "ℹ️ Política de retención aplicada: ${DELETED_COUNT} archivos antiguos eliminados (>14 días)."
echo "🎉 [$(date +'%Y-%m-%d %H:%M:%S')] Respaldo completado exitosamente."
