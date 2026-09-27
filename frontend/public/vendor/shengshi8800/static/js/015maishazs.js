var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

/*
 * 单双中特（mode 28）正确性判定。
 * 厂商原逻辑：高亮条件为「特码号码落在该池内」，而单/双两池合起来恰好覆盖
 * 01..49，条件恒为真；模板又把「准」写死，因此每期都显示为正确。
 * 现改为按「预测的 单/双 == 特码实际 单/双」判定，未开奖不显示「准」。
 * 参数：contentItems（可选，单值时优先）、specialCode、groupOneZodiacs、
 *       groupTwoZodiacs、specialZodiac（后三者用于单双四肖这种双组结构）
 */
window.__parityVerdict = function (contentItems, specialCode, groupOneZodiacs, groupTwoZodiacs, specialZodiac) {
    function actualParity(code) {
        var raw = String(code == null ? '' : code).trim();
        if (!/^\d{1,2}$/.test(raw)) return '';
        var number = parseInt(raw, 10);
        if (!(number >= 1 && number <= 49)) return '';
        return number % 2 === 1 ? '单' : '双';
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
    if (Object.prototype.toString.call(items) !== '[object Array]') items = [];

    var labels = [];
    for (var index = 0; index < items.length; index++) {
        var label = String(items[index]).split('|')[0].trim();
        if (label.indexOf('单') === 0) labels.push('单');
        else if (label.indexOf('双') === 0) labels.push('双');
    }

    var size = actualParity(specialCode);
    if (!size) return 'pending';

    // 单值预测：直接比较
    if (labels.length === 1) {
        return labels[0] === size ? 'ok' : 'miss';
    }

    // 双组生肖结构（单双四肖）：用特码生肖落在哪一组交叉验证
    var one = String(groupOneZodiacs || '').split(',').filter(Boolean);
    var two = String(groupTwoZodiacs || '').split(',').filter(Boolean);
    if (one.length && two.length) {
        var zodiac = String(specialZodiac || '').trim();
        if (!zodiac) return 'unknown';
        if (one.indexOf(zodiac) !== -1) return size === '单' ? 'ok' : 'miss';
        if (two.indexOf(zodiac) !== -1) return size === '双' ? 'ok' : 'miss';
        return 'unknown';
    }

    return 'unknown';
};

$.ajax({
    url: httpApi + `/api/kaijiang/danshuang?web=${web}&type=${type}`,
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
                let result = '00'
                let codeSplit = (d.res_code || '').split(',');
                let sxSplit = (d.res_sx || '').split(',');
                let code = codeSplit[codeSplit.length - 1] || '';
                let sx = sxSplit[sxSplit.length - 1] || '';
                let xiao = [];
                let xiaoV = [];
                let ma = [];
                let content = JSON.parse(d.content);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }
                let c1 = [];
                let b = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (code && xiaoV[i].indexOf(code) !== -1) {
                        b = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}数</span>`);
                    }else {
                        c1.push(`${xiao[i]}数`)
                    }
                }

                // 命中判定：按 单/双 与特码实际单双比较，而不是“特码落在本池内”
                let verdict = window.__parityVerdict(content, code);
                let verdictTxt = verdict === 'ok' ? '准' : (verdict === 'miss' ? '错' : '');
                let shown = c1[0] || '';
                if (verdict === 'ok') {
                    shown = `<span style="background-color: #FFFF00">${xiao[0]}数</span>`;
                }

                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
	    <td width='28%'><font color='#000000'>第${data[i].term}期:</font></td>
	    <td><span class='zl'><font color='#0000FF'>${shown}${shown}${shown}</font></span></td>
	    <td width='24%'><font color='#000000'>开${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}${verdictTxt}</font></td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title' >台湾六合彩论坛『买啥开啥』 </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $("#msks").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});









/*


document.writeln("	 <div class='box pad' id='yxym'>");
document.writeln("		<div class='list-title' >台湾六合彩论坛『买啥开啥』 </div>");
document.writeln("		<table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>");


document.writeln("			<tr>");
document.writeln("				<td width='28%'><font color='#000000'>第269期:</font></td>");
document.writeln("				<td><span class='zl'><font color='#0000FF'>双数双数双数</font></span></td>");
document.writeln("				<td width='24%'><font color='#000000'>开？00</font></td>");
document.writeln("			</tr>");

 
 

document.writeln("			<tr>");
document.writeln("				<td width='28%'><font color='#000000'>第268期:</font></td>");
document.writeln("				<td><span class='zl'><font color='#0000FF'>双数双数双数</font></span></td>");
document.writeln("				<td width='24%'><font color='#000000'>开羊22</font></td>");
document.writeln("			</tr>");

 
 

document.writeln("			<tr>");
document.writeln("				<td width='28%'><font color='#000000'>第267期:</font></td>");
document.writeln("				<td><span class='zl'><font color='#0000FF'>双数双数双数</font></span></td>");
document.writeln("				<td width='24%'><font color='#000000'>开蛇12</font></td>");
document.writeln("			</tr>");

 

document.writeln("			<tr>");
document.writeln("				<td width='28%'><font color='#000000'>第266期:</font></td>");
document.writeln("				<td><span class='zl'><font color='#0000FF'>单数单数单数</font></span></td>");
document.writeln("				<td width='24%'><font color='#000000'>开虎27</font></td>");
document.writeln("			</tr>");






document.writeln("		</table></div>");*/

