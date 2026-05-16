$.ajax({
    url: httpApi + `/api/kaijiang/getNnnx?web=${web}&type=${type}&num=4`,
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

                let nan = d.nan.split(',');
                let c1 = [];
                let zj = false;
                for (let i = 0; i < nan.length; i++) {
                    if (sx && nan[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${nan[i]}</span>`);
                    }else {
                        c1.push(`${nan[i]}`)
                    }
                }

                let nv = d.nv.split(',');
                let c2 = [];
                for (let i = 0; i < nv.length; i++) {
                    if (sx && nv[i].indexOf(sx) !== -1) {
                        zj = true;
                        c2.push(`<span style="background-color: #FFFF00">${nv[i]}</span>`);
                    }else {
                        c2.push(`${nv[i]}`)
                    }
                }

                htmlBoxList += ` 
<tr>
<td align='center' height=39><b>
<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>${d.term}期:</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>男</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>${c1.join('')}</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>】</font><font color='#FF00FF' style='font-size: 12pt' face='方正粗黑宋简体'>女</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【</font><font color='#FF00FF' style='font-size: 12pt' face='方正粗黑宋简体'>${c2.join('')}</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>】 开</font><font color='#0000FF' style='font-size: 12pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font></font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>男女四肖</font></font></font></b></td>

		</tr>
	

            ${htmlBoxList}
            </table>
        `;
        $(".l53").html(htmlBoxList)
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
.stylenv {
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>男女四肖</font></font></font></b></td>

		</tr>








			<tr>
			<td align='center' height=39><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>268期:</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>男</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>狗鼠虎龙</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>】</font><font color='#FF00FF' style='font-size: 12pt' face='方正粗黑宋简体'>女</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【</font><font color='#FF00FF' style='font-size: 12pt' face='方正粗黑宋简体'>羊猪鸡兔</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>】 开</font><font color='#0000FF' style='font-size: 12pt' face='方正粗黑宋简体'>？00</font></font></b></td>
		</tr>




			
				<tr>
			<td align='center' height=39><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>267期:</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>男</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>狗马鼠猴</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>】</font><font color='#FF00FF' style='font-size: 12pt' face='方正粗黑宋简体'>女</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【</font><font color='#FF00FF' style='font-size: 12pt' face='方正粗黑宋简体'>兔鸡<span style='background-color: #FFFF00'>蛇</span>羊</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>】 开</font><font color='#0000FF' style='font-size: 12pt' face='方正粗黑宋简体'>蛇12</font></font></b></td>
		</tr>



 

			<tr>
			<td align='center' height=39><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>265期:</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>男</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>马<span style='background-color: #FFFF00'>牛</span>猴狗</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>】</font><font color='#FF00FF' style='font-size: 12pt' face='方正粗黑宋简体'>女</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【</font><font color='#FF00FF' style='font-size: 12pt' face='方正粗黑宋简体'>兔蛇羊鸡</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>】 开</font><font color='#0000FF' style='font-size: 12pt' face='方正粗黑宋简体'>牛16</font></font></b></td>
		</tr>


 
 
 
 
  


							
	</table>

</body>
*/
