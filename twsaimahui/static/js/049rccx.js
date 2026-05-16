$.ajax({
    url: httpApi + `/api/kaijiang/getRccx?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let rou = '';
        let cai = '';
        let cao = '';
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
                    xiao.push(c[0].split('')[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let b = false;
                let c1 = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        b = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                    if (xiao[i] === '肉') {
                        rou = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '菜') {
                        cai = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '草') {
                        cao = xiaoV[i].replaceAll(',','');
                    }
                }
                if (sx && !b) continue;

                htmlBoxList += ` 
 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>肉草菜肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}肖</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
</strong>
</td>
</tr>\t
 
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>肉草菜肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>肉肖</span>:<span class='stylezi'>${rou}</span><span class='styleliao'>  菜肖</span>:<span class='stylezi'>${cai}</span><br>草肖</span>:<span class='stylezi'>${cao}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l11").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>肉草菜肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>肉肖</span>:<span class='stylezi'>虎蛇龙狗</span><span class='styleliao'>  菜肖</span>:<span class='stylezi'>猪鼠鸡猴</span><br>草肖</span>:<span class='stylezi'>牛羊马兔</span>
</td>
</tr>		
















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>肉草菜肖</strong></span>:<span class='stylezi'><strong>草肉肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>肉草菜肖</strong></span>:<span class='stylezi'><strong>草<span style='background-color: #FFFF00'>肉</span>肖</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>肉草菜肖</strong></span>:<span class='stylezi'><strong>草<span style='background-color: #FFFF00'>肉</span>肖</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>肉草菜肖</strong></span>:<span class='stylezi'><strong>草<span style='background-color: #FFFF00'>肉</span>肖</strong></span><strong> 开:龙13准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>肉草菜肖</strong></span>:<span class='stylezi'><strong>肉<span style='background-color: #FFFF00'>菜</span>肖</strong></span><strong> 开:鸡44准
</strong>
</td>
</tr>	
 
  
 

</table>*/
