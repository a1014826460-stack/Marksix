$.ajax({
    url: httpApi + `/api/kaijiang/getXiaoma2?web=${web}&type=${type}&num=4`,
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
                let maValue = [];
                let content = JSON.parse(d.content);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    maValue[i] = c[1];
                    ma.push(...c[1].split(','));
                }



                let c = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) !== -1) {
                        zj =true;
                        c.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c.push(`${xiao[i]}`)
                    }
                }


                let c1 = [];
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">${ma[i]}</span>`);
                    }else {
                        c1.push(`${ma[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【${c[0]}:${c1.slice(0,2).join('.')}】【${c[1]}:${c1.slice(2,4).join('.')}】<br>【${c[2]}:${c1.slice(4,6).join('.')}】【${c[3]}:${c1.slice(6).join('.')}】</font></b></td>
</tr>

            `
            }
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 			


	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>四肖八码</font></font></font></b></td>

		</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l5").html(htmlBoxList)
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
    
    
    <title>澳 |马会开奖结果|一肖中特免费公开资料|香港六合彩|六合彩开奖结果|历史开奖记录|最快开奖尽在澳王中王</title>
    <meta name='keywords' content='澳王中王,本港台开奖现场直播,香港马会开奖结果,香港马会资料,买马网站,香港挂牌正版彩图,管家婆彩图,白小姐玄机图,现场报码' />
    <meta name='description' content='澳王中王开奖结果 - 与本港电视台同步直播。第一时间更新开奖结果及开奖记录、王中王汇集网上最强势的彩票网址大全,提供买马资料,开奖记录查询等大型综合买马新闻文字报道网站' />
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
.style1 {
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>四肖八码</font></font></font></b></td>

		</tr>













<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【牛:16.40】【猪:18.42】<br>【猴:21.45】【马:11.35】</font></b></td>
</tr>




<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>267期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>蛇</span>:24.48】【鸡:20.32】<br>【狗:31.43】【兔:14.38】</font></b></td>
</tr>





<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>266期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【鼠:05.41】【羊:22.46】<br>【蛇:24.36】【<span style='background-color: #FFFF00'>虎</span>:<span style='background-color: #FFFF00'>27</span>.39】</font></b></td>
</tr>




		
<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>265期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【兔:26.02】【马:23.35】<br>【猴:09.45】【<span style='background-color: #FFFF00'>牛</span>:28.40】</font></b></td>
</tr>




<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>264期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>猪</span>:18.42】【马:23.47】<br>【蛇:24.48】【猴:21.33】</font></b></td>
</tr>




		
<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>263期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【鼠:17.41】【<span style='background-color: #FFFF00'>龙</span>:<span style='background-color: #FFFF00'>13</span>.37】<br>【兔:26.38】【虎:15.39】</font></b></td>
</tr>



 
 

 
 
 
 

 

						</table>


</body>*/
