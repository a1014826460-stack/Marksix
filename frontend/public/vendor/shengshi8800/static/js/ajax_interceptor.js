// Plan B: request dedup cache + XHR tracking for abort
window.__moduleXHRs = window.__moduleXHRs || [];
window.__moduleRequestCache = window.__moduleRequestCache || new Map();

$.ajaxSetup({
    beforeSend: function(xhr) {
        window.__moduleXHRs.push(xhr);
    },
    complete: function(xhr) {
        // Clean up completed XHRs from tracker
        var idx = window.__moduleXHRs.indexOf(xhr);
        if (idx !== -1) window.__moduleXHRs.splice(idx, 1);
    },
    success: function(data, textStatus, jqXHR) {
        return null;
    },
});

// Plan B: deduplicate concurrent requests to the same URL
$.ajaxPrefilter(function(options, originalOptions, jqXHR) {
    // Only dedup GET requests to /api/kaijiang/
    if (options.type !== 'GET' || !options.url) return;
    if (options.url.indexOf('/api/kaijiang/') === -1) return;

    var cacheKey = options.url;
    var cached = window.__moduleRequestCache.get(cacheKey);
    if (cached && cached.readyState !== 4) {
        // Reuse in-flight request — abort this one and pipe callbacks
        jqXHR.abort = function() {};
        var origDone = jqXHR.done;
        cached.done(function(data, textStatus, jqXHR2) {
            if (originalOptions.success) {
                originalOptions.success(data, textStatus, jqXHR);
            }
        });
        cached.fail(function(jqXHR2, textStatus, errorThrown) {
            if (originalOptions.error) {
                originalOptions.error(jqXHR, textStatus, errorThrown);
            }
        });
        return false; // prevent this request from being sent
    }

    window.__moduleRequestCache.set(cacheKey, jqXHR);

    // Cleanup cache entry when request completes
    jqXHR.always(function() {
        if (window.__moduleRequestCache.get(cacheKey) === jqXHR) {
            window.__moduleRequestCache.delete(cacheKey);
        }
    });

    // Intercept response data for traditional→simplified conversion
    jqXHR.done(function(data) {
        var array = data.data;
        if (!(array instanceof Array)) {
            return data;
        }
        array.forEach(function(e) {
            if (!e.res_sx) return;
            e.res_sx = replaceOldChat(e.res_sx);
        });
        return data;
    });
});

function replaceOldChat(str) {
    if (typeof str !== "string") return str;
    return str.replaceAll('龍', '龙').replaceAll('馬', '马')
        .replaceAll('雞', '鸡')
        .replaceAll('鷄', '鸡')
        .replaceAll('豬', '猪')
}
