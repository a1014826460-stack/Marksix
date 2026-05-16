$.ajax({
    url: httpApi + `/api/kaijiang/getCyptwei?web=${web}&type=${type}&num=2`,
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
                let num;
                if (d.title.indexOf('一') !== -1) {
                    num = 1;
                }else if (d.title.indexOf('二') !== -1) {
                    num = 2;
                }else if (d.title.indexOf('三') !== -1) {
                    num = 3;
                }else if (d.title.indexOf('四') !== -1) {
                    num = 4;
                }else if (d.title.indexOf('五') !== -1) {
                    num = 5;
                }else if (d.title.indexOf('六') !== -1) {
                    num = 6;
                }else if (d.title.indexOf('七') !== -1) {
                    num = 7;
                }else if (d.title.indexOf('八') !== -1) {
                    num = 8;
                }else if (d.title.indexOf('九') !== -1) {
                    num = 9;
                }else if (d.title.indexOf('零') !== -1) {
                    num = 0;
                }else {
                    continue
                }
                num +=''
                let index=99;
                for (let k in codeSplit) {
                    if (!codeSplit[k]) continue;
                    let w = codeSplit[k].split('')[1];
                    if (w === num) {
                        index = k;
                        break
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>成语平特尾</strong></span>:【<span class='stylezi'><strong>${d.title}</strong></span><strong>】 开:${codeSplit[index]||code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>成语平特尾</font></font></font></b></td>
</tr>
	

            ${htmlBoxList}
            </table>
        `;
        $(".l20").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>成语平特尾</font></font></font></b></td>
</tr>












<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>成语平特尾</strong></span>:【<span class='stylezi'><strong>五福临门</strong></span><strong>】 开:00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>成语平特尾</strong></span>:【<span class='stylezi'><strong>四海鼎沸</strong></span><strong>】 开:34准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>成语平特尾</strong></span>:【<span class='stylezi'><strong>二缶锺惑</strong></span><strong>】 开:02准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>成语平特尾</strong></span>:【<span class='stylezi'><strong>三足鼎立</strong></span><strong>】 开:33准
</strong>
</td>
</tr>	
 



</table>*/
