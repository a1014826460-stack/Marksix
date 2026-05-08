var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

document.writeln("<div class=\"list-title\">台湾大小中特</div><table class=\"ptyx11\" width=\"100%\" border=\"1\">");
// document.writeln("  <tr>");
// document.writeln("    <th>台湾大小中特</th>");
// document.writeln("  </tr>");
document.writeln(" ");
document.writeln("");
document.writeln("  </tr>");
document.writeln("  ");
document.writeln("");


document.writeln("<table id='dxzt'  border=1 width=100% bgcolor=#ffffff style='font-weight:bold'><tbody></tbody></table>");

// 


// document.writeln("    <tr>");
// document.writeln("    <td class=\"td\">");
// document.writeln("	<p align=\"center\">269期:<font color=\"#0000FF\">大数小数</font><font color=\"#FF0000\">【大数+0头】</font>开？00准</td>");
// document.writeln("  </tr>");

$.ajax({
    url: httpApi + `/api/kaijiang/getDxztt1?num=1&web=${web}&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        if(response.data.length > 0){
            let html = ""
            let w = ''
            let dx = ''
            let dx_ = ''
            let t = ''
            let code = ''
            let tm = ''

            response.data.forEach(el=>{
                tm = code=dx=dx_=w=''
                t= JSON.parse(el.tou)[0][0]
                w = selTxtBcT2(t,el.res_code)
                if(null != el.res_code && el.res_code.length>0){
                    code = el.res_code.split(',')
                    tm = code[code.length-1]
                }
                dx = JSON.parse(el.content)[0].split('|')
             
                if(null != el.res_code && el.res_code.length>0 && dx[1].indexOf(tm) != -1){
                    dx_ = `<span style="background-color: #FFFF00">${dx[0]}数</span>`
                }else{
                    dx_ = dx[0]+'数'
                }
                dx = ''
                html += `<tr>
                            <td class="td">
                                <p align="center">${el.term}期:<font color="#0000FF">大数小数</font><font color="#FF0000">【${dx_}+${w}】</fon>开${getResult(el.res_code,el.res_sx)}
                            </td>
                        </tr>`
            })
            
            $("#dxzt").html(replaceLegacySiteText(html))
        }
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});


 
  
document.writeln("</table>");

