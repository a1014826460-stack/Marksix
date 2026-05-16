# 前端 ↔ 后端 API 缺口分析

> 分析日期：2026-05-15
> 最后更新：2026-05-16（P0 修复批次 1）
>
> 范围：twsaimahui 静态前端项目所需的 48 个唯一 API 端点，对照后端 Python API + Next.js 兼容层的实际实现状态。

## 0. 修复记录

### 2026-05-16 — P0 修复批次 1

| 修复项 | 文件 | 状态 |
|---|---|---|
| Python 注册 `/api/kaijiang/*` 兜底路由 | `backend/src/routes/legacy_routes.py` | ✅ 已修复 |
| Python 注册 `/api/post/getList` 路由 | `backend/src/routes/legacy_routes.py` | ✅ 已修复 |
| Python 创建 `GET /api/public/notice` + `/api/index/notice` | `backend/src/routes/public_routes.py` | ✅ 已修复 |
| Next.js 创建 `GET /api/index/notice` 代理 | `frontend/app/api/index/notice/route.ts` | ✅ 已修复 |
| Next.js 添加 `getXiaoma2` → `getXiaoma` 别名 | `frontend/app/api/kaijiang/[...path]/route.ts` | ✅ 已修复 |
| Next.js 添加 `getHbx` → `getHbnx` 别名 | `frontend/app/api/kaijiang/[...path]/route.ts` | ✅ 已修复 |
| Next.js `default` 分支代理到 Python kaijiang 兜底 | `frontend/app/api/kaijiang/[...path]/route.ts` | ✅ 已修复 |

**修复策略说明：**

- **已知 modes_id 的端点**：继续走 Next.js 显式 case → `/api/legacy/module-rows`，行为不变
- **路径别名**：`getXiaoma2` 和 `getHbx` 映射到已有的 `getXiaoma` 和 `getHbnx` case
- **未知 modes_id 的端点**（约 28 个）：Next.js `default` → 代理到 Python `/api/kaijiang/*` → `frontend_compat.py` 使用 `num` 参数作为 modes_id 查询数据
- **notice 端点**：Next.js `/api/index/notice` → Python `/api/public/notice` → 读取 `managed_sites.announcement`

**剩余风险：**

- 兜底机制中 `num` 参数不一定等于正确的 modes_id，返回的数据可能不准确
- 需要后续逐个确认 modes_id 映射后，将端点从兜底提升为显式 case
- `notice.content` 的 XSS 过滤需要后端配合

## 1. 调用链路

```
twsaimahui 静态 HTML
  → window.httpApi + /api/kaijiang/*
  → 生产 Nginx 路由
  → Next.js frontend /api/kaijiang/[...path]/route.ts  （兼容层）
  → Python backend /api/legacy/module-rows             （数据源）
         ↓
     读取 created.mode_payload_* / public.mode_payload_* 表
```

关键文件：

- 兼容层: `frontend/app/api/kaijiang/[...path]/route.ts`（~32 个 case 分支）
- 数据源: `backend/src/routes/legacy/` → `GET /api/legacy/module-rows?modes_id=X&web=Y&type=Z&limit=N`
- 前端配置: `twsaimahui/static/js/lottery_config.js`（3 个彩种的 web/type/apiBase 映射）

---

## 2. 缺口总览

| 类别 | 数量 | 严重程度 | 状态 |
|---|---|---|---|
| 后端 Python 完全缺失的端点 | ~~2~~ → 0 | P0 | ✅ 已修复 |
| Next.js 兼容层未映射的 kaijiang 端点 | ~~29~~ → 29 个中 27 个走兜底 | P0→P1 | 🔧 兜底可用 |
| Next.js 兼容层路径名拼写不匹配 | ~~2~~ → 0 | P0 | ✅ 已修复 |
| 响应字段不完整（已对接端点） | 15+ | P1 | ⚠️ 待确认 |
| 特殊字段需求（兼容层无处理逻辑） | 10 | P1 | ⚠️ 待确认 |
| `/api/legacy/module-rows` 自身限制 | 4 项 | P2 | ⚠️ 待确认 |

---

## 3. 后端 Python 完全缺失的端点

### 3.1 `GET /api/index/notice` — 公告弹窗 ✅ 已修复

