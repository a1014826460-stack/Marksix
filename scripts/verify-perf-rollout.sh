#!/usr/bin/env bash
# 性能改造上线核查（图片压缩 / 开奖面板 / nginx 边缘缓存 / 预测资料快照 / twsaimahui 合并）。
#
# 设计原则：只读、幂等、可在任意节点执行；每条检查打印 PASS / PENDING / FAIL。
#   - "PENDING" 表示该改动尚未部署到本节点（用于部署前试跑与部署后复验）。
#
# 用法：
#   sh scripts/verify-perf-rollout.sh --role backend      # 中心节点（python-api + redis）
#   sh scripts/verify-perf-rollout.sh --role frontend     # 前端节点（Next + nginx）
set -u

ROLE="backend"
while [ $# -gt 0 ]; do
  case "$1" in
    --role) ROLE="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

PASS=0; FAIL=0; PENDING=0; SKIP=0
pass()    { PASS=$((PASS + 1));    printf 'PASS     %s\n' "$1"; }
pending() { PENDING=$((PENDING + 1)); printf 'PENDING  %s\n' "$1"; }
fail()    { FAIL=$((FAIL + 1));    printf 'FAIL     %s\n' "$1"; }
skip()    { SKIP=$((SKIP + 1));    printf 'SKIP     %s\n' "$1"; }

# 每个节点只服务自己那批域名；非本节点域名会命中 default server 返回 301（169 字节），
# 必须跳过而不是判成失败。
served_domains=$(docker exec liuhecai-nginx nginx -T 2>/dev/null \
  | awk '/^[[:space:]]*server_name/ {for (i = 2; i <= NF; i++) {gsub(/;/, "", $i); print $i}}' | sort -u)
is_served() { printf '%s\n' "$served_domains" | grep -qx "$1"; }
# 所有"按 Host 头取本机样例"的检查都必须用本节点真正服务的域名，否则会命中 default
# server 的 301（169 字节重定向体），把未部署/异常判断搞错。
sample_domain=$(printf '%s\n' "$served_domains" | grep '^www\.' | head -1)
[ -n "$sample_domain" ] || sample_domain=$(printf '%s\n' "$served_domains" | head -1)
echo "节点服务域名：$(printf '%s ' $served_domains)"
echo "本节点样例域名：${sample_domain:-<未识别>}"

code() { # code <host> <path> [timeout]
  curl -sk -o /dev/null -m "${3:-15}" -w '%{http_code}' "https://127.0.0.1$2" -H "Host: $1"
}
bytes() { # bytes <host> <path>
  curl -sk -o /dev/null -m 30 -H 'Accept-Encoding: identity' -w '%{size_download}' "https://127.0.0.1$2" -H "Host: $1"
}
header() { # header <host> <path> <name>
  curl -sk -D - -o /dev/null -m 20 "https://127.0.0.1$2" -H "Host: $1" | tr -d '\r' | awk -v want="$3" 'BEGIN{IGNORECASE=1} index($0, want":")==1 {print $0; exit}'
}

echo "=== 1. 十站基础可达性（本机 nginx，按域名 Host 头；非本节点域名跳过）==="
for domain in www.tw8800.com www.twcaibawang.com www.twsaimahui.com www.twtongtian.com www.twcf888.com \
              www.twssz.com www.twbst528.com www.twjsz666.com www.twwanli.com www.twsyw.com; do
  if ! is_served "$domain"; then
    skip "$domain 不在本节点服务范围"
    continue
  fi
  root=$(code "$domain" "/")
  panel=$(code "$domain" "/vendor/shengshi8800/kj/local.html?lottery_type=3")
  draw=$(code "$domain" "/api/latest-draw?lottery_type=3")
  if [ "$root" = "200" ] && [ "$panel" = "200" ] && [ "$draw" = "200" ]; then
    pass "$domain / = $root, panel = $panel, latest-draw = $draw"
  else
    fail "$domain / = $root, panel = $panel, latest-draw = $draw"
  fi
done

echo
echo "=== 2. 开奖面板改造（并发取数 + 5 秒缓存去重）==="
panel_body=$(curl -sk -m 30 "https://127.0.0.1/vendor/shengshi8800/kj/local.html?lottery_type=3" -H "Host: $sample_domain")
if printf '%s' "$panel_body" | grep -q 'loadLatestDrawPayload'; then
  pass "面板含 loadLatestDrawPayload（缓存/去重层）"
else
  pending "面板不含 loadLatestDrawPayload（改动未部署）"
fi
if printf '%s' "$panel_body" | grep -qE 'load\(\{ revealOnLoad: true \}\);'; then
  pass "面板初始化并发发起 load()"
else
  pending "面板初始化仍是串行（改动未部署）"
fi

echo
echo "=== 3. 图片体积与缓存策略 ==="
if is_served www.twssz.com; then
  twssz_html=$(bytes www.twssz.com "/vendor/twssz/index.html")
  if [ "$twssz_html" -lt 512000 ]; then
    pass "twssz index.html = ${twssz_html} B（< 500 KB，内联 base64 已外置）"
  else
    pending "twssz index.html = ${twssz_html} B（≈1.16 MB 表示改动未部署）"
  fi
else
  skip "twssz 不在本节点服务范围（换到前端节点执行）"
