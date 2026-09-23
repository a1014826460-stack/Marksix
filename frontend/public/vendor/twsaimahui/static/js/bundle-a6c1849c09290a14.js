/* twsaimahui 模块脚本合并包（顺序与原文档一致）
 *   static/js/061jy2x.js
 *   static/js/033zuoyou.js
 *   static/js/012liuxiao.js
 *   static/js/044yinyang.js
 *   static/js/027six8m.js
 *   static/js/003ds4w.js
 *   static/js/071ds.js
 *   static/js/073sixiao.js
 *   static/js/006heshuds.js
 *   static/js/043tiandi.js
 *   static/js/049rccx.js
 *   static/js/040jiaye.js
 *   static/js/042ycwx.js
 *   static/js/039heibai.js
 *   static/js/014jiuxiao.js
 *   static/js/031wuxiao.js
 *   static/js/060ds4x.js
 *   static/js/011jiepaoma.js
 *   static/js/030lflx.js
 *   static/js/068chengyupw.js
 *   static/js/023sanqibizhong.js
 *   static/js/075tiandi.js
 *   static/js/038ma10.js
 *   static/js/050siji.js
 *   static/js/004danshuang.js
 *   static/js/036ma12.js
 *   static/js/026siw8m.js
 *   static/js/035ma16.js
 *   static/js/065yiziptx.js
 *   static/js/047liuxiao.js
 *   static/js/046wenwu.js
 *   static/js/002daxiao.js
 *   static/js/045youwu.js
 *   static/js/067sanzipw.js
 *   static/js/062linbei6x.js
 *   static/js/053wfsb.js
 *   static/js/057s1x.js
 *   static/js/022pt1w.js
 *   static/js/072liangtou.js
 *   static/js/056s7m.js
 *   static/js/058s2x.js
 *   static/js/051fyld.js
 *   static/js/066chengyupx.js
 *   static/js/019liubuzhong.js
 *   static/js/013jiux1m.js
 *   static/js/024santou.js
 *   static/js/025sanhang.js
 *   static/js/001sb.js
 *   static/js/018sha1tou.js
 *   static/js/041meichou.js
 *   static/js/015sha3w.js
 *   static/js/016sha3x.js
 *   static/js/034feishou.js
 *   static/js/074ptyx.js
 *   static/js/037dandaxiao.js
 *   static/js/048hllx.js
 *   static/js/052qqsh.js
 */
// 特邀家野两肖 (使用统一请求工具 + safeParseJSON)
window.apiClient.get('/api/kaijiang/getJyxiao2', { web: window.web, type: window.type, num: '2' })
    .done(function (response) {
        var htmlBoxList = '';
        var data = response.data;
        if (!data || !data.length) {
            renderEmpty('.l1');
            return;
        }
        for (var i = 0; i < data.length; i++) {
            var d = data[i];
            var codeSplit = (d.res_code || '').split(',');
            var sxSplit = (d.res_sx || '').split(',');
            var code = codeSplit[codeSplit.length - 1] || '';
            var sx = sxSplit[sxSplit.length - 1] || '';
            var xiao = [];
            var xiaoV = [];
            var ma = (d.xiao || '').split(',');
            var content = safeParseJSON(d.content, []);
            if (!content.length) continue;
            for (var j = 0; j < content.length; j++) {
                var c = content[j].split('|');
                xiao.push(c[0]);
                xiaoV[j] = c[1] || '';
            }
            var c1 = [];
            var zj = false;
            for (var k = 0; k < xiao.length; k++) {
                if (sx && xiaoV[k] && xiaoV[k].indexOf(sx) !== -1) {
                    zj = true;
                    c1.push('<span style="background-color: #FFFF00">' + xiao[k] + '</span>');
                } else {
                    c1.push(xiao[k]);
                }
            }
            var c2 = [];
            for (var m = 0; m < ma.length; m++) {
                if (sx && ma[m].indexOf(sx) !== -1) {
                    zj = true;
                    c2.push('<span style="background-color: #FFFF00">' + ma[m] + '</span>');
                } else {
                    c2.push(ma[m]);
                }
            }
            htmlBoxList += ' <tr><td align=\'center\' height=40 class=\'stylelxz\'><strong>' + d.term + '期</strong><span class=\'styleliao\'><strong>家畜野兽</strong></span>:【<span class=\'stylezi\'><strong>' + c1.join('') + '+' + c2.join('') + '</strong></span><strong>】 开:' + (sx || '？') + (code || '00') + (sx ? (zj ? '准' : '错') : '??') + '</strong></td></tr>';
        }
        if (!htmlBoxList) {
            renderEmpty('.l1');
            return;
        }
        $('.l1').html('<table border=\'1\' width=\'100%\' cellpadding=\'0\' cellspacing=\'0\' bgcolor=\'#FFFFFF\' bordercolor=\'#D4D4D4\' style=\'border-collapse: collapse\'><tr><td class=\'center f13 black l150\' height=\'29\' align=\'center\' bgcolor=\'#FF0000\'><b><font size=\'4\'><font color=\'#FFFF00\' face=\'微软雅黑\'>&nbsp;</font><font face=\'微软雅黑\'><font color=\'#FFFF00\'> </font><font color=\'#FFFFFF\'>家禽+野兽</font></font></font></b></td></tr><tr><td align=\'center\' height=40 class=\'stylelxz\'><span class=\'styleliao\'>特邀高手：【阳光下的真实】【家禽+野兽】</span></td></tr>' + htmlBoxList + '</table>');
    })
    .fail(function () {
        renderError('.l1', '家禽+野兽数据加载失败');
    });

