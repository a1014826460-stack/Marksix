#!/usr/bin/env bash
# 中心节点发布脚本（tw8800 / 中心后端节点 207.56.3.82:29618）
#
# 用法（推荐经跳板机，见 DEPLOY.md「部署工作流（含跳板机）」）：
#   gzip -c deploy-scripts/deploy-center.sh | ssh <跳板参数> root@<中心节点> \
#     "gunzip > /tmp/deploy-center.sh && bash /tmp/deploy-center.sh <UTC 时间戳>"
#
# 行为：时间戳备份 -> git ff-only 同步 origin/main -> 重建 db-migrate/python-api/scheduler-worker/frontend
#       -> nginx -t -> 容器状态与容器内文件校验。不重建 PostgreSQL/PgBouncer/数据卷。
#
# 注意：db-migrate 必须一起重建。python-api/scheduler-worker 都声明
#   depends_on: db-migrate: condition: service_completed_successfully，
# 而 db-migrate 是自带 build: 的一次性服务；只 build python-api 会让 db-migrate
# 用旧镜像跑出「Schema migrations are already current」，随后新版 python-api 因
# validate_runtime_schema 判定缺版本而崩溃重启（2026-09-28 迁移 30/31 上线时实际发生）。
set -uo pipefail

cd /root/Marksix
STAMP="${1:?usage: deploy-center.sh <UTC timestamp e.g. 20260927T134420Z> [label]}"
LABEL="${2:-deploy}"
B="/root/Marksix/.deploy-backups/${LABEL}-${STAMP}"
mkdir -p "$B"

echo "=== 1. 备份到 $B"
git rev-parse HEAD > "$B/HEAD.txt"
git rev-parse --abbrev-ref HEAD >> "$B/HEAD.txt"
git status --porcelain > "$B/status.txt"
git diff > "$B/worktree.patch"
git ls-files --others --exclude-standard > "$B/untracked.txt"
cp -a docker-compose.yml "$B/" 2>/dev/null || true
cp -a .env "$B/" 2>/dev/null || true
cp -a deploy/nginx.conf "$B/" 2>/dev/null || true
echo "部署前 HEAD: $(head -1 "$B/HEAD.txt")  工作区改动: $(wc -l < "$B/status.txt") 项"
ls -1 "$B"

echo "=== 2. 同步 origin/main"
git fetch --prune origin main
TARGET=$(git rev-parse origin/main)
echo "目标提交: $TARGET"
git merge --ff-only "$TARGET" || { echo "FF-ONLY 失败，已停在备份状态，请人工处理"; exit 1; }
echo "同步后 HEAD: $(git rev-parse --short HEAD)"

echo "=== 3. 重建 db-migrate / python-api / scheduler-worker / frontend ==="
docker compose build db-migrate python-api scheduler-worker frontend 2>&1 | tail -3
docker compose up -d python-api scheduler-worker frontend
echo "up rc=$?"

echo "=== 4. nginx -t ==="
docker compose exec -T nginx nginx -t 2>&1 | tail -2

echo "=== 5. 容器状态 ==="
docker compose ps --format '{{.Name}} {{.Status}}' | head -10

echo "=== 6. 公网自检（最多等 60s，避免 up -d 预热 502 掩盖真实故障）==="
HEALTH_OK=0
for attempt in $(seq 1 12); do
  FAIL=0
  for h in www.tw8800.com www.twcaibawang.com; do
    c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://$h/health")
    printf '%s %s (第 %s 次)\n' "$h" "$c" "$attempt"
    [ "$c" = "200" ] || FAIL=1
  done
  if [ "$FAIL" = "0" ]; then HEALTH_OK=1; break; fi
  sleep 5
done
if [ "$HEALTH_OK" != "1" ]; then
  echo "!! /health 60s 内未恢复，打印 python-api / db-migrate 日志尾部"
  docker compose logs --tail 30 python-api
  docker compose logs --tail 10 db-migrate
  echo "DEPLOY_CENTER_FAILED $(git rev-parse --short HEAD)"
  exit 1
fi
echo "DEPLOY_CENTER_DONE $(git rev-parse --short HEAD)"
