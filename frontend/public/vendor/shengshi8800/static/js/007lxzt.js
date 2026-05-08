var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/lxzt?web=${web}&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        
        if(data.length>0){
            
            data = data.slice(0, 10);

            for(let i in data){
                let d = data[i];
                let resCode = d.res_code.split(",");
                let resSx = d.res_sx.split(",");
                let result = '00'
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

                htmlBoxList = htmlBoxList + ` 
    
    <tr>
      <td>
        <font color='#0000FF'>${data[i].term}期:</font>
        <font color='#000000'>必中六肖
          <span class='zl'>&laquo;</span></font>
        <span class='zl'>${c.join('')}
          <font color='#000000'>&raquo;</font></span>
        <font color='#000000'>开</font>${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}准</td>
    </tr>
    
            `}
        }
        
        htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title'>台湾六合彩论坛『六肖中特』</div>
  <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'> 
        `+htmlBoxList+` 
 </table>
</div>

`
        
        
        $(".lxztBox").html(replaceLegacySiteText(htmlBox))
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 










    // <tr>
    //   <td>
    //     <font color='#0000FF'>269期:</font>
    //     <font color='#000000'>必中六肖
    //       <span class='zl'>&laquo;</span></font>
    //     <span class='zl'>龙牛兔鸡虎猪
    //       <font color='#000000'>&raquo;</font></span>
    //     <font color='#000000'>开</font>？00准</td></tr>
    // <tr>
    //   <td>
    //     <font color='#0000FF'>268期:</font>
    //     <font color='#000000'>必中六肖
    //       <span class='zl'>&laquo;</span></font>
    //     <span class='zl'>
    //       <span style='background-color: #FFFF00'>羊</span>鼠猪龙牛鸡
    //       <font color='#000000'>&raquo;</font></span>
    //     <font color='#000000'>开</font>羊22准</td>
    // </tr>
    // <tr>
    
   