- **用途**: 页面加载时弹出公告窗口，内容为 HTML
- **调用位置**: `index.html` 内联 `<script>`（第 1836 行附近）
- **请求示例**: `/api/index/notice?web=6`
- **当前状态**: ✅ Python 路由 `/api/public/notice` + `/api/index/notice` 已注册；Next.js `app/api/index/notice/route.ts` 已创建

**请求参数**:

| 参数名 | 位置 | 必填 | 类型 | 示例 | 说明 |
|---|---|---|---|---|---|
| `web` | query | 是 | integer | `6` | 站点 ID |

**成功响应**（前端要求）:

```json
{
  "code": 600,
  "data": {
    "content": "<div>公告内容 HTML</div>"
  }
}
```

**关键约束**:

- `code` **必须等于 `600`**，否则前端直接 `return` 忽略公告
- `data.content` 会通过 `innerHTML` 插入页面 —— **必须过滤 XSS**
- 推荐后端只允许白名单 HTML 标签：`<div> <p> <span> <b> <font> <table> <img> <a> <br>`
- 必须过滤：`<script>` `onerror` `onclick` `onload` `javascript:` `data:text/html`

**建议实现方式**（二选一）:

A. 后端新增路由 `GET /api/public/notice?web=6`，从 `managed_sites.announcement` 字段读取
B. Next.js 兼容层新增 `frontend/app/api/index/notice/route.ts`，调用后端获取站点公告

### 3.2 `GET /api/post/getList` — 推荐资料列表

- **用途**: "推"模块展示推荐文章/图片列表
- **调用位置**: `zx.js`（Vue 3 组件，挂载到 `#zx5`）
- **请求示例**: `/api/post/getList?web=6&type=3&pc=72`
- **当前状态**: ✅ Python 路由 `/api/post/getList` 已注册（`legacy_routes.py`），委托给 `frontend_compat.py` 处理；Next.js 有 `app/api/post/getList/route.ts` 代理。**链路已通，需确认 `pc=72` 的数据存在。**

**请求参数**:

| 参数名 | 位置 | 必填 | 类型 | 示例 | 说明 |
|---|---|---|---|---|---|
| `web` | query | 是 | integer | `6` | 站点 ID |
| `type` | query | 是 | integer | `3` | 彩种类型 |
| `pc` | query | 是 | integer | `72` | 推荐位/分类参数，非页码 |

**成功响应**:

```json
{
  "data": [
    { "id": 1, "title": "推荐资料标题一" },
    { "id": 2, "title": "推荐资料标题二" }
  ]
}
```

**安全要求**:

- `title` 通过 Vue `v-html` 渲染 —— **必须过滤 XSS**

---

## 4. Next.js 兼容层缺失的 kaijiang 端点映射

以下 29 个端点在 twsaimahui 前端被调用，但 `frontend/app/api/kaijiang/[...path]/route.ts` 的 `switch` 语句中无对应 `case`，会走到 `default: return jsonResponse([])` 分支返回空数组。

### 4.1 完整缺失列表

