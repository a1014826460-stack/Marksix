var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/getPingte?web=${web}&type=${type}&num=1`,
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
                let result = '00'
                let c1 = '';

                let index = getZjIndex(d.content,resSx);
                if (index !== undefined) {
                    c1 += `<span style="background-color: #FFFF00">${d.content}</span>`;
                }else {
                    c1+=`${d.content}`
                }


                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
	    <td>
            <font color='#0000FF'>${data[i].term}期:</font><font color='#000000'>平特一肖</font>
            <span class='zl'><font color='#000000'>&laquo;&laquo;</font>${c1}${c1}${c1}<font color='#000000'>&raquo;&raquo;</font></span>
            <font color='#000000'>开</font>${resCode[index]||'00'}准
        </td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title'>台湾六合彩论坛『平特一肖』 </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1784'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $(".ptyx").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});



/*

document.writeln("");
document.writeln("<div class='box pad\' id=\'yxym\'>");
document.writeln("<div class=\'list-title\'>台湾六合彩论坛『平特一肖』 </div>");
document.writeln("<table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\' id=\'table1784\'>");


document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>269期:</font><font color=\'#000000\'>平特一肖</font><span class=\'zl\'><font color=\'#000000\'>&laquo;&laquo;</font>鼠鼠鼠<font color=\'#000000\'>&raquo;&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>00准</td>");
document.writeln("</tr>");

 
document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>267期:</font><font color=\'#000000\'>平特一肖</font><span class=\'zl\'><font color=\'#000000\'>&laquo;&laquo;</font>龙龙龙<font color=\'#000000\'>&raquo;&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>01准</td>");
document.writeln("</tr>");


document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>265期:</font><font color=\'#000000\'>平特一肖</font><span class=\'zl\'><font color=\'#000000\'>&laquo;&laquo;</font>马马马<font color=\'#000000\'>&raquo;&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>23准</td>");
document.writeln("</tr>");

 
 
document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>264期:</font><font color=\'#000000\'>平特一肖</font><span class=\'zl\'><font color=\'#000000\'>&laquo;&laquo;</font>鸡鸡鸡<font color=\'#000000\'>&raquo;&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>44准</td>");
document.writeln("</tr>");



document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>261期:</font><font color=\'#000000\'>平特一肖</font><span class=\'zl\'><font color=\'#000000\'>&laquo;&laquo;</font>羊羊羊<font color=\'#000000\'>&raquo;&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>10准</td>");
document.writeln("</tr>");


document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>260期:</font><font color=\'#000000\'>平特一肖</font><span class=\'zl\'><font color=\'#000000\'>&laquo;&laquo;</font>马马马<font color=\'#000000\'>&raquo;&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>23准</td>");
document.writeln("</tr>");



document.writeln("");
document.writeln("</table></div>");*/

