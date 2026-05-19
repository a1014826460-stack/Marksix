$.ajax({
    url: httpApi + `/api/kaijiang/getHeds?web=${web}&type=${type}&num=2`,
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
                let xiao = [];
                let xiaoV = [];
                let ma = [];
                let content = JSON.parse(d.content);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '阴肖') {
                        yinx = c[1].replaceAll(',','');
                    }else{
                        yangx = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (code && xiaoV[i].indexOf(code) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 
\t\t\t\t\t\t\t\t\t<tr>
\t\t\t<td align='center' height=40><b>
\t\t\t<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>澳合数</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.join('')}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${ (sx?( zj?'中':'不中'):'??')}</font></b></td>
\t\t</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 			


	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>合数中特</font></font></font></b></td>

		</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l9").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>合数中特</font></font></font></b></td>

		</tr>

























									<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>澳合数</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>合单</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font></b></td>
		</tr>







									<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>267期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>澳合数</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>合单</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font></b></td>
		</tr>


 

									<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>265期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>澳合数</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>合单</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>牛16</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font></b></td>
		</tr>




 


 
 
 
 
 
 
 

						</table>
*/


