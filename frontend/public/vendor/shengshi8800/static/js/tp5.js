$.ajax({
    url: httpApi + `/api/kaijiang/getPmxjcz?web=${web}&type=${type}&num=6`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let dw = '';
        let xw = '';
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
                let xiao =  [];
                let xiaoV =  [];
                let ma = [];
                let content = JSON.parse(d.x7m14);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0].split('')[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }
                let c1 = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }
                let c2 = [];
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) !== -1) {
                        c2.push(`<span style="background-color: #FFFF00">${ma[i]}</span>`);
                    }else {
                        c2.push(`${ma[i]}`)
                    }
                }
                htmlBoxList += ` 
<table  border=1 width=100% bgcolor=#ffffff style='font-weight:bold'>
 <td style='margin: 0px; padding: 3px 2px;  word-break: break-all; text-align: center; line-height: 26px;'>
<p style='font-size: 12pt; margin-bottom: 8px; text-align: left;'>
<font face='楷体' size='4'>
<b>
<font color='#800000'><span style='background-color: #C0C0C0'>${d.year}-${d.term}期跑马玄机测字</span></font><font color='#FF0000'>开${sx||'？'}${code||'00'}准</font></b>
</font>
<b>
<font color='#0000FF' face='微软雅黑' size='4'><br>
</font>
<font face='微软雅黑'>
<span style='background-color: #FFFF00'>
<font color='#FF0000' size='5'>${d.title}</font></span></font><font face='微软雅黑' size='4' color='#0000FF'><br>
</font></b><font color='#0000FF'><font face='微软雅黑' size='3'>
解：${d.content.replaceAll('\n',`<br>`)}<br>
</font></font><font face='微软雅黑' size='4'>
<b>
<br>
</b>
<font size='4'>
<font color='#800000'>
<span style='font-family: 微软雅黑; text-indent: 2em'>
综合七肖：${c1.join('')}</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br>
</span><font color='#800000'>
<span style='font-family: 微软雅黑; text-indent: 2em'>
综合五肖：${c1.slice(0,5).join('')}</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br>
</span><font color='#800000'>
<span style='font-family: 微软雅黑; text-indent: 2em'>
综合三肖：${c1.slice(0,3).join('')}</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br>
</span><font color='#800000'>
<span style='font-family: 微软雅黑; text-indent: 2em'>
主特：${c2.join('.')}</span></font></font><b><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; font-size: 16px'>
</span></p>
</table>
            `
            }
        }
        htmlBoxList = `
<!--div class="tit"><a href="https://t2.xn--odc6dra3b5a7f.xn--hdc6bwac9bsvfl0m6eh.xn--gecrj9c:8443/#pm49dh"><font size="2">点击提前查看跑马解图</font></a></div-->
         <tr>
<th>台湾梦影逍遥『跑马图』</th>
</tr>
${htmlBoxList}
            
        `;
        $(".tp5").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});


