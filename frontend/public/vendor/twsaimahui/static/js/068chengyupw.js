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
                // null/undefined 安全的 CSV 解析：`String(null)` 会得到 'null'，会被误判成已开奖。
                let csv = function (v) { return (v === null || v === undefined) ? [] : String(v).split(','); };

                let codeSplit = csv(d.res_code);
                let sxSplit = csv(d.res_sx);
                // 开奖口径：res_code/res_sx 的**最后一项**才是本期特码/特肖
                // （res_code 是本期完整开奖串，与 lottery_draws.numbers 同序，末位即特码）。
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let opened = !!(code && sx);
                let xiao = [];
                let xiaoV = [];
                let ma = [];
                let title = d.title || '';
                let num;
                if (title.indexOf('一') !== -1) {
                    num = 1;
                }else if (title.indexOf('二') !== -1) {
                    num = 2;
                }else if (title.indexOf('三') !== -1) {
                    num = 3;
                }else if (title.indexOf('四') !== -1) {
                    num = 4;
                }else if (title.indexOf('五') !== -1) {
                    num = 5;
                }else if (title.indexOf('六') !== -1) {
                    num = 6;
                }else if (title.indexOf('七') !== -1) {
                    num = 7;
                }else if (title.indexOf('八') !== -1) {
                    num = 8;
                }else if (title.indexOf('九') !== -1) {
                    num = 9;
                }else if (title.indexOf('零') !== -1) {
                    num = 0;
                }else {
                    continue
                }
                num +=''
                // 命中口径（平特尾）：本期**七个开奖号码**里任一号码的尾数 == 成语对应尾数即命中，
                // 不是只看最后一个特码。只看特码会漏判：
                //   190 期【零珠片玉】(零 → 尾 0)，20 是平码、尾数 0，旧口径按特码 45 判「错」；
                //   271 期【六道轮回】(六 → 尾 6)，第一个开奖号码 36 的尾数就是 6。
                let zj = false;
                if (opened) {
                    for (let k = 0; k < codeSplit.length; k++) {
                        let digits = String(codeSplit[k] || '').replace(/[^0-9]/g, '');
                        if (digits && digits.charAt(digits.length - 1) === num) {
                            zj = true;
                            break;
                        }
                    }
                }

                // 命中时把**预测的成语**标黄：平特尾的命中项是「预测的那一位尾数」本身，
                // 而命中的号码可能是平码（特码不一定是它），照旧标黄特码会给出假命中标记。
                // 开奖段固定显示本期真实特码；未开奖只显示「开:待开奖」，不判定、不高亮。
                let titleHtml = zj
                    ? `<span style="background-color:#FFFF00">${title}</span>`
                    : `${title}`;
                let resTxt;
                if (!opened) {
                    resTxt = '开:待开奖';
                } else {
                    resTxt = `开:${sx}${code}${zj ? '准' : '错'}`;
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>成语平特尾</strong></span>:【<span class='stylezi'><strong>${titleHtml}</strong></span><strong>】 ${resTxt}
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
