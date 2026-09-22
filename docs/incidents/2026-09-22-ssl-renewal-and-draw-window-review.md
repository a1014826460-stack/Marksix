# 证书自动续期整改 + 2026-09-22 开奖窗口复查

时间：2026-09-22（Asia/Hong_Kong）
范围：中心节点 `207.56.3.82:29618`、前端节点 `207.56.2.71:62594`。均为**只读检查 + 已授权的修复/安装**。

## 一、十个站点证书现状与三个真问题

### 1.1 检查结果（改动前）

| 站点 | nginx 加载的证书 | 到期 | 状态 |
| --- | --- | --- | --- |
| www.tw8800.com | `deploy/ssl/fullchain.pem` | 2026-12-03 | 正常 |
| www.twsaimahui.com | 同上（同一张 SAN） | 2026-12-03 | 正常 |
| www.twcaibawang.com | 同上 | 2026-12-03 | 正常 |
| www.twcf888.com | 同上 | 2026-12-03 | 正常 |
| **www.twtongtian.com** | `deploy/ssl/twtongtian/fullchain.pem` | **2026-09-03** | **已过期 19 天** |
| www.twbst528.com | `deploy/ssl/twbst528/` | 2026-10-30 | 正常（38 天） |
| www.twjsz666.com | `deploy/ssl/twjsz666/` | 2026-10-30 | 正常（38 天） |
| www.twssz.com | `deploy/ssl/twssz/` | 2026-10-25 | 正常（32 天，最早到期） |
| www.twsyw.com | `deploy/ssl/twsyw/` | 2026-10-30 | 正常 |
| www.twwanli.com | `deploy/ssl/twwanli/` | 2026-10-30 | 正常 |

（前端节点另有 `monster-domains` 一张，2026-10-28，非本次十个站点。）

### 1.2 问题 1：`www.twtongtian.com` 线上证书已过期 19 天

- nginx 实际挂载的是 `<repo>/deploy/ssl`，而 certbot 只更新 `/etc/letsencrypt/live/**`；
  两者之间**靠人工 `cp`**。
- `/etc/letsencrypt/live/www.twtongtian.com/fullchain.pem` 早已是 **2026-12-03** 的新证书
  （证书目录 mtime 09-04 15:18），但 `deploy/ssl/twtongtian/` 里仍是 08-03 复制的旧文件
  （到期 09-03）→ 线上一直发过期证书。
- 旁证：同一次续期里 `deploy/ssl/fullchain.pem` 在 09-04 15:20 被复制过（tw8800 系列四个域名因此正常），
  只是漏了 `twtongtian/` 这一个目录。

**处置**：已把新证书 `cp -L` 同步进 `deploy/ssl/twtongtian/`（必须用 `-L` 解引用，certbot 的
`live/*.pem` 是相对符号链接，直接复制会留下悬空链接），`nginx -t` 通过后 reload。
现在 `https://www.twtongtian.com/health` 在不加 `-k` 的情况下返回 **200**。

### 1.3 问题 2：中心节点 certbot 的续期**全部失败**

```
# certbot renew --dry-run
Failed to renew certificate www.twtongtian.com with error: Could not bind TCP port 80
because it is already in use by another process ... 3 renew failure(s)
```

`/etc/letsencrypt/renewal/*.conf` 里三张证书都是 `authenticator = standalone`，而 80 端口
被 nginx 容器长期占用 → 每次定时续期都失败，只是失败信息只落在
`/var/log/letsencrypt/letsencrypt.log`，没有任何通知。**12-03 到期时会重演 twtongtian 的结果。**

### 1.4 问题 3：前端节点 certbot 的续期**也全部失败**

5 张证书配置为 `authenticator = webroot`，`webroot_path = /root/Marksix/deploy/certbot-webroot`，
nginx 里也确实有 `location ^~ /.well-known/acme-challenge/ { root /var/www/certbot; }`，
但 **nginx 容器只挂载了 `deploy/nginx.frontend-node.conf.local` 与 `deploy/ssl`**，
`/var/www/certbot` 在容器内是空的默认目录 → 校验必然 404。另外 `twssz.com` 用的是 `standalone`，
同样撞 80 端口。dry-run 结果：`6 renew failure(s)`。

