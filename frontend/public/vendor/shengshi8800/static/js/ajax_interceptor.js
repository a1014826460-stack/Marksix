// Plan B: request dedup cache + XHR tracking for abort
window.__moduleXHRs = window.__moduleXHRs || [];
window.__moduleRequestCache = window.__moduleRequestCache || new Map();
window.__legacyRevealGate = window.__legacyRevealGate || null;

function legacyAjaxDebugLog(eventName, payload) {
    if (!(window.__LEGACY_EMBED_CONFIG__ && window.__LEGACY_EMBED_CONFIG__.debug)) return;
    if (typeof console === "undefined" || typeof console.log !== "function") return;
    console.log("[legacy-ajax]", eventName, payload || {});
}

function normalizeLegacyIssue(issue) {
    var text = String(issue || '').trim();
    if (!text) return '';
    if (text.length <= 4) return text;
    return text.slice(0, 4) + text.slice(4).replace(/^0+/, '') || '0';
}

function parseBeijingDateTimeToSeconds(value) {
    var text = String(value || '').trim();
    var match = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})$/.exec(text);
    if (!match) return 0;
    var year = Number(match[1]);
    var month = Number(match[2]);
    var day = Number(match[3]);
    var hour = Number(match[4]);
    var minute = Number(match[5]);
    var second = Number(match[6]);
    return Math.floor(Date.UTC(year, month - 1, day, hour - 8, minute, second) / 1000);
}

function resolveLegacyTypeForGate() {
    try {
        if (window.__LEGACY_GAME_STATE__ && typeof window.__LEGACY_GAME_STATE__.getType === 'function') {
            return Number(window.__LEGACY_GAME_STATE__.getType()) || 3;
        }
    } catch (_) {}
    if (typeof window.type !== 'undefined') {
        return Number(window.type) || 3;
    }
    return 3;
}

function setLegacyRevealGate(gate) {
    window.__legacyRevealGate = gate || null;
    legacyAjaxDebugLog('reveal-gate:set', gate || {});
}

function clearLegacyRevealGate() {
    window.__legacyRevealGate = null;
    legacyAjaxDebugLog('reveal-gate:clear');
}

function normalizeIssueText(issue) {
    var text = String(issue || '').trim();
    if (!text) return '';
    return text.length > 4 ? text.slice(0, 4) + text.slice(4).replace(/^0+/, '') : text;
}

function normalizeGateIssue(issue) {
    var text = normalizeIssueText(issue);
    return text;
}

function rowMatchesRevealGate(row, revealGate) {
    if (!row || !revealGate) return false;
    var rowIssue = normalizeIssueText(row.issue || row.term || row.current_issue);
    var gateIssue = normalizeGateIssue(revealGate.issue);
    if (!rowIssue || !gateIssue) return false;
    return rowIssue === gateIssue;
}

function applyRevealMask(data, revealGate) {
    if (!revealGate || !data || !data.data || !(data.data instanceof Array)) return data;
    data.data.forEach(function(row) {
        if (!rowMatchesRevealGate(row, revealGate)) return;
        row.res_code = '';
        row.res_sx = '';
    });
    return data;
}

function updateLegacyRevealGateFromPayload(payload) {
    if (!payload || !payload.current_issue || !payload.draw_time) return;
    var drawTimeSec = parseBeijingDateTimeToSeconds(payload.draw_time);
    if (!(drawTimeSec > 0)) return;
    var unlockAtSec = drawTimeSec + (25 * 6);
    var nowSec = Math.floor(Date.now() / 1000);
    if (!(unlockAtSec > nowSec)) return;
    setLegacyRevealGate({
        lotteryType: resolveLegacyTypeForGate(),
        issue: normalizeLegacyIssue(payload.current_issue),
        unlockAt: unlockAtSec
    });
}

window.__legacyUpdateRevealGateFromPayload = updateLegacyRevealGateFromPayload;
window.__legacyClearRevealGate = clearLegacyRevealGate;

window.addEventListener('message', function(event) {
    var data = event && event.data ? event.data : null;
    if (!data || typeof data !== 'object') return;
    if (data.kind !== 'legacy-draw-reveal-complete') return;
    clearLegacyRevealGate();
});

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

    var revealGate = window.__legacyRevealGate;
    if (revealGate && revealGate.issue && revealGate.unlockAt) {
        try {
            var absoluteUrl = new URL(options.url, window.location.origin);
            absoluteUrl.searchParams.set('presentation_mask', '1');
            absoluteUrl.searchParams.set('presentation_issue', revealGate.issue);
            absoluteUrl.searchParams.set('presentation_unlock_at', String(revealGate.unlockAt));
            absoluteUrl.searchParams.set('presentation_lottery_type', String(revealGate.lotteryType || resolveLegacyTypeForGate()));
            options.url = absoluteUrl.pathname + absoluteUrl.search;
        } catch (_) {}
    }

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
        data = applyRevealMask(data, window.__legacyRevealGate);
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
