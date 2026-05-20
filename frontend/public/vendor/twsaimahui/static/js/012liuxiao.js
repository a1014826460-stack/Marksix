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
