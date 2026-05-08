$.ajax({
    url: httpApi + `/api/kaijiang/sbzt?web=${web}&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        
        if(data.length>0){
            
            data = data.slice(0, 6);
            
            for(let i in data){
                let d = data[i]
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao =  [];
                let xiaoV =  [];
                let ma = [];
                let bo = d.content.split(',');

                let c1 = [];
                for (let i = 0; i < bo.length; i++) {
                    let nums = getNumsByColor(bo[i].split('')[0]);
                    console.log(d.term,nums,code,bo[i])
                    if (nums && code && nums.indexOf(code) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">${bo[i]}</span>`);
                    }else {
                        c1.push(`${bo[i]}`)
                    }
                }


                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
    
    <tr>
      <td>
        <font color='#0000FF'>${data[i].term}期:</font>
        <font color='#000000'>双波中特
          <span class='zl'>&laquo;</span></font>
        <span class='zl'>${c1.join('')}
          <font color='#000000'>&raquo;</font></span>
        <font color='#000000'>开:</font>${sx||'？'}${code||'00'}准</td>
    </tr>
    
            `}
        }
        
        htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title'>台湾六合彩论坛『双波中特』</div>
  <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1782'>   
        `+htmlBoxList+` 
 </table>
</div>

`
        
        
        $("#sbztBox").html(htmlBox)
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 

