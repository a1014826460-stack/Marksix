$.ajax({
    url: httpApi + `/api/kaijiang/getSanqiXiao4new?web=${web}&type=${type}&num=7`,
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

                let terms = [];
                let names = d.name.split('-');
                let mid = Math.min(parseInt(names[0]),parseInt(names[1]));
                mid = (++mid).toString();
                if (mid.length < names[0].length) {
                    mid = '0'+mid;
                }
                terms[0] = names[0];
                terms[1] = mid;
                terms[2] = names[1];

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
 <table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
<b><font face='微软雅黑'>${terms[2]}期</font></b></td>
<td align='center' bgcolor='#FFFFFF' width='55%' rowspan='3'>
<font face='微软雅黑' size='5' color='#FF0000'><strong>
龙马羊狗</span></strong></span></font></td>
<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
<font face='微软雅黑'>开:猫00</font></td>
</tr>
<tr>
<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
${terms[1]}期</font></b></td>
<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
<font face='微软雅黑'>开:蛇12</font></td>
</tr>
<tr>
<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
${terms[0]}期</font></b></td>
<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
<font face='微软雅黑'>开:虎27</font></td>
</tr>
</table>
 
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' height='29' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

<tr>

<td  height='29' align='center' bgcolor='#FF0000'>

<font color='#FFFFFF' size='4'>
<span style='font-family: 微软雅黑; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 700; letter-spacing: normal; orphans: 2; text-align: -webkit-center; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; display: inline !important; float: none'>
 【四肖三期内必出】 </span></font></td>
</tr>
</table>
            ${htmlBoxList}
        `;
        $(".l21").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});






/*

<table border='1' width='100%' cellpadding='0' height='29' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

	<tr>

		<td  height='29' align='center' bgcolor='#FF0000'>

		<font color='#FFFFFF' size='4'>
		<span style='font-family: 微软雅黑; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 700; letter-spacing: normal; orphans: 2; text-align: -webkit-center; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; display: inline !important; float: none'>
		 【四肖三期内必出】 </span></font></td>
		</tr>
		</table>


	<!----开始---->    
	<table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
		<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b><font face='微软雅黑'>268期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='55%' rowspan='3'>
		<font face='微软雅黑' size='5' color='#FF0000'><strong>
		龙马羊狗</span></strong></span></font></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:猫00</font></td>
		</tr>
	<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		267期</font></b></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:蛇12</font></td>
		</tr>
	<tr>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		266期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<font face='微软雅黑'>开:虎27</font></td>
		</tr>
		</table>
		
<!----结束----> 			






	
	<!----开始---->    
	<table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
		<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b><font face='微软雅黑'>265期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='55%' rowspan='3'>
		<font face='微软雅黑' size='5' color='#FF0000'><strong>
		<span style='background-color: #FFFF00'>鸡</span>虎蛇羊</span></strong></span></font></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:牛16</font></td>
		</tr>
	<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		264期</font></b></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:猪30</font></td>
		</tr>
	<tr>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		263期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<font face='微软雅黑'>开:龙13</font></td>
		</tr>
		</table>
		
<!----结束----> 			







	<!----开始---->    
	<table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
		<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b><font face='微软雅黑'>262期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='55%' rowspan='3'>
		<font face='微软雅黑' size='5' color='#FF0000'><strong>
		<span style='background-color: #FFFF00'>龙</span>鸡羊<span style='background-color: #FFFF00'>牛</span></span></strong></span></font></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:鸡44</font></td>
		</tr>
	<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		261期</font></b></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:龙01</font></td>
		</tr>
	<tr>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		260期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<font face='微软雅黑'>开:牛40</font></td>
		</tr>
		</table>
		



 

 
 

 

 

 
*/
