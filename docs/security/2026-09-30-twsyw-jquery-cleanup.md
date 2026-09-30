# twsyw jQuery 隐藏脚本加载器清理与来源追踪

检查及本地修复日期：2026-09-30（UTC+8）。基线提交：`2fa5c1620842a84d2ecffaa0381fea1f32905432`。

## 结论

`frontend/public/vendor/twsyw/static/js/jquery.js` 尾部夹带了一段混淆的外部脚本加载器。公开页面的浏览器抓包以及隔离浏览器回归测试均确认，它会加载 `https://www.cnzz-api.com/?id=G-E5C9V5Z3W2`。

Git 记录显示该代码随供应商模板导入仓库，早于本次发现；这不是认定“最近服务器被入侵”的证据。提交署名只能说明哪个提交导入了文件，不能证明提交者编写或有意植入了加载器。也没有足够证据确认它已把访客导向 `https://vvv.56313599.top/`。

本轮完成本地清理与验证，没有发布、登录服务器或执行线上审计。因此线上是否已清除，需待获授权发布后确认。

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

## 发布时仍需确认

按项目 AGENTS.md，服务器操作需要用户在当次消息中明确指定服务器及操作。本轮未取得发布授权。

获授权发布后，应检查新 HTML 使用带版本参数的请求 URL、新库与上述官方校验值一致，并在无 `tool` Cookie 的新会话中确认不再出现 `cnzz-api.com` 请求。若 CDN 忽略查询参数作为缓存键，需要额外清除旧资源缓存；随后执行项目要求的线上展示审计。不要据本地测试宣称线上风险已解除。
