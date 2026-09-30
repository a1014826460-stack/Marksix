# twsyw jQuery 隐藏脚本加载器清理与来源追踪

检查及本地修复日期：2026-09-30（UTC+8）。基线提交：`2fa5c1620842a84d2ecffaa0381fea1f32905432`。

## 结论

`frontend/public/vendor/twsyw/static/js/jquery.js` 尾部夹带了一段混淆的外部脚本加载器。公开页面的浏览器抓包以及隔离浏览器回归测试均确认，它会加载 `https://www.cnzz-api.com/?id=G-E5C9V5Z3W2`。

Git 记录显示该代码随供应商模板导入仓库，早于本次发现；这不是认定“最近服务器被入侵”的证据。提交署名只能说明哪个提交导入了文件，不能证明提交者编写或有意植入了加载器。用户随后报告在真实 Android 夸克浏览器上复现跳转；目前未取得该现场的完整跳转链及对应外部脚本响应，不能最终确认具体跳转由该加载器造成。

本地阶段先完成清理与验证。用户随后明确授权中心和前端服务器的全部修复操作范围，本轮已完成两节点发布和线上验证，结果见下文“发布结果”。

后续用户反馈：在 Android 夸克浏览器、Wi-Fi 网络上实际复现首次访问跳转，之后及换浏览器均未再触发。此反馈应视为已发生的访客异常，不能用当前检查网络未复现予以否定。加载器自身在电脑和移动浏览器均执行；跨浏览器的次数限制可能还有外部服务按 IP/设备/时间筛选，但尚未取得对应响应及完整跳转链，不能把该推测当作已验证根因。追加的两个中文移动新会话（Chrome 与微信 WebView UA）仍取得该外部服务的空正文。

用户随后明确授权中心服务器和前端服务器本轮修复的全部操作范围。部署前只读核对确认，两节点均运行基线 `2fa5c16`，宿主库的污染文件哈希与上述 Git 文件一致；Nginx 均挂载 `/root/Marksix/frontend/public` 为 `/srv/public`。中心已有三张运行期图片改动，前端没有已跟踪文件改动；部署应保留这些文件。本报告的“本地验证”是发布前阶段记录，发布结果将在完成后追加。

## 已完成的清理

