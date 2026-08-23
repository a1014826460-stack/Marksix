#!/bin/sh
set -eu
ROOT=${1:-/root/Marksix}
BACKUP=${2:?backup directory required}
for f in \
  frontend/public/vendor/_shared/forced-announcement.js \
  backend/src/alerts/alert_service.py \
  backend/src/database/versioned_migrations.py
do
  install -D -m 0644 "$BACKUP/$f" "$ROOT/$f"
done
echo "RESTORED_SOURCE_FILES=$ROOT"
if [ "${ROLLBACK_REBUILD:-0}" = 1 ]; then
  docker compose -f "$ROOT/docker-compose.yml" build db-migrate frontend python-api scheduler-worker
  docker compose -f "$ROOT/docker-compose.yml" up -d --no-deps --force-recreate frontend python-api scheduler-worker
fi
