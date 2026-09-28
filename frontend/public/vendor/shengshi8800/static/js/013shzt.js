var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/getXingte?web=${web}&type=${type}&num=3`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {

        let htmlBox = '',htmlBoxList = '',term=''

        let data = response.data
        if(data.length>0){
            for(let i in data){
                let result = '00'
                let d = data[i];
                let resCode = data[i].res_code.split(",");
                let resSx = data[i].res_sx.split(",");
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = [];
                // content 兜底解析：后端 content 在部分 mode/期次上不是 JSON（纯中文串 / `标签|值` / 逗号串），
                // 旧写法 JSON.parse 抛错会中断 success 回调，让整个模块容器保持空白。改用 util.js 的 parseContentList。
                // 只取标签（= 预测的三行）：标签后的号码清单不参与判定与高亮，
                // 历史遗留行的清单是按生肖五行拼的（见下面的判定注释）。
                let content = parseContentList(d.content);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                }
                let c = [];
                // 判定与高亮必须同源，且**只按特码号码的五行**（mode 53 = 三行中特 /
                // 灭庄三行）：命中 = 特码号码所属五行 ∈ 预测三行；高亮只点亮命中的那一行。
                // 不得再拿生肖五行判定，也不得再用正文里每个标签后的号码清单点行 ——
                // 历史遗留的 mode 53 正文号码清单是按**生肖五行**拼的（`土|03,06,…,24,…`
                // 里含 24，而 24 的号码五行是木），照它点行会点错行、判定会误「准」。
                // 权威口径见 legacy-prediction-verdict.js 的 ELEMENT_NUMBER_GROUPS
                // （= backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS）。
                let __verdict = window.legacyPredictionVerdict ? window.legacyPredictionVerdict.verdictOf(53, d) : 'unknown';
                let __verdictTxt = window.legacyPredictionVerdict ? window.legacyPredictionVerdict.verdictText(__verdict) : '';
                let __hitElement = window.legacyPredictionVerdict ? window.legacyPredictionVerdict.hitElementOf(53, d) : '';
                // 与判定层用同一个标签归一化，避免「判了准却一行都没点亮」。
                let __normalize = window.legacyPredictionVerdict && window.legacyPredictionVerdict.normalizeElementLabel
                    ? window.legacyPredictionVerdict.normalizeElementLabel
                    : function (value) { return String(value == null ? '' : value).trim(); };
                for (let i = 0; i < xiao.length; i++) {
                    if (__hitElement && __normalize(xiao[i]) === __hitElement) {
                        c.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c.push(`${xiao[i]}`)
                    }
                }

                // let wei = parseInt()
                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
    
     
    <tr>
    <td>
        <font color='#0000FF'>${d.term}期:</font>
        <font color='#000000'>灭庄三行<span class='zl'>&laquo;</span></font><span class='zl'>${c.join('')}<font color='#000000'>&raquo;</font>
        </span>
        <font color='#000000'>开:</font>
            ${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}${__verdictTxt}
            <font color='#000000'></span>
        </font>
    </td>
    </tr>
    
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
<div class='list-title'>台湾六合彩论坛『三行中特』</div>
    <span class='zl'>』 </div>
    <table border='1' width='100%' class='duilianpt' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1728'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $(".sxzt").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});


/*

document.writeln("	");
document.writeln("	<div class='box pad\' id=\'yxym\'>");
document.writeln("		<div class=\'list-title\'>台湾六合彩论坛『三行中特』</div>");
document.writeln("		<table border=\'1\' width=\'100%\' class=\'duilianpt\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\' id=\'table1728\'>");
document.writeln("	");
document.writeln("");
document.writeln("");
document.writeln("");

 
 
   
 
 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#0000FF\'>269期:</font><font color=\'#000000\'>灭庄三行<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'>火土水<font color=\'#000000\'>&raquo;</font></span><font color=\'#000000\'>开:</font>？00准<font color=\'#000000\'></span></font></td>");
document.writeln("			</tr>	");

 
 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#0000FF\'>268期:</font><font color=\'#000000\'>灭庄三行<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'><span style=\'background-color: #FFFF00\'>木</span>水土<font color=\'#000000\'>&raquo;</font></span><font color=\'#000000\'>开:</font>羊22准<font color=\'#000000\'></span></font></td>");
document.writeln("			</tr>	");


 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#0000FF\'>267期:</font><font color=\'#000000\'>灭庄三行<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'><span style=\'background-color: #FFFF00\'>水</span>土火<font color=\'#000000\'>&raquo;</font></span><font color=\'#000000\'>开:</font>蛇12准<font color=\'#000000\'></span></font></td>");
document.writeln("			</tr>	");


 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#0000FF\'>266期:</font><font color=\'#000000\'>灭庄三行<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'>木金<span style=\'background-color: #FFFF00\'>土</span><font color=\'#000000\'>&raquo;</font></span><font color=\'#000000\'>开:</font>虎27准<font color=\'#000000\'></span></font></td>");
document.writeln("			</tr>	");

 
 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#0000FF\'>265期:</font><font color=\'#000000\'>灭庄三行<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'>木水<span style=\'background-color: #FFFF00\'>火</span><font color=\'#000000\'>&raquo;</font></span><font color=\'#000000\'>开:</font>牛16准<font color=\'#000000\'></span></font></td>");
document.writeln("			</tr>	");

 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#0000FF\'>264期:</font><font color=\'#000000\'>灭庄三行<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'>金<span style=\'background-color: #FFFF00\'>火</span>土<font color=\'#000000\'>&raquo;</font></span><font color=\'#000000\'>开:</font>猪30准<font color=\'#000000\'></span></font></td>");
document.writeln("			</tr>	");

 
 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#0000FF\'>263期:</font><font color=\'#000000\'>灭庄三行<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'>火<span style=\'background-color: #FFFF00\'>水</span>土<font color=\'#000000\'>&raquo;</font></span><font color=\'#000000\'>开:</font>龙13准<font color=\'#000000\'></span></font></td>");
document.writeln("			</tr>	");




document.writeln("");
document.writeln("		</table></div>");*/

