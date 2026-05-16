$.ajax({
    url: httpApi + `/api/kaijiang/rd70i73lziizczak/0gmqnw/1`,
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
                let ma = d.u6_code.split(',');

                let c1 = [];
                let zj = false;
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) === -1) {
                        zj = true;
                        c1.push(`<span>${ma[i]}</span>`);
                    }else {
                        c1.push(`${ma[i]}`)
                    }
                }
                // if (!zj) continue;

                htmlBoxList += ` 
<td align='center' style='height: 40px'><b>
<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>${d.term}期:</font><font color='#FF00FF' style='font-size: 13pt' face='方正粗黑宋简体'>六不中</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>${c1.join('-')}</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】</font></font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>六不中</font></font></font></b></td>
		</tr>
            ${htmlBoxList}
            </table>
        `;
        $(".l52").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>六不中</font></font></font></b></td>

		</tr>





			<td align='center' style='height: 40px'><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>268期:</font><font color='#FF00FF' style='font-size: 13pt' face='方正粗黑宋简体'>六不中</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>25-43-27-32-47-06</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】</font></font></b></td>
		</tr>		

 


		<td align='center' style='height: 40px'><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>266期:</font><font color='#FF00FF' style='font-size: 13pt' face='方正粗黑宋简体'>六不中</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>44-45-46-16-17-18</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】</font></font></b></td>
		</tr>		



 
	<td align='center' style='height: 40px'><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>264期:</font><font color='#FF00FF' style='font-size: 13pt' face='方正粗黑宋简体'>六不中</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>35-47-20-38-40-42</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】</font></font></b></td>
		</tr>		



	<td align='center' style='height: 40px'><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>263期:</font><font color='#FF00FF' style='font-size: 13pt' face='方正粗黑宋简体'>六不中</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>32-07-19-16-28-15</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】</font></font></b></td>
		</tr>		
		



 

 
 

 
 


		
																																			
	</table>
*/


