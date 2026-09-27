var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/getShaXiao?web=${web}&type=${type}&num=3`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {

        let htmlBox = '',htmlBoxList = '',term=''

        let data = response.data

        if(data.length>0){
            for(let i in data){
                let d = data[i];
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

                // 绝杀三肖（mode 42）是排除玩法：特肖不在候选 3 肖里才算杀中。
                // 厂商原文在杀中时给整组候选加黄底，这里沿用同一表现，并补上「准/错」。
                let verdict = window.legacyPredictionVerdict
                    ? window.legacyPredictionVerdict.verdictOf(42, d)
                    : 'unknown';
                let verdictTxt = window.legacyPredictionVerdict
                    ? window.legacyPredictionVerdict.verdictText(verdict)
                    : '';
                let pool = xiao.join('');
                let c1 = verdict === 'ok'
                    ? `<span style="background-color: #FFFF00">${pool}</span>`
                    : pool;
                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
        <td>
            <font color='#000000'>${d.term}期:</font>
            <font color='#0000FF'>绝杀→<span class='zl'>[${c1}]</span> </font>
            开:${sx||'？'}${code||'00'}${verdictTxt}
        </td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title' >台湾六合彩→<font color='#FF0000'>【</font>绝杀三肖<font color='#FF0000'>】</font>→ </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $(".jssx").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});








/*

document.writeln("  <div class='box pad' id='yxym'>");
document.writeln("  <div class='box pad' id='yxym'>");
document.writeln("        <div class='list-title' >台湾六合彩→<font color='#FF0000'>【</font>绝杀三肖<font color='#FF0000'>】</font>→ </div>");
document.writeln("        <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>");
document.writeln("		");
document.writeln("			");
document.writeln("		");

document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>269期:</font><font color='#0000FF'>绝杀→<span class='zl'>[<span style='background-color: #FFFF00'>鼠牛马</span>]</span> </font>开:？00</td>");
document.writeln("			</tr>");

 
document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>268期:</font><font color='#0000FF'>绝杀→<span class='zl'>[<span style='background-color: #FFFF00'>猴蛇猪</span>]</span> </font>开:羊22</td>");
document.writeln("			</tr>");


 
document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>266期:</font><font color='#0000FF'>绝杀→<span class='zl'>[<span style='background-color: #FFFF00'>猪羊蛇</span>]</span> </font>开:虎27</td>");
document.writeln("			</tr>");

 
document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>265期:</font><font color='#0000FF'>绝杀→<span class='zl'>[<span style='background-color: #FFFF00'>鸡狗羊</span>]</span> </font>开:牛16</td>");
document.writeln("			</tr>");

 
 
document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>264期:</font><font color='#0000FF'>绝杀→<span class='zl'>[<span style='background-color: #FFFF00'>牛兔鸡</span>]</span> </font>开:猪30</td>");
document.writeln("			</tr>");

document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>263期:</font><font color='#0000FF'>绝杀→<span class='zl'>[<span style='background-color: #FFFF00'>兔鸡马</span>]</span> </font>开:龙13</td>");
document.writeln("			</tr>");

 
document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>262期:</font><font color='#0000FF'>绝杀→<span class='zl'>[<span style='background-color: #FFFF00'>羊虎马</span>]</span> </font>开:鸡44</td>");
document.writeln("			</tr>");

 

 


 



document.writeln("			");
document.writeln("			</table>");
document.writeln("    </div>");*/

