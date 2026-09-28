 /**
 * 全局 API 配置常量
 * API_WEB — 所有 API 请求中使用的 web 参数默认值（站点标识）
 * 该常量集中管理，修改此值即可统一调整所有请求的 web 参数
 */
var API_WEB = 4;

sx = {
    "鼠": "05,17,29,41",
    "牛": "04,16,28,40",
    "虎": "03,15,27,39",
    "兔": "02,14,26,38",
    "龙": "01,13,25,37,49",
    "蛇": "12,24,36,48",
    "马": "11,23,35,47",
    "羊": "10,22,34,46",
    "猴": "09,21,33,45",
    "鸡": "08,20,32,44",
    "狗": "07,19,31,43",
    "猪": "06,18,30,42",
}
 function getNumBySx(sxName){
    for (let i in sx) {
        if (sx[i].indexOf(sxName) !== -1) {
            return i;
        }
    }
    return '';
}

 function getLocationSearch(){
    let search = window.location.search.replace('?','');
    let obj = {};
    search.split('&').forEach(item => {
        let split = item.split('=');
        obj[split[0]] = split[1];
    })
    return obj;
}

function getZjNum(str,array){
    for (let i = 0; i < array.length; i++) {
        let arr = array[i];
        if (str.indexOf(arr) !== -1) {
            return arr;
        }
    }
}
function getZjIndex(str,array){
    for (let i = 0; i < array.length; i++) {
        let arr = array[i];
        if (!arr) continue;
        if (str.indexOf(arr) !== -1) {
            return i;
        }
    }
}

 const colro = {
     "红": "01,02,07,08,12,13,18,19,23,24,29,30,34,35,40,45,46",
     "绿": "05,06,11,16,17,21,22,27,28,32,33,38,39,43,44,49",
     "蓝": "03,04,09,10,14,15,20,25,26,31,36,37,41,42,47,48",
 }
 function getNumsByColor(colorName) {
     return colro[colorName.trim()];
 }

/**
 * 安全的 JSON.parse：解析失败时返回 fallback 而不是抛异常。
 * 语义与 frontend/public/vendor/twsaimahui/static/js/util.js 的 safeParseJSON 一致。
 * @param {string} str - 待解析的 JSON 字符串
 * @param {*} fallback - 解析失败时的默认返回值（默认 []）
 */
function safeParseJSON(str, fallback) {
    if (typeof str !== 'string' || str === '') return fallback !== undefined ? fallback : [];
    try {
        return JSON.parse(str);
    } catch (e) {
        console.warn('JSON parse failed:', e.message);
        return fallback !== undefined ? fallback : [];
    }
}

/**
 * 兜底切分：把裸串还原成 `标签|值` 分组数组。只在 JSON.parse 失败时使用。
 * 覆盖 `家畜|04,16,28,40`、`金|10,11, 土|03,06`、`龙,牛,兔,羊`
 * 以及残缺 JSON（`[兔|04,16,马|11`）三种形态。
 */
function splitRawContent(raw) {
    var text = String(raw == null ? '' : raw)
        .replace(/^\s*\[/, '')
        .replace(/\]\s*$/, '')
        .replace(/"/g, '')
        .trim();
    if (!text) return [];

    var parts = text.split(',');
    var groups = [];
    for (var i = 0; i < parts.length; i++) {
        var token = parts[i].trim();
        if (!token) continue;
        if (token.indexOf('|') !== -1) {
            var at = token.indexOf('|');
            var label = token.substring(0, at).trim();
            var codes = token.substring(at + 1).trim();
            groups.push(codes ? label + '|' + codes : label);
        } else if (groups.length > 0 && groups[groups.length - 1].indexOf('|') !== -1) {
            // 没有 `|` 的片段是上一个分组的号码尾巴：`家畜|04,16,28,40`
            groups[groups.length - 1] = groups[groups.length - 1] + ',' + token;
        } else {
            groups.push(token);
        }
    }
    return groups;
}

/**
 * 把 legacy 的 `content` / `code` / `tou` 字段归一成 `["标签|值", ...]` 数组，
 * 永不抛异常。
 *
 * 正常路径与 JSON.parse 逐字等价：合法 JSON 数组逐项 String() 返回
 * （元素本来就是字符串，String(item) === item），页面输出不变。
 *
 * 只有 JSON.parse 会抛异常的输入才走兜底分支。后端同一个 content 列在不同
 * mode/期次上语义不同：`public.mode_payload_48` 是 `龙,牛,兔,羊` 这种逗号串，
 * `mode_payload_59` 是整段中文，取数层（frontend/app/api/kaijiang/[[...path]]/
 * route.ts 的 mapSimpleContent）原样透传、不做 JSON 归一。旧写法
 * `JSON.parse(d.content)` 在这类行上抛错，success 回调中断，整个模块容器
 * 保持空白（展示规范 S8 要防的「整块模块空白」）。
 *
 * 分支：
 *   1) 已经是数组：逐项 String() 返回；
 *   2) 带 `|` 的裸串：按 `,` 切开后把后续无 `|` 片段并回分组，重建 `标签|值`；
 *   3) 纯逗号串（`龙,牛,兔,羊`）：按 `,` 切成多个裸标签项；
 *   4) 残缺 JSON（`[兔|04,16,马|11`）：剥掉首尾 `[` `]` 与引号后按 2)/3) 处理；
 *   5) 取不到（null / 空串 / JSON 对象 / JSON 标量）：返回 []，
 *      调用方照常渲染该期行、候选区为空（空态），不再整块模块空白。
 */
function parseContentList(content) {
    if (content === null || content === undefined) return [];
    if (Object.prototype.toString.call(content) === '[object Array]') {
        return content.map(function (item) { return String(item); });
    }
    var raw = String(content).trim();
    if (!raw) return [];
    // JSON 对象：旧写法会在 for-in 里拿到属性名再 .split 抛错，这里按取不到处理
    if (raw.charAt(0) === '{') return [];

    var parsed;
    try {
        parsed = JSON.parse(raw);
    } catch (e) {
        return splitRawContent(raw);
    }
    if (Object.prototype.toString.call(parsed) === '[object Array]') {
        return parsed.map(function (item) { return String(item); });
    }
    // JSON 字符串 / 数字 / 布尔 / 对象：不是候选数组，按取不到处理
    return [];
}
