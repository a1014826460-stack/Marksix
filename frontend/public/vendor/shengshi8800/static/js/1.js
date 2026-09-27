var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };


$.ajax({
    url: httpApi + `/api/kaijiang/yyptj?web=${web}&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        
        if(data.length>0){
            for(let i in data){
                
                let result = '00'
                
                //console.log(ma)
                // 命中判定：口径见 legacy-prediction-verdict.js（mode 244 为纯文本诗句，
                // 接口未返回可核对的候选生肖/号码，因此当前不显示判定）
                let __verdictTxt = window.legacyPredictionVerdict ? window.legacyPredictionVerdict.verdictText(window.legacyPredictionVerdict.verdictOf(244, data[i])) : '';
                htmlBoxList = htmlBoxList + ` 


<font color="#008000">${data[i].term}期《一语破天机》开[${getResultNoTxt(data[i].res_code,data[i].res_sx)}]${__verdictTxt}</font>
<br>
<font color="#0000FF">${data[i].content}</font>
<br>
<font color="#C0C0C0">......................................................</font>
<br>
  
            `}
        }
        
        htmlBox = `<div class="list-title">台湾一语破天机</div>
<table class="ptyx11" width="100%" border="1">
  <tr>
    <td align="left" height=60>
      <p align="center">
        <font style="font-size: 13pt">
          <b>
        
        `+htmlBoxList+` 
</b>
    </td>
  </tr>
</table>`
        
        
        $("#yyptjBox").html(replaceLegacySiteText(htmlBox))
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});   

