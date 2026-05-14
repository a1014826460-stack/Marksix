var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/getPingte?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {
        let htmlBox = '', htmlBoxList = '', term = '';

        let data = response.data;

        if (data.length > 0) {
            data = data.slice(0, 6);
            for (let i in data) {
                let d = data[i];
                let codeSplit = (d.res_code || '').split(',');
                let sxSplit = (d.res_sx || '').split(',');
                let resSx = d.res_sx || '';
                let code = codeSplit[codeSplit.length - 1] || '';
                let sx = sxSplit[sxSplit.length - 1] || '';
                let result = [];
                let xiao = d.content.split(",");
                let reSx = d.res_sx.split(',');

                let c = [];
                for (let j = 0; j < xiao.length; j++) {
                    let index = getZjIndex(xiao[j], sxSplit);
                    if (index !== undefined) {
                        result.push(xiao[j]);
                        c.push(`<span>${xiao[j]}</span>`);
                    } else {
                        c.push(`${xiao[j]}`);
                    }
                }

                if (result.length === 0) {
                    if (resSx) {
                        // 已开奖，预测全不命中 → 显示真实开奖生肖
                        let lastSx = sxSplit.filter(function (s) { return s; }).slice(-2);
                        if (lastSx.length === 0) {
                            result = ['猫', '猫'];
                        } else if (lastSx.length === 1) {
                            result = [lastSx[0], lastSx[0]];
                        } else {
                            result = lastSx;
                        }
                    } else {
                        // 未开奖，无开奖数据 → 占位
                        result = ['猫', '猫'];
                    }
                } else if (result.length === 1) {
                    result[1] = result[0];
                }

                htmlBoxList = htmlBoxList + ` 
                <tr>
                    <td>
                        <font color='#000000'>${d.term}期:</font><font color='#3b9aeb'>平特王→<span class='zl'>[${c.join('')}]</span> </font>
                        开:${result.slice(0,2).join('')}准
                    </td>
                </tr>`;
            }
        }

        htmlBox = `
        <div class='box pad' id='yxym'>
            <div class='list-title' >台湾六合彩→<font color='#FF0000'>【</font>两肖平特王<font color='#FF0000'>】</font>→两肖在手，天下我有</div>
            <table border='1' width='100%' class='duilianpt1' bgcolor='3ea7d7' cellspacing='0' bordercolor='3ea7d7' bordercolorlight='3ea7d7' bordercolordark='3ea7d7' cellpadding='2'>
                `+ htmlBoxList + ` 
            </table>
        </div>`;

        $("#3t1").html(replaceLegacySiteText(htmlBox));
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});





/*

document.writeln("  <div class=\'box pad\' id=\'yxym\'>");
document.writeln("        <div class=\'list-title\' >台湾六合彩→<font color=\'#FF0000\'>【</font>两肖平特王<font color=\'#FF0000\'>】</font>→两肖在手，天下我有</div>");
document.writeln("        <table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'3ea7d7\' cellspacing=\'0\' bordercolor=\'3ea7d7\' bordercolorlight=\'3ea7d7\' bordercolordark=\'3ea7d7\' cellpadding=\'2\'>");
document.writeln("		");
document.writeln("			");
document.writeln("		");


 
 


 

document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>269期:</font><font color=\3b9aeb\'>平特王→<span class=\'zl\'>[兔马]</span> </font>开:猫猫准</td>");
document.writeln("			</tr>"); 



document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>266期:</font><font color=\3b9aeb\'>平特王→<span class=\'zl\'>[鼠虎]</span> </font>开:鼠虎准</td>");
document.writeln("			</tr>"); 



document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>264期:</font><font color=\3b9aeb\'>平特王→<span class=\'zl\'>[龙狗]</span> </font>开:狗狗准</td>");
document.writeln("			</tr>"); 



document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>263期:</font><font color=\3b9aeb\'>平特王→<span class=\'zl\'>[猴鸡]</span> </font>开:鸡鸡准</td>");
document.writeln("			</tr>"); 




document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>261期:</font><font color=\3b9aeb\'>平特王→<span class=\'zl\'>[鸡兔]</span> </font>开:鸡鸡准</td>");
document.writeln("			</tr>"); 




document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>260期:</font><font color=\3b9aeb\'>平特王→<span class=\'zl\'>[蛇猴]</span> </font>开:蛇蛇准</td>");
document.writeln("			</tr>"); 






document.writeln("			");
document.writeln("			</table>");
document.writeln("    </div>");*/

