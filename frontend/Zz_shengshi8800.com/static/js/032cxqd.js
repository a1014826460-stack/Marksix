$.ajax({
    url: httpApi + `/api/kaijiang/getSjsx?web=${web}&type=${type}&num=3`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {

        let htmlBox = '',htmlBoxList = '',term=''

        let data = response.data
        let chunAll = '';
        let xiaALl = '';
        let qiuALl = '';
        let dongALl = '';
        if(data.length>0){
            for (let i in data) {
                data[i]['content'] = JSON.parse(data[i].content);
                data[i].value = '';
                for (let i2 in data[i].content) {
                    let split = data[i]['content'][i2].split('|');
                    let v = split[0].split('')[0];
                    data[i].value += v;
                    if (split[1]) {
                        let split2 = split[1].split(',')
                        for (let i3 in split2) {
                            let v2 = split2[i3];
                            if (v === '春' && chunAll.indexOf(v2) === -1) {
                                chunAll += v2 + ',';
                            } else if (v === '夏' && xiaALl.indexOf(v2) === -1) {
                                xiaALl += v2 + ',';
                            } else if (v === '秋' && qiuALl.indexOf(v2) === -1) {
                                qiuALl += v2 + ',';
                            } else if (v === '冬' && dongALl.indexOf(v2) === -1) {
                                dongALl += v2 + ',';
                            }
                        }
                    }
                }
            }

            if (chunAll) {
                chunAll = chunAll.replaceAll(',','');
            }
            if (xiaALl) {
                xiaALl = chunAll.replaceAll(',','');
            }
            if (qiuALl) {
                qiuALl = chunAll.replaceAll(',','');
            }
            if (dongALl) {
                dongALl = chunAll.replaceAll(',','');
            }
            for(let i in data){
                let d = data[i];
                let resCode = d.res_code.split(",");
                let resSx = d.res_sx.split(",");
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao =  [];
                let xiaoV =  [];
                let ma = [];
                let content = d.content;
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0].split('')[0])
                    xiaoV[i] = c[1];
                    ma.push(...(c[1]||'').split(','));
                }

                let c1 = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i] && xiaoV[i].indexOf(sx) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                    if (xiaoV[i]) {
                        if (xiao[i] === '春') {
                            chun = xiaoV[i].replaceAll(',','');
                        }else if (xiao[i] === '夏') {
                            xia = xiaoV[i].replaceAll(',','');
                        }else if (xiao[i] === '秋') {
                            qiu = xiaoV[i].replaceAll(',','');
                        }else if (xiao[i] === '冬') {
                            dong = xiaoV[i].replaceAll(',','');
                        }
                    }

                }
                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
	    <td><font color='#000000'>${d.term}期:</font><font color='#0000FF'>春夏秋冬→${c1.join('')}</span> </font>开:${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}准</td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title' >台湾六合彩→<font color='#FF0000'>【</font>春夏秋冬<font color='#FF0000'>】</font>→ </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
        <td><font color='#000000'></font><span class='zl'>春:兔虎龙　夏:羊蛇马<br>秋:狗鸡猴　冬:猪牛鼠</span></td>
        `+htmlBoxList+`
 </table>
</div>

`
        $(".cxqd").html(htmlBox)

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});









/*

document.writeln("  <div class='box pad' id='yxym'>");
document.writeln("        <div class='list-title' >台湾六合彩→<font color='#FF0000'>【</font>春夏秋冬<font color='#FF0000'>】</font>→ </div>");
document.writeln("        <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>");
document.writeln("		");
document.writeln("			");
document.writeln("		");


document.writeln("					<tr>");
document.writeln("				<td><font color='#000000'></font><span class='zl'>春:虎兔龙　夏:蛇马羊<br>秋:猴鸡狗　冬:鼠牛猪</span></td>");
document.writeln("			</tr>");


document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>269期:</font><font color='#0000FF'>春夏秋冬→春秋夏</span> </font>开:？00准</td>");
document.writeln("			</tr>");



document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>268期:</font><font color='#0000FF'>春夏秋冬→秋<span style='background-color: #FFFF00'>夏</span>冬</span> </font>开:羊22准</td>");
document.writeln("			</tr>");



document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>267期:</font><font color='#0000FF'>春夏秋冬→春<span style='background-color: #FFFF00'>夏</span>冬</span> </font>开:蛇12准</td>");
document.writeln("			</tr>");



document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>264期:</font><font color='#0000FF'>春夏秋冬→春夏<span style='background-color: #FFFF00'>冬</span></span> </font>开:猪30准</td>");
document.writeln("			</tr>");



document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>263期:</font><font color='#0000FF'>春夏秋冬→<span style='background-color: #FFFF00'>春</span>秋冬</span> </font>开:龙13准</td>");
document.writeln("			</tr>");



document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>262期:</font><font color='#0000FF'>春夏秋冬→夏<span style='background-color: #FFFF00'>秋</span>冬</span> </font>开:鸡44准</td>");
document.writeln("			</tr>");





document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>261期:</font><font color='#0000FF'>春夏秋冬→冬秋<span style='background-color: #FFFF00'>春</span></span> </font>开:龙01准</td>");
document.writeln("			</tr>");



document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>259期:</font><font color='#0000FF'>春夏秋冬→春夏<span style='background-color: #FFFF00'>冬</span></span> </font>开:鼠29准</td>");
document.writeln("			</tr>");



document.writeln("			<tr>");
document.writeln("				<td><font color='#000000'>258期:</font><font color='#0000FF'>春夏秋冬→春秋<span style='background-color: #FFFF00'>冬</span></span> </font>开:牛40准</td>");
document.writeln("			</tr>");



document.writeln("			");
document.writeln("			</table>");
document.writeln("    </div>");*/
