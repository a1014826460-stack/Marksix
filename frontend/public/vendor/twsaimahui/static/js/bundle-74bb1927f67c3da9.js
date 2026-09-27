/* twsaimahui 模块脚本合并包（顺序与原文档一致）
 *   static/js/054sbanbo.js
 *   static/js/055sbands.js
 */
$.ajax({
    url: httpApi + `/api/kaijiang/getShaBanbo?web=${web}&type=${type}&num=1`,
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
                let ma = [];
                let content = safeParseJSON(d.content, []);
                for (let j in content) {
                    let c = String(content[j]||'').split('|');
                    if (!c[0]) continue;
                    xiao.push(c[0])
                    xiaoV[xiao.length-1] = c[1] || '';
                    ma.push(...String(c[1]||'').split(','));
                }

                // 绝杀语义：杀掉的半波号码集合「不含」开奖特码 = 命中 = 准；含 = 错。
                // 未开奖不判定、不高亮。
                let c1 = [];
                let hitAny = false;
                for (let k = 0; k < xiao.length; k++) {
                    if (opened && code && xiaoV[k] && xiaoV[k].indexOf(code) !== -1) { hitAny = true; }
                    c1.push(`<span>${xiao[k]}</span>`);
                }
                let zj = opened && !hitAny;

                let resHtml = opened
                    ? (`开:${sx}${code}${zj ? '准' : '错'}`)
                    : '开:待开奖';

                htmlBoxList += ` 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>${c1.join('')}</strong></span><strong>】 ${resHtml}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀半波</font></font></font></b></td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l68").html(htmlBoxList)
        applyLotteryRegionTitlePrefix(document.querySelector('.l68'))
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀半波</font></font></font></b></td>
</tr>












<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>绿双</strong></span><strong>】 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>绿双</strong></span><strong>】 开:蛇12准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>红双</strong></span><strong>】 开:虎27准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>蓝单</strong></span><strong>】 开:牛16准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>蓝单</strong></span><strong>】 开:猪30准
</strong>
</td>
</tr>	

 

<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>红双</strong></span><strong>】 开:鸡44准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>绿双</strong></span><strong>】 开:龙01准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
260期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>蓝双</strong></span><strong>】 开:牛40准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
259期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>红双</strong></span><strong>】 开:鼠29准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
258期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>绿单</strong></span><strong>】 开:牛40准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
257期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>蓝单</strong></span><strong>】 开:鸡08准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
256期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>红单</strong></span><strong>】 开:虎39准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
255期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>绿单</strong></span><strong>】 开:猪30准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
254期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>红双</strong></span><strong>】 开:虎27准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
253期</strong><span class='styleliao'><strong>绝杀半波</strong></span>:【<span class='stylezi'><strong>红单</strong></span><strong>】 开:马47准
</strong>
</td>
</tr>	

  

 */

;
$.ajax({
    url: httpApi + `/api/kaijiang/getShaBds?web=${web}&type=${type}&num=1`,
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
                let ma = [];
                let content = safeParseJSON(d.content, []);
                for (let j in content) {
                    let c = String(content[j]||'').split('|');
                    if (!c[0]) continue;
                    xiao.push(c[0])
                    xiaoV[xiao.length-1] = c[1] || '';
                    ma.push(...String(c[1]||'').split(','));
                }

                // 绝杀语义：杀掉的半单双号码集合「不含」开奖特码 = 命中 = 准；含 = 错。
                // 未开奖不判定、不高亮。
                let c1 = [];
                let hitAny = false;
                for (let k = 0; k < xiao.length; k++) {
                    if (opened && code && xiaoV[k] && xiaoV[k].indexOf(code) !== -1) { hitAny = true; }
                    c1.push(`<span>${xiao[k]}</span>`);
                }
                let zj = opened && !hitAny;

                let resHtml = opened
                    ? (`开:${sx}${code}${zj ? '准' : '错'}`)
                    : '开:待开奖';

                htmlBoxList += ` 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>绝杀半单双</strong></span>:【<span class='stylezi'><strong>${c1.join('')}</strong></span><strong>】 ${resHtml}
</strong>
</td>
</tr>
 
            `
            }
        }
        htmlBoxList = `
<style>
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
</style>
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀半单双</font></font></font></b></td>
</tr>
	

            ${htmlBoxList}
            </table>
        `;
        $(".l69").html(htmlBoxList)
        applyLotteryRegionTitlePrefix(document.querySelector('.l69'))
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀半单双</font></font></font></b></td>
</tr>







<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>绝杀半单双</strong></span>:【<span class='stylezi'><strong>大双</strong></span><strong>】 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>绝杀半单双</strong></span>:【<span class='stylezi'><strong>大双</strong></span><strong>】 开:蛇12准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>绝杀半单双</strong></span>:【<span class='stylezi'><strong>小双</strong></span><strong>】 开:猪30准
</strong>
</td>
</tr>	
 
  
  
  

</table>*/

