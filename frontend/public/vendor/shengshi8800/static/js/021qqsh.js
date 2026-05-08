var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/qqsh?web=${web}&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        
        if(data.length>0){
            for(let i in data){
                let d = data[i];
                let resCode = data[i].res_code.split(",");
                let resSx = data[i].res_sx.split(",");
                let result = '00'
                let codeSplit = (d.res_code || '').split(',');
                let sxSplit = (d.res_sx || '').split(',');
                let code = codeSplit[codeSplit.length - 1] || '';
                let sx = sxSplit[sxSplit.length - 1] || '';
                let xiao = d.title.split(',');
                let xiaoV = [];
                let ma = [];
                let cont = d.content.split(',');;
                xiaoV[0] = cont.slice(0,3).join('');
                xiaoV[1] = cont.slice(3,6).join('');
                xiaoV[2] = cont.slice(6).join('');
                let c1 = [];
                let b = false
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        b =true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                
                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
      <td>
        <font color='#000000'>${data[i].term}期:</font>
        <font color='#0000FF'>琴棋书画→${c1.join('')}</font>开:${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}</td>
    </tr>

    
            `}
        }
        
        htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title'>台湾六合彩→
    <font color='#FF0000'>【</font>琴棋书画
    <font color='#FF0000'>】</font>→ </div>
  <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
    <tr>
      <td>
        <font color='#000000'></font>
        <span class='zl'>琴:兔蛇鸡　棋:鼠牛狗
          <br>书:虎龙马　画:羊猴猪</span></td>
    </tr>
        `+htmlBoxList+` 
 </table>
</div>

`
        
        
        $("#qqshBox").html(replaceLegacySiteText(htmlBox))
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 





    
    // <tr>
    //   <td>
    //     <font color='#000000'>269期:</font>
    //     <font color='#0000FF'>琴棋书画→书画棋</span></font>开:？00</td>
    // </tr>
    // <tr>
    //   <td>
    //     <font color='#000000'>267期:</font>
    //     <font color='#0000FF'>琴棋书画→画
    //       <span style='background-color: #FFFF00'>琴</span>书</span></font>开:蛇12</td>
    // </tr>
   
