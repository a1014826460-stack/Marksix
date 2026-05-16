$.ajax({
 url: httpApi + `/api/kaijiang/getShatou?web=${web}&type=${type}&num=1`,
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
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.join('')}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${ (sx?( zj?'中':'不中'):'??')}</font> </font></b></td>
</tr>
            `
   }
  }
  htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀①头</font></font></font></b></td>

		</tr>	

            ${htmlBoxList}
            </table>
        `;
  $(".l58").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀①头</font></font></font></b></td>

		</tr>
















				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>4头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>




				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>267期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>3头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>266期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>0头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>虎27</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>




 							
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>265期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>2头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>牛16</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>




	 
				
			
	<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>264期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>3头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>猪30</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>	




							
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>263期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>2头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>龙13</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>






		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>262期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>2头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>鸡44</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>




							
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>261期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>2头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>龙01</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>


 

				
							<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>259期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>0头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>鼠29</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>


 

				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>257期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>3头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>鸡08</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



				
							<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>256期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>0头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>虎39</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



							
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>255期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>2头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>猪30</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>254期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>0头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>虎27</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>




	<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>253期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>2头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>马47</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



				
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>252期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>0头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>蛇36</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>251期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>4头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>兔14</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>250期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>3头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>蛇24</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>
 
 
  
 
  

		
	</table>
*/

