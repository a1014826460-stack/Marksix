#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
central_nginx="$project_dir/deploy/nginx.conf"
node_compose="$project_dir/docker-compose.frontend-node.yml"
node_nginx="$project_dir/deploy/nginx.frontend-node.conf"
node_env="$project_dir/.env.frontend-node.example"

test -f "$node_compose"
test -f "$node_nginx"
test -f "$node_env"

# The central API stays behind the existing public HTTPS endpoint and keeps
# the frontend compatibility routes under /api/ separate from the raw API.
grep -Fq 'location ^~ /central-api/api/' "$central_nginx"
grep -Fq 'proxy_pass http://python-api:8000/api/;' "$central_nginx"
grep -Fq 'location ^~ /central-api/uploads/' "$central_nginx"
grep -Fq 'proxy_pass http://python-api:8000/uploads/;' "$central_nginx"

# Frontend nodes must not create a second writer, scheduler, or database.
for forbidden_service in postgres pgbouncer python-api scheduler-worker db-migrate backend-admin; do
    if grep -Eq "^[[:space:]]{2}${forbidden_service}:" "$node_compose"; then
        echo "frontend node compose must not define ${forbidden_service}" >&2
        exit 1
    fi
done
grep -Fq 'LOTTERY_BACKEND_BASE_URL: "${LOTTERY_BACKEND_BASE_URL:?Set LOTTERY_BACKEND_BASE_URL to the central API}"' "$node_compose"
grep -Fq 'LOTTERY_UPLOADS_BASE_URL: "${LOTTERY_UPLOADS_BASE_URL:?Set LOTTERY_UPLOADS_BASE_URL to the central uploads API}"' "$node_compose"
grep -Fq 'https://www.tw8800.com/central-api/api' "$node_env"
grep -Fq 'https://www.tw8800.com/central-api/uploads' "$node_env"
grep -Fq 'proxy_pass http://frontend:3000;' "$node_nginx"
if grep -Fq 'python-api' "$node_nginx"; then
    echo "frontend node nginx must not proxy to a local python-api" >&2
    exit 1
fi

# Images are source-of-truth data too: remote frontend nodes must proxy them
# from the central API instead of carrying a copied backend data directory.
grep -Fq 'LOTTERY_UPLOADS_BASE_URL' "$project_dir/frontend/app/uploads/[...path]/route.ts"
grep -Fq 'LOTTERY_UPLOADS_BASE_URL' "$project_dir/frontend/app/uploads/image/[bucket]/[filename]/route.ts"
if grep -Fq 'COPY --chown=nextjs:nodejs backend/data/Images' "$project_dir/Dockerfile.frontend"; then
    echo "frontend image must not embed central backend images" >&2
    exit 1
fi
