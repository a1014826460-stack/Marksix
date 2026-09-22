#!/usr/bin/env bash
# 证书续期 + 同步 + 校验（十个站点及同机其它域名）。
#
# 为什么需要这个脚本：
#   1. certbot 只更新 /etc/letsencrypt/live/**，而 nginx 容器实际挂载的是
#      <repo>/deploy/ssl/**；两者之间原来靠人工 cp，一旦漏做就会出现
#      “certbot 已续期、线上仍是旧证书”乃至证书过期（2026-09-22 的
#      www.twtongtian.com 就是这样过期了 19 天）。
#   2. 本机 nginx 占用 80 端口，certbot 的 standalone 验证会失败；webroot 验证
#      又依赖 webroot 目录被挂载进 nginx 容器。为不改动线上 nginx 配置，这里用
#      --pre-hook/--post-hook 在**确有证书需要续期时**短暂停/起 nginx 容器，再走
#      standalone 验证。
#   3. 续期后必须 reload nginx，否则仍继续加载旧证书。
#
# 重要：本脚本只对 **nginx 容器本身** 执行 stop/start/exec，**绝不调用 docker compose**。
#   两台服务器的仓库目录同名（Marksix），compose 项目名因此都是 marksix；在同一台机器上
#   误用另一份 compose 文件（中心节点 docker-compose.yml / 前端节点
#   docker-compose.frontend-node.yml）会让 compose 以同名容器替换掉本机真实服务，
#   并顺带创建 postgres/pgbouncer/redis 等依赖容器 —— 2026-09-22 就是这样把前端节点
#   的 nginx 和 frontend 顶掉、5 个站点中断约 10 分钟。改用容器级操作后，
#   这个失效模式在结构上不可能再发生。
#
# 用法：
#   scripts/sync-nginx-certs.sh [--dry-run] [--min-days N] [--skip-renew]
# 环境变量：
#   LIUHECAI_REPO            仓库目录，默认 /root/Marksix
#   LIUHECAI_NGINX_CONTAINER nginx 容器名，默认 liuhecai-nginx
#   LIUHECAI_SSL_LOG         日志文件，默认 /var/log/liuhecai-ssl-sync.log
# 配置：
#   <repo>/deploy/ssl-sync.map   每行 “<letsencrypt lineage 目录名> <deploy/ssl 下相对子目录或 .>”
#
# 退出码：0 正常；1 有证书已过期或剩余天数低于阈值；2 执行环境错误。

set -uo pipefail

REPO="${LIUHECAI_REPO:-/root/Marksix}"
NGINX_CONTAINER="${LIUHECAI_NGINX_CONTAINER:-liuhecai-nginx}"
MAP_FILE="${REPO}/deploy/ssl-sync.map"
LOG_FILE="${LIUHECAI_SSL_LOG:-/var/log/liuhecai-ssl-sync.log}"

DRY_RUN=0
SKIP_RENEW=0
MIN_DAYS=14

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --skip-renew) SKIP_RENEW=1 ;;
    --min-days) shift; MIN_DAYS="${1:-14}" ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

log() {
  local line
  line="$(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"
  echo "$line"
  if [ "$DRY_RUN" -eq 0 ]; then
    printf '%s\n' "$line" >> "$LOG_FILE" 2>/dev/null || true
  fi
}

container_running() {
  [ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null)" = "true" ]
}

nginx_running() { container_running "$NGINX_CONTAINER"; }
nginx_stop()    { docker stop "$NGINX_CONTAINER" >/dev/null 2>&1 || true; }
nginx_start()   { docker start "$NGINX_CONTAINER" >/dev/null 2>&1 || true; sleep 3; }
nginx_test()    { docker exec "$NGINX_CONTAINER" nginx -t >/dev/null 2>&1; }
nginx_reload()  { docker exec "$NGINX_CONTAINER" nginx -s reload >/dev/null 2>&1; }

if [ ! -d "$REPO" ]; then
  echo "repo not found: $REPO" >&2
  exit 2
fi
if ! docker inspect "$NGINX_CONTAINER" >/dev/null 2>&1; then
  echo "nginx container not found: $NGINX_CONTAINER (set LIUHECAI_NGINX_CONTAINER)" >&2
  exit 2
fi

cd "$REPO" || exit 2

restore_nginx() {
  # 任何退出路径都必须让 nginx 处于运行状态，否则整机站点会一直 502。
  if ! nginx_running; then
    log "restoring nginx container after interrupt"
    nginx_start
  fi
}
trap restore_nginx EXIT

# ── 读取映射 ────────────────────────────────────────────────
if [ -f "$MAP_FILE" ]; then
  log "using mapping file: $MAP_FILE"
  mapfile -t MAP_LINES < <(grep -vE '^\s*(#|$)' "$MAP_FILE")
