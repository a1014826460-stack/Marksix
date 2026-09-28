// 四肖三期内必出（mode 197 / getSanqiXiao4new）
//
// 展示口径（见 docs/prediction-display-standard.md）：
//   一个窗口 3 期，**每期都要显示自己的开奖与判定**（未开奖显示「开:待开奖」，不给判定、不高亮）；
//   某期特肖 ∈ 候选 4 肖 → 准（该生肖标黄），否则错（整行零黄底）。
//
// 数据来源：接口返回 `periods`（新增字段）= 窗口内逐期开奖明细，按期中升序，
// 每项 { term, res_code, res_sx }；res_code/res_sx 是该期完整开奖串，
// 特码/特肖取**最后一项**（与 061jy2x.js / 012liuxiao.js / shengshi8800 023sqzt.js 同口径）。
// 既有 res_code/res_sx（窗口内最新已开奖那一期）保留不变，仅在缺少 periods 时兜底。
$.ajax({
    url: httpApi + `/api/kaijiang/getSanqiXiao4new?web=${web}&type=${type}&num=7`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBoxList = ''

        let data = response.data
        if (!data || !data.length) { return }

        let csv = function (v) {
            if (v === null || v === undefined) { return []; }
            return String(v).split(',').map(function (x) { return String(x).trim(); })
                .filter(function (x) { return x !== ''; });
        };
        let esc = function (v) { return String(v === null || v === undefined ? '' : v); };

        for (let i = 0; i < data.length; i++) {
            let d = data[i]

            // 候选四肖来自真实 content（`肖|号码池` 形态，取左侧肖名）。
            let xiao = []
            let content = safeParseJSON(d.content, [])
            for (let j = 0; j < content.length; j++) {
                let c = String(content[j] || '').split('|')
                let name = String(c[0] || '').trim()
                if (!name) continue
                xiao.push(name)
            }
            if (!xiao.length) { continue }

            // 窗口期号：names[0] 最早、names[1] 最晚，中间期 = 最小期 + 1（保持补零宽度）。
            let terms = []
            let names = String(d.name || '').split('-')
            if (names.length === 2 && names[0] && names[1]) {
                let lo = names[0].trim()
                let hi = names[1].trim()
                let width = Math.max(lo.length, hi.length)
                let mid = String(Math.min(parseInt(lo, 10), parseInt(hi, 10)) + 1)
                while (mid.length < width) { mid = '0' + mid; }
                while (lo.length < width) { lo = '0' + lo; }
                while (hi.length < width) { hi = '0' + hi; }
                // 渲染顺序：最新期在上（与厂商静态样表一致）。
                terms = [hi, mid, lo]
            } else if (d.name) {
                terms = [String(d.name).trim()]
            }
            if (!terms.length) { continue }

            // 逐期开奖：periods（接口新增字段）。缺失时退回既有 res_code/res_sx，
            // 并把它记在窗口最新期上（旧接口只能给出一期的开奖）。
            let periods = Array.isArray(d.periods) ? d.periods : safeParseJSON(d.periods, [])
            let byTerm = {}
            for (let p = 0; p < periods.length; p++) {
                let item = periods[p]
                if (!item || item.term === undefined || item.term === null) continue
                byTerm[String(item.term).trim()] = item
            }
            if (!periods.length) {
                byTerm[terms[0]] = { term: terms[0], res_code: d.res_code, res_sx: d.res_sx }
            }

            let rowsHtml = ''
            for (let t = 0; t < terms.length; t++) {
                let term = terms[t]
                let info = byTerm[term] || {}
                let codeSplit = csv(info.res_code)
                let sxSplit = csv(info.res_sx)
                // 特码/特肖取开奖串最后一项：完整开奖串的前 6 项是平码。
                let code = codeSplit[codeSplit.length - 1] || ''
                let sx = sxSplit[sxSplit.length - 1] || ''
                let opened = !!(code && sx)
                let zj = opened && sx !== '' && xiao.indexOf(sx) !== -1

                // 命中才高亮，未命中/未开奖整行零黄底。
                let c1 = []
                for (let k = 0; k < xiao.length; k++) {
                    if (zj && xiao[k] === sx) {
                        c1.push(`<span style="background-color:#FFFF00">${xiao[k]}</span>`)
                    } else {
                        c1.push(`${xiao[k]}`)
                    }
                }
                let resTxt = opened ? ('开:' + sx + code + (zj ? '准' : '错')) : '开:待开奖'

                rowsHtml += `
<tr>
<td align='center' bgcolor='#FFFFFF' width='22%' height='11'>
<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>${esc(term)}期</font></b></td>
<td align='center' bgcolor='#FFFFFF' width='55%'>
<font face='微软雅黑' size='5' color='#FF0000'><strong>${c1.join('')}</strong></font></td>
<td align='center' bgcolor='#FFFFFF' width='22%'>
<font face='微软雅黑'>${resTxt}</font></td>
</tr>`
            }

            htmlBoxList += `
 <table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
${rowsHtml}
 </table>
            `
        }
        let htmlBox = `
<table border='1' width='100%' cellpadding='0' height='29' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

<tr>

<td  height='29' align='center' bgcolor='#FF0000'>

<font color='#FFFFFF' size='4'>
<span style='font-family: 微软雅黑; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 700; letter-spacing: normal; orphans: 2; text-align: -webkit-center; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; display: inline !important; float: none'>
 【四肖三期内必出】 </span></font></td>
</tr>
</table>
            ${htmlBoxList}
        `;
        $(".l21").html(htmlBox)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});
