var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };



$.ajax({
    url: httpApi + `/api/kaijiang/getSzxj?web=${web}&type=${type}`,
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
                let xiao = d.jiexi.split('');
                let ma = [];
                let maValue = [];
                let c = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) !== -1) {
                        c.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c.push(`${xiao[i]}`)
                    }
                }
                // let wei = parseInt()
                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
 
 
    
     
    <tr style='background: #FFFF00;'>
        <td style='background-color: #CCFFCC; text-align: left'>
            <span class='zl'>
                <font color='#000000'>${d.term}期四字玄机：≤${d.title}≥</font>
            </span>
        </td>
    </tr>
    <tr>
        <td style='text-align: left'><font color='#008000'>可解得：：${c.join('')}。</font><br>
        <span class='zl'><font>开奖结果：：</font>${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}准</span></td>
    </tr>
    
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title'>台湾六合彩论坛『四字玄机<span class='zl'>』 </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1810'>
        `+htmlBoxList+` 
 </table>
</div>

`


        $("#szxj").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});

/*

document.writeln("<div class=\'box pad\' id=\'yxym\'>");
document.writeln("<div class=\'list-title\'>台湾六合彩论坛『四字玄机<span class=\'zl\'>』 </div>");
document.writeln("<table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\' id=\'table1810\'>");



document.writeln("		<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<font color=\'#000000\'>269期【四字玄机】：≤踏雪尋梅≥</font></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><span class=\'zl\'>");
document.writeln("");
document.writeln("				<font color=\'#008000\'>可解得：鸡蛇猴牛马兔羊</font><br>开奖结果：？00准</span></td>");
document.writeln("");
document.writeln("			</tr>");




document.writeln("		<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<font color=\'#000000\'>268期【四字玄机】：≤芙蓉映日≥</font></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><span class=\'zl\'>");
document.writeln("");
document.writeln("				<font color=\'#008000\'>可解得：狗兔蛇<span style=\'background-color: #FFFF00\'>羊</span>鼠虎鸡</font><br>开奖结果：羊22准</span></td>");
document.writeln("");
document.writeln("			</tr>");





document.writeln("		<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<font color=\'#000000\'>267期【四字玄机】：≤春草碧色≥</font></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><span class=\'zl\'>");
document.writeln("");
document.writeln("				<font color=\'#008000\'>可解得：鸡虎兔羊龙猪<span style=\'background-color: #FFFF00\'>蛇</span></font><br>开奖结果：蛇12准</span></td>");
document.writeln("");
document.writeln("			</tr>");



document.writeln("		<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<font color=\'#000000\'>264期【四字玄机】：≤陽氣肅殺≥</font></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><span class=\'zl\'>");
document.writeln("");
document.writeln("				<font color=\'#008000\'>可解得：兔羊<span style=\'background-color: #FFFF00\'>猪</span>马狗鸡蛇</font><br>开奖结果：猪30准</span></td>");
document.writeln("");
document.writeln("			</tr>");



document.writeln("		<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<font color=\'#000000\'>261期【四字玄机】：≤小橋流水≥</font></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><span class=\'zl\'>");
document.writeln("");
document.writeln("				<font color=\'#008000\'>可解得：蛇羊<span style=\'background-color: #FFFF00\'>龙</span>鸡鼠虎猪</font><br>开奖结果：龙01准</span></td>");
document.writeln("");
document.writeln("			</tr>");



document.writeln("		<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<font color=\'#000000\'>258期【四字玄机】：≤南面称王≥</font></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><span class=\'zl\'>");
document.writeln("");
document.writeln("				<font color=\'#008000\'>可解得：<span style=\'background-color: #FFFF00\'>牛</span>马狗鼠鸡虎兔</font><br>开奖结果：牛40准</span></td>");
document.writeln("");
document.writeln("			</tr>");



document.writeln("		<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<font color=\'#000000\'>256期【四字玄机】：≤小橋流水≥</font></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><span class=\'zl\'>");
document.writeln("");
document.writeln("				<font color=\'#008000\'>可解得：蛇羊龙鸡鼠<span style=\'background-color: #FFFF00\'>虎</span>猪</font><br>开奖结果：虎39准</span></td>");
document.writeln("");
document.writeln("			</tr>");






document.writeln("		<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<font color=\'#000000\'>255期【四字玄机】：≤風霜滄桑≥</font></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><span class=\'zl\'>");
document.writeln("");
document.writeln("				<font color=\'#008000\'>可解得：龙羊虎狗兔<span style=\'background-color: #FFFF00\'>猪</span>马</font><br>开奖结果：猪30准</span></td>");
document.writeln("");
document.writeln("			</tr>");









document.writeln("");
document.writeln("</table></div>");

document.writeln("");*/