;
﻿
$.ajax({
    url: httpApi + `/api/kaijiang/getZyx?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let zx = '';
        let yx = '';
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
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '左肖') {
                        zx = c[1].replaceAll(',','');
                    }else{
                        yx = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>左右生肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>左右生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>左肖</span>:<span class='stylezi'>${zx}</span><br><span class='styleliao'>  右肖</span>:<span class='stylezi'>${yx}</span>
</td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l2").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>左右生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>左肖</span>:<span class='stylezi'>鼠牛龙蛇猴鸡</span><br><span class='styleliao'>  右肖</span>:<span class='stylezi'>虎兔马羊狗猪</span>
</td>
</tr>		





<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>左右生肖</strong></span>:<span class='stylezi'><strong>左肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>左右生肖</strong></span>:<span class='stylezi'><strong>左肖</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>左右生肖</strong></span>:<span class='stylezi'><strong>右肖</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>左右生肖</strong></span>:<span class='stylezi'><strong>左肖</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	
 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>左右生肖</strong></span>:<span class='stylezi'><strong>左肖</strong></span><strong> 开:龙13准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>左右生肖</strong></span>:<span class='stylezi'><strong>左肖</strong></span><strong> 开:鸡44准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>左右生肖</strong></span>:<span class='stylezi'><strong>左肖</strong></span><strong> 开:龙01准
</strong>
</td>
</tr>	


 
 

 

 
  


</table>*/

;
// 精品六肖 (使用统一请求工具 + safeParseJSON)
window.apiClient.get('/api/kaijiang/getXiaoma2', { web: window.web, type: window.type, num: '6' })
    .done(function (response) {
        var htmlBoxList = '';
        var data = response.data;
        if (!data || !data.length) {
            renderEmpty('.l3');
            return;
        }

        for (var i = 0; i < data.length; i++) {
            var d = data[i];
            var codeSplit = (d.res_code || '').split(',');
            var sxSplit = (d.res_sx || '').split(',');
            var code = codeSplit[codeSplit.length - 1] || '';
            var sx = sxSplit[sxSplit.length - 1] || '';
            var content = safeParseJSON(d.content, []);
            if (!content.length) {
                continue;
            }

            var xiao = [];
            var ma = [];
            for (var j = 0; j < content.length; j++) {
                var c = String(content[j] || '').split('|');
                xiao.push(c[0] || '');
                xiao.push(c[1] || '');
                ma.push.apply(ma, String(c[1] || '').split(','));
            }

            var c1 = [];
            for (var k = 0; k < xiao.length; k += 2) {
                if (sx && xiao[k + 1] && xiao[k + 1].indexOf(sx) !== -1) {
                    c1.push('<span style="background-color: #FFFF00">' + xiao[k] + '</span>');
                } else {
                    c1.push(xiao[k]);
                }
            }

            var c2 = [];
            for (var m = 0; m < ma.length; m++) {
                if (code && ma[m].indexOf(code) !== -1) {
                    c2.push('<span style="background-color: #FFFF00">' + ma[m] + '</span>');
                } else {
                    c2.push(ma[m]);
                }
            }

            var ma12 = '<p style="font-size:13pt;margin-bottom:8px;text-align:left"><span style="text-indent:28px;color:#000;font-family:\\5fae\\8f6f\\96c5\\9ed1;font-size:12pt">\u7cbe\u900912\u7801\uff1a' + c2.join('.') + '</span></p>';
            var ma6 = '<p style="font-size:13pt;margin-bottom:8px;text-align:left"><span style="text-indent:28px;color:#000;font-family:\\5fae\\8f6f\\96c5\\9ed1;font-size:12pt">\u7cbe\u9009\u516d\u7801\uff1a' + c2.slice(0, 6).join('.') + '</span></p>';
            var ma1 = '<p style="font-size:13pt;margin-bottom:8px;text-align:left"><span style="text-indent:28px;color:#000;font-family:\\5fae\\8f6f\\96c5\\9ed1;font-size:12pt">\u5fc5\u4e2d\u4e00\u7801\uff1a' + c2.slice(0, 1).join('.') + '</span></p>';
            var x6 = '<p style="font-size:13pt;margin-bottom:8px;text-align:left"><span style="text-indent:28px;color:#000;font-family:\\5fae\\8f6f\\96c5\\9ed1;font-size:12pt">\u5fc5\u4e2d\u516d\u8096\uff1a' + c1.join('.') + '</span></p>';
            var x3 = '<p style="font-size:13pt;margin-bottom:8px;text-align:left"><span style="text-indent:28px;color:#000;font-family:\\5fae\\8f6f\\96c5\\9ed1;font-size:12pt">\u5fc5\u4e2d\u4e09\u8096\uff1a' + c1.slice(0, 3).join('.') + '</span></p>';
            var x1 = '<p style="font-size:13pt;margin-bottom:8px;text-align:left"><span style="text-indent:28px;color:#000;font-family:\\5fae\\8f6f\\96c5\\9ed1;font-size:12pt">\u5fc5\u4e2d\u4e00\u8096\uff1a' + c1.slice(0, 1).join('.') + '</span></p>';

            htmlBoxList += '<table border="1" width="100%" cellpadding="0" height="100" cellspacing="0" bordercolorlight="#FFFFFF" bordercolordark="#FFFFFF" bgcolor="#FFFFFF" style="border-collapse:collapse;border-spacing:0;color:#444;font-family:tahoma,\\5fae\\8f6f\\96c5\\9ed1,\\5b8b\\4f53,arial,georgia,verdana,helvetica,sans-serif;font-size:14px;font-style:normal;font-variant-ligatures:normal;font-weight:normal;letter-spacing:normal;line-height:21px;text-align:start;text-indent:0;text-transform:none;white-space:normal;widows:1;word-spacing:0;-webkit-text-stroke-width:0;background-color:#fff"><tbody><tr class="firstRowxx"><td height="35" style="background:#FF0000;margin:0;border-color:green;word-break:break-all;text-align:center;font-size:13pt;line-height:26px;color:#333;padding-left:2px;padding-right:2px;padding-top:3px;padding-bottom:3px"><span style="color:#FFF;font-family:\\5fae\\8f6f\\96c5\\9ed1;font-weight:700;line-height:normal;font-size:12pt">' + d.term + '\u671f\uff1a\u516d\u8096\u4e09\u7801</span></td></tr><tr><td style="margin:0;padding:3px 2px;border-color:#e5e5e5;word-break:break-all;text-align:center;line-height:26px">' + x6 + x3 + x1 + ma12 + ma6 + ma1 + '</td></tr></tbody></table>';
        }

        if (!htmlBoxList) {
            renderEmpty('.l3');
            return;
        }

        $('.l3').html('<style>div.sbxztt{border-radius:4px;box-shadow:0 1px 2px rgba(180,180,180,0.7);background-color:#fff;zoom:1;font:14px/1.5 tahoma,\\5fae\\8f6f\\96c5\\9ed1,\\5b8b\\4f53,arial,georgia,verdana,helvetica,sans-serif;color:#444}tr.firstRowxx{background-color:rgb(139,69,19)}</style><div class="sbxztt">' + htmlBoxList + '</div>');
        applyLotteryRegionTitlePrefix(document.querySelector('.l3'));
    })
    .fail(function () {
        renderError('.l3', '\u7cbe\u54c1\u516d\u8096\u6570\u636e\u52a0\u8f7d\u5931\u8d25');
    });

;
﻿
$.ajax({
    url: httpApi + `/api/kaijiang/getYysx?web=${web}&type=${type}&num=2`,
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
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '阴肖') {
                        yinx = c[1].replaceAll(',','');
                    }else{
                        yangx = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>阴阳生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>阴肖</span>:<span class='stylezi'>${yinx}</span><br><span class='styleliao'>  阳肖</span>:<span class='stylezi'>${yangx}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l4").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>阴阳生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>阴肖</span>:<span class='stylezi'>鼠龙蛇马狗猪</span><br><span class='styleliao'>  阳肖</span>:<span class='stylezi'>牛虎兔羊猴鸡</span>
</td>
</tr>			
















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>阳肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>阳肖</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>阳肖</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>阴肖</strong></span><strong> 开:猪30准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>阴肖</strong></span><strong> 开:龙13准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>阴阳生肖</strong></span>:<span class='stylezi'><strong>阳肖</strong></span><strong> 开:鸡44准
</strong>
</td>
</tr>	


 
 
 



</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getXiaoma2?web=${web}&type=${type}&num=4`,
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
                let maValue = [];
                let content = safeParseJSON(d.content, []);
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    maValue[i] = c[1];
                    ma.push(...c[1].split(','));
                }



                let c = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) !== -1) {
                        zj =true;
                        c.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c.push(`${xiao[i]}`)
                    }
                }


                let c1 = [];
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">${ma[i]}</span>`);
                    }else {
                        c1.push(`${ma[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【${c[0]}:${c1.slice(0,2).join('.')}】【${c[1]}:${c1.slice(2,4).join('.')}】<br>【${c[2]}:${c1.slice(4,6).join('.')}】【${c[3]}:${c1.slice(6).join('.')}】</font></b></td>
</tr>

            `
            }
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 			


	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>四肖八码</font></font></font></b></td>

		</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l5").html(htmlBoxList)
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
    
    
    <title>澳 |马会开奖结果|一肖中特免费公开资料|香港六合彩|六合彩开奖结果|历史开奖记录|最快开奖尽在澳王中王</title>
    <meta name='keywords' content='澳王中王,本港台开奖现场直播,香港马会开奖结果,香港马会资料,买马网站,香港挂牌正版彩图,管家婆彩图,白小姐玄机图,现场报码' />
    <meta name='description' content='澳王中王开奖结果 - 与本港电视台同步直播。第一时间更新开奖结果及开奖记录、王中王汇集网上最强势的彩票网址大全,提供买马资料,开奖记录查询等大型综合买马新闻文字报道网站' />
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
.style1 {
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>四肖八码</font></font></font></b></td>

		</tr>













<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【牛:16.40】【猪:18.42】<br>【猴:21.45】【马:11.35】</font></b></td>
</tr>




<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>267期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>蛇</span>:24.48】【鸡:20.32】<br>【狗:31.43】【兔:14.38】</font></b></td>
</tr>





<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>266期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【鼠:05.41】【羊:22.46】<br>【蛇:24.36】【<span style='background-color: #FFFF00'>虎</span>:<span style='background-color: #FFFF00'>27</span>.39】</font></b></td>
</tr>




		
<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>265期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【兔:26.02】【马:23.35】<br>【猴:09.45】【<span style='background-color: #FFFF00'>牛</span>:28.40】</font></b></td>
</tr>




<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>264期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>猪</span>:18.42】【马:23.47】<br>【蛇:24.48】【猴:21.33】</font></b></td>
</tr>




		
<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>263期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四肖八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【鼠:17.41】【<span style='background-color: #FFFF00'>龙</span>:<span style='background-color: #FFFF00'>13</span>.37】<br>【兔:26.38】【虎:15.39】</font></b></td>
</tr>



 
 

 
 
 
 

 

						</table>


</body>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getDsWei?web=${web}&type=${type}&num=4`,
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

                let w1 = d.dan.split(',');
                let w2 = d.shuang.split(',');

                let c1 = [];
                let zj = false;
                for (let i = 0; i < w1.length; i++) {
                    if (code && w1[i] === code.split('')[1]) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${w1[i]}</span>`);
                    }else {
                        c1.push(`${w1[i]}`)
                    }
                }

                let c2 = [];
                for (let i = 0; i < w2.length; i++) {
                    if (code && w2[i] === code.split('')[1]) {
                        zj = true;
                        c2.push(`<span style="background-color: #FFFF00">${w2[i]}</span>`);
                    }else {
                        c2.push(`${w2[i]}`)
                    }
                }

                htmlBoxList += ` 
<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>${d.term}期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【${c1.join('')}】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【${c2.join('')}】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>${ (sx?( zj?'赢':'输'):'??')}</font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>


	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双四尾</font></font></font></b></td>

		</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l6").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双四尾</font></font></font></b></td>

		</tr>









				<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>268期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1359】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【0268】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




		
							<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>267期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1579】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>2</span>468】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




					<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>266期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【13<span style='background-color: #FFFF00'>7</span>9】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【0468】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>虎27</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




							<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>265期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1579】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【24<span style='background-color: #FFFF00'>6</span>8】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>牛16</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>264期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1379】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>0</span>248】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>猪30</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	



 

									<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>262期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1359】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【2<span style='background-color: #FFFF00'>4</span>68】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>鸡44</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	



							<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>261期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>1</span>579】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【2468】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>龙01</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




				<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>260期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1359】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>0</span>268】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>牛40</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




	   <tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>259期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【137<span style='background-color: #FFFF00'>9</span>】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【0468】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>鼠29</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




			<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>258期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1579】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【<span style='background-color: #FFFF00'>0</span>268】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>牛40</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




		
							<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>257期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【1579】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【246<span style='background-color: #FFFF00'>8</span>】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>鸡08</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	




	   <tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>256期:</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>单尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【137<span style='background-color: #FFFF00'>9</span>】</font><font color='#996633' style='font-size: 12pt' face='方正粗黑宋简体'>双尾</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【0468】开</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>虎39</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>	



 
 
 
  
 


	</table>
*/


;
﻿
$.ajax({
    url: httpApi + `/api/kaijiang/danshuang?web=${web}&type=${type}&num=2`,
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
                let content = safeParseJSON(d.content, []);
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let c = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (code && xiaoV[i].indexOf(code) !== -1) {
                        zj = true;
                        c.push(`<span style="background-color: #FFFF00">${xiao[i]}数</span>`)
                    }else{
                        c.push(`${xiao[i]}数`)
                    }
                }


                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>单双中特</strong></span>:【<span class='stylezi'><strong>${c.join('')}</strong></span><strong>】 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
</strong>
</td>
</tr>\t
 
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双中特</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【明年今日】【单双中特】</span>
</td>
</tr>\t

            ${htmlBoxList}
            </table>
        `;
        $(".l7").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双中特</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【明年今日】【单双中特】</span>
</td>
</tr>		

















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>单双中特</strong></span>:【<span class='stylezi'><strong>单数</strong></span><strong>】 开:？00准
</strong>
</td>
</tr>	

 
 
 

 

</table>*/

