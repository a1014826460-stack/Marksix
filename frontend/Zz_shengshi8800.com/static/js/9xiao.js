$.ajax({
    url: httpApi + `/api/kaijiang/jxzt?web=2&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        
        if(data.length>0){
            
            data = data.slice(0, 10);
            
            for(let i in data){
                
                
                let result = '00'
                
                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 

  <tr>
    <td align='center' height=38>
      <b>
        <font color='#000000' style='font-size: 13pt'>${data[i].term}期</font>
        <font color='#008000' style='font-size: 13pt'>【${selNumBcMa22(data[i].content,data[i].res_sx)}】</font>
        <font color='#000000' style='font-size: 13pt'>开</font>
        <font color='#FF0000' style='font-size: 13pt'>${getResultNoTxt(data[i].res_code,data[i].res_sx)}</font>
        <font color='#000000' style='font-size: 13pt'>准</font></b>
    </td>
  </tr>
  
            `}
        }
        
        htmlBox = `<div class="list-title">台湾九肖中特</div>
<table class="ptyx11" width="100%" border="1">
        
        `+htmlBoxList+` 
 </table>`
        
        
        $("#jxztBox1").html(htmlBox)
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 