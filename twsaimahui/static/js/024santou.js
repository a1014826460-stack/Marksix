$.ajax({
    url: httpApi + `/api/kaijiang/getTou?web=${web}&type=${type}&num=3`,
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
 <tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>三头中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>『${c1.join('.')}』开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${ (sx?( zj?'准':'错'):'??')}</font> </font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>



	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>三头中特</font></font></font></b></td>


            ${htmlBoxList}
            </table>
        `;
        $(".l55").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>三头中特</font></font></font></b></td>

















							<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>三头中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>『0头.2头.4头』开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>准</font> </font></b></td>
		</tr>


				<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>267期</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>三头中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>『<span style='background-color: #FFFF00'>1</span>头.2头.4头』开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>准</font> </font></b></td>
		</tr>
			



			<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>266期</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>三头中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>『0头.<span style='background-color: #FFFF00'>2</span>头.4头』开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>虎27</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>准</font> </font></b></td>
		</tr>


 
 
  

 
	</table>


*/
