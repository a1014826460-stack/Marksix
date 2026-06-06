// 默认值：防止外部脚本(pub.js/gg.js)缺失时报错
var jy = window.jy || { siteid: '', cur: '' };
var pt = window.pt || { link: '#', name: '投注' };
var popMore = window.popMore || '';

$('.content').css('margin-bottom','50px')

function setIframeHeight(iframe) {
  if (iframe) {
    var iframeWin = iframe.contentWindow || iframe.contentDocument.parentWindow;
    if (iframeWin.document.body) {
    iframe.height = iframeWin.document.documentElement.scrollHeight || iframeWin.document.body.scrollHeight;
    }
  }
}

function addCookie(objName, objValue, objHours) {
    var str = objName + "=" + escape(objValue);
    if (objHours > 0) {
        var date = new Date();
        var ms = objHours * 3600 * 1000;
        date.setTime(date.getTime() + ms);
        str += "; expires=" + date.toUTCString();
    }
    document.cookie = str;
}

function getCookie(objName) {
    var arrStr = document.cookie.split("; ");
    for (var i = 0; i < arrStr.length; i++) {
        var temp = arrStr[i].split("=");
        if (temp[0] == objName)
            return unescape(temp[1]);
    }
}

function iOS() {
  return [
    'iPad Simulator','iPhone Simulator','iPod Simulator','iPad','iPhone','iPod'
  ].includes(navigator.platform) || (navigator.userAgent.includes("Mac") && "ontouchend" in document)
}

var appLink = iOS()?('https://app.vuehelp.com/ios/'+jy.siteid+'.mobileconfig'):('https://app.vuehelp.com/apk/'+jy.siteid+'.apk');

