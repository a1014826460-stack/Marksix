$.ajax({
    url: httpApi + `/api/kaijiang/getShama?web=${web}&type=${type}&num=7`,
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
                // null/undefined 安全的 CSV 解析：`String(null)` 会得到 'null'，会被误判成已开奖。
                let csv = function (v) { return (v === null || v === undefined) ? [] : String(v).split(','); };
                // 开奖口径：res_code/res_sx 第 1 项 = 本期特码/特肖（已交叉验证）。
                let codeSplit = csv(d.res_code);
                let sxSplit = csv(d.res_sx);
                let code = codeSplit[0]||'';
                let sx = sxSplit[0]||'';
                let opened = !!(code && sx);
                let xiao = [];
                let xiaoV = [];
                let ma = (d.content === null || d.content === undefined) ? [] : String(d.content).split(',');

                // 绝杀语义：杀掉的 7 个号码「全部都不含」开奖特码 = 命中 = 准；
                // 只要开奖特码出现在杀号里 = 错。
                // 旧写法用「只要有一项不含就判准」，且缺少已开奖前置判断，
                // 导致未开奖期也可能被判成「准」。
                let c1 = [];
                let hitAny = false;
                for (let k = 0; k < ma.length; k++) {
                    if (opened && code && ma[k] && ma[k].indexOf(code) !== -1) { hitAny = true; }
                    c1.push(`<span>${ma[k]}</span>`);
                }
                let zj = opened && !hitAny;

                let resHtml = opened
                    ? (`开:${sx}${code}${zj ? '准' : '错'}`)
                    : '开:待开奖';

                htmlBoxList += ` 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>${c1.join('.')}</span><strong>】
 ${resHtml}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀七码</font></font></font></b></td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l45").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀七码</font></font></font></b></td>
</tr>











<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>03.20.24.25.26.27.28</span><strong>】
开:？00准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>05.09.24.28.36.38.42</span><strong>】
开:蛇12准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>08.09.12.26.29.30.37</span><strong>】
开:虎27准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>05.06.07.19.30.31.35</span><strong>】
开:牛16准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>16.19.20.21.22.23.24</span><strong>】
开:猪30准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>26.39.40.41.42.46.47</span><strong>】
开:龙13准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>26.27.28.37.39.40.43</span><strong>】
开:鸡44准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>13.24.25.28.29.39.42</span><strong>】
开:龙01准
</strong>
</td>
</tr>	

  
 
 
 


</table>*/