else
  log "mapping file missing ($MAP_FILE); falling back to every letsencrypt lineage -> its own subdir"
  mapfile -t MAP_LINES < <(
    for d in /etc/letsencrypt/live/*/; do
      [ -d "$d" ] || continue
      name="$(basename "$d")"
      printf '%s %s\n' "$name" "$name"
    done
  )
fi

if [ "${#MAP_LINES[@]}" -eq 0 ]; then
  log "ERROR: no certificate mapping configured"
  exit 2
fi

target_dir_for() {
  local sub="$1"
  if [ "$sub" = "." ] || [ -z "$sub" ]; then
    printf '%s' "$REPO/deploy/ssl"
  else
    printf '%s' "$REPO/deploy/ssl/$sub"
  fi
}

# ── 当前状态 ────────────────────────────────────────────────
report_state() {
  local label="$1" now_epoch days end_date
  now_epoch="$(date -u +%s)"
  log "--- certificate state ($label) ---"
  for entry in "${MAP_LINES[@]}"; do
    set -- $entry
    local lineage="$1" sub="${2:-.}"
    local file; file="$(target_dir_for "$sub")/fullchain.pem"
    if [ ! -f "$file" ]; then
      log "MISSING    ${lineage} -> ${sub}"
      continue
    fi
    end_date="$(openssl x509 -enddate -noout -in "$file" 2>/dev/null | sed 's/notAfter=//')"
    if [ -z "$end_date" ]; then
      log "UNREADABLE ${lineage} -> ${sub}"
      continue
    fi
    local end_epoch
    end_epoch="$(date -u -d "$end_date" +%s 2>/dev/null || echo 0)"
    days=$(( (end_epoch - now_epoch) / 86400 ))
    if [ "$days" -lt 0 ]; then
      log "EXPIRED    ${lineage} -> ${sub}  end=${end_date}"
    else
      log "OK         ${lineage} -> ${sub}  days_left=${days}  end=${end_date}"
    fi
  done
  log "---------------------------------"
}

report_state "before"

# ── 续期 ────────────────────────────────────────────────────
renewed=0
if [ "$SKIP_RENEW" -eq 1 ]; then
  log "renewal skipped (--skip-renew)"
elif [ "$DRY_RUN" -eq 1 ]; then
  log "dry-run: would stop ${NGINX_CONTAINER} only if a certificate is due, then run certbot renew --standalone"
else
  log "running certbot renew (standalone; ${NGINX_CONTAINER} stopped only when a certificate is due)"
  # certbot 只在确有证书需要续期时才执行 pre/post hook，因此平时没有停机。
  if certbot renew --standalone --non-interactive \
      --pre-hook "docker stop ${NGINX_CONTAINER}" \
      --post-hook "docker start ${NGINX_CONTAINER}" \
      >>"$LOG_FILE" 2>&1; then
    renewed=1
    log "certbot renew finished ok"
  else
    log "ERROR: certbot renew failed (see $LOG_FILE and /var/log/letsencrypt/letsencrypt.log)"
  fi
  if ! nginx_running; then
    nginx_start
  fi
fi

# ── 同步到 nginx 挂载目录 ───────────────────────────────────
changed=0
for entry in "${MAP_LINES[@]}"; do
  set -- $entry
  lineage="$1"; sub="${2:-.}"
  src="/etc/letsencrypt/live/$lineage"
  dir="$(target_dir_for "$sub")"
  if [ ! -f "$src/fullchain.pem" ]; then
    log "WARN: lineage missing, skipped: $src"
    continue
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    log "dry-run: would sync $src -> $dir"
    continue
  fi
  mkdir -p "$dir"
  src_fp="$(openssl x509 -noout -fingerprint -sha256 -in "$src/fullchain.pem" 2>/dev/null | sed 's/.*=//')"
  dst_fp=""
  [ -f "$dir/fullchain.pem" ] && dst_fp="$(openssl x509 -noout -fingerprint -sha256 -in "$dir/fullchain.pem" 2>/dev/null | sed 's/.*=//')"
  if [ -n "$src_fp" ] && [ "$src_fp" = "$dst_fp" ]; then
    continue
  fi
  # 用 -L 解引用：certbot 的 live/*.pem 是符号链接，直接复制会留下悬空链接。
  cp -L "$src/fullchain.pem" "$dir/fullchain.pem"
  cp -L "$src/privkey.pem" "$dir/privkey.pem"
  chmod 644 "$dir/fullchain.pem"
  chmod 600 "$dir/privkey.pem"
  changed=$((changed + 1))
  log "synced $lineage -> $sub (fp ${src_fp:0:17}…)"
done

# ── 校验并 reload ──────────────────────────────────────────
if [ "$DRY_RUN" -eq 0 ]; then
  if ! nginx_running; then
    log "WARN: ${NGINX_CONTAINER} not running; starting before reload check"
    nginx_start
  fi
  if nginx_test; then
    nginx_reload && log "${NGINX_CONTAINER} reloaded"
  else
    log "ERROR: nginx -t failed after cert sync; NOT reloading"
    exit 1
  fi
fi

report_state "after"

# ── 判定是否仍有风险 ───────────────────────────────────────
now_epoch="$(date -u +%s)"
worst=999999
for entry in "${MAP_LINES[@]}"; do
  set -- $entry
  sub="${2:-.}"
  file="$(target_dir_for "$sub")/fullchain.pem"
  [ -f "$file" ] || continue
  end_date="$(openssl x509 -enddate -noout -in "$file" 2>/dev/null | sed 's/notAfter=//')"
  end_epoch="$(date -u -d "$end_date" +%s 2>/dev/null || echo 0)"
  days=$(( (end_epoch - now_epoch) / 86400 ))
  [ "$days" -lt "$worst" ] && worst="$days"
done

if [ "$worst" -lt 0 ]; then
  log "ERROR: at least one served certificate is EXPIRED (worst=$worst days)"
  exit 1
fi
if [ "$worst" -lt "$MIN_DAYS" ]; then
  log "ERROR: a served certificate expires within ${MIN_DAYS} days (worst=${worst} days)"
  exit 1
fi

log "done: synced=${changed} renewed=${renewed} worst_days_left=${worst}"
exit 0
