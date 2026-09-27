/*
 * legacy-prediction-verdict.js — tw8800（shengshi8800）legacy 页面的统一命中判定
 * ---------------------------------------------------------------------------
 * 背景：这些渲染脚本原来把「准」直接写在结果旁边（或使用内部写死「准」的
 * getResult()），无论预测对错都显示「准」。本文件提供**唯一**的判定实现，
 * 各渲染脚本只调用它，规则为：
 *
 *     verdictOf(modeId, row) -> 'ok' | 'miss' | 'pending' | 'unknown'
 *     命中 -> 显示「准」；未命中 -> 显示「错」；未开奖 -> 不显示判定
 *     无法判定（无预测值 / 文本类无法核对）-> 不显示判定
 *
 * 判定口径与后端一致的模块定义见 backend/docs/prediction-module-rules.md。
 * 只读取接口已返回的字段，不修改任何数据。
 */
(function (global) {
    'use strict';

    var ZODIAC = '鼠牛虎兔龙蛇马羊猴鸡狗猪';
    var COLOR_BY_CODE = (function () {
        var map = {};
        // 与库内 res_color 一致的标准六合彩波色分组（红 17 / 蓝 16 / 绿 16）
        var red = ['01', '02', '07', '08', '12', '13', '18', '19', '23', '24', '29', '30', '34', '35', '40', '45', '46'];
        var blue = ['03', '04', '09', '10', '14', '15', '20', '25', '26', '31', '36', '37', '41', '42', '47', '48'];
        var green = ['05', '06', '11', '16', '17', '21', '22', '27', '28', '32', '33', '38', '39', '43', '44', '49'];
        function put(list, name) {
            for (var i = 0; i < list.length; i++) map[list[i]] = name;
        }
        put(red, 'red');
        put(blue, 'blue');
        put(green, 'green');
        return map;
    })();

    function text(value) {
        return String(value == null ? '' : value);
    }

    function csv(value) {
        var raw = text(value).trim();
        if (!raw) return [];
        var out = [];
        var parts = raw.split(',');
        for (var i = 0; i < parts.length; i++) {
            var item = parts[i].trim();
            if (item) out.push(item);
        }
        return out;
    }

    function pad(value) {
        var raw = text(value).trim();
        if (!/^\d{1,2}$/.test(raw)) return '';
        var number = parseInt(raw, 10);
        if (!(number >= 1 && number <= 49)) return '';
        return (number < 10 ? '0' : '') + number;
    }

    function specialCode(row, resCode) {
        var codes = csv(resCode);
        return codes.length ? pad(codes[codes.length - 1]) : '';
    }

    function specialZodiac(row, code) {
        var zodiacs = csv(row && row.res_sx);
        if (zodiacs.length) return zodiacs[zodiacs.length - 1];
        var sx = text(row && row.sx).trim();
        return sx ? sx.charAt(0) : '';
    }

    /** 解析 `["标签|号码或生肖", ...]` 形态，返回 [{label, codes, pool, raw}]。
     *  - codes: 右侧可解析为号码的部分（用于号码判定）
     *  - pool : 右侧原始 token 列表（可能是号码，也可能是生肖）
     *  兼容纯字符串（CSV 或含 `|` 的单条）。
     */
    function groups(content) {
        var items = [];
        if (Object.prototype.toString.call(content) === '[object Array]') {
            items = content;
        } else if (content != null && text(content).trim() !== '') {
            var raw = text(content).trim();
            try {
                var parsed = JSON.parse(raw);
                if (Object.prototype.toString.call(parsed) === '[object Array]') {
                    items = parsed;
                } else if (parsed && typeof parsed === 'object') {
                    return [];
                } else {
                    items = raw.indexOf('|') !== -1 ? [raw] : csv(raw);
                }
            } catch (error) {
                items = raw.indexOf('|') !== -1 ? [raw] : csv(raw);
            }
        }
        var out = [];
        for (var i = 0; i < items.length; i++) {
            var item = text(items[i]).trim();
            if (!item) continue;
            if (item.indexOf('|') === -1) {
                // 不含 `|` 的条目：每个逗号项本身就是候选（波色名 / 生肖 / 号码）
                var tokens = item.split(',');
                for (var t = 0; t < tokens.length; t++) {
                    var tokenValue = tokens[t].trim();
                    if (!tokenValue) continue;
                    var onlyCode = pad(tokenValue);
                    out.push({
                        label: onlyCode ? '' : tokenValue,
                        codes: onlyCode ? [onlyCode] : [],
                        pool: [tokenValue],
                        raw: tokenValue,
                    });
                }
                continue;
            }
            var parts = item.split('|');
            var label = parts[0].trim();
            var codes = [];
            var pool = [];
            if (parts.length > 1) {
                var poolParts = parts[1].split(',');
                for (var j = 0; j < poolParts.length; j++) {
                    var token = poolParts[j].trim();
                    if (!token) continue;
                    pool.push(token);
                    var code = pad(token);
                    if (code) codes.push(code);
                }
            }
            out.push({ label: label, codes: codes, pool: pool, raw: item });
        }
        return out;
    }

    /** content 里出现的所有生肖（支持 CSV、`标签|生肖` 分组、纯文本嵌入）。 */
    function zodiacsOf(content) {
        var found = [];
        function push(zodiac) {
            if (zodiac && ZODIAC.indexOf(zodiac) !== -1 && found.indexOf(zodiac) === -1) found.push(zodiac);
        }
        var items = groups(content);
        if (items.length) {
            for (var i = 0; i < items.length; i++) {
                var pool = items[i].codes.length ? items[i].codes : items[i].label.split(',');
                for (var j = 0; j < pool.length; j++) {
                    var token = text(pool[j]).trim();
                    if (token.length === 1) push(token);
                    else {
                        for (var k = 0; k < token.length; k++) push(token.charAt(k));
                    }
                }
            }
            return found;
        }
        var raw = text(content);
        for (var index = 0; index < raw.length; index++) push(raw.charAt(index));
        return found;
    }

    function numberInGroups(groupList, code) {
        if (!code) return '';
        for (var i = 0; i < groupList.length; i++) {
            if (groupList[i].codes.indexOf(code) !== -1) return true;
        }
        return groupList.length ? false : '';
    }

    function zodiacInGroups(groupList, zodiac) {
        if (!zodiac) return '';
        var anyPool = false;
        for (var i = 0; i < groupList.length; i++) {
            var group = groupList[i];
            if (isZodiacToken(group.label)) {
                anyPool = true;
                if (group.label === zodiac) return true;
            }
            var pool = group.pool && group.pool.length ? group.pool : group.label.split(',');
            for (var j = 0; j < pool.length; j++) {
                var token = text(pool[j]).trim();
                if (!token) continue;
                anyPool = true;
                if (token === zodiac) return true;
            }
        }
        return anyPool ? false : '';
    }

    function hasAnyCode(groupList) {
        for (var i = 0; i < groupList.length; i++) {
            if (groupList[i].codes && groupList[i].codes.length) return true;
        }
        return false;
    }

    function hasAnyZodiac(groupList) {
        for (var i = 0; i < groupList.length; i++) {
            var group = groupList[i];
            // 生肖可能写在标签里（如 `["狗|09"]`），也可能写在池里（如 `["家禽|牛,狗,猪"]`）
            if (isZodiacToken(group.label)) return true;
            var pool = group.pool && group.pool.length ? group.pool : group.label.split(',');
            for (var j = 0; j < pool.length; j++) {
                if (isZodiacToken(pool[j])) return true;
            }
        }
        return false;
    }

    function isZodiacToken(value) {
        var token = text(value).trim();
        return token.length === 1 && ZODIAC.indexOf(token) !== -1;
    }

    function verdictFromBoolean(value) {
        if (value === '') return 'unknown';
        return value ? 'ok' : 'miss';
    }

    function sizeLabel(code) {
        return code ? (parseInt(code, 10) >= 25 ? '大' : '小') : '';
    }

    function parityLabel(code) {
        if (!code) return '';
        return parseInt(code, 10) % 2 === 1 ? '单' : '双';
    }

    function labelInContent(groupList, label) {
        for (var i = 0; i < groupList.length; i++) {
            if (groupList[i].label.indexOf(label) === 0) return true;
        }
        return false;
    }

    /** 半波（mode 58）：候选是「红单」「蓝双」这类标签，按标签判定。 */
    function halfWaveByLabel(groupList, code) {
        var color = COLOR_BY_CODE[code];
        if (!color) return 'pending';
        var parity = parityLabel(code);
        var wanted = { red: '红', blue: '蓝', green: '绿' }[color] + parity;
        var labels = [];
        for (var i = 0; i < groupList.length; i++) {
            if (groupList[i].label) labels.push(groupList[i].label);
        }
        if (!labels.length) return 'unknown';
        for (var j = 0; j < labels.length; j++) {
            if (labels[j].indexOf(wanted) === 0) return 'ok';
        }
        return 'miss';
    }

    /**
     * 统一判定入口。
     * @param {number} modeId  后端 modes_id
     * @param {object} row     接口行（含 content / res_code / res_sx 等）
     * @param {string} [resCode] 显式指定开奖号码（不传则取 row.res_code）
     */
    function verdictOf(modeId, row, resCode) {
        row = row || {};
        modeId = parseInt(modeId, 10) || 0;
        var code = specialCode(row, resCode == null ? row.res_code : resCode);
        var zodiac = specialZodiac(row, code);
        var content = row.content;
        var groupList = groups(content);
        var needsDraw = modeId !== 331 && modeId !== 244 && modeId !== 62 && modeId !== 17;

        if (needsDraw && !code) return 'pending';

        switch (modeId) {
            // ── 号码池 / 生肖池：按数据实际维度判定 ───────────────
            // 维度判定顺序很重要：
            //   1) 池里出现生肖 -> 以「特码生肖是否在候选生肖里」为准
            //      （如 8肖中特 `["狗|09"]`、9肖中特、四肖八码，号码只是配码）
            //   2) 否则池里出现号码 -> 以「特码是否在候选号码里」为准
            //   3) 都没有 -> 退回类别标签（半波/波色）
            case 3:
            case 5:
            case 8:
            case 12:
            case 20:
            case 26:
            case 42:
            case 43:
            case 46:
            case 48:
            case 49:
            case 51:
            case 53:
            case 54:
            case 56:
            case 58:
            case 61:
            case 63:
            case 151:
            case 197: {
                var hasZodiac = hasAnyZodiac(groupList);
                var hasCode = hasAnyCode(groupList);
                if (hasZodiac && zodiac && zodiacInGroups(groupList, zodiac) === true) return 'ok';
                if (hasCode && code && numberInGroups(groupList, code) === true) return 'ok';
                if (hasZodiac || hasCode) return 'miss';
                if (modeId === 58) return halfWaveByLabel(groupList, code);
                return 'unknown';
            }
            case 34: {
                var numbers = csv(content);
                if (!numbers.length) return 'unknown';
                var padded = [];
                for (var n = 0; n < numbers.length; n++) {
                    var value = pad(numbers[n]);
                    if (value) padded.push(value);
                }
                return verdictFromBoolean(padded.indexOf(code) !== -1);
            }
            // ── 单双 / 大小 ───────────────────────────────────────
            case 28: {
                var parity = parityLabel(code);
                if (!parity) return 'pending';
                if (!labelInContent(groupList, '单') && !labelInContent(groupList, '双')) return 'unknown';
                return labelInContent(groupList, parity) ? 'ok' : 'miss';
            }
            case 57:
            case 108: {
                var size = sizeLabel(code);
                if (!size) return 'pending';
                if (!labelInContent(groupList, '大') && !labelInContent(groupList, '小')) return 'unknown';
                return labelInContent(groupList, size) ? 'ok' : 'miss';
            }
            // ── 波色 / 半波 ───────────────────────────────────────
            case 38: {
                var color = COLOR_BY_CODE[code];
                if (!color) return 'pending';
                var waves = [];
                for (var w = 0; w < groupList.length; w++) {
                    if (groupList[w].label) waves.push(groupList[w].label);
                }
                if (!waves.length) waves = csv(content);
                if (!waves.length) return 'unknown';
                var name = { red: '红波', blue: '蓝波', green: '绿波' }[color];
                return waves.indexOf(name) !== -1 ? 'ok' : 'miss';
            }
            // 58 已在号码池分支处理（有号码池按号码，否则按半波标签）
            // ── 双组生肖（单双四肖 / 黑白各三肖）──────────────────
            case 31: {
                var one = csv(row.xiao_1);
                var two = csv(row.xiao_2);
                if (!one.length && !two.length) return 'unknown';
                if (!zodiac) return 'pending';
                return (one.indexOf(zodiac) !== -1 || two.indexOf(zodiac) !== -1) ? 'ok' : 'miss';
            }
            case 45: {
                var hei = csv(row.hei);
                var bai = csv(row.bai);
                if (!hei.length && !bai.length) return 'unknown';
                if (!zodiac) return 'pending';
                return (hei.indexOf(zodiac) !== -1 || bai.indexOf(zodiac) !== -1) ? 'ok' : 'miss';
            }
            // ── 生肖落在文本里 ───────────────────────────────────
            case 50: {
                var jiexi = text(row.jiexi);
                var pool50 = jiexi ? zodiacsOf(jiexi) : zodiacsOf(content);
                if (!pool50.length) return 'unknown';
                if (!zodiac) return 'pending';
                return pool50.indexOf(zodiac) !== -1 ? 'ok' : 'miss';
            }
            case 52: {
                var chars = text(row.jiexi);
                if (!chars) return 'unknown';
                if (!zodiac) return 'pending';
                return chars.indexOf(zodiac) !== -1 ? 'ok' : 'miss';
            }
            case 331: {
                var pool331 = zodiacsOf(row.jiexi || row.content);
                if (!pool331.length) return 'unknown';
                if (!zodiac) return 'pending';
                return pool331.indexOf(zodiac) !== -1 ? 'ok' : 'miss';
            }
            // ── 段位 ─────────────────────────────────────────────
            case 65: {
                var segments = csv(content);
                if (!segments.length) return 'unknown';
                if (!code) return 'pending';
                var first = pad(segments[0]);
                var last = pad(segments[segments.length - 1]);
                if (!first || !last) return 'unknown';
                var value = parseInt(code, 10);
                return (value >= parseInt(first, 10) && value <= parseInt(last, 10)) ? 'ok' : 'miss';
            }
            // ── 文本类无法核对：不显示判定 ───────────────────────
            case 59:
            case 62:
            case 17:
            case 244:
            default:
                return 'unknown';
        }
    }

    /** 命中 -> '准'；未命中 -> '错'；待开奖/无法判定 -> ''（按需求不显示）。 */
    function verdictText(verdict) {
        if (verdict === 'ok') return '准';
        if (verdict === 'miss') return '错';
        return '';
    }

    function verdictHit(verdict) {        return verdict === 'ok';
    }

    global.legacyPredictionVerdict = {
        verdictOf: verdictOf,
        verdictText: verdictText,
        verdictHit: verdictHit,
        groups: groups,
        zodiacsOf: zodiacsOf,
        specialCode: specialCode,
        specialZodiac: specialZodiac,
    };
})(typeof window !== 'undefined' ? window : this);
