var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

/*
 * 大小中特（mode 57）正确性判定。
 * 厂商原逻辑：高亮条件为「特码号码落在该池内」，而大/小两池合起来恰好覆盖
 * 01..49，条件恒为真；模板又写死「准」，因此每期都显示为正确。
 * 现改为按「预测的 大/小 == 特码实际 大/小」判定，未开奖不显示「准」。
 */
window.__sizeVerdict = function (contentItems, specialCode) {
    function actualSize(code) {
        var raw = String(code == null ? '' : code).trim();
        if (!/^\d{1,2}$/.test(raw)) return '';
        var number = parseInt(raw, 10);
        if (!(number >= 1 && number <= 49)) return '';
        return number >= 25 ? '大' : '小';
    }

    var items = [];
    if (Object.prototype.toString.call(contentItems) === '[object Array]') {
        items = contentItems;
    } else if (contentItems != null && String(contentItems) !== '') {
        try {
            items = JSON.parse(contentItems);
        } catch (error) {
            items = String(contentItems).indexOf('|') !== -1 ? [String(contentItems)] : [];
        }
    }
    if (Object.prototype.toString.call(items) !== '[object Array]') return 'unknown';

    var labels = [];
    for (var index = 0; index < items.length; index++) {
        var label = String(items[index]).split('|')[0].trim();
        if (label.indexOf('大') === 0) labels.push('大');
        else if (label.indexOf('小') === 0) labels.push('小');
    }
    if (labels.length !== 1) return 'unknown';

    var size = actualSize(specialCode);
    if (!size) return 'pending';
    return labels[0] === size ? 'ok' : 'miss';
};

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
                let content = JSON.parse(d.content);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    maValue[i] = c[1];
                    ma.push(...c[1].split(','));
                }
                let c = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (code && maValue[i].indexOf(code) !== -1) {
                        c.push(`<span style="background-color: #FFFF00">${xiao[i]}数</span>`);
                    }else {
                        c.push(`${xiao[i]}数`)
                    }
                }

                // 命中判定：按 大/小 与特码实际大小比较，而不是“特码落在本池内”
                let verdict = window.__sizeVerdict(content, code);
                let verdictTxt = verdict === 'ok' ? '准' : (verdict === 'miss' ? '错' : '');
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

