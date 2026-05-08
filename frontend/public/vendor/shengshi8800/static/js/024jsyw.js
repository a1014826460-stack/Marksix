var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };


$.ajax({
    url: httpApi + `/api/kaijiang/getShaWei?web=${web}&type=${type}&num=1`,
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
                let b = true;
                for (let i = 0; i < xiao.length; i++) {
                    if (code && xiao[i].split('')[0] !== code.split('')[1]) {
                        c.push(`<span>${xiao[i]}</span>`);
                    }else {
                        b=false;
                        c.push(`${xiao[i]}`)
                    }
                }

                if (sx && !b) continue;

                // let wei = parseInt()
                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
    
     
    <tr>
        <td><font color='#000000'>${d.term}期:</font><font color='#0000FF'>绝杀一尾→<span class='zl'>[${c[0]}]</span> </font>开:${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}准</td>
    </tr>
    
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title' >台湾六合彩→<font color='#FF0000'>【</font>绝杀一尾<font color='#FF0000'>】</font>→ </div>
    <span class='zl'>』 </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $("#jsyw").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});




/*


document.writeln("  <div class='box pad\' id=\'yxym\'>");
document.writeln("        <div class=\'list-title\' >台湾六合彩→<font color=\'#FF0000\'>【</font>绝杀一尾<font color=\'#FF0000\'>】</font>→ </div>");
document.writeln("        <table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\'>");
document.writeln("		");
document.writeln("			");
document.writeln("		");

document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>269期:</font><font color=\'#0000FF\'>绝杀一尾→<span class=\'zl\'>[1尾]</span> </font>开:？00准</td>");
document.writeln("			</tr>");

 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>268期:</font><font color=\'#0000FF\'>绝杀一尾→<span class=\'zl\'>[7尾]</span> </font>开:羊22准</td>");
document.writeln("			</tr>");

 
 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>267期:</font><font color=\'#0000FF\'>绝杀一尾→<span class=\'zl\'>[5尾]</span> </font>开:蛇12准</td>");
document.writeln("			</tr>");

 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>266期:</font><font color=\'#0000FF\'>绝杀一尾→<span class=\'zl\'>[4尾]</span> </font>开:虎27准</td>");
document.writeln("			</tr>");

 
 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>265期:</font><font color=\'#0000FF\'>绝杀一尾→<span class=\'zl\'>[2尾]</span> </font>开:牛16准</td>");
document.writeln("			</tr>");

 

 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>264期:</font><font color=\'#0000FF\'>绝杀一尾→<span class=\'zl\'>[9尾]</span> </font>开:猪30准</td>");
document.writeln("			</tr>");

 
 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>263期:</font><font color=\'#0000FF\'>绝杀一尾→<span class=\'zl\'>[0尾]</span> </font>开:龙13准</td>");
document.writeln("			</tr>");

 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>262期:</font><font color=\'#0000FF\'>绝杀一尾→<span class=\'zl\'>[6尾]</span> </font>开:鸡44准</td>");
document.writeln("			</tr>");


 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>260期:</font><font color=\'#0000FF\'>绝杀一尾→<span class=\'zl\'>[2尾]</span> </font>开:牛40准</td>");
document.writeln("			</tr>");


 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>257期:</font><font color=\'#0000FF\'>绝杀一尾→<span class=\'zl\'>[6尾]</span> </font>开:鸡08准</td>");
document.writeln("			</tr>");

 
 


document.writeln("			");
document.writeln("			</table>");
document.writeln("    </div>");*/

