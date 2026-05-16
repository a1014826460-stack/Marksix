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
                let zj = true;
                for (let i = 0; i < xiao.length; i++) {
                    if (code && xiaoV[i].indexOf(code) === -1) {
                        c1.push(`<span>${xiao[i]}</span>`);
                    }else {
                        zj = false;
                        c1.push(`${xiao[i]}`)
                    }
                }
                if (code && !zj) continue;

                htmlBoxList += ` 

<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.join('')}尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font> </font></b></td>
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
