var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/getWei?num=6&web=${API_WEB}&type=${type}`,
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        if(response.data.length > 0){
            let html = ""
            let w = ''
            let htmlBoxList = ''
            
            response.data.forEach(el=>{
                
                w = selTxtBcW3(el.content,el.res_code)
                htmlBoxList += ` <tr>
<td class="td1" width="372" height="23">${el.term}期</td>
	  <td class="td2" height="23">${w.replaceAll('尾','').replaceAll(',','-')}</td>
	  <td class="td3" height="23">${getResultNoTxt(el.res_code,el.res_sx)}</td>
    </tr>
  `
          
            })
            
            html = `<div class="list-title">台湾必中六尾</div><table class="bzlx" width="100%" border="1">
  <tbody>
 `+htmlBoxList+`</tbody></table>`

            $("#6wbox").html(replaceLegacySiteText(html))
        }
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});