;
﻿
$.ajax({
    url: httpApi + `/api/kaijiang/getZhongte?web=${web}&type=${type}&num=4`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

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

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>四肖中特</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
</strong>
</td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='40' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>张小丫四肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<strong>【<span class='stylezi'><strong>特邀高手：张小丫『四肖』</strong></span>】
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l8").html(htmlBoxList)
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
<td class='center f13 black l150' height='40' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>张小丫四肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<strong>【<span class='stylezi'><strong>特邀高手：张小丫『四肖』</strong></span>】
</td>
</tr>	








<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>四肖中特</strong></span>:<span class='stylezi'><strong>鼠虎龙猪</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	



 
 
 

 
 

 
 
 
  


 



</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getHeds?web=${web}&type=${type}&num=2`,
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
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '阴肖') {
                        yinx = c[1].replaceAll(',','');
                    }else{
                        yangx = c[1].replaceAll(',','');
                    }
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
 
\t\t\t\t\t\t\t\t\t<tr>
\t\t\t<td align='center' height=40><b>
\t\t\t<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>澳合数</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.join('')}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${ (sx?( zj?'中':'不中'):'??')}</font></b></td>
\t\t</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 			


	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>合数中特</font></font></font></b></td>

		</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l9").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>合数中特</font></font></font></b></td>

		</tr>

























									<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>澳合数</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>合单</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font></b></td>
		</tr>







									<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>267期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>澳合数</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>合单</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font></b></td>
		</tr>


 

									<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>265期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>澳合数</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>合单</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>牛16</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font></b></td>
		</tr>




 


 
 
 
 
 
 
 

						</table>
*/



;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getTdsx1?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let tx = '';
        let dx = '';
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
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '天肖') {
                        tx = c[1].replaceAll(',','');
                    }else{
                        dx = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }
                // 预测失败也显示当期资料，不再跳过

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>天地生肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':' '):'??')}
</strong>
</td>
</tr>\t
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>天地生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>天肖</span>:<span class='stylezi'>${tx}</span><br><span class='styleliao'>  地肖</span>:<span class='stylezi'>${dx}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l22").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>天地生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>天肖</span>:<span class='stylezi'>兔猴马猪牛龙</span><br><span class='styleliao'>  地肖</span>:<span class='stylezi'>蛇羊鸡狗鼠虎</span>
</td>
</tr>		








<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>天地生肖</strong></span>:<span class='stylezi'><strong>地肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>天地生肖</strong></span>:<span class='stylezi'><strong>地肖</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>天地生肖</strong></span>:<span class='stylezi'><strong>地肖</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>天地生肖</strong></span>:<span class='stylezi'><strong>天肖</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	

 
  



</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getRccx?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let rou = '';
        let cai = '';
        let cao = '';
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
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0].split('')[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let b = false;
                let c1 = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        b = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                    if (xiao[i] === '肉') {
                        rou = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '菜') {
                        cai = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '草') {
                        cao = xiaoV[i].replaceAll(',','');
                    }
                }
                let zj = b;
                htmlBoxList += ` 
 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>肉草菜肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}肖</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
</strong>
</td>
</tr>\t
 
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>肉草菜肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>肉肖</span>:<span class='stylezi'>${rou}</span><span class='styleliao'>  菜肖</span>:<span class='stylezi'>${cai}</span><br>草肖</span>:<span class='stylezi'>${cao}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l11").html(htmlBoxList)
        applyLotteryRegionTitlePrefix(document.querySelector('.l11'))
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>肉草菜肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>肉肖</span>:<span class='stylezi'>虎蛇龙狗</span><span class='styleliao'>  菜肖</span>:<span class='stylezi'>猪鼠鸡猴</span><br>草肖</span>:<span class='stylezi'>牛羊马兔</span>
</td>
</tr>		
















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>肉草菜肖</strong></span>:<span class='stylezi'><strong>草肉肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>肉草菜肖</strong></span>:<span class='stylezi'><strong>草<span style='background-color: #FFFF00'>肉</span>肖</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>肉草菜肖</strong></span>:<span class='stylezi'><strong>草<span style='background-color: #FFFF00'>肉</span>肖</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>肉草菜肖</strong></span>:<span class='stylezi'><strong>草<span style='background-color: #FFFF00'>肉</span>肖</strong></span><strong> 开:龙13准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>肉草菜肖</strong></span>:<span class='stylezi'><strong>肉<span style='background-color: #FFFF00'>菜</span>肖</strong></span><strong> 开:鸡44准
</strong>
</td>
</tr>	
 
  
 

</table>*/

;
﻿
$.ajax({
    url: httpApi + `/api/kaijiang/getJyzt?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let jc = '';
        let ys = '';
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
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '家禽') {
                        jc = c[1].replaceAll(',','');
                    }else{
                        ys = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }
                // if (sx && !zj) continue;
                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>家畜野兽</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
</strong>
</td>
</tr>\t
            `
            }
        }
        htmlBoxList = `
</style>
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>家畜野兽</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>家畜</span>:<span class='stylezi'>牛马羊鸡狗猪</span><br><span class='styleliao'>  野兽</span>:<span class='stylezi'>鼠虎兔龙蛇猴</span>
</td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l12").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>家畜野兽</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>家畜</span>:<span class='stylezi'>牛马羊鸡狗猪</span><br><span class='styleliao'>  野兽</span>:<span class='stylezi'>鼠虎兔龙蛇猴</span>
</td>
</tr>			







<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>家畜野兽</strong></span>:<span class='stylezi'><strong>家畜</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	
 

<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>家畜野兽</strong></span>:<span class='stylezi'><strong>野兽</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>家畜野兽</strong></span>:<span class='stylezi'><strong>家畜</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	

 
 
 

 
 
 
 
 
 


</table>*/

;
﻿
$.ajax({
    url: httpApi + `/api/kaijiang/getZhongte?web=${web}&type=${type}&num=5`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

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

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>五肖中特</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
</strong>
</td>
</tr>\t
 
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>隐刺五肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<strong>【<span class='stylezi'><strong>特邀高手：隐刺 『五肖』</strong></span>】
</td>
</tr>	
<tr>
<td align='center' height=40 class='stylelxz'>
<span class='stylezi'><strong><a target='_blank' href='/tuizhan.html'>点击进入王中王全网高手会员区</a></strong></span>
</td>
</tr>\t

            ${htmlBoxList}
            </table>
        `;
        $(".l13").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>隐刺五肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<strong>【<span class='stylezi'><strong>特邀高手：隐刺 『五肖』</strong></span>】
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='stylezi'><strong><a target='_blank' href='/tuizhan.html'>点击进入王中王全网高手会员区</a></strong></span>
</td>
</tr>	
















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>五肖中特</strong></span>:<span class='stylezi'><strong>狗猴牛羊鼠</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


 
 

 




</table>*/
;
﻿
$.ajax({
    url: httpApi + `/api/kaijiang/getHbx?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let hei = '';
        let bai = '';
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
                    if (c[0] === '白') {
                        bai = c[1].replaceAll(',','');
                    }else{
                        hei = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}肖</span>`);
                    }else {
                        c1.push(`${xiao[i]}肖`)
                    }
                }
                // if (!zj) continue;
                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>黑白生肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>黑白生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>白边生肖</span>:<span class='stylezi'>鼠牛虎鸡狗猪</span><br><span class='styleliao'>  黑中生肖</span>:<span class='stylezi'>兔龙蛇马羊猴</span>
</td>
</tr>			

            ${htmlBoxList}
            </table>
        `;
        $(".l14").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>黑白生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>白边生肖</span>:<span class='stylezi'>鼠牛虎鸡狗猪</span><br><span class='styleliao'>  黑中生肖</span>:<span class='stylezi'>兔龙蛇马羊猴</span>
</td>
</tr>			




<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>黑白生肖</strong></span>:<span class='stylezi'><strong>白肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	
 

<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>黑白生肖</strong></span>:<span class='stylezi'><strong>白肖</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	
 

 
 


</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getZhongte?web=${web}&type=${type}&num=9`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

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

                htmlBoxList += ` 
 <td align='center' height=40><b>
<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>${d.term}期:</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>九肖</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【${c1.join('')}】 开</font><font color='#0000FF' style='font-size: 12pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>${ (sx?( zj?'赢':'输'):'??')}</font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>九肖中特</font></font></font></b></td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l15").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>九肖中特</font></font></font></b></td>
</tr>

















		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>268期:</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>九肖</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【狗虎猴兔马蛇羊鼠龙】 开</font><font color='#0000FF' style='font-size: 12pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>



		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>267期:</font><font color='#FF0000' style='font-size: 12pt' face='方正粗黑宋简体'>九肖</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>【猪鼠鸡<span style='background-color: #FFFF00'>蛇</span>龙狗猴兔羊】 开</font><font color='#0000FF' style='font-size: 12pt' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 12pt' face='方正粗黑宋简体'>赢</font></b></td>
		</tr>



 

 
 
 
 
  
 
 
			</table>
*/


;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getZhongte?web=${web}&type=${type}&num=3`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

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

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>三肖中特</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>三肖中特</font></font></font></b></td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l16").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>三肖中特</font></font></font></b></td>
</tr>



















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>三肖中特</strong></span>:<span class='stylezi'><strong>羊马狗</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	

 

 
 
 
 
 
 


</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getDsnx?web=${web}&type=${type}&num=4`,
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
                let x1 = d.xiao_1.split(',');
                let x2 = d.xiao_2.split(',');
                xiao.push(...x1,...x2);

                let c = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (xiao[i].indexOf(sx) !== -1 && sx) {
                        zj =true;
                        c.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期【</strong><span class='styleliao'><strong>单：${c.slice(0,4).join('')}</strong></span>:<span class='stylezi'><strong>双：${c.slice(4).join('')}</strong></span><strong>】开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
</strong>
</td>
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双四肖</font></font></font></b></td>
</tr>
<tr>
<td align='center' height=40 class='stylelxz'>
<strong>【<span class='stylezi'><strong>特邀高手：周星驰 星爷『单双四肖』</strong></span>】
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'>
<span class='stylezi'><strong><a target='_blank' href='/tuizhan.html'>点击进入王中王全网高手会员区</a></strong></span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l17").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双四肖</font></font></font></b></td>
</tr>
<tr>
<td align='center' height=40 class='stylelxz'>
<strong>【<span class='stylezi'><strong>特邀高手：周星驰 星爷『单双四肖』</strong></span>】
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'>
<span class='stylezi'><strong><a target='_blank' href='/tuizhan.html'>点击进入王中王全网高手会员区</a></strong></span>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期【</strong><span class='styleliao'><strong>单：狗猴马虎</strong></span>:<span class='stylezi'><strong>双：羊蛇鸡兔</strong></span><strong>】开:？00准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期【</strong><span class='styleliao'><strong>单：龙虎鼠猴</strong></span>:<span class='stylezi'><strong>双：<span style='background-color: #FFFF00'>蛇</span>兔羊猪</strong></span><strong>】开:蛇12准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期【</strong><span class='styleliao'><strong>单：马<span style='background-color: #FFFF00'>虎</span>狗猴</strong></span>:<span class='stylezi'><strong>双：羊猪牛鸡</strong></span><strong>】开:虎27准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期【</strong><span class='styleliao'><strong>单：马虎鼠猴</strong></span>:<span class='stylezi'><strong>双：鸡<span style='background-color: #FFFF00'>猪</span>羊兔</strong></span><strong>】开:猪30准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期【</strong><span class='styleliao'><strong>单：虎猴马<span style='background-color: #FFFF00'>龙</span></strong></span>:<span class='stylezi'><strong>双：羊蛇牛鸡</strong></span><strong>】开:龙13准
</strong>
</td>
</tr>	
 
 
 

</table>*/

;
﻿$.ajax({
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

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getZhongte?web=${web}&type=${type}&num=4`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

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

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>四肖中特</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>精选四肖</font></font></font></b></td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l19").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>精选四肖</font></font></font></b></td>
</tr>


















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>四肖中特</strong></span>:<span class='stylezi'><strong>鼠蛇马猪</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>四肖中特</strong></span>:<span class='stylezi'><strong>虎<span style='background-color: #FFFF00'>蛇</span>马猪</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>四肖中特</strong></span>:<span class='stylezi'><strong>猴<span style='background-color: #FFFF00'>虎</span>鸡牛</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>四肖中特</strong></span>:<span class='stylezi'><strong>猪<span style='background-color: #FFFF00'>龙</span>狗蛇</strong></span><strong> 开:龙13准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>四肖中特</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>鸡</span>猪鼠虎</strong></span><strong> 开:鸡44准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>四肖中特</strong></span>:<span class='stylezi'><strong>兔<span style='background-color: #FFFF00'>龙</span>鼠牛</strong></span><strong> 开:龙01准
</strong>
</td>
</tr>	


 
  

 

