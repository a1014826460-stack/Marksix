(function (window, document) {
  "use strict";

  var SESSION_PREFIX = "forced-announcement:session:";
  var CONFIRMED_PREFIX = "forced-announcement:confirmed:";
  var mountedPromise = null;

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

  function shouldDisplay(announcement) {
    var version = versionOf(announcement);
    if (!version) return false;
    return !storageHas(window.sessionStorage, SESSION_PREFIX + version)
      && !storageHas(window.localStorage, CONFIRMED_PREFIX + version);
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

  function render(announcement) {
    if (!shouldDisplay(announcement)) return null;
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
      storageSet(window.sessionStorage, SESSION_PREFIX + version);
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
      storageSet(window.localStorage, CONFIRMED_PREFIX + version);
      closeOverlay(overlay);
    });
    actions.appendChild(confirm);
    dialog.appendChild(actions);
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
    return overlay;
  }

  function requestUrl(options) {
    var params = new window.URLSearchParams();
    var bodyData = document.body && document.body.dataset || {};
    var siteId = String(options && options.siteId || bodyData.siteId || "").trim();
    var siteKey = String(options && options.siteKey || bodyData.siteKey || "").trim();
    if (!siteKey && window.location) {
      var pathSiteKey = String(window.location.pathname || "").split("/")[1] || "";
      if (/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(pathSiteKey)
          && ["api", "vendor", "_next", "fackyou"].indexOf(pathSiteKey) < 0) {
        siteKey = pathSiteKey;
      }
    }
    if (siteId) params.set("site_id", siteId);
    else if (siteKey) params.set("site_key", siteKey);
    var query = params.toString();
    return "/api/public/forced-announcement" + (query ? "?" + query : "");
  }

  function mount(options) {
    if (mountedPromise) return mountedPromise;
    mountedPromise = window.fetch(requestUrl(options), {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      cache: "no-store"
    }).then(function (response) {
      if (!response || !response.ok) throw new Error("request failed");
      return response.json();
    }).then(function (announcement) {
      if (!announcement || typeof announcement !== "object") return null;
      if (typeof announcement.version !== "string") return null;
      if (typeof announcement.title !== "string") return null;
      if (typeof announcement.html !== "string") return null;
      return render(announcement);
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
    try {
      if (window.parent && window.parent !== window && window.parent.ForcedAnnouncement) {
        return;
      }
    } catch (_) {
      // Cross-origin parents cannot coordinate; mount in the current document.
    }
    mount();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoMount, { once: true });
  } else {
    autoMount();
  }
})(window, document);