## 二、整改：自动续期 + 同步 + 校验 + 定时

新增 `scripts/sync-nginx-certs.sh`：

1. **续期**：`certbot renew --standalone`，并用 `--pre-hook`/`--post-hook` 仅在**确有证书需要
   续期时**短暂 `docker stop/start liuhecai-nginx`，从而绕开 80 端口占用，且**不改动线上 nginx 配置**。
2. **同步**：把每个 lineage 的 `fullchain.pem`/`privkey.pem` 用 `cp -L` 写入
   `deploy/ssl/<子目录>`（映射见 `deploy/ssl-sync.map`，每台机器不同、已加入 `.gitignore`），
   权限 644/600。
3. **生效**：`nginx -t` 通过后 `nginx -s reload`；`nginx -t` 失败则不 reload 并以退出码 1 结束。
4. **校验**：逐张打印剩余天数；任一张已过期或低于 `--min-days`（默认 14）→ 退出码 1。
5. 全流程写入 `/var/log/liuhecai-ssl-sync.log`。

`deploy/systemd/liuhecai-ssl-sync.{service,timer}`：每天 **04:20 Asia/Hong_Kong** 执行
（两台服务器系统时区是 UTC，因此 OnCalendar 显式带时区；否则会落在 12:20 北京，与
`daily_prediction` 12:00 撞车），`Persistent=true` 支持开机补跑。两台机器均已 `enable --now`。

## 三、整改过程中发生的一次生产事故（已恢复）

**15:27 UTC 前端节点 5 个站点中断约 10 分钟。**

- 原因：脚本初版用 `docker compose` 做 stop/up/reload，`LIUHECAI_COMPOSE_FILE` 默认
  `docker-compose.yml`。手工首次执行时没有传该变量，于是在**前端节点**上使用了**中心节点的**
  compose 文件；两台机器仓库目录同名（`Marksix`），compose 项目名都是 `marksix`，
  compose 因此把本机真实的 `liuhecai-nginx` / `liuhecai-frontend` **以同名容器替换**，
  并顺着 nginx 的依赖链创建了 `python-api`、`backend-admin`、`postgres`、`pgbouncer`、
  `redis`、`db-migrate`。
- 恢复（15:36 UTC 前后）：按名字 `docker rm -f` 删掉这 8 个误建容器（**未删除任何数据卷**），
  再 `docker compose -f docker-compose.frontend-node.yml up -d` 重建 `frontend` + `nginx`。
  5 个站点 `/health`、`/history`、`/api/latest-draw` 全部恢复 **200**，证书保持正常。
- 结构性修复：脚本**完全不再调用 docker compose**，只对 nginx 容器本身执行
  `docker stop/start` 与 `docker exec ... nginx -t/-s reload`；新增前置检查，容器不存在直接
  退出码 2。改完后再次执行（`--skip-renew`）验证：容器集合完全不变（前端节点始终只有
  `liuhecai-nginx` + `liuhecai-frontend`）。

## 四、2026-09-22 开奖窗口复查（20:30-22:40 北京）

### 4.1 正常的两个彩种

| 彩种 | 期号 | 计划 | 入库 | 开盘 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 澳门彩 | 265 | 21:32 | 21:34:43 | `auto_open opened=1 public_open_delay_seconds=132` | 正常（历史常态区间 110~190s） |
| 台湾彩 | 265 | 22:32 | — | `is_opened=1` 于 22:32:13 | 正常（持久化任务 +13s） |

并发验证了本次修复生效：

- `13:33:39 Auto-crawl 澳门彩: refreshed an already-published draw (2026264), no re-open and no auto_open audit`
  → 已发布期不再被回退/重复开盘，也不再产生 `public_open_delay_seconds≈86400` 的假审计；
- 澳门彩的入库发生在 13:34:43，**没有出现 5 分钟抓取空窗**；`backfill_after_draw:1:2026103`
  的回填任务精确按 +8.0 分钟排程。

### 4.2 异常的香港彩：上游故障，我方行为正确

