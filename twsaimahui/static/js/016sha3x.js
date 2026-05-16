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
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

                let c1 = [];
                let zj = true;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) === -1) {
                        c1.push(`<span>${xiao[i]}</span>`);
                    }else {
                        zj = false;
                        c1.push(`${xiao[i]}`)
                    }
                }
                if (sx && !zj) continue;

                htmlBoxList += ` 
<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>${d.term}期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（${c1.join('')}）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>${ (sx?( zj?'赢':'输'):'??')}</font> </font></b></td>
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


