/**
 * 台湾彩霸王（twcaibawang）**号码五行**分组 —— 该站五行类玩法（四行中特 mode 482 等）
 * 展示与判定的唯一口径。
 *
 * ⚠️ 本文件**不再自带常量表**，只是对唯一权威前端共享源 `@/lib/element-number-groups`
 * 的**再导出（re-export shim）**，保留既有导出签名（`TwcaibawangHomeClient.tsx` 与
 * `frontend/test/twcaibawang-verdict-contract.mjs` 都从这里引用）。新增代码请直接
 * import `@/lib/element-number-groups`。
 *
 * 权威来源：`backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS`
 * （= `public.fixed_data` 的 `sign='五行'`；后端 `public/api.py::_ELEMENT_MAP` 也由它派生）。
 * 01-49 全覆盖、互不重叠（2026-09-29 整体改判为「新表」：相对上一版 25 个号码换组，
 * 规律为 `new(x) = old(x-1)`、01 归水）：
 *   金 04,05,12,13,26,27,34,35,42,43
 *   木 08,09,16,17,24,25,38,39,46,47
 *   水 01,14,15,22,23,30,31,44,45
 *   火 02,03,10,11,18,19,32,33,40,41,48,49
 *   土 06,07,20,21,28,29,36,37
 *
 * ⚠️ `fixed_data` 里另有一份 `sign='五行肖'`，那是**生肖五行**（虎兔为木、蛇马为火…），
 * 只用于生肖类玩法。四行中特历史上（正文 `木|04,05,16,17,28,29,40,41` 这种清单）
 * 用的就是生肖五行，于是 37 马被算成「火」（号码五行应为「土」）、24 羊被算成「土」
 * （号码五行应为「木」）。号码五行只能由**特码号码**推导，禁止回退到生肖五行。
 */
export {
  ELEMENT_BY_CODE,
  ELEMENT_NUMBER_GROUPS,
  elementHitJudgement,
  elementOfCode,
  normalizeElementLabel,
} from "@/lib/element-number-groups"
