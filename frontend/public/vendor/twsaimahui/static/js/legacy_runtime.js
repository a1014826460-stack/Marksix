(function (window) {
  var SITE_KEY = "twsaimahui";
  var VENDOR_MARKER = "/vendor/twsaimahui/";

  function normalizeBase(value) {
    if (typeof value !== "string") {
      return "";
    }
    return value.replace(/\/+$/, "");
  }

  function normalizeHost(value) {
    if (typeof value !== "string") {
      return "";
    }
    return value.trim().toLowerCase().replace(/:\d+$/, "");
  }

  function normalizePathPrefix(value) {
    if (typeof value !== "string") {
      return "";
    }
    var trimmed = value.trim();
    if (!trimmed || trimmed === "/") {
      return "";
    }
    trimmed = trimmed.replace(/^[a-z]+:\/\/[^/]+/i, "");
    trimmed = "/" + trimmed.replace(/^\/+/, "").replace(/\/+$/, "");
    return trimmed === "/" ? "" : trimmed;
  }

  function ensureLeadingSlash(value) {
    var text = String(value || "");
    return text.charAt(0) === "/" ? text : "/" + text;
  }

  function readQuery(name) {
    try {
      return new URLSearchParams(window.location.search || "").get(name) || "";
    } catch (_) {
      return "";
    }
  }

  function readStringCandidate() {
    for (var i = 0; i < arguments.length; i++) {
      var value = arguments[i];
      if (typeof value === "string" && value.trim()) {
        return value.trim();
      }
    }
    return "";
  }

  function resolveOrigin() {
    if (window.location && typeof window.location.origin === "string" && window.location.origin) {
      return window.location.origin;
    }
    var protocol = window.location && window.location.protocol ? window.location.protocol : "http:";
    var host = window.location && window.location.host ? window.location.host : "";
    return protocol + "//" + host;
  }

  function inferAppBasePath() {
    var explicit = normalizePathPrefix(
      readStringCandidate(
        window.__LEGACY_APP_BASE_PATH__,
        window.__TWSAIMAHUI_APP_BASE_PATH__,
        readQuery("app_base")
      )
    );

    if (explicit) {
      return explicit;
    }

    var pathname = window.location && typeof window.location.pathname === "string"
      ? window.location.pathname
      : "";
    var vendorIndex = pathname.indexOf(VENDOR_MARKER);
    if (vendorIndex >= 0) {
      return normalizePathPrefix(pathname.slice(0, vendorIndex));
    }

    return "";
  }

  function buildAppPath(path) {
    return appBasePath + ensureLeadingSlash(path || "/");
  }

  function buildAppUrl(path) {
    return origin + buildAppPath(path);
  }

  function buildVendorPath(path) {
    var cleanPath = String(path || "").replace(/^\/+/, "");
    return buildAppPath("/vendor/twsaimahui/" + cleanPath);
  }

  function buildVendorUrl(path) {
    return origin + buildVendorPath(path);
  }

  function inferSourceFromHost(hostname) {
    if (/(^|\.)shengshi8800\.com$/i.test(hostname)) {
      return "shengshi8800";
    }
    if (/(^|\.)twsaimahui\.com$/i.test(hostname)) {
      return "twsaimahui";
    }
    return SITE_KEY;
  }

  function appendSearchParams(searchParams, data) {
    if (!data) {
      return;
    }

    if (typeof URLSearchParams !== "undefined" && data instanceof URLSearchParams) {
      data.forEach(function (value, key) {
        searchParams.append(key, value);
      });
      return;
    }

    if (typeof data === "string") {
      new URLSearchParams(data).forEach(function (value, key) {
        searchParams.append(key, value);
      });
      return;
    }

    if (Object.prototype.toString.call(data) === "[object Array]") {
      for (var i = 0; i < data.length; i++) {
        var item = data[i] || {};
        if (item.name) {
          searchParams.append(item.name, item.value == null ? "" : String(item.value));
        }
      }
      return;
    }

    for (var key in data) {
      if (!Object.prototype.hasOwnProperty.call(data, key)) {
        continue;
      }
      var value = data[key];
      if (value == null || value === "") {
        continue;
      }
      searchParams.append(key, String(value));
    }
  }

  function extendSiteParams(searchParams) {
    if (!searchParams.get("source")) {
      searchParams.set("source", siteSource);
    }
    if (!searchParams.get("domain")) {
      searchParams.set("domain", currentHost);
    }
    if (!searchParams.get("site_key")) {
      searchParams.set("site_key", SITE_KEY);
    }
    if (!searchParams.get("hostname")) {
      searchParams.set("hostname", currentHost);
    }
  }

  function isKaijiangRequest(url) {
    return String(url || "").indexOf("/api/kaijiang") !== -1;
  }

  function parseKaijiangPath(url) {
    var raw = String(url || "");
    var urlObject = new URL(raw, origin);
    var markerIndex = urlObject.pathname.indexOf("/api/kaijiang");
    var endpointPath = markerIndex >= 0
      ? urlObject.pathname.slice(markerIndex + "/api/kaijiang".length)
      : urlObject.pathname;

    return {
      endpointPath: endpointPath || "",
      search: urlObject.search || ""
    };
  }

  function buildKaijiangUrl(url, data) {
    var parsed = parseKaijiangPath(url);
    var searchParams = new URLSearchParams(parsed.search || "");
    appendSearchParams(searchParams, data);
    extendSiteParams(searchParams);

    var endpointPath = parsed.endpointPath || "";
    if (endpointPath && endpointPath.charAt(0) !== "/") {
      endpointPath = "/" + endpointPath;
    }

    var finalUrl = kaijiangApiBase + endpointPath;
    var queryString = searchParams.toString();
    return queryString ? finalUrl + "?" + queryString : finalUrl;
  }

  function buildHistoryUrl(lotteryType, extraParams) {
    var searchParams = new URLSearchParams();
    searchParams.set("type", String(lotteryType || ""));
    appendSearchParams(searchParams, extraParams);
    return buildAppUrl("/history?" + searchParams.toString());
  }

  var origin = resolveOrigin();
  var appBasePath = inferAppBasePath();
  var appBaseUrl = normalizeBase(origin) + appBasePath;
  var currentHost = normalizeHost(window.location && window.location.hostname);
  var siteSource = readStringCandidate(
    window.__TWSAIMAHUI_SOURCE__,
    readQuery("source")
  ) || inferSourceFromHost(currentHost);
  var httpApiBase = normalizeBase(
    readStringCandidate(
      window.__LOTTERY_API_BASE__,
      window.__TWSAIMAHUI_HTTP_API_BASE__,
      readQuery("api_base"),
      readQuery("http_api_base")
    )
  ) || appBaseUrl;
  var kaijiangApiBase = normalizeBase(
    readStringCandidate(
      window.__LEGACY_KAIJIANG_API_BASE__,
      window.__TWSAIMAHUI_KAIJIANG_API_BASE__,
      readQuery("kaijiang_api_base")
    )
  ) || buildAppUrl("/api/kaijiang");

  window.LEGACY_TWSAIMAHUI_RUNTIME = {
    siteKey: SITE_KEY,
    source: siteSource,
    hostname: currentHost,
    appBasePath: appBasePath,
    appBaseUrl: appBaseUrl,
    httpApiBase: httpApiBase,
    kaijiangApiBase: kaijiangApiBase,
    getHttpApiBase: function () {
      return httpApiBase;
    },
    getKaijiangApiBase: function () {
      return kaijiangApiBase;
    },
    getSiteParams: function () {
      return {
        source: siteSource,
        domain: currentHost,
        site_key: SITE_KEY,
        hostname: currentHost
      };
    },
    buildAppPath: buildAppPath,
    buildAppUrl: buildAppUrl,
    buildVendorPath: buildVendorPath,
    buildVendorUrl: buildVendorUrl,
    buildHistoryUrl: buildHistoryUrl,
    buildKaijiangUrl: buildKaijiangUrl,
    isKaijiangRequest: isKaijiangRequest
  };

  window.__LOTTERY_API_BASE__ = httpApiBase;
  window.__LEGACY_KAIJIANG_API_BASE__ = kaijiangApiBase;
})(window);
