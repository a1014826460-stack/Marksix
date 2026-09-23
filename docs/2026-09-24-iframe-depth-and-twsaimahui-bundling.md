# 第 3 项：减少 iframe 层数 + 合并 twsaimahui 脚本（2026-09-24）

目标（用户四项中的第 3 项）。本文记录已完成的部分、未完成部分的真实阻塞点与安全路径。

## 1. 已实施：twsaimahui 逐模块脚本合并（59 请求 → 2）

### 1.1 现状盘点

`twsaimahui/index.html` 有 119 个 `<script src>`：

| 分类 | 数量 | 说明 |
| --- | --- | --- |
| 双引号 / 单引号标签 | 23 / 96 | 混用，靠正则两种引号都要覆盖 |
| **HTML 注释里** | **41** | 例如 `<!-- <script src="static/js/032ma20.js"></script> -->`，是**刻意停用**的模块，绝不能激活 |
| 启用模块脚本 | 59 | `static/js/0NN*.js`，分散在文档各处 |
| 其它（jquery/vue/axios/kj.js/第三方） | 其余 | 不合并 |

关键结论：这些模块脚本**没有** `"use strict"`、**没有** `document.currentScript`（顶层作用域在传统脚本里本来就共享），且都是"发 AJAX→回调里渲染"，因此按顺序拼接在语义上等价。

### 1.2 合并规则（只合并连续区间）

脚本在文档里是**穿插**的：模块脚本之间夹着其它脚本与 inline 脚本。把 59 个全部挪到一个文件会改变执行顺序、进而改变渲染顺序。因此：

- 只有"模块脚本之间除注释/停用标签外没有其它**生效**脚本"的相邻段落才合并；
- 合并后，区间的**位置不变**（bundle 标签放在区间首个脚本的位置），区间内其余标签**逐个删除**（保留它们之间的注释等非脚本内容）；
- 注释里的脚本既不算启用、也不被删除（合并前后都保持停用）；
- bundle 文件名 = 来源名+内容的 sha256 前 16 位（内容寻址，幂等）。

实测结果：**59 个启用模块脚本分成 2 段 → 2 个 bundle（322.5 KB + 11.6 KB）**，请求数 63→2。

### 1.3 验证

| 验证项 | 结果 |
| --- | --- |
| `node --check`（两个 bundle） | 通过 |
| `frontend/test/twsaimahui-bundle-contract.mjs` | 通过：bundle 逐字节按序包含全部源文件；index.html 无启用模块标签；4 个残留引用全部在注释内且文件仍在磁盘（api-audit 契约仍按文件名引用） |
| 幂等重跑 `--apply` | "already bundled (no module runs left); manifest kept"，不产生新 bundle |
| **真实浏览器（Playwright + 系统 Chrome）** `frontend/test/twsaimahui-bundle-smoke.py` | 合并前 vs 合并后：`body_text_hash` 均为 `945324bcb16419e2`、正文长度 476、console 错误 130、page 错误 4、`frames=2`、`.KJ-TabBox`/`.KJ-IFRAME` 各 1 —— **逐项一致**；元素数 342→287，差值正好等于被移除的 script 元素数 |

工具：`scripts/bundle-twsaimahui-modules.py`（dry-run 默认，`--apply` 写回）。

## 2. 未实施：iframe 层数收敛（阻塞点已查清）

### 2.1 现状层级

| 站点 | 链路 |
| --- | --- |
| twssz / twwanli / twsyw / twjsz666 / twbst528 | Next 页 → `/vendor/<site>/index.html` → `kai.html` → 开奖面板 |
| twjinniu / twcf888 / twcaibawang | Next 页 → `/vendor/<site>/index.html` → 开奖面板（直接内嵌） |
| twsaimahui | `/vendor/twsaimahui/index.html` → JS 建面板 |

### 2.2 为什么不能直接内联 `kai.html`

`iframe[src='kai.html']` 是**跨文件契约**，直接内联会同时打断四处：

1. 站点适配器按该选择器找开奖 frame：`twssz/site-data-adapter.js:1489`、
   `twsyw/site-data-adapter.js:9`、`twwanli/site-data-adapter.js:9`、
   `twjsz666/site-data-adapter.js:761`；
2. 静态契约：`twssz-adapter-contract.mjs:127`、`twsyw-adapter-contract.mjs:5,11`、
   `twwanli-adapter-contract.mjs:4,10`、`twjsz666-static-contract.mjs:62`、
   `twjsz666-subpage-contract.mjs:6,56-58`、`vendor-static-weight-contract.mjs:36-55`；
3. 浏览器契约（Playwright）：`site-ui-browser-contract.py`（`draw: "iframe[src='kai.html']"`）、
   `twssz-live-mapping-contract.py:147`、`twsyw-live-mapping-contract.py:52,55`、
   `twwanli-live-mapping-contract.py:90,95`、`twjsz666-live-mapping-contract.py:105,296`；
4. 面板与父页的 `postMessage`（`lottery-change` 切彩种）当前跨 "面板 → kai.html → 站点页"
   两级，内联后父级关系改变，必须同步改协议。

也就是说，这不是"改一行 HTML"，而是一次**跨页面 + 适配器 + 12 个契约 + 消息协议**的
协调改造，且必须用真实浏览器回归才能确认。本轮先完成脚本合并（风险可控、可验证），
iframe 内联按下面的安全路径单独推进。

### 2.3 安全推进路径（建议下一轮）

1. 先做 `twsyw`（最小面）：`index.html` 的 `kai.html` iframe 内联为等价的 tab 结构，
   适配器的 `knownDrawFrame` 改成直接取面板 frame，`lottery-change` 由面板直接
   `postMessage` 给站点页；
2. 同步更新该站点的 3 个契约（adapter/legacy/live-mapping），用 Playwright 跑通；
3. 通过后再复制到 `twwanli`、`twssz`、`twjsz666`、`twbst528`（twbst528 的面板由
   `KJTB.init` 创建，规则不同）；
4. `twjinniu`/`twcf888`/`twcaibawang` 的"外层 React + 内层整站 iframe"属于结构性改造，
   收益最大但需要重写厂商页为 React 组件，建议单独立项评估。

## 3. 回滚

- 脚本合并：`git checkout -- frontend/public/vendor/twsaimahui/index.html` 并删除
  `static/js/bundle-*.js`、`static/js/bundles.json` 即可回到 63 个独立请求的原始状态
  （原始模块文件始终保留）。
- 合并脚本本身是幂等的，重跑 `--apply` 不会重复合并。
