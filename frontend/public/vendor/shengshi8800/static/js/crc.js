// document.writeln("<table class=\"ptyx\" width=\"100%\" border=\"1\">");
// document.writeln("  <tr>");
// document.writeln("    <th>台湾肉菜草肖</th>");
// document.writeln("  </tr>");
// document.writeln(" ");
// document.writeln("");
// document.writeln("  </tr>");
// document.writeln("  ");
// document.writeln("");


// document.writeln("<table id='crc'  border=1 width=100% bgcolor=#ffffff style='font-weight:bold'><tbody></tbody></table>");

// document.writeln("    <tr>");
// document.writeln("    <td class=\"td\">");
// document.writeln("	<p align=\"center\">269期:<font color=\"#0000FF\">菜肉草肖</font><font color=\"#FF0000\">【菜肖草肖】</font>开？00准</td>");
// document.writeln("  </tr>");
   


// document.writeln("    <tr>");
// document.writeln("    <td class=\"td\">");
// document.writeln("	<p align=\"center\">266期:<font color=\"#0000FF\">菜肉草肖</font><font color=\"#FF0000\">【菜肖<span style=\'background-color: #FFFF00\'>肉肖</span>】</font>开虎27准</td>");
// document.writeln("  </tr>");
  
 

// document.writeln("    <tr>");
// document.writeln("    <td class=\"td\">");
// document.writeln("	<p align=\"center\">265期:<font color=\"#0000FF\">菜肉草肖</font><font color=\"#FF0000\">【菜肖<span style=\'background-color: #FFFF00\'>草肖</span>】</font>开2牛16准</td>");
// document.writeln("  </tr>");
  
 

// document.writeln("    <tr>");
// document.writeln("    <td class=\"td\">");
// document.writeln("	<p align=\"center\">264期:<font color=\"#0000FF\">菜肉草肖</font><font color=\"#FF0000\">【<span style=\'background-color: #FFFF00\'>菜肖</span>肉肖】</font>开猪30准</td>");
// document.writeln("  </tr>");
  
 


// document.writeln("    <tr>");
// document.writeln("    <td class=\"td\">");
// document.writeln("	<p align=\"center\">262期:<font color=\"#0000FF\">菜肉草肖</font><font color=\"#FF0000\">【<span style=\'background-color: #FFFF00\'>菜肖</span>肉肖】</font>开鸡44准</td>");
// document.writeln("  </tr>");
  

// document.writeln("    <tr>");
// document.writeln("    <td class=\"td\">");
// document.writeln("	<p align=\"center\">260期:<font color=\"#0000FF\">菜肉草肖</font><font color=\"#FF0000\">【肉肖<span style=\'background-color: #FFFF00\'>草肖</span>】</font>开牛40准</td>");
// document.writeln("  </tr>");
 
    

// document.writeln("    <tr>");
// document.writeln("    <td class=\"td\">");
// document.writeln("	<p align=\"center\">259期:<font color=\"#0000FF\">菜肉草肖</font><font color=\"#FF0000\">【<span style=\'background-color: #FFFF00\'>菜肖</span>草肖】</font>开鼠29准</td>");
// document.writeln("  </tr>");
 
    
 
  
 
 


// document.writeln("    ");
// document.writeln("");
// document.writeln("   ");
// document.writeln("");
// document.writeln("  <tr>");
// document.writeln("    <td class=\"td\">");
// document.writeln("	<p align=\"center\" id=\"crc_attach\">");
// //<font color=\"#FF9900\"></font>肉肖:虎-蛇-龙-狗<br>菜肖:猪-鼠-鸡-猴<br>草肖:牛-羊-马-兔<br>
// document.writeln("<font color=\"#FF9900\"></font></td>");
// document.writeln("");
// document.writeln(" ");
// document.writeln("  </tr>");
// document.writeln("");
// document.writeln("");
// document.writeln("");
// document.writeln("");
// document.writeln("");
// document.writeln("</table>");

$.ajax({
    url: httpApi + `/api/kaijiang/getRccx?num=2&web=2&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        let data = response.data
        if (data.length > 0) {
            let attach = response.attach
            let crcHtml = ""
            let attrHtml = ""
            
            attach.forEach(el=>{
                attrHtml += `${el.name}:${el.code.split(",").join("-")}<br>`
            })
            $("#crc_attach").html(attrHtml)
            data.forEach(el=>{

                let sx = el.res_sx.split(',')
                let sx_ = sx[sx.length -1]
                let rc = JSON.parse(el.content)
                let rc_hrml = ''
                let n = ''
                for(let i in rc){
                    n = rc[i].split('|')[0]
                    if(null != el.res_code && el.res_code.length>0 && rc[i].indexOf(sx_) != -1){
                        rc_hrml += `<span style='background-color: #FFFF00'>`+n+`</span>`
                    }else{
                        rc_hrml += n
                    }
                }
            
            
                crcHtml +=  `
                		<tr>
                			<td class="td">
                				<p align="center">${el.term}期:<font color="#0000FF">肉菜草肖</font><font color="#FF0000">【`+rc_hrml+`】</font>开${getResultNoTxt(el.res_code,el.res_sx)}准
                			</td>
                		</tr>
                `
            })
            let html = `<div class="list-title">台湾肉菜草肖</div><table class="ptyx11" width="100%" border="1">
  <tbody>`+crcHtml+`</tbody></table>`
            $("#crcbox").html(html)
           
        }
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 







