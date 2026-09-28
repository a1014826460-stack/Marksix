
$.ajax({
    url: httpApi + `/api/kaijiang/danshuang?web=${web}&type=${type}&num=2`,
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
                // 开奖口径：res_code/res_sx 的**最后一项**才是本期特码/特肖
                // （res_code 是本期完整开奖串，与 lottery_draws.numbers 同序，末位即特码）。
                let codeSplit = csv(d.res_code);
                let sxSplit = csv(d.res_sx);
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let opened = !!(code && sx);
                let xiao = [];
                let xiaoV = [];
                let ma = [];
                let content = safeParseJSON(d.content, []);
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = String(content[i]||'').split('|');
                    xiao.push(c[0])
                    xiaoV[xiao.length-1] = c[1] || '';
                    ma.push(...String(c[1]||'').split(','));
                }

                // 命中口径：本期特码落在预测的单/双号码集合内。
                // 高亮与判定绑定：只有命中的那一行才把命中的「单/双数」标黄；
                // 判「错」的行一律没有黄色高亮（旧写法把黄底写在开奖段的 font 上）。
                let c = [];
                let zj = false;
                for (let j = 0; j < xiao.length; j++) {
                    if (opened && code && xiaoV[j].indexOf(code) !== -1) {
                        zj = true;
                        c.push(`<span style="background-color:#FFFF00">${xiao[j]}数</span>`)
                    }else{
                        c.push(`${xiao[j]}数`)
                    }
                }

                let resHtml = opened
                    ? (zj
                        ? `开:<span style="background-color:#FFFF00">${sx}${code}</span>准`
                        : `开:${sx}${code}错`)
                    : '开:待开奖';


                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>单双中特</strong></span>:【<span class='stylezi'><strong>${c.join('')}</strong></span><strong>】 ${resHtml}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双中特</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【明年今日】【单双中特】</span>
</td>
</tr>\t

            ${htmlBoxList}
            </table>
        `;
        $(".l7").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});

/*


<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双中特</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【明年今日】【单双中特】</span>
</td>
</tr>		

















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>单双中特</strong></span>:【<span class='stylezi'><strong>单数</strong></span><strong>】 开:？00准
</strong>
</td>
</tr>	

 
 
 

 

</table>*/
