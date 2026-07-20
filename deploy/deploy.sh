#!/usr/bin/env bash
# ============================================================
# Liuhecai 部署脚本
# 支持两种模式：
#   1. 无域名 / IP / HTTP
#   2. 有域名 / HTTPS
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

load_env() {
    cd "$PROJECT_DIR"

    if [ -f .env ]; then
        set -a
        # shellcheck disable=SC1091
        . ./.env
        set +a
    fi
}

validate_production_environment() {
    cd "$PROJECT_DIR"

    if [ "${LIUHECAI_RUNTIME_ENV:-production}" != "production" ]; then
        log_error "Production deployment requires LIUHECAI_RUNTIME_ENV=production"
        exit 1
    fi

    if grep -Eq '^[[:space:]]*DATABASE_URL[[:space:]]*=' .env 2>/dev/null; then
        log_error "Root .env must not define DATABASE_URL; production services receive pgbouncer:6432 only from docker-compose.yml"
        exit 1
    fi
}

check_prerequisites() {
    log_info "检查部署前置条件..."

    if ! command -v docker >/dev/null 2>&1; then
        log_error "未检测到 Docker。请先执行: curl -fsSL https://get.docker.com | sudo bash"
        exit 1
    fi

    if ! docker compose version >/dev/null 2>&1; then
        log_error "未检测到 Docker Compose 插件。请先执行: sudo apt install -y docker-compose-plugin"
        exit 1
    fi

    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon 未启动，请先启动 Docker 服务"
        exit 1
    fi

    log_info "前置条件检查通过"
}

prepare_env() {
    cd "$PROJECT_DIR"

    mkdir -p deploy/ssl

    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            log_warn "未找到 .env，正在从 .env.example 复制..."
            cp .env.example .env
            log_warn "请先编辑 .env，至少修改 POSTGRES_PASSWORD 后再用于生产环境"
        else
            log_error "未找到 .env.example，无法自动创建 .env"
            exit 1
        fi
    else
        log_info ".env 已存在"
    fi

    if grep -q "POSTGRES_PASSWORD=change_me_in_production" .env 2>/dev/null; then
        log_warn "POSTGRES_PASSWORD 仍是默认占位值，请尽快修改"
    fi
}

validate_deploy_mode() {
    cd "$PROJECT_DIR"

    local nginx_conf_source="${NGINX_CONF_SOURCE:-./deploy/nginx.conf}"
    local https_expected="${NGINX_EXPECT_HTTPS:-0}"
    local public_host="${PUBLIC_HOST:-localhost}"
    local public_scheme="${PUBLIC_SCHEME:-http}"

    if [ ! -f "$nginx_conf_source" ]; then
        log_error "NGINX_CONF_SOURCE 指向的文件不存在: $nginx_conf_source"
        exit 1
    fi

    if [ "$https_expected" = "1" ]; then
        if [ "$public_scheme" != "https" ]; then
            log_error "当 NGINX_EXPECT_HTTPS=1 时，PUBLIC_SCHEME 必须为 https"
            exit 1
        fi

        if [ "$nginx_conf_source" = "./deploy/nginx.conf" ]; then
            log_error "HTTPS 模式不能继续使用默认的 HTTP 配置 deploy/nginx.conf"
            log_error "请先复制 SSL 示例配置到 deploy/nginx.conf.local，并让 NGINX_CONF_SOURCE 指向它"
            exit 1
        fi

        if [ ! -f deploy/ssl/fullchain.pem ] || [ ! -f deploy/ssl/privkey.pem ]; then
            log_error "HTTPS 模式要求存在 deploy/ssl/fullchain.pem 和 deploy/ssl/privkey.pem"
            exit 1
        fi

        log_info "当前部署模式: 域名 + HTTPS (${public_host})"
    else
        if [ "$public_scheme" != "http" ]; then
            log_warn "当前为 HTTP 模式，建议将 PUBLIC_SCHEME 设置为 http"
        fi
        log_info "当前部署模式: 无域名/IP + HTTP (${public_host})"
    fi
}