var menu = '<div class="cgi-foot-links"><div class="cgi-pl-quick"><style>.download65{left: 0px;position:absolute;width:100%;height: 31px;bottom:59px;background-color:rgba(0,0,0,.8);z-index: 1;}.download65 i.close{display:block;position:absolute;top: 16px;left:0;height:25px;width:25px;background-image:url(https://res.shanghaixiaochagu.com/assets/img/gb.png);background-size:20px 20px;background-repeat:no-repeat;background-position:50%;}.download65 p{margin: auto 0px;font-size:13px;font-weight:700;color:#fff;line-height: 34px;text-indent:3px;white-space: nowrap;}.download65 .btn{height: 25px;line-height: 25px;width:70px;text-align:left;background-color:#ec0909;bottom:0;top:0;margin: auto 10px auto 10px;font-size:14px;border: none;border-radius: 5px;padding: 0;color: #fff;display: inline-block;cursor: pointer;}.download65 a:hover{height: 25px;line-height: 25px;width:70px;text-align:left;background-color:#ec0909;bottom:0;top:0;margin: auto 10px auto 10px;font-size:14px;border: none;border-radius: 5px;padding: 0;color: #fff;}.download65 span { display: inline-block; width: 57px; height: 23px; vertical-align: middle; background: url(https://res.shanghaixiaochagu.com/assets/img/gx.gif) no-repeat; background-size: 100% 100%;}</style><div id="guanbia" class="download65"><p id="apaa" style="padding-left:10px"><a target="_blank" href="'+appLink+'" style="color:inherit;">'+document.title.split('-')[0]+'APP已经上线了</a><a target="_blank" href="'+appLink+'" class="btn" id="apas">点击下载</a><span></span></p></div><div id="bar" style="z-index:999"><div class="kai" style="display:none" onclick="$(\'.guan\').show();$(\'.kai\').hide();$(\'.cgi-foot-links\').css(\'bottom\',\'0\')">展开 ⇈ </div><div class="guan" onclick="$(\'.kai\').show();$(\'.guan\').hide();$(\'.cgi-foot-links\').css(\'bottom\',\'-60px\')">收起 ⇊ </div></div>'+
    '<ul class="clearfix">'+
    '<li><a id="fixedNavIndex" href="javascript:$(\'#allsite\').hide();$(\'#popMore\').toggle()" style="color:red"><span><svg class="icon" style="width:30px;height:38px;vertical-align: middle;fill: currentColor;overflow: hidden;" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="740"><path d="M951.9 902.9L827.1 736l59.7-59.7c11.8-11.8 4.8-32-11.8-34l-87.8-10.4C803.4 594.6 812 554 812 512s-8.6-82.6-24.9-119.9l87.7-10.4c16.6-2 23.6-22.2 11.8-34L827 288l124.8-167c24.2-32.4-16.6-73.2-49-49l-167 124.8-59.7-59.7c-11.8-11.8-32-4.8-34 11.8l-10.4 87.8C594.5 220.6 553.9 212 512 212c-41.9 0-82.5 8.6-119.8 24.8L381.8 149c-2-16.6-22.2-23.6-34-11.8l-59.7 59.7-167-124.8c-32.4-24.2-73.2 16.6-49 49L197 288l-59.7 59.7c-11.8 11.8-4.8 32 11.8 34l87.7 10.4C220.6 429.4 212 470 212 512s8.6 82.6 24.9 119.9l-87.7 10.4c-16.6 2-23.6 22.2-11.8 34L197 736 72.2 903c-24.2 32.4 16.6 73.2 49 49l167-124.8 59.7 59.7c11.8 11.8 32 4.8 34-11.8l10.4-87.8C429.5 803.4 470.1 812 512 812c41.9 0 82.6-8.6 119.9-24.8l10.4 87.8c2 16.6 22.2 23.6 34 11.8l59.7-59.7 167 124.8c32.3 24.2 73.1-16.6 48.9-49zM512 752c-40.6 0-78.8-10.1-112.3-28l10.4-87.7c1.5-12.8-9.4-23.7-22.2-22.2L300 624.5c-17.9-33.6-28-71.9-28-112.5 0-40.6 10.2-78.9 28-112.5l87.7 10.4c12.8 1.5 23.7-9.4 22.2-22.2L399.6 300c33.5-17.9 71.8-28 112.4-28 40.6 0 78.8 10.1 112.4 28L614 387.7c-1.5 12.8 9.4 23.7 22.2 22.2l87.7-10.4c17.9 33.6 28 71.8 28 112.5 0 40.6-10.2 78.9-28 112.5l-87.7-10.4c-12.8-1.5-23.7 9.4-22.2 22.2l10.4 87.7c-33.5 17.9-71.8 28-112.4 28zM512 512m-130 0a130 130 0 1 0 260 0 130 130 0 1 0-260 0Z" p-id="741"></path></svg></span>一肖一码</a></li>'+
    //'<li><a id="fixedNavIndex" href="/"><span class="home"></span>首页</a></li>'+
    '<li><a id="fixedNavKjZl" class="hover" target="_blank" href="https://www.8852666.com/user/year.html"><span class="list"></span>开奖</a></li>'+
    '<li class="cfl-more"><a id="fixedNavKjZl" onclick="siteToggle()">更多</a></li>'+
    '<li><a id="fixedNavKjZs" href="#pl"><span class="cfl4"></span>评论</a></li>'+
    '<li><a id="fixedNavTk" href="'+pt.link+'" target="_blank"><span class="bag"></span>送588红包</a></li></ul></div>';


var sites = '<div id="allsite"><ul class="clearfix" style="background: linear-gradient(#13ab56,#077e35);">'+
'<li><a href="https://163744.pe386yrvgq.shop/#gdgd" target="_blank">澳门内幕</a></li>'+
'<li><a href="https://152544.rfdvmmnphq.shop/#gdgd" target="_blank">牛魔王网</a></li>'+
'<li><a href="https://159044.zl4adaydbt.shop/#gdgd" target="_blank">男人味网</a></li>'+
'<li><a href="https://157144.lppyq4wd3b.shop/#gdgd" target="_blank">大庄家网</a></li>'+
'<li><a href="https://156144.002yg4gu1l.shop/#gdgd" target="_blank">黄鹤楼网</a></li>'+

'<li><a href="https://153544.pklnbdecl7.shop/#gdgd" target="_blank">九龙心水</a></li>'+
'<li><a href="https://153044.9w9gak8wmw.shop/#gdgd" target="_blank">澳门码神</a></li>'+
'<li><a href="https://145044.56dq3wheqr.shop/#gdgd" target="_blank">马会彩讯</a></li>'+
'<li><a href="https://141044.uhpc04ij0e.shop/#gdgd" target="_blank">澳门公益</a></li>'+
'<li><a href="https://140744.2ajcs1yybg.shop/#gdgd" target="_blank">招财猫网</a></li>'+

