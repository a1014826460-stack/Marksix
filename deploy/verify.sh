#!/usr/bin/env bash
# ============================================================
# 六合彩部署验证脚本
# 验证所有服务端点是否正常响应
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
    check "${service} 运行中" \
        "docker compose ps --services --status running | grep -x '${service}'" \
        "${service}"
}

echo ""
echo "========================================"
echo "  六合彩部署验证"
echo "========================================"
echo ""

echo "[容器状态]"
check_service_running "postgres"
check_service_running "python-api"
check_service_running "backend-admin"
check_service_running "frontend"
check_service_running "nginx"

echo ""
echo "[健康检查端点]"
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
echo "[核心路由]"
check "前端主页 /" \
    "curl -L -s -o /dev/null -w '%{http_code}' http://localhost/" \
    "200"

check "后台管理 /fackyou/login" \
    "curl -L -s -o /dev/null -w '%{http_code}' http://localhost/fackyou/login" \
    "200"

check "前端兼容 API /api/latest-draw" \
    "curl -s -o /dev/null -w '%{http_code}' http://localhost/api/latest-draw" \
    "200"

check "PostgreSQL 连接" \
    "docker compose exec postgres pg_isready -U postgres -d liuhecai 2>&1" \
    "accepting"

echo ""
echo "[HTTPS]"
if grep -q "listen 443" deploy/nginx.conf 2>/dev/null; then
    check "HTTPS /health" \
        "curl -k -s -o /dev/null -w '%{http_code}' https://localhost/health" \
        "200"
else
    echo -e "  ${YELLOW}SKIP${NC} 当前 nginx.conf 未启用 HTTPS"
fi

echo ""
echo "========================================"
echo -e "  结果: ${GREEN}$PASS 通过${NC} / ${RED}$FAIL 失败${NC}"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
