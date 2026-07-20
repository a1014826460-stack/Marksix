(function (window, document) {
  "use strict";

  var script = document.currentScript || {};
  var siteKey = (script.dataset && script.dataset.siteKey) || "";
  var CACHE_POLICY = {
    config: { fresh: 300000, stale: 1800000 },
    draw: { fresh: 20000, stale: 120000 },
    prediction: { fresh: 300000, stale: 1800000 }
  };
  var state = { config: null, draw: "idle", prediction: "idle" };
  var memory = {};
  var inFlight = {};

  function emit(name, detail) {
    window.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
  }

  function errorFor(code, message, retryable) {
    return { code: code, message: message || "Request failed", retryable: Boolean(retryable) };
  }

  function readError(response) {
    return response.json().catch(function () { return {}; }).then(function (payload) {
      var source = payload && payload.error;
      if (source && typeof source === "object") return source.message || "Request failed";
      return typeof source === "string" ? source : "Request failed with status " + response.status;
    });
  }

  function canonicalQuery(query) {
    return String(query || "").replace(/^\?/, "");
  }

  function cacheKey(phase, query) {
    return "lottery-site-bridge:" + siteKey + ":" + phase + ":" + canonicalQuery(query);
  }

  function readCache(key) {
    if (memory[key]) return memory[key];
    try {
      var raw = window.sessionStorage && window.sessionStorage.getItem(key);
      if (raw) {
        var parsed = JSON.parse(raw);
        if (parsed && typeof parsed.at === "number" && parsed.data) {
          memory[key] = parsed;
          return parsed;
        }
      }
    } catch (_) {}
    return null;
  }

  function writeCache(key, data) {
    var entry = { at: Date.now(), data: data };
    memory[key] = entry;
    try {
      if (window.sessionStorage) window.sessionStorage.setItem(key, JSON.stringify(entry));
    } catch (_) {}
    return entry;
  }

  function applyConfig(config) {
    state.config = config;
    if (window.LEGACY_TWSAIMAHUI_RUNTIME && typeof window.LEGACY_TWSAIMAHUI_RUNTIME.applyBridgeConfig === "function") {
      window.LEGACY_TWSAIMAHUI_RUNTIME.applyBridgeConfig(config);
    }
    emit("lottery:bridge-ready", { site_key: siteKey, config: config });
    return config;
  }

  function fetchResource(path, phase, query, key) {
    state[phase] = "loading";
    emit("lottery:" + phase + "-loading", { site_key: siteKey, cached: false });
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timeout = controller ? setTimeout(function () { controller.abort(); }, 10000) : null;
    return fetch(path, { cache: "no-store", signal: controller ? controller.signal : undefined })
      .then(function (response) {
        if (!response.ok) return readError(response).then(function (message) { throw errorFor("BACKEND", message, response.status >= 500); });
        return response.json();
      })
      .then(function (payload) {
        if (!payload || payload.ok !== true || !payload.data) throw errorFor("BAD_RESPONSE", "Invalid site bridge response", false);
        var data = payload.data;
        writeCache(key, data);
        state[phase] = "ready";
        emit("lottery:" + phase + "-ready", { site_key: siteKey, data: data, cached: false, stale: false });
        return data;
      })
      .catch(function (error) {
        var normalized = error && error.code ? error : errorFor(error && error.name === "AbortError" ? "TIMEOUT" : "NETWORK", error && error.message, true);
        state[phase] = "error";
        emit("lottery:error", { site_key: siteKey, phase: phase, error: normalized });
        throw normalized;
      })
      .finally(function () {
        delete inFlight[key];
        if (timeout) clearTimeout(timeout);
      });
  }

  function request(path, phase, query) {
    if (!siteKey) return Promise.reject(errorFor("CONFIG", "site key is required", false));
    var key = cacheKey(phase, query);
    var policy = CACHE_POLICY[phase] || CACHE_POLICY.prediction;
    var cached = readCache(key);
    var age = cached ? Date.now() - cached.at : Infinity;
    if (cached && age <= policy.fresh) {
      state[phase] = "ready";
      emit("lottery:" + phase + "-ready", { site_key: siteKey, data: cached.data, cached: true, stale: false });
      return Promise.resolve(cached.data);
    }
    if (!inFlight[key]) inFlight[key] = fetchResource(path, phase, query, key);
    if (cached && age <= policy.stale) {
      state[phase] = "ready";
      emit("lottery:" + phase + "-stale", { site_key: siteKey, data: cached.data, cached: true, stale: true });
      inFlight[key].catch(function () {});
      return Promise.resolve(cached.data);
    }
    return inFlight[key];
  }

  function sitePath(resource, query) {
    return "/api/sites/" + encodeURIComponent(siteKey) + "/" + resource + (query ? "?" + canonicalQuery(query) : "");
  }

  var bridge = {
    state: state,
    ready: request(sitePath("bridge-config"), "config", "").then(applyConfig),
    getPredictionModules: function (query) { return request(sitePath("prediction-modules", query), "prediction", query); },
    getDraw: function (query) { return request(sitePath("draw", query), "draw", query); }
  };

  window.LotterySiteBridge = bridge;
})(window, document);