'<li><a href="https://298544.44acm3fze0.shop/#gdgd" target="_blank">青龙阁网</a></li>'+
'<li><a href="https://298144.mgarguhar2.shop/#gdgd" target="_blank">藏宝阁网</a></li>'+
'<li><a href="https://297144.zf2s3uisqc.shop/#gdgd" target="_blank">金财神网</a></li>'+
'<li><a href="https://296144.fxabhz1xzz.shop/#gdgd" target="_blank">澳门全讯</a></li>'+
'<li><a href="https://295144.75omy1oal0.shop/#gdgd" target="_blank">蛇蛋论坛</a></li>'+

'<li><a href="https://293544.b2hksyzmpj.shop/#gdgd" target="_blank">聚彩论坛</a></li>'+
'<li><a href="https://291544.kesnsxd7uv.shop/#gdgd" target="_blank">曾道人网</a></li>'+
'<li><a href="https://289144.gko5fgslyk.shop/#gdgd" target="_blank">天线宝宝</a></li>'+
'<li><a href="https://287144.uezadkicyd.shop/#gdgd" target="_blank">老鼠报网</a></li>'+
'<li><a href="https://286144.9du4czbxut.shop/#gdgd" target="_blank">澳彩霸王</a></li>'+

'<li><a href="https://356122.88t5twi6yn.shop/#gdgd" target="_blank">澳门挂牌</a></li>'+
'<li><a href="https://195338.ssdr3fe87f.shop/#gdgd" target="_blank">西游降庄</a></li>'+
'<li><a href="https://36296.r0nxya74t5.shop/#gdgd" target="_blank">澳门玄机</a></li>'+
'<li><a href="https://404455.shypwza4ex.shop/#gdgd" target="_blank">凤凰天机</a></li>'+
'<li><a href="https://356822.wmptqaefmz.shop/#gdgd" target="_blank">澳彩民网</a></li>'+

'<li><a href="https://442251.qhfo8cc10c.shop/#gdgd" target="_blank">澳鬼谷子</a></li>'+
'<li><a href="https://443303.91b6ine6d8.shop/#gdgd" target="_blank">澳摇钱树</a></li>'+
'<li><a href="https://725322.wfr6njr603.shop/#gdgd" target="_blank">澳彩论坛</a></li>'+
'<li><a href="https://726322.be78327d4s.shop/#gdgd" target="_blank">澳王中王</a></li>'+
'<li><a href="https://726533.27ob50wrjz.shop/#gdgd" target="_blank">惠泽社群</a></li>'+

'<li><a href="https://726822.3m5tio7ma8.shop/#gdgd" target="_blank">澳门跑狗</a></li>'+
'<li><a href="https://727522.6tfktusawy.shop/#gdgd" target="_blank">澳高手网</a></li>'+
'<li><a href="https://728911.5epqogu37w.shop/#gdgd" target="_blank">澳金多宝</a></li>'+
'<li><a href="https://193544.t7wo0hrgj0.shop/#gdgd" target="_blank">澳六合彩</a></li>'+
'<li><a href="https://195144.j3155drog6.shop/#gdgd" target="_blank">报彩神童</a></li>'+

'<li><a href="https://219472.o9ifgt40rm.shop/#gdgd" target="_blank">红双喜网</a></li>'+
'<li><a href="https://279144.18gncwapg2.shop/#gdgd" target="_blank">金手指网</a></li>'+
'<li><a href="https://283544.mga1iyfzcp.shop/#gdgd" target="_blank">红姐论坛</a></li>'+
'<li><a href="https://285144.3snufxlaf8.shop/#gdgd" target="_blank">淘码论坛</a></li>'+
'<li><a href="https://216744.uhf8uisi3x.shop/#gdgd" target="_blank">创富论坛</a></li>'+