</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getCyptwei?web=${web}&type=${type}&num=2`,
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
                let title = d.title || '';
                let num;
                let zj = false;
                if (title.indexOf('一') !== -1) {
                    num = 1;
                }else if (title.indexOf('二') !== -1) {
                    num = 2;
                }else if (title.indexOf('三') !== -1) {
                    num = 3;
                }else if (title.indexOf('四') !== -1) {
                    num = 4;
                }else if (title.indexOf('五') !== -1) {
                    num = 5;
                }else if (title.indexOf('六') !== -1) {
                    num = 6;
                }else if (title.indexOf('七') !== -1) {
                    num = 7;
                }else if (title.indexOf('八') !== -1) {
                    num = 8;
                }else if (title.indexOf('九') !== -1) {
                    num = 9;
                }else if (title.indexOf('零') !== -1) {
                    num = 0;
                }else {
                    continue
                }
                num +=''
                let index=99;
                for (let k in codeSplit) {
                    if (!codeSplit[k]) continue;
                    let w = codeSplit[k].split('')[1];
                    if (w === num) {
                        zj = true;
                        index = k;
                        break
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>成语平特尾</strong></span>:【<span class='stylezi'><strong>${title}</strong></span><strong>】 开:${codeSplit[index]||code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>成语平特尾</font></font></font></b></td>
</tr>
	

            ${htmlBoxList}
            </table>
        `;
        $(".l20").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>成语平特尾</font></font></font></b></td>
</tr>












<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>成语平特尾</strong></span>:【<span class='stylezi'><strong>五福临门</strong></span><strong>】 开:00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>成语平特尾</strong></span>:【<span class='stylezi'><strong>四海鼎沸</strong></span><strong>】 开:34准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>成语平特尾</strong></span>:【<span class='stylezi'><strong>二缶锺惑</strong></span><strong>】 开:02准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>成语平特尾</strong></span>:【<span class='stylezi'><strong>三足鼎立</strong></span><strong>】 开:33准
</strong>
</td>
</tr>	
 



</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getSanqiXiao4new?web=${web}&type=${type}&num=7`,
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
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let terms = [];
                let names = d.name.split('-');
                let mid = Math.min(parseInt(names[0]),parseInt(names[1]));
                mid = (++mid).toString();
                if (mid.length < names[0].length) {
                    mid = '0'+mid;
                }
                terms[0] = names[0];
                terms[1] = mid;
                terms[2] = names[1];

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

                htmlBoxList += ` 
 <table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
<b><font face='微软雅黑'>${terms[2]}期</font></b></td>
<td align='center' bgcolor='#FFFFFF' width='55%' rowspan='3'>
<font face='微软雅黑' size='5' color='#FF0000'><strong>
龙马羊狗</span></strong></span></font></td>
<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
<font face='微软雅黑'>开:猫00</font></td>
</tr>
<tr>
<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
${terms[1]}期</font></b></td>
<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
<font face='微软雅黑'>开:蛇12</font></td>
</tr>
<tr>
<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
${terms[0]}期</font></b></td>
<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
<font face='微软雅黑'>开:虎27</font></td>
</tr>
</table>
 
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' height='29' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

<tr>

<td  height='29' align='center' bgcolor='#FF0000'>

<font color='#FFFFFF' size='4'>
<span style='font-family: 微软雅黑; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 700; letter-spacing: normal; orphans: 2; text-align: -webkit-center; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; display: inline !important; float: none'>
 【四肖三期内必出】 </span></font></td>
</tr>
</table>
            ${htmlBoxList}
        `;
        $(".l21").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});






/*

<table border='1' width='100%' cellpadding='0' height='29' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

	<tr>

		<td  height='29' align='center' bgcolor='#FF0000'>

		<font color='#FFFFFF' size='4'>
		<span style='font-family: 微软雅黑; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 700; letter-spacing: normal; orphans: 2; text-align: -webkit-center; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; display: inline !important; float: none'>
		 【四肖三期内必出】 </span></font></td>
		</tr>
		</table>


	<!----开始---->    
	<table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
		<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b><font face='微软雅黑'>268期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='55%' rowspan='3'>
		<font face='微软雅黑' size='5' color='#FF0000'><strong>
		龙马羊狗</span></strong></span></font></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:猫00</font></td>
		</tr>
	<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		267期</font></b></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:蛇12</font></td>
		</tr>
	<tr>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		266期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<font face='微软雅黑'>开:虎27</font></td>
		</tr>
		</table>
		
<!----结束----> 			






	
	<!----开始---->    
	<table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
		<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b><font face='微软雅黑'>265期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='55%' rowspan='3'>
		<font face='微软雅黑' size='5' color='#FF0000'><strong>
		<span style='background-color: #FFFF00'>鸡</span>虎蛇羊</span></strong></span></font></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:牛16</font></td>
		</tr>
	<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		264期</font></b></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:猪30</font></td>
		</tr>
	<tr>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		263期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<font face='微软雅黑'>开:龙13</font></td>
		</tr>
		</table>
		
<!----结束----> 			







	<!----开始---->    
	<table border='1' width='100%' cellpadding='0' height='83' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
		<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b><font face='微软雅黑'>262期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='55%' rowspan='3'>
		<font face='微软雅黑' size='5' color='#FF0000'><strong>
		<span style='background-color: #FFFF00'>龙</span>鸡羊<span style='background-color: #FFFF00'>牛</span></span></strong></span></font></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:鸡44</font></td>
		</tr>
	<tr>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		261期</font></b></td>
		<td  height='11' align='center' bgcolor='#FFFFFF' width='22%'>
		<font face='微软雅黑'>开:龙01</font></td>
		</tr>
	<tr>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<b style='padding: 0px; margin: 0px; word-wrap: break-word;'>
		<font face='微软雅黑' style='word-wrap: break-word; margin: 0px; padding: 0px'>
		260期</font></b></td>
		<td align='center' bgcolor='#FFFFFF' width='22%' style='height: 26px'>
		<font face='微软雅黑'>开:牛40</font></td>
		</tr>
		</table>
		



 

 
 

 

 

 
*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getTdsx1?web=${web}&type=${type}&num=2`,
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
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }
                // if (!zj) continue;

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>天地生肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
</strong>
</td>
</tr>\t
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='40' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>天地生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<strong>【<span class='stylezi'><strong>特邀高手：佛跳墙『天地生肖』</strong></span>】
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l10").html(htmlBoxList)
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
<td class='center f13 black l150' height='40' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>天地生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<strong>【<span class='stylezi'><strong>特邀高手：佛跳墙『天地生肖』</strong></span>】
</td>
</tr>	









<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>天地生肖</strong></span>:<span class='stylezi'><strong>地肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>天地生肖</strong></span>:<span class='stylezi'><strong>地肖</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>天地生肖</strong></span>:<span class='stylezi'><strong>天肖</strong></span><strong> 开:猪30准
</strong>
</td>
</tr>	

 
 




