
$.ajax({
    url: httpApi + `/api/kaijiang/getYzxj?web=${web}&type=${type}&num=6/12`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let dw = '';
        let xw = '';
        let imgUrl;
        if (data.length > 0) {
            for (let i in data) {
                let d = data[i]
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao =  d.xiao.split('');
                let xiaoV =  [];
                let ma = [];
                let c1 = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr><td align='center' height=40><b>
<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#008000' style='font-size: 14pt' face='方正粗黑宋简体'>一字玄机</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>${d.zi}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】<br></font>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>
${d.jiexi}<br></font><font color='#800000' style='font-size: 14pt' face='方正粗黑宋简体'>
综合取肖：【${c1.join('')}】</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>
</font></font></b></td></tr>
            `
            }
        }

        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>一字玄机</font></font></font></b></td>

		</tr>

            ${htmlBoxList}
            
            </table>
        `;
        $(".yzxj").html(htmlBoxList)
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
.styleszxj {
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>一字玄机</font></font></font></b></td>

		</tr>


















<tr><td align='center' height=40><b>
<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>268期</font><font color='#008000' style='font-size: 14pt' face='方正粗黑宋简体'>一字玄机</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>榃</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】<br></font>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>
解字：木字解木肖，虎兔；田，解土肖，牛龙羊狗。<br></font><font color='#800000' style='font-size: 14pt' face='方正粗黑宋简体'>
综合取肖：【虎兔牛龙羊狗】</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>
</font></font></b></td></tr>





<tr><td align='center' height=40><b>
<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>267期</font><font color='#008000' style='font-size: 14pt' face='方正粗黑宋简体'>一字玄机</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>笗</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】<br></font>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>
解字：⺮解竹肖，蛇马羊；冬字解冬肖，猪鼠牛。<br></font><font color='#800000' style='font-size: 14pt' face='方正粗黑宋简体'>
综合取肖：【<span style='background-color: #FFFF00'>蛇</span>马羊猪鼠牛】</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>
</font></font></b></td></tr>


<tr><td align='center' height=40><b>
<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>266期</font><font color='#008000' style='font-size: 14pt' face='方正粗黑宋简体'>一字玄机</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>墚</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】<br></font>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>
解字：土字旁解土肖，龙狗牛羊；木解木肖，虎兔。<br></font><font color='#800000' style='font-size: 14pt' face='方正粗黑宋简体'>
综合取肖：【龙狗牛羊<span style='background-color: #FFFF00'>虎</span>兔】</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>
</font></font></b></td></tr>


 
  
 
 
 
 
 
 

			</table>

</body>*/
