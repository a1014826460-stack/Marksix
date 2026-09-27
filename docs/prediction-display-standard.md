# 预测模块展示规范与例行检查工作流

适用：本站全部 10 个前台站点（`web_id` 4–13）的所有预测模块。
目的：把「判定正确显示准/对、错误显示错、未开奖不显示判定；命中的生肖/号码/段数/文字黄色高亮，
未命中一律不高亮；静态文本与分组说明正常显示」固化成可自动检查的规则，避免同类缺陷反复出现。

---

## 一、展示规范（硬性规则）

| 编号 | 规则 | 说明 |
| --- | --- | --- |
| **S1** | 判定文字只允许三种状态 | 命中 → `准`（或 `对`，同一站点内保持一致）；未命中 → `错`；**未开奖 → 不显示任何判定文字** |
| **S2** | 只有命中才高亮 | 命中项的生肖 / 号码 / 段位 / 五行 / 头尾 / 波色 / 天地肖 / 文字映射加 `background-color: #FFFF00` |
| **S3** | 未命中绝不保留高亮 | 判定为「错」的那一期，整行（整期）不得出现任何 `#FFFF00`。**不能沿用供应商静态 HTML 里的高亮** |
| **S4** | 逐期独立判定 | 一行里拼了多期（如 `270期…错269期…错`）时，必须按期分别判定与高亮，不能整行共用一个状态 |
| **S5** | 不外泄原始数据 | 页面可见文本不得出现 `["`、`"]`、`\`、JSON 花括号或未解析的 `标签\|值` 原始串 |
| **S6** | 静态文本正常显示 | 分组说明（左肖/右肖、阴肖/阳肖、文肖/武肖、有肖/无肖、吉美/凶丑、肥肖/瘦肖、胆大/胆小…）**两组都要显示**，不能只显示本期恰好抽到的那一组 |
| **S7** | 展示值不得长期重复 | 同一模块相邻 **3 期以上**展示值完全相同即为异常（二选一模块最容易出现） |
| **S8** | 页面无 JS 报错 | 任何 `pageerror` 都视为缺陷（会连带整块模块不渲染） |

判定口径与后端机制一致性以 `backend/docs/prediction-module-rules.md` 为准；
生成的唯一性规则见 `backend/src/prediction_generation/diversity.py`。

---

## 二、自动审计工具

脚本：`scripts/audit-prediction-display.py`（Python + Playwright，chromium 路径已内置）。

```powershell
# 全站审计（约 10–15 分钟），输出 md + json 报告，退出码 1 表示有 error
python scripts\audit-prediction-display.py --json .codex-temp\audit-all.json

# 单站点
python scripts\audit-prediction-display.py twsaimahui --json .codex-temp\audit-tsam.json

# 发布前本地预检：把线上域名换成本地 next dev
python scripts\audit-prediction-display.py twsaimahui --base-url http://127.0.0.1:3000 --json .codex-temp\audit-local.json
```

报告里的检查项与上面的规范一一对应：

| 规则 | 字段 | 级别 | 含义 |
| --- | --- | --- | --- |
| R1 | `raw_json_leak` | error | 可见文本残留原始 JSON 片段（S5） |
| R2 | `verdict_pending` | error（占位+命中）/ warn（占位+未命中） | 未开奖却给判定（S1） |
| R3 | `highlight_miss` | error | 判定「错」但仍有一处黄色高亮（S3） |
| R4 | `highlight_hit` | warn | 命中却没有高亮（S2/S4） |
| R5 | `repeat_run` | warn | 连续 ≥3 期展示值相同（S7） |
| R6 | `empty_legend` | error | 分组说明后面为空（S6） |

**验收门槛：`error=0` 且 `js_errors=0`。** warn 需要人工判断，但数量不得比上一轮增加。

---

## 三、例行检查工作流（每次改动后 / 每次上线前）

1. **本地改代码** → 启动本地服务：
   ```powershell
   # 后端
   $env:LIUHECAI_RUNTIME_ENV='development'
   python backend\src\app.py --host 127.0.0.1 --port 8000 --db-path "postgresql://postgres:***@127.0.0.1:5432/liuhecai"
   # 前端
   cd frontend; node node_modules\next\dist\bin\next dev --webpack --hostname 127.0.0.1 --port 3000
   ```
2. **本地预检**：`python scripts\audit-prediction-display.py <site> --base-url http://127.0.0.1:3000`
   确认 `error=0` 后再提交。
3. **提交并推送**：`git push origin main`（需要用户当次授权；授权不跨轮次继承）。
4. **发布**（见 `DEPLOY.md`「部署工作流（含跳板机）」）：先中心节点、后前端节点；
   两个节点都用 `git merge --ff-only`，失败即停。
5. **线上审计**：`python scripts\audit-prediction-display.py --json .codex-temp\audit-live.json`，
   要求 `error=0`；把报告归档到 `docs/vendor-sites/<site>-*.md` 或 DEPLOY.md 的发布记录里。
6. **回归**：`cd backend/src; python -m pytest -q`；
   `node frontend/test/<站点契约>.mjs`。

