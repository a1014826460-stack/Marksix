$.ajax({
    url: httpApi + `/api/kaijiang/getSanqiXiao4new?web=${web}&type=${type}&num=7`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let yinx = '';
        let yangx = '';
        if (data.length > 0) {
            for (let i in data) {
                let d = data[i]
                // 开奖口径（已交叉验证）：
                //   mode_payload_197 每期一行，res_code/res_sx 是该行 term 的真实开奖，
                //   第 1 项 = 特码/特肖；前端 /api/kaijiang/getSanqiXiao4new 经
                //   filterSanqiDisplayRows 只保留「窗口内已开奖的最新一期」，
                //   已用 lottery_draws.numbers 验证 res_code 与窗口最新期完全一致。
                // null/undefined 安全的 CSV 解析：`String(null)` 会得到 'null'，会被误判成已开奖。
                let csv = function (v) {
                    if (v === null || v === undefined) { return []; }
                    return String(v).split(',').filter(function (x) { return x !== ''; });
                };
                let codeSplit = csv(d.res_code);
                let sxSplit = csv(d.res_sx);
                let code = codeSplit[0]||'';
                let sx = sxSplit[0]||'';
                let opened = !!(code && sx);
                let xiao = [];
                let xiaoV = [];
                let ma = [];
                let content = safeParseJSON(d.content, []);
                for (let j in content) {
                    let c = String(content[j]||'').split('|');
                    if (!c[0]) continue;
                    xiao.push(c[0])
                    xiaoV[xiao.length-1] = c[1] || '';
                    ma.push(...String(c[1]||'').split(','));
                }

                // 窗口期号：names[0] 最早、names[1] 最晚，中间期 = 最小期 + 1（保持补零宽度）。
                let terms = [];
                let names = String(d.name||'').split('-');
                if (names.length === 2 && names[0] && names[1]) {
                    let lo = names[0].trim();
                    let hi = names[1].trim();
                    let width = Math.max(lo.length, hi.length);
                    let mid = String(Math.min(parseInt(lo, 10), parseInt(hi, 10)) + 1);
                    while (mid.length < width) { mid = '0' + mid; }
                    while (lo.length < width) { lo = '0' + lo; }
                    while (hi.length < width) { hi = '0' + hi; }
                    terms[0] = lo;
                    terms[1] = mid;
                    terms[2] = hi;
                }

                // 候选四肖来自真实 content，替换供应商硬编码的「龙马羊狗」。
                // 命中（本期特肖 ∈ 候选四肖）→ 该生肖标黄；未命中 → 不高亮。
                let c1 = [];
                let zj = false;
                for (let k = 0; k < xiao.length; k++) {
                    if (opened && sx && xiao[k].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color:#FFFF00">${xiao[k]}</span>`);
                    }else {
                        c1.push(`${xiao[k]}`)
                    }
                }

                // res_code/res_sx 只覆盖窗口内已开奖的最新一期，其余两期没有逐期开奖数据，
                // 因此只有该期显示判定与开奖；另两期只显示期号，不显示准/错、不高亮。
                let resTxt = opened ? ('开:' + sx + code + (zj ? '准' : '错')) : '';
                let resCell = function (pos) { return (pos === 2 && resTxt) ? resTxt : ''; };
                let rowTd = function (pos, extra) {
                    return "<td align='center' bgcolor='#FFFFFF' width='22%'" + (extra || '') + ">" +
                        "<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>" +
                        "<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>" +
                        (terms[pos] ? (terms[pos] + '期') : '') + "</font></b></td>";
                };

                htmlBoxList += ` 
 <table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
${rowTd(2, " height='11'")}
<td align='center' bgcolor='#FFFFFF' width='55%' rowspan='3'>
<font face='微软雅黑' size='5' color='#FF0000'><strong>${c1.join('')}</strong></font></td>
<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
<font face='微软雅黑'>${resCell(2)}</font></td>
</tr>
<tr>
${rowTd(1, " height='11'")}
<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
<font face='微软雅黑'>${resCell(1)}</font></td>
</tr>
<tr>
${rowTd(0, " style='height: 26px'")}
<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
<font face='微软雅黑'>${resCell(0)}</font></td>
</tr>
 </table>
            `
            }
        }
        htmlBoxList = `
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
        $(".l21").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});






/*

<table border='1' width='100%' cellpadding='0' height='29' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

	<tr>

		<td  height='29' align='center' bgcolor='#FF0000'>

		<font color='#FFFFFF' size='4'>
		<span style='font-family: 微软雅黑; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 700; letter-spacing: normal; orphans: 2; text-align: -webkit-center; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; display: inline !important; float: none'>
		 【四肖三期内必出】 </span></font></td>
		</tr>
		</table>


	<!----开始---->    
	<table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
		<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b><font face='微软雅黑'>268期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='55%' rowspan='3'>
		<font face='微软雅黑' size='5' color='#FF0000'><strong>
		龙马羊狗</span></strong></span></font></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:猫00</font></td>
		</tr>
	<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		267期</font></b></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:蛇12</font></td>
		</tr>
	<tr>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		266期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<font face='微软雅黑'>开:虎27</font></td>
		</tr>
		</table>
		
<!----结束----> 			






	
	<!----开始---->    
	<table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
		<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b><font face='微软雅黑'>265期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='55%' rowspan='3'>
		<font face='微软雅黑' size='5' color='#FF0000'><strong>
		<span style='background-color: #FFFF00'>鸡</span>虎蛇羊</span></strong></span></font></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:牛16</font></td>
		</tr>
	<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		264期</font></b></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:猪30</font></td>
		</tr>
	<tr>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		263期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<font face='微软雅黑'>开:龙13</font></td>
		</tr>
		</table>
		
<!----结束----> 			







	<!----开始---->    
	<table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
		<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b><font face='微软雅黑'>262期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='55%' rowspan='3'>
		<font face='微软雅黑' size='5' color='#FF0000'><strong>
		<span style='background-color: #FFFF00'>龙</span>鸡羊<span style='background-color: #FFFF00'>牛</span></span></strong></span></font></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:鸡44</font></td>
		</tr>
	<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		261期</font></b></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:龙01</font></td>
		</tr>
	<tr>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		260期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<font face='微软雅黑'>开:牛40</font></td>
		</tr>
		</table>
		



 

 
 

 

 

 
*/
