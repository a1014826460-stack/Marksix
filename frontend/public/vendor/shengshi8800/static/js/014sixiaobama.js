var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/sxbm?web=${web}&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        
        if(data.length>0){
            for(let i in data){
                let d = data[i];
                let resCode = d.res_code.split(",");
                let resSx = d.res_sx.split(",");
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = [];
                let ma = [];
                let maValue = [];
                let content = d.content.split(",");
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    maValue[i] = c[1];
                    ma.push(...c[1].split('.'));
                }

                let c = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) !== -1) {
                        c.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c.push(`${xiao[i]}`)
                    }
                }
                let c1 = [];
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">${ma[i]}</span>`);
                    }else {
                        c1.push(`${ma[i]}`)
                    }
                }

                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
    <tr>
      <td>
        <font color='#000000'>${data[i].term}期【四肖八码】${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}准
          <br></font>
        <span class='zl'>
            ${c[0]}【${c1.slice(0,2).join('.')}】${c[1]}【${c1.slice(2,4).join('.')}】
          <br>${c[2]}【${c1.slice(4,6).join('.')}】${c[3]}【${c1.slice(6,8).join('.')}】</span>
      </td>
    </tr>
    
    
            `}
        }
        
        htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title'>台湾六合彩论坛『四肖八码』 </div>
  <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
        `+htmlBoxList+` 
 </table>
</div>

`
        
        
        $(".sxbmBox").html(replaceLegacySiteText(htmlBox))
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 



