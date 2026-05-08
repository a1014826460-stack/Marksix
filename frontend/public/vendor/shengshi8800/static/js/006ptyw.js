var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/ptyw?web=${web}&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        
        if(data.length>0){
            data = data.slice(0, 8);
            for(let i in data){
                let result = '00'
                let d = data[i]
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = [];
                let ma = [];
                let maValue = [];
                let content = JSON.parse(d.content);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0].split('')[0])
                    maValue[i] = c[1];
                    ma.push(...c[1].split(','));
                }
                let c = [];
                let num;
                for (let i = 0; i < xiao.length; i++) {
                    num = getZjNum(maValue[i],codeSplit);
                    if (num) {
                        c.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c.push(`${xiao[i]}`)
                    }
                }
                // let wei = parseInt()
                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
    
     <tr>
      <td>
        <font color='#0000FF'>${data[i].term}期:</font><font color='#000000'>平特一尾<span class='zl'>《</span></font><span class='zl'>${c[0]}${c[0]}${c[0]}${c[0]}${c[0]}<font color='#000000'>》</font></span><font color='#000000'>开</font>${num||'00'}准</td>
    </tr>
    
            `}
        }
        
        htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title'>台湾六合彩论坛『平特一尾
    <span class='zl'>』 </div>
  <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1810'>
        `+htmlBoxList+` 
 </table>
</div>

`
        
        
        $(".ptywBox").html(replaceLegacySiteText(htmlBox))
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 















    // <tr>
    //   <td>
    //     <font color='#0000FF'>269期:</font>
    //     <font color='#000000'>平特一尾
    //       <span class='zl'>《</span></font>
    //     <span class='zl'>55555
    //       <font color='#000000'>》</font></span>
    //     <font color='#000000'>开</font>00准</td></tr>
    // <tr>
    //   <td>
    //     <font color='#0000FF'>268期:</font>
    //     <font color='#000000'>平特一尾
    //       <span class='zl'>《</span></font>
    //     <span class='zl'>99999
    //       <font color='#000000'>》</font></span>
    //     <font color='#000000'>开</font>09准</td>
    // </tr>
   
