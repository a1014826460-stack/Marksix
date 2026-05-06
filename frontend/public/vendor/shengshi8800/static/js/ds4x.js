$.ajax({
    url: httpApi + `/api/kaijiang/getDsnx?num=4&web=2&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        let attach = response.attach
        if(data.length>0){
            for(let i in data){
                let d = data[i]
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao =  [];
                let xiaoV =  [];
                let ma = [];

                
                htmlBoxList = htmlBoxList + `<tr>
    <td class="td1" height="20" width="363">
${d.term}期<br> </td>
<td><font color="#0000FF">单:${selNumBcMa22(data[i].xiao_1,data[i].res_sx)}</td>
<td><font color="#0000FF">双:${selNumBcMa22(data[i].xiao_2,data[i].res_sx)}</font></td>
<td>
中:<font color="#FF0000">开${getResultNoTxt(data[i].res_code,data[i].res_sx)}</font>
</td>
</tr>
        `
        }
        }
        
        htmlBox = `<div class="list-title">单双各四肖</div>
<table class="sqbk" width="100%" border="1">
  <tbody>
        
        `+htmlBoxList+` </tbody></table>`
        
        
        $(".ds4xbox").html(htmlBox)
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 








