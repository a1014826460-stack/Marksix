(function (window) {
  "use strict";

  var siteConfig = window.TwsszSiteConfig;
  var client = window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey });
  var activeLottery = siteConfig.lotteries[0];

  function preload(resource, query) {
    return client[resource === "draw" ? "loadDraw" : "loadPredictions"](query).then(function (result) {
      if (typeof window.CustomEvent === "function" && typeof window.dispatchEvent === "function") {
        window.dispatchEvent(new window.CustomEvent("site-data:ready", {
          detail: { siteKey: siteConfig.siteKey, resource: resource, state: result.state }
        }));
      }
      return result;
    });
  }

  function textNodes(root) {
    var nodes = [];
    if (!root || !window.document.createTreeWalker) return nodes;
    var walker = window.document.createTreeWalker(root, window.NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) nodes.push(node);
    return nodes;
  }

  function lotteryForType(lotteryType) {
    var normalizedType = Number(lotteryType);
    return siteConfig.lotteries.filter(function (lottery) {
      return lottery.lotteryType === normalizedType;
    })[0] || null;
  }

  function replaceConfiguredText(lottery) {
    lottery = lottery || activeLottery;
    textNodes(window.document.body).forEach(function (node) {
      var value = node.nodeValue;
      if (!value) return;
      var updated = value
        .replace(/(?:台湾|澳门|香港|澳洲)精选/g, lottery.titlePrefix)
        .replace(/(?:台湾|澳门|香港)\s*(?=A级猛料大公开)/g, "")
        .replace(/A级猛料大公开/g, lottery.titleRegionPrefix + " A级猛料大公开")
        .replace(/gat566\.cc/g, siteConfig.siteDomain);
      if (updated !== value) node.nodeValue = updated;
    });
  }

  function matchingAnchor(anchor, occurrence) {
    var matches = window.document.querySelectorAll("#" + anchor);
    return matches[Number(occurrence) || 0] || null;
  }

  // Preserve the vendor's visible five-number wording when its existing cell
  // is populated by the canonical five-tail replacement module.
  function preserveFiveNumberLabel() {
    var tailLabel = window.document.querySelector(".dz_content08ab2d table tr:nth-child(5) td:nth-child(2) span > span");
    if (tailLabel) tailLabel.textContent = "⑤码";
  }

  function modulesFrom(result) {
    if (!result || !result.data) return;
    var envelope = result.data;
    while (envelope && !Array.isArray(envelope.canonical_modules) && envelope.data) envelope = envelope.data;
    var modules = envelope && envelope.canonical_modules;
    if (!Array.isArray(modules)) return;
    var moduleByKey = {};
    modules.forEach(function (module) { moduleByKey[module.moduleKey] = module; });
    return moduleByKey;
  }

  var latestModulesByLottery = {};
  var historicalModulesByLottery = {};
  var historicalRequestsByLottery = {};
  var historyActivated = false;

  // Every target is an existing vendor container. We only update its existing
  // text nodes, so table layout, inline colors and typography stay untouched.
  var COMPLETE_SECTION_MAPPINGS = [
    { key: "sanxiao_siwei_xiao", title: "2组连肖连尾", target: function () { return targetAfter("top_14", 0, 2); }, rows: allRows, fallbackKey: "pt2xiao" },
    { key: "ma24", title: "精选24码", target: function () { return matchingAnchor("top_9", 0).parentElement; }, rows: function (target) { return Array.prototype.slice.call(target.querySelectorAll(".dz_content08ab2d table")); } },
    { key: "daxiao", title: "极品大小", target: function () { return targetAfter("top_13", 0, 1); }, rows: allRows },
    { key: "sixiao_sima", title: "精准四肖", target: function () { return targetAfter("top_13", 0, 4); }, rows: allRows },
    { key: "pt2xiao", title: "家野二肖", target: function () { return targetAfter("top_8", 0, 2); }, rows: allRows },
    { key: "3tou", title: "三头中特", target: function () { return targetAfter("top_8", 1, 2); }, rows: allRows },
    { key: "title_5", title: "精准天地+两肖", target: function () { return tableAfterHeading("精准天地+两肖"); }, rows: historyRows },
    // The composite is one existing text block. Keep it as one API-backed
    // section and show all four approved replacement mechanisms together.
    { key: "juesha2xiao", title: "综合绝杀", target: compositeTable, rows: function (target) { return target ? [target] : []; }, compositeKeys: ["juesha1wei", "juesha1xiao", "juesha2xiao", "jueshabanbo"] },
    { key: "juesha1wei", title: "特料公开", target: function () { return targetAfter("top_1", 0, 2); }, rows: allRows },
    { key: "pt1wei", title: "平特一尾", target: function () { return targetAfter("top_3", 0, 3); }, rows: allRows },
    { key: "pt1xiao", title: "平特一肖", target: function () { return targetAfter("top_3", 0, 6); }, rows: allRows },
    { key: "title_48", title: "8肖16码", target: function () { return targetAfter("top_11", 0, 1); }, rows: allRows },
    { key: "wuzhong5ma", title: "内幕⑤不中", target: function () { return targetAfter("top_10", 0, 1); }, rows: allRows },
    { key: "juesha1xiao", title: "绝杀7码", target: function () { return followingParagraphs("top_4", 0, 0, 1)[0]; }, rows: function () { return followingParagraphs("top_4", 0, 0, 8); } },
    { key: "juesha2xiao", title: "绝杀二肖", target: function () { return followingParagraphs("top_4", 0, 8, 1)[0]; }, rows: function () { return followingParagraphs("top_4", 0, 8, 8); } },
    { key: "jueshabanbo", title: "绝杀半波", target: function () { return followingParagraphs("top_4", 0, 16, 1)[0]; }, rows: function () { return followingParagraphs("top_4", 0, 16, 8); } },
    { key: "3hang", title: "综合资料", target: function () { return targetAfter("top_2", 0, 2); }, rows: allRows },
    { key: "pt3xiao", title: "三肖六码", target: function () { return targetAfter("top_2", 0, 4); }, rows: allRows },
    { key: "shuangbo", title: "双波10码", target: function () { return targetAfter("top_6", 0, 2); }, rows: allRows },
    { key: "title_47", title: "四肖中特", target: function () { return targetAfter("top_8", 2, 2); }, rows: allRows },
    { key: "danshuangtema", title: "单双中特", target: function () { return window.document.querySelector("#con_jihuadanshuang50000ww_1"); }, rows: allParagraphs },
    { key: "title_143", title: "一波中特", target: function () { return window.document.querySelector("#con_jihuadanshuang50000ww_2"); }, rows: allParagraphs },
    { key: "3tou", title: "一头一码", target: function () { return window.document.querySelector("#top_12").nextElementSibling.querySelector(".dz_content08ab2d"); }, rows: function (target) { return Array.prototype.slice.call(target.querySelectorAll(".bizhong1")); } }
  ];

  function targetAfter(anchor, occurrence, steps) {
    var target = matchingAnchor(anchor, occurrence);
    for (var index = 0; target && index < steps; index += 1) target = target.nextElementSibling;
    return target;
  }

  function allRows(target) {
    return Array.prototype.slice.call(target.querySelectorAll("tr"));
  }

  function allParagraphs(target) {
    return Array.prototype.slice.call(target.querySelectorAll("p"));
  }

  function historyRows(target) {
    // The target table has eight data rows plus a final static legend row.
    return Array.prototype.slice.call(target.querySelectorAll("tr")).slice(0, 8);
  }

  function headingLeaf(heading) {
    return Array.prototype.filter.call(window.document.querySelectorAll("body *"), function (node) {
      return !node.children.length && String(node.textContent || "").indexOf(heading) !== -1;
    })[0] || null;
  }

  function tableAfterHeading(heading) {
    var leaf = headingLeaf(heading);
    var table = leaf;
    while (table && table.tagName !== "TABLE") table = table.parentElement;
    return table && table.nextElementSibling && table.nextElementSibling.tagName === "TABLE" ? table.nextElementSibling : null;
  }

  function compositeTable() {
    var leaf = headingLeaf("综合绝杀");
    var table = leaf;
    while (table && table.tagName !== "TABLE") table = table.parentElement;
    return table && table.nextElementSibling && table.nextElementSibling.id === "table1" ? table.nextElementSibling : null;
  }

  function compositeLines(label) {
    return function (target) {
      if (!target) return [];
      var text = textNodes(target).filter(function (node) {
        return String(node.nodeValue || "").indexOf(label) !== -1;
      });
      return text.length ? text : [];
    };
  }

  function compositeLineTarget(label) {
    var table = compositeTable();
    if (!table) return null;
    var line = compositeLines(label)(table)[0];
    return line && line.parentElement ? line.parentElement : table;
  }

  function followingParagraphs(anchor, occurrence, skip, limit) {
    var node = matchingAnchor(anchor, occurrence);
    var rows = [];
    while (node && rows.length < skip + limit) {
      node = nextFollowingElement(node);
      if (node && node.tagName === "P") rows.push(node);
    }
    return rows.slice(skip, skip + limit);
  }

  function nextFollowingElement(node) {
    while (node) {
      if (node.nextElementSibling) return node.nextElementSibling;
      node = node.parentElement;
    }
    return null;
  }

  function tableRowsAfter(anchor, occurrence, steps) {
    return function () {
      var target = targetAfter(anchor, occurrence, steps);
      return target ? Array.prototype.slice.call(target.querySelectorAll("tr")).slice(1) : [];
    };
  }

  function moduleRow(module, index) {
    var rows = module && Array.isArray(module.rows) ? module.rows : [];
    return rows[index] || null;
  }

  function resultLabel(row) {
    var result = row && row.result || {};
    if (!result.isOpened) return "待开奖";
    return result.isCorrect ? "对" : "错";
  }

  function predictionText(row) {
    var tokens = row && row.prediction && row.prediction.tokens;
    return Array.isArray(tokens) && tokens.length ? tokens.join(" · ") : "暂无后端资料";
  }

  function replaceLeafText(node, value) {
    var texts = textNodes(node).filter(function (text) { return String(text.nodeValue || "").trim(); });
    if (!texts.length) return;
    texts[0].nodeValue = value;
    for (var index = 1; index < texts.length; index += 1) texts[index].nodeValue = "";
  }

  function rowDisplay(row, title) {
    if (!row) return "暂无后端资料";
    var term = String(row.term || row.issue || "").trim();
    var result = row.result || {};
    return term + "期 " + title + " 【" + predictionText(row) + "】 开 " + (result.text || "待开奖") + " " + resultLabel(row);
  }

  function replaceRowText(node, value) {
    var texts = textNodes(node).filter(function (text) { return String(text.nodeValue || "").trim(); });
    if (!texts.length) return;
    texts[0].nodeValue = value;
    for (var index = 1; index < texts.length; index += 1) texts[index].nodeValue = "";
  }

  function renderStandardSection(mapping, module, moduleByKey) {
    var target = mapping.target();
    if ((!module || !module.rows || !module.rows.length) && mapping.fallbackKey) module = moduleByKey[mapping.fallbackKey];
    if (!target) return;
    if (mapping.compositeKeys) {
      target.setAttribute("data-prediction-section", mapping.key);
      target.setAttribute("data-prediction-row", "0");
      var compositeText = mapping.compositeKeys.map(function (key) {
        return rowDisplay(moduleRow(moduleByKey[key], 0), key);
      }).join("\n");
      replaceRowText(target, compositeText);
      return;
    }
    var sectionKey = mapping.key;
    if (target.getAttribute("data-prediction-section")) {
      sectionKey += "-" + mapping.title;
    }
    target.setAttribute("data-prediction-section", sectionKey);
    var rows = mapping.rows(target);
    rows.forEach(function (node, index) {
      if (node.nodeType === 3) {
        node.nodeValue = rowDisplay(moduleRow(module, index), mapping.title);
        return;
      }
      node.setAttribute("data-prediction-row", String(index));
      replaceRowText(node, rowDisplay(moduleRow(module, index), mapping.title));
    });
  }

  function gradeModules(moduleByKey) {
    return [
      moduleByKey["7xiao7ma"], moduleByKey["sixiao_sima"], moduleByKey["wensha10ma"], moduleByKey["3zxt"],
      moduleByKey["4xiao8ma"], moduleByKey["pt2xiao"], moduleByKey["title_66"]
    ];
  }

  function renderGradeHistory(moduleByKey) {
    var anchor = matchingAnchor("top_15", 0);
    if (!anchor || !anchor.parentElement) return;
    var target = anchor.parentElement;
    var modules = gradeModules(moduleByKey);
    preserveFiveNumberLabel();
    target.setAttribute("data-prediction-section", "grade-a");
    Array.prototype.slice.call(target.querySelectorAll("table")).forEach(function (table, historyIndex) {
      table.setAttribute("data-prediction-row", String(historyIndex));
      var tableRows = table.querySelectorAll("tr");
      if (!tableRows.length) return;
      replaceLeafText(tableRows[0], activeLottery.titleRegionPrefix + " A级猛料大公开");
      for (var rowIndex = 1; rowIndex < tableRows.length; rowIndex += 1) {
        var cells = tableRows[rowIndex].querySelectorAll("td");
        for (var cellIndex = 0; cellIndex < cells.length; cellIndex += 1) {
          var module = modules[(rowIndex - 1) * 2 + cellIndex] || modules[0];
          replaceLeafText(cells[cellIndex], rowDisplay(moduleRow(module, historyIndex), ""));
        }
      }
    });
  }

  function renderCompleteSections(moduleByKey) {
    moduleByKey = moduleByKey || {};
    renderGradeHistory(moduleByKey);
    COMPLETE_SECTION_MAPPINGS.forEach(function (mapping) {
      renderStandardSection(mapping, moduleByKey[mapping.key], moduleByKey);
    });
  }

  function clearStaticPredictionPayload() {
    // During deferred loading, no vendor prediction, result or hit text is exposed.
    renderCompleteSections({});
  }

  function loadLatestPredictions(lottery) {
    lottery = lottery || activeLottery;
    return preload("predictions", { lotteryType: lottery.lotteryType, historyLimit: 1, includeVendor: false }).then(function (result) {
      var modules = modulesFrom(result);
      if (modules) latestModulesByLottery[lottery.lotteryType] = modules;
      if (modules && activeLottery.lotteryType === lottery.lotteryType) {
        renderGradeHistory(modules);
      }
      return result;
    });
  }

  function loadHistoricalPredictions(lottery) {
    lottery = lottery || activeLottery;
    var lotteryType = lottery.lotteryType;
    if (historicalRequestsByLottery[lotteryType]) return historicalRequestsByLottery[lotteryType];
    historicalRequestsByLottery[lotteryType] = preload("predictions", { lotteryType: lotteryType, historyLimit: 8, includeVendor: false }).then(function (result) {
      var modules = modulesFrom(result);
      if (!modules || !Object.keys(modules).length) modules = latestModulesByLottery[lotteryType] || {};
      historicalModulesByLottery[lotteryType] = modules;
      if (activeLottery.lotteryType === lotteryType) renderCompleteSections(modules);
      return modules;
    }, function () {
      var modules = latestModulesByLottery[lotteryType] || {};
      if (activeLottery.lotteryType === lotteryType) renderCompleteSections(modules);
      return modules;
    });
    return historicalRequestsByLottery[lotteryType];
  }

  function observeDeferredMappings() {
    if (historyActivated) return;
    historyActivated = true;
    loadHistoricalPredictions(activeLottery);
  }

  function scheduleAfterFirstPaint(callback) {
    var scheduleIdle = function () {
      if (window.requestIdleCallback) window.requestIdleCallback(callback, { timeout: 1200 });
      else window.setTimeout(callback, 0);
    };
    if (!window.requestAnimationFrame) {
      scheduleIdle();
      return;
    }
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(scheduleIdle);
    });
  }

  window.TwsszSiteData = {
    preloadDraw: function (lottery) {
      lottery = lottery || activeLottery;
      return preload("draw", { lotteryType: lottery.lotteryType });
    },
    preloadPredictions: loadLatestPredictions,
    selectLottery: function (lotteryType) {
      var lottery = lotteryForType(lotteryType);
      if (!lottery) return;
      activeLottery = lottery;
      replaceConfiguredText(lottery);
      loadLatestPredictions(lottery);
      var historicalModules = historicalModulesByLottery[lottery.lotteryType];
      if (historicalModules) {
        renderCompleteSections(historicalModules);
      } else {
        clearStaticPredictionPayload();
        if (historyActivated) loadHistoricalPredictions(lottery);
      }
    }
  };

  function receiveDrawLotteryChange(event) {
    var drawFrame = window.document.querySelector("iframe[src='kai.html']");
    if (!drawFrame || event.source !== drawFrame.contentWindow || event.origin !== window.location.origin) return;
    var data = event.data || {};
    if (data.type !== "lottery-change" || data.siteKey !== siteConfig.siteKey) return;
    window.TwsszSiteData.selectLottery(data.lotteryType);
  }

  function initialize() {
    replaceConfiguredText(activeLottery);
    clearStaticPredictionPayload();
    window.TwsszSiteData.preloadDraw();
    scheduleAfterFirstPaint(function () {
      window.TwsszSiteData.preloadPredictions();
    });
    // Historical rows are intentionally deferred until a visitor navigates below the fold.
    window.addEventListener("scroll", observeDeferredMappings, { once: true, passive: true });
    window.addEventListener("message", receiveDrawLotteryChange);
  }

  // The supplied scripts are in <head>; wait for every vendor text node before
  // applying configuration and mapping API rows into the existing tables.
  if (window.document.readyState === "loading") {
    window.document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})(window);
