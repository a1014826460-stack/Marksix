$.ajax({
    url: httpApi + `/api/kaijiang/getCode?web=${web}&type=${type}&num=20`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let yinx = '';
        let yangx = '';
        if (data.length > 0) {
            for (let i in data) {
                let d = data[i]
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = [];
                let xiaoV = [];
                let ma = d.content.split(',');

                let c1 = [];
                let zj = false;
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${ma[i]}</span>`);
                    }else {
                        c1.push(`${ma[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>精选20码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【${c1.slice(0,10).join('.')}】<br>【${c1.slice(10).join('.')}】</font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
</style>
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>精选20码</font></font></font></b></td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l26").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});

/*

<style>
<!--
* { word-wrap: break-word; }
*{padding:0;margin:0}
* { word-wrap: break-word; }
* {
PADDING-BOTTOM: 0px; MARGIN: 0px; PADDING-LEFT: 0px; PADDING-RIGHT: 0px; PADDING-TOP: 0px
}
* {
WORD-WRAP: break-word
}
* {
WORD-WRAP: break-word
}
* {
WORD-WRAP: break-word
}
* {
WORD-WRAP: break-word
}
.stylesb {
background-color: #FFFF00;
}
.stylelxz {
font-family: 方正粗黑宋简体;
font-size: medium;
}
.styleliao {
color: #800080;
}
.stylezi {
color: #FF0000;
}
-->
</style>
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>精选20码</font></font></font></b></td>
</tr>












<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>精选20码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【02.03.07.16.17.18.19.20.21.31】<br>【35.38.41.42.43.44.45.46.47.48】</font></b></td>
</tr>
 
<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>265期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>精选20码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【02.03.04.05.09.10.11.14.15.<span style='background-color: #FFFF00'>16</span>】<br>【23.28.34.35.36.40.44.45.46.48】</font></b></td>
</tr>

 
 
 
  


</table>*/
