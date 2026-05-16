$.ajax({
    url: httpApi + `/api/kaijiang/getCode?web=${web}&type=${type}&num=16`,
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
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>精选16码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【${c1.slice(0,8).join('.')}】<br>【${c1.slice(8).join('.')}】</font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>16码中特</font></font></font></b></td>
</tr>


            ${htmlBoxList}
            </table>
        `;
        $(".l29").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});

/*

<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>16码中特</font></font></font></b></td>
</tr>







<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>精选16码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【06.07.08.09.17.22.23.24】<br>【25.28.30.31.32.39.40.41】</font></b></td>
</tr>
 
<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>265期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>精选16码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【01.02.03.06.08.09.10.12】<br>【15.<span style='background-color: #FFFF00'>16</span>.18.19.20.22.24.25】</font></b></td>
</tr>

<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>264期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>精选16码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【15.16.17.19.27.28.29.<span style='background-color: #FFFF00'>30</span>】<br>【31.32.33.34.35.36.39.47】</font></b></td>
</tr>

<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>263期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>精选16码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>13</span>.14.15.16.17.24.25.26】<br>【40.41.42.43.44.45.46.47】</font></b></td>
</tr>


 
 

 
 

 

</table>*/
