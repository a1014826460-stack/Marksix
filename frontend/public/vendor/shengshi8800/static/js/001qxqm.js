var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/getXiaoma?web=${web}&type=${type}&num=7`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {
        let htmlBox = '',htmlBoxList = '',term=''

        let data = response.data
        if(data.length>0){
            for(let i in data){
                let d = data[i]
                let codeSplit = (d.res_code||'').split(',');
                let sxSplit = (d.res_sx||'').split(',');
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

                let c1 = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }
                let c2 = [];
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) !== -1) {
                        c2.push(`<span style="background-color: #FFFF00">${ma[i]}</span>`);
                    }else {
                        c2.push(`${ma[i]}`)
                    }
                }



                htmlBoxList = htmlBoxList + ` 
    
     <tr>
        <td style='text-align:center; background: #FFCCFF;' width='100%' colspan='2' size='5' height='50'>
            <font color='#0000FF'> ${d.term}期:勇敢向钱钱钱飞!</font>
        </td>
    </tr>
    <tr>
        <td style='text-align: left' bgcolor='#F4F4F4' width='45%' height='24'>
            <font color='#000080'>一肖:</font><font color='#FF0000'><span class='xz3'>${c1[0]}</span></font>
        </td>
        <td style='text-align: left' bgcolor='#F4F4F4' height='24'>
            <font color='#000080'>一码:</font><font color='#FF0000'><span class='xz3'>${c2[0]}</span></font>
        </td>
    </tr>
    <tr>
        <td style='text-align: left' bgcolor='#F4F4F4' width='45%' height='24'>
            <font color='#000080'>二肖:</font><font color='#FF0000'><span class='xz3'>${c1.slice(0,2).join('')}</span></font>
        </td>
        <td style='text-align: left' bgcolor='#F4F4F4' height='24'>
            <font color='#000080'>二码:</font><font color='#FF0000'><span class='xz3'>${c2.slice(0,2).join('.')}</span></font>
        </td>
    </tr>
    <tr>
        <td style='text-align: left' bgcolor='#F4F4F4' width='45%' height='24'>
            <font color='#000080'>四肖:</font><font color='#FF0000'><span class='xz'>${c1.slice(0,4).join('')}</span></font>
        </td>
        <td style='text-align: left' bgcolor='#F4F4F4' height='24'>
            <font color='#000080'>四码:</font><font color='#FF0000'><span class='xz'>${c2.slice(0,4).join('.')}</span></font>
        </td>
    </tr>
    <tr>
        <td style='text-align: left' bgcolor='#F4F4F4' width='45%' height='24'>
            <font color='#000080'>七肖:</font><font color='#FF0000'><span class='xz2'>${c1.join('')}</span></font>
        </td>
        <td style='text-align: left' bgcolor='#F4F4F4' height='24'>
            <font color='#000080'>七码:</font><font color='#FF0000'>${c2.join('.')}</font>
        </td>
    </tr>
    <tr>
        <td style='text-align:center; background: #CCFFCC;' width='100%' colspan='2'>台湾六合彩论坛是您人生成功的第一步</td>
    </tr>
    
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title'>台湾资料网!</div>
    <span class='zl'>』 </div>
    <table border='1' width='100%' cellpadding='0' cellspacing='0' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' bgcolor='#FFFFFF' class='qxtable' id='table1773'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $("#7x1m").html(replaceLegacySiteText(htmlBox))
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});



