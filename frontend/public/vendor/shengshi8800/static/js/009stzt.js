var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/getTou?web=${web}&type=${type}&num=3`,
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
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = [];
                let ma = [];
                let content = JSON.parse(d.content);
                let wei = [];
                let weiNum = [];
                let weiValue = [];
                for (let i = 0; i < content.length; i++) {
                    wei[i] = content[i].split('|')[0];
                    weiNum[i] = content[i].split('|')[0].split('')[0];
                    weiValue[i] = content[i].split('|')[1];
                }
                let c1 = ``;
                for (let i = 0; i < wei.length; i++) {
                    if (code && weiValue[i].indexOf(code) !== -1) {
                        c1 += `<span style="background-color: #FFFF00">${weiNum[i]}头</span>`;
                    }else {
                        c1+=`${weiNum[i]}头`
                    }
                }


                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
      <td>
        <font color='#0000FF'>${data[i].term}期:</font>
        <font color='#000000'>台湾三头<span class='zl'>&laquo;</span></font><span class='zl'>${c1}<font color='#000000'>&raquo;</font></span>
        <font color='#000000'>开</font>${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}准
      </td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title'>台湾六合彩论坛『三头中特』</div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1790'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $(".stzt").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});





/*

document.writeln("");
document.writeln("<div class='box pad\' id=\'yxym\'>");
document.writeln("<div class=\'list-title\'>台湾六合彩论坛『三头中特』</div>");
document.writeln("<table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\' id=\'table1790\'>");



document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>269期:</font><font color=\'#000000\'>台湾三头<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'>0头3头4头<font color=\'#000000\'>&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>？00准</td>");
document.writeln("</tr>");


document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>268期:</font><font color=\'#000000\'>台湾三头<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'>1头<span style=\'background-color: #FFFF00\'>2</span>头3头<font color=\'#000000\'>&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>羊22准</td>");
document.writeln("</tr>");


document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>266期:</font><font color=\'#000000\'>台湾三头<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'><span style=\'background-color: #FFFF00\'>2</span>头3头4头<font color=\'#000000\'>&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>虎27准</td>");
document.writeln("</tr>");


document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>265期:</font><font color=\'#000000\'>台湾三头<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'>0头<span style=\'background-color: #FFFF00\'>1</span>头3头<font color=\'#000000\'>&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>牛16准</td>");
document.writeln("</tr>");


document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>262期:</font><font color=\'#000000\'>台湾三头<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'>1头3头<span style=\'background-color: #FFFF00\'>4</span>头<font color=\'#000000\'>&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>鸡44准</td>");
document.writeln("</tr>");


document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>261期:</font><font color=\'#000000\'>台湾三头<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'><span style=\'background-color: #FFFF00\'>0</span>头2头4头<font color=\'#000000\'>&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>龙01准</td>");
document.writeln("</tr>");


document.writeln("<tr>");
document.writeln("<td><font color=\'#0000FF\'>259期:</font><font color=\'#000000\'>台湾三头<span class=\'zl\'>&laquo;</span></font><span class=\'zl\'>1头<span style=\'background-color: #FFFF00\'>2</span>头4头<font color=\'#000000\'>&raquo;</font></span>");
document.writeln("<font color=\'#000000\'>开</font>鼠29准</td>");
document.writeln("</tr>");









document.writeln("");
document.writeln("");
document.writeln("");
document.writeln("</table></div>");*/