- 13:28:32 起 `www.lnlllt.com` 与 `api.csjid.com` 双双返回 **HTTP 200 但内容不可用**
  （日志 `Expecting value: line 1 column 1 (char 0)`）。
- 现场复现（事后 15:0x UTC 直接 curl 两个源）：
  - `www.lnlllt.com` 返回的 JSON 结构与期号体系异常：`{"issue":11358158,"result":"8,6,2",
    "open_time":"2026-09-22 23:03:46","display_issue":113…}` —— `result` 只有 **3 个号码**；
  - `api.csjid.com` 返回 **HTTP 401**：`{"errorCode":401,"message":"apiKey 无效，请检查是否填写
    正确…"}` → **备用源的 apiKey 已失效**。
- 影响：香港彩 103 期数据 21:38:00 才入库（比计划 21:30 晚约 480s，`draw_time` 21:37:20）。
- 我方表现正确：追赶模式生效后每 ~10s 轮询一次（13:33:49/13:34:19/13:35:00/13:35:20…），
  没有 5 分钟盲区；按新基线（香港彩 grace=199s）在 13:34:19 判 `level=yellow`、
  13:36:29 判 `level=orange`；13:38:00 恢复并自动发出恢复通知。
- **需要你处理**：`api.csjid.com` 的 apiKey 必须更新（`DRAW_HK_BACKUP_COLLECT_URL` /
  `draw.hk_backup_collect_url`，以及澳门彩同名变量），否则香港彩/澳门彩在主的源异常时没有可用备用源。

### 4.3 本次复查发现的缺陷（已修复并部署）

三个彩种里**只有香港彩**排到了开奖后预测结果回填：

- 澳门彩 265 由 `_process_auto_crawl_batch` 开盘 —— 该路径从不调用
  `_schedule_backfill_after_draw`；
- 台湾彩 265 被 60 秒兜底轮询 `_auto_open_draws` 先开盘（`14:32:13.552 AutoOpen: Set is_opened=1`），
  随后 `taiwan_precise_open` 任务拿到 `opened_count=0`，`if opened_count > 0` 的分支跳过了排程；
- 结果这两期的预测结果回填要等到次日 12:00 的 `daily_prediction`。

修复：两条路径都在确实开盘后调用 `_schedule_backfill_after_draw`（任务 key 按期号
`backfill_after_draw:<彩种>:<YYYY###>`，幂等）。

### 4.4 今晚实际发出的告警邮件（4 封，新模板已生效）

```
13:12:31  [六合彩报警] 香港彩爬虫连续失败 3 次
13:32:05  [六合彩报警] 香港彩开奖期号不匹配
13:34:20  [production][提示] 开奖数据滞后 · 香港彩 · 超计划 4分19秒（期号 2026102）
13:38:01  [production][已恢复] 开奖数据滞后已恢复 · 香港彩
```

澳门彩（132s，基线 483s）与台湾彩（13s，基线 120s）**均未告警** —— 误报消除达到预期。

## 五、当前状态

| 项 | 中心节点 | 前端节点 |
| --- | --- | --- |
| HEAD | `8e5f9f1`（= origin/main） | `8e5f9f1` |
| 工作树 | 无 tracked 改动 | 无 tracked 改动 |
| 证书定时任务 | active，下次 04:20 北京 | active，下次 04:23 北京 |
| 5 站严格 HTTPS | 全部 200 | 全部 200 |
| 证书到期 | 2026-12-03 | 2026-10-25 / 10-30 |

**遗留待办**

1. 更新 `api.csjid.com` 的 apiKey（否则香港彩/澳门彩无可用备用源）。
2. 香港彩主源 `www.lnlltt.com` 的返回结构异常（`issue` 变成 8 位、`result` 只有 3 个号码），
   需观察是否为源站临时状态；若持续，需要评估是否更换或被限流。
3. 可选加固：把前端节点的 webroot 目录挂进 nginx 容器
   （`./deploy/certbot-webroot:/var/www/certbot`）并给中心节点也加上，
   即可在不停机的前提下完成校验；当前脚本用“必要时短暂停 nginx”已能工作。
