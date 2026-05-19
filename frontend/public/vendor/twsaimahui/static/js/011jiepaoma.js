$.ajax({
    url: httpApi + `/api/kaijiang/getXiaoma2?web=${web}&type=${type}&num=7`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let yinx = '';
        let yangx = '';
        let imgUrl;
        if (data.length > 0) {
            for (let i in data) {
                let d = data[i]
                if (!imgUrl && d.image_url) {
                    if (d.image_url.indexOf('http') > -1) {
                        imgUrl = d.image_url;
                    }else {
                        imgUrl = httpApi + d.image_url;
                    }
                }
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
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }
                let c2 = [];
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) !== -1) {
                        zj = true;
                        c2.push(`<span style="background-color: #FFFF00">${ma[i]}</span>`);
                    }else {
                        c2.push(`${ma[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td style='text-align:center' height='60'>
<table border=1 width=100% bgcolor=#ffffff><tbody>
<td style='margin: 0px; padding: 3px 2px;  word-break: break-all; text-align: center; line-height: 26px;'>
<p style='font-size: 13pt; margin-bottom: 8px; text-align: left;'>
<b>
${d.term}期跑马图解<font color='#0000FF'>七肖14码</font><br></b>
<b>
<font color='#008000'>
<span style='font-family: 宋体; text-indent: 2em; font-size: 16px'>
精解七肖：${c1.join('')}</span></font><font color='#0000FF'><span style='color: #008000; font-family: 宋体; text-indent: 2em; font-size: 16px'><br>
精解14码：${c2.join('.')}</table>
</tr></td>
            `
            }
        }
        htmlBoxList = `
<style type='text/css'>
.stylejpg {
	background-color: #FFFF00;
}
</style>

<tr>
<td style='text-align:center' height='60'>
<table border=1 width=100% bgcolor=#ffffff><tbody>
 	<tr>
      <td width='100%' bordercolor='#FF0000' bgcolor='#FF0000' align='center' style='margin: 0; padding: 0; height: 40px;'>
		<b><font face='微软雅黑' color='#FFFFFF' size='5'> 《解澳跑马》</font></td></tr>
</table>

            ${htmlBoxList}
        `;
        $(".l18").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});
/*


<style type='text/css'>
.stylejpg {
	background-color: #FFFF00;
}
</style>


<tr>
<td style='text-align:center' height='60'>
<table border=1 width=100% bgcolor=#ffffff><tbody>
 	<tr>
      <td width='100%' bordercolor='#FF0000' bgcolor='#FF0000' align='center' style='margin: 0; padding: 0; height: 40px;'>
		<b><font face='微软雅黑' color='#FFFFFF' size='5'> 《解澳跑马》</font></td></tr>
</table>

<tr>
<td style='text-align:center' height='60'>
<table border=1 width=100% bgcolor=#ffffff><tbody>
<td style='margin: 0px; padding: 3px 2px;  word-break: break-all; text-align: center; line-height: 26px;'>
<p style='font-size: 13pt; margin-bottom: 8px; text-align: left;'>
<b>
268期跑马图解<font color='#0000FF'>七肖14码</font><br></b>
<b>
<font color='#008000'>
<span style='font-family: 宋体; text-indent: 2em; font-size: 16px'>
精解七肖：鼠牛虎兔龙蛇鸡</span></font><font color='#0000FF'><span style='color: #008000; font-family: 宋体; text-indent: 2em; font-size: 16px'><br>
精解14码：29.17.40.28.03.39.14.26.25.37.12.24.20.32</table>
</tr></td>



<tr>
<td style='text-align:center' height='60'>
<table border=1 width=100% bgcolor=#ffffff><tbody>
<td style='margin: 0px; padding: 3px 2px;  word-break: break-all; text-align: center; line-height: 26px;'>
<p style='font-size: 13pt; margin-bottom: 8px; text-align: left;'>
<b>
267期跑马图解<font color='#0000FF'>七肖14码</font><br></b>
<b>
<font color='#008000'>
<span style='font-family: 宋体; text-indent: 2em; font-size: 16px'>
精解七肖：龙虎马猴狗<span style='background-color: #FFFF00'>蛇</span>鸡</span></font><font color='#0000FF'><span style='color: #008000; font-family: 宋体; text-indent: 2em; font-size: 16px'><br>
精解14码：25.37.15.39.23.47.45.21.43.31.<span style='background-color: #FFFF00'>12</span>.48.08.20</table>
</tr></td>
 

<tr>
<td style='text-align:center' height='60'>
<table border=1 width=100% bgcolor=#ffffff><tbody>
<td style='margin: 0px; padding: 3px 2px;  word-break: break-all; text-align: center; line-height: 26px;'>
<p style='font-size: 13pt; margin-bottom: 8px; text-align: left;'>
<b>
264期跑马图解<font color='#0000FF'>七肖14码</font><br></b>
<b>
<font color='#008000'>
<span style='font-family: 宋体; text-indent: 2em; font-size: 16px'>
精解七肖：猴鸡狗<span style='background-color: #FFFF00'>猪</span>兔马羊</span></font><font color='#0000FF'><span style='color: #008000; font-family: 宋体; text-indent: 2em; font-size: 16px'><br>
精解14码：09.33.08.44.19.43.06.42.14.02.23.47.22.46</table>
</tr></td>
 




 


 
 
 

  
 
 
 
 

*/
