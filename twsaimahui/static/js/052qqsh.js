
$.ajax({
    url: httpApi + `/api/kaijiang/qqsh?web=${web}&type=${type}&num=3`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let qin = '';
        let qi = '';
        let shu = '';
        let hua = '';
        if (data.length > 0) {
            for (let i in data) {
                let d = data[i]
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = d.title.split(',');
                let xiaoV = [];
                let ma = [];
                let cont = d.content.split(',');;
                xiaoV[0] = cont.slice(0,3).join('');
                xiaoV[1] = cont.slice(3,6).join('');
                xiaoV[2] = cont.slice(6).join('');

                let c1 = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                    if (xiao[i] === '琴') {
                        qin = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '书') {
                        shu = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '棋') {
                        qi = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '画') {
                        hua = xiaoV[i].replaceAll(',','');
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>琴棋书画</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>琴肖</span>:<span class='stylezi'>${qin}</span>     <span class='styleliao'>棋肖</span>:<span class='stylezi'>${qi}</span><br>
<span class='styleliao'>书肖</span>:<span class='stylezi'>${shu}</span>     <span class='styleliao'>画肖</span>:<span class='stylezi'>${hua}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l67").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>琴棋书画</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>琴肖</span>:<span class='stylezi'>鸡兔蛇</span>     <span class='styleliao'>棋肖</span>:<span class='stylezi'>鼠牛狗</span><br>
<span class='styleliao'>书肖</span>:<span class='stylezi'>马龙虎</span>     <span class='styleliao'>画肖</span>:<span class='stylezi'>羊猪猴</span>
</td>
</tr>			























<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong>书画琴</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong>书画<span style='background-color: #FFFF00'>琴</span></strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	

 

<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>棋</span>书琴</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong>琴书<span style='background-color: #FFFF00'>画</span></strong></span><strong> 开:猪30准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong>琴画<span style='background-color: #FFFF00'>书</span></strong></span><strong> 开:龙13准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>琴</span>棋画</strong></span><strong> 开:鸡44准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong>棋<span style='background-color: #FFFF00'>书</span>画</strong></span><strong> 开:龙01准
</strong>
</td>
</tr>	
  
  

</table>*/
