
$.ajax({
    url: httpApi + `/api/kaijiang/getYysx?web=${web}&type=${type}&num=2`,
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
                    if (c[0] === '阴肖') {
                        yinx = c[1].replaceAll(',','');
                    }else{
                        yangx = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>阴阳生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>阴肖</span>:<span class='stylezi'>${yinx}</span><br><span class='styleliao'>  阳肖</span>:<span class='stylezi'>${yangx}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l4").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>阴阳生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>阴肖</span>:<span class='stylezi'>鼠龙蛇马狗猪</span><br><span class='styleliao'>  阳肖</span>:<span class='stylezi'>牛虎兔羊猴鸡</span>
</td>
</tr>			
















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>阳肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>阳肖</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>阳肖</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>阴肖</strong></span><strong> 开:猪30准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>阴肖</strong></span><strong> 开:龙13准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>阳肖</strong></span><strong> 开:鸡44准
</strong>
</td>
</tr>	


 
 
 



</table>*/
