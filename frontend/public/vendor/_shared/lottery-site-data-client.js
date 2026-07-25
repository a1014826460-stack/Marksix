(function (window) {
  "use strict";

  var STORAGE_PREFIX = "liuhecai:site-data:v1:";
  var POLICIES = {
    draw: { freshMs: 5000, staleMs: 60000 },
    predictions: { freshMs: 60000, staleMs: 900000 }
  };
  var inFlight = {};

  function normalizeNumber(value, fallback) {
    var number = Number(value);
    return Number.isFinite(number) && number > 0 ? Math.floor(number) : fallback;
  }

  function normalizeQuery(resource, query) {
    var normalized = {
      lotteryType: normalizeNumber(query && query.lotteryType, 3)
    };
    if (resource === "predictions") {
      normalized.historyLimit = normalizeNumber(query && query.historyLimit, 8);
    }
    return normalized;
  }

  function storageKey(siteKey, resource, query) {
    return STORAGE_PREFIX + siteKey + ":" + resource + ":" + JSON.stringify(query);
  }

  function readCache(key) {
    try {
      var raw = window.sessionStorage && window.sessionStorage.getItem(key);
      if (!raw) return null;
      var cached = JSON.parse(raw);
      if (!cached || typeof cached.cachedAt !== "number" || !("data" in cached)) return null;
      return cached;
    } catch (_) {
      return null;
    }
  }

  function writeCache(key, data) {
    try {
      if (!window.sessionStorage) return;
      window.sessionStorage.setItem(key, JSON.stringify({ cachedAt: Date.now(), data: data }));
    } catch (_) {
      // Private browsing or quota errors must not affect the legacy renderer.
    }
  }

  function errorResult(error) {
    return {
      state: "error",
      error: {
        message: error && error.message ? String(error.message) : "request failed",
        retryable: true
      },
      source: "network"
    };
  }

  function cacheResult(cached, policy, now) {
    if (!cached) return null;
    var age = Math.max(0, now - cached.cachedAt);
    if (age <= policy.freshMs) {
      return { state: "ready", data: cached.data, source: "session-storage" };
    }
    if (age <= policy.staleMs) {
      return { state: "stale", data: cached.data, source: "session-storage" };
    }
    return null;
  }

  function buildUrl(siteKey, resource, query) {
    var params = new window.URLSearchParams({ lottery_type: String(query.lotteryType) });
    if (resource === "predictions") params.set("history_limit", String(query.historyLimit));
    return "/api/sites/" + encodeURIComponent(siteKey) + "/" + resource + "?" + params.toString();
  }

  function create(options) {
    var siteKey = String(options && options.siteKey || "").trim();
    if (!siteKey) throw new Error("siteKey is required");

    function load(resource, query) {
      var normalizedQuery = normalizeQuery(resource, query);
      var policy = POLICIES[resource];
      var key = storageKey(siteKey, resource, normalizedQuery);
      var cached = readCache(key);
      var fromCache = cacheResult(cached, policy, Date.now());
      if (fromCache && fromCache.state === "ready") return Promise.resolve(fromCache);

      var requestKey = siteKey + ":" + resource + ":" + JSON.stringify(normalizedQuery);
      if (inFlight[requestKey]) return inFlight[requestKey];

      inFlight[requestKey] = window.fetch(buildUrl(siteKey, resource, normalizedQuery), {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      }).then(function (response) {
        if (!response || !response.ok) throw new Error("request failed");
        return response.json();
      }).then(function (data) {
        writeCache(key, data);
        return { state: "ready", data: data, source: "network" };
      }).catch(function (error) {
        return fromCache && fromCache.state === "stale" ? fromCache : errorResult(error);
      }).finally(function () {
        delete inFlight[requestKey];
      });

      return inFlight[requestKey];
    }

    return {
      loadDraw: function (query) { return load("draw", query); },
      loadPredictions: function (query) { return load("predictions", query); },
      clear: function (resource) {
        if (resource !== "draw" && resource !== "predictions") return;
        var prefix = STORAGE_PREFIX + siteKey + ":" + resource + ":";
        try {
          for (var index = window.sessionStorage.length - 1; index >= 0; index -= 1) {
            var key = window.sessionStorage.key(index);
            if (key && key.indexOf(prefix) === 0) window.sessionStorage.removeItem(key);
          }
        } catch (_) {
          // Storage cleanup is best effort.
        }
      }
    };
  }

  window.LotterySiteDataClient = { create: create };
})(window);
