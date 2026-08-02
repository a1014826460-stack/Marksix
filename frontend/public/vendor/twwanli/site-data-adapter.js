(function (window, document) {
  "use strict";

  var siteConfig = window.TwwanliSiteConfig;
  if (!siteConfig || !window.LotterySiteDataClient) return;

  var client = window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey });
  var activeLotteryType = 3;
  var knownDrawFrame = document.querySelector(".haoju iframe[src='kai.html']");

  function modulesByKey(envelope) {
    var data = envelope && envelope.data && envelope.data.data || {};
    var modules = data.canonical_modules || data.modules || [];
    return modules.reduce(function (result, module) {
      var key = String(module && (module.key || module.moduleKey) || "");
      if (key) result[key] = module;
      return result;
    }, {});
  }

  function issueOf(row) {
    return String(row && (row.issue || row.term || ((row.year || "") + (row.term || ""))) || "").replace(/^第/, "").replace(/期$/, "").trim();
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

  function resultText(row) {
    var result = row && row.result || {};
    if (!result.isOpened) return "开:待开奖";
    var last = function (value) {
      var tokens = String(value || "").split(/[,，、|\s]+/).filter(Boolean);
      return tokens.length ? tokens[tokens.length - 1] : "";
    };
    var code = last(result.code);
    var zodiac = last(result.zodiac);
    if (/^\d$/.test(code)) code = "0" + code;
    return "开:" + (code && zodiac ? code + zodiac : String(result.text || "暂无后端资料")) + (result.isCorrect === true ? "对" : result.isCorrect === false ? "错" : "");
  }

  function tokenValues(row) {
    var prediction = row && row.prediction || {};
    if (Array.isArray(prediction.tokens)) return prediction.tokens.map(String).filter(Boolean);
    return String(prediction.text || "").split(/[|,，、\s]+/).map(function (value) { return value.trim(); }).filter(Boolean);
  }

  function codeValues(row) {
    var values = [];
    tokenValues(row).forEach(function (token) {
      var match = String(token).match(/\d{1,2}/g);
      if (match) values = values.concat(match.map(function (value) { return ("0" + value).slice(-2); }));
    });
    return values;
  }

  function labels(row) {
    return tokenValues(row).map(function (value) { return value.split("|")[0].trim(); }).filter(Boolean);
  }

  function rawValue(row, key) {
    var prediction = row && row.prediction || {};
    var raw = row && row.raw || {};
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

  function section(id) { return document.getElementById(id); }
  function slots(root) { return root ? root.querySelectorAll("[data-prediction-issue], [data-prediction-content], [data-prediction-content-secondary], [data-prediction-result]") : []; }
  function rows(root) { return root ? Array.prototype.filter.call(root.querySelectorAll("tr"), function (row) { return slots(row).length; }) : []; }

  function clearHit(root) {
    Array.prototype.forEach.call(root.querySelectorAll("[data-prediction-hit]"), function (node) {
      node.removeAttribute("data-prediction-hit");
    });
  }

  function writeRow(row, issue, content, result, secondary, hit) {
    var issueSlot = row.querySelector("[data-prediction-issue]");
    var contentSlot = row.querySelector("[data-prediction-content]");
    var secondarySlot = row.querySelector("[data-prediction-content-secondary]");
    var resultSlot = row.querySelector("[data-prediction-result]");
    clearHit(row);
    if (issueSlot) issueSlot.textContent = issue || "";
    if (contentSlot) contentSlot.textContent = content || "";
    if (secondarySlot) secondarySlot.textContent = secondary || "";
    if (resultSlot) resultSlot.textContent = result || "";
    if (hit && contentSlot) contentSlot.setAttribute("data-prediction-hit", "true");
  }

  function renderUnavailableHistory(id) {
    rows(section(id)).forEach(function (row) { writeRow(row, "", "暂无后端资料", ""); });
  }

  function renderThreeColumnHistory(id, module, format) {
    var sourceRows = distinctRows(module);
    rows(section(id)).forEach(function (row, index) {
      var source = sourceRows[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "");
      var value = format(source);
      writeRow(row, issueOf(source) + "期", value, resultText(source), "", source.result && source.result.isCorrect === true);
    });
  }

  function renderOneCodeOneXiaoTable(modules) {
    var codeRows = distinctRows(modules.selected_22_codes || modules.ma24);
    var xiaoRows = distinctRows(modules["9xzt"]);
    var waveRows = distinctRows(modules.shuangbo);
    Array.prototype.forEach.call(document.querySelectorAll("#yxym table.yxym"), function (table, index) {
      var codeRow = codeRows[index];
      var xiaoRow = xiaoRows[index] || codeRow;
      var waveRow = waveRows[index] || codeRow;
      Array.prototype.forEach.call(rows(table), function (row, rowIndex) {
        var source = rowIndex < 4 ? codeRow : rowIndex < 12 ? xiaoRow : waveRow;
        if (!source) return writeRow(row, "", "暂无后端资料", "");
        var codeCount = [1, 3, 5, 7][rowIndex];
        var xiaoCount = rowIndex >= 4 && rowIndex <= 11 ? rowIndex - 3 : 0;
        var value = codeCount ? codeValues(source).slice(0, codeCount).join(".") : xiaoCount ? labels(source).slice(0, xiaoCount).join("") : listValue(rawValue(source, "wave")).slice(0, 2).join("+");
        var label = ["一码", "三码", "五码", "七码", "一肖", "二肖", "三肖", "四肖", "五肖", "六肖", "七肖", "九肖", "波色"][rowIndex] || "";
        writeRow(row, issueOf(source) + "期:" + label, value || "暂无后端资料", resultText(source), "", source.result && source.result.isCorrect === true);
      });
    });
  }

  function renderBuyWhatOpens(modules) { renderThreeColumnHistory("msks", modules.title_14, function (row) { return labels(row).slice(0, 1).join("") || "暂无后端资料"; }); }
  function renderKillThreeXiao(modules) { renderThreeColumnHistory("wsxx", modules.juesha3xiao, function (row) { return "杀三肖『" + labels(row).slice(0, 3).join("") + "』"; }); }
  function renderFourXiao(modules) { renderThreeColumnHistory("wl4x", modules.sixiao_sima, function (row) { return labels(row).slice(0, 4).join("") || "暂无后端资料"; }); }
  function renderBigSmall(modules) { renderThreeColumnHistory("dxzt", modules.daxiao, function (row) { var value = String(rawValue(row, "daxiao") || labels(row)[0] || ""); return value === "大" ? "大数" : value === "小" ? "小数" : value || "暂无后端资料"; }); }
  function renderFiveTail(modules) { renderThreeColumnHistory("5wzt", modules.title_66, function (row) { return listValue(rawValue(row, "tail")).slice(0, 5).join("-") || labels(row).slice(0, 5).join("-") || "暂无后端资料"; }); }
  function renderSelectedTwentyFour(modules) { renderThreeColumnHistory("jx24m", modules.ma24, function (row) { return codeValues(row).slice(0, 24).join("-") || "暂无后端资料"; }); }
  function renderFourSegments(modules) { renderThreeColumnHistory("sdzt", modules.siduanzhongte, function (row) { return labels(row).slice(0, 4).join("+") || "暂无后端资料"; }); }
  function renderOneWave(modules) { renderThreeColumnHistory("ybzt", modules.title_143, function (row) { return listValue(rawValue(row, "wave")).slice(0, 1).join("") || labels(row).slice(0, 1).join("") || "暂无后端资料"; }); }
  function renderHeavenEarth(modules) { renderThreeColumnHistory("tdsx", modules.title_5, function (row) { return labels(row).slice(0, 3).join("+") || "暂无后端资料"; }); }
  function renderThreeHeads(modules) { renderThreeColumnHistory("3tzt", modules["3tou"], function (row) { return labels(row).slice(0, 3).join("-") || "暂无后端资料"; }); }
  function renderSumBigSmall(modules) { renderThreeColumnHistory("hsdx", modules.title_279, function (row) { return labels(row).slice(0, 1).join("") || "暂无后端资料"; }); }
  function renderFlatOneXiao(modules) { renderThreeColumnHistory("pt1xiao", modules.pt1xiao, function (row) { return labels(row).slice(0, 1).join("") || "暂无后端资料"; }); }
  function renderSumOddEven(modules) { renderThreeColumnHistory("hsds", modules.title_132, function (row) { return labels(row).slice(0, 1).join("") || "暂无后端资料"; }); }
  function renderMusicChess(modules) { renderThreeColumnHistory("qqsh", modules.qinqi, function (row) { return labels(row).slice(0, 2).join("") || "暂无后端资料"; }); }
  function renderLuckyOminousSixXiao(modules) { renderThreeColumnHistory("jxzt", modules["6xzt"], function (row) { return labels(row).slice(0, 6).join("") || "暂无后端资料"; }); }
  function renderFiveElements(modules) { renderThreeColumnHistory("jz5x", modules["3hang"], function (row) { return labels(row).slice(0, 3).join("+") || "暂无后端资料"; }); }
  function renderOddEvenFourXiao(modules) {
    var sourceRows = distinctRows(modules.danshuang4xiao);
    rows(section("dssx")).forEach(function (row, index) {
      var source = sourceRows[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", "");
      writeRow(
        row,
        issueOf(source) + "期",
        String(rawValue(source, "xiao_1") || labels(source).slice(0, 4).join("")),
        resultText(source),
        String(rawValue(source, "xiao_2") || labels(source).slice(4, 8).join("")),
        source.result && source.result.isCorrect === true
      );
    });
  }

  function renderPredictions(envelope) {
    var modules = modulesByKey(envelope);
    renderBuyWhatOpens(modules);
    renderKillThreeXiao(modules);
    renderOneCodeOneXiaoTable(modules);
    renderFourXiao(modules);
    renderBigSmall(modules);
    renderLuckyOminousSixXiao(modules);
    renderFiveElements(modules);
    renderFiveTail(modules);
    renderSelectedTwentyFour(modules);
    renderOddEvenFourXiao(modules);
    renderFourSegments(modules);
    renderOneWave(modules);
    renderHeavenEarth(modules);
    renderThreeHeads(modules);
    renderSumBigSmall(modules);
    renderFlatOneXiao(modules);
    renderSumOddEven(modules);
    renderMusicChess(modules);
  }

  function renderDrawPanel(envelope) {
    var data = envelope && envelope.data && envelope.data.data || {};
    var frame = knownDrawFrame && knownDrawFrame.contentDocument;
    if (!frame) return;
    var target = frame.querySelector("[data-current-issue]");
    if (target) target.textContent = String(data.issue || data.current_issue || "");
  }

  function selectLottery(lotteryType) {
    lotteryType = Number(lotteryType);
    if (![1, 2, 3].includes(lotteryType)) return;
    activeLotteryType = lotteryType;
    client.loadDraw({ lotteryType: lotteryType }).then(function (envelope) {
      if (activeLotteryType === lotteryType && envelope.data) renderDrawPanel(envelope);
    });
    client.loadPredictions({ lotteryType: lotteryType, historyLimit: 8 }).then(function (envelope) {
      if (activeLotteryType !== lotteryType || !envelope.data) return;
      renderPredictions(envelope);
      window.dispatchEvent(new window.CustomEvent("site-data:ready", { detail: { siteKey: siteConfig.siteKey, resource: "predictions", state: envelope.state } }));
    });
  }

  window.addEventListener("message", function (event) {
    if (event.origin !== window.location.origin || event.source !== knownDrawFrame.contentWindow) return;
    var message = event.data || {};
    if (message.type === "lottery-change" && message.siteKey === siteConfig.siteKey) selectLottery(message.lotteryType);
  });

  window.TwwanliSiteDataAdapter = { selectLottery: selectLottery, siteConfig: siteConfig };
  selectLottery(activeLotteryType);
})(window, document);


