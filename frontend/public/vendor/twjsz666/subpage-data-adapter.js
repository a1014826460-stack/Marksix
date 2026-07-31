(function (window) {
  "use strict";

  var siteConfig = window.Twjsz666SiteConfig;
  if (!siteConfig) return;

  var siteBasePath = "/vendor/" + siteConfig.siteKey + "/";

  function setText(selector, value) {
    var nodes = window.document.querySelectorAll(selector);
    for (var index = 0; index < nodes.length; index += 1) nodes[index].textContent = value;
  }

  function setMetadata() {
    var body = window.document.body;
    var pageTitle = body ? String(body.getAttribute("data-page-title") || "").trim() : "";
    window.document.title = siteConfig.siteName + (pageTitle ? " - " + pageTitle : "");

    var keywords = window.document.querySelector('meta[name="keywords"]');
    if (keywords) keywords.setAttribute("content", siteConfig.siteName + "," + siteConfig.siteDomain + ",彩票娱乐,开奖记录,预测资料");

    var description = window.document.querySelector('meta[name="description"]');
    if (description) description.setAttribute("content", siteConfig.siteName + "提供分类整理的彩票资料与开奖记录，站点域名：" + siteConfig.siteDomain);
  }

  function normalizeLinks() {
    var links = window.document.querySelectorAll("a[href]");
    for (var index = 0; index < links.length; index += 1) {
      var href = links[index].getAttribute("href");
      if (href === "/baomaqg/am/kaijiangjilu.html") links[index].setAttribute("href", siteBasePath + "wylhc.html");
    }
  }

  function applySiteIdentity() {
    setMetadata();
    setText("[data-site-name]", siteConfig.siteName);
    setText("[data-site-domain]", siteConfig.siteDomain);
    setText("[data-site-footer]", siteConfig.siteName + "（" + siteConfig.siteDomain + "）");
    normalizeLinks();
  }

  if (window.document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", applySiteIdentity);
  } else {
    applySiteIdentity();
  }
})(window);