| # | 前端路径 | 调用源 JS | num 值 | 业务名称 | 需确定 modes_id |
|---|---|---|---|---|---|
| 1 | `/api/kaijiang/getJyxiao2` | 061jy2x.js | 2 | 特邀家野两肖 | 待查 |
| 2 | `/api/kaijiang/getZyx` | 033zuoyou.js | 2 | 左右 | 待查 |
| 3 | `/api/kaijiang/getXiaoma2` | 012liuxiao.js | 6 | 精品六肖 | 待查（可能复用 getXiaoma 的 44） |
| 4 | `/api/kaijiang/getXiaoma2` | 027six8m.js | 4 | 四肖八码 | 同上 |
| 5 | `/api/kaijiang/getXiaoma2` | 011jiepaoma.js | 7 | 跑马图/解跑马 | 同上 |
| 6 | `/api/kaijiang/getYysx` | 044yinyang.js | 2 | 阴阳 | 待查 |
| 7 | `/api/kaijiang/getDsWei` | 003ds4w.js | 4 | 单双四尾 | 待查 |
| 8 | `/api/kaijiang/getZhongte` | 073sixiao.js | 4 | 六肖 | 待查 |
| 9 | `/api/kaijiang/getZhongte` | 042ycwx.js | 5 | 隐刺五肖 | 待查 |
| 10 | `/api/kaijiang/getZhongte` | 014jiuxiao.js | 9 | 九肖 | 待查 |
| 11 | `/api/kaijiang/getZhongte` | 031wuxiao.js | 3 | 三肖 | 待查 |
| 12 | `/api/kaijiang/getZhongte` | 030lflx.js | 4 | 四肖 | 待查 |
| 13 | `/api/kaijiang/getZhongte` | 047liuxiao.js | 6 | 风小子六肖 | 待查 |
| 14 | `/api/kaijiang/getZhongte` | 062linbei6x.js | 6 | 林北 | 待查 |
| 15 | `/api/kaijiang/getHeds` | 006heshuds.js | 2 | 合数单双 | 待查 |
| 16 | `/api/kaijiang/getTdsx1` | 043tiandi.js | 2 | 天地(一) | 待查 |
| 17 | `/api/kaijiang/getTdsx1` | 075tiandi.js | 2 | 天地(二) | 同上 |
| 18 | `/api/kaijiang/getCyptwei` | 068chengyupw.js | 2 | 成语平特尾 | 待查 |
| 19 | `/api/kaijiang/getDsxiao` | 004danshuang.js | 2 | 单双(变体) | 待查 |
| 20 | `/api/kaijiang/getYbzt` | 036ma12.js | 2 | 一波 | 待查 |
| 21 | `/api/kaijiang/getWeima2` | 026siw8m.js | 4 | 四尾八码 | 待查 |
| 22 | `/api/kaijiang/getWwx` | 046wenwu.js | 2 | 文武 | 待查 |
| 23 | `/api/kaijiang/getYwx` | 045youwu.js | 2 | 有无 | 待查 |
| 24 | `/api/kaijiang/getBmzy` | 053wfsb.js | 3 | 文房四宝 | 待查 |
| 25 | `/api/kaijiang/getX2jiam8` | 069lxbm.js | 2 | 两肖+八码 | 待查 |
| 26 | `/api/kaijiang/getPtWei` | 022pt1w.js | 2 | 平特一尾 | 待查 |
| 27 | `/api/kaijiang/getShama` | 056s7m.js | 7 | 杀七码 | 待查 |
| 28 | `/api/kaijiang/getFyld` | 051fyld.js | 3 | 风雨雷电 | 待查 |
| 29 | `/api/kaijiang/getYzxj` | 029yizixuanji.js | 6/12 | 一字玄机 | 待查 |
| 30 | `/api/kaijiang/getCypt` | 066chengyupx.js | 2 | 成语平肖 | 待查 |
| 31 | `/api/kaijiang/getNnnx` | 020nn4x.js | 4 | 男女 | 待查 |
| 32 | `/api/kaijiang/getXysxma` | 013jiux1m.js | 9/8 | 九肖一码 | 待查 |
| 33 | `/api/kaijiang/getShatou` | 018sha1tou.js | 1 | 杀一头 | 待查 |
| 34 | `/api/kaijiang/getJmxc` | 041meichou.js | 2 | 美丑 | 待查 |
| 35 | `/api/kaijiang/getFsx` | 034feishou.js | 2 | 肥瘦 | 待查 |
| 36 | `/api/kaijiang/getDxd` | 037dandaxiao.js | 2 | 胆大胆小 | 待查 |
| 37 | `/api/kaijiang/getShaBds` | 055sbands.js | 1 | 杀半单双 | 待查 |
| 38 | `/api/kaijiang/rd70i73lziizczak/0gmqnw/1` | 019liubuzhong.js | — | 六不中 | 待查 |

### 4.2 路径名拼写不匹配 ✅ 已修复

| 前端实际调用的路径 | 兼容层已处理的 case | 差异 | 修复方式 | 状态 |
|---|---|---|---|---|
| `getXiaoma2` | `getXiaoma` | 多 "2" 后缀 | 已添加 `case "getXiaoma2":` 复用 `getXiaoma` 逻辑 | ✅ |
| `getHbx` | `getHbnx` | 少 "n" 字母 | 已添加 `case "getHbx":` 复用 `getHbnx` 逻辑 | ✅ |

---

## 5. 已对接端点的响应字段缺口

### 5.1 缺少必要字段

