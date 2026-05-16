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
