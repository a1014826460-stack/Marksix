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
