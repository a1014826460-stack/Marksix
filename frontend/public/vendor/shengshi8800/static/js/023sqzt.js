$.ajax({
    url: httpApi + `/api/kaijiang/getSanqiXiao4new?web=${web}&type=${type}`,
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        
        if(data.length>0){

            for(let i in data){
                let d = data[i]
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = [];
                let xiaoV = [];
                let ma = [];
                let content = [];
                try {
                    content = JSON.parse(d.content || "[]");
                } catch (error) {
                    content = [];
                }
                if (!(content instanceof Array)) {
                    content = [];
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (code && xiaoV[i].indexOf(code) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }
                let term = '中1期';
                if (!sx) term = '中几期'

                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 

    <tr>
      <td>
        <font color='#000000'>${data[i].start}-${data[i].end}期:</font>
        <font color='#0000FF'>三期中特→
          <span class='zl'>[${c1.join('')}]</span></font>开:${term}</td>
    </tr>    
    
            `}
        }
        
        htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title'>台湾六合彩→
    <font color='#FF0000'>【</font>三期中特
    <font color='#FF0000'>】</font>→39821</div>
  <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>      
        `+htmlBoxList+` 
  </table>
</div>

`
        
        
        $("#sqbzBox").html(htmlBox)
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 





    // <tr>
    //   <td>
    //     <font color='#000000'>269-271期:</font>
    //     <font color='#0000FF'>三期中特→
    //       <span class='zl'>[兔龙猴鼠]</span></font>开:中几期</td>
    // </tr>
    // <tr>
    //   <td>
    //     <font color='#000000'>266-268期:</font>
    //     <font color='#0000FF'>三期中特→
    //       <span class='zl'>[马兔
    //         <span style='background-color: #FFFF00'>羊</span>狗]</span></font>开:中几期</td>
    // </tr>
    // <tr>
    //   <td>
    //     <font color='#000000'>263-265期:</font>
    //     <font color='#0000FF'>三期中特→
    //       <span class='zl'>[猴
    //         <span style='background-color: #FFFF00'>龙</span>马虎]</span></font>开:中1期</td>
    // </tr>
