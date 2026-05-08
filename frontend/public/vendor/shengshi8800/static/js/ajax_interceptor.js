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
        array.forEach(e=>{
            if (!e.res_sx) return;
            e.res_sx = replaceOldChat(e.res_sx);
        })

        return data;
    });
});



function replaceOldChat(str){
    if (typeof str !== "string") return str;
    return str.replaceAll('龍','龙').replaceAll('馬','马')
        .replaceAll('雞','鸡')
        .replaceAll('鷄','鸡')
        .replaceAll('豬','猪')
}
