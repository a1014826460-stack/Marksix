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
 * 01-49 全覆盖、互不重叠：
 *   金 03,04,11,12,25,26,33,34,41,42
 *   木 07,08,15,16,23,24,37,38,45,46
 *   水 13,14,21,22,29,30,43,44
 *   火 01,02,09,10,17,18,31,32,39,40,47,48
 *   土 05,06,19,20,27,28,35,36,49
 *
 * ⚠️ `fixed_data` 里另有一份 `sign='五行肖'`，那是**生肖五行**（虎兔为木、蛇马为火…），
 * 只用于生肖类玩法。四行中特历史上（正文 `木|04,05,16,17,28,29,40,41` 这种清单）
 * 用的就是生肖五行，于是 17 虎被算成「木」（号码五行应为「火」）、37 马被算成「火」
 * （号码五行应为「木」）。号码五行只能由**特码号码**推导，禁止回退到生肖五行。
 */
export {
  ELEMENT_BY_CODE,
  ELEMENT_NUMBER_GROUPS,
  elementHitJudgement,
  elementOfCode,
  normalizeElementLabel,
} from "@/lib/element-number-groups"
