var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

/*
 * 大小中特（mode 57）正确性判定。
 * 厂商原逻辑：高亮条件为「特码号码落在该池内」，而大/小两池合起来恰好覆盖
 * 01..49，条件恒为真；模板又写死「准」，因此每期都显示为正确。
 * 现统一走 legacy-prediction-verdict.js 的 mode 57 口径：
 * 「预测的 大/小 == 特码实际 大/小」才算命中，未开奖不显示判定。
 *
 * 这里曾定义全局 `window.__sizeVerdict`，与 dx.js（大小中特带1头）的同名全局
 * 互相覆盖；两者实现相同所以未暴露问题，现已移除并统一使用
 * window.legacyPredictionVerdict，避免跨模块全局名冲突。
 */

$.ajax({
    url: httpApi + `/api/kaijiang/getDxzt?web=${web}&type=${type}&num=1`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {

        let htmlBox = '',htmlBoxList = '',term=''

        let data = response.data

        if(data.length>0){
            for(let i in data){
                let d = data[i];
                let resCode = data[i].res_code.split(",");
                let resSx = data[i].res_sx.split(",");
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = [];
                let ma = [];
                let maValue = [];
                // content 兜底解析：后端 content 在部分 mode/期次上不是 JSON（纯中文串 / `标签|值` / 逗号串），
                // 旧写法 JSON.parse 抛错会中断 success 回调，让整个模块容器保持空白。改用 util.js 的 parseContentList。
                let content = parseContentList(d.content);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    maValue[i] = c[1] || '';
                    ma.push(...(c[1] || '').split(','));
                }
                let c = [];
                // 大/小两池合起来覆盖 01..49，按号码落池高亮恒为真，因此这里只输出标签，
                // 高亮统一由命中判定决定。
                for (let i = 0; i < xiao.length; i++) {
                    c.push(`${xiao[i]}数`)
                }

                // 命中判定：按 大/小 与特码实际大小比较，而不是“特码落在本池内”
                let verdict = window.legacyPredictionVerdict
                    ? window.legacyPredictionVerdict.verdictOf(57, d)
                    : 'unknown';
                let verdictTxt = verdict === 'ok' ? '准' : (verdict === 'miss' ? '错' : '');
                if (verdict === 'ok') {
                    c[0] = `<span style="background-color: #FFFF00">${xiao[0]}数</span>`;
                }
                let resTxt = (code && resSx[resSx.length-1])
                    ? `${resSx[resSx.length-1]}${code}`
                    : '？00';

                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
	    <td>
            <font color='#0000FF'>${data[i].term}期:</font><font color='#000000'>精准大小</font>
            <span class='zl'><font color='#000000'>〔〔</font>${c.join('')}<font color='#000000'>〕〕</font></span>
            <font color='#000000'>开</font>${resTxt}<font color='#000000'>${verdictTxt}</font>
        </td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title'>台湾六合彩论坛『大小中特』 </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1784'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $(".dxzt").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});
/*

document.writeln("");
document.writeln("");
document.writeln("<div class=\'box pad\' id=\'yxym\'>");
document.writeln("");
document.writeln("");
document.writeln("<div class=\'list-title\'>台湾六合彩论坛『大小中特』 </div>");
document.writeln("<table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\'>");

document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>269期:</font><font color=\'#000000\'>精准大小</font><span class=\'zl\'><font color=\'#000000\'>〔〔</font>大数<font color=\'#000000\'>〕〕</font></span>");
document.writeln("<font color=\'#000000\'>开</font>？00准</td>");
document.writeln("</tr>");
 
 
document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>268期:</font><font color=\'#000000\'>精准大小</font><span class=\'zl\'><font color=\'#000000\'>〔〔</font>小数<font color=\'#000000\'>〕〕</font></span>");
document.writeln("<font color=\'#000000\'>开</font>羊22准</td>");
document.writeln("</tr>");
 

document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>267期:</font><font color=\'#000000\'>精准大小</font><span class=\'zl\'><font color=\'#000000\'>〔〔</font>小数<font color=\'#000000\'>〕〕</font></span>");
document.writeln("<font color=\'#000000\'>开</font>蛇12准</td>");
document.writeln("</tr>");
 

document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>266期:</font><font color=\'#000000\'>精准大小</font><span class=\'zl\'><font color=\'#000000\'>〔〔</font>大数<font color=\'#000000\'>〕〕</font></span>");
document.writeln("<font color=\'#000000\'>开</font>虎27准</td>");
document.writeln("</tr>");
 

document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>265期:</font><font color=\'#000000\'>精准大小</font><span class=\'zl\'><font color=\'#000000\'>〔〔</font>小数<font color=\'#000000\'>〕〕</font></span>");
document.writeln("<font color=\'#000000\'>开</font>牛16准</td>");
document.writeln("</tr>");
 

document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>264期:</font><font color=\'#000000\'>精准大小</font><span class=\'zl\'><font color=\'#000000\'>〔〔</font>大数<font color=\'#000000\'>〕〕</font></span>");
document.writeln("<font color=\'#000000\'>开</font>猪30准</td>");
document.writeln("</tr>");
 

document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>263期:</font><font color=\'#000000\'>精准大小</font><span class=\'zl\'><font color=\'#000000\'>〔〔</font>小数<font color=\'#000000\'>〕〕</font></span>");
document.writeln("<font color=\'#000000\'>开</font>龙13准</td>");
document.writeln("</tr>");
 



document.writeln("");
document.writeln("");
document.writeln("</table></div>");
document.writeln("");*/

