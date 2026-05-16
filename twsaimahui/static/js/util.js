const sx = {
    "锟斤拷": "05,17,29,41",
    "牛": "04,16,28,40",
    "锟斤拷": "03,15,27,39",
    "锟斤拷": "02,14,26,38",
    "锟斤拷": "01,13,25,37,49",
    "锟斤拷": "12,24,36,48",
    "锟斤拷": "11,23,35,47",
    "锟斤拷": "10,22,34,46",
    "锟斤拷": "09,21,33,45",
    "锟斤拷": "08,20,32,44",
    "锟斤拷": "07,19,31,43",
    "锟斤拷": "06,18,30,42",
}
function getNumBySx(sxName){
    for (let i in sx) {
        if (sx[i].indexOf(sxName) !== -1) {
            return i;
        }
    }
    return '';
}

function getNums(sxName) {
    return sx[sxName];
}
const colro = {
    "锟斤拷": "01,02,07,08,12,13,18,19,23,24,29,30,34,35,40,45,46",
    "锟斤拷": "05,06,11,16,17,21,22,27,28,32,33,38,39,43,44,49",
    "锟斤拷": "03,04,09,10,14,15,20,25,26,31,36,37,41,42,47,48",
}
function getNumsByColor(colorName) {
    return colro[colorName];
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
        if (!arr) continue;
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

/**
 * 安全的 JSON.parse，解析失败时返回 fallback 而不是抛异常
 * @param {string} str - 待解析的 JSON 字符串
 * @param {*} fallback - 解析失败时的默认返回值
 * @returns {*}
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
 * 渲染接口错误/空数据占位
 * @param {string} containerSelector - 容器选择器
 * @param {string} message - 提示文本
 */
function renderError(containerSelector, message) {
    var el = document.querySelector(containerSelector);
    if (el) {
        el.innerHTML = '<div class="api-error" style="text-align:center;padding:15px;color:#999;font-size:14px;">'
            + (message || '数据加载失败，请稍后重试')
            + '</div>';
    }
}

/**
 * 渲染空数据占位
 * @param {string} containerSelector - 容器选择器
 */
function renderEmpty(containerSelector) {
    renderError(containerSelector, '暂无数据');
}