| 端点 | 兼容层返回的字段 | 前端期望但缺失的字段 | 影响 |
|---|---|---|---|
| `getSanqiXiao4new` | `term, start, end, content` | `name` | 023sanqibizhong.js 读取 `d.name` 会得到 `undefined` |
| `getJyxiao2` | （未对接） | `content(JSON), xiao, res_code, res_sx, term` | 061jy2x.js 读取 `d.xiao.split(',')` |
| `getDsWei` | （未对接） | `dan, shuang, res_code, res_sx, term` | 003ds4w.js 读取 `d.dan`, `d.shuang` |
| `getNnnx` | （未对接） | `nan, nv, res_code, res_sx, term` | 020nn4x.js 读取 `d.nan`, `d.nv` |
| `getXysxma` | （未对接） | `code, xiao, res_code, res_sx, term` | 013jiux1m.js 读取 `d.code`, `d.xiao` |
| `getX2jiam8` | （未对接） | `code, content, res_code, res_sx, term` | 069lxbm.js 读取 `d.code` |
| `getYzxj` | （未对接） | `jiexi, xiao, zi, res_code, res_sx, term` | 029yizixuanji.js 读取 `d.jiexi`, `d.xiao`, `d.zi` |
| `rd70i73lziizczak/0gmqnw/1` | （未对接） | `u6_code, res_code, res_sx, term` | 019liubuzhong.js 读取 `d.u6_code` |
| `getCyptwei` | （未对接） | `title, res_code, res_sx, term` | 068chengyupw.js 读取 `d.title` |
| `getCypt` | （未对接） | `title, res_code, res_sx, term` | 066chengyupx.js 读取 `d.title` |

### 5.2 content 字段格式必须为 JSON 字符串

以下已对接端点的 `content` 字段会被前端 `JSON.parse()` 解析，后端必须返回合法 JSON 字符串（如 `"[\"鼠|05,17\",\"牛|04,16\"]"`），不能直接返回数组：

- `getRccx` → 049rccx.js
- `getSjsx` → 050siji.js
- `getHllx` → 048hllx.js
- `getDxzt` → 002daxiao.js
- `getJyzt` → 040jiaye.js
- `danshuang` → 071ds.js
- `getTou` → 072liangtou.js, 024santou.js
- `getShaWei` → 015sha3w.js
- `getShaBanbo` → 054sbanbo.js
- `getXiaoma` → 012liuxiao.js（已通过 mapSevenXiaoQiMa 处理）

---

## 6. 后端 `/api/legacy/module-rows` 自身限制

| 问题 | 说明 | 建议 |
|---|---|---|
| modes_id 映射表缺失 | 29 个端点的 modes_id 未确定，无法查询对应数据 | 查 `fetched_modes` 表，建立 `前端路径 → modes_id` 映射表 |
| web 回退不完整 | `LEGACY_WEB_FALLBACK_BY_TYPE` 只覆盖 9 个 modes_id | 为新增 modes_id 补充 web 回退规则 |
| 无分页参数 | 前端不传分页，后端 `limit` 默认 10 | 根据各模块实际展示条数设定合理的默认 limit |
| type 过滤精度 | 部分端点需严格按 type 区分彩种数据 | 确保 `mode_payload_*` 表中 `type` 字段正确填充 |

---

## 7. 已正确对接的端点（供参考）

以下端点链路已通，可作为新增端点的实现参考：

