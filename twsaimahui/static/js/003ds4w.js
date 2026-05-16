$.ajax({
    url: httpApi + `/api/kaijiang/getDsWei?web=${web}&type=${type}&num=4`,
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

                let w1 = d.dan.split(',');
                let w2 = d.shuang.split(',');

                let c1 = [];
                let zj = false;
                for (let i = 0; i < w1.length; i++) {
                    if (code && w1[i] === code.split('')[1]) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${w1[i]}</span>`);
                    }else {
                        c1.push(`${w1[i]}`)
                    }
                }

                let c2 = [];
                for (let i = 0; i < w2.length; i++) {
                    if (code && w2[i] === code.split('')[1]) {
                        zj = true;
                        c2.push(`<span style="background-color: #FFFF00">${w2[i]}</span>`);
                    }else {
                        c2.push(`${w2[i]}`)
                    }
                }

                htmlBoxList += ` 
<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>${d.term}期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【${c1.join('')}】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【${c2.join('')}】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>${ (sx?( zj?'赢':'输'):'??')}</font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>


	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双四尾</font></font></font></b></td>

		</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l6").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双四尾</font></font></font></b></td>

		</tr>









				<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>268期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1359】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【0268】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




		
							<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>267期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1579】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>2</span>468】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




					<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>266期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【13<span style='background-color: #FFFF00'>7</span>9】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【0468】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>虎27</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




							<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>265期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1579】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【24<span style='background-color: #FFFF00'>6</span>8】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>牛16</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>264期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1379】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>0</span>248】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>猪30</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	



 

									<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>262期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1359】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【2<span style='background-color: #FFFF00'>4</span>68】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>鸡44</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	



							<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>261期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>1</span>579】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【2468】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>龙01</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




				<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>260期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1359】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>0</span>268】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>牛40</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




	   <tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>259期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【137<span style='background-color: #FFFF00'>9</span>】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【0468】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>鼠29</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




			<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>258期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1579】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>0</span>268】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>牛40</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




		
							<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>257期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1579】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【246<span style='background-color: #FFFF00'>8</span>】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>鸡08</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




	   <tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>256期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【137<span style='background-color: #FFFF00'>9</span>】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【0468】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>虎39</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	



 
 
 
  
 


	</table>
*/