---

## 四、新站点接入 checklist

1. **站点注册**：`frontend/sites/<siteKey>/site.manifest.ts` 填 `domains` / `routePath` / `webId` / `siteId`；
   `backend/src/domains/prediction/site_page_dependencies.py` 登记页面依赖（脚本 → endpoint → mode_id）。
2. **模块授权**：`public.site_prediction_modules` 只授权页面**实际启用**的模块；
   用 `python backend/scripts/reconcile_site_prediction_modules.py` 审计后再 `--apply`。
3. **渲染方式判定**（决定改哪里）：
   | 形态 | 判断方法 | 改动位置 |
   | --- | --- | --- |
   | legacy 单页 + 独立 JS | `frontend/public/vendor/<site>/static/js/*.js` 调 `/api/kaijiang/*` | 直接改该 JS |
   | legacy + bundle | 目录里有 `bundles.json` / `bundle-<hash>.js` | **改源 JS 后必须重建 bundle**（见下） |
   | legacy + iframe | 首页只有 `<iframe src="/vendor/<site>/index.html">` | 审计/预检要打开 iframe 地址 |
   | React 组件 | `frontend/components/<site>/*.tsx` | 改 TSX，跑 `npx tsc --noEmit` |
4. **bundle 站点重建**（文件名是内容哈希 + 长缓存，**必须改名**才能击穿缓存）：
   ```powershell
   python scripts\bundle-twsaimahui-modules.py --rebuild --apply
   ```
   其他 bundle 站点同理，用各自的 bundle 脚本。
5. **首轮审计**：`python scripts\audit-prediction-display.py <site>` → 把 error 清零。
6. **判定口径**：在 `backend/docs/prediction-module-rules.md` 对应 mode 行确认
   `rule` 与 `outcome semantics`，前端判定必须与之一致（平特看 7 个开奖号码、绝杀看「不在候选内」等）。
7. **分组说明**：凡是「二选一 / 多选一」的生肖或号码分组，两组都必须渲染；
   固定分组值以 `public.fixed_data` 为准，且 `status` 必须为 1。

---

## 五、十个站点的渲染形态（维护参考）

| site | web_id | 前台地址 | 渲染方式 | 备注 |
| --- | ---: | --- | --- | --- |
| shengshi8800 | 4 | `/vendor/shengshi8800/embed.html?type=3&web=4…` | legacy 单页 + 独立 JS | 统一判定模块 `legacy-prediction-verdict.js` |
| twcaibawang | 5 | `/twcaibawang` | React 组件 | `TwcaibawangHomeClient.tsx`；另有 vendor 聚合接口 |
| twsaimahui | 6 | `/vendor/twsaimahui/index.html`（首页用 iframe 包） | legacy + **bundle** | 改源 JS 后必须 `--rebuild --apply` |
| twjinniu | 7 | `/twjinniu` | React 组件 + 文章页 | |
| twcf888 | 8 | `/twcf888` | React 组件 + 文章页 | |
| twssz | 9 | `/twssz` | legacy + `site-data-adapter.js` | DOM 适配层，高亮要在适配层判定 |
| twbst528 | 10 | `/twbst528` | legacy + `site-data-adapter.js` + 文章页 | 常见「一行多期」结构，必须逐期判定 |
| twjsz666 | 11 | `/twjsz666` | legacy + `site-data-adapter.js` + 文章页 | |
| twwanli | 12 | `/twwanli` | React 组件 | |
| twsyw | 13 | `/twsyw` | 页面自渲染 | 首轮审计 0 违规，可作参考实现 |

---

## 六、常见根因速查

| 现象 | 常见根因 | 处理 |
| --- | --- | --- |
| 「错」的期仍有黄底 | 高亮取自供应商静态 HTML 的命中标记；或整行/整模块共用一个命中状态 | 高亮条件必须与本期判定绑定；渲染前先清除旧高亮 |
| 某一期 `开:？00错` | 模块在找不到开奖号码对应项时用了占位串 | 固定显示本期真实特码，判定照常 |
| 全场都是同一个分组（全左肖/全阳肖…） | 生成侧每期只输出一个标签 + 没有相邻期约束 | 把该 mode 加入 `THREE_PERIOD_UNIQUE_MODE_IDS`，并保证候选标签能枚举出两组 |
| 分组说明少一组 | 前端只按「本期恰好抽到哪组」拼说明；或 `fixed_data` 该行被停用 | 用固定分组兜底 + 打开 `fixed_data.status` |
| 页面出现 `["` `"]` | JS 直接 `d.content.split(',')` 或 `print` 了原始 JSON | 改用 `safeParseJSON` / 正确解析后取标签 |
| 整块模块空白 + JS 报错 | `JSON.parse` 遇到非 JSON 的 content 抛错 | 用 `safeParseJSON` 兜底，并给出兜底渲染分支 |
| 高亮文件名没变导致改动不生效 | bundle 站点文件名是内容哈希且长缓存 | 必须 `--rebuild --apply` 重建（文件名会变） |
