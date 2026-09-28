$.ajax({
    url: httpApi + `/api/kaijiang/getXingte?web=${web}&type=${type}&num=3`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let yinx = '';
        let yangx = '';
        // ── 特码**号码五行**（唯一权威口径）───────────────────────────────
        // 与 backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS（= public.fixed_data
        // sign='五行'）逐项一致：01-49 全覆盖、互不重叠。
        //
        // 「三行中特」(mode 53) 的判定与高亮**只能**看特码号码的五行。历史落库正文里
        // 每个五行标签后的号码清单是按**生肖五行**（fixed_data sign='五行肖'）拼出来的，
        // 两者对同一号码会给出不同的五行，例如 24 → 号码五行「木」而生肖（羊）五行「土」、
        // 37 马 → 号码五行「木」而生肖五行「火」、45 狗 → 号码五行「木」而生肖五行「土」。
        // 旧实现用 `xiaoV[i].indexOf(code)`（正文清单）同时决定黄底与「准/错」，
        // 于是「生肖五行 ∈ 三行、号码五行 ∉ 三行」的期会被判成「准」并把黄底点在错行上。
        var ELEMENT_NUMBER_GROUPS = {
            金: [3, 4, 11, 12, 25, 26, 33, 34, 41, 42],
            木: [7, 8, 15, 16, 23, 24, 37, 38, 45, 46],
            水: [13, 14, 21, 22, 29, 30, 43, 44],
            火: [1, 2, 9, 10, 17, 18, 31, 32, 39, 40, 47, 48],
            土: [5, 6, 19, 20, 27, 28, 35, 36, 49]
        };
        var ELEMENT_ORDER = ['金', '木', '水', '火', '土'];
        /** 正文标签归一化：去掉引号/括号/空白与后缀「行」。 */
        function normalizeElementLabel(value) {
            return String(value == null ? '' : value).replace(/[[\]"'　\s]/g, '').replace(/行$/, '');
        }
        /** 特码号码 → 号码五行；号码缺失/非法返回空串（**绝不**回退到生肖五行）。 */
        function specialElementOfCode(value) {
            var parsed = parseInt(String(value == null ? '' : value).replace(/[^0-9]/g, ''), 10);
            if (!(parsed >= 1 && parsed <= 49)) return '';
            for (var g = 0; g < ELEMENT_ORDER.length; g++) {
                var group = ELEMENT_NUMBER_GROUPS[ELEMENT_ORDER[g]];
                for (var k = 0; k < group.length; k++) {
                    if (group[k] === parsed) return ELEMENT_ORDER[g];
                }
            }
            return '';
        }
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
                let content = safeParseJSON(d.content, []);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                // 命中行 = 特码号码五行所在的那一行（与判定同源），
                // 不再拿正文里的号码清单定位黄底。
                let hitElement = specialElementOfCode(code);
                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (hitElement && normalizeElementLabel(xiao[i]) === hitElement) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' style='height: 40px'><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#008000' style='font-size: 14pt' face='方正粗黑宋简体'>三行中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.join('')}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${ (sx?( zj?'准':'错'):'??')}</font> </font></b></td>
</tr>
 
            `
            }
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'>www.twsaimahui.com</font><font color='#FFFFFF'>三行中特</font></font></font></b></td>


            ${htmlBoxList}
            </table>
        `;
        $(".l56").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});

/*

<!DOCTYPE HTML>
<html>
<head>
    <meta http-equiv='Content-Type' content='text/html;charset=utf-8' />
    <meta name='viewport' content='width=device-width,minimum-scale=1.0,maximum-scale=1.0,user-scalable=no' />
    <meta name='applicable-device' content='mobile' />
    <meta name='apple-mobile-web-app-capable' content='yes' />
    <meta name='apple-mobile-web-app-status-bar-style' content='black' />
    <meta content='telephone=no' name='format-detection' />
    
    <meta name='mobile-agent' content='format=xhtml;url=/'>
    <meta name='mobile-agent' content='format=html5;url=/'>
    <link rel='alternate' media='only screen and(max-width: 640px)' href='/'>

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
.style1sxx {
	background-color: #FFFF00;
}
-->
</style>
</head>
<body>
  

 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'>www.twsaimahui.com</font><font color='#FFFFFF'>三行中特</font></font></font></b></td>




















				
				<tr>
			<td align='center' style='height: 40px'><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#008000' style='font-size: 14pt' face='方正粗黑宋简体'>三行中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>火土木</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>准</font> </font></b></td>
		</tr>
							

 
 
  
  
 

	</table>

</body>
*/
