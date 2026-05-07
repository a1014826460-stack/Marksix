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

    log_info "依赖检查通过 ✓"
}

# ---- 准备环境变量 ----
prepare_env() {
    cd "$PROJECT_DIR"

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

    # 检查密码是否为默认值
    if grep -q "POSTGRES_PASSWORD=change_me_in_production" .env 2>/dev/null; then
        log_warn "检测到数据库密码仍为默认值，强烈建议修改!"
    fi
}

# ---- 数据迁移（SQLite → PostgreSQL） ----
migrate_data() {
    log_info "检查是否需要数据迁移..."
    cd "$PROJECT_DIR"

    # 如果 SQLite 文件存在，提示迁移
    if [ -f backend/data/lottery_modes.sqlite3 ]; then
        log_info "检测到 SQLite 数据文件，可以在容器启动后手动执行迁移:"
        echo ""
        echo "  docker compose exec python-api python /app/src/utils/migrate_sqlite_to_postgres.py \\"
        echo "    --sqlite /app/data/lottery_modes.sqlite3 \\"
        echo "    --postgres postgresql://postgres:\${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
        echo ""
    fi

    # 导入固定数据
    if [ -f backend/data/fixed_data.json ] && [ -f backend/data/lottery_modes.sqlite3 ]; then
        log_info "检测到 fixed_data.json，将在启动后自动导入"
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
    sleep 10

    # 检查服务状态
    if docker compose ps | grep -q "Up"; then
        log_info "所有服务启动成功 ✓"
    else
        log_error "部分服务启动失败，请检查日志: docker compose logs"
        exit 1
    fi
}

# ---- 导入固定数据 ----
import_fixed_data() {
    log_info "导入固定数据到数据库..."
    cd "$PROJECT_DIR"

    if docker compose ps | grep -q "python-api.*Up"; then
        docker compose exec -T python-api python /app/src/utils/import_fixed_data.py \
            --json /app/data/fixed_data.json 2>/dev/null || \
            log_warn "fixed_data 导入失败（可能已存在），可忽略"
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
    echo "    SQLite→PG 迁移: docker compose exec python-api python /app/src/utils/migrate_sqlite_to_postgres.py --help"
    echo "    生成文本映射:   docker compose exec python-api python /app/src/utils/build_text_history_mappings.py"
    echo "    导入固定数据:   docker compose exec python-api python /app/src/utils/import_fixed_data.py --json /app/data/fixed_data.json"
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
    migrate_data
    build_images
    start_services
    import_fixed_data
    show_deploy_info
}

main "$@"