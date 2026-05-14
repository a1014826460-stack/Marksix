// Plan B: request dedup cache + XHR tracking for abort
window.__moduleXHRs = window.__moduleXHRs || [];
window.__moduleRequestCache = window.__moduleRequestCache || new Map();

function legacyAjaxDebugLog(eventName, payload) {
    if (!(window.__LEGACY_EMBED_CONFIG__ && window.__LEGACY_EMBED_CONFIG__.debug)) return;
    if (typeof console === "undefined" || typeof console.log !== "function") return;
    console.log("[legacy-ajax]", eventName, payload || {});
}

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

    var requestSeq = Number(window.__LEGACY_SWITCH_SEQ__ || 0);
    var originalSuccess = originalOptions.success;
    var originalError = originalOptions.error;
    var originalComplete = originalOptions.complete;

    legacyAjaxDebugLog("request:prepare", {
        url: options.url,
        requestSeq: requestSeq,
        activeSeq: Number(window.__LEGACY_SWITCH_SEQ__ || 0),
    });

    options.success = function(data, textStatus, xhr) {
        if (requestSeq !== Number(window.__LEGACY_SWITCH_SEQ__ || 0)) {
            legacyAjaxDebugLog("request:stale-success", {
                url: options.url,
                requestSeq: requestSeq,
                activeSeq: Number(window.__LEGACY_SWITCH_SEQ__ || 0),
            });
            return;
        }
        legacyAjaxDebugLog("request:success", {
            url: options.url,
            requestSeq: requestSeq,
        });
        if (typeof originalSuccess === "function") {
            return originalSuccess.call(this, data, textStatus, xhr);
        }
    };

    options.error = function(xhr, textStatus, errorThrown) {
        if (textStatus === "abort") return;
        if (requestSeq !== Number(window.__LEGACY_SWITCH_SEQ__ || 0)) {
            legacyAjaxDebugLog("request:stale-error", {
                url: options.url,
                requestSeq: requestSeq,
                activeSeq: Number(window.__LEGACY_SWITCH_SEQ__ || 0),
                textStatus: textStatus,
            });
            return;
        }
        legacyAjaxDebugLog("request:error", {
            url: options.url,
            requestSeq: requestSeq,
            textStatus: textStatus,
        });
        if (typeof originalError === "function") {
            return originalError.call(this, xhr, textStatus, errorThrown);
        }
    };

    options.complete = function(xhr, textStatus) {
        if (requestSeq !== Number(window.__LEGACY_SWITCH_SEQ__ || 0)) {
            legacyAjaxDebugLog("request:stale-complete", {
                url: options.url,
                requestSeq: requestSeq,
                activeSeq: Number(window.__LEGACY_SWITCH_SEQ__ || 0),
                textStatus: textStatus,
            });
            return;
        }
        if (typeof originalComplete === "function") {
            return originalComplete.call(this, xhr, textStatus);
        }
    };

    var cacheKey = options.url;
    var cached = window.__moduleRequestCache.get(cacheKey);
    if (cached && cached.readyState !== 4) {
        legacyAjaxDebugLog("request:dedup-hit", {
            url: options.url,
            requestSeq: requestSeq,
        });
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
    legacyAjaxDebugLog("request:send", {
        url: options.url,
        requestSeq: requestSeq,
    });

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
