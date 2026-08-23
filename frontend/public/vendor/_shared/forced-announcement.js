(function (window, document) {
  "use strict";

  var SESSION_PREFIX = "forced-announcement:session:";
  var CONFIRMED_PREFIX = "forced-announcement:confirmed:";
  // Vendor resources retain historical directory names, while the backend
  // resolves announcements by the registered manifest site key. Do not depend
  // on Host for iframe/static pages: their URL provides a stable identity.
  var VENDOR_SITE_KEYS = {
    "shengshi8800": "shengshi8800",
    "twsaimahui": "twsaimahui",
    "twcaibawang.com": "twcaibawang",
    "twjinniu": "twjinniu",
    "twcf888.com": "twcf888",
    "twssz": "twssz",
    "twbst528": "twbst528",
    "twjsz666": "twjsz666",
    "twwanli": "twwanli",
    "twsyw": "twsyw"
  };
  var REGISTERED_SITE_KEYS = {
    "shengshi8800": true,
    "twsaimahui": true,
    "twcaibawang": true,
    "twjinniu": true,
    "twcf888": true,
    "twssz": true,
    "twbst528": true,
    "twjsz666": true,
    "twwanli": true,
    "twsyw": true
  };
  var REGISTERED_HOSTS = {
    "www.tw8800.com": true,
    "www.twsaimahui.com": true,
    "www.twcaibawang.com": true,
    "www.twjinniu.com": true,
    "www.twcf888.com": true,
    "www.twssz.com": true,
    "www.twbst528.com": true,
    "www.twjsz666.com": true,
    "www.twwanli.com": true,
    "www.twsyw.com": true
  };
  var mountedPromise = null;
  var activeSiteKey = "";

  function storageHas(storage, key) {
    try {
      return Boolean(storage && storage.getItem(key));
    } catch (_) {
      return false;
    }
  }

  function storageSet(storage, key) {
    try {
      if (storage) storage.setItem(key, "1");
    } catch (_) {
      // Storage can be unavailable in private browsing; the page remains usable.
    }
  }

  function versionOf(announcement) {
    return String(announcement && announcement.version || "").trim();
  }

  function storageKey(prefix, version, siteKey) {
    var scope = String(siteKey || "").trim().toLowerCase();
    if (!scope && window.location) scope = String(window.location.host || "").trim().toLowerCase();
    return prefix + (scope || "default") + ":" + version;
  }

  function shouldDisplay(announcement, siteKey) {
    var version = versionOf(announcement);
    if (!version) return false;
    var resolvedSiteKey = siteKey || activeSiteKey || resolveSiteKey();
    return !storageHas(window.sessionStorage, storageKey(SESSION_PREFIX, version, resolvedSiteKey))
      && !storageHas(window.localStorage, storageKey(CONFIRMED_PREFIX, version, resolvedSiteKey));
  }

  function installStyles() {
    if (document.getElementById("forced-announcement-style")) return;
    var style = document.createElement("style");
    style.id = "forced-announcement-style";
    style.textContent = [
      ".forced-announcement-overlay{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;padding:16px;background:rgba(0,0,0,.62);font-family:Arial,\"Microsoft JhengHei\",sans-serif}",
      ".forced-announcement-dialog{position:relative;width:min(520px,100%);max-height:min(80vh,680px);overflow:auto;border:1px solid #d8d8d8;border-radius:8px;background:#fff;color:#222;box-shadow:0 16px 48px rgba(0,0,0,.28)}",
      ".forced-announcement-header{display:flex;min-height:52px;align-items:center;justify-content:space-between;gap:12px;padding:12px 12px 12px 18px;border-bottom:1px solid #e7e7e7}",
      ".forced-announcement-title{min-width:0;margin:0;font-size:20px;line-height:1.4;font-weight:700;overflow-wrap:anywhere;letter-spacing:0}",
      ".forced-announcement-close{display:inline-flex;width:40px;height:40px;flex:0 0 40px;align-items:center;justify-content:center;border:0;background:transparent;color:#555;font-size:28px;line-height:1;cursor:pointer}",
      ".forced-announcement-close:hover,.forced-announcement-close:focus-visible{background:#f1f1f1;color:#111;outline:2px solid #222;outline-offset:-2px}",
      ".forced-announcement-content{padding:18px;font-size:16px;line-height:1.75;overflow-wrap:anywhere}",
      ".forced-announcement-content p:first-child{margin-top:0}.forced-announcement-content p:last-child{margin-bottom:0}",
      ".forced-announcement-content a{color:#075bb5;text-decoration:underline}",
      ".forced-announcement-actions{display:flex;justify-content:flex-end;padding:12px 18px 18px}",
      ".forced-announcement-confirm{min-height:44px;border:1px solid #9d1821;border-radius:6px;padding:10px 18px;background:#b51f2a;color:#fff;font-size:15px;font-weight:700;letter-spacing:0;cursor:pointer}",
      ".forced-announcement-confirm:hover,.forced-announcement-confirm:focus-visible{background:#941821;outline:2px solid #222;outline-offset:2px}",
      "@media (max-width:480px){.forced-announcement-overlay{align-items:flex-end;padding:10px}.forced-announcement-dialog{max-height:88vh}.forced-announcement-title{font-size:18px}.forced-announcement-content{padding:16px;font-size:15px}.forced-announcement-actions{padding:10px 16px 16px}.forced-announcement-confirm{width:100%}}"
    ].join("");
    document.head.appendChild(style);
  }

  function closeOverlay(overlay) {
    if (overlay && typeof overlay.remove === "function") overlay.remove();
  }

  function render(announcement, siteKey) {
    if (!shouldDisplay(announcement, siteKey)) return null;
    installStyles();

    var version = versionOf(announcement);
    var overlay = document.createElement("div");
    overlay.className = "forced-announcement-overlay";

    var dialog = document.createElement("section");
    dialog.className = "forced-announcement-dialog";
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-labelledby", "forced-announcement-title");

    var header = document.createElement("header");
    header.className = "forced-announcement-header";
    var title = document.createElement("h2");
    title.id = "forced-announcement-title";
    title.className = "forced-announcement-title";
    title.textContent = String(announcement.title || "");
    header.appendChild(title);

    var close = document.createElement("button");
    close.type = "button";
    close.className = "forced-announcement-close";
    close.dataset.action = "session-close";
    close.setAttribute("aria-label", "关闭公告，本次会话不再提示");
    close.setAttribute("title", "关闭");
    close.textContent = "\u00d7";
    close.addEventListener("click", function () {
      storageSet(window.sessionStorage, storageKey(SESSION_PREFIX, version, siteKey));
      closeOverlay(overlay);
    });
    header.appendChild(close);
    dialog.appendChild(header);

    var content = document.createElement("div");
    content.className = "forced-announcement-content";
    content.innerHTML = String(announcement.html || "");
    dialog.appendChild(content);

    var actions = document.createElement("footer");
    actions.className = "forced-announcement-actions";
    var confirm = document.createElement("button");
    confirm.type = "button";
    confirm.className = "forced-announcement-confirm";
    confirm.dataset.action = "confirm";
    confirm.textContent = "我已确认，不再提示";
    confirm.addEventListener("click", function () {
      storageSet(window.localStorage, storageKey(CONFIRMED_PREFIX, version, siteKey));
      closeOverlay(overlay);
    });
    actions.appendChild(confirm);
    dialog.appendChild(actions);
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
    return overlay;
  }

  function resolveSiteKey(options) {
    var bodyData = document.body && document.body.dataset || {};
    var siteKey = String(options && options.siteKey || "").trim();
    if (!siteKey && window.location) {
      var vendorMatch = String(window.location.pathname || "").match(/^\/vendor\/([^/]+)/i);
      if (vendorMatch) siteKey = VENDOR_SITE_KEYS[vendorMatch[1].toLowerCase()] || "";
    }
    if (!siteKey) siteKey = String(bodyData.siteKey || "").trim();
    if (!siteKey && window.location) {
      var pathSiteKey = String(window.location.pathname || "").split("/")[1] || "";
      if (REGISTERED_SITE_KEYS[pathSiteKey.toLowerCase()]) {
        siteKey = pathSiteKey;
      }
    }
    return REGISTERED_SITE_KEYS[siteKey.toLowerCase()] ? siteKey : "";
  }

  function requestUrl(options, siteKey) {
    var params = new window.URLSearchParams();
    var bodyData = document.body && document.body.dataset || {};
    var siteId = String(options && options.siteId || bodyData.siteId || "").trim();
    if (siteKey) params.set("site_key", siteKey);
    else if (siteId) params.set("site_id", siteId);
    var query = params.toString();
    return "/api/public/forced-announcement" + (query ? "?" + query : "");
  }

  function mount(options) {
    if (mountedPromise) return mountedPromise;
    var siteKey = resolveSiteKey(options);
    var host = String(window.location && window.location.host || "").toLowerCase().split(":")[0];
    if (!siteKey && !(options && options.siteId) && !REGISTERED_HOSTS[host]) return Promise.resolve(null);
    var canonicalSiteKey = siteKey;
    activeSiteKey = siteKey;
    mountedPromise = window.fetch(requestUrl(options, siteKey), {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      cache: "no-store"
    }).then(function (response) {
      if (!response || !response.ok) throw new Error("request failed");
      if (response.headers && typeof response.headers.get === "function") {
        canonicalSiteKey = String(response.headers.get("X-Announcement-Site-Key") || siteKey).trim();
      }
      activeSiteKey = canonicalSiteKey;
      return response.json();
    }).then(function (announcement) {
      if (!announcement || typeof announcement !== "object") return null;
      if (typeof announcement.version !== "string") return null;
      if (typeof announcement.title !== "string") return null;
      if (typeof announcement.html !== "string") return null;
      return render(announcement, canonicalSiteKey);
    }).catch(function () {
      return null;
    });
    return mountedPromise;
  }

  window.ForcedAnnouncement = {
    mount: mount,
    shouldDisplay: shouldDisplay
  };

  function autoMount() {
    if (window.parent && window.parent !== window) {
      try {
        // Exactly one document in a same-origin frame tree owns the overlay.
        // Do not race the parent runtime: the highest same-origin ancestor will
        // mount even if its ForcedAnnouncement global is not initialized yet.
        void window.parent.document;
        return;
      } catch (_) {
        // A cross-origin parent cannot coordinate, so mount in this document.
      }
    }
    mount();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoMount, { once: true });
  } else {
    autoMount();
  }
})(window, document);
