$.ajax({
    url: httpApi + `/api/kaijiang/getXingte?web=${web}&type=${type}&num=3`,
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
<td align='center' style='height: 40px'><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#008000' style='font-size: 14pt' face='方正粗黑宋简体'>三行中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.join('')}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${ (sx?( zj?'准':'错'):'??')}</font> </font></b></td>
</tr>
 
            `
            }
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'>www.twsaimahui.com</font><font color='#FFFFFF'>三行中特</font></font></font></b></td>


            ${htmlBoxList}
            </table>
        `;
        $(".l56").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});

/*

<!DOCTYPE HTML>
<html>
<head>
    <meta http-equiv='Content-Type' content='text/html;charset=utf-8' />
    <meta name='viewport' content='width=device-width,minimum-scale=1.0,maximum-scale=1.0,user-scalable=no' />
    <meta name='applicable-device' content='mobile' />
    <meta name='apple-mobile-web-app-capable' content='yes' />
    <meta name='apple-mobile-web-app-status-bar-style' content='black' />
    <meta content='telephone=no' name='format-detection' />
    
    <meta name='mobile-agent' content='format=xhtml;url=/'>
    <meta name='mobile-agent' content='format=html5;url=/'>
    <link rel='alternate' media='only screen and(max-width: 640px)' href='/'>

<style>

<!--

* { word-wrap: break-word; }
*{padding:0;margin:0}
* { word-wrap: break-word; }
* {
	PADDING-BOTTOM: 0px; MARGIN: 0px; PADDING-LEFT: 0px; PADDING-RIGHT: 0px; PADDING-TOP: 0px
}
* {
	WORD-WRAP: break-word
}
* {
	WORD-WRAP: break-word
}
* {
	WORD-WRAP: break-word
}
* {
	WORD-WRAP: break-word
}
.style1sxx {
	background-color: #FFFF00;
}
-->
</style>
</head>
<body>
  

 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'>www.twsaimahui.com</font><font color='#FFFFFF'>三行中特</font></font></font></b></td>




















				
				<tr>
			<td align='center' style='height: 40px'><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#008000' style='font-size: 14pt' face='方正粗黑宋简体'>三行中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>火土木</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>准</font> </font></b></td>
		</tr>
							

 
 
  
  
 

	</table>

</body>
*/
