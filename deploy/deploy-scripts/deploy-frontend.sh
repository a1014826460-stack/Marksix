#!/usr/bin/env bash
# 前端节点发布脚本（tw8800 / 前端节点 207.56.2.71:62594）
#
# 用法（推荐经跳板机，见 DEPLOY.md「部署工作流（含跳板机）」）：
#   gzip -c deploy-scripts/deploy-frontend.sh | ssh <跳板参数> root@<前端节点> \
#     "gunzip > /tmp/deploy-frontend.sh && bash /tmp/deploy-frontend.sh <UTC 时间戳>"
#
# 行为：时间戳备份 -> git ff-only 同步 origin/main -> 仅重建 frontend
#       -> nginx -t（只校验不重启）-> 容器状态与容器内文件校验。
#       该节点还承载其他非 Liuhecai 容器，禁止动 nginx/TLS/其他容器。
set -uo pipefail

cd /root/Marksix
STAMP="${1:?usage: deploy-frontend.sh <UTC timestamp e.g. 20260927T135458Z> [label]}"
LABEL="${2:-deploy}"
B="/root/Marksix/.deploy-backups/${LABEL}-${STAMP}"
mkdir -p "$B"

echo "=== 1. 备份到 $B"
git rev-parse HEAD > "$B/HEAD.txt"
git rev-parse --abbrev-ref HEAD >> "$B/HEAD.txt"
git status --porcelain > "$B/status.txt"
git diff > "$B/worktree.patch"
git ls-files --others --exclude-standard > "$B/untracked.txt"
cp -a docker-compose.frontend-node.yml "$B/" 2>/dev/null || true
cp -a .env "$B/" 2>/dev/null || true
cp -a deploy/nginx.frontend-node.conf "$B/" 2>/dev/null || true
echo "部署前 HEAD: $(head -1 "$B/HEAD.txt")  工作区改动: $(wc -l < "$B/status.txt") 项"
ls -1 "$B"

echo "=== 2. 同步 origin/main ==="
git fetch --prune origin main
TARGET=$(git rev-parse origin/main)
echo "目标提交: $TARGET"
git merge --ff-only "$TARGET" || { echo "FF-ONLY 失败，已停在备份状态，请人工处理"; exit 1; }
echo "同步后 HEAD: $(git rev-parse --short HEAD)"

echo "=== 3. 仅重建 frontend（保留 nginx/TLS 与其他容器）==="
docker compose -f docker-compose.frontend-node.yml build frontend 2>&1 | tail -3
docker compose -f docker-compose.frontend-node.yml up -d frontend
echo "up rc=$?"

echo "=== 4. nginx -t（只校验不重启）==="
docker compose -f docker-compose.frontend-node.yml exec -T nginx nginx -t 2>&1 | tail -2

echo "=== 5. 容器状态 ==="
docker compose -f docker-compose.frontend-node.yml ps --format '{{.Name}} {{.Status}}'

echo "=== 6. 站点自检 ==="
for h in www.twbst528.com www.twjsz666.com www.twssz.com www.twsyw.com www.twwanli.com www.twcaibawang.com; do
  printf '%s %s\n' "$h" "$(curl -s -o /dev/null -w '%{http_code}' "https://$h/")"
done
echo "DEPLOY_FRONTEND_DONE $(git rev-parse --short HEAD)"
