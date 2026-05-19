
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
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = d.xiao.split(',');
                let xiaoV = [];
                let ma = [];
                let content = [d.content];
                let ds = [];
                let dsv = [];
                for (let i in content) {
                    let c = content[i].split('|');
                    ds.push(c[0].split('')[0])
                    dsv[i] = c[1];
                }

                let c = `${ds[0]}`;
                if (sx && dsv[0].indexOf(sx) !== -1) {
                    c = `<span style="background-color: #FFFF00">${ds[0]}</span>`
                }

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
 <tr>
<td align='center' height=40><b>
<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c}+${c1.join('')}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}${zj?'准':'错'}</font> </font></b></td>
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

