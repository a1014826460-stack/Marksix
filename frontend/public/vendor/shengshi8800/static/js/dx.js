var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

/*
 * 大数小数（mode 108）正确性判定。
 * 厂商原逻辑：高亮条件为「特码号码落在该池内」，而大/小两池合起来恰好覆盖
 * 01..49，条件恒为真；`getResult()` 又写死「准」，因此每期都显示为正确。
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

document.writeln("<div class=\"list-title\">台湾大小中特</div><table class=\"ptyx11\" width=\"100%\" border=\"1\">");
// document.writeln("  <tr>");
// document.writeln("    <th>台湾大小中特</th>");
// document.writeln("  </tr>");
document.writeln(" ");
document.writeln("");
document.writeln("  </tr>");
document.writeln("  ");
document.writeln("");


document.writeln("<table id='dxzt'  border=1 width=100% bgcolor=#ffffff style='font-weight:bold'><tbody></tbody></table>");

// 


// document.writeln("    <tr>");
// document.writeln("    <td class=\"td\">");
// document.writeln("	<p align=\"center\">269期:<font color=\"#0000FF\">大数小数</font><font color=\"#FF0000\">【大数+0头】</font>开？00准</td>");
// document.writeln("  </tr>");

$.ajax({
    url: httpApi + `/api/kaijiang/getDxztt1?num=1&web=${web}&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        if(response.data.length > 0){
            let html = ""
            let w = ''
            let dx = ''
            let dx_ = ''
            let t = ''
            let code = ''
            let tm = ''

            response.data.forEach(el=>{
                tm = code=dx=dx_=w=''
                t= JSON.parse(el.tou)[0][0]
                w = selTxtBcT2(t,el.res_code)
                if(null != el.res_code && el.res_code.length>0){
                    code = el.res_code.split(',')
                    tm = code[code.length-1]
                }
                var items = JSON.parse(el.content)
                dx = items[0].split('|')

                // 命中判定：按 大/小 与特码实际大小比较，而不是“特码落在本池内”
                var verdict = window.__sizeVerdict(items, tm)
                var verdictTxt = verdict === 'ok' ? '准' : (verdict === 'miss' ? '错' : '')
                if(verdict === 'ok'){
                    dx_ = `<span style="background-color: #FFFF00">${dx[0]}数</span>`
                }else{
                    dx_ = dx[0]+'数'
                }
                var resTxt = tm ? ('' + (el.res_sx ? el.res_sx.split(',').pop() : '') + tm) : '？00'
                dx = ''
                html += `<tr>
                            <td class="td">
                                <p align="center">${el.term}期:<font color="#0000FF">大数小数</font><font color="#FF0000">【${dx_}+${w}】</fon>开<font color="#000000">${resTxt}${verdictTxt}</font>
                            </td>
                        </tr>`
            })
            
            $("#dxzt").html(replaceLegacySiteText(html))
        }
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});


 
  
document.writeln("</table>");

