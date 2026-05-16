$.ajax({
    url: httpApi + `/api/kaijiang/getWeima2?web=${web}&type=${type}&num=4`,
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
                    xiao.push(c[0].split('')[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (code && xiao[i] === code.split('')[1]) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}尾</span>`);
                    }else {
                        c1.push(`${xiao[i]}尾`)
                    }
                }

                let c2 = [];
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) !== -1) {
                        zj = true;
                        c2.push(`<span style="background-color: #FFFF00">${ma[i]}</span>`);
                    }else {
                        c2.push(`${ma[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四尾八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【${c1[0]}-${c2.slice(0,2).join('.')}】【${c1[1]}-${c2.slice(2,4).join('.')}】<br>【${c1[2]}-${c2.slice(4,6).join('.')}】【${c1[3]}-${c2.slice(6,8).join('.')}】</font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
	<tr>
		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>四尾八码</font></font></font></b></td>
		</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l28").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>四尾八码</font></font></font></b></td>
		</tr>

























<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四尾八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【4尾-34.44】【3尾-03.43】<br>【1尾-01.31】【6尾-26.36】</font></b></td>
</tr>




 
 
 
 
 

						</table>*/