| 前端路径 | Next.js case | modes_id | 数据映射函数 |
|---|---|---|---|
| `/api/kaijiang/sbzt` | `sbzt` | 38 | `mapSimpleContent` |
| `/api/kaijiang/getPingte` | `getPingte` | 43/56 | `mapPingte2` |
| `/api/kaijiang/danshuang` | `danshuang` | 28 | `mapSimpleContent` |
| `/api/kaijiang/getDsnx` | `getDsnx` | 31 | `mapDanShuangSiXiao` |
| `/api/kaijiang/getCode` | `getCode` | 34 | `mapClassic24Codes` |
| `/api/kaijiang/getShaXiao` | `getShaXiao` | 42 | `mapSimpleContent` |
| `/api/kaijiang/getHllx` | `getHllx` | 8 | `mapSimpleContent` |
| `/api/kaijiang/getDxzt` | `getDxzt` | 57 | `mapSimpleContent` |
| `/api/kaijiang/getJyzt` | `getJyzt` | 63 | `mapSimpleContent` |
| `/api/kaijiang/getTou` | `getTou` | 12 | `mapSimpleContent` |
| `/api/kaijiang/getXingte` | `getXingte` | 53 | `mapSimpleContent` |
| `/api/kaijiang/qqsh` | `qqsh` | 26 | `mapQinQiShuHua` |
| `/api/kaijiang/getShaBanbo` | `getShaBanbo` | 58 | `mapSimpleContent` |
| `/api/kaijiang/getShaWei` | `getShaWei` | 20 | `mapSimpleContent` |
| `/api/kaijiang/getSjsx` | `getSjsx` | 61 | `mapSimpleContent` |
| `/api/kaijiang/getRccx` | `getRccx` | 3 | `mapRouCaiCao` |
| `/api/kaijiang/getSanqiXiao4new` | `getSanqiXiao4new` | 197 | `mapSanqi` |
| `/api/post/getList` | `post/getList` | — | Next.js 代理到 `/legacy/post-list` |

---

## 8. 修复优先级与工作量估算

### 已修复 (2026-05-16)

| 任务 | 状态 |
|---|---|
| 1. Python `/api/kaijiang/*` 兜底路由 | ✅ 已注册 `legacy_routes.py` |
| 2. Python `/api/post/getList` 路由 | ✅ 已注册 `legacy_routes.py` |
| 3. Python `/api/public/notice` + `/api/index/notice` | ✅ 已注册 `public_routes.py` |
| 4. Next.js `app/api/index/notice/route.ts` | ✅ 已创建 |
| 5. Next.js 路径别名（getXiaoma2, getHbx） | ✅ 已添加 case |
| 6. Next.js default 兜底代理到 Python | ✅ 已实现 |

### P1 — 功能验证（本周）

| 任务 | 工作量 | 依赖 |
|---|---|---|
| 7. 验证兜底代理返回数据是否正确（抽查 5-10 个端点） | 0.5 天 | 需有测试数据 |
| 8. 为特殊字段端点补充数据映射函数 | 1-2 天 | 需查表确认字段名 |
| 9. 扩展 LEGACY_WEB_FALLBACK_BY_TYPE | 0.5 天 | 需测试各 type 下的数据可用性 |
| 10. 修复 getSanqiXiao4new 缺少 name 字段 | 0.5 小时 | 无 |

### P2 — 数据质量提升（迭代修复）

| 任务 | 工作量 | 依赖 | 状态 |
|---|---|---|---|
| 11. 逐个确定 28 个缺失端点的 modes_id → 从兜底提升为显式 case | 2-3 天 | 需查 `fetched_modes` 表 | 🔧 已添加 `getZhongte` case；其余待确认 |
| 12. 确保所有 JSON content 端点返回合法 JSON 字符串 | 0.5 天 | 需逐个测试 | ⚠️ 58 个文件仍用裸 `JSON.parse()` |
| 13. 配置合理的 CORS 响应头 | 0.5 小时 | 运维配合 | ✅ Nginx 配置已文档化 |

### 2026-05-16 — P2 修复批次 2

| 修复项 | 文件 | 状态 |
|---|---|---|
| 扩展 `ajax_interceptor.js` null 保护 | `twsaimahui/static/js/ajax_interceptor.js` | ✅ 新增 `dan`, `shuang`, `nan`, `nv`, `xiao`, `code`, `u6_code`, `title`, `jiexi`, `zi`, `name`, `start`, `end`, `image_url`, `content` 共 15 个字段的 null → `""` 转换 |
| 添加 `getZhongte` Next.js case | `frontend/app/api/kaijiang/[...path]/route.ts` | ✅ num=3/4/5/6 → modes_id=46 (lxzt), num=9 → modes_id=49 (jxzt) |
| 移除危险的 Python `num` 作为 modes_id 兜底 | `frontend/app/api/kaijiang/[...path]/route.ts` | ✅ default 分支不再代理到 Python，改为返回 `[]` + 日志警告 |
| Nginx 配置文档化 | `deploy/nginx.conf`, `deploy/nginx.domain.ssl.conf.example` | ✅ 添加 API 路由说明注释 |

