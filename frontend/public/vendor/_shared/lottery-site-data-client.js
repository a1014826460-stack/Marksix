(function (window) {
  "use strict";

  var STORAGE_PREFIX = "liuhecai:site-data:v1:";
  // Bump this value when the cached API envelope or its rendering contract changes.
  var PERSISTENT_CACHE_VERSION = "v1";
  var PERSISTENT_STORAGE_PREFIX = "liuhecai:site-data:durable:" + PERSISTENT_CACHE_VERSION + ":";
  var POLICIES = {
    draw: { freshMs: 5000, staleMs: 60000 },
    predictions: { freshMs: 60000, staleMs: 900000, durableMs: 86400000 }
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
      normalized.includeVendor = query && query.includeVendor === false ? false : true;
    }
    return normalized;
  }

  function storageKey(siteKey, resource, query) {
    return STORAGE_PREFIX + siteKey + ":" + resource + ":" + JSON.stringify(query);
  }

  function readCache(storage, key) {
    try {
      var raw = storage && storage.getItem(key);
      if (!raw) return null;
      var cached = JSON.parse(raw);
      if (!cached || typeof cached.cachedAt !== "number" || !("data" in cached)) return null;
      return cached;
    } catch (_) {
      return null;
    }
  }

  function writeCache(storage, key, data) {
    try {
      if (!storage) return;
      storage.setItem(key, JSON.stringify({ cachedAt: Date.now(), data: data }));
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

  function durableCacheResult(cached, policy, now) {
    if (!cached) return null;
    var age = Math.max(0, now - cached.cachedAt);
    if (age <= policy.freshMs) {
      return { state: "ready", data: cached.data, source: "local-storage" };
    }
    if (age <= policy.durableMs) {
      return { state: "stale", data: cached.data, source: "local-storage" };
    }
    return null;
  }

  function buildUrl(siteKey, resource, query) {
    var params = new window.URLSearchParams({ lottery_type: String(query.lotteryType) });
    if (resource === "predictions") {
      params.set("history_limit", String(query.historyLimit));
      if (!query.includeVendor) params.set("include_vendor", "0");
    }
    var endpoint = resource === "predictions" ? "prediction-modules" : resource;
    return "/api/sites/" + encodeURIComponent(siteKey) + "/" + endpoint + "?" + params.toString();
  }

  function create(options) {
    var siteKey = String(options && options.siteKey || "").trim();
    if (!siteKey) throw new Error("siteKey is required");

    function load(resource, query) {
      var normalizedQuery = normalizeQuery(resource, query);
      var policy = POLICIES[resource];
      var key = storageKey(siteKey, resource, normalizedQuery);
      var cached = readCache(window.sessionStorage, key);
      var fromCache = cacheResult(cached, policy, Date.now());
      if (fromCache && fromCache.state === "ready") return Promise.resolve(fromCache);
      var durableKey = PERSISTENT_STORAGE_PREFIX + siteKey + ":" + resource + ":" + JSON.stringify(normalizedQuery);
      var durable = resource === "predictions"
        ? durableCacheResult(readCache(window.localStorage, durableKey), policy, Date.now())
        : null;
      if (durable && durable.state === "ready") return Promise.resolve(durable);

      var requestKey = siteKey + ":" + resource + ":" + JSON.stringify(normalizedQuery);
      if (inFlight[requestKey]) return inFlight[requestKey];

      inFlight[requestKey] = window.fetch(buildUrl(siteKey, resource, normalizedQuery), {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      }).then(function (response) {
        if (!response || !response.ok) throw new Error("request failed");
        return response.json();
      }).then(function (data) {
        writeCache(window.sessionStorage, key, data);
        if (resource === "predictions") writeCache(window.localStorage, durableKey, data);
        return { state: "ready", data: data, source: "network" };
      }).catch(function (error) {
        if (fromCache && fromCache.state === "stale") return fromCache;
        return durable || errorResult(error);
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
        if (resource !== "predictions") return;
        var durablePrefix = PERSISTENT_STORAGE_PREFIX + siteKey + ":" + resource + ":";
        try {
          for (var durableIndex = window.localStorage.length - 1; durableIndex >= 0; durableIndex -= 1) {
            var durableKey = window.localStorage.key(durableIndex);
            if (durableKey && durableKey.indexOf(durablePrefix) === 0) window.localStorage.removeItem(durableKey);
          }
        } catch (_) {
          // Persistent storage may be unavailable in private browsing.
        }
      }
    };
  }

  window.LotterySiteDataClient = { create: create };
})(window);