/*

document.writeln("");
document.writeln("<div class=\'box pad\' id=\'yxym\'>");
document.writeln("<div class=\'list-title\'>台湾资料网!</div>");
document.writeln("");
document.writeln("<table border=\'1\' width=\'100%\' cellpadding=\'0\' cellspacing=\'0\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' bgcolor=\'#FFFFFF\' class=\'qxtable\' id=\'table1773\'>");
document.writeln("");

document.writeln("<tr>");
document.writeln("<td style=\'text-align:center; background: #FFCCFF;\' width=\'100%\' colspan=\'2\' size=\'5\' height=\'50\'>");
document.writeln("<font color=\'#0000FF\'> 269期:勇敢向钱钱钱飞!</font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>一肖:</font><font color=\'#FF0000\'><span class=\'xz3\'>龙</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>一码:</font><font color=\'#FF0000\'><span class=\'xz3\'>13</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>二肖:</font><font color=\'#FF0000\'><span class=\'xz3\'>龙鸡</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>二码:</font><font color=\'#FF0000\'><span class=\'xz3\'>13.32</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\'>");
document.writeln("<font color=\'#000080\'>四肖:</font><font color=\'#FF0000\'><span class=\'xz\'>龙鸡狗猴</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\'>");
document.writeln("<font color=\'#000080\'>四码:</font><font color=\'#FF0000\'><span class=\'xz\'>13.32.07.45</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\'>");
document.writeln("<font color=\'#000080\'>七肖:</font><font color=\'#FF0000\'><span class=\'xz2\'>龙鸡狗猴牛马虎</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\'>");
document.writeln("<font color=\'#000080\'>七码:</font><font color=\'#FF0000\'>13.32.07.45.40.47.39</font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align:center; background: #CCFFCC;\' width=\'100%\' colspan=\'2\'>台湾六合彩论坛是您人生成功的第一步</td>");
document.writeln("</tr>");




document.writeln("<tr>");
document.writeln("<td style=\'text-align:center; background: #FFCCFF;\' width=\'100%\' colspan=\'2\' size=\'5\' height=\'50\'>");
document.writeln("<font color=\'#0000FF\'> 267期:勇敢向钱钱钱飞!</font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>一肖:</font><font color=\'#FF0000\'><span class=\'xz3\'>牛</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>一码:</font><font color=\'#FF0000\'><span class=\'xz3\'>16</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>二肖:</font><font color=\'#FF0000\'><span class=\'xz3\'>牛兔</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>二码:</font><font color=\'#FF0000\'><span class=\'xz3\'>16.02</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\'>");
document.writeln("<font color=\'#000080\'>四肖:</font><font color=\'#FF0000\'><span class=\'xz\'>牛兔猪鸡</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\'>");
document.writeln("<font color=\'#000080\'>四码:</font><font color=\'#FF0000\'><span class=\'xz\'>16.02.06.44</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\'>");
document.writeln("<font color=\'#000080\'>七肖:</font><font color=\'#FF0000\'><span class=\'xz2\'>牛兔猪鸡龙<span style=\'background-color: #FFFF00\'>蛇</span>虎</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\'>");
document.writeln("<font color=\'#000080\'>七码:</font><font color=\'#FF0000\'>16.02.06.44.13.36.15</font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align:center; background: #CCFFCC;\' width=\'100%\' colspan=\'2\'>台湾六合彩论坛是您人生成功的第一步</td>");
document.writeln("</tr>");




document.writeln("<tr>");
document.writeln("<td style=\'text-align:center; background: #FFCCFF;\' width=\'100%\' colspan=\'2\' size=\'5\' height=\'50\'>");
document.writeln("<font color=\'#0000FF\'> 265期:勇敢向钱钱钱飞!</font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>一肖:</font><font color=\'#FF0000\'><span class=\'xz3\'>龙</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>一码:</font><font color=\'#FF0000\'><span class=\'xz3\'>37</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>二肖:</font><font color=\'#FF0000\'><span class=\'xz3\'>龙<span style=\'background-color: #FFFF00\'>牛</span></span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>二码:</font><font color=\'#FF0000\'><span class=\'xz3\'>37.16</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\'>");
document.writeln("<font color=\'#000080\'>四肖:</font><font color=\'#FF0000\'><span class=\'xz\'>龙<span style=\'background-color: #FFFF00\'>牛</span>马羊</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\'>");
document.writeln("<font color=\'#000080\'>四码:</font><font color=\'#FF0000\'><span class=\'xz\'>37.16.47.34</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\'>");
document.writeln("<font color=\'#000080\'>七肖:</font><font color=\'#FF0000\'><span class=\'xz2\'>龙<span style=\'background-color: #FFFF00\'>牛</span>马羊虎猪鼠</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\'>");
document.writeln("<font color=\'#000080\'>七码:</font><font color=\'#FF0000\'>37.16.47.34.15.18.29</font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align:center; background: #CCFFCC;\' width=\'100%\' colspan=\'2\'>台湾六合彩论坛是您人生成功的第一步</td>");
document.writeln("</tr>");

 


document.writeln("<tr>");
document.writeln("<td style=\'text-align:center; background: #FFCCFF;\' width=\'100%\' colspan=\'2\' size=\'5\' height=\'50\'>");
document.writeln("<font color=\'#0000FF\'> 264期:勇敢向钱钱钱飞!</font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>一肖:</font><font color=\'#FF0000\'><span class=\'xz3\'><span style=\'background-color: #FFFF00\'>猪</span></span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>一码:</font><font color=\'#FF0000\'><span class=\'xz3\'>18</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>二肖:</font><font color=\'#FF0000\'><span class=\'xz3\'><span style=\'background-color: #FFFF00\'>猪</span></span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>二码:</font><font color=\'#FF0000\'><span class=\'xz3\'>18.19</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\'>");
document.writeln("<font color=\'#000080\'>四肖:</font><font color=\'#FF0000\'><span class=\'xz\'><span style=\'background-color: #FFFF00\'>猪</span>狗猴羊</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\'>");
document.writeln("<font color=\'#000080\'>四码:</font><font color=\'#FF0000\'><span class=\'xz\'>18.19.21.34</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\'>");
document.writeln("<font color=\'#000080\'>七肖:</font><font color=\'#FF0000\'><span class=\'xz2\'><span style=\'background-color: #FFFF00\'>猪</span>狗猴羊鼠虎鸡</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\'>");
document.writeln("<font color=\'#000080\'>七码:</font><font color=\'#FF0000\'>18.19.21.34.05.03.08</font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align:center; background: #CCFFCC;\' width=\'100%\' colspan=\'2\'>台湾六合彩论坛是您人生成功的第一步</td>");
document.writeln("</tr>");



document.writeln("<tr>");
document.writeln("<td style=\'text-align:center; background: #FFCCFF;\' width=\'100%\' colspan=\'2\' size=\'5\' height=\'50\'>");
document.writeln("<font color=\'#0000FF\'> 263期:勇敢向钱钱钱飞!</font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>一肖:</font><font color=\'#FF0000\'><span class=\'xz3\'><span style=\'background-color: #FFFF00\'>龙</span></span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>一码:</font><font color=\'#FF0000\'><span class=\'xz3\'>37</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>二肖:</font><font color=\'#FF0000\'><span class=\'xz3\'><span style=\'background-color: #FFFF00\'>龙</span>虎</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>二码:</font><font color=\'#FF0000\'><span class=\'xz3\'>37.39</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\'>");
document.writeln("<font color=\'#000080\'>四肖:</font><font color=\'#FF0000\'><span class=\'xz\'><span style=\'background-color: #FFFF00\'>龙</span>虎鸡鼠</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\'>");
document.writeln("<font color=\'#000080\'>四码:</font><font color=\'#FF0000\'><span class=\'xz\'>37.39.44.17</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\'>");
document.writeln("<font color=\'#000080\'>七肖:</font><font color=\'#FF0000\'><span class=\'xz2\'><span style=\'background-color: #FFFF00\'>龙</span>虎鸡鼠狗猪羊</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\'>");
document.writeln("<font color=\'#000080\'>七码:</font><font color=\'#FF0000\'>37.39.44.17.43.18.10</font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align:center; background: #CCFFCC;\' width=\'100%\' colspan=\'2\'>台湾六合彩论坛是您人生成功的第一步</td>");
document.writeln("</tr>");



document.writeln("<tr>");
document.writeln("<td style=\'text-align:center; background: #FFCCFF;\' width=\'100%\' colspan=\'2\' size=\'5\' height=\'50\'>");
document.writeln("<font color=\'#0000FF\'> 262期:勇敢向钱钱钱飞!</font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>一肖:</font><font color=\'#FF0000\'><span class=\'xz3\'>兔</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>一码:</font><font color=\'#FF0000\'><span class=\'xz3\'>26</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>二肖:</font><font color=\'#FF0000\'><span class=\'xz3\'>兔牛</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' height=\'24\'>");
document.writeln("<font color=\'#000080\'>二码:</font><font color=\'#FF0000\'><span class=\'xz3\'>26.28</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\'>");
document.writeln("<font color=\'#000080\'>四肖:</font><font color=\'#FF0000\'><span class=\'xz\'>兔牛马<span style=\'background-color: #FFFF00\'>鸡</span></span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\'>");
document.writeln("<font color=\'#000080\'>四码:</font><font color=\'#FF0000\'><span class=\'xz\'>26.28.47.32</span></font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\' width=\'45%\'>");
document.writeln("<font color=\'#000080\'>七肖:</font><font color=\'#FF0000\'><span class=\'xz2\'>兔牛马<span style=\'background-color: #FFFF00\'>鸡</span>鼠虎蛇</span></font></td>");
document.writeln("<td style=\'text-align: left\' bgcolor=\'#F4F4F4\'>");
document.writeln("<font color=\'#000080\'>七码:</font><font color=\'#FF0000\'>26.28.47.32.41.03.12</font></td>");
document.writeln("</tr>");
document.writeln("<tr>");
document.writeln("<td style=\'text-align:center; background: #CCFFCC;\' width=\'100%\' colspan=\'2\'>台湾六合彩论坛是您人生成功的第一步</td>");
document.writeln("</tr>");



document.writeln("");
document.writeln("</table></div>");
document.writeln("");*/

