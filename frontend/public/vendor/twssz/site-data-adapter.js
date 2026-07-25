(function (window) {
  "use strict";

  var siteConfig = window.TwsszSiteConfig;
  var client = window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey });
  var activeLottery = siteConfig.lotteries[0];

  // Each entry keeps the supplied table and only names the closest canonical module.
  var TABLE_MAPPINGS = [
    { anchor: "top_15", moduleKeys: ["7xiao7ma", "sixiao_sima", "wensha10ma", "3zxt", "4xiao8ma", "pt2xiao", "title_66"], renderer: "grade-a" },
    { anchor: "top_14", moduleKeys: ["title_5", "title_66", "pt2xiao"], renderer: "token-list" },
    { anchor: "top_9", moduleKeys: ["ma24"], renderer: "token-list" },
    { anchor: "top_13", moduleKeys: ["daxiao"], renderer: "token-list" },
    { anchor: "top_8", moduleKeys: ["title_14"], renderer: "token-list" },
    { anchor: "top_8", moduleKeys: ["3tou"], renderer: "token-list", occurrence: 1 },
    { anchor: "top_1", moduleKeys: ["juesha1wei", "title_74", "danshuangtema", "juesha3xiao", "title_48", "pt2xiao", "9xzt", "pt1xiao", "shuangbo", "pt3xiao", "title_66", "title_279", "sitouzhongte", "title_14"], renderer: "published-list" },
    { anchor: "top_3", moduleKeys: ["pt1wei"], renderer: "token-list" },
    { anchor: "top_11", moduleKeys: ["9xiao12ma"], renderer: "token-list" },
    { anchor: "top_10", moduleKeys: ["wensha10ma"], renderer: "token-list" },
    { anchor: "top_4", moduleKeys: ["wensha10ma"], renderer: "following-paragraph-list" },
    { anchor: "top_2", moduleKeys: ["6xzt", "title_66", "3hang", "shuangbo", "title_132", "pt3xiao", "title_279", "sitouzhongte", "title_14"], renderer: "published-list" },
    { anchor: "top_6", moduleKeys: ["shuangbo"], renderer: "token-list" },
    { anchor: "top_8", moduleKeys: ["sixiao_sima"], renderer: "token-list", occurrence: 2 },
    { anchor: "top_12", moduleKeys: ["3tou"], renderer: "token-list" },
    { anchor: "top_7", moduleKeys: ["danshuangtema", "shuangbo"], renderer: "token-list" }
  ];

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

  function tokensFor(module, index) {
    if (!module || !module.rows || !module.rows[index]) return [];
    var prediction = module.rows[index].prediction || {};
    return Array.isArray(prediction.tokens) ? prediction.tokens.filter(Boolean) : [];
  }

  function beforeSeparator(token) {
    return String(token).split("|")[0];
  }

  function afterSeparator(token) {
    var parts = String(token).split("|");
    return parts.length > 1 ? parts[1].split(",") : [parts[0]];
  }

  function updateTextNodes(nodes, values) {
    for (var index = 0; index < nodes.length; index += 1) {
      nodes[index].textContent = index < values.length ? values[index] : "";
    }
  }

  function updateCell(cell, module, format) {
    var tokens = tokensFor(module, 0);
    if (!cell || !tokens.length) return;
    var term = String(module.rows[0].term || module.rows[0].issue || "").trim();
    var termNode = cell.querySelector("span > span:first-child");
    if (termNode && term) termNode.textContent = term + "期";
    updateTextNodes(cell.querySelectorAll("span > span:last-child font"), format(tokens));
  }

  function renderGradeA(moduleByKey) {
    var table = window.document.querySelector(".dz_content08ab2d table");
    if (!table) return;
    var rows = table.querySelectorAll("tr");
    if (rows.length < 5) return;
    updateCell(rows[1].cells[0], moduleByKey["7xiao7ma"], function (tokens) { return tokens.map(beforeSeparator); });
    updateCell(rows[2].cells[0], moduleByKey["sixiao_sima"], function (tokens) { return tokens.map(beforeSeparator); });
    updateCell(rows[2].cells[1], moduleByKey["wensha10ma"], function (tokens) { return tokens; });
    updateCell(rows[3].cells[0], moduleByKey["3zxt"], function (tokens) { return tokens.map(beforeSeparator); });
    updateCell(rows[3].cells[1], moduleByKey["4xiao8ma"], function (tokens) { return tokens.reduce(function (numbers, token) { return numbers.concat(afterSeparator(token)); }, []); });
    updateCell(rows[4].cells[0], moduleByKey["pt2xiao"], function (tokens) { return tokens.map(beforeSeparator); });
    var tailLabel = rows[4].cells[1].querySelector("span > span");
    if (tailLabel) tailLabel.textContent = "⑤码";
    updateCell(rows[4].cells[1], moduleByKey["title_66"], function (tokens) { return tokens.map(beforeSeparator); });
  }

  function matchingAnchor(anchor, occurrence) {
    var matches = window.document.querySelectorAll("#" + anchor);
    return matches[Number(occurrence) || 0] || null;
  }

  function mappingScope(mapping) {
    var anchor = matchingAnchor(mapping.anchor, mapping.occurrence);
    if (!anchor) return null;
    if (anchor.tagName === "TABLE") return anchor;
    return firstContentSibling(anchor);
  }

  function firstContentSibling(anchor) {
    var sibling = anchor ? anchor.nextElementSibling : null;
    while (sibling) {
      var text = String(sibling.textContent || "").trim();
      if (sibling.tagName !== "STYLE" && sibling.tagName !== "TABLE" && sibling.tagName !== "H3" && text) {
        return sibling;
      }
      sibling = sibling.nextElementSibling;
    }
    return null;
  }

  function nearestLeafFonts(root) {
    return Array.prototype.filter.call(root.querySelectorAll("font"), function (node) {
      return !node.querySelector("font") && String(node.textContent || "").trim();
    });
  }

  function updateTermNode(root, term) {
    if (!term) return;
    textNodes(root).some(function (node) {
      if (!/\d{1,7}\s*期/.test(node.nodeValue || "")) return false;
      node.nodeValue = node.nodeValue.replace(/\d{1,7}\s*期/, term + "期");
      return true;
    });
  }

  function renderTokenList(scope, modules, mapping) {
    var module = modules[mapping.moduleKeys[0]];
    var tokens = tokensFor(module, 0);
    if (!scope || !tokens.length) return;
    var term = String(module.rows[0].term || module.rows[0].issue || "").trim();
    updateTermNode(scope, term);
    var values = tokens.reduce(function (all, token) { return all.concat(afterSeparator(token)); }, []);
    var fonts = nearestLeafFonts(scope);
    if (fonts.length) updateTextNodes(fonts.slice(-values.length), values);
  }

  function renderParagraphList(scope, modules, mapping) {
    var module = modules[mapping.moduleKeys[0]];
    if (!scope || !module || !module.rows) return;
    var lines = scope.querySelectorAll("p");
    for (var index = 0; index < lines.length && index < module.rows.length; index += 1) {
      var tokens = tokensFor(module, index);
      if (!tokens.length) continue;
      updateTermNode(lines[index], String(module.rows[index].term || module.rows[index].issue || "").trim());
      updateTextNodes(nearestLeafFonts(lines[index]), tokens.reduce(function (all, token) { return all.concat(afterSeparator(token)); }, []));
    }
  }

  function renderFollowingParagraphList(modules, mapping) {
    var anchor = matchingAnchor(mapping.anchor, mapping.occurrence);
    var header = anchor && anchor.parentElement;
    var module = modules[mapping.moduleKeys[0]];
    if (!header || !module || !module.rows) return;
    var line = header.nextElementSibling;
    for (var index = 0; line && index < module.rows.length; line = line.nextElementSibling) {
      if (line.tagName !== "P") continue;
      var tokens = tokensFor(module, index);
      if (!tokens.length) continue;
      updateTermNode(line, String(module.rows[index].term || module.rows[index].issue || "").trim());
      updateTextNodes(nearestLeafFonts(line), tokens.reduce(function (all, token) { return all.concat(afterSeparator(token)); }, []));
      index += 1;
    }
  }

  function renderPublishedList(scope, modules, mapping) {
    if (!scope) return;
    var cells = scope.querySelectorAll("td");
    for (var index = 0; index < cells.length && index < mapping.moduleKeys.length; index += 1) {
      var module = modules[mapping.moduleKeys[index]];
      var tokens = tokensFor(module, 0);
      if (!tokens.length) continue;
      updateTermNode(cells[index], String(module.rows[0].term || module.rows[0].issue || "").trim());
      var target = textNodes(cells[index]).filter(function (node) { return /已公开/.test(node.nodeValue || ""); })[0];
      if (target) target.nodeValue = tokens.map(beforeSeparator).join(" ");
    }
  }

  function renderMapping(mapping, moduleByKey) {
    if (mapping.renderer === "grade-a") {
      renderGradeA(moduleByKey);
      return;
    }
    var scope = mappingScope(mapping);
    if (mapping.renderer === "following-paragraph-list") renderFollowingParagraphList(moduleByKey, mapping);
    else if (mapping.renderer === "paragraph-list") renderParagraphList(scope, moduleByKey, mapping);
    else if (mapping.renderer === "published-list") renderPublishedList(scope, moduleByKey, mapping);
    else renderTokenList(scope, moduleByKey, mapping);
  }

  function modulesFrom(result) {
    if (!result || !result.data || !result.data.data) return;
    var modules = result.data.data.canonical_modules;
    if (!Array.isArray(modules)) return;
    var moduleByKey = {};
    modules.forEach(function (module) { moduleByKey[module.moduleKey] = module; });
    return moduleByKey;
  }

  var latestModulesByLottery = {};
  var historicalModulesByLottery = {};
  var historicalRequestsByLottery = {};
  var deferredMappingsObserved = false;
  var activatedMappings = [];

  function loadLatestPredictions(lottery) {
    lottery = lottery || activeLottery;
    return preload("predictions", { lotteryType: lottery.lotteryType, historyLimit: 1, includeVendor: false }).then(function (result) {
      var modules = modulesFrom(result);
      if (modules) latestModulesByLottery[lottery.lotteryType] = modules;
      if (modules && activeLottery.lotteryType === lottery.lotteryType) renderGradeA(modules);
      return result;
    });
  }

  function loadHistoricalPredictions(lottery) {
    lottery = lottery || activeLottery;
    var lotteryType = lottery.lotteryType;
    if (historicalRequestsByLottery[lotteryType]) return historicalRequestsByLottery[lotteryType];
    historicalRequestsByLottery[lotteryType] = preload("predictions", { lotteryType: lotteryType, historyLimit: 8, includeVendor: false }).then(function (result) {
      var modules = modulesFrom(result) || latestModulesByLottery[lotteryType];
      if (modules) historicalModulesByLottery[lotteryType] = modules;
      return modules;
    });
    return historicalRequestsByLottery[lotteryType];
  }

  function renderDeferredMapping(mapping) {
    var lottery = activeLottery;
    loadHistoricalPredictions(lottery).then(function (modules) {
      if (modules && activeLottery.lotteryType === lottery.lotteryType) renderMapping(mapping, modules);
    }, function () {
      // The renderer keeps the supplied static history intact when the network is unavailable.
      var latestModules = latestModulesByLottery[lottery.lotteryType];
      if (latestModules && activeLottery.lotteryType === lottery.lotteryType) renderMapping(mapping, latestModules);
    });
  }

  function observeDeferredMappings() {
    if (deferredMappingsObserved) return;
    deferredMappingsObserved = true;
    var deferredMappings = TABLE_MAPPINGS.filter(function (mapping) { return mapping.renderer !== "grade-a"; });
    if (!window.IntersectionObserver) {
      deferredMappings.forEach(function (mapping) {
        activatedMappings.push(mapping);
        renderDeferredMapping(mapping);
      });
      return;
    }
    deferredMappings.forEach(function (mapping) {
      var scope = mappingScope(mapping);
      if (!scope) return;
      var observer = new window.IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          observer.unobserve(entry.target);
          activatedMappings.push(mapping);
          renderDeferredMapping(mapping);
        });
      }, { rootMargin: "240px 0px" });
      observer.observe(scope);
    });
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
    // Two frames leave the vendor shell and its navigation responsive before API work begins.
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
      if (historicalModules) activatedMappings.forEach(function (mapping) { renderMapping(mapping, historicalModules); });
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
