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
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---- 检查前置依赖 ----
check_prerequisites() {
    log_info "检查系统依赖..."

    if ! command -v docker &>/dev/null; then
        log_error "Docker 未安装，请执行: curl -fsSL https://get.docker.com | sudo bash"
        exit 1
    fi

    # 检查 Docker Compose (v2 语法: docker compose)
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

# ---- 准备环境变量 ----
prepare_env() {
    cd "$PROJECT_DIR"

    mkdir -p deploy/ssl

    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            log_warn ".env 文件不存在，从 .env.example 复制..."
            cp .env.example .env
            log_warn "请编辑 .env 文件，修改 POSTGRES_PASSWORD 等配置"
        else
            log_error ".env.example 不存在，无法创建 .env"
            exit 1
        fi
    else
        log_info ".env 文件已存在"
    fi

    # 加载 .env 变量到当前 shell
    set -a
    source .env
    set +a

    # 检查密码是否为默认值
    if grep -q "POSTGRES_PASSWORD=change_me_in_production" .env 2>/dev/null; then
        log_warn "检测到数据库密码仍为默认值，强烈建议修改!"
    fi
}

# ---- 数据迁移（SQLite → PostgreSQL） ----
migrate_data() {
    log_info "检查是否需要数据迁移..."
    cd "$PROJECT_DIR"

    if [ "${RUN_SQLITE_MIGRATION:-0}" != "1" ]; then
        log_info "未设置 RUN_SQLITE_MIGRATION=1，跳过 SQLite→PostgreSQL 自动迁移"
        return
    fi

    # 获取数据库密码
    DB_PASS="${POSTGRES_PASSWORD:-change_me_in_production}"
    PG_DSN="postgresql://postgres:${DB_PASS}@postgres:5432/liuhecai"

    if [ -f backend/data/lottery_modes.sqlite3 ]; then
        log_info "检测到 SQLite 数据文件，开始迁移到 PostgreSQL..."
        if docker compose ps | grep -q "python-api.*Up"; then
            docker compose exec -T python-api python /app/src/tools/migrate_sqlite_to_postgres.py \
                --source-sqlite /app/data/lottery_modes.sqlite3 \
                --target-dsn "${PG_DSN}" \
                --drop-existing 2>&1 || log_warn "SQLite→PG 迁移失败，请检查日志"
        else
            log_warn "Python API 容器未运行，跳过迁移"
        fi
    fi
}

# ---- 构建镜像 ----
build_images() {
    log_info "构建 Docker 镜像..."

    cd "$PROJECT_DIR"

    log_info "构建 Python API 镜像..."
    docker compose build python-api

    log_info "构建 Next.js 后端管理镜像..."
    docker compose build backend-admin

    log_info "构建 Next.js 前端镜像..."
    docker compose build frontend

    log_info "所有镜像构建完成 ✓"
}

# ---- 启动服务 ----
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

# ---- 导入固定数据 ----
import_fixed_data() {
    log_info "导入固定数据到数据库..."
    cd "$PROJECT_DIR"

    DB_PASS="${POSTGRES_PASSWORD:-change_me_in_production}"
    PG_DSN="postgresql://postgres:${DB_PASS}@postgres:5432/liuhecai"

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
                docker compose exec -T python-api python /app/src/tools/import_fixed_data.py \
                    --fixed-data-path /app/data/fixed_data.json \
                    --db-path "${PG_DSN}" 2>&1 || \
                    log_warn "fixed_data 导入失败，请检查日志"
            fi
        else
            log_warn "backend/data/fixed_data.json 不存在，跳过固定数据导入"
        fi
    fi
}

# ---- 显示部署信息 ----
show_deploy_info() {
    echo ""
    echo "============================================"
    echo -e "  ${GREEN}六合彩彩票数据管理系统 部署完成${NC}"
    echo "============================================"
    echo ""
    echo "  访问地址:"
    echo "    前端站点:     http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')"
    echo "    后端管理:     http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')/admin"
    echo "    Python API:   http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')/api"
    echo ""
    echo "  常用命令:"
    echo "    查看日志:     docker compose logs -f"
    echo "    查看状态:     docker compose ps"
    echo "    停止服务:     docker compose down"
    echo "    重启服务:     docker compose restart"
    echo "    进入 API 容器: docker compose exec python-api bash"
    echo ""
    echo "  数据管理:"
    echo "    SQLite→PG 迁移: docker compose exec python-api python /app/src/tools/migrate_sqlite_to_postgres.py --help"
    echo "    生成文本映射:   docker compose exec python-api python /app/src/utils/build_text_history_mappings.py --db-path postgresql://postgres:\${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
    echo "    规范化数据表:   docker compose exec python-api python /app/src/utils/normalize_sqlite.py --db-path postgresql://postgres:\${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
    echo "    导入固定数据:   docker compose exec python-api python /app/src/tools/import_fixed_data.py --fixed-data-path /app/data/fixed_data.json --db-path postgresql://postgres:\${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
    echo "    HTTPS 说明:     默认仅启用 HTTP；如需 HTTPS，请按 DEPLOY.md 配置证书和 Nginx 443 server"
    echo ""
}

# ---- 主流程 ----
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