'<li><a href="https://217144.b1dg3gjkvg.shop/#gdgd" target="_blank">博彩皇网</a></li>'+
'<li><a href="https://101963.u3g7mn1l2l.shop/#gdgd" target="_blank">花仙子网</a></li>'+
'<li><a href="https://101960.c9w8zgm3cx.shop/#gdgd" target="_blank">观音救世</a></li>'+
'<li><a href="https://216144.0gliz8bqm7.shop/#gdgd" target="_blank">黄大仙网</a></li>'+
'<li><a href="https://215144.qtnazt86da.shop/#gdgd" target="_blank">姜太公网</a></li>'+

'<li><a href="https://213544.azhq73fsw4.shop/#gdgd" target="_blank">皇博神算</a></li>'+
'<li><a href="https://212544.nvpp0in748.shop/#gdgd" target="_blank">挂牌论坛</a></li>'+
'<li><a href="https://101984.2ruy41786l.shop/#gdgd" target="_blank">幽默玄机</a></li>'+
'<li><a href="https://101981.htt89kjl7f.shop/#gdgd" target="_blank">美人鱼网</a></li>'+
'<li><a href="https://101974.11v66642uw.shop/#gdgd" target="_blank">夜明珠网</a></li>'+

'<li><a href="https://101971.fjpomzipf2.shop/#gdgd" target="_blank">铁算盘网</a></li>'+
'<li><a href="https://101956.g3si4kdwrv.shop/#gdgd" target="_blank">彩票论坛</a></li>'+
'<li><a href="https://101934.1t9b4chwky.shop/#gdgd" target="_blank">金钥匙网</a></li>'+
'<li><a href="https://101931.kuukdws4co.shop/#gdgd" target="_blank">今日闲情</a></li>'+
'<li><a href="https://101902.6uy93al6ku.shop/#gdgd" target="_blank">百晓生网</a></li>'+

'<li><a href="https://101924.4li6oibtrt.shop/#gdgd" target="_blank">水果奶奶</a></li>'+
'<li><a href="https://101921.gtlq2ytri2.shop/#gdgd" target="_blank">澳彩开奖</a></li>'+
'<li><a href="https://190144.kht42ky7nd.shop/#gdgd" target="_blank">老奇人网</a></li>'+
'<li><a href="https://191544.mwo30hxc8d.shop/#gdgd" target="_blank">澳白小姐</a></li>'+
'<li><a href="https://101913.kvbzwvlpbq.shop/#gdgd" target="_blank">马会传真</a></li>'+



'<li><a href="https://176144.ppnezfgno3.shop/#gdgd" target="_blank">彩民之家</a></li>'+
'<li><a href="https://176744.uu0t5ke8q6.shop/#gdgd" target="_blank">凤凰论坛</a></li>'+
'<li><a href="https://175644.jtnl7e85r5.shop/#gdgd" target="_blank">天空彩票</a></li>'+
'<li><a href="https://182544.7qv9wrxo0t.shop/#gdgd" target="_blank">澳管家婆</a></li>'+
'<li><a href="https://173744.8p5zwi5lcs.shop/#gdgd" target="_blank">澳门平特</a></li>'+

'<li><a href="https://183544.229k6hjfgw.shop/#gdgd" target="_blank">彩票通讯</a></li>'+
'<li><a href="https://185144.m2nzyfad3z.shop/#gdgd" target="_blank">澳神算子</a></li>'+
'<li><a href="https://163044.dm95z6kkle.shop/#gdgd" target="_blank">六合之家</a></li>'+
'<li><a href="https://172544.1wjnbf781e.shop/#gdgd" target="_blank">澳何仙姑</a></li>'+
'<li><a href="https://178144.t7jzw26g3w.shop/#gdgd" target="_blank">澳彩预测</a></li>'+

'<li><a href="https://179644.vguh4byj7s.shop/#gdgd" target="_blank">澳公证处</a></li>'+
'<li><a href="https://409144.ucqrvf3jne.shop/#gdgd" target="_blank">澳丰收网</a></li>'+
'<li><a href="https://410544.dnfuylpr0t.shop/#gdgd" target="_blank">澳盛世网</a></li>'+
'<li><a href="https://415144.25i79952c1.shop/#gdgd" target="_blank">澳门宝典</a></li>'+
'<li><a href="https://416144.r0q1sb4y08.shop/#gdgd" target="_blank">澳金算盘</a></li>'+

  '<div class="clearfix"></div></ul><ul class="clearfix" style="background: linear-gradient(#e10019,#bf0000);">' +
