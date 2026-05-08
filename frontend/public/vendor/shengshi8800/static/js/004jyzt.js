var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/getJyzt?web=${web}&type=${type}&num=2`,
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
                let xiao =  [];
                let xiaoV =  [];
                let ma = [];
                let content = JSON.parse(d.content);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (code && xiaoV[i].indexOf(code) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }



                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
        <td><font color='#0000FF'>${d.term}期:</font><font color='#000000'>火爆家野<span class='zl'>〈〈</span></font><span class='zl'>${c1[0]}<font color='#000000'>〉〉</font></span>
        <font color='#000000'>准</font>${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}准</td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title'>台湾六合彩论坛『家野中特』 </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1776'>
    `+htmlBoxList+`
 </table>
</div>

`
        $(".jyzt").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});
/*

document.writeln("");
document.writeln("<div class='box pad' id='yxym'>");
document.writeln("");
document.writeln("");
document.writeln("<div class='list-title'>台湾六合彩论坛『家野中特』 </div>");
document.writeln("<table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1776'>");


document.writeln("<tr>");
document.writeln("<td><font color='#0000FF'>269期:</font><font color='#000000'>火爆家野<span class='zl'>〈〈</span></font><span class='zl'>家畜<font color='#000000'>〉〉</font></span>");
document.writeln("<font color='#000000'>准</font>？00准</td>");
document.writeln("</tr>");
 

document.writeln("<tr>");
document.writeln("<td><font color='#0000FF'>268期:</font><font color='#000000'>火爆家野<span class='zl'>〈〈</span></font><span class='zl'>家畜<font color='#000000'>〉〉</font></span>");
document.writeln("<font color='#000000'>准</font>羊22准</td>");
document.writeln("</tr>");
 


document.writeln("<tr>");
document.writeln("<td><font color='#0000FF'>266期:</font><font color='#000000'>火爆家野<span class='zl'>〈〈</span></font><span class='zl'>野兽<font color='#000000'>〉〉</font></span>");
document.writeln("<font color='#000000'>准</font>虎27准</td>");
document.writeln("</tr>");
 


document.writeln("<tr>");
document.writeln("<td><font color='#0000FF'>264期:</font><font color='#000000'>火爆家野<span class='zl'>〈〈</span></font><span class='zl'>家畜<font color='#000000'>〉〉</font></span>");
document.writeln("<font color='#000000'>准</font>猪30准</td>");
document.writeln("</tr>");
 
 

document.writeln("<tr>");
document.writeln("<td><font color='#0000FF'>263期:</font><font color='#000000'>火爆家野<span class='zl'>〈〈</span></font><span class='zl'>野兽<font color='#000000'>〉〉</font></span>");
document.writeln("<font color='#000000'>准</font>龙13准</td>");
document.writeln("</tr>");
 

document.writeln("<tr>");
document.writeln("<td><font color='#0000FF'>262期:</font><font color='#000000'>火爆家野<span class='zl'>〈〈</span></font><span class='zl'>家畜<font color='#000000'>〉〉</font></span>");
document.writeln("<font color='#000000'>准</font>鸡44准</td>");
document.writeln("</tr>");
 

document.writeln("<tr>");
document.writeln("<td><font color='#0000FF'>261期:</font><font color='#000000'>火爆家野<span class='zl'>〈〈</span></font><span class='zl'>野兽<font color='#000000'>〉〉</font></span>");
document.writeln("<font color='#000000'>准</font>龙01准</td>");
document.writeln("</tr>");




document.writeln("");
document.writeln("</table>");
document.writeln("<table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1802'>");
document.writeln("");
document.writeln("</table></div>");*/

