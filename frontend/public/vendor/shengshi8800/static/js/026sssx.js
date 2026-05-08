var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/getHllx?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {

        let htmlBox = '',htmlBoxList = '',term=''

        let data = response.data
        let redAll = '';
        let buleAll = '';
        let greenAll = '';
        if(data.length>0){
            for(let i in data){
                let d = data[i];
                let result = '00'
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
                    xiao.push(c[0].split('')[0])
                    maValue[i] = c[1];
                    ma.push(...c[1].split(','));
                }
                let c1 = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && maValue[i].indexOf(sx) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                // let wei = parseInt()
                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
    
     <tr>
        <td><font color='#000000'>${d.term}期:</font><font color='2e88d4'>红蓝绿肖→<span class='zl'>[${c1.join('')}肖]</span> </font>开:${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}准</td>
    </tr>
    
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title' >台湾六合彩→<font color='#FF0000'>【</font>三色生肖<font color='#FF0000'>】</font>→ </div>
  <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
     <td><font color='#000000'></font><span class='zl'>红:马.兔.鼠.鸡 蓝:蛇.虎.猪.猴<br>绿:羊.龙.牛.狗</span></td>
        `+htmlBoxList+` 
 </table>
</div>

`


        $("._3ssx").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});








/*


document.writeln("  <div class='box pad' id='yxym'>");
document.writeln("        <div class='list-title' >台湾六合彩→<font color='#FF0000'>【</font>三色生肖<font color='#FF0000'>】</font>→ </div>");
document.writeln("        <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>");
document.writeln("		");
document.writeln("			");
document.writeln("		");

document.writeln("					<tr>");
document.writeln("				<td><font color='#000000'></font><span class='zl'>红:鼠兔马鸡 蓝:虎蛇猴猪<br>绿:牛龙羊狗</span></td>");
document.writeln("			</tr>");











document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>269期:</font><font color='2e88d4'>红蓝绿肖→<span class='zl'>[红绿肖]</span> </font>开:猫？00准</td>");
document.writeln("			</tr>"); 


document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>267期:</font><font color='2e88d4'>红蓝绿肖→<span class='zl'>[<span style='background-color: #FFFF00'>蓝</span>红肖]</span> </font>开:蓝蛇12准</td>");
document.writeln("			</tr>"); 




document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>265期:</font><font color='2e88d4'>红蓝绿肖→<span class='zl'>[红<span style='background-color: #FFFF00'>绿</span>肖]</span> </font>开:绿牛16准</td>");
document.writeln("			</tr>"); 



document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>264期:</font><font color='2e88d4'>红蓝绿肖→<span class='zl'>[<span style='background-color: #FFFF00'>蓝</span>红肖]</span> </font>开:蓝猪30准</td>");
document.writeln("			</tr>"); 

document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>261期:</font><font color='2e88d4'>红蓝绿肖→<span class='zl'>[<span style='background-color: #FFFF00'>绿</span>红肖]</span> </font>开:绿龙01准</td>");
document.writeln("			</tr>"); 




document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>260期:</font><font color='2e88d4'>红蓝绿肖→<span class='zl'>[红<span style='background-color: #FFFF00'>绿</span>肖]</span> </font>开:绿牛40准</td>");
document.writeln("			</tr>"); 






document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>259期:</font><font color='2e88d4'>红蓝绿肖→<span class='zl'>[蓝<span style='background-color: #FFFF00'>红</span>肖]</span> </font>开:红鼠29准</td>");
document.writeln("			</tr>"); 







document.writeln("			");
document.writeln("			</table>");
document.writeln("    </div>");*/

