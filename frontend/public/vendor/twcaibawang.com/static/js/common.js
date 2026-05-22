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
    '<li><a id="fixedNavKjZl" class="hover" target="_blank" href="/history?type=1"><span class="list"></span>开奖</a></li>'+
    '<li class="cfl-more"><a id="fixedNavKjZl" onclick="siteToggle()">更多</a></li>'+
    '<li><a id="fixedNavKjZs" href="#pl"><span class="cfl4"></span>评论</a></li>'+
    '<li><a id="fixedNavTk" href="'+pt.link+'" target="_blank"><span class="bag"></span>送588红包</a></li></ul></div>';


var sites = '<div id="allsite"><ul class="clearfix" style="background: linear-gradient(#13ab56,#077e35);">'+
'<li><a href="/twcaibawang">香港天天彩首页</a></li>'+
'<li><a href="/history?type=1" target="_blank">香港彩历史记录</a></li>'+
'<li><a href="/history?type=2" target="_blank">澳门彩历史记录</a></li>'+
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


