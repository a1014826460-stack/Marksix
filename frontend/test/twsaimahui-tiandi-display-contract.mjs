/**
 * twsaimahui 天地生肖（`043tiandi.js`，mode 5）头部固定分类契约
 * ---------------------------------------------------------------
 * 背景（2026-10-05 用户反馈）：
 *   mode 5 每期 `content` 只记录**本期选中的那一组**（`天肖|…` 或 `地肖|…`），
 *   因为渲染层的判定口径就是「特肖是否落在该组」（把两组都塞进 content 会让
 *   `zj` 恒为真、判定恒「准」）。面板头部却要同时显示天肖/地肖两行，
 *   于是拿 content 推另一组必然缺一行 —— 用户看到「天肖:兔马猴猪牛龙 / 地肖:（空）」。
 * 修复：`/api/kaijiang/getTdsx1` 附加上 `fixed_data`（sign=天地生肖）的完整分组，
 *   面板头部优先用它补齐；`data` 形状与每期判定口径不变。
 *
 * 固定行为：
 *   1. 响应带 `groups` → 头部天肖/地肖都完整（来自 fixed_data）；
 *   2. 响应不带 `groups`（旧后端）→ 退回原来的「按 content 推断」，行为不变；
 *   3. 每期历史行的正文与「准/错」仍只按该行自己的 content 判定；
 *   4. bundle 内的同一段逻辑必须同步（首屏走 bundle）。
 */
import fs from "node:fs"
import vm from "node:vm"

const PANEL_PATH = "frontend/public/vendor/twsaimahui/static/js/043tiandi.js"
const BUNDLE_PATH = "frontend/public/vendor/twsaimahui/static/js/bundle-78c5cb0f22e5ec36.js"

function loadPanel() {
  const source = fs.readFileSync(PANEL_PATH, "utf8")
  let ajaxConfig = null
  let rendered = ""
  const sandbox = {
    httpApi: "",
    web: "6",
    type: "3",
    safeParseJSON: (text, fallback) => {
      try {
        return JSON.parse(text)
      } catch {
        return fallback
      }
    },
    $: Object.assign(
      (selector) => ({ html: (value) => { if (selector === ".l22") rendered = String(value) } }),
      { ajax: (config) => { ajaxConfig = config } },
    ),
    console,
    JSON,
  }
  vm.createContext(sandbox)
  vm.runInContext(source, sandbox, { filename: "043tiandi.js" })
  if (!ajaxConfig) throw new Error("043tiandi.js 没有发起 ajax")
  return { ajaxConfig, html: () => rendered }
}

/** 一行 mode 5 记录：content 只有一组，xiao/term/res_* 与线上同形。 */
function row({ term, group, members, resSx, resCode }) {
  return {
    term: String(term),
    content: JSON.stringify([`${group}|${members}`]),
    xiao: "猴,虎",
    res_code: resCode || "",
    res_sx: resSx || "",
  }
}

const FIXED_GROUPS = [
  { label: "天肖", codes: ["兔", "马", "猴", "猪", "牛", "龙"] },
  { label: "地肖", codes: ["蛇", "羊", "鸡", "狗", "鼠", "虎"] },
]

// ── 1. 带 groups：头部两行都完整（即使 content 只选了天肖）────────────────
{
  const panel = loadPanel()
  panel.ajaxConfig.success({
    data: [row({ term: 275, group: "天肖", members: "兔,马,猴,猪,牛,龙", resSx: "马", resCode: "01,02,03,04,05,06,37" })],
    groups: FIXED_GROUPS,
  })
  const html = panel.html()
  if (!html.includes("天肖</span>:<span class='stylezi'>兔马猴猪牛龙")) {
    throw new Error(`头部天肖缺失或形态变化：${html.slice(0, 200)}`)
  }
  if (!html.includes("地肖</span>:<span class='stylezi'>蛇羊鸡狗鼠虎")) {
    throw new Error("头部地肖未按 fixed_data 补齐")
  }
  if (!html.includes("275期") || !html.includes("开:马37准")) {
    throw new Error("历史行未按原样渲染（本期选天肖、开奖特肖马 → 准）")
  }
}

// ── 2. content 只选地肖时，天肖同样由 groups 补齐 ────────────────────────
{
  const panel = loadPanel()
  panel.ajaxConfig.success({
    data: [row({ term: 274, group: "地肖", members: "蛇,羊,鸡,狗,鼠,虎", resSx: "马", resCode: "01,02,03,04,05,06,37" })],
    groups: FIXED_GROUPS,
  })
  const html = panel.html()
  if (!html.includes("天肖</span>:<span class='stylezi'>兔马猴猪牛龙")) {
    throw new Error("content 只选地肖时，头部天肖未补齐")
  }
  if (!html.includes("地肖</span>:<span class='stylezi'>蛇羊鸡狗鼠虎")) {
    throw new Error("content 只选地肖时，头部地肖缺失")
  }
  // 判定仍按该行自己的组：本期选的是地肖，开奖特肖「马」属于天肖 → 不是「准」
  // （头部完整显示两组不影响判定口径；043tiandi.js 未命中时后缀为空格）
  if (!html.includes("开:马37") || html.includes("开:马37准")) {
    throw new Error(`每期判定口径被改变：${html.slice(0, 240)}`)
  }
}

// ── 3. 旧后端（无 groups）：退回按 content 推断，形态与修复前一致 ─────────
{
  const panel = loadPanel()
  panel.ajaxConfig.success({
    data: [row({ term: 273, group: "天肖", members: "兔,马,猴,猪,牛,龙", resSx: "马", resCode: "01,02,03,04,05,06,37" })],
  })
  const html = panel.html()
  if (!html.includes("天肖</span>:<span class='stylezi'>兔马猴猪牛龙")) {
    throw new Error("无 groups 时天肖未按 content 渲染")
  }
  if (!html.includes("地肖</span>:<span class='stylezi'></span>")) {
    throw new Error("无 groups 时不应凭空补地肖（保持旧行为）")
  }
}

// ── 4. bundle 内同一段逻辑必须已同步 ─────────────────────────────────────
{
  const bundle = fs.readFileSync(BUNDLE_PATH, "utf8")
  if (!bundle.includes("let fixedGroups = response.groups || [];")) {
    throw new Error("bundle 内的天地生肖逻辑未同步修复（首屏走 bundle）")
  }
  if (!bundle.includes("tx = tx || c[1].replaceAll(',','');")) {
    throw new Error("bundle 内未把 content 推断改成兜底")
  }
}

console.log("twsaimahui tiandi display contract passed")
