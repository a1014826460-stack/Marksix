$.ajax({
    url: httpApi + `/api/kaijiang/getShaWei?web=${web}&type=${type}&num=3`,
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
                // null/undefined 安全的 CSV 解析：`String(null)` 会得到 'null'，会被误判成已开奖。
                let csv = function (v) { return (v === null || v === undefined) ? [] : String(v).split(','); };
                // 开奖口径：res_code/res_sx 的**最后一项**才是本期特码/特肖
                // （res_code 是本期完整开奖串，与 lottery_draws.numbers 同序，末位即特码）。
                let codeSplit = csv(d.res_code);
                let sxSplit = csv(d.res_sx);
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let opened = !!(code && sx);
                let xiao = [];
                let xiaoV = [];
                let ma = [];
                let content = safeParseJSON(d.content, []);
                for (let j in content) {
                    let c = String(content[j]||'').split('|');
                    if (!c[0]) continue;
                    xiao.push(String(c[0]).split('')[0])
                    xiaoV[xiao.length-1] = c[1] || '';
                    ma.push(...String(c[1]||'').split(','));
                }

                // 绝杀语义：杀掉的集合「不含」开奖特码 = 命中 = 准；含 = 错。
                // 未开奖不判定、不高亮。
                let c1 = [];
                let zj = false;
                let hitAny = false;
                for (let k = 0; k < xiao.length; k++) {
                    let inList = !!(code && xiaoV[k] && xiaoV[k].indexOf(code) !== -1);
                    if (inList) { hitAny = true; }
                    c1.push(`<span>${xiao[k]}</span>`);
                }
                if (opened && !hitAny) { zj = true; }

                let resHtml = opened
                    ? (`开:${sx}${code}${zj ? '准' : '错'}`)
                    : '开:待开奖';

                htmlBoxList += ` 

<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.join('')}尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>${resHtml}</font> </font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀三尾</font></font></font></b></td>

		</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l61").html(htmlBoxList)
        applyLotteryRegionTitlePrefix(document.querySelector('.l61'))
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});

/*

 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀三尾</font></font></font></b></td>

		</tr>












		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>358尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>？00</font> </font></b></td>
		</tr>	
		



		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>267期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>146尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>蛇12</font> </font></b></td>
		</tr>	



 

				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>264期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>269尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>猪30</font> </font></b></td>
		</tr>	
		




		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>263期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>269尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>龙13</font> </font></b></td>
		</tr>	
		



		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>262期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>159尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>鸡44</font> </font></b></td>
		</tr>	
		




		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>261期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>269尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>龙01</font> </font></b></td>
		</tr>	
		


		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>260期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>358尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>牛40</font> </font></b></td>
		</tr>	
		




		
				<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>259期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>158尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>鼠29</font> </font></b></td>
		</tr>	
		



  
 
 
 
	</table>

*/
