$.ajax({
    url: httpApi + `/api/kaijiang/wxzt?web=${web}&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        
        if(data.length>0){
            data = data.slice(0, 6);
            for(let i in data){
                
                let result = '00'
                
                // let content = data[i].content.split(',')
                
                htmlBoxList = htmlBoxList + ` 
  
  <tr>
    <td height="40" bordercolor="#D5E5E8">
      <p align="center">
        <font face="微软雅黑" size="4">
          <b>${data[i].term}期:
            <font color='#008080' size="4">五肖中特</font>
            <font color="#FF00FF">╠${selNumBcMa22(data[i].content,data[i].res_sx)}╣</font>开
            <font color="#0000FF">${getResultNoTxt(data[i].res_code,data[i].res_sx)}</font>准</b></td>
  </tr>
  
            `}
        }
        
        htmlBox = `<div class="list-title">台湾五肖中特</div>
<table class="ptyx11" width="100%" border="1">
        
        `+htmlBoxList+` 

</table>`
        
        
        $("#wxztBox").html(htmlBox)
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 





//   <!--开始-->
//   <tr>
//     <td height="40" bordercolor="#D5E5E8">
//       <p align="center">
//         <font face="微软雅黑" size="4">
//           <b>269期:
//             <font color='#008080' size="4">五肖中特</font>
//             <font color="#FF00FF">╠羊龙牛鼠狗╣</font>开
//             <font color="#0000FF">？00</font>准</b></td>
//   </tr>
//   <!--结束-->
//   <!--开始-->
//   <tr>
//     <td height="40" bordercolor="#D5E5E8">
//       <p align="center">
//         <font face="微软雅黑" size="4">
//           <b>268期:
//             <font color='#008080' size="4">五肖中特</font>
//             <font color="#FF00FF">╠猪猴
//               <span style='background-color: #FFFF00'>羊</span>鸡龙╣</font>开
//             <font color="#0000FF">羊22</font>准</b></td>
//   </tr>
//   <!--结束-->
 
