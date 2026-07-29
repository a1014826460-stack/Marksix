(function (window) {
  "use strict";

  var siteConfig = window.Twbst528SiteConfig;
  var client = window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey });
  var PAGE_CONTRACTS = {
    "15": { moduleKey: "title_198", label: "逢买必中" },
    "16": { moduleKey: "sitouzhongte", label: "四头必中" },
    "17": { moduleKey: "title_14", label: "家禽野兽" },
    "18": { moduleKey: "title_5", label: "天地生肖" },
    "19": { moduleKey: "title_47", label: "稳料四肖中" },
    "20": { moduleKey: "title_279", label: "合数大小" },
    "21": { moduleKey: "title_66", label: "5尾中特" },
    "22": { moduleKey: "3hang", label: "精准五行" },
    "23": { moduleKey: "title_132", label: "合数单双" },
    "24": { moduleKey: "qinqi", label: "琴棋书画" },
    "27": { moduleKey: "3hang", label: "三行中特" },
    "30": { moduleKey: "title_198", label: "逢买必中" },
    "31": { moduleKey: "juesha1wei", label: "绝杀①尾" },
    "32": { moduleKey: "sitouzhongte", label: "四头必中" },
    "33": { moduleKey: "title_14", label: "家禽野兽" },
    "35": { moduleKey: "title_47", label: "稳料四肖中" },
    "36": { moduleKey: "title_279", label: "合数大小" },
    "37": { moduleKey: "title_66", label: "5尾中特" },
    "38": { moduleKey: "3hang", label: "精准五行" },
    "39": { moduleKey: "title_132", label: "合数单双" },
    "40": { moduleKey: "qinqi", label: "琴棋书画" },
    "41": { moduleKey: "pt3xiao", label: "平特③肖连" },
    "42": { moduleKey: "3tou", label: "三头中特" },
    "43": { moduleKey: "3hang", label: "三行中特" },
    "44": { moduleKey: "yijuzhenyan", label: "一句中特" },
    "45": { moduleKey: "title_198", label: "逢买必中" },
    "46": { moduleKey: "juesha1wei", label: "绝杀①尾" },
    "47": { moduleKey: "sitouzhongte", label: "四头必中" },
    "48": { moduleKey: "title_14", label: "家禽野兽" },
    "49": { moduleKey: "title_5", label: "天地生肖" },
    "51": { moduleKey: "title_279", label: "合数大小" },
    "52": { moduleKey: "title_47", label: "精准四肖" },
    "53": { moduleKey: "title_66", label: "5尾中特" },
    "54": { moduleKey: "3hang", label: "精准五行" },
    "55": { moduleKey: "title_132", label: "合数单双" },
    "56": { moduleKey: "qinqi", label: "琴棋书画" },
    "57": { moduleKey: "pt3xiao", label: "平特③肖连" },
    "58": { moduleKey: "3tou", label: "三头中特" },
    "59": { moduleKey: "3hang", label: "三行中特" },
    "60": { moduleKey: "yijuzhenyan", label: "一句中特" },
    "77": { moduleKey: "title_198", label: "逢买必中" },
    "78": { moduleKey: "juesha1wei", label: "绝杀①尾" },
    "79": { moduleKey: "sitouzhongte", label: "四头必中" },
    "80": { moduleKey: "title_14", label: "家禽野兽" },
    "141": { moduleKey: "title_198", label: "逢买必中" },
    "142": { moduleKey: "juesha1wei", label: "绝杀①尾" },
    "143": { moduleKey: "sitouzhongte", label: "四头必中" },
    "144": { moduleKey: "title_14", label: "家禽野兽" },
    "145": { moduleKey: "title_5", label: "天地生肖" },
    "146": { moduleKey: "title_47", label: "稳料四肖中" },
    "147": { moduleKey: "title_279", label: "合数大小" },
    "148": { moduleKey: "title_47", label: "精准四肖" },
    "149": { moduleKey: "title_66", label: "5尾中特" },
    "150": { moduleKey: "3hang", label: "精准五行" },
    "151": { moduleKey: "title_132", label: "合数单双" },
    "152": { moduleKey: "qinqi", label: "琴棋书画" },
    "153": { moduleKey: "pt3xiao", label: "平特③肖连" },
    "154": { moduleKey: "3tou", label: "三头中特" },
    "155": { moduleKey: "3hang", label: "三行中特" },
    "156": { moduleKey: "yijuzhenyan", label: "一句中特" }
  };

  function pageContract() {
    var match = /\/(\d+)\.html$/.exec(window.location.pathname);
    return match ? PAGE_CONTRACTS[match[1]] || null : null;
  }

  function textNodes(root) {
    var nodes = [];
    if (!root || !window.document.createTreeWalker) return nodes;
    var walker = window.document.createTreeWalker(root, window.NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) nodes.push(node);
    return nodes;
  }

  function distinctRows(module) {
    var seen = {};
    return Array.isArray(module && module.rows) ? module.rows.filter(function (row) {
      var key = String(row && (row.issue || row.term || "") || "");
      if (!key || seen[key]) return false;
      seen[key] = true;
      return true;
    }) : [];
  }

  function moduleFrom(result, moduleKey) {
    var envelope = result && result.data;
    while (envelope && !Array.isArray(envelope.canonical_modules) && envelope.data) envelope = envelope.data;
    return Array.isArray(envelope && envelope.canonical_modules) ? envelope.canonical_modules.filter(function (module) {
      return String(module.moduleKey || module.module_key || "") === moduleKey;
    })[0] || null : null;
  }

  function predictionText(row, contract) {
    var values = Array.isArray(row && row.prediction && row.prediction.tokens)
      ? row.prediction.tokens.map(String).filter(Boolean)
      : [];
    var text = String(row && row.prediction && row.prediction.text || "").replace(/\|/g, " ").trim();
    if (contract.moduleKey === "title_14" && values.length) return values.join("+");
    if (contract.moduleKey === "title_5" && values.length) return values.join("+");
    if (contract.moduleKey === "yijuzhenyan") return text || values.join(" ");
    return text || values.join("-");
  }

  function resultText(row) {
    var result = row && row.result || {};
    if (!result.isOpened) return "待开奖";
    var code = resultToken(result.code, true);
    var zodiac = resultToken(result.zodiac, false);
    var number = code && zodiac ? code + zodiac : String(result.text || "");
    return number + (result.isCorrect === true ? "对" : result.isCorrect === false ? "错" : "");
  }

  function resultToken(value, padNumber) {
    var values = String(value || "").split(/[,，、|]+/).map(function (item) {
      return item.trim();
    }).filter(Boolean);
    var token = values.length ? values[values.length - 1] : "";
    return padNumber && /^\d{1,2}$/.test(token) ? token.padStart(2, "0") : token;
  }

  function articleRows() {
    return Array.prototype.slice.call(window.document.querySelectorAll(".article-content > p"));
  }

  function writeArticleRow(node, row, contract) {
    var leaves = textNodes(node);
    if (!leaves.length) return;
    var value = row
      ? "第" + String(row.term || row.issue || "").replace(/^第|期$/g, "") + "期 " + contract.label + " 【" + predictionText(row, contract) + "】开 " + resultText(row)
      : "暂无后端资料";
    var marker = node.querySelector("span[style*='background-color']");
    var markerLeaf = marker && textNodes(marker)[0];
    var isHit = Boolean(row && row.result && row.result.isCorrect === true);
    var predicted = predictionText(row, contract);
    Array.prototype.forEach.call(node.querySelectorAll("span[style*='background-color']"), function (item) {
      item.style.backgroundColor = "";
    });
    if (isHit && markerLeaf && predicted) {
      var predictionIndex = value.indexOf(predicted);
      leaves[0].nodeValue = predictionIndex >= 0 ? value.slice(0, predictionIndex) : value;
      markerLeaf.nodeValue = predicted;
      var markerIndex = leaves.indexOf(markerLeaf);
      var trailing = leaves[markerIndex + 1];
      if (trailing) trailing.nodeValue = predictionIndex >= 0 ? value.slice(predictionIndex + predicted.length) : "";
      leaves.forEach(function (leaf) {
        if (leaf !== leaves[0] && leaf !== markerLeaf && leaf !== trailing) leaf.nodeValue = "";
      });
      marker.style.backgroundColor = "#FFFF00";
      return;
    }
    leaves[0].nodeValue = value;
    leaves.slice(1).forEach(function (leaf) { leaf.nodeValue = ""; });
  }

  function render(contract, result) {
    var rows = distinctRows(moduleFrom(result, contract.moduleKey));
    articleRows().forEach(function (node, index) {
      writeArticleRow(node, rows[index], contract);
    });
  }

  function announce(result) {
    if (typeof window.CustomEvent === "function") {
      window.dispatchEvent(new window.CustomEvent("site-data:ready", {
        detail: { siteKey: siteConfig.siteKey, resource: "predictions", state: result.state }
      }));
    }
  }

  function initialize() {
    var contract = pageContract();
    if (!contract) return;
    client.loadPredictions({ lotteryType: 3, historyLimit: 8 }).then(function (result) {
      render(contract, result);
      announce(result);
    });
  }

  if (window.document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }
})(window);