- 使用 [jQuery 官方 CDN 的 1.10.2 文件](https://code.jquery.com/jquery-1.10.2.min.js) 完整替换本地 `jquery.js`，保留原版本以控制兼容性风险。替换前正常库代码与官方文件一致，差异来自尾部附加加载器。
- 修改 twsyw 首页及 `20281.html`—`20332.html`，共 53 个页面的脚本引用为 `static/js/jquery.js?v=0ba081f54608`。现有 Next.js 配置对 `/vendor/:siteKey/static/:path*` 使用一年 `immutable` 缓存，更新请求 URL 可避免浏览器直接复用原 URL 的污染文件。
- 新增 `frontend/test/twsyw-jquery-security-contract.py`，在非 localhost 的隔离 HTTPS 测试域名上执行真实浏览器，覆盖电脑和安卓模拟浏览器及空、`1`、`2` 三种 `tool` Cookie 状态。全部请求在测试内拦截，不向加载器的外部服务发送流量。

官方文件：93,107 字节。SHA-256：

```text
0ba081f546084bd5097aa8a73c75931d5aa1fc4d6e846e53c21f98e6a1509988
```

替换前 Git 文件：96,103 字节。SHA-256：

```text
8fa0540aa480f9a218e241d36ecbf715e9dd3c47d6f4da186548b99c626e7544
```

## 加载器行为

尾部以 `;eval(function(p,a,c,k,e,r)...` 开始；静态解包可读出：

1. 读取 `tool` Cookie；仅在其不存在或值小于 `2` 时运行，递增计数并设置次日零点过期。
2. 排除 `localhost` 与代码拼接得到的 `127.0.0.0`，按浏览器类型选择加载分支。不能只在 localhost 或重复访问环境中检查它。
3. 将十六进制数组还原为 `www.cnzz-api.com`，组合出 `?id=G-E5C9V5Z3W2`。
4. 常见浏览器通过隐藏图片的 `onerror` 创建 `script`；另一分支通过隐藏 iframe 写入 `script`。

外部服务可据此下发与站点同文档执行的代码。首次公开网页检查时该服务返回 HTTP 200、空正文，未复现指定目标域名的跳转。

## 何时进入模板

下表时间来自本地 Git 提交记录，均为 UTC+8；不是供应商上游文件的创建时间。

| 时间 | 提交 | 路径与证据 |
| --- | --- | --- |
| 2026-05-06 22:48:32 | `a39eafa162d581fe8ba46d8e3c604dc7425325f4` | `frontend/public/vendor/shengshi8800/static/js/jquery.js` 已入库；不存在附加加载器。忽略 UTF-8 BOM 后与官方文件一致。 |
| 2026-08-01 20:28:54 | `47e199f7d2dcf71953d21e337798ee051dd7c082` | 新增 `frontend/public/vendor/Zz_felwi.am55689.com/static/js/jquery.js`，已经包含加载器；父提交没有该路径。这是沿文件历史找到的首次污染模板导入。Git 署名为 `a1014826460-stack`，提交消息为 `2333`。 |
| 2026-08-02 01:56:23 | `2b00ab774deb6b2aa9ca5baa706a5ef9a8f58145` | 新增 `frontend/public/vendor/twsyw/static/js/jquery.js`，父提交没有该路径。忽略 BOM/换行差异后，与上面的污染模板相同；文件字节与本轮修复前 HEAD 一致。Git 署名为 `a1014826460-stack`，消息为 `feat(twsyw): add pmtj_image and brainteaser modules`。 |

复查命令（只读取本地 Git 对象）：

```powershell
git log --follow --name-status --format='%H %aI %cI %an %s' -- frontend/public/vendor/twsyw/static/js/jquery.js
git show 47e199f:frontend/public/vendor/Zz_felwi.am55689.com/static/js/jquery.js
git show 2b00ab7:frontend/public/vendor/twsyw/static/js/jquery.js
```

因此，可定位到“8 月 1 日导入的供应商模板中已经夹带，8 月 2 日进入 twsyw”；无法从这些记录进一步确定供应商最初何时加入、谁实际编写、外部服务何时下发过何种内容。

## 本地验证结果

- 安全回归测试：替换前失败，明确记录外部脚本请求和 `tool` Cookie 变更；替换后 6 个浏览器场景通过。
- 官方 SHA-256 校验、JS 语法检查、53 个 HTML 的最小差异检查及未版本化引用扫描通过。53 个页面除资源版本参数外没有变化。
- `twsyw-legacy-script-contract.mjs`、`twsyw-adapter-contract.mjs`、`twsyw-site-registration-contract.mjs` 通过。
- `pnpm test:display-contracts` 全部通过。
- 本地展示审计：545 行，`error=0`、`js_errors=0`、`warn=10`。警告来自通用数据展示规则，未改预测数据或展示逻辑。
- 后端 `python -m pytest -q`：1,171 通过、13 跳过、2 失败。不能把全量后端验收标记为通过。失败为：
  - `tests/integration/test_versioned_migrations.py::test_postgres_scheduler_task_is_exclusively_acquired_and_recovers_after_lock_timeout`：本地测试数据库已有较早的到期调度任务，取任务结果多于测试预期。
  - `tests/unit/test_ha_runtime_config_contract.py::test_nginx_exposes_exact_liveness_and_readiness_proxies`：当前 Nginx 配置不含测试预期的 `proxy_pass http://python-api:8000/health/live;` 字面值。
  - 两者不涉及本轮修改的静态库或 HTML；本轮未修改后端源码、测试或 Nginx 配置，也未清理共享数据库。

```powershell
python frontend/test/twsyw-jquery-security-contract.py
node --check frontend/public/vendor/twsyw/static/js/jquery.js
node frontend/test/twsyw-legacy-script-contract.mjs
node frontend/test/twsyw-adapter-contract.mjs
node frontend/test/twsyw-site-registration-contract.mjs
pnpm test:display-contracts
python scripts/audit-prediction-display.py twsyw --base-url http://127.0.0.1:3000 --json <本地输出路径>
# 在 backend/src 目录：
python -m pytest -q
```

## 发布结果

代码发布提交：`f88470f7b3e290e1651d532e44104e7bb32c7be1`。备份时间戳：`20260930T100414Z`（UTC+8 为 18:04:14）。

- 中心 `207.56.3.82:29618` 与前端 `207.56.2.71:62594` 均经既有 SSH 跳板访问，先备份，再按中心、前端顺序 `git fetch` 与 `git merge --ff-only` 到该提交。
- 两节点备份均为 `/root/Marksix/.deploy-backups/twsyw-jquery-20260930T100414Z`，含原 HEAD、工作区补丁、未跟踪文件清单、配置、`.env`、原 twsyw 静态目录压缩包及原前端镜像 ID；目录权限为 `700`。原镜像还保留 `liuhecai-frontend:before-twsyw-20260930T100414Z` 标签。
- 此次只重建及替换 `frontend`，使用 `up -d --no-deps frontend`，未运行数据库迁移，未重启数据库、Python API、调度服务或 Nginx。中心原有三张运行期图片的修改和两节点原有未跟踪文件保留。
- 两节点前端均为 `healthy`，两节点 `nginx -t` 通过；宿主和容器 `/app/public/vendor/twsyw/static/js/jquery.js` 均匹配上述官方 SHA-256。
- 公网首页内嵌 HTML 已引用 `jquery.js?v=0ba081f54608`；新旧脚本 URL 均 HTTP 200 且正文与官方文件一致。新 URL 使用一年 immutable 缓存，内嵌 HTML 为 `max-age=0, must-revalidate`。本次观测路径无需额外清缓存服务操作。
- 发布后的全新 Android 模拟会话和电脑会话中，所有脚本均来自 `www.twsyw.com`，`cnzz-api.com` 与 `56313599.top` 请求为 0，`tool` Cookie 为 0，页面 JS 错误为 0，最终地址保持在本站。此为 Chromium 模拟移动测试，不是用户真实夸克及 Wi-Fi 网络的同环境复现。
- 十站首页均 HTTP 200。线上完整展示审计共 3,765 行，全部 `error=0`、`js_errors=0`，30 个数据展示警告；其中 twsyw 为 545 行、8 个警告。

前端新镜像：中心 `sha256:e04e49c8016ba74c646b6a1f416599d345365def4bc41ac3843cf9ebae99ffac`；前端节点 `sha256:ec813fe38a7092755bda2c22af05a249c051f06164fc1364f2772fb177f4e16d`。

线上审计、公开资源校验及节点检查记录保存在本机 `C:/Users/Administrator/AppData/Local/Temp/twsyw-check-20260930/` 下：`audit-online-after.json`、`public-static-after-sync.json`、`public-browser-after-build.json`、`final-server-check.json` 等。

## 仍需区分的事项

已清除并验证了这个隐藏外部脚本加载入口；仅凭未观察到再次跳转，不能最终解释外部服务之前如何按访客条件分发。夸克如仍打开旧标签或保存旧页面，可清除该站点缓存并重新打开，再比较 Wi-Fi 和移动数据环境。

后端全量测试的两项失败仍保留在“本地验证结果”中，未通过修改无关测试或清理共享数据库掩盖。本次只发布了静态文件修复；不代表站点所有依赖完成全面安全审计，也不包含 jQuery 大版本升级。
