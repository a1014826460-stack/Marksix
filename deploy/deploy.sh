#!/usr/bin/env bash
# ============================================================
# 六合彩彩票数据管理系统 - 一键部署脚本
# 适用于 Ubuntu 24.04 LTS
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

check_prerequisites() {
    log_info "检查系统依赖..."

    if ! command -v docker &>/dev/null; then
        log_error "Docker 未安装，请执行: curl -fsSL https://get.docker.com | sudo bash"
        exit 1
    fi

    if ! docker compose version &>/dev/null; then
        log_error "Docker Compose 插件未安装，请执行: sudo apt install -y docker-compose-plugin"
        exit 1
    fi

    if ! docker info &>/dev/null; then
        log_error "Docker daemon 未启动，请先启动 Docker 服务"
        exit 1
    fi

    log_info "依赖检查通过 ✓"
}

prepare_env() {
    cd "$PROJECT_DIR"

    mkdir -p deploy/ssl

    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            log_warn ".env 文件不存在，从 .env.example 复制..."
            cp .env.example .env
            log_warn "请编辑 .env 文件，至少修改 POSTGRES_PASSWORD"
        else
            log_error ".env.example 不存在，无法创建 .env"
            exit 1
        fi
    else
        log_info ".env 文件已存在"
    fi

    if grep -q "POSTGRES_PASSWORD=change_me_in_production" .env 2>/dev/null; then
        log_warn "检测到数据库密码仍为默认值，强烈建议修改"
    fi
}

migrate_data() {
    cd "$PROJECT_DIR"

    if [ "${RUN_SQLITE_MIGRATION:-0}" != "1" ]; then
        return
    fi

    log_warn "当前重构后的仓库未包含可直接执行的 SQLite→PostgreSQL 迁移脚本，已跳过自动迁移"
    log_warn "如果你仍只有历史 SQLite 数据，请先在旧工具/旧分支完成迁移，再导入 PostgreSQL"
}

build_images() {
    log_info "构建 Docker 镜像..."

    cd "$PROJECT_DIR"
    docker compose build python-api
    docker compose build backend-admin
    docker compose build frontend

    log_info "所有镜像构建完成 ✓"
}

start_services() {
    log_info "启动服务..."
    cd "$PROJECT_DIR"

    docker compose up -d

    log_info "等待服务就绪..."
    local services=(postgres python-api backend-admin frontend nginx)
    local service
    local attempt

    for attempt in {1..24}; do
        local all_ready=1
        for service in "${services[@]}"; do
            if ! docker compose ps --services --status running | grep -qx "$service"; then
                all_ready=0
                break
            fi
        done

        if [ "$all_ready" -eq 1 ]; then
            log_info "所有服务启动成功 ✓"
            return
        fi

        sleep 5
    done

    log_error "部分服务未在预期时间内启动，请检查日志: docker compose logs"
    docker compose ps || true
    exit 1
}

import_fixed_data() {
    log_info "导入 fixed_data 到数据库..."
    cd "$PROJECT_DIR"

    if docker compose ps | grep -q "python-api.*Up"; then
        if [ -f backend/data/fixed_data.json ]; then
            local fixed_exists
            fixed_exists="$(
                docker compose exec -T postgres psql -U postgres -d liuhecai -tAc \
                    "SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'fixed_data'
                    )" 2>/dev/null | tr -d '[:space:]'
            )"

            if [ "$fixed_exists" = "t" ]; then
                log_info "fixed_data 表已存在，跳过初始化导入"
            else
                docker compose exec -T python-api sh -lc \
                    'python /app/src/tools/import_fixed_data.py --fixed-data-path /app/data/fixed_data.json --db-path "$DATABASE_URL"' \
                    2>&1 || \
                    log_warn "fixed_data 导入失败，请检查日志"
            fi
        else
            log_warn "backend/data/fixed_data.json 不存在，跳过固定数据导入"
        fi
    fi
}

show_deploy_info() {
    local host_ip
    host_ip="$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')"

    echo ""
    echo "============================================"
    echo -e "  ${GREEN}六合彩彩票数据管理系统 部署完成${NC}"
    echo "============================================"
    echo ""
    echo "  对外访问:"
    echo "    前端站点:        http://${host_ip}/"
    echo "    后台管理:        http://${host_ip}/admin"
    echo "    前端兼容 API:    http://${host_ip}/api/..."
    echo ""
    echo "  服务器本机访问:"
    echo "    Python API:      http://127.0.0.1:8000/api/health"
    echo "    PostgreSQL:      127.0.0.1:5432"
    echo ""
    echo "  常用命令:"
    echo "    查看日志:        docker compose logs -f"
    echo "    查看状态:        docker compose ps"
    echo "    停止服务:        docker compose down"
    echo "    重启服务:        docker compose restart"
    echo "    进入 API 容器:   docker compose exec python-api bash"
    echo ""
    echo "  数据初始化命令:"
    echo "    规范化数据表:    docker compose exec python-api python /app/src/utils/normalize_payload_tables.py --db-path postgresql://postgres:\${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
    echo "    生成文本映射:    docker compose exec python-api python /app/src/utils/build_text_history_mappings.py --db-path postgresql://postgres:\${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
    echo "    导入 fixed_data: docker compose exec python-api python /app/src/tools/import_fixed_data.py --fixed-data-path /app/data/fixed_data.json --db-path postgresql://postgres:\${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
    echo ""
    echo "  HTTPS:"
    echo "    默认 nginx.conf 仅启用 HTTP"
    echo "    绑定域名与 HTTPS 时，请参考 DEPLOY.md 和 deploy/nginx.domain.ssl.conf.example"
    echo ""
}

main() {
    echo ""
    echo "============================================"
    echo "  六合彩彩票数据管理系统 - 部署工具"
    echo "  目标系统: Ubuntu 24.04 LTS"
    echo "============================================"
    echo ""

    check_prerequisites
    prepare_env
    build_images
    start_services
    migrate_data
    import_fixed_data
    show_deploy_info
}

main "$@"
