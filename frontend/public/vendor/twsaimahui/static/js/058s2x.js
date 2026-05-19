$.ajax({
    url: httpApi + `/api/kaijiang/getShaXiao?web=${web}&type=${type}&num=2`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) === -1) {
                        zj = true;
                        c1.push(`<span>${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>${c1.join('')}</strong></span><strong>】开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
</strong>
</td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀二肖</font></font></font></b></td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l47").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});

/*

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
.stylesb {
background-color: #FFFF00;
}
.stylelxz {
font-family: 方正粗黑宋简体;
font-size: medium;
}
.styleliao {
color: #800080;
}
.stylezi {
color: #FF0000;
}
-->
</style>
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀二肖</font></font></font></b></td>
</tr>




















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>牛羊</strong></span><strong>】开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>猪龙</strong></span><strong>】开:蛇12准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>猴鸡</strong></span><strong>】开:虎27准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>狗虎</strong></span><strong>】开:猪30准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>马猪</strong></span><strong>】开:龙13准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>羊虎</strong></span><strong>】开:鸡44准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>猴虎</strong></span><strong>】开:龙01准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
260期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>猪马</strong></span><strong>】开:牛40准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
259期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>狗兔</strong></span><strong>】开:鼠29准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
258期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>鸡鼠</strong></span><strong>】开:牛40准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
257期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>蛇马</strong></span><strong>】开:鸡08准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
256期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>马龙</strong></span><strong>】开:虎39准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
255期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>虎鸡</strong></span><strong>】开:猪30准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
254期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>龙鸡</strong></span><strong>】开:虎27准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
253期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>羊虎</strong></span><strong>】开:马47准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
252期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>虎牛</strong></span><strong>】开:蛇36准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
251期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>牛羊</strong></span><strong>】开:兔14准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
250期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>猪龙</strong></span><strong>】开:蛇24准
</strong>
</td>
</tr>	

 
 
 
  
  

 

 


</table>*/
