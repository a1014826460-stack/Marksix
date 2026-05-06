$.ajax({
    url: httpApi + `/api/kaijiang/getRccx?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {

        let htmlBox = '',htmlBoxList = '',term=''

        let data = response.data
        let caix = '';
        let roux = '';
        let caox = '';
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
                            if (v === '菜' && caix.indexOf(v2) === -1) {
                                caix += v2 + '';
                            } else if (v === '草' && caox.indexOf(v2) === -1) {
                                caox += v2 + '';
                            } else if (v === '肉' && roux.indexOf(v2) === -1) {
                                roux += v2 + '';
                            }
                        }
                    }
                }
            }

            if (caix) {
                caix.substring(0,caix.length-2);
            }
            if (roux) {
                roux.substring(0,roux.length-2);
            }
            if (caox) {
                caox.substring(0,caox.length-2);
            }

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
                let content = d.content;
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0].split('')[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">吃${xiao[i]}</span>`);
                    }else {
                        c1.push(`吃${xiao[i]}`)
                    }
                    if (xiao[i] === '肉') {
                        rou = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '菜') {
                        cai = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '草') {
                        cao = xiaoV[i].replaceAll(',','');
                    }
                }



                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
        <td>
            <font color='#000000'>${d.term}期:</font><font color='#0000FF'>肉菜草→${c1.join('')}</span> </font>开:${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}
        </td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class=\'list-title\' >台湾六合彩→<font color=\'#FF0000\'>【</font>肉菜草<font color=\'#FF0000\'>】</font>→ </div>
    <table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\'>
       <td><font color=\'#000000\'></font><span class=\'zl\'>肉肖:${roux} 菜肖:${caix}<br>草肖:${caox}</span></td>    
    `+htmlBoxList+`
 </table>
</div>

`
        $(".rcc").html(htmlBox)

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});



/*

document.writeln("  <div class=\'box pad\' id=\'yxym\'>");
document.writeln("        <div class=\'list-title\' >台湾六合彩→<font color=\'#FF0000\'>【</font>肉菜草<font color=\'#FF0000\'>】</font>→ </div>");
document.writeln("        <table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\'>");
document.writeln("		");
document.writeln("			");
document.writeln("		");



document.writeln("					<tr>");
document.writeln("				<td><font color=\'#000000\'></font><span class=\'zl\'>肉肖:虎蛇龙狗 菜肖:猪鼠鸡猴<br>草肖:牛羊马兔</span></td>");
document.writeln("			</tr>");






document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>269期:</font><font color=\'#0000FF\'>肉菜草→菜草</span> </font>开:？00</td>");
document.writeln("			</tr>");

 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>268期:</font><font color=\'#0000FF\'>肉菜草→菜<span style=\'background-color: #FFFF00\'>草</span></span> </font>开:羊22</td>");
document.writeln("			</tr>");




document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>265期:</font><font color=\'#0000FF\'>肉菜草→<span style=\'background-color: #FFFF00\'>草</span>肉</span> </font>开:牛16</td>");
document.writeln("			</tr>");


 
 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>264期:</font><font color=\'#0000FF\'>肉菜草→肉<span style=\'background-color: #FFFF00\'>菜</span></span> </font>开:猪30</td>");
document.writeln("			</tr>");

 
 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>263期:</font><font color=\'#0000FF\'>肉菜草→草<span style=\'background-color: #FFFF00\'>肉</span></span> </font>开:龙13</td>");
document.writeln("			</tr>");



document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>261期:</font><font color=\'#0000FF\'>肉菜草→<span style=\'background-color: #FFFF00\'>肉</span>菜</span> </font>开:龙01</td>");
document.writeln("			</tr>");

 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>260期:</font><font color=\'#0000FF\'>肉菜草→<span style=\'background-color: #FFFF00\'>草</span>肉</span> </font>开:牛40</td>");
document.writeln("			</tr>");


 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>259期:</font><font color=\'#0000FF\'>肉菜草→肉<span style=\'background-color: #FFFF00\'>菜</span></span> </font>开:鼠29</td>");
document.writeln("			</tr>");






document.writeln("			");
document.writeln("			</table>");
document.writeln("    </div>");*/
