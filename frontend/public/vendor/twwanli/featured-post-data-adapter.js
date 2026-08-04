(function (window, document) {
  "use strict";

  var siteConfig = window.TwwanliSiteConfig;
  var root = document.querySelector('[data-prediction-article="true"]');
  if (!siteConfig || !root || !window.LotterySiteDataClient) return;

  var moduleKey = String(root.getAttribute("data-prediction-module") || "");
  var client = window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey });

  function lotteryTypeFromUrl() {
    var value = Number(new window.URLSearchParams(window.location.search).get("lottery_type") || 3);
    return [1, 2, 3].includes(value) ? value : 3;
  }

  function moduleFrom(envelope) {
    var data = envelope && envelope.data && envelope.data.data || {};
    var modules = data.canonical_modules || data.modules || [];
    return modules.filter(function (module) {
      return String(module && (module.key || module.moduleKey || module.module_key) || "") === moduleKey;
    })[0] || null;
  }

  function issueOf(row) {
    return String(row && (row.issue || row.term || "") || "").replace(/^第/, "").replace(/期$/, "").trim();
  }

  function distinctRows(module) {
    var seen = {};
    return (module && Array.isArray(module.rows) ? module.rows : []).filter(function (row) {
      var issue = issueOf(row);
      if (!issue || seen[issue]) return false;
      seen[issue] = true;
      return true;
    });
  }

  function tokenValues(row) {
    var prediction = row && row.prediction || {};
    if (Array.isArray(prediction.tokens)) return prediction.tokens.map(String).filter(Boolean);
    return String(prediction.text || "").split(/[|,，、\s]+/).map(function (value) { return value.trim(); }).filter(Boolean);
  }

  function labels(row) {
    return tokenValues(row).map(function (value) { return value.split("|")[0].trim(); }).filter(Boolean);
  }

  function rawValue(row, key) {
    var raw = row && row.raw || {};
    var prediction = row && row.prediction || {};
    return raw[key] !== undefined ? raw[key] : prediction.extra && prediction.extra[key];
  }

  function listValue(value) {
    if (Array.isArray(value)) return value.map(String).filter(Boolean);
    if (typeof value !== "string") return [];
    try {
      var parsed = JSON.parse(value);
      if (Array.isArray(parsed)) return parsed.map(String).filter(Boolean);
    } catch (_) {}
    return value.split(/[|,，、\s]+/).map(function (item) { return item.trim(); }).filter(Boolean);
  }

  function formatPrediction(row) {
    if (moduleKey === "pt1wei") {
      return listValue(rawValue(row, "tail")).slice(0, 1).join("") || labels(row).slice(0, 1).join("");
    }
    if (moduleKey === "pt1xiao") return labels(row).slice(0, 1).join("");
    if (moduleKey === "sitouzhongte") {
      return labels(row).slice(0, 4).map(function (label) { return label.replace(/头$/, ""); }).join("-");
    }
    if (moduleKey === "title_14") {
      var domestic = listValue(rawValue(row, "jia")).slice(0, 4).join("");
      var wild = listValue(rawValue(row, "ye")).slice(0, 4).join("");
      if (domestic || wild) return "家禽:" + (domestic || "暂无") + " 野兽:" + (wild || "暂无");
      return labels(row).slice(0, 8).join("");
    }
    return "";
  }

  function lastToken(value) {
    var values = String(value || "").split(/[,，、|\s]+/).filter(Boolean);
    return values.length ? values[values.length - 1] : "";
  }

  function resultText(row) {
    var result = row && row.result || {};
    if (!result.isOpened) return "开:待开奖";
    var code = lastToken(result.code);
    var zodiac = lastToken(result.zodiac);
    if (/^\d$/.test(code)) code = "0" + code;
    var value = code && zodiac ? code + zodiac : String(result.text || "暂无后端资料");
    return "开:" + value + (result.isCorrect === true ? "对" : result.isCorrect === false ? "错" : "");
  }

  function writeRow(node, row) {
    var issueSlot = node.querySelector("[data-prediction-issue]");
    var contentSlot = node.querySelector("[data-prediction-content]");
    var resultSlot = node.querySelector("[data-prediction-result]");
    if (!row) {
      if (issueSlot) issueSlot.textContent = "";
      if (contentSlot) contentSlot.textContent = "暂无后端资料";
      if (resultSlot) resultSlot.textContent = "";
      if (contentSlot) contentSlot.removeAttribute("data-prediction-hit");
      return;
    }
    if (issueSlot) issueSlot.textContent = issueOf(row) + "期";
    if (contentSlot) contentSlot.textContent = formatPrediction(row) || "暂无后端资料";
    if (resultSlot) resultSlot.textContent = resultText(row);
    if (contentSlot) {
      contentSlot.removeAttribute("data-prediction-hit");
      if (row.result && row.result.isCorrect === true) contentSlot.setAttribute("data-prediction-hit", "true");
    }
  }

  function renderArticle(envelope) {
    var sourceRows = distinctRows(moduleFrom(envelope));
    Array.prototype.forEach.call(root.querySelectorAll("p[data-prediction-row]"), function (node, index) {
      writeRow(node, sourceRows[index]);
    });
  }

  function initialize() {
    client.loadPredictions({ lotteryType: lotteryTypeFromUrl(), historyLimit: 8 }).then(function (envelope) {
      renderArticle(envelope);
      window.dispatchEvent(new window.CustomEvent("site-data:ready", {
        detail: { siteKey: siteConfig.siteKey, resource: "predictions", state: envelope.state }
      }));
    });
  }

  if (document.readyState === "loading") window.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})(window, document);
