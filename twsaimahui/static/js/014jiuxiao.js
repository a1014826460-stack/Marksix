$.ajax({
    url: httpApi + `/api/kaijiang/getZhongte?web=${web}&type=${type}&num=9`,
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
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <td align='center' height=40><b>
<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>${d.term}期:</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>九肖</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【${c1.join('')}】 开</font><font color='#0000FF' style='font-size: 12pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>${ (sx?( zj?'赢':'输'):'??')}</font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>九肖中特</font></font></font></b></td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l15").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>九肖中特</font></font></font></b></td>
</tr>

















		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>268期:</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>九肖</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【狗虎猴兔马蛇羊鼠龙】 开</font><font color='#0000FF' style='font-size: 12pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>



		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>267期:</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>九肖</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【猪鼠鸡<span style='background-color: #FFFF00'>蛇</span>龙狗猴兔羊】 开</font><font color='#0000FF' style='font-size: 12pt' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>



 

 
 
 
 
  
 
 
			</table>
*/

