#!/usr/bin/env bash
# ============================================================
# 部署验证脚本
# 同时支持：
#   1. 无域名 / IP / HTTP
#   2. 有域名 / HTTPS
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$PROJECT_DIR/.env"
    set +a
fi

validate_production_environment() {
    if [ "${LIUHECAI_RUNTIME_ENV:-production}" != "production" ]; then
        echo -e "${RED}[ERROR]${NC} Production verification requires LIUHECAI_RUNTIME_ENV=production"
        exit 1
    fi
    if grep -Eq '^[[:space:]]*DATABASE_URL[[:space:]]*=' "$PROJECT_DIR/.env" 2>/dev/null; then
        echo -e "${RED}[ERROR]${NC} Root .env must not define DATABASE_URL; Compose injects pgbouncer:6432."
        exit 1
    fi
}

validate_production_environment

VERIFY_HOST="${VERIFY_HOST:-${PUBLIC_HOST:-localhost}}"
VERIFY_HTTP_RESOLVE="--resolve ${VERIFY_HOST}:80:127.0.0.1"
VERIFY_HTTPS_RESOLVE="--resolve ${VERIFY_HOST}:443:127.0.0.1"

PASS=0
FAIL=0

check() {
    local desc="$1"
    local cmd="$2"
    local expected="${3:-200}"
    local actual
    actual=$(eval "$cmd" 2>/dev/null) || true
    if echo "$actual" | grep -q "$expected"; then
        echo -e "  ${GREEN}PASS${NC} $desc"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC} $desc (got: $actual)"
        FAIL=$((FAIL + 1))
    fi
}

check_service_running() {
    local service="$1"
    check "${service} 服务运行中" \
        "docker compose ps --services --status running | grep -x '${service}'" \
        "${service}"
}

echo ""
echo "========================================"
echo "  部署验证"
echo "========================================"
echo ""

echo "[容器状态]"
check_service_running "postgres"
check_service_running "pgbouncer"
check_service_running "python-api"
check_service_running "backend-admin"
check_service_running "frontend"
check_service_running "nginx"

echo ""
echo "[健康检查]"
check "python-api /health" \
    "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health" \
    "200"

check "python-api /api/health" \
    "curl -s http://localhost:8000/api/health | grep -o '\"ok\":true\\|\"ok\": true'" \
    "ok"

if [ "${NGINX_EXPECT_HTTPS:-0}" = "1" ]; then
    check "nginx HTTP 跳转到 HTTPS" \
        "curl -s -o /dev/null -w '%{http_code}' ${VERIFY_HTTP_RESOLVE} http://${VERIFY_HOST}/health" \
        "301\\|308"

    check "nginx HTTPS /health" \
        "curl -k -s -o /dev/null -w '%{http_code}' ${VERIFY_HTTPS_RESOLVE} https://${VERIFY_HOST}/health" \
        "200"
else
    check "nginx /health" \
        "curl -s -o /dev/null -w '%{http_code}' ${VERIFY_HTTP_RESOLVE} http://${VERIFY_HOST}/health" \
        "200"
fi

echo ""
echo "[路由检查]"
if [ "${NGINX_EXPECT_HTTPS:-0}" = "1" ]; then
    check "前端首页 /" \
        "curl -k -L -s -o /dev/null -w '%{http_code}' ${VERIFY_HTTPS_RESOLVE} https://${VERIFY_HOST}/" \
        "200"

    check "后台登录 /fackyou/login" \
        "curl -k -L -s -o /dev/null -w '%{http_code}' ${VERIFY_HTTPS_RESOLVE} https://${VERIFY_HOST}/fackyou/login" \
        "200"

    check "前端兼容 API /api/latest-draw" \
        "curl -k -s -o /dev/null -w '%{http_code}' ${VERIFY_HTTPS_RESOLVE} https://${VERIFY_HOST}/api/latest-draw" \
        "200"
else
    check "前端首页 /" \
        "curl -L -s -o /dev/null -w '%{http_code}' ${VERIFY_HTTP_RESOLVE} http://${VERIFY_HOST}/" \
        "200"

    check "后台登录 /fackyou/login" \
        "curl -L -s -o /dev/null -w '%{http_code}' ${VERIFY_HTTP_RESOLVE} http://${VERIFY_HOST}/fackyou/login" \
        "200"

    check "前端兼容 API /api/latest-draw" \
        "curl -s -o /dev/null -w '%{http_code}' ${VERIFY_HTTP_RESOLVE} http://${VERIFY_HOST}/api/latest-draw" \
        "200"
fi

check "PostgreSQL 可连接" \
    "docker compose exec postgres pg_isready -U postgres -d liuhecai 2>&1" \
    "accepting"

check "PgBouncer 可连接 PostgreSQL" \
    "docker compose exec pgbouncer sh -lc 'PGPASSWORD=\"${POSTGRES_PASSWORD}\" psql -h 127.0.0.1 -p 6432 -U postgres -d liuhecai -tAc \"SELECT 1\"'" \
    "1"

check "python-api 内可用 pg_dump" \
    "docker compose exec python-api sh -lc 'command -v pg_dump >/dev/null && pg_dump --version'" \
    "pg_dump"

echo ""
echo "[HTTPS]"
if [ "${NGINX_EXPECT_HTTPS:-0}" = "1" ]; then
    check "Nginx 已加载 443 SSL 监听" \
        "docker compose exec nginx sh -lc 'nginx -T 2>/dev/null | grep -q \"listen 443 ssl\"'"

    check "HTTPS /health" \
        "curl -k -s -o /dev/null -w '%{http_code}' ${VERIFY_HTTPS_RESOLVE} https://${VERIFY_HOST}/health" \
        "200"
else
    echo -e "  ${YELLOW}SKIP${NC} 当前未启用 HTTPS 校验；如需生产 HTTPS 验证，请设置 NGINX_EXPECT_HTTPS=1"
fi

echo ""
echo "========================================"
echo -e "  结果: ${GREEN}$PASS 通过${NC} / ${RED}$FAIL 失败${NC}"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
