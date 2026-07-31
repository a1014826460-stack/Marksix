(function (window) {
  "use strict";

  var siteConfig = window.Twjsz666SiteConfig;
  if (!siteConfig) return;

  var SECTION_CONTRACTS = Object.freeze([
    { id: "four-xiao-odds", titlePattern: "单双各四肖", containerSelector: ".box.pad", classification: "unavailable", moduleKeys: [], rendererName: "renderFourXiaoOddsUnavailable", issueGroups: 9, supplierSentinels: ["单肖"] },
    { id: "one-head-one-code", titlePattern: "单车变宝马", containerSelector: ".pad#yxym", classification: "unavailable", moduleKeys: [], rendererName: "renderOneHeadOneCodeUnavailable", issueGroups: 1, supplierSentinels: ["24码中特"] },
    { id: "fortune-nine-xiao", titlePattern: "发财⑨肖", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["9xzt"], rendererName: "renderFortuneNineXiao", issueGroups: 9, supplierSentinels: ["发财⑨肖"] },
    { id: "three-head-four-tail", titlePattern: "三头", containerSelector: ".box.pad", classification: "unavailable", moduleKeys: [], rendererName: "renderThreeHeadFourTailUnavailable", issueGroups: 9, supplierSentinels: ["三头"] },
    { id: "flat-one-xiao", titlePattern: "平特一肖", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["pt1xiao"], rendererName: "renderPingTeXiaoHistory", issueGroups: 9, supplierSentinels: ["平特一肖"] },
    { id: "four-character-flat-xiao", titlePattern: "四字解平特肖", containerSelector: ".box.pad", classification: "unavailable", moduleKeys: [], rendererName: "renderFourCharacterFlatXiaoUnavailable", issueGroups: 9, supplierSentinels: ["四字解"] },
    { id: "expert-publications", titlePattern: "精准台湾高手", containerSelector: ".box.pad", classification: "unavailable", moduleKeys: [], rendererName: "renderExpertPublicationsUnavailable", issueGroups: 9, supplierSentinels: ["临高高手", "060期"] },
    { id: "official-gallery", titlePattern: "正版图库", containerSelector: ".box.pad", classification: "static", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 0, supplierSentinels: ["正版图库"] },
    { id: "double-wave", titlePattern: "双波", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["shuangbo"], rendererName: "renderShuangBoHistory", issueGroups: 9, supplierSentinels: ["双波"] },
    { id: "poultry-versus-beast", titlePattern: "家禽VS野兽", containerSelector: ".box.pad", classification: "unavailable", moduleKeys: [], rendererName: "renderPoultryBeastUnavailable", issueGroups: 9, supplierSentinels: ["家禽"] },
    { id: "flat-three-xiao", titlePattern: "平特③肖", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["pt3xiao"], rendererName: "renderFlatThreeXiao", issueGroups: 9, supplierSentinels: ["平特③肖"] },
    { id: "four-xiao-eight-code", titlePattern: "④肖⑧码", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["4xiao8ma"], rendererName: "renderFourXiaoEightCode", issueGroups: 9, supplierSentinels: ["④肖⑧码"] },
    { id: "big-small-special", titlePattern: "大小中特", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["daxiao"], rendererName: "renderDaXiaoHistory", issueGroups: 9, supplierSentinels: ["大小中特"] },
    { id: "seven-tail-special", titlePattern: "七尾中特", containerSelector: ".box.pad", classification: "unavailable", moduleKeys: [], rendererName: "renderSevenTailUnavailable", issueGroups: 9, supplierSentinels: ["七尾"] },
    { id: "before-bet-selection", titlePattern: "小康早到来", containerSelector: ".box.pad", classification: "composite", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 9, supplierSentinels: ["精选："] },
    { id: "flat-one-tail", titlePattern: "平特一尾", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["pt1wei"], rendererName: "renderFlatOneTail", issueGroups: 9, supplierSentinels: ["平特一尾"] },
    { id: "selected-twenty-two-code", titlePattern: "精选22码", containerSelector: ".box.pad", classification: "unavailable", moduleKeys: [], rendererName: "renderSelectedTwentyTwoUnavailable", issueGroups: 9, supplierSentinels: ["精选22码"] },
    { id: "kill-two-xiao", titlePattern: "绝杀二肖", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["juesha2xiao"], rendererName: "renderKillTwoXiao", issueGroups: 9, supplierSentinels: ["绝杀二肖"] },
    { id: "kill-one-wave", titlePattern: "绝杀①波", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["jueshabanbo"], rendererName: "renderKillOneWave", issueGroups: 9, supplierSentinels: ["绝杀①波"] },
    { id: "kill-one-tail", titlePattern: "绝杀①尾", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["juesha1wei"], rendererName: "renderKillOneTail", issueGroups: 9, supplierSentinels: ["绝杀①尾"] },
    { id: "kill-seven-code", titlePattern: "稳杀⑦码", containerSelector: ".box.pad", classification: "unavailable", moduleKeys: [], rendererName: "renderKillSevenCodeUnavailable", issueGroups: 9, supplierSentinels: ["稳杀⑦码"] },
    { id: "one-sentence-special", titlePattern: "一句话中特码", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["yijuzhenyan"], rendererName: "renderOneSentenceSpecial", issueGroups: 9, supplierSentinels: ["一句话"] },
    { id: "zodiac-knowledge", titlePattern: "属性知识", containerSelector: ".box.pad", classification: "static", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 0, supplierSentinels: ["sx.html"] },
    { id: "fast-results-footer", titlePattern: "最快开奖", containerSelector: ".box.pad", classification: "static", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 0, supplierSentinels: ["白小姐"] },
    { id: "public-before-bet-card-1", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(1)", classification: "composite", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-2", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(2)", classification: "composite", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-3", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(3)", classification: "composite", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-4", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(4)", classification: "composite", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-5", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(5)", classification: "composite", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-6", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(6)", classification: "composite", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-7", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(7)", classification: "composite", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-8", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(8)", classification: "composite", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-9", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(9)", classification: "composite", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 1, supplierSentinels: ["㈤肖"] }
  ].map(function (contract) {
    contract.moduleKeys = Object.freeze(contract.moduleKeys);
    contract.supplierSentinels = Object.freeze(contract.supplierSentinels);
    return Object.freeze(contract);
  }));

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
    return row ? row.querySelectorAll(":scope > td, :scope > th") : [];
  }

  function sectionRows(section) {
    return Array.prototype.filter.call(section.querySelectorAll("table tr"), function (row) {
      return rowCells(row).length >= 1;
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
        if (cells.length === 1) writeLeaf(cells[0], "暂无后端资料");
        else writeLeaf(cells[1], "暂无后端资料");
        if (cells[2]) writeLeaf(cells[2], "");
        return;
      }
      var issue = "第" + issueOf(row).replace(/^(第|期)/g, "") + "期";
      if (cells.length === 1) writeLeaf(cells[0], issue + " " + formatter(row) + " " + resultText(row));
      else {
        writeLeaf(cells[0], issue);
        writeLeaf(cells[1], formatter(row));
        if (cells[2]) writeLeaf(cells[2], resultText(row));
      }
      tr.setAttribute("data-prediction-row", String(index));
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

  function clearUnavailableSlots(section) {
    sectionRows(section).forEach(function (tr) {
      var cells = rowCells(tr);
      for (var index = 0; index < cells.length; index += 1) clearLeaves(cells[index]);
      if (cells[0]) writeLeaf(cells[0], "暂无后端资料");
    });
  }

  function renderTokenHistory(section, module, formatter) {
    renderThreeColumnSection(section, module, formatter || function (row) {
      return formatLabels(row, " ");
    });
  }

  function renderFortuneNineXiao(section, module) {
    renderTokenHistory(section, module, function (row) {
      return formatLabels(row, "、").slice(0, 36);
    });
  }

  function renderFlatThreeXiao(section, module) {
    renderTokenHistory(section, module, function (row) {
      return formatLabels(row, "、").slice(0, 24);
    });
  }

  function renderFourXiaoEightCode(section, module) {
    renderTokenHistory(section, module, function (row) {
      var zodiac = listValue(rawValue(row, "xiao")).slice(0, 4);
      var codes = listValue(rawValue(row, "code")).slice(0, 8);
      var values = zodiac.concat(codes);
      return values.length ? values.join("、") : formatLabels(row, "、").slice(0, 40);
    });
  }

  function renderFlatOneTail(section, module) {
    renderTokenHistory(section, module, function (row) {
      return String(rawValue(row, "tail") || formatLabels(row, "、")).split(/[|,，、\s]+/).filter(Boolean).slice(0, 8).join("、");
    });
  }

  function renderKillTwoXiao(section, module) {
    renderTokenHistory(section, module, function (row) {
      return listValue(rawValue(row, "xiao")).slice(0, 2).join("、") || formatLabels(row, "、").slice(0, 12);
    });
  }

  function renderKillOneWave(section, module) {
    renderTokenHistory(section, module, function (row) {
      return String(rawValue(row, "wave") || formatLabels(row, "、")).split(/[|,，、\s]+/).filter(Boolean).slice(0, 1).join("");
    });
  }

  function renderKillOneTail(section, module) {
    renderTokenHistory(section, module, function (row) {
      return String(rawValue(row, "tail") || formatLabels(row, "、")).split(/[|,，、\s]+/).filter(Boolean).slice(0, 1).join("");
    });
  }

  function renderOneSentenceSpecial(section, module) {
    renderTokenHistory(section, module, function (row) {
      return String(rawValue(row, "sentence") || row && row.prediction && row.prediction.text || formatLabels(row, " ")).replace(/[|]/g, " ").trim().slice(0, 80);
    });
  }

  function renderStaticSection() {}
  function renderExpertPublicationsUnavailable(section) { clearUnavailableSlots(section); }
  function renderFourXiaoOddsUnavailable(section) { clearUnavailableSlots(section); }
  function renderOneHeadOneCodeUnavailable(section) { clearUnavailableSlots(section); }

  function renderThreeHeadFourTailUnavailable(section) { clearUnavailableSlots(section); }
  function renderFourCharacterFlatXiaoUnavailable(section) { clearUnavailableSlots(section); }
  function renderPoultryBeastUnavailable(section) { clearUnavailableSlots(section); }

  function renderSevenTailUnavailable(section) { clearUnavailableSlots(section); }

  function renderSelectedTwentyTwoUnavailable(section) { clearUnavailableSlots(section); }

  function renderKillSevenCodeUnavailable(section) { clearUnavailableSlots(section); }


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

  function isSupportedLotteryType(type) {
    return siteConfig.lotteries.some(function (item) { return item.lotteryType === Number(type); });
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
    var contract = SECTION_CONTRACTS.filter(function (item) {
      return title.indexOf(item.titlePattern) !== -1 && item.containerSelector.indexOf("table.qxtable") === -1;
    })[0];
    if (!contract) throw new Error("Unknown visible twjsz666 section: " + title);
    var renderers = {
      renderStaticSection: renderStaticSection,
      renderExpertPublicationsUnavailable: renderExpertPublicationsUnavailable,
      renderFourXiaoOddsUnavailable: renderFourXiaoOddsUnavailable,
      renderOneHeadOneCodeUnavailable: renderOneHeadOneCodeUnavailable,
      renderFortuneNineXiao: renderFortuneNineXiao,
      renderThreeHeadFourTailUnavailable: renderThreeHeadFourTailUnavailable,
      renderPingTeXiaoHistory: renderPingTeXiaoHistory,
      renderFourCharacterFlatXiaoUnavailable: renderFourCharacterFlatXiaoUnavailable,
      renderShuangBoHistory: renderShuangBoHistory,
      renderPoultryBeastUnavailable: renderPoultryBeastUnavailable,
      renderFlatThreeXiao: renderFlatThreeXiao,
      renderFourXiaoEightCode: renderFourXiaoEightCode,
      renderDaXiaoHistory: renderDaXiaoHistory,
      renderSevenTailUnavailable: renderSevenTailUnavailable,
      renderFlatOneTail: renderFlatOneTail,
      renderSelectedTwentyTwoUnavailable: renderSelectedTwentyTwoUnavailable,
      renderKillTwoXiao: renderKillTwoXiao,
      renderKillOneWave: renderKillOneWave,
      renderKillOneTail: renderKillOneTail,
      renderKillSevenCodeUnavailable: renderKillSevenCodeUnavailable,
      renderOneSentenceSpecial: renderOneSentenceSpecial
    };
    var renderer = renderers[contract.rendererName];
    if (!renderer) throw new Error("Unknown twjsz666 renderer: " + contract.rendererName);
    renderer(section, modules[contract.moduleKeys[0]]);
  }

  function clearExpertPublicationLinks(section) {
    Array.prototype.forEach.call(section.querySelectorAll("li"), function (item) {
      var leaves = textNodes(item);
      leaves.forEach(function (leaf) { leaf.nodeValue = ""; });
      writeLeaf(item, "暂无后端资料");
    });
  }

  function renderPredictions(result, lotteryType) {
    var modules = moduleMap(result);
    var lottery = lotteryForType(lotteryType);
    Array.prototype.forEach.call(window.document.querySelectorAll(".box.pad"), function (section) {
      if (!section.querySelector(".list-title")) return;
      updateTitle(section, lottery);
      renderSection(section, modules);
      if (/精准台湾高手/.test(String((section.querySelector(".list-title") || {}).textContent || ""))) clearExpertPublicationLinks(section);
    });
    Array.prototype.forEach.call(window.document.querySelectorAll("table.qxtable"), function (card) {
      clearUnavailableSlots(card);
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
  function historyLimitForPage() {
    var maximum = 0;
    Array.prototype.forEach.call(window.document.querySelectorAll(".box.pad"), function (section) {
      var rows = sectionRows(section).length;
      if (rows > maximum) maximum = rows;
    });
    return Math.min(Math.max(maximum, 1), 20);
  }

  function selectLottery(type) {
    if (!isSupportedLotteryType(type)) return Promise.resolve([]);
    activeLottery = lotteryForType(type);
    var selected = activeLottery.lotteryType;
    var drawPromise = client.loadDraw({ lotteryType: selected }).then(function (result) { return announce("draw", result); });
    var predictionPromise = historyByLottery[selected]
      ? Promise.resolve(historyByLottery[selected])
      : historyRequests[selected] || client.loadPredictions({ lotteryType: selected, historyLimit: historyLimitForPage() }).then(function (result) {
        if (result && result.state !== "error") historyByLottery[selected] = result;
        return result;
      }).finally(function () {
        delete historyRequests[selected];
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
