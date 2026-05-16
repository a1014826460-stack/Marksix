$.ajaxSetup({
/*    beforeSend: function(xhr) {
        console.log('拦截AJAX请求');
// 在请求头中添加token
        xhr.setRequestHeader('Authorization', 'Bearer token');
    },*/
    complete: function(xhr) {
// 处理响应数据
//         console.log(xhr);
        // let response = JSON.parse(xhr.responseText);
        // if (response.error) {
        //     alert('请求出错：' + response.error);
        // }
    },
    success: function(data, textStatus, jqXHR) {
        // 修改返回的数据
        console.log(data)
        return null; // 注意：这里直接返回数据不会影响原始数据，只是改变了回调中的数据值
    },
/*    statusCode: {
        404: function() {
            alert('数据获取失败，404错误');
        },
        500: function() {
            alert('服务器错误，500错误');
        }
    }*/
});

//拦截器
$.ajaxPrefilter(function(options, originalOptions, jqXHR) {
    // 拦截返回的数据
    jqXHR.done(function(data) {
        // 修改返回的数据
        let array = data.data;
        if (!(array instanceof Array)) {
            return data;
        }
        array.forEach(function(e) {
            // 确保所有可能被 .split(',') 或 JSON.parse() 使用的字段不为 null
            // res_code / res_sx 固定保护
            if (e.res_code == null) e.res_code = '';
            if (e.res_sx == null) e.res_sx = '';
            else e.res_sx = replaceOldChat(e.res_sx);

            // content 字段：全部业务模块都会读取
            if (e.content == null) e.content = '';

            // 特殊字段：对应模块直接用 .split() 读取，null 会导致 JS 报错
            // 单双四尾 (003ds4w.js)
            if (e.dan == null) e.dan = '';
            if (e.shuang == null) e.shuang = '';
            // 男女 (020nn4x.js)
            if (e.nan == null) e.nan = '';
            if (e.nv == null) e.nv = '';
            // 特邀单双四肖 (060ds4x.js)
            if (e.xiao_1 == null) e.xiao_1 = '';
            if (e.xiao_2 == null) e.xiao_2 = '';
            // 九肖一码 (013jiux1m.js)、两肖+八码 (069lxbm.js)、特邀家野两肖 (061jy2x.js)
            if (e.xiao == null) e.xiao = '';
            if (e.code == null) e.code = '';
            // 六不中 (019liubuzhong.js)
            if (e.u6_code == null) e.u6_code = '';
            // 成语平肖 (066chengyupx.js)、成语平特尾 (068chengyupw.js)、琴棋书画 (052qqsh.js)
            if (e.title == null) e.title = '';
            // 一字玄机 (029yizixuanji.js)
            if (e.jiexi == null) e.jiexi = '';
            if (e.zi == null) e.zi = '';
            // 三期必中 (023sanqibizhong.js)
            if (e.name == null) e.name = '';
            if (e.start == null) e.start = '';
            if (e.end == null) e.end = '';
            // 跑马图 (011jiepaoma.js)
            if (e.image_url == null) e.image_url = '';
        })

        return data;
    });
});



function replaceOldChat(str){
    return str.replaceAll('龍','龙').replaceAll('馬','马')
        .replaceAll('雞','鸡')
        .replaceAll('鷄','鸡')
        .replaceAll('豬','猪')
}