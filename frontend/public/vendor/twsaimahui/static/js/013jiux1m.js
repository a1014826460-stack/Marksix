$.ajax({
    url: httpApi + `/api/kaijiang/getXysxma?web=${web}&type=${type}&num=9/8`,
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
                let xiao = d.xiao.split(',');
                let xiaoV = [];
                let ma = d.code.split(',');

                let c1 = [];
                let zj = false;
                let xIndex = 1;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) !== -1) {
                        xIndex = Math.min(i+1,xIndex);
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                let maIndex = 1;
                let c2 = [];
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) !== -1) {
                        maIndex = Math.min(i+1,maIndex);
                        zj = true;
                        c2.push(`<span style="background-color: #FFFF00">${ma[i]}</span>`);
                    }else {
                        c2.push(`${ma[i]}`)
                    }
                }
                // if (xIndex >= 99 && maIndex >= 99) {
                //     continue;
                // }

                htmlBoxList += ` 
     <tr height='31'> 
     <td width='99%' colspan='3' bgcolor='#FF0000'><font face='Arial Black' size='4' color='#000000'> 
${d.term}期A级大公开;准确率100%!</font></td> 
    </tr> 
    <tr height='31' style="${maIndex <= 1?'':'display: none;'}"> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
${d.term}期一码</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font size='4' color='#0000FF'>重拳出击-</font><font color='#FF00FF' style='font-size: 16pt' face='Arial'>${c2.slice(0,1).join(' ')}</font><font size='4' color='#0000FF'>-信心十足</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:${sx||'？'}${code||'00'}</font></td> 
    </tr> 
    <tr height='31' style="${maIndex <= 3?'':'display: none;'}"> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
${d.term}期三码</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'>
${c2.slice(0,3).join(' ')}</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:${sx||'？'}${code||'00'}</font></td> 
    </tr> 
    <tr height='31' style="${maIndex <= 5?'':'display: none;'}"> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
${d.term}期五码</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
${c2.slice(0,5).join(' ')}</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:${sx||'？'}${code||'00'}</font></td> 
    </tr> 
    <tr height='31' style="${maIndex <= 8?'':'display: none;'}"> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
${d.term}期八码</font></td> 
     <td width='59%' bgcolor='#FFFF99'> <font color='#FF0000' face='宋体' style='font-size: 12pt;'>
${c2.slice(0,8).join(' ')}</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:${sx||'？'}${code||'00'}</font></td> 
    </tr> 
    <tr height='31' style="${xIndex <= 1?'':'display: none;'}"> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
${d.term}期一肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体'>${c1.slice(0,1).join('')}</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:${sx||'？'}${code||'00'}</font></td> 
    </tr> 
    <tr height='31' style="${xIndex <= 2?'':'display: none;'}"> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
${d.term}期二肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
${c1.slice(0,2).join('')}</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:${sx||'？'}${code||'00'}</font></td> 
    </tr> 
    <tr height='31' style="${xIndex <= 3?'':'display: none;'}"> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
${d.term}期三肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
${c1.slice(0,3).join('')}</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:${sx||'？'}${code||'00'}</font></td> 
    </tr> 
    <tr style="${xIndex <= 4?'':'display: none;'}"> 
     <td width='23%' bgcolor='#CCFF66' style='height: 41px'><font face='宋体' style='font-size: 12pt;color:#000'> 
${d.term}期四肖</font></td> 
     <td width='59%' bgcolor='#FFFF99' style='height: 41px'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
${c1.slice(0,4).join('')}</font></td> 
     <td width='18%' bgcolor='#CCFF66' style='height: 41px'><font face='宋体' style='font-size: 12pt;color:#000'> 開:${sx||'？'}${code||'00'}</font></td> 
    </tr> 
    <tr height='31' style="${xIndex <= 6?'':'display: none;'}"> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
${d.term}期六肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
${c1.slice(0,6).join('')}</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:${sx||'？'}${code||'00'}</font></td> 
    </tr> 
    <tr height='31' style="${xIndex <= 7?'':'display: none;'}"> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
${d.term}期七肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
${c1.slice(0,7).join('')}</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:${sx||'？'}${code||'00'}</font></td> 
    </tr> 
    <tr height='31' style="${xIndex <= 9?'':'display: none;'}"> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
${d.term}期九肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
${c1.slice(0,9).join('')}</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:${sx||'？'}${code||'00'}</font></td> 
    </tr> 
 
    <tr> 
     <td colspan='3' height='27' width='99%' bgcolor='#000000'><font color='#FFFFFF' style=' font-size: 11pt; font-weight: 700;'>资料由www.twsaimahui.com长期免费公开!</font></td> 
    </tr> 
            `
            }
        }
        htmlBoxList = `
<style type='text/css'>
.stylejxym {
	background-color: #00FF00;
}
.style1 {
	background-color: #FFFF00;
}
</style>	
<table id='table400916271' style='border-collapse:collapse;text-align:center;font-weight:700;' bordercolor='#808000' cellspacing='0' cellpadding='0' width='100%' border='1'> 
   <tbody>

            ${htmlBoxList}
            </tbody>
            </table>
        `;
        $(".l54").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});

