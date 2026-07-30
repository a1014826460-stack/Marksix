(function (window) {
  "use strict";

  var siteConfig = window.Twjsz666SiteConfig;
  if (!siteConfig) return;

  function textNodes(root) {
    var nodes = [];
    if (!root || !window.document.createTreeWalker) return nodes;
    var walker = window.document.createTreeWalker(root, window.NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) nodes.push(node);
    return nodes;
  }

  function firstLeaf(root) {
    return textNodes(root)[0] || null;
  }

  function clearLeaves(root, keep) {
    textNodes(root).forEach(function (node) {
      if (!keep || keep.indexOf(node) === -1) node.nodeValue = "";
    });
  }

  function writeLeaf(root, value) {
    var leaf = firstLeaf(root);
    if (!leaf) return;
    leaf.nodeValue = String(value || "");
    clearLeaves(root, [leaf]);
  }

  function issueOf(row) {
    return String(row && (row.issue || row.term || ((row.year || "") + "-" + (row.term || ""))) || "").trim();
  }

  function distinctRows(module) {
    var seen = {};
    return Array.isArray(module && module.rows) ? module.rows.filter(function (row) {
      var issue = issueOf(row);
      if (!issue || seen[issue]) return false;
      seen[issue] = true;
      return true;
    }) : [];
  }

  function tokenValues(row) {
    var prediction = row && row.prediction || {};
    if (Array.isArray(prediction.tokens)) return prediction.tokens.map(String).filter(Boolean);
    var value = String(prediction.text || "");
    return value.replace(/[【】\[\]"]/g, "").split(/[|,，、\s]+/).map(function (item) {
      return item.trim();
    }).filter(Boolean);
  }

  function rawValue(row, key) {
    var raw = row && row.raw || {};
    var extra = row && row.prediction && row.prediction.extra || {};
    return raw[key] !== undefined ? raw[key] : extra[key];
  }

  function listValue(value) {
    if (Array.isArray(value)) return value.map(String).filter(Boolean);
    if (typeof value !== "string") return [];
    try {
      var parsed = JSON.parse(value);
      if (Array.isArray(parsed)) return parsed.map(String).filter(Boolean);
    } catch (_) {
      // Legacy payloads can be delimited strings.
    }
    return value.split(/[|,，、\s]+/).map(function (item) { return item.trim(); }).filter(Boolean);
  }

  function resultToken(value, padNumber) {
    var values = String(value || "").split(/[,，、|]+/).map(function (item) { return item.trim(); }).filter(Boolean);
    var token = values.length ? values[values.length - 1] : "";
    return padNumber && /^\d{1,2}$/.test(token) ? ("0" + token).slice(-2) : token;
  }

  function resultText(row) {
    var result = row && row.result || {};
    if (!result.isOpened) return "开:待开奖";
    var code = resultToken(result.code, true);
    var zodiac = resultToken(result.zodiac, false);
    var value = code && zodiac ? code + zodiac : String(result.text || "");
    return "开:" + value + (result.isCorrect === true ? "对" : result.isCorrect === false ? "错" : "");
  }

  function rowCells(row) {
    return row ? row.querySelectorAll(":scope > td") : [];
  }

  function sectionRows(section) {
    return Array.prototype.filter.call(section.querySelectorAll("table tr"), function (row) {
      return rowCells(row).length >= 2;
    });
  }

  function formatLabels(row, separator) {
    return tokenValues(row).map(function (value) {
      return String(value).split("|", 1)[0].replace(/[\[\]"]/g, "").trim();
    }).filter(Boolean).join(separator || "");
  }

  function renderThreeColumnSection(section, module, formatter) {
    var data = distinctRows(module);
    sectionRows(section).forEach(function (tr, index) {
      var cells = rowCells(tr);
      var row = data[index];
      if (!row) {
        writeLeaf(cells[0], "");
        writeLeaf(cells[1], "暂无后端资料");
        if (cells[2]) writeLeaf(cells[2], "");
        return;
      }
      writeLeaf(cells[0], "第" + issueOf(row).replace(/^(第|期)/g, "") + "期");
      writeLeaf(cells[1], formatter(row));
      if (cells[2]) writeLeaf(cells[2], resultText(row));
      tr.setAttribute("data-prediction-row", String(index));
    });
  }

  function renderSanTouSiWeiHistory(section, module) {
    renderThreeColumnSection(section, module, function (row) {
      var head = listValue(rawValue(row, "head")).slice(0, 3);
      var tail = listValue(rawValue(row, "tail")).slice(0, 4);
      return "三头【" + (head.length ? head.join(".") : formatLabels(row, ".")) + "】四尾【" + (tail.length ? tail.join(".") : "暂无后端资料") + "】";
    });
  }

  function renderYixiaoYimaHistory(section, module) {
    renderThreeColumnSection(section, module, function (row) {
      var xiao = listValue(rawValue(row, "xiao")).slice(0, 1);
      var code = listValue(rawValue(row, "code")).slice(0, 24);
      return "一肖【" + (xiao.join("") || "暂无后端资料") + "】一码【" + (code.join(".") || "暂无后端资料") + "】";
    });
  }

  function renderShuangBoHistory(section, module) {
    renderThreeColumnSection(section, module, function (row) {
      return formatLabels(row, "+").slice(0, 30);
    });
  }

  function renderPingTeXiaoHistory(section, module) {
    renderThreeColumnSection(section, module, function (row) {
      return formatLabels(row, "").slice(0, 12);
    });
  }

  function renderDaXiaoHistory(section, module) {
    renderThreeColumnSection(section, module, function (row) {
      var value = String(rawValue(row, "daxiao") || formatLabels(row, "") || "");
      return value === "大" ? "大数" : value === "小" ? "小数" : value;
    });
  }

  function renderUnavailableSection(section) {
    sectionRows(section).forEach(function (tr) {
      var cells = rowCells(tr);
      if (cells[0]) writeLeaf(cells[0], "");
      if (cells[1]) writeLeaf(cells[1], "暂无后端资料");
      if (cells[2]) writeLeaf(cells[2], "");
    });
  }

  function moduleMap(result) {
    var envelope = result && result.data;
    while (envelope && !Array.isArray(envelope.canonical_modules) && envelope.data) envelope = envelope.data;
    return Array.isArray(envelope && envelope.canonical_modules) ? envelope.canonical_modules.reduce(function (all, item) {
      all[String(item.moduleKey || item.module_key || "")] = item;
      return all;
    }, {}) : {};
  }

  function lotteryForType(type) {
    return siteConfig.lotteries.filter(function (item) { return item.lotteryType === Number(type); })[0] || siteConfig.lotteries[0];
  }

  function updateTitle(section, lottery) {
    var title = section.querySelector(".list-title");
    if (!title) return;
    var leaf = firstLeaf(title);
    if (!leaf) return;
    var value = String(leaf.nodeValue || "");
    value = value.replace(/(?:台湾|澳门|香港)精选/g, lottery.titlePrefix);
    value = value.replace(/台湾金手指/g, lottery.titlePrefix);
    if (/A级猛料大公开/.test(value) && value.indexOf(lottery.titleRegionPrefix + " ") !== 0) value = lottery.titleRegionPrefix + " " + value;
    leaf.nodeValue = value;
  }

  function renderSection(section, modules) {
    var title = String((section.querySelector(".list-title") || {}).textContent || "");
    var module = null;
    var renderer = renderUnavailableSection;
    if (/三头/.test(title)) {
      module = modules.pt3xiao || modules.title_47;
      renderer = renderSanTouSiWeiHistory;
    } else if (/一头一码|一肖一码/.test(title)) {
      module = modules["9xiao12ma"] || modules.pt1xiao;
      renderer = renderYixiaoYimaHistory;
    } else if (/双波/.test(title)) {
      module = modules.shuangbo;
      renderer = renderShuangBoHistory;
    } else if (/平特一肖|平特③肖/.test(title)) {
      module = modules.pt1xiao;
      renderer = renderPingTeXiaoHistory;
    } else if (/大小中特/.test(title)) {
      module = modules.daxiao;
      renderer = renderDaXiaoHistory;
    }
    renderer(section, module);
  }

  function renderPredictions(result, lotteryType) {
    var modules = moduleMap(result);
    var lottery = lotteryForType(lotteryType);
    Array.prototype.forEach.call(window.document.querySelectorAll(".box.pad, .box.pad.xjct"), function (section) {
      updateTitle(section, lottery);
      renderSection(section, modules);
    });
  }

  function announce(resource, result) {
    if (typeof window.CustomEvent === "function") {
      window.dispatchEvent(new window.CustomEvent("site-data:ready", {
        detail: { siteKey: siteConfig.siteKey, resource: resource, state: result.state }
      }));
    }
    return result;
  }

  if (window.parent !== window && /\/kai\.html$/.test(window.location.pathname)) {
    function bindDrawTabs() {
      Array.prototype.forEach.call(window.document.querySelectorAll(".KJ-TabBox li"), function (item) {
        item.addEventListener("click", function () {
          var type = Number(item.getAttribute("data-lottery-type"));
          if (type && window.parent && typeof window.parent.postMessage === "function") {
            window.parent.postMessage({ type: "lottery-change", siteKey: siteConfig.siteKey, lotteryType: type }, window.location.origin);
          }
        });
      });
    }
    if (window.document.readyState === "loading") window.addEventListener("DOMContentLoaded", bindDrawTabs);
    else bindDrawTabs();
    return;
  }

  if (!window.LotterySiteDataClient || typeof window.LotterySiteDataClient.create !== "function") return;
  window.document.title = siteConfig.siteName;
  var client = window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey });
  var activeLottery = siteConfig.lotteries[0];
  var historyByLottery = {};
  var historyRequests = {};
  var HISTORY_LIMIT = 9;

  function selectLottery(type) {
    activeLottery = lotteryForType(type);
    var selected = activeLottery.lotteryType;
    var drawPromise = client.loadDraw({ lotteryType: selected }).then(function (result) { return announce("draw", result); });
    var predictionPromise = historyByLottery[selected]
      ? Promise.resolve(historyByLottery[selected])
      : historyRequests[selected] || client.loadPredictions({ lotteryType: selected, historyLimit: HISTORY_LIMIT }).then(function (result) {
        historyByLottery[selected] = result;
        return result;
      });
    historyRequests[selected] = predictionPromise;
    predictionPromise.then(function (result) {
      if (activeLottery.lotteryType === selected) renderPredictions(result, selected);
      announce("predictions", result);
    });
    return Promise.all([drawPromise, predictionPromise]);
  }

  window.addEventListener("message", function (event) {
    var drawFrame = window.document.querySelector("iframe[src='kai.html']");
    if (!drawFrame || event.source !== drawFrame.contentWindow || event.origin !== window.location.origin) return;
    var message = event.data || {};
    if (message.type !== "lottery-change" || message.siteKey !== siteConfig.siteKey) return;
    selectLottery(Number(message.lotteryType));
  });

  window.Twjsz666SiteData = Object.freeze({ selectLottery: selectLottery, siteConfig: siteConfig });
  window.addEventListener("DOMContentLoaded", function () { selectLottery(activeLottery.lotteryType); });
})(window);
