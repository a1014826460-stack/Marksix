var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

// 该模块后端为「8肖中特」(mode 48)：content 是 8 组 `生肖|配码`。
// 原实现只取前 5 肖渲染，导致判定用 8 肖、页面只显示 5 肖，用户看不出命中原因。
// 现改为完整显示 8 肖（配码不展示，判定只按生肖）。
function normalizeWxztContent(content) {
    if (Array.isArray(content)) {
        content = content.join(',');
    }

    content = String(content || '').trim();
    if (!content) {
        return '';
    }

    if (content.charAt(0) === '[' && content.charAt(content.length - 1) === ']') {
        try {
            let parsed = JSON.parse(content);
            if (Array.isArray(parsed)) {
                content = parsed.join(',');
            }
        } catch (error) {
            content = content.replace(/^\[/, '').replace(/\]$/, '').replace(/"/g, '');
        }
    }

    let items = content.split(',').map(function(item) {
        return String(item || '').trim();
    }).filter(Boolean);

    if (items.length === 0) {
        return '';
    }

    return items.map(function(item) {
        return item.split('|')[0].trim();
    }).filter(Boolean).join(',');
}

function renderWxztContent(content, resSx) {
    return selNumBcMa22(normalizeWxztContent(content), resSx);
}

$.ajax({
    url: httpApi + `/api/kaijiang/wxzt?web=${web}&type=${type}`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {

        let htmlBox = '', htmlBoxList = '', term = '';

        let data = response.data;

        if (data.length > 0) {
            for (let i in data) {

                let result = '00';
                let displayContent = renderWxztContent(data[i].content, data[i].res_sx);

                let __verdictTxt = window.legacyPredictionVerdict ? window.legacyPredictionVerdict.verdictText(window.legacyPredictionVerdict.verdictOf(48, data[i])) : '';
                htmlBoxList = htmlBoxList + `

  <tr>
    <td height="40" bordercolor="#D5E5E8">
      <p align="center">
        <font face="微软雅黑" size="4">
          <b>${data[i].term}期:
            <font color='#008080' size="4">八肖中特</font>
            <font color="#FF00FF">╠${displayContent}╣</font>开
            <font color="#0000FF">${getResultNoTxt(data[i].res_code, data[i].res_sx)}</font>${__verdictTxt}</b></td>
  </tr>

            `;
            }
        }

        htmlBox = `<div class="list-title">台湾八肖中特</div>
<table class="ptyx11" width="100%" border="1">

        ` + htmlBoxList + `

</table>`;


        $("#wxztBox").html(replaceLegacySiteText(htmlBox));

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