</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getCode?web=${web}&type=${type}&num=10`,
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
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>10码中特</strong></span>:<span class='stylezi'><strong>${c1.join('.')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>10码中特</font></font></font></b></td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l23").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>10码中特</font></font></font></b></td>
</tr>










<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>10码中特</strong></span>:<span class='stylezi'><strong>08.09.24.25.27.38.39.40.41.42</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	 
 

<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>10码中特</strong></span>:<span class='stylezi'><strong>04.05.09.10.11.<span style='background-color: #FFFF00'>12</span>.13.14.17.18</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	 

 
 
 



</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getSjsx?web=${web}&type=${type}&num=3`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let chun = '';
        let xia = '';
        let qiu = '';
        let dong = '';
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
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0].split('')[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                    if (xiao[i] === '春') {
                        chun = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '夏') {
                        xia = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '秋') {
                        qiu = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '冬') {
                        dong = xiaoV[i].replaceAll(',','');
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>四季生肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>四季生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>春肖</span>:<span class='stylezi'>${chun}</span>     <span class='styleliao'>夏肖</span>:<span class='stylezi'>${xia}</span><br>
<span class='styleliao'>秋肖</span>:<span class='stylezi'>${qiu}</span>     <span class='styleliao'>冬肖</span>:<span class='stylezi'>${dong}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l24").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>四季生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>春肖</span>:<span class='stylezi'>龙虎兔</span>     <span class='styleliao'>夏肖</span>:<span class='stylezi'>马羊蛇</span><br>
<span class='styleliao'>秋肖</span>:<span class='stylezi'>猴鸡狗</span>     <span class='styleliao'>冬肖</span>:<span class='stylezi'>猪鼠牛</span>
</td>
</tr>		



















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>四季生肖</strong></span>:<span class='stylezi'><strong>春冬夏肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>四季生肖</strong></span>:<span class='stylezi'><strong>春冬<span style='background-color: #FFFF00'>夏</span>肖</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	
 

<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>四季生肖</strong></span>:<span class='stylezi'><strong>春夏<span style='background-color: #FFFF00'>冬</span>肖</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>四季生肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>冬</span>秋春肖</strong></span><strong> 开:猪30准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>四季生肖</strong></span>:<span class='stylezi'><strong>冬秋<span style='background-color: #FFFF00'>春</span>肖</strong></span><strong> 开:龙13准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>四季生肖</strong></span>:<span class='stylezi'><strong>春夏<span style='background-color: #FFFF00'>秋</span>肖</strong></span><strong> 开:鸡44准
</strong>
</td>
</tr>	
 
  
 
 

</table>*/

;
﻿
$.ajax({
    url: httpApi + `/api/kaijiang/getDsxiao?web=${web}&type=${type}&num=2`,
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
                let ma = [];
                let content = [d.content];
                let ds = [];
                let dsv = [];
                for (let i in content) {
                    let c = content[i].split('|');
                    ds.push(c[0].split('')[0])
                    dsv[i] = c[1];
                }

                let c = `${ds[0]}`;
                if (sx && dsv[0].indexOf(sx) !== -1) {
                    c = `<span style="background-color: #FFFF00">${ds[0]}</span>`
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

                htmlBoxList += ` 
 <tr>
<td align='center' height=40><b>
<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c}+${c1.join('')}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}${zj?'准':'错'}</font> </font></b></td>
</tr>
 
            `
            }
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>


	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双中特</font></font></font></b></td>

		</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l25").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>单双中特</font></font></font></b></td>

		</tr>


























		
							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>268期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>单+兔猪</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>？00准</font> </font></b></td>
		</tr>



							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>267期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>双</span>+狗虎</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>蛇12准</font> </font></b></td>
		</tr>
		
		



 
		
						<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>265期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>单+<span style='background-color: #FFFF00'>牛</span>羊</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>牛16准</font> </font></b></td>
		</tr>
		

 

		
							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>263期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>双+<span style='background-color: #FFFF00'>龙</span>马</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>龙13准</font> </font></b></td>
		</tr>
		



		

							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>262期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>单+<span style='background-color: #FFFF00'>鸡</span>兔</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>鸡44准</font> </font></b></td>
		</tr>
		



		
						<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>261期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>双+马<span style='background-color: #FFFF00'>龙</span></font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>龙01准</font> </font></b></td>
		</tr>
		



		
						<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>260期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>双</span>+鼠猴</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>牛40准</font> </font></b></td>
		</tr>



		
							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>259期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>单</span>+牛猪</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>鼠29准</font> </font></b></td>
		</tr>





							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>258期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>双</span>+马鼠</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>牛40准</font> </font></b></td>
		</tr>
		
		



							<tr>
			<td align='center' height=40><b>
			<font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>257期本期买</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>双</span>+狗鼠</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中特开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>鸡08准</font> </font></b></td>
		</tr>
		


  
 
  
  

 
 


	</table>
*/


;
﻿$.ajax({
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
                let nums = getNumsByColor((d.content || '').split('')[0]) || '';
                let c1 = [];
                let zj = false;
                if (code && nums.indexOf(code) !== -1) {
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

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getWeima2?web=${web}&type=${type}&num=4`,
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
                let content = safeParseJSON(d.content, []);
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0].split('')[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (code && code.length >= 2 && xiao[i] === code.split('')[1]) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}尾</span>`);
                    }else {
                        c1.push(`${xiao[i]}尾`)
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
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四尾八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【${c1[0]}-${c2.slice(0,2).join('.')}】【${c1[1]}-${c2.slice(2,4).join('.')}】<br>【${c1[2]}-${c2.slice(4,6).join('.')}】【${c1[3]}-${c2.slice(6,8).join('.')}】</font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
	<tr>
		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>四尾八码</font></font></font></b></td>
		</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l28").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>四尾八码</font></font></font></b></td>
		</tr>

























<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>四尾八码</font></b><br>
<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>【4尾-34.44】【3尾-03.43】<br>【1尾-01.31】【6尾-26.36】</font></b></td>
</tr>




 
 
 
 
 

						</table>*/

;
﻿$.ajax({
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

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getPingte?web=${web}&type=${type}&num=1`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

                let c1 = [];
                let b = false;
                let index = getZjIndex(xiao[0],sxSplit);
                if (index !== undefined) {
                    b = true;
                    c1.push(`<span style="background-color: #FFFF00">${xiao[0]}</span>`);
                }else {
                    c1.push(`${xiao[0]}`)
                }
                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>平特一肖</strong></span>:【<span class='stylezi'><strong>${c1[0]}${c1[0]}${c1[0]}</strong></span><strong>】 开:${(index !== undefined ? codeSplit[index] : '00')}${ (sx?( b?'准':'错'):'??')}
</strong>
</td>
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>平特一肖</font></font></font></b></td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l30").html(htmlBoxList)
        applyLotteryRegionTitlePrefix(document.querySelector('.l30'))
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>平特一肖</font></font></font></b></td>
</tr>














<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>平特一肖</strong></span>:【<span class='stylezi'><strong>鼠鼠鼠</strong></span><strong>】 开:00准
</strong>
</td>
</tr>	


 
  


</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getZhongte?web=${web}&type=${type}&num=6`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

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

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>六肖中特</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
</strong>
</td>
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>六肖中特</font></font></font></b></td>
</tr>
<tr>
<td align='center' height=40 class='stylelxz'>
<strong>【<span class='stylezi'><strong>特邀高手：风小子 『六肖』</strong></span>】
</td>
</tr>		

            ${htmlBoxList}
            </table>
        `;
        $(".l31").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>六肖中特</font></font></font></b></td>
</tr>
<tr>
<td align='center' height=40 class='stylelxz'>
<strong>【<span class='stylezi'><strong>特邀高手：风小子 『六肖』</strong></span>】
</td>
</tr>	




















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>六肖中特</strong></span>:<span class='stylezi'><strong>牛马虎鸡龙猴</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>六肖中特</strong></span>:<span class='stylezi'><strong>羊龙<span style='background-color: #FFFF00'>蛇</span>猪猴鸡</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>六肖中特</strong></span>:<span class='stylezi'><strong>鼠狗龙<span style='background-color: #FFFF00'>牛</span>兔鸡</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>六肖中特</strong></span>:<span class='stylezi'><strong>鼠龙兔鸡马<span style='background-color: #FFFF00'>猪</span></strong></span><strong> 开:猪30准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>六肖中特</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>龙</span>猪马鸡蛇虎</strong></span><strong> 开:龙13准
</strong>
</td>
</tr>	

 
  
 


</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getWwx?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let wenx = '';
        let wux = '';
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
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '文肖') {
                        wenx = c[1].replaceAll(',','');
                    }else{
                        wux = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>文武生肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>文武生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>文肖</span>:<span class='stylezi'>${wenx}</span><br><span class='styleliao'>  武肖</span>:<span class='stylezi'>${wux}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l32").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>文武生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>文肖</span>:<span class='stylezi'>鼠免龙羊鸡猪</span><br><span class='styleliao'>  武肖</span>:<span class='stylezi'>牛马虎蛇猴狗</span>
</td>
</tr>			








<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>文武生肖</strong></span>:<span class='stylezi'><strong>文肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	
 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>文武生肖</strong></span>:<span class='stylezi'><strong>武肖</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	


 
 
 
 


</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getDxzt?web=${web}&type=${type}&num=2`,
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
                    xiao.push(c[0])
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
<td align='center' style='height: 40px'><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#6600FF' style='font-size: 14pt' face='方正粗黑宋简体'>大小中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#800000' style='font-size: 14pt' face='方正粗黑宋简体'>${c1[0]}${c1[0]}${c1[0]}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${ (sx?( zj?'中':'不中'):'??')}</font> </font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse;'>
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'>www.twsaimahui.com</font><font color='#FFFFFF'>大小中特</font></font></font></b></td>


            ${htmlBoxList}
            </table>
        `;
        $(".l33").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});
/*


<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse;'>
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'>www.twsaimahui.com</font><font color='#FFFFFF'>大小中特</font></font></font></b></td>














				
		<tr>
			<td align='center' style='height: 40px'><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#6600FF' style='font-size: 14pt' face='方正粗黑宋简体'>大小中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#800000' style='font-size: 14pt' face='方正粗黑宋简体'>大大大</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>		




				
		<tr>
			<td align='center' style='height: 40px'><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>267期</font><font color='#6600FF' style='font-size: 14pt' face='方正粗黑宋简体'>大小中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#800000' style='font-size: 14pt' face='方正粗黑宋简体'>小小小</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>		



 
 
 
 
 

 

  

	</table>


*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getYwx?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let yx = '';
        let wx = '';
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
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '无肖') {
                        wx = c[1].replaceAll(',','');
                    }else{
                        yx = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>有无生肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>有无生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>有肖</span>:<span class='stylezi'>${yx}</span><br><span class='styleliao'>  无肖</span>:<span class='stylezi'>${wx}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l34").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>有无生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>有肖</span>:<span class='stylezi'>龙蛇猴鸡狗猪</span><br><span class='styleliao'>  无肖</span>:<span class='stylezi'>鼠牛虎兔马羊</span>
</td>
</tr>		


























<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>有无生肖</strong></span>:<span class='stylezi'><strong>无肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>有无生肖</strong></span>:<span class='stylezi'><strong>无肖</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	
 

<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>有无生肖</strong></span>:<span class='stylezi'><strong>无肖</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	
 
 



</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getPingte?web=${web}&type=${type}&num=3`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    let index = getZjIndex(xiao[i],sxSplit);
                    if (index !== undefined) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }


                htmlBoxList += ` 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>${c1.join('')}</strong></span><strong>】 
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>平特三肖</font></font></font></b></td>
</tr>


<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【神仙买码】【平特三肖】</span>
</td>
</tr>		

            ${htmlBoxList}
            </table>
        `;
        $(".l35").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>平特三肖</font></font></font></b></td>
</tr>


<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【神仙买码】【平特三肖】</span>
</td>
</tr>		











<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>猴蛇虎</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>猴</span>狗虎</strong></span><strong>】 
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>牛</span>羊<span style='background-color: #FFFF00'>龙</span></strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>鼠马</span>鸡</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>猪<span style='background-color: #FFFF00'>马</span>牛</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>狗猪<span style='background-color: #FFFF00'>鸡</span></strong></span><strong>】 
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>虎<span style='background-color: #FFFF00'>狗</span>兔</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
260期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>猴<span style='background-color: #FFFF00'>蛇</span>鸡</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
259期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>鼠</span>龙羊</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
258期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>虎</span>猴蛇</strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
257期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>马</span>兔<span style='background-color: #FFFF00'>羊</span></strong></span><strong>】 
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
256期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>猴</span>狗<span style='background-color: #FFFF00'>猪</span></strong></span><strong>】 
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
255期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>鸡<span style='background-color: #FFFF00'>蛇猴</span></strong></span><strong>】 
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
254期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong><span style='background-color: #FFFF00'>牛龙</span>狗</strong></span><strong>】 
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
253期</strong><span class='styleliao'><strong>平特三肖</strong></span>:【<span class='stylezi'><strong>鸡<span style='background-color: #FFFF00'>马</span>猪</strong></span><strong>】 
</strong>
</td>
</tr>	
  
  
 
 
 

</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getZhongte?web=${web}&type=${type}&num=6`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

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

                htmlBoxList += ` 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>林北六肖</strong></span>:【<span class='stylezi'><strong>${c1.join('')}</strong></span><strong>】 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>林北六肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【哇林北】【林北六肖】</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l36").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>林北六肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>特邀高手：【哇林北】【林北六肖】</span>
</td>
</tr>		


<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>林北六肖</strong></span>:【<span class='stylezi'><strong>马羊猴鸡狗猪</strong></span><strong>】 开:？00准
</strong>
</td>
</tr>	
 
 
 

</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getBmzy?web=${web}&type=${type}&num=3`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let bi = '';
        let mo = '';
        let zhi = '';
        let yan  = '';
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
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0].split('')[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '笔肖') {
                        bi = c[1].replaceAll(',','');
                    }else if (c[0] === '墨肖') {
                        mo = c[1].replaceAll(',','');
                    }else if (c[0] === '纸肖') {
                        zhi = c[1].replaceAll(',','');
                    }else if (c[0] === '砚肖') {
                        yan = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>笔墨纸砚肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>笔墨纸砚</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>笔肖</span>:<span class='stylezi'>${bi}</span>     <span class='styleliao'>墨肖</span>:<span class='stylezi'>${mo}</span><br>
<span class='styleliao'>纸肖</span>:<span class='stylezi'>${zhi}</span>     <span class='styleliao'>砚肖</span>:<span class='stylezi'>${yan}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l37").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>笔墨纸砚</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>笔肖</span>:<span class='stylezi'>鸡兔蛇</span>     <span class='styleliao'>墨肖</span>:<span class='stylezi'>鼠牛狗</span><br>
<span class='styleliao'>纸肖</span>:<span class='stylezi'>马龙虎</span>     <span class='styleliao'>砚肖</span>:<span class='stylezi'>羊猪猴</span>
</td>
</tr>		
















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>笔墨纸砚肖</strong></span>:<span class='stylezi'><strong>笔墨砚</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>笔墨纸砚肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>笔</span>墨砚</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>笔墨纸砚肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>纸</span>墨砚</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>笔墨纸砚肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>墨</span>纸笔</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>笔墨纸砚肖</strong></span>:<span class='stylezi'><strong>纸墨<span style='background-color: #FFFF00'>砚</span></strong></span><strong> 开:猪30准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>笔墨纸砚肖</strong></span>:<span class='stylezi'><strong>墨<span style='background-color: #FFFF00'>纸</span>砚</strong></span><strong> 开:龙13准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>笔墨纸砚肖</strong></span>:<span class='stylezi'><strong>墨<span style='background-color: #FFFF00'>纸</span>砚</strong></span><strong> 开:龙01准
</strong>
</td>
</tr>	

  
  

 


</table>*/

;
﻿
$.ajax({
    url: httpApi + `/api/kaijiang/getShaXiao?web=${web}&type=${type}&num=1`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) === -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }
                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>${c1.join('')}</strong></span><strong>】开:${sx||'？'}${code||'00'}${zj? (sx?'准':'--'):'错'}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀一肖</font></font></font></b></td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l40").html(htmlBoxList)
        applyLotteryRegionTitlePrefix(document.querySelector('.l40'))
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀一肖</font></font></font></b></td>
</tr>










<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>兔</strong></span><strong>】开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>鼠</strong></span><strong>】开:蛇12准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>龙</strong></span><strong>】开:虎27准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>猪</strong></span><strong>】开:牛16准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>牛</strong></span><strong>】开:猪30准
</strong>
</td>
</tr>	
 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>猴</strong></span><strong>】开:鸡44准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>狗</strong></span><strong>】开:龙01准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
260期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>蛇</strong></span><strong>】开:牛40准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
259期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>鸡</strong></span><strong>】开:鼠29准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
258期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>兔</strong></span><strong>】开:牛40准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
257期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>龙</strong></span><strong>】开:鸡08准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
256期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>羊</strong></span><strong>】开:虎39准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
255期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>兔</strong></span><strong>】开:猪30准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
254期</strong><span class='styleliao'><strong>绝杀一肖</strong></span>:【<span class='stylezi'><strong>鼠</strong></span><strong>】开:虎27准
</strong>
</td>
</tr>	

 
 
 

</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getPtWei?web=${web}&type=${type}&num=2`,
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
                let index;
                for (let i = 0; i < xiao.length; i++) {
                    index = getZjIndex(xiao[i],codeSplit);
                    if (index !== undefined) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#FF00FF' style='font-size: 14pt' face='方正粗黑宋简体'>平特一尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.slice(0,1).join('')}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】</font><font color='#FF00FF' style='font-size: 14pt' face='方正粗黑宋简体'>二连尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.join('')}尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】${ (sx?( zj?'中':'不中'):'??')}</font> </font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>


				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>平特一尾</font></font></font></b></td>

		</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l42").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>平特一尾</font></font></font></b></td>

		</tr>



















							<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#FF00FF' style='font-size: 14pt' face='方正粗黑宋简体'>平特一尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>2</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】</font><font color='#FF00FF' style='font-size: 14pt' face='方正粗黑宋简体'>二连尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>25尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中</font> </font></b></td>
		</tr>


 

		
					<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>266期</font><font color='#FF00FF' style='font-size: 14pt' face='方正粗黑宋简体'>平特一尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>3</span></font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】</font><font color='#FF00FF' style='font-size: 14pt' face='方正粗黑宋简体'>二连尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'><span style='background-color: #FFFF00'>39</span>尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】中</font> </font></b></td>
		</tr>



 
 
  
 
  
  
 
  
  
  
						</table>


*/

;
﻿$.ajax({
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

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getShama?web=${web}&type=${type}&num=7`,
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
                    if (code && ma[i].indexOf(code) === -1) {
                        zj = true;
                        c1.push(`<span>${ma[i]}</span>`);
                    }else {
                        c1.push(`${ma[i]}`)
                    }
                }

                htmlBoxList += ` 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>${c1.join('.')}</span><strong>】
开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀七码</font></font></font></b></td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l45").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀七码</font></font></font></b></td>
</tr>











<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>03.20.24.25.26.27.28</span><strong>】
开:？00准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>05.09.24.28.36.38.42</span><strong>】
开:蛇12准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>08.09.12.26.29.30.37</span><strong>】
开:虎27准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>05.06.07.19.30.31.35</span><strong>】
开:牛16准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>16.19.20.21.22.23.24</span><strong>】
开:猪30准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>26.39.40.41.42.46.47</span><strong>】
开:龙13准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>26.27.28.37.39.40.43</span><strong>】
开:鸡44准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>绝杀七码</strong></span>:【<span class='stylezi'>13.24.25.28.29.39.42</span><strong>】
开:龙01准
</strong>
</td>
</tr>	

  
 
 
 


</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getShaXiao?web=${web}&type=${type}&num=2`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) === -1) {
                        zj = true;
                        c1.push(`<span>${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>${c1.join('')}</strong></span><strong>】开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀二肖</font></font></font></b></td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l47").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀二肖</font></font></font></b></td>
</tr>




















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>牛羊</strong></span><strong>】开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>猪龙</strong></span><strong>】开:蛇12准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>猴鸡</strong></span><strong>】开:虎27准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>狗虎</strong></span><strong>】开:猪30准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>马猪</strong></span><strong>】开:龙13准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>羊虎</strong></span><strong>】开:鸡44准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>猴虎</strong></span><strong>】开:龙01准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
260期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>猪马</strong></span><strong>】开:牛40准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
259期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>狗兔</strong></span><strong>】开:鼠29准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
258期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>鸡鼠</strong></span><strong>】开:牛40准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
257期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>蛇马</strong></span><strong>】开:鸡08准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
256期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>马龙</strong></span><strong>】开:虎39准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
255期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>虎鸡</strong></span><strong>】开:猪30准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
254期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>龙鸡</strong></span><strong>】开:虎27准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
253期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>羊虎</strong></span><strong>】开:马47准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
252期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>虎牛</strong></span><strong>】开:蛇36准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
251期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>牛羊</strong></span><strong>】开:兔14准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
250期</strong><span class='styleliao'><strong>绝杀二肖</strong></span>:【<span class='stylezi'><strong>猪龙</strong></span><strong>】开:蛇24准
</strong>
</td>
</tr>	

 
 
 
  
  

 

 


</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getFyld?web=${web}&type=${type}&num=3`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let feng = '';
        let yu = '';
        let lei = '';
        let dian = '';
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
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '雷') {
                        lei = c[1].replaceAll(',','');
                    }else if(c[0] === '风'){
                        feng = c[1].replaceAll(',','');
                    }else if(c[0] === '雨'){
                        yu = c[1].replaceAll(',','');
                    }else if(c[0] === '电'){
                        dian = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>风雨雷电肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}肖</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>风雨雷电</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>风肖</span>:<span class='stylezi'>${feng}</span>     <span class='styleliao'>雨肖</span>:<span class='stylezi'>${yu}</span><br>
<span class='styleliao'>雷肖</span>:<span class='stylezi'>${lei}</span>     <span class='styleliao'>电肖</span>:<span class='stylezi'>${dian}</span>
</td>
</tr>

            ${htmlBoxList}
            </table>
        `;
        $(".l48").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>风雨雷电</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>风肖</span>:<span class='stylezi'>龙虎兔</span>     <span class='styleliao'>雨肖</span>:<span class='stylezi'>猪鼠牛</span><br>
<span class='styleliao'>雷肖</span>:<span class='stylezi'>马羊蛇</span>     <span class='styleliao'>电肖</span>:<span class='stylezi'>猴鸡狗</span>
</td>
</tr>			






<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>风雨雷电肖</strong></span>:<span class='stylezi'><strong>风雷电肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>风雨雷电肖</strong></span>:<span class='stylezi'><strong>风<span style='background-color: #FFFF00'>雷</span>电肖</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>风雨雷电肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>风</span>雷雨肖</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>风雨雷电肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>雨</span>风电肖</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>风雨雷电肖</strong></span>:<span class='stylezi'><strong>雷<span style='background-color: #FFFF00'>雨</span>风肖</strong></span><strong> 开:猪30准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>风雨雷电肖</strong></span>:<span class='stylezi'><strong>雨雷<span style='background-color: #FFFF00'>风</span>肖</strong></span><strong> 开:龙13准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>风雨雷电肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>电</span>雨雷肖</strong></span><strong> 开:鸡44准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>风雨雷电肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>风</span>雨雷肖</strong></span><strong> 开:龙01准
</strong>
</td>
</tr>	

  
  


</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getCypt?web=${web}&type=${type}&num=2`,
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

                let b = false;
                let c1 = [];
                let index = getZjIndex(d.title,sxSplit);
                if (sx && index !== undefined) {
                    b = true;
                    c1.push(`<span style="background-color: #FFFF00">${d.title}</span>`)
                }else {
                    c1.push(`<span>${d.title}</span>`)
                }
                htmlBoxList += ` 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>成语平特肖</strong></span>:【<span class='stylezi'><strong>${c1[0]}</strong></span><strong>】 开:${(index !== undefined ? sxSplit[index] : '？')}${(index !== undefined ? codeSplit[index] : '00')}${ (sx?( b?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>成语平特肖</font></font></font></b></td>
</tr>
	

            ${htmlBoxList}
            </table>
        `;
        $(".l51").html(htmlBoxList)
        applyLotteryRegionTitlePrefix(document.querySelector('.l51'))
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>成语平特肖</font></font></font></b></td>
</tr>




















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>成语平特肖</strong></span>:【<span class='stylezi'><strong>对牛弹琴</strong></span><strong>】 开:00准
</strong>
</td>
</tr>	

 

  
  
 
 



</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/rd70i73lziizczak/0gmqnw/1`,
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
                if (!d.u6_code) continue;
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = [];
                let xiaoV = [];
                let ma = d.u6_code.split(',');

                let c1 = [];
                let zj = false;
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) === -1) {
                        zj = true;
                        c1.push(`<span>${ma[i]}</span>`);
                    }else {
                        c1.push(`${ma[i]}`)
                    }
                }
                // if (!zj) continue;

                htmlBoxList += ` 
<td align='center' style='height: 40px'><b>
<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>${d.term}期:</font><font color='#FF00FF' style='font-size: 13pt' face='方正粗黑宋简体'>六不中</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>${c1.join('-')}</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】</font></font></b></td>
</tr>
            `
            }
        }
        if (!htmlBoxList) {
            $(".l52").html('');
            return;
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>
				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>六不中</font></font></font></b></td>
		</tr>
            ${htmlBoxList}
            </table>
        `;
        $(".l52").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>六不中</font></font></font></b></td>

		</tr>





			<td align='center' style='height: 40px'><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>268期:</font><font color='#FF00FF' style='font-size: 13pt' face='方正粗黑宋简体'>六不中</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>25-43-27-32-47-06</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】</font></font></b></td>
		</tr>		

 


		<td align='center' style='height: 40px'><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>266期:</font><font color='#FF00FF' style='font-size: 13pt' face='方正粗黑宋简体'>六不中</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>44-45-46-16-17-18</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】</font></font></b></td>
		</tr>		



 
	<td align='center' style='height: 40px'><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>264期:</font><font color='#FF00FF' style='font-size: 13pt' face='方正粗黑宋简体'>六不中</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>35-47-20-38-40-42</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】</font></font></b></td>
		</tr>		



	<td align='center' style='height: 40px'><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>263期:</font><font color='#FF00FF' style='font-size: 13pt' face='方正粗黑宋简体'>六不中</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>32-07-19-16-28-15</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】</font></font></b></td>
		</tr>		
		



 

 
 

 
 


		
																																			
	</table>
*/


;
﻿$.ajax({
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

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getTou?web=${web}&type=${type}&num=3`,
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
                    xiao.push(c[0])
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
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>三头中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>『${c1.join('.')}』开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${ (sx?( zj?'准':'错'):'??')}</font> </font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>



	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>三头中特</font></font></font></b></td>


            ${htmlBoxList}
            </table>
        `;
        $(".l55").html(htmlBoxList)
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>三头中特</font></font></font></b></td>

















							<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>三头中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>『0头.2头.4头』开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>准</font> </font></b></td>
		</tr>


				<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>267期</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>三头中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>『<span style='background-color: #FFFF00'>1</span>头.2头.4头』开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>准</font> </font></b></td>
		</tr>
			



			<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>266期</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>三头中特</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>『0头.<span style='background-color: #FFFF00'>2</span>头.4头』开</font><font color='#FF0000' style='font-size: 14pt; background-color:#FFFF00' face='方正粗黑宋简体'>虎27</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>准</font> </font></b></td>
		</tr>


 
 
  

 
	</table>


*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getXingte?web=${web}&type=${type}&num=3`,
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
                    xiao.push(c[0])
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

;
window.apiClient.get('/api/kaijiang/sbzt', { web: window.web, type: window.type, num: '2' })
    .done(function (response) {
        var data = response.data || [];
        if (!data.length) {
            renderEmpty('.l57');
            return;
        }

        var htmlBoxList = '';
        for (var i = 0; i < data.length; i++) {
            var d = data[i];
            var codeSplit = (d.res_code || '').split(',');
            var sxSplit = (d.res_sx || '').split(',');
            var code = codeSplit[codeSplit.length - 1] || '';
            var sx = sxSplit[sxSplit.length - 1] || '';
            var colors = (d.content || '').split(',').filter(Boolean);
            var c1 = [];
            var zj = false;

            for (var j = 0; j < colors.length; j++) {
                var color = colors[j].charAt(0);
                var nums = getNumsByColor(color) || '';
                if (code && nums.indexOf(code) !== -1) {
                    zj = true;
                    c1.push('<span style="background-color: #FFFF00">' + color + '</span>');
                } else {
                    c1.push(color);
                }
            }

            htmlBoxList += "<tr><td align='center' height='40'><b>"
                + "<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>" + d.term + "期</font>"
                + "<font color='#800080' style='font-size: 14pt' face='方正粗黑宋简体'>必中波色</font>"
                + "<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>:</font>"
                + "<font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>" + c1.join('') + "波</font>"
                + "<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'> 开" + (sx || '？') + (code || '00') + (sx ? (zj ? '准' : '错') : '??') + "</font>"
                + "</b></td></tr>";
        }

        $('.l57').html(
            "<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>"
            + "<tr><td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>"
            + "<b><font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>必中双波</font></font></font></b>"
            + "</td></tr>"
            + htmlBoxList
            + "</table>"
        );
    })
    .fail(function () {
        renderError('.l57', '必中双波数据加载失败');
    });

;
﻿$.ajax({
 url: httpApi + `/api/kaijiang/getShatou?web=${web}&type=${type}&num=1`,
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
     xiao.push(c[0])
     xiaoV[i] = c[1];
     ma.push(...c[1].split(','));
    }

    let c1 = [];
    let zj = true;
    for (let i = 0; i < xiao.length; i++) {
     if (code && xiaoV[i].indexOf(code) === -1) {
      c1.push(`<span>${xiao[i]}</span>`);
     }else {
      zj = false;
      c1.push(`${xiao[i]}`)
     }
    }
    htmlBoxList += ` 
<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.join('')}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${ (sx?( zj?'中':'不中'):'??')}</font> </font></b></td>
</tr>
            `
   }
  }
  htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀①头</font></font></font></b></td>

		</tr>	

            ${htmlBoxList}
            </table>
        `;
  $(".l58").html(htmlBoxList)
  applyLotteryRegionTitlePrefix(document.querySelector('.l58'))
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀①头</font></font></font></b></td>

		</tr>
















				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>4头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>




				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>267期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>3头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>266期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>0头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>虎27</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>




 							
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>265期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>2头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>牛16</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>




	 
				
			
	<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>264期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>3头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>猪30</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>	




							
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>263期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>2头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>龙13</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>






		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>262期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>2头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>鸡44</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>




							
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>261期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>2头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>龙01</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>


 

				
							<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>259期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>0头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>鼠29</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>


 

				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>257期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>3头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>鸡08</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



				
							<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>256期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>0头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>虎39</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



							
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>255期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>2头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>猪30</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>254期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>0头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>虎27</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>




	<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>253期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>2头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>马47</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



				
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>252期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>0头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>蛇36</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>251期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>4头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>兔14</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>



				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>250期※</font><font color='#808000' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀①头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>※【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>3头</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>蛇24</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font> </font></b></td>
		</tr>
 
 
  
 
  

		
	</table>
*/


;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getJmxc?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let attach = response.attach || [];
        let jm = attach[1] && attach[1].code ? attach[1].code : '';
        let xc = attach[0] && attach[0].code ? attach[0].code : '';
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
                if (!content.length) {
                    continue;
                }
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>吉美凶丑</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>吉美凶丑</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>吉美生肖</span>:<span class='stylezi'>${jm.replaceAll(",",'').replaceAll(",",'')}</span><br><span class='styleliao'>  凶丑生肖</span>:<span class='stylezi'>${xc.replaceAll(",",'')}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l59").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>吉美凶丑</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>吉美生肖</span>:<span class='stylezi'>兔龙蛇马羊鸡</span><br><span class='styleliao'>  凶丑生肖</span>:<span class='stylezi'>鼠牛虎猴狗猪</span>
</td>
</tr>			














<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>吉美凶丑</strong></span>:<span class='stylezi'><strong>吉美</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>吉美凶丑</strong></span>:<span class='stylezi'><strong>吉美</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>吉美凶丑</strong></span>:<span class='stylezi'><strong>凶丑</strong></span><strong> 开:猪30准
</strong>
</td>
</tr>	
 
 
  


 
 
  
 


</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getShaWei?web=${web}&type=${type}&num=3`,
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
                let zj = true;
                for (let i = 0; i < xiao.length; i++) {
                    if (code && xiaoV[i].indexOf(code) === -1) {
                        c1.push(`<span>${xiao[i]}</span>`);
                    }else {
                        zj = false;
                        c1.push(`${xiao[i]}`)
                    }
                }
                htmlBoxList += ` 

<td align='center' height=40><b>
<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.join('')}尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font> </font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 
	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀三尾</font></font></font></b></td>

		</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l61").html(htmlBoxList)
        applyLotteryRegionTitlePrefix(document.querySelector('.l61'))
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀三尾</font></font></font></b></td>

		</tr>












		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>358尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>？00</font> </font></b></td>
		</tr>	
		



		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>267期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>146尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>蛇12</font> </font></b></td>
		</tr>	



 

				
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>264期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>269尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>猪30</font> </font></b></td>
		</tr>	
		




		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>263期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>269尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>龙13</font> </font></b></td>
		</tr>	
		



		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>262期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>159尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>鸡44</font> </font></b></td>
		</tr>	
		




		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>261期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>269尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>龙01</font> </font></b></td>
		</tr>	
		


		
		<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>260期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>358尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>牛40</font> </font></b></td>
		</tr>	
		




		
				<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>259期</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>绝杀三尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>158尾</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开:</font><font color='#0000FF' style='font-size: 14pt' face='方正粗黑宋简体'>鼠29</font> </font></b></td>
		</tr>	
		



  
 
 
 
	</table>

*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getShaXiao?web=${web}&type=${type}&num=3`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

                let c1 = [];
                let zj = true;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) === -1) {
                        c1.push(`<span>${xiao[i]}</span>`);
                    }else {
                        zj = false;
                        c1.push(`${xiao[i]}`)
                    }
                }
                htmlBoxList += ` 
<tr>
<td align='center' height=40><b>
<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>${d.term}期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（${c1.join('')}）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>${ (sx?( zj?'赢':'输'):'??')}</font> </font></b></td>
</tr>
            `
            }
        }
        htmlBoxList = `
 <table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀三肖</font></font></font></b></td>

		</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l62").html(htmlBoxList)
        applyLotteryRegionTitlePrefix(document.querySelector('.l62'))
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
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>绝杀三肖</font></font></font></b></td>

		</tr>










		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>268期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（鼠猪牛）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		
		




		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>267期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（龙马猴）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		
		



		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>266期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（鸡龙狗）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>虎27</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		
		



		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>265期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（龙马猴）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>牛16</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		
		


					<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>264期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（马猴牛）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>猪30</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		



		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>263期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（狗鸡蛇）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>龙13</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		
		


 

		<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>261期:</font><font color='#800080' style='font-size: 13pt' face='方正粗黑宋简体'>绝杀三肖</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'> 【</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>（狗鸡蛇）</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 13pt' face='方正粗黑宋简体'>龙01</font><font color='#000000' style='font-size: 13pt' face='方正粗黑宋简体'>赢</font> </font></b></td>
		</tr>		
		

 
 
 
 
 

 
  

	</table>
*/



;
﻿
$.ajax({
    url: httpApi + `/api/kaijiang/getFsx?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let feix = '';
        let soux = '';
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
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '瘦肖') {
                        soux = c[1].replaceAll(',','');
                    }else{
                        feix = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>肥瘦生肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>肥瘦生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>肥肖</span>:<span class='stylezi'>${feix}</span><br><span class='styleliao'>  瘦肖</span>:<span class='stylezi'>${soux}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l63").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>肥瘦生肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>肥肖</span>:<span class='stylezi'>龙虎猴鼠牛猪</span><br><span class='styleliao'>  瘦肖</span>:<span class='stylezi'>狗兔蛇马羊鸡</span>
</td>
</tr>			














<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>肥瘦生肖</strong></span>:<span class='stylezi'><strong>瘦肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>肥瘦生肖</strong></span>:<span class='stylezi'><strong>瘦肖</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>肥瘦生肖</strong></span>:<span class='stylezi'><strong>肥肖</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	

 
  
 
 

 



</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getPingte?web=${web}&type=${type}&num=1`,
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
                let xiao = d.content.split(',');
                let xiaoV = [];
                let ma = [];

                let c1 = [];
                let zj = false;
                let index;
                for (let i = 0; i < xiao.length; i++) {
                    index = getZjIndex(xiao[i],sxSplit);
                    if (index !== undefined) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }
                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>平特一肖</strong></span>:【<span class='stylezi'><strong>${c1[0]}${c1[0]}${c1[0]}</strong></span><strong>】 开:${codeSplit[index]||'00'}${ (sx?( zj?'准':'错'):'??')}
</strong>
</td>
</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>
<tr>
<td class='center f13 black l150' height='40' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>平特一肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<strong>【<span class='stylezi'><strong>特邀高手：折烟花『平特一肖』</strong></span>】
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l64").html(htmlBoxList)
        applyLotteryRegionTitlePrefix(document.querySelector('.l64'))
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
<td class='center f13 black l150' height='40' align='center' bgcolor='#FF0000'>
<b>
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>平特一肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<strong>【<span class='stylezi'><strong>特邀高手：折烟花『平特一肖』</strong></span>】
</td>
</tr>	





















<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>平特一肖</strong></span>:【<span class='stylezi'><strong>马马马</strong></span><strong>】 开:00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>平特一肖</strong></span>:【<span class='stylezi'><strong>兔兔兔</strong></span><strong>】 开:38准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>平特一肖</strong></span>:【<span class='stylezi'><strong>狗狗狗</strong></span><strong>】 开:19准
</strong>
</td>
</tr>	
 
 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>平特一肖</strong></span>:【<span class='stylezi'><strong>鸡鸡鸡</strong></span><strong>】 开:44准
</strong>
</td>
</tr>	

 
 
 
 


 



</table>*/

;
﻿
$.ajax({
    url: httpApi + `/api/kaijiang/getDxd?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let dand = '';
        let danx = '';
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
                    xiao.push(c[0].substring(0,2))
                    xiaoV[i] = c[1];
                    if (c[0] === '胆大生肖') {
                        dand = c[1].replaceAll(',','');
                    }else{
                        danx = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>胆大胆小</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>胆大胆小</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>胆大生肖</span>:<span class='stylezi'>牛虎马猴狗猪</span><br><span class='styleliao'>  胆小生肖</span>:<span class='stylezi'>鼠兔龙蛇羊鸡</span>
</td>
</tr>		

            ${htmlBoxList}
            </table>
        `;
        $(".l65").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>胆大胆小</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>胆大生肖</span>:<span class='stylezi'>牛虎马猴狗猪</span><br><span class='styleliao'>  胆小生肖</span>:<span class='stylezi'>鼠兔龙蛇羊鸡</span>
</td>
</tr>			








<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>胆大胆小</strong></span>:<span class='stylezi'><strong>胆小</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	

<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>胆大胆小</strong></span>:<span class='stylezi'><strong>胆小</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	

 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>胆大胆小</strong></span>:<span class='stylezi'><strong>胆大</strong></span><strong> 开:猪30准
</strong>
</td>
</tr>	

 

 


</table>*/

;
﻿$.ajax({
    url: httpApi + `/api/kaijiang/getHllx?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let hong = '';
        let lv = '';
        let lan = '';
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
                    if (c[0] === '红肖') {
                        hong = c[1].replaceAll(',','');
                    }else if (c[0] === '蓝肖'){
                        lan = c[1].replaceAll(',','');
                    }else if (c[0] === '绿肖'){
                        lv = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>红蓝绿肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}肖</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>红蓝绿肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>红肖</span>:<span class='stylezi'>马.兔.鼠.鸡</span><span class='styleliao'>  蓝肖</span>:<span class='stylezi'>蛇.虎.猪.猴</span><br>绿肖</span>:<span class='stylezi'>羊.龙.牛.狗</span>
</td>
</tr>		

            ${htmlBoxList}
            </table>
        `;
        $(".l66").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>红蓝绿肖</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>红肖</span>:<span class='stylezi'>马兔鼠鸡</span><span class='styleliao'>  蓝肖</span>:<span class='stylezi'>蛇虎猪猴</span><br>绿肖</span>:<span class='stylezi'>羊龙牛狗</span>
</td>
</tr>		












<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>红蓝绿肖</strong></span>:<span class='stylezi'><strong>红蓝肖</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>红蓝绿肖</strong></span>:<span class='stylezi'><strong>红<span style='background-color: #FFFF00'>蓝</span>肖</strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	



<tr>
<td align='center' height=40 class='stylelxz'><strong>
266期</strong><span class='styleliao'><strong>红蓝绿肖</strong></span>:<span class='stylezi'><strong>绿<span style='background-color: #FFFF00'>蓝</span>肖</strong></span><strong> 开:虎27准
</strong>
</td>
</tr>	
 
<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>红蓝绿肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>蓝</span>红肖</strong></span><strong> 开:猪30准
</strong>
</td>
</tr>	

 
 

 
 
  
  


</table>*/

;
﻿
$.ajax({
    url: httpApi + `/api/kaijiang/qqsh?web=${web}&type=${type}&num=3`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let qin = '';
        let qi = '';
        let shu = '';
        let hua = '';
        if (data.length > 0) {
            for (let i in data) {
                let d = data[i]
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = d.title.split(',');
                let xiaoV = [];
                let ma = [];
                let cont = d.content.split(',');;
                xiaoV[0] = cont.slice(0,3).join('');
                xiaoV[1] = cont.slice(3,6).join('');
                xiaoV[2] = cont.slice(6).join('');

                let c1 = [];
                let zj = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiaoV[i].indexOf(sx) !== -1) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                    if (xiao[i] === '琴') {
                        qin = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '书') {
                        shu = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '棋') {
                        qi = xiaoV[i].replaceAll(',','');
                    }else if (xiao[i] === '画') {
                        hua = xiaoV[i].replaceAll(',','');
                    }
                }

                htmlBoxList += ` 
 <tr>
<td align='center' height=40 class='stylelxz'><strong>
${d.term}期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong>${c1.join('')}</strong></span><strong> 开:${sx||'？'}${code||'00'}${ (sx?( zj?'准':'错'):'??')}
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>琴棋书画</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>琴肖</span>:<span class='stylezi'>${qin}</span>     <span class='styleliao'>棋肖</span>:<span class='stylezi'>${qi}</span><br>
<span class='styleliao'>书肖</span>:<span class='stylezi'>${shu}</span>     <span class='styleliao'>画肖</span>:<span class='stylezi'>${hua}</span>
</td>
</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l67").html(htmlBoxList)
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
<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>琴棋书画</font></font></font></b></td>
</tr>

<tr>
<td align='center' height=40 class='stylelxz'>
<span class='styleliao'>琴肖</span>:<span class='stylezi'>鸡兔蛇</span>     <span class='styleliao'>棋肖</span>:<span class='stylezi'>鼠牛狗</span><br>
<span class='styleliao'>书肖</span>:<span class='stylezi'>马龙虎</span>     <span class='styleliao'>画肖</span>:<span class='stylezi'>羊猪猴</span>
</td>
</tr>			























<tr>
<td align='center' height=40 class='stylelxz'><strong>
268期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong>书画琴</strong></span><strong> 开:？00准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
267期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong>书画<span style='background-color: #FFFF00'>琴</span></strong></span><strong> 开:蛇12准
</strong>
</td>
</tr>	

 

<tr>
<td align='center' height=40 class='stylelxz'><strong>
265期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>棋</span>书琴</strong></span><strong> 开:牛16准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
264期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong>琴书<span style='background-color: #FFFF00'>画</span></strong></span><strong> 开:猪30准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
263期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong>琴画<span style='background-color: #FFFF00'>书</span></strong></span><strong> 开:龙13准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
262期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong><span style='background-color: #FFFF00'>琴</span>棋画</strong></span><strong> 开:鸡44准
</strong>
</td>
</tr>	


<tr>
<td align='center' height=40 class='stylelxz'><strong>
261期</strong><span class='styleliao'><strong>琴棋书画肖</strong></span>:<span class='stylezi'><strong>棋<span style='background-color: #FFFF00'>书</span>画</strong></span><strong> 开:龙01准
</strong>
</td>
</tr>	
  
  

</table>*/

