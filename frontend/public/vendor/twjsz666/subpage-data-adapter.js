(function (window) {
  "use strict";

  var siteConfig = window.Twjsz666SiteConfig;
  if (!siteConfig) return;

  var siteBasePath = "/vendor/" + siteConfig.siteKey + "/";
  var ARTICLE_MODULE_KEYS = Object.freeze({
    "154.html": "daxiao",
    "155.html": "selected_22_codes",
    "156.html": "title_14",
    "157.html": "three_head_four_tail",
    "158.html": "steady_kill_7_codes",
    "159.html": "shuangbo",
    "160.html": "4xiao8ma",
    "161.html": "juesha1wei",
    "162.html": "title_74",
    "163.html": "jueshabanbo",
    "164.html": "juesha2xiao",
    "165.html": "pt1xiao",
    "166.html": "pt3xiao",
    "167.html": "yijuzhenyan"
  });
  var ARTICLE_TITLES = Object.freeze({
    "154.html": "大小中特",
    "155.html": "精选22码",
    "156.html": "家禽VS野兽",
    "157.html": "三头四尾",
    "158.html": "稳杀七码",
    "159.html": "双波中特",
    "160.html": "四肖八码",
    "161.html": "绝杀一尾",
    "162.html": "七尾中特",
    "163.html": "绝杀一波",
    "164.html": "绝杀二肖",
    "165.html": "平特一肖",
    "166.html": "平特三肖",
    "167.html": "一句话中特码"
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
      if (href === "/baomaqg/am/kaijiangjilu.html") links[index].setAttribute("href", "/history?type=3");
    }
  }

  function applySiteIdentity() {
    setMetadata();
    setText("[data-site-name]", siteConfig.siteName);
    setText("[data-site-domain]", siteConfig.siteDomain);
    setText("[data-site-footer]", siteConfig.siteName + "（" + siteConfig.siteDomain + "）");
    normalizeLinks();
  }

  function currentFilename() {
    return window.location.pathname.split("/").pop();
  }

  function applyArticleIdentity() {
    var filename = currentFilename();
    var moduleKey = ARTICLE_MODULE_KEYS[filename];
    var title = ARTICLE_TITLES[filename];
    var root = window.document.querySelector('[data-prediction-article="true"]');
    if (!root || !moduleKey || !title) return;
    root.setAttribute("data-prediction-module", moduleKey);
    var heading = root.querySelector("h1 font");
    if (heading) heading.textContent = "【" + title + "】资料已公开";
    if (window.document.body) window.document.body.setAttribute("data-page-title", title);
  }

  function issueOf(row) {
    return String(row && (row.issue || row.term) || "").trim();
  }
  function displayIssue(row) {
    var value = issueOf(row).replace(/^第/, "").replace(/期$/, "");
    var digits = value.replace(/\D/g, "");
    return (digits.length > 3 ? digits.slice(-3) : digits || value) + "期";
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
        ? displayIssue(row) + " 【" + predictionText(row) + "】 " + openedText(row)
        : "";
    }
  }

  function loadArticlePredictions() {
    var filename = currentFilename();
    var moduleKey = ARTICLE_MODULE_KEYS[filename];
    var root = window.document.querySelector('[data-prediction-article="true"]');
    if (!root) return;
    if (!moduleKey || !window.LotterySiteDataClient) {
      renderArticleRows(null, moduleKey);
      return;
    }
    var client = window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey });
    function load(retried) {
      client.loadPredictions({ lotteryType: 3, historyLimit: 9 }).then(function (result) {
        if (!result || result.state === "error") {
          renderArticleRows(null, moduleKey);
          return;
        }
        if (!uniqueRows(moduleByKey(result, moduleKey)).length && !retried) {
          client.clear("predictions");
          load(true);
          return;
        }
        renderArticleRows(result, moduleKey);
      });
    }
    load(false);
  }

  if (window.document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", function () { applyArticleIdentity(); applySiteIdentity(); loadArticlePredictions(); });
  } else {
    applyArticleIdentity();
    applySiteIdentity();
    loadArticlePredictions();
  }
})(window);
