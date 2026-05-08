var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };


$.ajax({
    url: httpApi + `/api/kaijiang/getYjzy?web=${web}&type=${type}`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {

        let htmlBox = '',htmlBoxList = '',term=''

        let data = response.data

        if(data.length>0){
            data = data.slice(0, 8);
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


                htmlBoxList = htmlBoxList + ` 
    <tr style='background: #FFFF00;'>
        <td style='background-color: #CCFFCC; text-align: left'>
            <span class='zl'>
                <font color='#000000'>${d.term}期一句真言：${d.title}</font>
            </span>
        </td>
    </tr>
    <tr>
        <td style='text-align: left'><font color='#008000'>真言解释：${d.content}。</font><br>
        <span class='zl'><font color='#000000'>真言解肖主前：</font>${c.join('')} 開:${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}</span></td>
    </tr>
    
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title'>台湾六合彩论坛『一句真言<span class='zl'>』 </div>
    <span class='zl'>』 </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1810'>
        `+htmlBoxList+` 
 </table>
</div>

`


        $("#zhenyan").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});










/*


document.writeln("<div class=\'box pad\' id=\'yxym\'>");
document.writeln("<div class=\'list-title\'>台湾六合彩论坛『一句真言<span class=\'zl\'>』 </div>");
document.writeln("<table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\' id=\'table1810\'>");






 
document.writeln("			<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<span class=\'zl\'><font color=\'#000000\'>269期一句真言：红花烂漫报春美</font></span></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><font color=\'#008000\'>真言解释：美解女肖蛇羊鸡兔。</font><br>");
document.writeln("");
document.writeln("				<span class=\'zl\'><font color=\'#000000\'>真言解肖主前：</font>蛇羊鸡兔鼠马猪 開:？00</span></td>");
document.writeln("");
document.writeln("			</tr>");




document.writeln("			<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<span class=\'zl\'><font color=\'#000000\'>266期一句真言：一轮红日照大地</font></span></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><font color=\'#008000\'>真言解释：地解地肖:蛇羊鸡狗鼠虎。</font><br>");
document.writeln("");
document.writeln("				<span class=\'zl\'><font color=\'#000000\'>真言解肖主前：</font>蛇羊鸡狗鼠<span style=\'background-color: #FFFF00\'>虎</span>牛 開:虎27</span></td>");
document.writeln("");
document.writeln("			</tr>");





document.writeln("			<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<span class=\'zl\'><font color=\'#000000\'>263期一句真言：花红柳绿四季春</font></span></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><font color=\'#008000\'>真言解释：花带草字头解吃草的生肖兔羊牛马。春解得春肖虎兔龙。</font><br>");
document.writeln("");
document.writeln("				<span class=\'zl\'><font color=\'#000000\'>真言解肖主前：</font>兔羊牛马虎<span style=\'background-color: #FFFF00\'>龙</span>狗 開:龙13</span></td>");
document.writeln("");
document.writeln("			</tr>");




document.writeln("					<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<span class=\'zl\'><font color=\'#000000\'>261期一句真言：冲天香阵透长安</font></span></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><font color=\'#008000\'>真言解释：天解天肖，兔马猴猪牛龙。</font><br>");
document.writeln("");
document.writeln("				<span class=\'zl\'><font color=\'#000000\'>真言解肖主前：</font>兔马猴猪牛狗<span style=\'background-color: #FFFF00\'>龙</span> 開:龙01</span></td>");
document.writeln("");
document.writeln("			</tr>");




document.writeln("					<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<span class=\'zl\'><font color=\'#000000\'>259期一句真言：人心不足蛇吞象</font></span></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><font color=\'#008000\'>真言解释：蛇吞象解猴鸡鼠蛇虎龙兔</font><br>");
document.writeln("");
document.writeln("				<span class=\'zl\'><font color=\'#000000\'>真言解肖主前：</font>猴鸡<span style=\'background-color: #FFFF00\'>鼠</span>蛇虎龙兔 開:鼠29</span></td>");
document.writeln("");
document.writeln("			</tr>");



document.writeln("			<tr style=\'background: #FFFF00;\'>");
document.writeln("");
document.writeln("				<td style=\'background-color: #CCFFCC; text-align: left\'>");
document.writeln("");
document.writeln("				<span class=\'zl\'><font color=\'#000000\'>258期一句真言：花红柳绿四季春</font></span></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style=\'text-align: left\'><font color=\'#008000\'>真言解释：花带草字头解吃草的生肖兔羊牛马。春解得春肖虎兔龙。</font><br>");
document.writeln("");
document.writeln("				<span class=\'zl\'><font color=\'#000000\'>真言解肖主前：</font>兔羊<span style=\'background-color: #FFFF00\'>牛</span>马虎龙狗 開:牛40</span></td>");
document.writeln("");
document.writeln("			</tr>");






document.writeln("");
document.writeln("</table></div>");

document.writeln("");*/

