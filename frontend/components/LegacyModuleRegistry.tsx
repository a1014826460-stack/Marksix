/**
 * 旧站模块渲染器注册表 — LegacyModuleRegistry.tsx
 * ---------------------------------------------------------------
 * 职责：集中管理所有旧站预测模块的 mechanism_key → React 组件映射。
 *
 * 每个旧站 JS 文件对应一个 mode_payload 表和一个渲染组件。
 * 新模块只需在此注册 mechanism_key 和渲染组件即可。
 *
 * 使用方式（在 PredictionModules.tsx 中）：
 *   const Renderer = LEGACY_RENDERERS[module.mechanism_key]
 *   if (Renderer) return <Renderer module={module} />
 */

import type { PublicModule, PublicHistoryRow } from "@/lib/site-page"

// ===================== 渲染器类型 =====================

/** 自定义渲染器接收完整的 PublicModule */
type LegacyRenderer = React.FC<{ module: PublicModule }>

// ===================== 注册表 =====================

/**
 * 渲染器注册表
 * ---------------------------------------------------------------
 * key:   mechanism_key（如 "legacy_7x7m"）
 * value: 渲染该模块的 React 组件
 *
 * 添加新渲染器：
 *   1. 在此文件中创建组件
 *   2. 在 LEGACY_RENDERERS 中添加映射
 *   3. 如需要新 CSS，在 globals.css 中添加
 */
export const LEGACY_RENDERERS: Record<string, LegacyRenderer> = {
  // 已迁移的旧渲染器
  legacy_7x7m: QxqmSection,
  legacy_6wei: LiuweiSection,

  // Category B - ptyx11 table modules
  legacy_wxzt: WxztSection,
  legacy_jxzt: JxztSection,
  legacy_dxztt1: Dxztt1Section,
  legacy_rccx: RccxOriginalSection,
  legacy_sjsx: CxqdSection,

  // Category C - complex multi-row modules
  legacy_9x1m: JxymSection,
  legacy_wxbm: WxbmSection,          // ← wxbm.js 浅月流歌（条件渲染）

  // Category D - three-column tables
  legacy_danshuang: DanshuangSection,

  // Category E - text/poem multi-line
  legacy_yqmtm: YqjtSection,
  legacy_yjzy: YjzySection,

  // Category F - special format
  legacy_hbnx: HblxSection,
  legacy_dssx: DssxSection,
  legacy_teduan: TeduanSection,
  legacy_tema: TemaSection,
  legacy_shaxiao: ShaxiaoSection,
  legacy_shabanbo: ShabanboSection,
  legacy_3ssx: SssxSection,
  legacy_qqsh: QqshSection,
  legacy_dsnx: DsnxSection,
  legacy_pmxjcz: PmxjczSection,
}

// ===================== 工具函数 =====================

/**
 * 判断预测是否命中（黄底高亮用）
 */
const ZODIAC_SET = new Set(["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"])

export function isContentMatch(content: string, resSx: string, resCode: string): boolean {
  if (!resSx && !resCode) return false
  const sxList = resSx.split(",").filter(Boolean).map(s => s.trim())
  const codeList = resCode.split(",").filter(Boolean).map(s => s.trim())

  // 检查生肖
  for (const char of content) {
    if (ZODIAC_SET.has(char) && sxList.includes(char)) return true
  }

  // 检查数字
  const nums = content.match(/\d+/g) || []
  for (const num of nums) {
    if (codeList.includes(num)) return true
  }

  return false
}

/**
 * 选中命中内容的字符，包裹 yellow 高亮
 * 例："鼠牛虎" 中 "牛" 命中 → "鼠<span class='highlight'>牛</span>虎"
 */
export function highlightMatches(content: string, resSx: string): string {
  if (!resSx) return content
  const sxList = resSx.split(",").filter(Boolean).map(s => s.trim())
  const matching = new Set(sxList)

  return content.split("").map(char => {
    if (ZODIAC_SET.has(char) && matching.has(char)) {
      return `<span class="highlight">${char}</span>`
    }
    return char
  }).join("")
}

// ===================== 七肖七码 / 台湾资料网 =====================

/**
 * 七肖七码 / 台湾资料网（mechanism_key=legacy_7x7m）自定义渲染
 * ---------------------------------------------------------------
 * 匹配旧站 001qxqm.js 的多行表格布局
 */
