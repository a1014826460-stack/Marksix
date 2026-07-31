(function (window) {
  "use strict";

  var siteConfig = window.Twjsz666SiteConfig;
  if (!siteConfig) return;

  var siteBasePath = "/vendor/" + siteConfig.siteKey + "/";
  var ARTICLE_MODULE_KEYS = Object.freeze({
    "154.html": "pt1wei",
    "155.html": "pt1xiao",
    "156.html": "daxiao",
    "157.html": "sitouzhongte",
    "158.html": "juesha1xiao",
    "159.html": "",
    "160.html": "4xiao8ma",
    "161.html": "",
    "162.html": "",
    "163.html": "",
    "164.html": "jueshabanbo",
    "165.html": "",
    "166.html": "qinqi",
    "167.html": "sitouzhongte"
  });

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

  function issueOf(row) {
    return String(row && (row.issue || row.term) || "").trim();
  }

  function uniqueRows(module) {
    var seen = {};
    var rows = module && Array.isArray(module.rows) ? module.rows : [];
    return rows.filter(function (row) {
      var issue = issueOf(row);
      if (!issue || seen[issue]) return false;
      seen[issue] = true;
      return true;
    });
  }

  function predictionText(row) {
    var prediction = row && row.prediction || {};
    var tokens = Array.isArray(prediction.tokens) ? prediction.tokens : [];
    return tokens.length ? tokens.join("、") : String(prediction.text || "").replace(/[|]/g, "、").trim();
  }

  function openedText(row) {
    var result = row && row.result || {};
    if (!result.isOpened) return "开:待开奖";
    var code = String(result.code || "").split(/[,，、|]/).pop() || "";
    var zodiac = String(result.zodiac || "").split(/[,，、|]/).pop() || "";
    return "开:" + (code && zodiac ? code + zodiac : String(result.text || "待开奖")) + (result.isCorrect === true ? "对" : result.isCorrect === false ? "错" : "");
  }

  function moduleByKey(result, key) {
    var data = result && result.data;
    while (data && !Array.isArray(data.canonical_modules) && data.data) data = data.data;
    var modules = data && Array.isArray(data.canonical_modules) ? data.canonical_modules : [];
    return modules.filter(function (module) { return String(module.moduleKey || module.module_key || "") === key; })[0];
  }

  function renderArticleRows(result, moduleKey) {
    var root = window.document.querySelector('[data-prediction-article="true"]');
    if (!root) return;
    var rows = uniqueRows(moduleByKey(result, moduleKey));
    var paragraphs = root.querySelectorAll("p[data-prediction-row]");
    for (var index = 0; index < paragraphs.length; index += 1) {
      var row = rows[index];
      paragraphs[index].textContent = row
        ? "第" + issueOf(row) + "期 【" + predictionText(row) + "】 " + openedText(row)
        : "资料同步中";
    }
  }

  function loadArticlePredictions() {
    var filename = window.location.pathname.split("/").pop();
    var moduleKey = ARTICLE_MODULE_KEYS[filename];
    var root = window.document.querySelector('[data-prediction-article="true"]');
    if (!root) return;
    if (!moduleKey || !window.LotterySiteDataClient) {
      renderArticleRows(null, moduleKey);
      return;
    }
    var client = window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey });
    client.loadPredictions({ lotteryType: 3, historyLimit: 9 }).then(function (result) {
      if (result && result.state !== "error") renderArticleRows(result, moduleKey);
      else renderArticleRows(null, moduleKey);
    });
  }

  if (window.document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", function () { applySiteIdentity(); loadArticlePredictions(); });
  } else {
    applySiteIdentity();
    loadArticlePredictions();
  }
})(window);
