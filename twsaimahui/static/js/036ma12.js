$.ajax({
    url: httpApi + `/api/kaijiang/getYbzt?web=${web}&type=${type}&num=2`,
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
                let ma = [];
                let nums = getNumsByColor(d.content.split('')[0]);
                let c1 = [];
                let zj = false;
                if (code && nums[i].indexOf(code) !== -1) {
                    zj = true;
                    c1.push(`<span style="background-color: #FFFF00">${d.content}</span>`);
                }else {
                    c1.push(`${d.content}`)
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>一波中特</strong></span>:【<span class='stylezi'><strong>${c1.join('')}</strong></span><strong>】 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
</strong>
</td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>一波中特</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【春风化雨】【一波中特】</span>
</td>
</tr>		

            ${htmlBoxList}
            </table>
        `;
        $(".l27").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>一波中特</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【春风化雨】【一波中特】</span>
</td>
</tr>		





















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>一波中特</strong></span>:【<span class='stylezi'><strong>蓝波</strong></span><strong>】 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>一波中特</strong></span>:【<span class='stylezi'><strong>红波</strong></span><strong>】 开:蛇12准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>一波中特</strong></span>:【<span class='stylezi'><strong>绿波</strong></span><strong>】 开:虎27准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>一波中特</strong></span>:【<span class='stylezi'><strong>红波</strong></span><strong>】 开:猪30准
</strong>
</td>
</tr>	


 
 
 
 
  
 


</table>*/