/*

<head>
<style type='text/css'>
.stylejxym {
	background-color: #00FF00;
}
.style1 {
	background-color: #FFFF00;
}
</style>
</head>

<table id='table400916271' style='border-collapse:collapse;text-align:center;font-weight:700;' bordercolor='#808000' cellspacing='0' cellpadding='0' width='100%' border='1'> 
   <tbody>










 <!----开始---->
    <tr height='31'> 
     <td width='99%' colspan='3' bgcolor='#FF0000'><font face='Arial Black' size='4' color='#000000'> 
		268期A级大公开;准确率100%!</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		268期一码</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font size='4' color='#0000FF'>重拳出击-</font><font color='#FF00FF' style='font-size: 16pt' face='Arial'>46</font><font size='4' color='#0000FF'>-信心十足</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:？00</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		268期三码</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'>
		46 34 47</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:？00</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		268期五码</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
		46 34 47 23 27</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:？00</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		268期八码</font></td> 
     <td width='59%' bgcolor='#FFFF99'> <font color='#FF0000' face='宋体' style='font-size: 12pt;'>
		46 34 47 23 27 03 02 38</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:？00</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		268期一肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体'>羊</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:？00</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		268期二肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
		羊马</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:？00</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		268期三肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
		羊马虎</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:？00</font></td> 
    </tr> 
    <tr> 
     <td width='23%' bgcolor='#CCFF66' style='height: 41px'><font face='宋体' style='font-size: 12pt;color:#000'> 
		268期四肖</font></td> 
     <td width='59%' bgcolor='#FFFF99' style='height: 41px'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
		羊马虎兔</font></td> 
     <td width='18%' bgcolor='#CCFF66' style='height: 41px'><font face='宋体' style='font-size: 12pt;color:#000'> 開:？00</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		268期六肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
		羊马虎兔鸡鼠</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:？00</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		268期七肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
		羊马虎兔鸡鼠龙</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:？00</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		268期九肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
		羊马虎兔鸡鼠龙猪狗</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:？00</font></td> 
    </tr> 
 
    <tr> 
     <td colspan='3' height='27' width='99%' bgcolor='#000000'><font color='#FFFFFF' style=' font-size: 11pt; font-weight: 700;'>资料由www.www.twsaimahui.com长期免费公开!</font></td>
    </tr> 
<!----结束---->    
   
   
   


 <!----开始---->
    <tr height='31'> 
     <td width='99%' colspan='3' bgcolor='#FF0000'><font face='Arial Black' size='4' color='#000000'> 
		267期A级大公开;准确率100%!</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		267期六肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
		猴兔鸡狗鼠<span style='background-color: #FFFF00'>蛇</span></font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:蛇12</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		267期七肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
		猴兔鸡狗鼠<span style='background-color: #FFFF00'>蛇</span>马</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:蛇12</font></td> 
    </tr> 
    <tr height='31'> 
     <td width='23%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 
		267期九肖</font></td> 
     <td width='59%' bgcolor='#FFFF99'><font color='#FF0000' face='宋体' style='font-size: 12pt;'> 
		猴兔鸡狗鼠<span style='background-color: #FFFF00'>蛇</span>马羊猪</font></td> 
     <td width='18%' bgcolor='#CCFF66'><font face='宋体' style='font-size: 12pt;color:#000'> 開:蛇12</font></td> 
    </tr> 
 
    <tr> 
     <td colspan='3' height='27' width='99%' bgcolor='#000000'><font color='#FFFFFF' style=' font-size: 11pt; font-weight: 700;'>资料由www.www.twsaimahui.com长期免费公开!</font></td>
    </tr> 
<!----结束---->    
   
 
 
 
 
 

 

   </tbody> 
  </table>*/
