var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
 url: httpApi + `/api/kaijiang/getShaXiao?web=${web}&type=${type}&num=3`,
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
    let xiao = d.content.split(',');
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

    //console.log(ma)
    htmlBoxList = htmlBoxList + ` 
		
	<tr>
	    <td width='20%'><font color='#000080'>${d.term}期</font></td>
	    <td><span class=\'zl\'>今期买${c.join('')}输尽光</span></td>
	    <td width=\'23%\'><font color=\'#000080\'>开:${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}准</td>
    </tr>
            `}
  }

  htmlBox = `
<div class='box pad' id='yxym'>
    <div class=\'list-title\' >台湾六合彩论坛『欲输尽光三肖』 </div>
    <table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\'>
    `+htmlBoxList+`
 </table>
</div>

`
  $(".js3x").html(replaceLegacySiteText(htmlBox))

 },
 error: function(xhr, status, error) {
  console.error('Error:', error);
 }
});

/*

document.writeln("<div class=\'box pad\' id=\'yxym\'>");
document.writeln("		<div class=\'list-title\' >台湾六合彩论坛『欲输尽光三肖』 </div>");
document.writeln("		<table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\'>");

 document.writeln("			<tr>");
document.writeln("				<td width=\'20%\'><font color=\'#000080\'>269期</font></td>");
document.writeln("				<td><span class=\'zl\'>今期买鸡鼠猪输尽光</span></td>");
document.writeln("				<td width=\'23%\'><font color=\'#000080\'>开:？00准</td>");
document.writeln("			</tr>");
 
 
 document.writeln("			<tr>");
document.writeln("				<td width=\'20%\'><font color=\'#000080\'>268期</font></td>");
document.writeln("				<td><span class=\'zl\'>今期买兔猴狗输尽光</span></td>");
document.writeln("				<td width=\'23%\'><font color=\'#000080\'>开:羊22准</td>");
document.writeln("			</tr>");

 
 document.writeln("			<tr>");
document.writeln("				<td width=\'20%\'><font color=\'#000080\'>267期</font></td>");
document.writeln("				<td><span class=\'zl\'>今期买羊龙兔输尽光</span></td>");
document.writeln("				<td width=\'23%\'><font color=\'#000080\'>开:蛇12准</td>");
document.writeln("			</tr>");

 document.writeln("			<tr>");
document.writeln("				<td width=\'20%\'><font color=\'#000080\'>266期</font></td>");
document.writeln("				<td><span class=\'zl\'>今期买蛇龙马输尽光</span></td>");
document.writeln("				<td width=\'23%\'><font color=\'#000080\'>开:虎27准</td>");
document.writeln("			</tr>");
 
 document.writeln("			<tr>");
document.writeln("				<td width=\'20%\'><font color=\'#000080\'>265期</font></td>");
document.writeln("				<td><span class=\'zl\'>今期买兔龙虎输尽光</span></td>");
document.writeln("				<td width=\'23%\'><font color=\'#000080\'>开:牛16准</td>");
document.writeln("			</tr>");
 
 document.writeln("			<tr>");
document.writeln("				<td width=\'20%\'><font color=\'#000080\'>264期</font></td>");
document.writeln("				<td><span class=\'zl\'>今期买猴兔鸡输尽光</span></td>");
document.writeln("				<td width=\'23%\'><font color=\'#000080\'>开:猪30准</td>");
document.writeln("			</tr>");
 
 document.writeln("			<tr>");
document.writeln("				<td width=\'20%\'><font color=\'#000080\'>263期</font></td>");
document.writeln("				<td><span class=\'zl\'>今期买羊鼠牛输尽光</span></td>");
document.writeln("				<td width=\'23%\'><font color=\'#000080\'>开:龙13准</td>");
document.writeln("			</tr>");

 
 document.writeln("			<tr>");
document.writeln("				<td width=\'20%\'><font color=\'#000080\'>261期</font></td>");
document.writeln("				<td><span class=\'zl\'>今期买猴鼠虎输尽光</span></td>");
document.writeln("				<td width=\'23%\'><font color=\'#000080\'>开:龙01准</td>");
document.writeln("			</tr>");



document.writeln("		</table></div>");
document.writeln("		");*/