migrate_data() {
    cd "$PROJECT_DIR"

    if [ "${RUN_SQLITE_MIGRATION:-0}" != "1" ]; then
        return
    fi

    log_warn "当前仓库不包含自动 SQLite -> PostgreSQL 迁移脚本"
    log_warn "如果你只有历史 SQLite 数据，请先单独完成迁移后再导入 PostgreSQL"
}

build_images() {
    log_info "开始构建 Docker 镜像..."
    cd "$PROJECT_DIR"

    docker compose build python-api
    docker compose build backend-admin
    docker compose build frontend

    log_info "镜像构建完成"
}

container_health_status() {
    local container_name="$1"
    docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_name" 2>/dev/null || true
}

container_running_status() {
    local container_name="$1"
    docker inspect -f '{{.State.Status}}' "$container_name" 2>/dev/null || true
}

start_services() {
    log_info "开始启动服务..."
    cd "$PROJECT_DIR"

    docker compose up -d || true

    log_info "等待服务就绪..."
    local healthy_services=(postgres pgbouncer python-api backend-admin frontend)
    local running_services=(nginx)
    local service
    local attempt
    local status
    local all_ready

    for attempt in {1..24}; do
        all_ready=1

        for service in "${healthy_services[@]}"; do
            status="$(container_health_status "liuhecai-${service}")"
            if [ "$status" != "healthy" ]; then
                all_ready=0
                break
            fi
        done

        if [ "$all_ready" -eq 1 ]; then
            for service in "${running_services[@]}"; do
                status="$(container_running_status "liuhecai-${service}")"
                if [ "$status" != "running" ]; then
                    all_ready=0
                    break
                fi
            done
        fi

        if [ "$all_ready" -eq 1 ]; then
            log_info "所有服务已就绪"
            return
        fi

        sleep 5
    done

    log_error "部分服务未在预期时间内就绪"
    docker compose ps || true

    for service in "${healthy_services[@]}" "${running_services[@]}"; do
        log_warn "最近日志: ${service}"
        docker compose logs --tail 80 "$service" || true
    done

    exit 1
}

import_fixed_data() {
    log_info "按需导入 fixed_data ..."
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
                    2>&1 || log_warn "fixed_data 导入失败，请检查日志"
            fi
        else
            log_warn "未找到 backend/data/fixed_data.json，跳过 fixed_data 导入"
        fi
    fi
}

show_deploy_info() {
    local host_ip
    local public_host
    local public_scheme

    host_ip="$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')"
    public_host="${PUBLIC_HOST:-$host_ip}"
    public_scheme="${PUBLIC_SCHEME:-http}"

    echo ""
    echo "============================================"
    echo -e "  ${GREEN}部署完成${NC}"
    echo "============================================"
    echo ""
    echo "  对外访问入口:"
    echo "    前端:            ${public_scheme}://${public_host}/"
    echo "    后台:            ${public_scheme}://${public_host}/fackyou/login"
    echo "    前端兼容 API:    ${public_scheme}://${public_host}/api/..."
    echo ""
    echo "  宿主机本地访问:"
    echo "    Python API:      http://127.0.0.1:8000/api/health"
    echo "    PostgreSQL:      127.0.0.1:5432"
    echo "    PgBouncer:       127.0.0.1:6432"
    echo ""
    echo "  常用命令:"
    echo "    查看日志:        docker compose logs -f"
    echo "    查看状态:        docker compose ps"
    echo "    停止服务:        docker compose down"
    echo "    重启服务:        docker compose restart"
    echo "    进入 API 容器:   docker compose exec python-api bash"
    echo ""
}

main() {
    echo ""
    echo "============================================"
    echo "  Liuhecai 部署工具"
    echo "============================================"
    echo ""

    check_prerequisites
    prepare_env
    load_env
    validate_production_environment
    validate_deploy_mode
    build_images
    start_services
    migrate_data
    import_fixed_data
    show_deploy_info
}

main "$@"
