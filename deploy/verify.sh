#!/usr/bin/env bash
# ============================================================
# Deployment verification script
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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
    check "${service} running" \
        "docker compose ps --services --status running | grep -x '${service}'" \
        "${service}"
}

echo ""
echo "========================================"
echo "  Deployment Verification"
echo "========================================"
echo ""

echo "[Containers]"
check_service_running "postgres"
check_service_running "python-api"
check_service_running "backend-admin"
check_service_running "frontend"
check_service_running "nginx"

echo ""
echo "[Health]"
check "python-api /health" \
    "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health" \
    "200"

check "python-api /api/health" \
    "curl -s http://localhost:8000/api/health | grep -o '\"ok\":true\\|\"ok\": true'" \
    "ok"

check "nginx /health" \
    "curl -s -o /dev/null -w '%{http_code}' http://localhost/health" \
    "200"

echo ""
echo "[Routes]"
check "frontend /" \
    "curl -L -s -o /dev/null -w '%{http_code}' http://localhost/" \
    "200"

check "admin /fackyou/login" \
    "curl -L -s -o /dev/null -w '%{http_code}' http://localhost/fackyou/login" \
    "200"

check "frontend API /api/latest-draw" \
    "curl -s -o /dev/null -w '%{http_code}' http://localhost/api/latest-draw" \
    "200"

check "PostgreSQL connection" \
    "docker compose exec postgres pg_isready -U postgres -d liuhecai 2>&1" \
    "accepting"

check "pg_dump available in python-api" \
    "docker compose exec python-api sh -lc 'command -v pg_dump >/dev/null && pg_dump --version'" \
    "pg_dump"

echo ""
echo "[HTTPS]"
if [ "${NGINX_EXPECT_HTTPS:-0}" = "1" ]; then
    check "Nginx loaded 443 SSL listener" \
        "docker compose exec nginx sh -lc 'nginx -T 2>/dev/null | grep -q \"listen 443 ssl\"'"

    check "HTTPS /health" \
        "curl -k -s -o /dev/null -w '%{http_code}' https://localhost/health" \
        "200"
else
    echo -e "  ${YELLOW}SKIP${NC} HTTPS validation disabled; set NGINX_EXPECT_HTTPS=1 in production"
fi

echo ""
echo "========================================"
echo -e "  Result: ${GREEN}$PASS passed${NC} / ${RED}$FAIL failed${NC}"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
