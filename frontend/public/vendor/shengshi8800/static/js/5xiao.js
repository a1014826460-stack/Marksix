var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

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
    }).filter(Boolean).slice(0, 5).join(',');
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

                htmlBoxList = htmlBoxList + `

  <tr>
    <td height="40" bordercolor="#D5E5E8">
      <p align="center">
        <font face="微软雅黑" size="4">
          <b>${data[i].term}期:
            <font color='#008080' size="4">五肖中特</font>
            <font color="#FF00FF">╠${displayContent}╣</font>开
            <font color="#0000FF">${getResultNoTxt(data[i].res_code, data[i].res_sx)}</font>准</b></td>
  </tr>

            `;
            }
        }

        htmlBox = `<div class="list-title">台湾五肖中特</div>
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
