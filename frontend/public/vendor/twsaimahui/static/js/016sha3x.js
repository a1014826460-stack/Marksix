$.ajax({
    url: httpApi + `/api/kaijiang/getShaXiao?web=${web}&type=${type}&num=3`,
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
                // 开奖口径：res_code/res_sx 第 1 项 = 本期特码/特肖（已交叉验证）。
                let codeSplit = csv(d.res_code);
                let sxSplit = csv(d.res_sx);
                let code = codeSplit[0]||'';
                let sx = sxSplit[0]||'';
                let opened = !!(code && sx);
                let xiao = (d.content === null || d.content === undefined) ? [] : String(d.content).split(',');
                let xiaoV = [];
                let ma = [];

                // 绝杀语义：杀掉的生肖「不含」开奖特肖 = 命中 = 准；含 = 错。
                // 未开奖不判定、不高亮。
                let c1 = [];
                let hitAny = false;
                for (let k = 0; k < xiao.length; k++) {
                    if (opened && sx && xiao[k].indexOf(sx) !== -1) { hitAny = true; }
                    c1.push(`<span>${xiao[k]}</span>`);
                }
                let zj = opened && !hitAny;

                let resHtml = opened
                    ? (`开:${sx}${code}${zj ? '准' : '错'}`)
                    : '开:待开奖';

                htmlBoxList += ` 
<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>${d.term}期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（${c1.join('')}）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>${resHtml}</font> </font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀三肖</font></font></font></b></td>

		</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l62").html(htmlBoxList)
        applyLotteryRegionTitlePrefix(document.querySelector('.l62'))
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀三肖</font></font></font></b></td>

		</tr>










		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>268期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（鼠猪牛）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		
		




		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>267期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（龙马猴）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		
		



		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>266期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（鸡龙狗）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>虎27</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		
		



		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>265期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（龙马猴）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>牛16</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		
		


					<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>264期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（马猴牛）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>猪30</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		



		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>263期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（狗鸡蛇）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>龙13</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		
		


 

		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>261期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（狗鸡蛇）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>龙01</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		
		

 
 
 
 
 

 
  

	</table>
*/


