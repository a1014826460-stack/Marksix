(function (window, document) {
  "use strict";

  var script = document.currentScript || {};
  var siteKey = (script.dataset && script.dataset.siteKey) || "";
  var state = { config: null, draw: "idle", prediction: "idle" };

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

  function request(path, phase) {
    if (!siteKey) return Promise.reject(errorFor("CONFIG", "site key is required", false));
    state[phase] = "loading";
    emit("lottery:" + phase + "-loading", { site_key: siteKey });
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timeout = controller ? setTimeout(function () { controller.abort(); }, 10000) : null;
    return fetch(path, {
      cache: "no-store",
      signal: controller ? controller.signal : undefined
    }).then(function (response) {
      if (!response.ok) {
        return readError(response).then(function (message) {
          throw errorFor("BACKEND", message, response.status >= 500);
        });
      }
      return response.json();
    }).then(function (payload) {
      if (!payload || payload.ok !== true || !payload.data) {
        throw errorFor("BAD_RESPONSE", "Invalid site bridge response", false);
      }
      state[phase] = "ready";
      emit("lottery:" + phase + "-ready", { site_key: siteKey, data: payload.data });
      return payload.data;
    }).catch(function (error) {
      var normalized = error && error.code
        ? error
        : errorFor(error && error.name === "AbortError" ? "TIMEOUT" : "NETWORK", error && error.message, true);
      state[phase] = "error";
      emit("lottery:error", { site_key: siteKey, phase: phase, error: normalized });
      throw normalized;
    }).finally(function () {
      if (timeout) clearTimeout(timeout);
    });
  }

  function applyConfig(config) {
    state.config = config;
    if (window.LEGACY_TWSAIMAHUI_RUNTIME && typeof window.LEGACY_TWSAIMAHUI_RUNTIME.applyBridgeConfig === "function") {
      window.LEGACY_TWSAIMAHUI_RUNTIME.applyBridgeConfig(config);
    }
    emit("lottery:bridge-ready", { site_key: siteKey, config: config });
    return config;
  }

  var bridge = {
    state: state,
    ready: request("/api/sites/" + encodeURIComponent(siteKey) + "/bridge-config", "config").then(applyConfig),
    getPredictionModules: function (query) {
      return request("/api/sites/" + encodeURIComponent(siteKey) + "/prediction-modules" + (query || ""), "prediction");
    },
    getDraw: function (query) {
      return request("/api/sites/" + encodeURIComponent(siteKey) + "/draw" + (query || ""), "draw");
    }
  };

  window.LotterySiteBridge = bridge;
})(window, document);