export function QxqmSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾资料网!</div>
      <table border={1} width="100%" cellPadding={0} cellSpacing={0}
        className="qxtable" bgcolor="#FFFFFF">
        <tbody>
          {module.history.map((row, idx) => {
            let zodiacs: string[] = []
            let codes: string[] = []

            // Try parsing raw xiao column (JSON object {"xiao":"...","code":"..."})
            try {
              const rawXiao = String(row.raw?.xiao || "")
              if (rawXiao.startsWith("{")) {
                const obj = JSON.parse(rawXiao)
                zodiacs = (obj.xiao || "").split(",").filter(Boolean)
                codes = (obj.code || "").split(",").filter(Boolean)
              }
            } catch { /* not JSON object */ }

            // Fallback: try legacy JSON array
            if (zodiacs.length === 0) {
              try {
                const rawContent = String(row.raw?.content || row.prediction_text)
                const parsed = JSON.parse(rawContent)
                if (Array.isArray(parsed)) {
                  zodiacs = parsed.map((item: string) => item.split('|')[0])
                  codes = parsed.flatMap((item: string) => (item.split('|')[1] || '').split(',').filter(Boolean))
                }
              } catch { /* not JSON array */ }
            }

            if (zodiacs.length === 0) {
              zodiacs = row.prediction_text.split(",").filter(Boolean)
            }

            const allNums = codes
            const resSx = String(row.raw?.res_sx || "")
            const resCode = String(row.raw?.res_code || "")

            function hz(z: string): string {
              if (resSx.split(",").map(s => s.trim()).some(sx => sx === z))
                return `<span class="highlight">${z}</span>`
              return z
            }
            function hc(n: string): string {
              if (resCode.split(",").map(s => s.trim()).some(c => c === n))
                return `<span class="highlight">${n}</span>`
              return n
            }

            return (
              <tr key={`7x7m-${idx}`}>
                <td colSpan={2} style={{ padding: 0 }}>
                  <table width="100%" cellPadding={0} cellSpacing={0} style={{ borderCollapse: 'collapse' }}>
                    <tbody>
                      <tr>
                        <td colSpan={2} style={{
                          textAlign: 'center', background: '#FFCCFF',
                          fontSize: '16px', fontWeight: 'bold', height: 50, color: '#0000FF'
                        }}>
                          {row.issue}:勇敢向钱钱钱飞!
                        </td>
                      </tr>
                      <tr>
                        <td width="45%" height="24" style={{ backgroundColor: '#F4F4F4', textAlign: 'left', paddingLeft: 8 }}>
                          <span style={{ color: '#000080' }}>一肖:</span>
                          <span style={{ color: '#FF0000', fontSize: 22 }} dangerouslySetInnerHTML={{
                            __html: zodiacs.length > 0 ? hz(zodiacs[0]) : ''
                          }} />
                        </td>
                        <td height="24" style={{ backgroundColor: '#F4F4F4', textAlign: 'left', paddingLeft: 8 }}>
                          <span style={{ color: '#000080' }}>一码:</span>
                          <span style={{ color: '#FF0000', fontSize: 22 }} dangerouslySetInnerHTML={{
                            __html: allNums.length > 0 ? hc(allNums[0]) : ''
                          }} />
                        </td>
                      </tr>
                      <tr>
                        <td width="45%" height="24" style={{ backgroundColor: '#F4F4F4', textAlign: 'left', paddingLeft: 8 }}>
                          <span style={{ color: '#000080' }}>二肖:</span>
                          <span style={{ color: '#FF0000', fontSize: 22 }} dangerouslySetInnerHTML={{
                            __html: zodiacs.slice(0, 2).map(hz).join('')
                          }} />
                        </td>
                        <td height="24" style={{ backgroundColor: '#F4F4F4', textAlign: 'left', paddingLeft: 8 }}>
                          <span style={{ color: '#000080' }}>二码:</span>
                          <span style={{ color: '#FF0000', fontSize: 22 }} dangerouslySetInnerHTML={{
                            __html: allNums.slice(0, 2).map(hc).join('.')
                          }} />
                        </td>
                      </tr>
                      <tr>
                        <td width="45%" style={{ backgroundColor: '#F4F4F4', textAlign: 'left', paddingLeft: 8 }}>
                          <span style={{ color: '#000080' }}>四肖:</span>
                          <span style={{ color: '#FF0000', fontSize: 26 }} dangerouslySetInnerHTML={{
                            __html: zodiacs.slice(0, 4).map(hz).join('')
                          }} />
                        </td>
                        <td style={{ backgroundColor: '#F4F4F4', textAlign: 'left', paddingLeft: 8 }}>
                          <span style={{ color: '#000080' }}>四码:</span>
                          <span style={{ color: '#FF0000', fontSize: 26 }} dangerouslySetInnerHTML={{
                            __html: allNums.slice(0, 4).map(hc).join('.')
                          }} />
                        </td>
                      </tr>
                      <tr>
                        <td width="45%" style={{ backgroundColor: '#F4F4F4', textAlign: 'left', paddingLeft: 8 }}>
                          <span style={{ color: '#000080' }}>七肖:</span>
                          <span style={{ color: '#FF0000', fontSize: 22 }} dangerouslySetInnerHTML={{
                            __html: zodiacs.map(hz).join('')
                          }} />
                        </td>
                        <td style={{ backgroundColor: '#F4F4F4', textAlign: 'left', paddingLeft: 8 }}>
                          <span style={{ color: '#000080' }}>七码:</span>
                          <span style={{ color: '#FF0000', fontSize: 22 }} dangerouslySetInnerHTML={{
                            __html: allNums.map(hc).join('.')
                          }} />
                        </td>
                      </tr>
                      <tr>
                        <td colSpan={2} style={{ textAlign: 'center', background: '#CCFFCC' }}>
                          台湾六合彩论坛是您人生成功的第一步
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 六尾中特（bzlx 三列表格） =====================

/**
 * 六尾中特（mechanism_key=legacy_6wei）
 * ---------------------------------------------------------------
 * 匹配旧站 6w.js 的三列表格布局
 */
export function LiuweiSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾必中六尾</div>
      <table width="100%" border={1} className="bzlx">
        <tbody>
          {module.history.map((row, idx) => {
            let tailDisplay = row.prediction_text
            try {
              const rawContent = (row.raw?.content as string) || row.prediction_text
              const parsed = JSON.parse(rawContent)
              if (Array.isArray(parsed)) {
                tailDisplay = parsed
                  .map((item: string) => item.split('|')[0].split('')[0])
                  .filter(Boolean)
                  .join('-')
              }
            } catch { /* already plain text */ }

            return (
              <tr key={`6w-${idx}`}>
                <td className="td1" height="23">{row.issue}</td>
                <td className="td2" height="23">{tailDisplay}</td>
                <td className="td3" height="23">{row.result_text}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 工具函数：生肖高亮 =====================

/** 对匹配生肖的字符做黄色高亮 */
function h(content: string, resSx: string): string {
  if (!resSx) return content
  const sxList = resSx.split(",").filter(Boolean).map(s => s.trim())
  const matchSet = new Set(sxList)
  return content.split("").map(c => ZODIAC_SET.has(c) && matchSet.has(c)
    ? `<span class="highlight">${c}</span>` : c).join("")
}

/** 对匹配生肖和号码做黄色高亮（用于逗号分隔的内容如"龙,鸡"） */
function hList(content: string, resSx: string, resCode: string): string {
  const sxList = (resSx || "").split(",").filter(Boolean).map(s => s.trim())
  const codeList = (resCode || "").split(",").filter(Boolean).map(s => s.trim())
  const matchSx = new Set(sxList)
  const matchCode = new Set(codeList)
  return content.split(",").map(part => {
    const trimmed = part.trim()
    // Check if this part matches a zodiac
    if (trimmed.length <= 2 && [...trimmed].some(c => ZODIAC_SET.has(c) && matchSx.has(c))) {
      return `<span class="highlight">${trimmed}</span>`
    }
    // Check if this part matches a code
    if (matchCode.has(trimmed) || matchCode.has(trimmed.padStart(2, '0'))) {
      return `<span class="highlight">${trimmed}</span>`
    }
    return trimmed
  }).join(",")
}

// ===================== 五肖中特（5xiao.js）=====================
// 旧站格式：{term}期: 五肖中特 ╠{5zodiacs}╣ 开{result}准
// 颜色：标签teal(#008080) 内容magenta(#FF00FF) 结果blue(#0000FF)
function WxztSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾五肖中特</div>
      <table border={1} width="100%" className="ptyx11" cellSpacing={0} cellPadding={2}>
        <tbody>
          {module.history.map((row, idx) => (
            <tr key={`wxzt-${idx}`}>
              <td>
                <span className="blue-text">{row.issue}:</span>
                <span style={{ color: '#008080', fontWeight: 'bold' }}>五肖中特</span>
                <span style={{ color: '#FF00FF', fontWeight: 'bold' }}>╠{row.prediction_text}╣</span>
                <span style={{ color: '#0000FF' }}> 开{row.result_text}</span>准
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 九肖中特（9xiao.js）=====================
// 旧站格式：{term}期 【{9zodiacs}】 开{result}准
// 颜色：内容green(#008000) 结果red(#FF0000)
function JxztSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾九肖中特</div>
      <table border={1} width="100%" className="ptyx11" cellSpacing={0} cellPadding={2}>
        <tbody>
          {module.history.map((row, idx) => (
            <tr key={`jxzt-${idx}`}>
              <td>
                <span className="black-text">{row.issue}期</span>
                <span style={{ color: '#008000', fontWeight: 'bold' }}>【{row.prediction_text}】</span>
                <span style={{ color: '#FF0000' }}> 开{row.result_text}</span>准
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 大小中特带头数（dx.js）=====================
// 旧站格式：{term}期: 大数小数 【{内容+头}】 开{result}
function Dxztt1Section({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾大小中特</div>
      <table border={1} width="100%" className="ptyx11" cellSpacing={0} cellPadding={2}>
        <tbody>
          {module.history.map((row, idx) => (
            <tr key={`dxztt1-${idx}`}>
              <td>
                <span className="blue-text">{row.issue}:</span>
                <span className="black-text">大数小数</span>
                <span className="zl" dangerouslySetInnerHTML={{
                  __html: h(row.prediction_text, row.raw?.res_sx as string || "")
                }} />
                <span> 开{row.result_text}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 四季生肖（cxqd.js）=====================
// 旧站格式：{term}期: 四季生肖 【{seasons}】 开{result}准
// 页脚显示：春肖:兔虎龙 夏肖:羊蛇马 秋肖:狗鸡猴 冬肖:猪牛鼠
function SjsxSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾四季生肖</div>
      <table border={1} width="100%" className="ptyx11" cellSpacing={0} cellPadding={2}>
        <tbody>
          {module.history.map((row, idx) => (
            <tr key={`sjsx-${idx}`}>
              <td>
                <span className="blue-text">{row.issue}:</span>
                <span className="blue-text">四季生肖</span>
                <span style={{ color: '#FF0000', fontWeight: 'bold' }}>
                  【{row.prediction_text}】
                </span>
                <span> 开{row.result_text}准</span>
              </td>
            </tr>
          ))}
          <tr>
            <td style={{ fontSize: 14 }}>
              春肖:兔虎龙 夏肖:羊蛇马 秋肖:狗鸡猴 冬肖:猪牛鼠
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

// ===================== 肉菜草肖（crc.js）=====================
// 旧站格式：{term}期: 肉菜草肖 【{categories}】 开{result}准
function RccxSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾肉菜草肖</div>
      <table border={1} width="100%" className="ptyx11" cellSpacing={0} cellPadding={2}>
        <tbody>
          {module.history.map((row, idx) => (
            <tr key={`rccx-${idx}`}>
              <td>
                <span className="blue-text">{row.issue}:</span>
                <span className="blue-text">肉菜草肖</span>
                <span style={{ color: '#FF0000', fontWeight: 'bold' }}>
                  【{row.prediction_text}】
                </span>
                <span> 开{row.result_text}准</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 买啥开啥 / 单双（015maishazs.js）=====================
// 旧站格式：第{term}期: | 单数单数单数(蓝色zl) | 开{result}
function DanshuangSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾六合彩论坛『买啥开啥』</div>
      <table border={1} width="100%" className="duilianpt1" cellSpacing={0} cellPadding={2}>
        <tbody>
          {module.history.map((row, idx) => (
            <tr key={`danshuang-${idx}`}>
              <td style={{ width: '30%', textAlign: 'center', fontWeight: 'bold' }}>
                第{row.issue}:
              </td>
              <td style={{ textAlign: 'center' }}>
                <span className="zl" style={{ color: '#0000FF' }}>
                  {row.prediction_text}
                </span>
              </td>
              <td style={{ width: '25%', textAlign: 'center' }}>
                开{row.result_text}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 单双四肖（031dssx.js）=====================
// 旧站格式：{term}期: [单：4肖][双：4肖] 开:{result}准
function DssxSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾六合彩→【单双四肖】→</div>
      <table border={1} width="100%" className="duilianpt1" cellSpacing={0} cellPadding={2}>
        <tbody>
          {module.history.map((row, idx) => (
            <tr key={`dssx-${idx}`}>
              <td>
                <span className="black-text">{row.issue}:</span>
                <span style={{ color: '#3f7ee8', fontWeight: 'bold' }}>
                  [单：{row.prediction_text}]
                </span>
                <span> 开:{row.result_text}准</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 黑白无双（035hblx.js）=====================
// 旧站格式：表头"特邀高手→【黑白无双】→全新上线"
// 每行：{term}期: →黑:3肖 白:3肖 开:{result}
function HblxSection({ module }: { module: PublicModule }) {
  // 黑肖 / 白肖 映射（来自 fixed_data）
  const BLACK_ZODIACS = "兔,龙,蛇,马,羊,猴"
  const WHITE_ZODIACS = "鼠,牛,虎,鸡,狗,猪"

  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">特邀高手→【黑白无双】→全新上线</div>
      <table border={1} width="100%" className="duilianpt1" cellSpacing={0} cellPadding={2}>
        <tbody>
          {/* 黑/白生肖映射表头 */}
          <tr>
            <td>
              <span className="zl">黑:{BLACK_ZODIACS} / 白:{WHITE_ZODIACS}</span>
            </td>
          </tr>
          {module.history.map((row, idx) => {
            const predText = row.prediction_text
            const resSx = String(row.raw?.res_sx || "")
            // Add yellow highlight on matched zodiacs in the prediction text
            let highlighted = predText
            if (resSx) {
              const matchSx = new Set(resSx.split(",").map(s => s.trim()))
              highlighted = predText.split("").map(c =>
                ZODIAC_SET.has(c) && matchSx.has(c)
                  ? `<span class="highlight">${c}</span>` : c
              ).join("")
            }
            return (
              <tr key={`hblx-${idx}`}>
                <td>
                  <span className="blue-text">{row.issue}:</span>
                  <span className="zl" dangerouslySetInnerHTML={{ __html: `→${highlighted}` }} />
                  <span> 开:{row.result_text}准</span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 春夏秋冬（032cxqd.js） =====================
// 完整版：表头显示季节生肖映射，行显示预测季节（高亮命中季节）
// content: JSON ["春|兔虎龙","夏|羊蛇马","秋|狗鸡猴","冬|猪牛鼠"] 或部分
function CxqdSection({ module }: { module: PublicModule }) {
  const seasonMap = { "春":"兔虎龙", "夏":"羊蛇马", "秋":"狗鸡猴", "冬":"猪牛鼠" }
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾六合彩→<span className="legacy-red">【</span>春夏秋冬<span className="legacy-red">】</span>→</div>
      <table border={1} width="100%" className="duilianpt1" bgcolor="#ffffff" cellSpacing={0} cellPadding={2}>
        <tbody>
          <tr>
            <td><span className="zl">春:兔虎龙　夏:羊蛇马<br/>秋:狗鸡猴　冬:猪牛鼠</span></td>
          </tr>
          {module.history.map((row, idx) => {
            const resSx = (row.raw?.res_sx as string || "")
            const lastSx = resSx.split(",").filter(Boolean).pop() || ""
            // Parse content: JSON array ["春|...","夏|...",...]
            let seasons = row.prediction_text
            try {
              const parsed = JSON.parse(String(row.raw?.content || row.prediction_text))
              if (Array.isArray(parsed)) {
                seasons = parsed.map((item: string) => {
                  const p = item.split('|')
                  const s = p[0].split('')[0]
                  // Yellow highlight if drawn zodiac matches this season's codes
                  if (lastSx && p[1] && (String(p[1]).includes(lastSx) || String(seasonMap[s as keyof typeof seasonMap] || "").includes(lastSx))) {
                    return `<span class="highlight">${s}</span>`
                  }
                  return s
                }).join('')
              }
            } catch { /* plain text */ }
            return (
              <tr key={`cxqd-${idx}`}>
                <td>
                  <span className="black-text">{row.issue}:</span>
                  <span className="blue-text">春夏秋冬→<span className="zl" dangerouslySetInnerHTML={{ __html: seasons }} /></span>
                  <span> 开:{row.result_text}准</span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 肉菜草（033rcc.js） =====================
// 完整版：表头肉菜草生肖映射，行显示"吃{X}"（命中高亮）
function RccxOriginalSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾六合彩→<span className="legacy-red">【</span>肉菜草<span className="legacy-red">】</span>→</div>
      <table border={1} width="100%" className="duilianpt1" bgcolor="#ffffff" cellSpacing={0} cellPadding={2}>
        <tbody>
          <tr>
            <td><span className="zl">肉肖:鼠牛虎兔龙蛇 菜肖:马羊猴鸡<br/>草肖:狗猪</span></td>
          </tr>
          {module.history.map((row, idx) => {
            let display = row.prediction_text
            try {
              const raw = String(row.raw?.content || "")
              const parsed = JSON.parse(raw)
              if (Array.isArray(parsed)) {
                display = parsed.map((item: string) => {
                  const p = item.split('|')
                  const cat = p[0].split('')[0]
                  return `吃${cat}`
                }).join('')
              }
            } catch { /* use prediction_text as-is */ }
            return (
              <tr key={`rccx-${idx}`}>
                <td>
                  <span className="black-text">{row.issue}:</span>
                  <span className="blue-text">肉菜草→{display}</span>
                  <span> 开:{row.result_text}</span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 精选九肖（008jxym.js） =====================
// 最复杂的之一：每期 9 行（①肖→⑨肖），qxtable yxym 三列表格
// content: JSON ["猴|46","龙|14",...] — 每项 "zodiac|code_list"
function JxymSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">名震全坛【台湾六合彩论坛 】等您来看</div>
      <table border={1} width="100%" cellPadding={0} cellSpacing={0} className="qxtable yxym" bgcolor="#FFFFFF">
        <tbody>
          {module.history.map((row, idx) => {
            // Parse content: JSON array ["猴|46","龙|14",...]
            let zodiacs: string[] = []
            let allCodes: string[] = []
            try {
              const raw = String(row.raw?.content || row.prediction_text)
              const parsed = JSON.parse(raw)
              if (Array.isArray(parsed)) {
                zodiacs = parsed.map((item: string) => item.split('|')[0])
                allCodes = parsed.flatMap((item: string) => (item.split('|')[1] || '').split(',').filter(Boolean))
              }
            } catch { /* use as-is */ }

            const resSx = String(row.raw?.res_sx || "").split(",").filter(Boolean)
            const resCode = String(row.raw?.res_code || "").split(",").filter(Boolean)
            const lastSx = resSx[resSx.length - 1] || "？"
            const lastCode = resCode[resCode.length - 1] || "00"

            // Build zodiac strings with yellow highlight
            const hzodiacs = (n: number) =>
              zodiacs.slice(0, n).map(z => {
                if (resSx.some(sx => sx.trim() === z)) return `<span class="highlight">${z}</span>`
                return z
              }).join('')

            // Build code string with highlight (normalize to 2-digit for matching)
            const resCodeNorm = new Set(resCode.map(s => s.trim().padStart(2, '0')))
            const hcodes = allCodes.slice(0, 12).map(c => {
              const cn = String(c).trim().padStart(2, '0')
              return resCodeNorm.has(cn) ? `<span class="highlight">${c}</span>` : c
            }).join(',')

            return (
              <tr key={`jxym-${idx}`}>
                <td colSpan={3} style={{ padding: 0 }}>
                  <table width="100%" cellPadding={0} cellSpacing={0} style={{ borderCollapse: 'collapse' }}>
                    <tbody>
                      {/* 精选: 号码行 */}
                      <tr>
                        <td colSpan={3} style={{ background: '#f7f7f7', color: '#FF0000', textAlign: 'center', padding: '4px 8px' }}>
                          <span className="jx" dangerouslySetInnerHTML={{ __html: `精选：${hcodes}` }} />
                        </td>
                      </tr>
                      {/* ①肖 行（特殊格式：规律-生肖-统计） */}
                      <tr>
                        <td style={{ background: '#d4eae9', width: '26%', textAlign: 'center' }}>
                          {row.issue}:①肖
                        </td>
                        <td style={{ background: '#f7f7f7', width: '56%', textAlign: 'center', color: '#FF0000', fontSize: 28 }}>
                          <span style={{ color: '#000000' }}>规律-</span>
                          <span style={{ fontSize: '22pt' }} dangerouslySetInnerHTML={{
                            __html: zodiacs[0]
                              ? (resSx.some(sx => sx.trim() === zodiacs[0])
                                  ? `<span class="highlight">${zodiacs[0]}</span>`
                                  : zodiacs[0])
                              : ''
                          }} />
                          <span style={{ color: '#000000' }}>-统计</span>
                        </td>
                        <td style={{ background: '#d4eae9', width: '18%', textAlign: 'center' }}>
                          {lastSx}{lastCode}中
                        </td>
                      </tr>
                      {/* ②肖 ③肖 ⑤肖 ⑦肖 ⑨肖 行 */}
                      {[2, 3, 5, 7, 9].map(n => (
                        <tr key={`${idx}-${n}`}>
                          <td style={{ background: '#d4eae9', textAlign: 'center' }}>
                            {row.issue}:{["","","②","③","","⑤","","⑦","","⑨"][n]}肖
                          </td>
                          <td style={{ background: '#f7f7f7', textAlign: 'center', color: '#FF0000', fontSize: 28 }}
                              dangerouslySetInnerHTML={{ __html: hzodiacs(n) }} />
                          <td style={{ background: '#d4eae9', textAlign: 'center' }}>
                            {lastSx}{lastCode}中
                          </td>
                        </tr>
                      ))}
                      {/* 页脚广告 */}
                      <tr>
                        <td colSpan={3} style={{ textAlign: 'center' }}>
                          台湾六合彩论坛 ,让赚钱的节奏停不下来
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 欲钱解特（011yqjt.js） =====================
// 文本格式：多行诗句，蓝/品红颜色
function YqjtSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾六合彩论坛『欲钱解特』</div>
      <table border={1} width="100%" className="duilianpt1 legacy-module-text" bgcolor="#ffffff" cellSpacing={0} cellPadding={2}>
        <tbody>
          {module.history.map((row, idx) => {
            const result = row.result_text.replace("待开奖", "？00")
            return (
              <tr key={`yqjt-${idx}`}>
                <td>
                  <div style={{ color: '#0000FF', fontWeight: 'bold', marginBottom: 4 }}>
                    {row.issue}：欲钱买特码【开{result}】
                  </div>
                  {row.prediction_text.split('\n').filter(Boolean).map((line, li) => (
                    <div key={li} style={{ color: '#000000', fontWeight: 'bold', lineHeight: 1.6 }}>
                      {line}
                    </div>
                  ))}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 一句真言（028sj.js） =====================
// 两行/期：黄底标题 + 白底解释，绿色文字
function YjzySection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾六合彩论坛『一句真言 』</div>
      <table border={1} width="100%" className="duilianpt1" bgcolor="#ffffff" cellSpacing={0} cellPadding={2}>
        <tbody>
          {module.history.map((row, idx) => {
            const raw = row.raw || {}
            const title = String(raw.title || "")
            const content = row.prediction_text
            const result = row.result_text.replace("待开奖", "？00")
            return (
              <tr key={`yjzy-${idx}`}>
                <td style={{ padding: 0 }}>
                  <table width="100%" cellPadding={4} cellSpacing={0}>
                    <tbody>
                      <tr style={{ backgroundColor: '#FFFFCC' }}>
                        <td style={{ color: '#008000', fontWeight: 'bold', fontSize: '14pt' }}>
                          {row.issue}一句真言：{title}
                        </td>
                      </tr>
                      <tr>
                        <td style={{ color: '#008000', lineHeight: 1.6 }}>
                          真言解释：{content}<br/>
                          开奖结果：{result}准
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 特段（016teduan.js） =====================
function TeduanSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾六合彩论坛『特码段数』</div>
      <table border={1} width="100%" className="duilianpt1" bgcolor="#ffffff" cellSpacing={0} cellPadding={2}>
        <tbody>
          {module.history.map((row, idx) => (
            <tr key={`teduan-${idx}`}>
              <td>
                <span className="blue-text">{row.issue}:开特码段【{row.prediction_text}】</span>
                <span> 开:{row.result_text}准</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 经典24码（019ma24.js） =====================
// 两行各12数字, {num.num...} 格式, duilianpt 类
function TemaSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾六合彩论坛（经典24码）</div>
      <table border={1} width="100%" className="duilianpt" bgcolor="#ffffff" cellSpacing={0} cellPadding={2}>
        <tbody>
          {module.history.map((row, idx) => {
            const codes = row.prediction_text.split(',').filter(Boolean)
            return (
              <tr key={`tema-${idx}`}>
                <td>
                  <span className="black-text">{row.issue}:《经典24码》开【{row.result_text}】</span>
                  <br/>
                  <span className="zl">{`{${codes.slice(0, 12).join('.')}}`}</span>
                  <br/>
                  <span className="zl">{`{${codes.slice(12).join('.')}}`}</span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 绝杀三肖（020ssx.js） =====================
// **特殊逻辑**：仅显示预测错误的行（drawn zodiac IS in kill list → SKIP row）
// 所以显示的是"杀对了"的行——即 drawn zodiac NOT in predicted list
function ShaxiaoSection({ module }: { module: PublicModule }) {
  const filteredRows = module.history.filter(row => {
    // Show row only if prediction was correct (kill succeeded = drawn zodiac NOT in content)
    return row.is_correct === false
  })
  if (filteredRows.length === 0) return null
  const modClone = { ...module, history: filteredRows }
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾六合彩→<span className="legacy-red">【</span>绝杀三肖<span className="legacy-red">】</span>→</div>
      <table border={1} width="100%" className="duilianpt1" bgcolor="#ffffff" cellSpacing={0} cellPadding={2}>
        <tbody>
          {modClone.history.map((row, idx) => (
            <tr key={`shaxiao-${idx}`}>
              <td>
                <span className="black-text">{row.issue}:</span>
                <span className="blue-text">绝杀→<span className="zl">[{row.prediction_text}]</span></span>
                <span> 开:{row.result_text}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 绝杀半波（022jsbb.js） =====================
// **特殊逻辑**：仅显示预测正确的行（kill succeeded）
function ShabanboSection({ module }: { module: PublicModule }) {
  const filteredRows = module.history.filter(row => row.is_correct === true)
  if (filteredRows.length === 0) return null
  const modClone = { ...module, history: filteredRows }
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾彩→<span className="legacy-red">【</span>绝杀半波<span className="legacy-red">】</span>→中中中</div>
      <table border={1} width="100%" className="duilianpt1" bgcolor="#ffffff" cellSpacing={0} cellPadding={2}>
        <tbody>
          {modClone.history.map((row, idx) => (
            <tr key={`shabanbo-${idx}`}>
              <td>
                <span className="black-text">{row.issue}:</span>
                <span className="blue-text">绝杀半波→<span className="zl">[{row.prediction_text}]</span></span>
                <span> 开:{row.result_text}准</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 三色生肖（026sssx.js） =====================
// 表头显示红蓝绿映射，行显示 [{color}肖]（命中高亮）
function SssxSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾六合彩→<span className="legacy-red">【</span>三色生肖<span className="legacy-red">】</span>→</div>
      <table border={1} width="100%" className="duilianpt1" bgcolor="#ffffff" cellSpacing={0} cellPadding={2}>
        <tbody>
          <tr>
            <td><span className="zl">红:马.兔.鼠.鸡 蓝:蛇.虎.猪.猴<br/>绿:羊.龙.牛.狗</span></td>
          </tr>
          {module.history.map((row, idx) => {
            let display = row.prediction_text
            try {
              const raw = String(row.raw?.content || "")
              const parsed = JSON.parse(raw)
              if (Array.isArray(parsed)) {
                const resSx = String(row.raw?.res_sx || "").split(",").filter(Boolean).pop() || ""
                display = parsed.map((item: string) => {
                  const p = item.split('|')
                  const color = p[0].replace('肖', '')
                  if (resSx && p[1] && String(p[1]).includes(resSx)) {
                    return `<span class="highlight">${color}</span>`
                  }
                  return color
                }).join('')
              }
            } catch { /* plain text */ }
            return (
              <tr key={`3ssx-${idx}`}>
                <td>
                  <span className="black-text">{row.issue}:</span>
                  <span style={{ color: '#2e88d4' }}>红蓝绿肖→<span className="zl" dangerouslySetInnerHTML={{ __html: `[${display}肖]` }} /></span>
                  <span> 开:{row.result_text}准</span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 琴棋书画（021qqsh.js） =====================
// 表头生肖映射，行显示预测的3/4艺术分类
function QqshSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">台湾六合彩→<span className="legacy-red">【</span>琴棋书画<span className="legacy-red">】</span>→</div>
      <table border={1} width="100%" className="duilianpt1" bgcolor="#ffffff" cellSpacing={0} cellPadding={2}>
        <tbody>
          <tr>
            <td><span className="zl">琴:兔蛇鸡　棋:鼠牛狗<br/>书:虎龙马　画:羊猴猪</span></td>
          </tr>
          {module.history.map((row, idx) => {
            // title: comma-separated art labels (e.g. "琴,棋,书")
            // content: comma-separated codes for each art
            let arts = row.prediction_text
            try {
              const rawTitle = String(row.raw?.title || "")
              const rawContent = String(row.raw?.content || row.prediction_text)
              const artLabels = rawTitle.split(',').filter(Boolean)
              const codes = rawContent.split(',').filter(Boolean)
              if (artLabels.length > 0 && codes.length > 0) {
                arts = artLabels.map((art, i) => {
                  const grpCodes = codes.slice(i*3, (i+1)*3)
                  const resSx = String(row.raw?.res_sx || "").split(",").filter(Boolean).pop() || ""
                  const artMap: Record<string, string> = { "琴":"兔蛇鸡", "棋":"鼠牛狗", "书":"虎龙马", "画":"羊猴猪" }
                  if (resSx && artMap[art]?.includes(resSx)) {
                    return `<span class="highlight">${art}</span>`
                  }
                  return art
                }).join('')
              }
            } catch { /* use as-is */ }
            return (
              <tr key={`qqsh-${idx}`}>
                <td>
                  <span className="black-text">{row.issue}:</span>
                  <span className="blue-text">琴棋书画→<span className="zl" dangerouslySetInnerHTML={{ __html: arts }} /></span>
                  <span> 开:{row.result_text}</span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 单双各四肖（ds4x.js） =====================
// 四列 sqbk 表格：期号 | 单:4肖 | 双:4肖 | 中:结果
function DsnxSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">单双各四肖</div>
      <table width="100%" border={1} className="sqbk">
        <tbody>
          {module.history.map((row, idx) => {
            const odd = String(row.raw?.xiao_1 || "")
            const even = String(row.raw?.xiao_2 || "")
            return (
              <tr key={`dsnx-${idx}`}>
                <td className="td1" height="20">{row.issue}<br/></td>
                <td><span style={{ color: '#0000FF' }}>单:{odd}</span></td>
                <td><span style={{ color: '#0000FF' }}>双:{even}</span></td>
                <td>中:<span style={{ color: '#FF0000' }}>开{row.result_text.replace(/^开:/, '').replace(/^开/, '')}</span></td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 跑马（tp5.js） =====================
// 最复杂：每期独立表格，含标题字 + 释义 + 综合七肖/五肖/三肖 + 主特号码
function PmxjczSection({ module }: { module: PublicModule }) {
  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <table width="100%" border={1} bgcolor="#ffffff" style={{ fontWeight: 'bold' }}>
        <tbody>
          <tr>
            <th>台湾梦影逍遥『跑马图』</th>
          </tr>
          {module.history.map((row, idx) => {
            const raw = row.raw || {}
            const title = String(raw.title || "")
            const content = String(raw.content || row.prediction_text).replace(/\n/g, '<br/>')
            const resSx = String(raw.res_sx || "").split(",").filter(Boolean).pop() || "？"
            const resCode = String(raw.res_code || "").split(",").filter(Boolean).pop() || "00"

            // Parse x7m14 field for zodiac/code predictions
            let zodiacs: string[] = []
            let codes: string[] = []
            try {
              const x7m14 = JSON.parse(String(raw.x7m14 || raw.content || '[]'))
              if (Array.isArray(x7m14)) {
                zodiacs = x7m14.map((item: string) => (item.split('|')[0] || '').split('')[0]).filter(Boolean)
                codes = x7m14.flatMap((item: string) => (item.split('|')[1] || '').split(',').filter(Boolean))
              }
            } catch {
              // fallback: use prediction_text
              zodiacs = row.prediction_text.split('').filter(c => ZODIAC_SET.has(c))
            }

            const hz = (n: number) => zodiacs.slice(0, n).join('')
            const hc = codes.join('.')

            return (
              <tr key={`pmxjcz-${idx}`}>
                <td style={{ margin: 0, padding: '3px 2px', wordBreak: 'break-all', textAlign: 'center', lineHeight: '26px' }}>
                  <p style={{ fontSize: '12pt', marginBottom: '8px', textAlign: 'left' }}>
                    <span style={{ fontFamily: '楷体', fontSize: '1.33em' }}>
                      <b>
                        <span style={{ color: '#800000' }}>
                          <span style={{ backgroundColor: '#C0C0C0' }}>{row.issue}跑马玄机测字</span>
                        </span>
                        <span style={{ color: '#FF0000' }}> 开{resSx}{resCode}准</span>
                      </b>
                    </span>
                    <b>
                      <span style={{ color: '#0000FF', fontFamily: '微软雅黑' }}><br/></span>
                      <span style={{ fontFamily: '微软雅黑' }}>
                        <span style={{ backgroundColor: '#FFFF00' }}>
                          <span style={{ color: '#FF0000', fontSize: '2em' }}>{title}</span>
                        </span>
                      </span>
                      <span style={{ fontFamily: '微软雅黑', color: '#0000FF' }}><br/></span>
                    </b>
                    <span style={{ color: '#0000FF' }}>
                      <span style={{ fontFamily: '微软雅黑' }}>
                        解：<span dangerouslySetInnerHTML={{ __html: content }} /><br/>
                      </span>
                    </span>
                    <span style={{ fontFamily: '微软雅黑' }}>
                      <b><br/></b>
                      <span>
                        <span style={{ color: '#800000', fontFamily: '微软雅黑' }}>综合七肖：{hz(7)}</span>
                        <span style={{ color: '#FF00FF', fontFamily: '微软雅黑' }}><br/></span>
                        <span style={{ color: '#800000', fontFamily: '微软雅黑' }}>综合五肖：{hz(5)}</span>
                        <span style={{ color: '#FF00FF', fontFamily: '微软雅黑' }}><br/></span>
                        <span style={{ color: '#800000', fontFamily: '微软雅黑' }}>综合三肖：{hz(3)}</span>
                        <span style={{ color: '#FF00FF', fontFamily: '微软雅黑' }}><br/></span>
                        <span style={{ color: '#800000', fontFamily: '微软雅黑' }}>主特：{hc}</span>
                      </span>
                    </span>
                    <b><span style={{ color: '#FF00FF', fontFamily: '微软雅黑', textIndent: '2em', fontSize: '16px' }} /></b>
                  </p>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ===================== 浅月流歌（wxbm.js） =====================
// 条件渲染：每期 8 行子预测，仅在命中或未开奖时显示
function WxbmSection({ module }: { module: PublicModule }) {
  const tdStyle: React.CSSProperties = {
    border: '1px solid #cccccc', margin: 0, padding: 5
  }

  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <table width="100%" border={1} style={{
        borderCollapse: 'collapse', fontWeight: 'bold', fontSize: 18,
        backgroundColor: '#fff', color: '#000', border: '0px none'
      }}>
        <thead>
          <tr>
            <th style={{ fontSize: 24, color: '#fff', padding: 5, background: 'rgb(255,102,102)' }}>
              <span style={{ fontWeight: 400 }}>浅月流歌</span>★一肖一码 独家火爆
            </th>
          </tr>
        </thead>
      </table>

      {module.history.map((row, idx) => {
        const raw = row.raw || {}
        const xiaoStr = String(raw.xiao || "")
        let xiaoList: string[] = []
        let codeList: string[] = []
        let pingZodiac = ""

        try {
          if (xiaoStr.startsWith("{")) {
            const obj = JSON.parse(xiaoStr)
            xiaoList = (obj.xiao || "").split(",").filter(Boolean)
            codeList = (obj.code || "").split(",").filter(Boolean)
            pingZodiac = obj.ping || ""
          }
        } catch { /* plain */ }

        if (xiaoList.length === 0) {
          xiaoList = row.prediction_text.split(",").filter(Boolean)
        }

        const resSx = String(raw.res_sx || "")
        const resCode = String(raw.res_code || "")
        const hasResult = !!resSx || !!resCode

        function hitsXs(items: string[]): boolean {
          if (!hasResult) return true
          const sxSet = new Set(resSx.split(",").map(s => s.trim()))
          return items.some(z => sxSet.has(z))
        }
        function hitsCs(items: string[]): boolean {
          if (!hasResult) return true
          const codeSet = new Set(resCode.split(",").map(s => s.trim()))
          return items.some(c => codeSet.has(c))
        }
        function hxz(zs: string[]): string {
          const sxSet = new Set(resSx.split(",").map(s => s.trim()))
          return zs.map(z => sxSet.has(z) ? `<span class="highlight">${z}</span>` : z).join("")
        }
        function hxc(cs: string[]): string {
          const codeSet = new Set(resCode.split(",").map(s => s.trim()))
          return cs.map(c => codeSet.has(c) ? `<span class="highlight">${c}</span>` : c).join(".")
        }

        const sections: React.ReactNode[] = []

        if (hitsXs(xiaoList)) {
          sections.push(
            <tr key={`s7-${idx}`}><td style={tdStyle}>
              <span style={{ color: '#0000FF', fontFamily: '微软雅黑' }}>{row.issue}七肖：</span>
              <span style={{ fontFamily: '微软雅黑' }} dangerouslySetInnerHTML={{ __html: hxz(xiaoList) }} />
            </td></tr>
          )
        }
        const xiao5 = xiaoList.slice(0, 5)
        if (hitsXs(xiao5)) {
          sections.push(
            <tr key={`s5-${idx}`}><td style={tdStyle}>
              <span style={{ color: '#0000FF', fontFamily: '微软雅黑' }}>{row.issue}五肖：</span>
              <span style={{ fontFamily: '微软雅黑' }} dangerouslySetInnerHTML={{ __html: hxz(xiao5) }} />
            </td></tr>
          )
        }
        const xiao3 = xiaoList.slice(0, 3)
        if (hitsXs(xiao3)) {
          sections.push(
            <tr key={`s3-${idx}`}><td style={tdStyle}>
              <span style={{ color: '#0000FF', fontFamily: '微软雅黑' }}>{row.issue}三肖：</span>
              <span style={{ fontFamily: '微软雅黑' }} dangerouslySetInnerHTML={{ __html: hxz(xiao3) }} />
            </td></tr>
          )
        }
        const xiao1 = xiaoList.slice(0, 1)
        if (hitsXs(xiao1)) {
          sections.push(
            <tr key={`s1-${idx}`}><td style={tdStyle}>
              <span style={{ color: '#0000FF', fontFamily: '微软雅黑' }}>{row.issue}一肖：</span>
              <span style={{ fontFamily: '微软雅黑' }} dangerouslySetInnerHTML={{ __html: hxz(xiao1) }} />
              <span style={{ fontFamily: '微软雅黑' }}>√</span>
            </td></tr>
          )
        }
        if (hitsCs(codeList)) {
          sections.push(
            <tr key={`c7-${idx}`}><td style={tdStyle}>
              <span style={{ color: '#0000FF', fontFamily: '微软雅黑' }}>{row.issue}八码：</span>
              <span style={{ fontFamily: '微软雅黑' }} dangerouslySetInnerHTML={{ __html: hxc(codeList) }} />
            </td></tr>
          )
        }
        const code5 = codeList.slice(0, 5)
        if (hitsCs(code5)) {
          sections.push(
            <tr key={`c5-${idx}`}><td style={tdStyle}>
              <span style={{ color: '#0000FF', fontFamily: '微软雅黑' }}>{row.issue}五码：</span>
              <span style={{ fontFamily: '微软雅黑' }} dangerouslySetInnerHTML={{ __html: hxc(code5) }} />
            </td></tr>
          )
        }
        if (pingZodiac && hitsXs([pingZodiac])) {
          sections.push(
            <tr key={`pt-${idx}`}><td style={tdStyle}>
              <span style={{ color: '#0000FF', fontFamily: '微软雅黑' }}>{row.issue}平特：</span>
              <span style={{ fontFamily: '微软雅黑' }}>
                {pingZodiac}{pingZodiac}{pingZodiac}
              </span>
            </td></tr>
          )
        }

        const finalZodiac = xiaoList[0] || ""
        const finalCode = codeList[0] || ""
        sections.push(
          <tr key={`ft-${idx}`}>
            <th style={{ margin: 0, padding: 5 }}>
              {row.issue}一肖一码：<span style={{ color: '#FF0000' }}>（{finalZodiac}{finalCode}）</span>跟者发财
            </th>
          </tr>
        )

        return (
          <table key={`wxbm-${idx}`} width="100%" border={1} style={{
            borderCollapse: 'collapse', fontWeight: 'bold', fontSize: 18,
            backgroundColor: '#fff', color: '#000', border: '0px none'
          }}>
            <tbody>{sections}</tbody>
          </table>
        )
      })}
    </div>
  )
}
