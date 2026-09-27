var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

/*
 * 大数小数（mode 108）正确性判定。
 * 厂商原逻辑：高亮条件为「特码号码落在该池内」，而大/小两池合起来恰好覆盖
 * 01..49，条件恒为真；`getResult()` 又写死「准」，因此每期都显示为正确。
 * 现统一走 legacy-prediction-verdict.js 的 mode 108 口径：
 * 「预测的 大/小 == 特码实际 大/小」才算命中，未开奖不显示判定。
 *
 * 这里曾定义全局 `window.__sizeVerdict`，与 003dxzt.js（大小中特）的同名全局
 * 互相覆盖；两者实现相同所以未暴露问题，现已移除并统一使用
 * window.legacyPredictionVerdict，避免跨模块全局名冲突。
 */

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
                var verdict = window.legacyPredictionVerdict
                    ? window.legacyPredictionVerdict.verdictOf(108, el)
                    : 'unknown';
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

