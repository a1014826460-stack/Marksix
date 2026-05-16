$.ajax({
    url: httpApi + `/api/kaijiang/getTou?web=${web}&type=${type}&num=2`,
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
                let content = JSON.parse(d.content);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0].split('')[0])
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

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>两头中特</strong></span>:【<span class='stylezi'><strong>${c1.join('.')}</strong></span><strong>】 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>两头中特</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【风平浪静】【两头中特】</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l44").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>两头中特</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【风平浪静】【两头中特】</span>
</td>
</tr>		

















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>两头中特</strong></span>:【<span class='stylezi'><strong>1.3</strong></span><strong>】 开:？00准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>两头中特</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>1</span>.4</strong></span><strong>】 开:蛇12准
</strong>
</td>
</tr>	
 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>两头中特</strong></span>:【<span class='stylezi'><strong>2.<span style='background-color: #FFFF00'>3</span></strong></span><strong>】 开:猪30准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>两头中特</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>1</span>.4</strong></span><strong>】 开:龙13准
</strong>
</td>
</tr>	


 
 
 

 
 

 


 

 
 



</table>*/
