var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/getShaBanbo?web=${web}&type=${type}&num=1`,
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
                for (let i = 0; i < xiao.length; i++) {
                    let xp = xiao[i].split('');
                    if (code && xiaoV[i].indexOf(code) === -1) {
                        c1.push(`<span style="background-color: #FFFF00">${xp[0]}波${xp[1]}</span>`);
                    }else {
                        c1.push(`<span >${xp[0]}波${xp[1]}</span>`)
                    }
                }

                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
        <td>
            <font color='#000000'>${data[i].term}期:</font>
            <font color='#0000FF'>绝杀半波→
                <span class='zl'>[${c1[0]}]</span> 
            </font>开:${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}准
        </td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title' > 台湾彩→<font color='#FF0000'>【</font>绝杀半波<font color='#FF0000'>】</font>→中中中</div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $(".jsbb").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});

/*

document.writeln("");
document.writeln("  <div class='box pad\' id=\'yxym\'>");
document.writeln("        <div class=\'list-title\' > 台湾彩→<font color=\'#FF0000\'>【</font>绝杀半波<font color=\'#FF0000\'>】</font>→中中中</div>");
document.writeln("        <table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\'>");
document.writeln("		");
document.writeln("			");
document.writeln("		");
document.writeln("");



document.writeln("");
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>269期:</font><font color=\'#0000FF\'>绝杀半波→<span class=\'zl\'>[<span style=\'background-color: #FFFF00\'>绿波双</span>]</span> </font>开:？00准</td>");
document.writeln("			</tr> ");
document.writeln("");

document.writeln("");
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>267期:</font><font color=\'#0000FF\'>绝杀半波→<span class=\'zl\'>[<span style=\'background-color: #FFFF00\'>蓝波双</span>]</span> </font>开:蛇12准</td>");
document.writeln("			</tr> ");
document.writeln("");


document.writeln("");
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>266期:</font><font color=\'#0000FF\'>绝杀半波→<span class=\'zl\'>[<span style=\'background-color: #FFFF00\'>红波双</span>]</span> </font>开:虎27准</td>");
document.writeln("			</tr> ");
document.writeln("");



document.writeln("");
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>265期:</font><font color=\'#0000FF\'>绝杀半波→<span class=\'zl\'>[<span style=\'background-color: #FFFF00\'>蓝波单</span>]</span> </font>开:牛16准</td>");
document.writeln("			</tr> ");
document.writeln("");


document.writeln("");
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>264期:</font><font color=\'#0000FF\'>绝杀半波→<span class=\'zl\'>[<span style=\'background-color: #FFFF00\'>绿波双</span>]</span> </font>开:猪30准</td>");
document.writeln("			</tr> ");
document.writeln("");


document.writeln("");
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>262期:</font><font color=\'#0000FF\'>绝杀半波→<span class=\'zl\'>[<span style=\'background-color: #FFFF00\'>蓝波单</span>]</span> </font>开:鸡44准</td>");
document.writeln("			</tr> ");
document.writeln("");





document.writeln("");
document.writeln("			");
document.writeln("			</table>");
document.writeln("    </div>");*/

