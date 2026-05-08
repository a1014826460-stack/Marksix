$.ajax({
    url: httpApi + `/api/kaijiang/getSjsx?num=3&web=${web}&type=${type}`, 
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
                let content = JSON.parse(d.content);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0].split('')[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }
                let c1 = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00;">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }
                
                htmlBoxList = htmlBoxList + ` 
  
  <tr>
      <td class="td">
        <p align="center">${d.term}期:
          <font color="#0000FF">四季生肖</font>
          <font color="#FF0000">【${c1.join('')}】</font>开${sx||'？'}${code||'00'}准</td>
  </tr>
  
            `}
        }
        
        htmlBox = `<div class="list-title">台湾四季生肖</div>
<table class="ptyx11" width="100%" border="1">
  <tr>
        
        `+htmlBoxList+` 

    <tr>
      <td class="td">
        <p align="center">
          <font color="#FF9900"></font>春肖:兔虎龙
          <br>夏肖:羊蛇马
          <br>秋肖:狗鸡猴
          <br>冬肖:猪牛鼠
          <br>
          <font color="#FF9900"></font></td>
    </tr>
</table>`
        
        
        $("#sjsxBox").html(htmlBox)
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 












    // <tr>
    //   <td class="td">
    //     <p align="center">269期:
    //       <font color="#0000FF">四季生肖</font>
    //       <font color="#FF0000">【夏冬春】</font>开？00准</td></tr>
    // <tr>
    //   <td class="td">
    //     <p align="center">268期:
    //       <font color="#0000FF">四季生肖</font>
    //       <font color="#FF0000">【冬
    //         <span style='background-color: #FFFF00'>夏</span>春】</font>开羊22准</td></tr>
   