'<li><a target="_blank" href="https://951144.8qwycn8pkd.shop/#gdgd">铁算盘网</a></li>'+
'<li><a target="_blank" href="https://504466.qdru40fvhy.shop/#gdgd">王中王网</a></li>'+
'<li><a target="_blank" href="https://446620.tbp6o37nym.shop/#gdgd">诸葛亮网</a></li>'+
'<li><a target="_blank" href="https://992241.g28v4jevd2.shop/#gdgd">管家婆网</a></li>'+
'<li><a target="_blank" href="https://705999.c906ygh6co.shop/#gdgd">天下彩网</a></li>'+
'<li><a target="_blank" href="https://006607.ajygyhcoet.shop/#gdgd">大丰收网</a></li>'+
'<li><a target="_blank" href="https://530044.wq984sd8sn.shop/#gdgd">宋小宝网</a></li>'+
'<li><a target="_blank" href="https://003389.qomuw9fgvw.shop/#gdgd">青苹果网</a></li>'+
'<li><a target="_blank" href="https://005559.rnrscy6x69.shop/#gdgd">大赢家网</a></li>'+
'<li><a target="_blank" href="https://36357.fhbbwilz9n.shop/#gdgd">六合之家</a></li>'+
'<li><a target="_blank" href="https://005506.m8c680s7il.shop/#gdgd">白小姐网</a></li>'+
'<li><a target="_blank" href="https://442250.fmukh8220s.shop/#gdgd">六合社区</a></li>'+
'<li><a target="_blank" href="https://6925888.8ufjhluevo.shop/#gdgd">小鱼儿网</a></li>'+
'<li><a target="_blank" href="https://003331.u3x0hvshf1.shop/#gdgd">凤凰论坛</a></li>'+
'<li><a target="_blank" href="https://444856.oukc6ub12b.shop/#gdgd">金明世家</a></li>'+
'<li><a target="_blank" href="https://003339.tdehcj5eir.shop/#gdgd">大头家网</a></li>'+
'<li><a target="_blank" href="https://444869.kobbras7di.shop/#gdgd">管家婆网</a></li>'+
'<li><a target="_blank" href="https://001128.lyqudrybpq.shop/#gdgd">金光佛网</a></li>'+
'<li><a target="_blank" href="https://444897.b5azwzgf68.shop/#gdgd">香港挂牌</a></li>'+
'<li><a target="_blank" href="https://005553.bq2hxplrxn.shop/#gdgd">马三炮网</a></li>'+
'<li><a target="_blank" href="https://444928.kidcjxq54a.shop/#gdgd">老奇人网</a></li>'+
'<li><a target="_blank" href="https://444158.uu5xwwg40y.shop/#gdgd">创富论坛</a></li>'+
'<li><a target="_blank" href="https://44317.pn4phrqe8y.shop/#gdgd">必發心水</a></li>'+
'<li><a target="_blank" href="https://003337.zgsmavzjaf.shop/#gdgd">六合宝典</a></li>'+
'<li><a target="_blank" href="https://006610.6hr0n1kfix.shop/#gdgd">彩霸王网</a></li>'+
'<li><a target="_blank" href="https://001113.d55b3i65gh.shop/#gdgd">光头强网</a></li>'+
'<li><a target="_blank" href="https://444896.w3l43f0t9s.shop/#gdgd">挂牌论坛</a></li>'+
'<li><a target="_blank" href="https://001176.zfbrkx4p39.shop/#gdgd">赛马会网</a></li>'+
'<li><a target="_blank" href="https://444867.p6z1mrcirx.shop/#gdgd">天马心水</a></li>'+
'<li><a target="_blank" href="https://003332.z8zxdn1f5f.shop/#gdgd">奇门遁甲</a></li>'+
'<li><a target="_blank" href="https://13265.0jk67l7zwm.shop/#gdgd">六合财神</a></li>'+
'<li><a target="_blank" href="https://006662.tk2yfb52fi.shop/#gdgd">六合头条</a></li>'+
'<li><a target="_blank" href="https://00332.aph1vo24dg.shop/#gdgd">一点红网</a></li>'+
'<li><a target="_blank" href="https://001152.g7ulpq7df8.shop/#gdgd">顶尖高手</a></li>'+
'<li><a target="_blank" href="https://444587.9rzdgn61p1.shop/#gdgd">状元红网</a></li>'+
'<li><a target="_blank" href="https://006669.z9b99jbgiy.shop/#gdgd">六合慈善</a></li>'+
'<li><a target="_blank" href="https://53161.8lc2h6rvt0.shop/#gdgd">金多宝网</a> </li>'+
'<li><a target="_blank" href="https://007751.wxj7mcjp29.shop/#gdgd">东方论坛</a></li>'+
'<li><a target="_blank" href="https://42771.e9fjezripn.shop/#gdgd">白姐论坛</a></li>'+
'<li><a target="_blank" href="https://005570.xw6qcu60ym.shop/#gdgd">鬼谷子网</a></li>'+
'<li><a target="_blank" href="https://007730.fu6fksgx9x.shop/#gdgd">马经论坛</a></li>'+
'<li><a target="_blank" href="https://007771.wdn9r4oxt5.shop/#gdgd">彩票论坛</a></li>'+
'<li><a target="_blank" href="https://003376.xcyyhatj8d.shop/#gdgd">马经卦网</a></li>'+
'<li><a target="_blank" href="https://524466.76owomcsuo.shop/#gdgd">太阳神网</a></li>'+
'<li><a target="_blank" href="https://444178.n5cvzg4d6c.shop/#gdgd">九五至尊</a></li>'+
'<li><a target="_blank" href="https://005520.e7w68uli4f.shop/#gdgd">手机开奖</a></li>'+
'<li><a target="_blank" href="https://005509.xflir440ln.shop/#gdgd">陈教授网</a></li>'+
'<li><a target="_blank" href="https://007705.by7p366zr8.shop/#gdgd">六合宝典</a></li>'+
'<li><a target="_blank" href="https://005501.hrp1fbsxof.shop/#gdgd">火箭少女</a></li>'+
'<li><a target="_blank" href="https://505511.lbzq6zbtab.shop/#gdgd">六合神话</a></li>'+
'<li><a target="_blank" href="https://531144.1bra93pxzs.shop/#gdgd">大话西游</a></li>'+
'<li><a target="_blank" href="https://005557.8h2ot1fw91.shop/#gdgd">智多星网</a></li>'+
'<li><a target="_blank" href="https://510044.fncj5sgh8r.shop/#gdgd">赛马会网</a></li>'+
'<li><a target="_blank" href="https://005502.t5gc5ce14q.shop/#gdgd">曾夫人网</a></li>'+
'<li><a target="_blank" href="https://444676.r6hg6vcnpy.shop/#gdgd">黄大仙网</a></li>'+
'<li><a target="_blank" href="https://450033.et1ic92mgb.shop/#gdgd">廣東會网</a></li>'+
'<li><a target="_blank" href="https://443369.v81npy5xhj.shop/#gdgd">白姐工作</a></li>'+
'<li><a target="_blank" href="https://1313kj.k64nhdq3j4.shop/#gdgd">最快开奖</a></li>'+
'<li><a target="_blank" href="https://336640.c8i0tc2iuy.shop/#gdgd">码王图库</a></li>'+
'<li><a href="'+pt.link+'" target="_blank">'+pt.name+'</a></li>'+
'<div class="clearfix"></div></ul></div>'+popMore;




function siteToggle() {
  $('#popMore').hide();
  $('#allsite').toggle();
}


$(document).ready(function() {
  $('.cgi-body').append(menu);
  
  $('.cgi-body').append(sites)
  
  $('p').on('click','img.thumb',function(){$(this).css('width','100%').css('max-height','auto').removeClass('thumb').addClass('prew')})
  $('p').on('click','img.prew',function(){$(this).css('width','auto').css('max-height','130px').removeClass('prew').addClass('thumb')})
  
  //if(jy.cur == 'detail') $('.cgi-body').append(tzBTN)
  
})

//香港汇总
var _hmt = _hmt || [];
(function() {
  var hm = document.createElement("script");
  hm.src = "https://hm.baidu.com/hm.js?2c7c0afaed0619aa48b953ef715006d0";
  var s = document.getElementsByTagName("script")[0]; 
  s.parentNode.insertBefore(hm, s);
})();