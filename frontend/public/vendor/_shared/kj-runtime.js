/**
 * 旧站开奖面板的站点运行时垫片。
 *
 * 共享开奖面板 `/vendor/shengshi8800/kj/local.html` 以 iframe 方式被十个站点引用。
 * 其中只有 twsaimahui 需要把 `/history` 与 `/api/*` 请求改写成它自己的站点 URL
 * （由父页的 `window.LEGACY_TWSAIMAHUI_RUNTIME` 提供）。其它九个站点没有该运行时，
 * 垫片会原样返回以 `/` 开头的路径，行为与引入垫片之前完全一致。
 *
 * 使用方：
 * - `twsaimahui/index.html`：构造开奖 iframe 的地址；
 * - 共享开奖面板 `local.html`：构造 `/history`、`/api/latest-draw`、
 *   `/api/next-draw-deadline`。
 *
 * 运行时在每次调用时惰性解析，因此本文件可以在父页 `legacy_runtime.js`
 * 之前或之后加载，都不影响结果。
 */
(function (global) {
  "use strict";

  var SHARED_VENDOR_BASE = "/vendor/shengshi8800/";

  function resolveDrawRuntime() {
    try {
      if (
        global.parent &&
        global.parent !== global &&
        global.parent.LEGACY_TWSAIMAHUI_RUNTIME
      ) {
        return global.parent.LEGACY_TWSAIMAHUI_RUNTIME;
      }
    } catch (_error) {
      // 跨域父页不可访问，按“没有站点运行时”处理。
    }
    return global.LEGACY_TWSAIMAHUI_RUNTIME || null;
  }

  function resolveAppBasePath() {
    var runtime = resolveDrawRuntime();
    if (runtime && typeof runtime.buildAppPath === "function") {
      try {
        var mapped = String(runtime.buildAppPath(SHARED_VENDOR_BASE));
        var vendorIndex = mapped.indexOf(SHARED_VENDOR_BASE);
        if (vendorIndex >= 0) return mapped.slice(0, vendorIndex);
      } catch (_error) {
        // 落到无前缀。
      }
    }
    return "";
  }

  function buildAppUrl(path) {
    var runtime = resolveDrawRuntime();
    if (runtime && typeof runtime.buildAppUrl === "function") {
      try {
        return String(runtime.buildAppUrl(String(path || "/")));
      } catch (_error) {
        // 落到无前缀。
      }
    }
    var normalized = String(path || "/");
    return normalized.charAt(0) === "/" ? normalized : "/" + normalized;
  }

  function buildHistoryUrl(lotteryType, extraParams) {
    var runtime = resolveDrawRuntime();
    if (runtime && typeof runtime.buildHistoryUrl === "function") {
      var extras = extraParams;
      if (extras === undefined || extras === null) {
        extras = typeof runtime.getSiteParams === "function" ? runtime.getSiteParams() : null;
      }
      try {
        return String(runtime.buildHistoryUrl(lotteryType, extras));
      } catch (_error) {
        // 落到无前缀。
      }
    }

    var params = new URLSearchParams();
    params.set("type", String(lotteryType || ""));
    if (extraParams) {
      for (var key in extraParams) {
        if (Object.prototype.hasOwnProperty.call(extraParams, key) && !params.has(key)) {
          params.set(key, String(extraParams[key]));
        }
      }
    }
    return "/history?" + params.toString();
  }

  function buildVendorPath(path) {
    var clean = String(path || "").replace(/^\/+/, "");
    return resolveAppBasePath() + SHARED_VENDOR_BASE + clean;
  }

  global.LegacyKjRuntime = {
    resolveDrawRuntime: resolveDrawRuntime,
    buildAppUrl: buildAppUrl,
    buildHistoryUrl: buildHistoryUrl,
    buildVendorPath: buildVendorPath,
    sharedPanelPath: SHARED_VENDOR_BASE + "kj/local.html",
  };
})(window);