// <!doctype html>
// <html>
// <head>
// <meta charset='utf-8'>
// <title>无标题文档</title>
// </head>
//
// <body>
//
// <img src='https://ttuu.wyvogue.com:4949/col/269/ampm.jpg' width='100%'></img>
//
//
//
//
//
// <div class="tit"><a href="https://t2.xn--odc6dra3b5a7f.xn--hdc6bwac9bsvfl0m6eh.xn--gecrj9c:8443/#pm49dh"><font size="2">点击提前查看跑马解图</font></a></div>
//
// //   <!--？？？-- >
//
//
// <table id='tp5'  border=1 width=100% bgcolor=#ffffff style='font-weight:bold'><tbody></tbody></table>
//
// let html =  `
// 		<tr>
// 			<td style='text-align:center' height='60'>
// 			<table class="ptyx" width="100%" border="1">
// 				<tr>
// 					<th>台湾梦影逍遥『跑马图』</th>
// 				</tr>
// 				<td style='margin: 0px; padding: 3px 2px;  word-break: break-all; text-align: center; line-height: 26px;'><p style='font-size: 12pt; margin-bottom: 8px; text-align: left;'><font face='楷体' size='4'><b><font color='#800000'><span style='background-color: #C0C0C0'>2024-268期跑马玄机测字</span></font><font color='#FF0000'>开羊22准</font></b></font><b><font color='#0000FF' face='微软雅黑' size='4'><br></font>
// 				<font face='微软雅黑'><span style='background-color: #FFFF00'><font color='#FF0000' size='5'>沙</font></span></font><font face='微软雅黑' size='4' color='#0000FF'><br></font></b><font color='#0000FF'><font face='微软雅黑' size='3'>解：沙：细碎的石粒解土肖牛羊龙狗，五行水解水肖鼠猪。<br></font></font><font face='微软雅黑' size='4'><b><br></b><font size='4'><font color='#800000'><span style='font-family: 微软雅黑; text-indent: 2em'>综合七肖：牛<span style='background-color: #FFFF00'>羊</span>龙狗鼠猪兔</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br></span><font color='#800000'><span style='font-family: 微软雅黑; text-indent: 2em'>综合五肖：牛<span style='background-color: #FFFF00'>羊</span>龙狗鼠</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br></span><font color='#800000'><span style='font-family: 微软雅黑; text-indent: 2em'>综合三肖：牛<span style='background-color: #FFFF00'>羊</span>龙</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br></span><font color='#800000'><span style='font-family: 微软雅黑; text-indent: 2em'>主特：27.39.02.26.35.47.10.19.30.33</span></font></font><b><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; font-size: 16px'></span></p>
// 		</table>
// `
//
// $("#tp5").html(html)

 
// <tr>
// <td style='text-align:center' height='60'>
// <table class="ptyx" width="100%" border="1">
//   <tr>
//     <th>台湾梦影逍遥『跑马图』</th>
//   </tr>
// 
// 
//  
// <td style='margin: 0px; padding: 3px 2px;  word-break: break-all; text-align: center; line-height: 26px;'>
// <p style='font-size: 12pt; margin-bottom: 8px; text-align: left;'>
// <font face='楷体' size='4'>
// <b>
// <font color='#800000'><span style='background-color: #C0C0C0'>2024-000期跑马玄机测字</span></font><font color='#FF0000'>开？00准</font></b>
// </font>
// <b>
// <font color='#0000FF' face='微软雅黑' size='4'><br>
// </font>
// <font face='微软雅黑'>
// <span style='background-color: #FFFF00'>
// <font color='#FF0000' size='5'>？</font></span></font><font face='微软雅黑' size='4' color='#0000FF'><br>
// </font></b><font color='#0000FF'><font face='微软雅黑' size='3'>
// 解：研究中。<br>
// </font></font><font face='微软雅黑' size='4'>
// <b>
// <br>
// </b>
// <font size='4'>
// <font color='#800000'>
// <span style='font-family: 微软雅黑; text-indent: 2em'>
// 综合七肖：更新中</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br>
// </span><font color='#800000'>
// <span style='font-family: 微软雅黑; text-indent: 2em'>
// 综合五肖：更新中</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br>
// </span><font color='#800000'>
// <span style='font-family: 微软雅黑; text-indent: 2em'>
// 综合三肖：更新中</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br>
// </span><font color='#800000'>
// <span style='font-family: 微软雅黑; text-indent: 2em'>
// 主特：更新中</span></font></font><b><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; font-size: 16px'>
// </span></p>
//   </table>
//   
//   
//   
//   <!--结束--> 

 
 
 
// <tr>
// <td style='text-align:center' height='60'>
// <table class="ptyx" width="100%" border="1">
//   <tr>
//     <th>台湾梦影逍遥『跑马图』</th>
//   </tr>
// 
// 
//  
// <td style='margin: 0px; padding: 3px 2px;  word-break: break-all; text-align: center; line-height: 26px;'>
// <p style='font-size: 12pt; margin-bottom: 8px; text-align: left;'>
// <font face='楷体' size='4'>
// <b>
// <font color='#800000'><span style='background-color: #C0C0C0'>2024-269期跑马玄机测字</span></font><font color='#FF0000'>开？00准</font></b>
// </font>
// <b>
// <font color='#0000FF' face='微软雅黑' size='4'><br>
// </font>
// <font face='微软雅黑'>
// <span style='background-color: #FFFF00'>
// <font color='#FF0000' size='5'>银</font></span></font><font face='微软雅黑' size='4' color='#0000FF'><br>
// </font></b><font color='#0000FF'><font face='微软雅黑' size='3'>
// 解：银：金属元素。符号Ag。白色而有光泽，故古代称“白金解白肖虎兔马羊狗猪，五行金解金肖猴鸡。<br>
// </font></font><font face='微软雅黑' size='4'>
// <b>
// <br>
// </b>
// <font size='4'>
// <font color='#800000'>
// <span style='font-family: 微软雅黑; text-indent: 2em'>
// 综合七肖：虎兔马羊狗猪猴</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br>
// </span><font color='#800000'>
// <span style='font-family: 微软雅黑; text-indent: 2em'>
// 综合五肖：虎兔马羊狗</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br>
// </span><font color='#800000'>
// <span style='font-family: 微软雅黑; text-indent: 2em'>
// 综合三肖：虎兔马</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br>
// </span><font color='#800000'>
// <span style='font-family: 微软雅黑; text-indent: 2em'>
// 主特：27.39.02.26.35.47.10.19.30.33</span></font></font><b><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; font-size: 16px'>
// </span></p>
//   </table>
//   
//   
//   
//   <!--结束--> 

 
// <tr>
// <td style='text-align:center' height='60'>
// <table class="ptyx" width="100%" border="1">
//   <tr>
//     <th>台湾梦影逍遥『跑马图』</th>
//   </tr>
// 
// 
//  
// <td style='margin: 0px; padding: 3px 2px;  word-break: break-all; text-align: center; line-height: 26px;'>
// <p style='font-size: 12pt; margin-bottom: 8px; text-align: left;'>
// <font face='楷体' size='4'>
// <b>
// <font color='#800000'><span style='background-color: #C0C0C0'>2024-268期跑马玄机测字</span></font><font color='#FF0000'>开羊22准</font></b>
// </font>
// <b>
// <font color='#0000FF' face='微软雅黑' size='4'><br>
// </font>
// <font face='微软雅黑'>
// <span style='background-color: #FFFF00'>
// <font color='#FF0000' size='5'>沙</font></span></font><font face='微软雅黑' size='4' color='#0000FF'><br>
// </font></b><font color='#0000FF'><font face='微软雅黑' size='3'>
// 解：沙：细碎的石粒解土肖牛羊龙狗，五行水解水肖鼠猪。<br>
// </font></font><font face='微软雅黑' size='4'>
// <b>
// <br>
// </b>
// <font size='4'>
// <font color='#800000'>
// <span style='font-family: 微软雅黑; text-indent: 2em'>
// 综合七肖：牛<span style='background-color: #FFFF00'>羊</span>龙狗鼠猪兔</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br>
// </span><font color='#800000'>
// <span style='font-family: 微软雅黑; text-indent: 2em'>
// 综合五肖：牛<span style='background-color: #FFFF00'>羊</span>龙狗鼠</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br>
// </span><font color='#800000'>
// <span style='font-family: 微软雅黑; text-indent: 2em'>
// 综合三肖：牛<span style='background-color: #FFFF00'>羊</span>龙</span></font><span style='color: #FF00FF; font-family: 微软雅黑; text-indent: 2em; '><br>
// </span><font color='#800000'>
 
//   </table>
//   
//   
//   
//   <!--结束--> 

 
  
 
