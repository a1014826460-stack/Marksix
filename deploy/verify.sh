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

echo ""
echo "========================================"
echo "  六合彩部署验证"
echo "========================================"
echo ""

# ── 容器状态 ──
echo "[容器状态]"
check "postgres 运行中"      "docker compose ps --format json | grep -o 'liuhecai-postgres.*Up'"
check "python-api 运行中"    "docker compose ps --format json | grep -o 'liuhecai-python-api.*Up'"
check "backend-admin 运行中" "docker compose ps --format json | grep -o 'liuhecai-backend-admin.*Up'"
check "frontend 运行中"      "docker compose ps --format json | grep -o 'liuhecai-frontend.*Up'"
check "nginx 运行中"         "docker compose ps --format json | grep -o 'liuhecai-nginx.*Up'"

echo ""
echo "[健康检查端点]"
# python-api /health
check "python-api /health" \
    "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health" \
    "200"

# python-api /api/health (带数据库摘要)
check "python-api /api/health" \
    "curl -s http://localhost:8000/api/health | grep -o '\"ok\": true'" \
    "ok"

# nginx /health → python-api
check "nginx /health" \
    "curl -s -o /dev/null -w '%{http_code}' http://localhost/health" \
    "200"

echo ""
echo "[核心路由]"
# 前端主页
check "前端主页 /" \
    "curl -s -o /dev/null -w '%{http_code}' http://localhost/" \
    "200"

# 后台管理 /admin
check "后台管理 /admin" \
    "curl -s -o /dev/null -w '%{http_code}' http://localhost/admin" \
    "200"

# 数据库连接
check "PostgreSQL 连接" \
    "docker compose exec postgres pg_isready -U postgres -d liuhecai 2>&1" \
    "accepting"

echo ""
echo "========================================"
echo -e "  结果: ${GREEN}$PASS 通过${NC} / ${RED}$FAIL 失败${NC}"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