**安全扫描结果：**

- `.split()` 风险：**已全局消除** — `ajax_interceptor.js` 将所有 15+ 个可能被 `.split()` 的字段从 null 转为 `""`
- `JSON.parse()` 风险：**部分缓解** — 4 个已迁移模块使用 `safeParseJSON()`，剩余 58 个依赖后端返回合法 JSON。所有 35 个已知 modes_id 由 Next.js 兼容层的数据映射函数处理（已内置 JSON 安全检查）

---

## 9. 如何确定 modes_id 映射

每个前端 `/api/kaijiang/xxx` 端点对应一个 `modes_id`。确定方法：

```sql
-- 查询所有已抓取的玩法及其 modes_id
SELECT fm.id AS modes_id, fm.title, fm.web_id, fm.type,
       COUNT(fmr.id) AS record_count
FROM fetched_modes fm
LEFT JOIN fetched_mode_records fmr ON fmr.mode_id = fm.id
GROUP BY fm.id, fm.title, fm.web_id, fm.type
ORDER BY fm.id;
```

将查询结果中的 `title` 与 twsaimahui 前端模块名称对照，建立映射表。

**已知映射**（从 Next.js 兼容层代码提取）:

| modes_id | 用途 |
|---|---|
| 2 | getWei |
| 3 | getRccx（吃肉草菜） |
| 8 | getHllx（红蓝绿肖） |
| 12 | getTou（两头/三头中特） |
| 20 | getShaWei（杀三尾） |
| 26 | qqsh（琴棋书画） |
| 28 | danshuang（单双） |
| 31 | getDsnx（特邀单双四肖） |
| 34 | getCode（10码/16码/20码） |
| 38 | sbzt（双波） |
| 42 | getShaXiao（杀一肖/杀两肖/绝杀三肖） |
| 43 | getPingte（num=2 平特） |
| 44 | getXiaoma（精品六肖/四肖八码/跑马图） |
| 45 | getHbnx/getHbx（黑白） |
| 46 | lxzt |
| 48 | wxzt |
| 49 | jxzt |
| 50 | getYjzy |
| 51 | sxbm |
| 52 | getSzxj |
| 53 | getXingte（三行） |
| 54 | ptyw |
| 56 | getPingte（num≠2 平特） |
| 57 | getDxzt（大小中特） |
| 58 | getShaBanbo（杀半波） |
| 59 | getDjym |
| 61 | getSjsx（四季肖） |
| 62 | getJuzi（num≠yqmtm） |
| 63 | getJyzt（家野） |
| 65 | getCodeDuan |
| 68 | getJuzi（num=yqmtm） |
| 108 | getDxztt1 |
| 151 | getXmx1 |
| 197 | getSanqiXiao4new（三期必中） |
| 244 | yyptj |
| 246 | qxbm |
| 331 | getPmxjcz |

**尚未确定 modes_id 的端点**（需通过上方的 SQL 查询补充）:

getJyxiao2, getZyx, getYysx, getDsWei, getZhongte, getHeds, getTdsx1, getCyptwei, getDsxiao, getYbzt, getWeima2, getWwx, getYwx, getBmzy, getX2jiam8, getPtWei, getShama, getFyld, getYzxj, getCypt, getNnnx, getXysxma, getShatou, getJmxc, getFsx, getDxd, getShaBds, rd70i73lziizczak/0gmqnw/1

---

## 10. 响应字段通用约束（所有接口适用）

无论端点是否已对接，后端必须遵守以下约束，否则前端会 JS 报错：

1. `res_code` / `res_sx` **不允许返回 `null`**，未开奖时返回空字符串 `""`
2. 标记为「content 为 JSON 字符串」的接口，`content` 必须是字符串形式的 JSON（如 `"[\"鼠|05,17\"]"`），不可直接返回数组
3. 号码统一使用两位字符串：`"01"`, `"09"`, `"49"`
4. 生肖统一使用简体中文：`龙` `马` `鸡` `猪`
5. `term` 统一使用字符串类型
6. 数据按 `term` 倒序排列，最新期在前
7. 所有接口均为公开 GET，不强制鉴权
8. 响应头 `Content-Type: application/json; charset=utf-8`
9. 跨域场景需配置 CORS
