// 特邀家野两肖 (使用统一请求工具 + safeParseJSON)
//
// 数据来源：`/api/kaijiang/getJyxiao2` → mode 251「家野两肖」。
//   content = `["家禽|牛,马,羊,鸡,狗,猪"]`（组名|组成员，来自后端 title 列）
//   xiao    = 两肖（字段语义宽度 2，例如 `蛇,龙`）
// 展示口径（见 docs/prediction-display-standard.md）：
//   【组名+两肖】；命中 = 特肖 ∈ 组成员 ∪ 两肖；
//   命中项高亮（命中的是两肖里的某一个 → 高亮该生肖；命中的是组内成员 → 高亮组名），
//   未命中的一律不高亮；未开奖显示「开:待开奖」，不显示判定也不高亮。
//
// 家禽/野兽的固定分组以 `public.fixed_data`（sign='家禽|野兽'，id 16/17，status=1）为准，
// 接口没带回组成员时用它兜底。
var JYXIAO2_FIXED_GROUPS = {
    '家禽': '牛,马,羊,鸡,狗,猪',
    '野兽': '鼠,虎,兔,龙,蛇,猴'
};

var jyxiao2SplitCsv = function (value) {
    return String(value === null || value === undefined ? '' : value)
        .split(',')
        .map(function (item) { return item.trim(); })
        .filter(function (item) { return item !== ''; });
};

window.apiClient.get('/api/kaijiang/getJyxiao2', { web: window.web, type: window.type, num: '2' })
    .done(function (response) {
        var htmlBoxList = '';
        var data = response.data;
        if (!data || !data.length) {
            renderEmpty('.l1');
            return;
        }
        for (var i = 0; i < data.length; i++) {
            var d = data[i];
            var codeSplit = jyxiao2SplitCsv(d.res_code);
            var sxSplit = jyxiao2SplitCsv(d.res_sx);
            // 特码/特肖都是开奖串的最后一项（与 012liuxiao.js / shengshi8800 023sqzt.js 同口径）。
            var code = codeSplit[codeSplit.length - 1] || '';
            var sx = sxSplit[sxSplit.length - 1] || '';
            var opened = !!(code && sx);

            var groupName = '';
            var groupMembers = [];
            var pair = jyxiao2SplitCsv(d.xiao);
            var content = safeParseJSON(d.content, []);
            for (var j = 0; j < content.length; j++) {
                var item = String(content[j] === null || content[j] === undefined ? '' : content[j]);
                var c = item.split('|');
                var left = String(c[0] || '').trim();
                if (!left) continue;
                // `组名|组成员`（组名是 家禽 / 野兽，右侧是该组 6 肖）
                if (c.length > 1 && JYXIAO2_FIXED_GROUPS[left]) {
                    groupName = left;
                    var members = jyxiao2SplitCsv(c[1]);
                    groupMembers = members.length ? members : jyxiao2SplitCsv(JYXIAO2_FIXED_GROUPS[left]);
                }
            }
            // 接口兜底：content 缺失时按固定分组表反查组名；两肖缺失时退回 content 左侧标签。
            if (!groupMembers.length && groupName && JYXIAO2_FIXED_GROUPS[groupName]) {
                groupMembers = jyxiao2SplitCsv(JYXIAO2_FIXED_GROUPS[groupName]);
            }
            if (!pair.length && content.length) {
                for (var k = 0; k < content.length; k++) {
                    var legacy = String(content[k] === null || content[k] === undefined ? '' : content[k]).split('|');
                    var legacyLabel = String(legacy[0] || '').trim();
                    if (legacyLabel && !JYXIAO2_FIXED_GROUPS[legacyLabel]) { pair.push(legacyLabel); }
                }
                pair = pair.slice(0, 2);
            }
            if (!groupName && !pair.length) continue;

            // 命中：特肖落在两肖里 → 高亮该生肖；否则落在组成员里 → 高亮组名；都不在 → 不高亮。
            var pairHit = opened && pair.indexOf(sx) !== -1;
            var groupHit = opened && !pairHit && groupMembers.indexOf(sx) !== -1;
            var zj = pairHit || groupHit;

            var groupHtml = (groupHit && sx)
                ? '<span style="background-color: #FFFF00">' + groupName + '</span>'
                : groupName;
            var pairHtml = pair.map(function (xiaoLabel) {
                return (pairHit && xiaoLabel === sx)
                    ? '<span style="background-color: #FFFF00">' + xiaoLabel + '</span>'
                    : xiaoLabel;
            }).join('');
            // 两肖缺失（异常数据）时不渲染多余的「+」。
            var shown = groupName
                ? (groupHtml + (pairHtml ? '+' + pairHtml : ''))
                : pairHtml;
            // 判定必须与真实开奖一致：命中 → 准，未命中 → 错，未开奖 → 不显示判定。
            var resTxt = opened ? (sx + code + (zj ? '准' : '错')) : '待开奖';

            htmlBoxList += ' <tr><td align=\'center\' height=40 class=\'stylelxz\'><strong>' + d.term + '期</strong><span class=\'styleliao\'><strong>家畜野兽</strong></span>:<span class=\'stylezi\'><strong>【' + shown + '】</strong></span><strong> 开:' + resTxt + '</strong></td></tr>';
        }
        if (!htmlBoxList) {
            renderEmpty('.l1');
            return;
        }
        $('.l1').html('<table border=\'1\' width=\'100%\' cellpadding=\'0\' cellspacing=\'0\' bgcolor=\'#FFFFFF\' bordercolor=\'#D4D4D4\' style=\'border-collapse: collapse\'><tr><td class=\'center f13 black l150\' height=\'29\' align=\'center\' bgcolor=\'#FF0000\'><b><font size=\'4\'><font color=\'#FFFF00\' face=\'微软雅黑\'>&nbsp;</font><font face=\'微软雅黑\'><font color=\'#FFFF00\'> </font><font color=\'#FFFFFF\'>家禽+野兽</font></font></font></b></td></tr><tr><td align=\'center\' height=40 class=\'stylelxz\'><span class=\'styleliao\'>特邀高手：【阳光下的真实】【家禽+野兽】</span></td></tr>' + htmlBoxList + '</table>');
    })
    .fail(function () {
        renderError('.l1', '家禽+野兽数据加载失败');
    });
