$.ajax({
    url: httpApi + `/api/kaijiang/getPingte?web=${web}&type=${type}&num=3`,
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
                    let index = getZjIndex(xiao[i],sxSplit);
                    if (index !== undefined) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }


                htmlBoxList += ` 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>${c1.join('')}</strong></span><strong>】 
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>平特三肖</font></font></font></b></td>
</tr>


<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【神仙买码】【平特三肖】</span>
</td>
</tr>		

            ${htmlBoxList}
            </table>
        `;
        $(".l35").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>平特三肖</font></font></font></b></td>
</tr>


<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【神仙买码】【平特三肖】</span>
</td>
</tr>		











<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>猴蛇虎</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>猴</span>狗虎</strong></span><strong>】 
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>牛</span>羊<span style='background-color: #FFFF00'>龙</span></strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>鼠马</span>鸡</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>猪<span style='background-color: #FFFF00'>马</span>牛</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>狗猪<span style='background-color: #FFFF00'>鸡</span></strong></span><strong>】 
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>虎<span style='background-color: #FFFF00'>狗</span>兔</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
260期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>猴<span style='background-color: #FFFF00'>蛇</span>鸡</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
259期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>鼠</span>龙羊</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
258期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>虎</span>猴蛇</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
257期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>马</span>兔<span style='background-color: #FFFF00'>羊</span></strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
256期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>猴</span>狗<span style='background-color: #FFFF00'>猪</span></strong></span><strong>】 
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
255期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>鸡<span style='background-color: #FFFF00'>蛇猴</span></strong></span><strong>】 
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
254期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>牛龙</span>狗</strong></span><strong>】 
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
253期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>鸡<span style='background-color: #FFFF00'>马</span>猪</strong></span><strong>】 
</strong>
</td>
</tr>	
  
  
 
 
 

</table>*/
