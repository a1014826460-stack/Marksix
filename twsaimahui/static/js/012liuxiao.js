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
            if (!content.length) continue;
            var xiao = [];
            var ma = [];
            for (var j = 0; j < content.length; j++) {
                var c = content[j].split('|');
                xiao.push(c[0]);
                xiao.push(c[1]);
                ma.push.apply(ma, (c[1] || '').split(','));
            }
            var c1 = [];
            var zj = false;
            for (var k = 0; k < xiao.length; k += 2) {
                if (sx && xiao[k + 1] && xiao[k + 1].indexOf(sx) !== -1) {
                    zj = true;
                    c1.push('<span style="background-color: #FFFF00">' + xiao[k] + '</span>');
                } else {
                    c1.push(xiao[k]);
                }
            }
            var c2 = [];
            for (var m = 0; m < ma.length; m++) {
                if (code && ma[m].indexOf(code) !== -1) {
                    zj = true;
                    c2.push('<span style="background-color: #FFFF00">' + ma[m] + '</span>');
                } else {
                    c2.push(ma[m]);
                }
            }
            var ma12j = c2.slice(0, 12).join('.');
            var ma12 = ma12j.indexOf('span') === -1 ? '' : '<p style=\'font-size:13pt;margin-bottom:8px;text-align:left\'><span style=\'text-indent:28px;color:#000;font-family:微软雅黑;font-size:12pt\'>精选12码：' + c2.join('.') + '</span></p>';
            var ma6j = c2.slice(0, 6).join('.');
            var ma6 = ma6j.indexOf('span') === -1 ? '' : '<p style=\'font-size:13pt;margin-bottom:8px;text-align:left\'><span style=\'text-indent:28px;color:#000;font-family:微软雅黑;font-size:12pt\'>精选六码：' + c2.slice(0, 6).join('.') + '</span></p>';
            var ma1j = c2.slice(0, 1).join('.');
            var ma1 = ma1j.indexOf('span') === -1 ? '' : '<p style=\'font-size:13pt;margin-bottom:8px;text-align:left\'><span style=\'text-indent:28px;color:#000;font-family:微软雅黑;font-size:12pt\'>必中一码：' + c2.slice(0, 1).join('.') + '</span></p>';
            var x6j = c1.slice(0, 6).join('-');
            var x6 = x6j.indexOf('span') === -1 ? '' : '<p style=\'font-size:13pt;margin-bottom:8px;text-align:left\'><span style=\'text-indent:28px;color:#000;font-family:微软雅黑;font-size:12pt\'>必中六肖：' + c1.join('.') + '</span></p>';
            var x3j = c1.slice(0, 3).join('-');
            var x3 = x3j.indexOf('span') === -1 ? '' : '<p style=\'font-size:13pt;margin-bottom:8px;text-align:left\'><span style=\'text-indent:28px;color:#000;font-family:微软雅黑;font-size:12pt\'>必中三肖：' + c1.slice(0, 3).join('.') + '</span></p>';
            var x1j = c1.slice(0, 1).join('-');
            var x1 = x1j.indexOf('span') === -1 ? '' : '<p style=\'font-size:13pt;margin-bottom:8px;text-align:left\'><span style=\'text-indent:28px;color:#000;font-family:微软雅黑;font-size:12pt\'>必中一肖：' + c1.slice(0, 1).join('.') + '</span></p>';
            htmlBoxList += ' <table border=\'1\' width=\'100%\' cellpadding=\'0\' height=\'100\' cellspacing=\'0\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' bgcolor=\'#FFFFFF\' style=\'border-collapse:collapse;border-spacing:0;color:#444;font-family:tahoma,微软雅黑,宋体,arial,georgia,verdana,helvetica,sans-serif;font-size:14px;font-style:normal;font-variant-ligatures:normal;font-weight:normal;letter-spacing:normal;line-height:21px;text-align:start;text-indent:0;text-transform:none;white-space:normal;widows:1;word-spacing:0;-webkit-text-stroke-width:0;background-color:#fff\'><tbody><tr class=\'firstRowxx\'><td height=\'35\' style=\'background:#FF0000;margin:0;border-color:green;word-break:break-all;text-align:center;font-size:13pt;line-height:26px;color:#333;padding-left:2px;padding-right:2px;padding-top:3px;padding-bottom:3px\'><span style=\'color:#FFF;font-family:微软雅黑;font-weight:700;line-height:normal;font-size:12pt\'>' + d.term + '期：六肖三码</span></td></tr><tr><td style=\'margin:0;padding:3px 2px;border-color:#e5e5e5;word-break:break-all;text-align:center;line-height:26px\'>' + x6 + x3 + x1 + ma12 + ma6 + ma1 + '</td></tr></tbody></table>';
        }
        if (!htmlBoxList) {
            renderEmpty('.l3');
            return;
        }
        $('.l3').html('<style>div.sbxztt{border-radius:4px;box-shadow:0 1px 2px rgba(180,180,180,0.7);background-color:#fff;zoom:1;font:14px/1.5 tahoma,微软雅黑,宋体,arial,georgia,verdana,helvetica,sans-serif;color:#444}tr.firstRowxx{background-color:rgb(139,69,19)}</style><div class=\'sbxztt\'>' + htmlBoxList + '</div>');
    })
    .fail(function () {
        renderError('.l3', '精品六肖数据加载失败');
    });