fi
for probe in "www.twcaibawang.com /vendor/twcaibawang.com/static/picture/42ce9a26360f319a1e46203fda6a5e68.webp" \
             "www.twjinniu.com /vendor/twjinniu/static/file/kingsjpz_1051_502_0231.webp" \
             "www.twbst528.com /vendor/twbst528/static/picture/3089.80.webp"; do
  set -- $probe
  if ! is_served "$1"; then
    skip "$1 $(basename "$2") 不在本节点服务范围"
    continue
  fi
  size=$(bytes "$1" "$2")
  if [ "$size" -gt 0 ] && [ "$size" -lt 409600 ]; then
    pass "$1 $(basename "$2") = ${size} B（< 400 KB 且为 WebP 素材）"
    asset_header=$(header "$1" "$2" "cache-control")
    case "$asset_header" in
      *immutable*) pass "$1 静态资源长缓存：$asset_header" ;;
      *) fail "$1 静态资源缓存头异常：${asset_header:-<缺失>}" ;;
    esac
  elif [ "$size" = "0" ]; then
    pending "$1 $(basename "$2") 不存在（图片改动未部署）"
  else
    fail "$1 $(basename "$2") = ${size} B（超过 400 KB）"
  fi
done

echo
echo "=== 4. nginx 边缘缓存（本节点，样例域名 $sample_domain）==="
first=$(code "$sample_domain" "/api/next-draw-deadline?lottery_type=3")
status=$(curl -sk -D - -o /dev/null -m 20 "https://127.0.0.1/api/next-draw-deadline?lottery_type=3" -H "Host: $sample_domain" | tr -d '\r' | awk 'BEGIN{IGNORECASE=1} /^x-cache-status:/ {print $2}')
if [ "$first" = "200" ] && [ -n "$status" ]; then
  pass "X-Cache-Status 可见（最近一次 = $status）"
else
  pending "无 X-Cache-Status（边缘缓存未部署，HTTP $first）"
fi
if docker exec liuhecai-nginx sh -c 'test -s /var/log/nginx/kj_cache.log' 2>/dev/null; then
  pass "缓存日志存在：$(docker exec liuhecai-nginx sh -c 'wc -l < /var/log/nginx/kj_cache.log' | tr -d ' ') 行"
else
  pending "无 kj_cache.log（缓存日志未部署）"
fi

if [ "$ROLE" = "backend" ]; then
  echo
  echo "=== 5. 预测资料快照（中心节点 python-api）==="
  first=$(curl -s -o /dev/null -m 30 -w '%{time_total}' "http://127.0.0.1:8000/api/legacy/module-rows?modes_id=56&limit=8&web=9&type=3")
  second=$(curl -s -o /dev/null -m 30 -w '%{time_total}' "http://127.0.0.1:8000/api/legacy/module-rows?modes_id=56&limit=8&web=9&type=3")
  echo "         module-rows 第一次 ${first}s / 第二次 ${second}s"
  if awk -v value="$second" 'BEGIN{exit !(value < 0.05)}'; then
    pass "第二次（快照命中）< 50 ms"
  else
    pending "第二次 ${second}s（快照未部署或未命中）"
  fi
  if docker logs liuhecai-python-api --since 30m 2>&1 | grep -q 'prediction snapshot'; then
    pass "日志含 prediction snapshot hit/miss 记录"
  else
    pending "日志无 prediction snapshot（未部署）"
  fi
  keys=$(docker exec liuhecai-redis redis-cli --scan --pattern 'public:prediction-snapshot:*' 2>/dev/null | wc -l | tr -d ' ')
  if [ "$keys" -gt 0 ]; then
    pass "Redis 快照/代际键 = $keys"
  else
    pending "Redis 无预测快照键"
  fi
  if docker exec liuhecai-redis redis-cli --scan --pattern 'public:prediction-snapshot:*generation*' 2>/dev/null | grep -q generation; then
    pass "代际计数键存在（失效触发已生效）"
  else
    pending "无代际计数键（失效触发未部署或尚未触发）"
  fi
fi

if [ "$ROLE" = "frontend" ]; then
  echo
  echo "=== 6. Next 进程内缓存（前端节点）==="
  if docker exec liuhecai-frontend sh -c 'grep -rl "upstream-cache\|LOTTERY_UPSTREAM_CACHE" /app/.next 2>/dev/null | head -1' | grep -q .; then
    pass "构建产物含 upstream cache 标记"
  else
    pending "构建产物无 upstream cache 标记（未部署）"
  fi
  echo
  echo "=== 7. twsaimahui 脚本合并（仓库/服务端副本）==="
  if is_served www.twsaimahui.com; then
    index=$(curl -sk -m 30 "https://127.0.0.1/vendor/twsaimahui/index.html" -H "Host: www.twsaimahui.com")
    source_label="服务端返回"
  else
    index=$(cat frontend/public/vendor/twsaimahui/index.html 2>/dev/null)
    source_label="本节点仓库文件（twsaimahui 由中心节点服务）"
  fi
  bundles=$(printf '%s' "$index" | grep -o 'static/js/bundle-[0-9a-f]\{16\}\.js' | sort -u | wc -l | tr -d ' ')
  modules=$(printf '%s' "$index" | grep -o 'static/js/0[0-9][0-9][A-Za-z0-9_]*\.js' | wc -l | tr -d ' ')
  if [ "$bundles" -ge 2 ]; then
    pass "$source_label 含 $bundles 个 bundle 标签"
  else
    pending "$source_label 无 bundle 标签（未部署）"
  fi
  echo "         （供参考）仍出现模块脚本引用 $modules 处；合并后这些应全部位于注释中"
fi

echo
echo "=== 8. 容器资源 ==="
docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' | grep -E 'liuhecai-(frontend|python-api|nginx|scheduler-worker)' || true

echo
echo "=== 汇总：PASS=$PASS PENDING=$PENDING SKIP=$SKIP FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ]
