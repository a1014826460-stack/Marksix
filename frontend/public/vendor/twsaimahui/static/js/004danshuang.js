
$.ajax({
    url: httpApi + `/api/kaijiang/getDsxiao?web=${web}&type=${type}&num=2`,
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
                let xiao = String(d.xiao == null ? '' : d.xiao).split(',');
                let xiaoV = [];
                let ma = [];
                let content = [d.content];
                let ds = [];
                let dsv = [];
                for (let i in content) {
                    let c = String(content[i]||'').split('|');
                    ds.push(String(c[0]||'').split('')[0])
                    dsv[i] = c[1] || '';
                }

                // 「单双选1（6肖分类池）+ 生肖选2」= 两个维度，任一维度命中即算命中。
                // 历史资料里 content 分类池与 xiao 候选生肖互斥，二者合计覆盖 8/12 生肖，
                // 只判 xiao 会把分类池命中的那一半全部误判成"错"（全部显示错的根因）。
                let dsHit = !!(opened && dsv[0] && dsv[0].indexOf(code) !== -1);
                let c = dsHit
                    ? `<span style="background-color:#FFFF00">${ds[0]}</span>`
                    : `${ds[0]}`;

                let c1 = [];
                let zj = false;
                for (let j = 0; j < xiao.length; j++) {
                    if (opened && sx && xiao[j].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color:#FFFF00">${xiao[j]}</span>`);
                    }else {
                        c1.push(`${xiao[j]}`)
                    }
                }

                let hit = dsHit || zj;

                // 开奖段只在命中时高亮（标黄本期特码），未命中/未开奖绝不高亮。
                // 旧写法把 `background-color:#FFFF00` 写在开奖段的 font 上，导致判「错」的行也有黄底。
                let resHtml = opened
                    ? (hit
                        ? `开:<span style="background-color:#FFFF00">${sx}${code}</span>准`
                        : `开:${sx}${code}错`)
                    : '开:待开奖';

                htmlBoxList += ` 
 <tr>
<td align='center' height=40><b>
<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c}+${c1.join('')}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${resHtml}</font></b></td>
</tr>
 
            `
            }
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>


	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双中特</font></font></font></b></td>

		</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l25").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双中特</font></font></font></b></td>

		</tr>


























		
							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>268期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>单+兔猪</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>？00准</font> </font></b></td>
		</tr>



							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>267期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>双</span>+狗虎</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>蛇12准</font> </font></b></td>
		</tr>
		
		



 
		
						<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>265期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>单+<span style='background-color: #FFFF00'>牛</span>羊</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>牛16准</font> </font></b></td>
		</tr>
		

 

		
							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>263期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>双+<span style='background-color: #FFFF00'>龙</span>马</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>龙13准</font> </font></b></td>
		</tr>
		



		

							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>262期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>单+<span style='background-color: #FFFF00'>鸡</span>兔</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>鸡44准</font> </font></b></td>
		</tr>
		



		
						<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>261期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>双+马<span style='background-color: #FFFF00'>龙</span></font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>龙01准</font> </font></b></td>
		</tr>
		



		
						<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>260期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>双</span>+鼠猴</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>牛40准</font> </font></b></td>
		</tr>



		
							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>259期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>单</span>+牛猪</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>鼠29准</font> </font></b></td>
		</tr>





							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>258期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>双</span>+马鼠</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>牛40准</font> </font></b></td>
		</tr>
		
		



							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>257期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>双</span>+狗鼠</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>鸡08准</font> </font></b></td>
		</tr>
		


  
 
  
  

 
 


	</table>
*/

