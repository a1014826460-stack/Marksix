#!/bin/sh
set -eu
ROOT=${1:-/root/Marksix}
BACKUP=${2:?backup directory required}
install -D -m 0644 "$BACKUP/nginx.conf.local.before" "$ROOT/deploy/nginx.conf.local"
echo "RESTORED_NGINX_CONFIG=$ROOT/deploy/nginx.conf.local"
if [ "${ROLLBACK_RELOAD:-0}" = 1 ]; then
  docker compose -f "$ROOT/docker-compose.yml" exec -T nginx nginx -t
  docker compose -f "$ROOT/docker-compose.yml" exec -T nginx nginx -s reload
fi
