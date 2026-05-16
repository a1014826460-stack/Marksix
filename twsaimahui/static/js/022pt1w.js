$.ajax({
    url: httpApi + `/api/kaijiang/getPtWei?web=${web}&type=${type}&num=2`,
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
                let index;
                for (let i = 0; i < xiao.length; i++) {
                    index = getZjIndex(xiao[i],codeSplit);
                    if (index !== undefined) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#FF00FF' style='font-size: 14pt' face='方正粗黑宋简体'>平特一尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.slice(0,1).join('')}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】</font><font color='#FF00FF' style='font-size: 14pt' face='方正粗黑宋简体'>二连尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.join('')}尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】${ (sx?( zj?'中':'不中'):'??')}</font> </font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>


				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>平特一尾</font></font></font></b></td>

		</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l42").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>平特一尾</font></font></font></b></td>

		</tr>



















							<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#FF00FF' style='font-size: 14pt' face='方正粗黑宋简体'>平特一尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>2</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】</font><font color='#FF00FF' style='font-size: 14pt' face='方正粗黑宋简体'>二连尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>25尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中</font> </font></b></td>
		</tr>


 

		
					<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>266期</font><font color='#FF00FF' style='font-size: 14pt' face='方正粗黑宋简体'>平特一尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>3</span></font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】</font><font color='#FF00FF' style='font-size: 14pt' face='方正粗黑宋简体'>二连尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>39</span>尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中</font> </font></b></td>
		</tr>



 
 
  
 
  
  
 
  
  
  
						</table>


*/
