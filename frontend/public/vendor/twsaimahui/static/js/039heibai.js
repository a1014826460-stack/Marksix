
$.ajax({
    url: httpApi + `/api/kaijiang/getHbx?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let hei = '';
        let bai = '';
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
                let content = safeParseJSON(d.content, []);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0].split('')[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '白') {
                        bai = c[1].replaceAll(',','');
                    }else{
                        hei = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                // 项目约定（与 twbst528 mode 45「黑白各3肖」一致）：显示**生成内容本身**
                // 的两组 3 肖，而不是由开奖结果反查出来的单一分组标签。
                // 命中 = 特码生肖 ∈ 任一组；标黄只标命中的那个生肖（未开奖/未命中零标黄）。
                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    let zodiacs = String(xiaoV[i] || '').split(',');
                    let hit = !!sx && zodiacs.indexOf(sx) !== -1;
                    if (hit) zj = true;
                    let tokens = zodiacs.map(function (z) {
                        return hit && z === sx
                            ? `<span style="background-color: #FFFF00">${z}</span>`
                            : z;
                    }).join('');
                    if (tokens) c1.push(xiao[i] + '肖：' + tokens);
                }
                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>黑白生肖</strong></span>:<span class='stylezi'><strong>${c1.join(' ')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>黑白生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>白边生肖</span>:<span class='stylezi'>鼠牛虎鸡狗猪</span><br><span class='styleliao'>  黑中生肖</span>:<span class='stylezi'>兔龙蛇马羊猴</span>
</td>
</tr>			

            ${htmlBoxList}
            </table>
        `;
        $(".l14").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>黑白生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>白边生肖</span>:<span class='stylezi'>鼠牛虎鸡狗猪</span><br><span class='styleliao'>  黑中生肖</span>:<span class='stylezi'>兔龙蛇马羊猴</span>
</td>
</tr>			




<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>黑白生肖</strong></span>:<span class='stylezi'><strong>白肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	
 

<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>黑白生肖</strong></span>:<span class='stylezi'><strong>白肖</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	
 

 
 


</table>*/
