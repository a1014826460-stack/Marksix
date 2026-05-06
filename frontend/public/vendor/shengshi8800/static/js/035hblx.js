$.ajax({
 url: httpApi + `/api/kaijiang/getHbnx?web=${web}&type=${type}&num=3`,
 type: 'GET',
 dataType: 'json',
 success: function(response) {

  let htmlBox = '',htmlBoxList = '',term=''
  let heiAll = '';
  let baiALl = '';
  let data = response.data
  if(data.length>0){
   for (let i in data) {
     let bai = data[i].bai.split(',');
     let hei = data[i].hei.split(',');
      for (let i2 in bai) {
       if (baiALl.indexOf(bai[i2]) === -1) {
        baiALl+=bai[i2]+','
       }
      }
      for (let i2 in hei) {
       if (heiAll.indexOf(hei[i2]) === -1) {
        heiAll+=hei[i2]+','
       }
      }
   }
   if (heiAll) {
     heiAll.substring(0,heiAll.length-3);
   }
   if (baiALl) {
    baiALl.substring(0,heiAll.length-3);
   }
   for(let i in data){
    let d = data[i];
    let resCode = d.res_code.split(',');
    let reSx = d.res_sx.split(',');
    let codeSplit = d.res_code.split(',');
    let sxSplit = d.res_sx.split(',');
    let code = codeSplit[codeSplit.length-1]||'';
    let sx = sxSplit[sxSplit.length-1]||'';
    let result = '00'
    let myhei = d.hei.split(',');
    let mybai = d.bai.split(',');

    let c = [];
    for (let i = 0; i < myhei.length; i++) {
     if (sx && myhei[i].indexOf(sx) !== -1) {
      c.push(`<span style="background-color: #FFFF00">${myhei[i]}</span>`);
     }else {
      c.push(`${myhei[i]}`)
     }
    }
    let c1 = [];
    for (let i = 0; i < mybai.length; i++) {
     if (sx && mybai[i].indexOf(sx) !== -1) {
      c1.push(`<span style="background-color: #FFFF00">${mybai[i]}</span>`);
     }else {
      c1.push(`${mybai[i]}`)
     }
    }

    //console.log(ma)
    htmlBoxList = `${htmlBoxList} 
    <tr>
        <td><font color='#000000'>${d.term}期:</font><font color='#0000FF'>→黑:${c.join('')} 白:${c1.join('')}</span> </font>开:${reSx[reSx.length-1]||'?'}${resCode[resCode.length-1]||'00'}</td>
    </tr>
    
            `}
  }

  htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title' >特邀高手→<font color='#FF0000'>【</font>黑白无双<font color='#FF0000'>】</font>→全新上线</div>
  <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
    <tr>
      <td><font color='#000000'></font><span class='zl'>黑:${heiAll}<br>白:${baiALl}</span></td>
    </tr>
        `+htmlBoxList+`
 </table>
</div>

`


  $("#hb3t").html(htmlBox)

 },
 error: function(xhr, status, error) {
  console.error('Error:', error);
 }
});

/*
document.writeln("  <div class=\'box pad\' id=\'yxym\'>");
document.writeln("        <div class=\'list-title\' >特邀高手→<font color=\'#FF0000\'>【</font>黑白无双<font color=\'#FF0000\'>】</font>→全新上线</div>");
document.writeln("        <table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\'>");
document.writeln("		");
document.writeln("			");
document.writeln("		");

document.writeln("					<tr>");
document.writeln("				<td><font color=\'#000000\'></font><span class=\'zl\'>黑:兔龙蛇马羊猴<br>白:鼠牛虎鸡狗猪</span></td>");
document.writeln("			</tr>");


 
 
 
 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>269期:</font><font color=\'#0000FF\'>→黑:兔龙马 白:牛虎鸡</span> </font>开:？00</td>");
document.writeln("			</tr>");


 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>268期:</font><font color=\'#0000FF\'>→黑:龙马<span style=\'background-color: #FFFF00\'>羊</span> 白:鼠虎狗</span> </font>开:羊22</td>");
document.writeln("			</tr>");



document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>267期:</font><font color=\'#0000FF\'>→黑:猴<span style=\'background-color: #FFFF00\'>蛇</span>马 白:牛鼠狗</span> </font>开:蛇12</td>");
document.writeln("			</tr>");


 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>265期:</font><font color=\'#0000FF\'>→黑:羊猴兔 白:<span style=\'background-color: #FFFF00\'>牛</span>猪虎</span> </font>开:牛16</td>");
document.writeln("			</tr>");



document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>264期:</font><font color=\'#0000FF\'>→黑:羊蛇龙 白:虎狗<span style=\'background-color: #FFFF00\'>猪</span></span> </font>开:猪30</td>");
document.writeln("			</tr>");




 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>263期:</font><font color=\'#0000FF\'>→黑:<span style=\'background-color: #FFFF00\'>龙</span>猴马 白:鸡虎鼠</span> </font>开:龙13</td>");
document.writeln("			</tr>");


 
 document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>261期:</font><font color=\'#0000FF\'>→黑:<span style=\'background-color: #FFFF00\'>龙</span>蛇马 白:鸡狗猪</span> </font>开:龙01</td>");
document.writeln("			</tr>");



 
document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>260期:</font><font color=\'#0000FF\'>→黑:羊猴兔 白:<span style=\'background-color: #FFFF00\'>牛</span>猪虎</span> </font>开:牛40</td>");
document.writeln("			</tr>");



 



 
document.writeln("			");
document.writeln("			</table>");
document.writeln("    </div>");
document.writeln("		<div class=\'box news-box\'>");
document.writeln("		<div class=\'haoju\'><font color=\'#FFFF00\'>台湾六合彩论坛能帮您排忧解难!</font> </div>");
document.writeln("	</div>");*/
