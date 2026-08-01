(function (window, document) {
  "use strict";

  var siteConfig = window.TwsywSiteConfig;
  if (!siteConfig || !window.LotterySiteDataClient) return;

  var client = window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey });
  var activeLotteryType = 3;
  var knownDrawFrame = document.querySelector("iframe[src='kai.html']");

  function modulesByKey(envelope) {
    var data = envelope && envelope.data && envelope.data.data || {};
    return (data.canonical_modules || data.modules || []).reduce(function (all, module) {
      var key = String(module && (module.key || module.moduleKey) || "");
      if (key) all[key] = module;
      return all;
    }, {});
  }

  function issueOf(row) { return String(row && (row.issue || row.term || "") || "").replace(/^第/, "").replace(/期$/, "").trim(); }
  function distinctRows(module) {
    var seen = {};
    return (module && Array.isArray(module.rows) ? module.rows : []).filter(function (row) {
      var value = issueOf(row);
      if (!value || seen[value]) return false;
      seen[value] = true;
      return true;
    });
  }
  function predictionText(row) { return String(row && row.prediction && row.prediction.text || "").replace(/[\[\]"]/g, "").trim(); }
  function tokens(row) {
    var value = row && row.prediction && row.prediction.tokens;
    return Array.isArray(value) ? value.map(String).filter(Boolean) : predictionText(row).split(/[|,，、\s]+/).filter(Boolean);
  }
  function labels(row) { return tokens(row).map(function (value) { return value.split("|")[0].split(";").pop().trim(); }).filter(Boolean); }
  function numbers(row) {
    var list = [];
    tokens(row).forEach(function (value) { (String(value).match(/\d{1,2}/g) || []).forEach(function (number) { list.push(("0" + number).slice(-2)); }); });
    return list;
  }
  function tailLabels(row) { return labels(row).filter(function (value) { return /尾$/.test(value); }); }
  function groupLabels(row) { return labels(row).filter(function (value) { return /^(?:[0-9]+段|[0-9]+头)$/.test(value); }); }
  function resultText(row) {
    var result = row && row.result || {};
    if (!result.isOpened) return "开:待开奖";
    var last = function (value) { var items = String(value || "").split(/[,，、|\s]+/).filter(Boolean); return items[items.length - 1] || ""; };
    var code = last(result.code), zodiac = last(result.zodiac);
    if (/^\d$/.test(code)) code = "0" + code;
    return "开:" + (code && zodiac ? code + zodiac : String(result.text || "暂无后端资料")) + (result.isCorrect === true ? "对" : result.isCorrect === false ? "错" : "");
  }
  function predictionImageUrl(row) {
    var prediction = row && row.prediction || {};
    return String(prediction.imageUrl || row && row.image_url || row && row.raw && row.raw.image_url || "").trim();
  }
  function section(id) { return document.getElementById(id); }
  function historyRows(root) { return root ? Array.prototype.filter.call(root.querySelectorAll("tr"), function (row) { return row.querySelector("[data-prediction-issue]"); }) : []; }
  function writeRow(row, term, content, opened, hit) {
    var issue = row.querySelector("[data-prediction-issue]");
    var value = row.querySelector("[data-prediction-content]");
    var result = row.querySelector("[data-prediction-result]");
    Array.prototype.forEach.call(row.querySelectorAll("[data-prediction-hit]"), function (node) { node.removeAttribute("data-prediction-hit"); });
    issue.textContent = term || "";
    value.textContent = content || "";
    result.textContent = opened || "";
    if (hit) value.setAttribute("data-prediction-hit", "true");
  }
  function renderHistory(id, module, formatter) {
    var source = distinctRows(module);
    historyRows(section(id)).forEach(function (row, index) {
      var current = source[index];
      if (!current) return writeRow(row, "", "暂无后端资料", "", false);
      writeRow(row, issueOf(current) + "期", formatter(current) || "暂无后端资料", resultText(current), current.result && current.result.isCorrect === true);
    });
  }
  function domesticWild(row) {
    var parts = predictionText(row).split(";");
    var domestic = parts[0] && parts[0].replace(/^家禽\|?/, "").replace(/[|,]/g, "") || "";
    var wild = parts[1] && parts[1].replace(/^野兽\|?/, "").replace(/[|,]/g, "") || "";
    return "家禽野兽资料：家禽 " + domestic + "；野兽 " + wild;
  }
  function heavenly(row) { return predictionText(row).replace("|", "：").replace(/,/g, ""); }
  function selectedCodes(row, count) { return numbers(row).slice(0, count).join("."); }
  function xiaoCodes(row, count) { return labels(row).slice(0, count).join(""); }
  function contentWithLabel(label, value) { return label + "资料：" + (value || "暂无后端资料"); }

  function renderFslx(modules) { renderHistory("fslx", modules.title_14, domesticWild); }
  function renderM24(modules) { renderHistory("m24", modules.ma24, function (row) { return selectedCodes(row, 24); }); }
  function renderDaxiao(modules) { renderHistory("daxiao", modules.daxiao, function (row) { return labels(row).slice(0, 1).join(""); }); }
  function renderJiaye(modules) { renderHistory("jiaye", modules.title_14, domesticWild); }
  function renderQixiao(modules) { renderHistory("qixiao", modules["9xzt"], function (row) { return xiaoCodes(row, 7); }); }
  function renderJiaye4xiao(modules) { renderHistory("jiaye4xiao", modules.sixiao_sima, function (row) { return contentWithLabel("四肖四码", xiaoCodes(row, 4)); }); }
  function renderGold6xiao(modules) {
    var nine = distinctRows(modules["9xzt"]), flat = distinctRows(modules.pt1xiao);
    historyRows(section("gold6xiao")).forEach(function (row, index) {
      var source = nine[index] || flat[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      writeRow(row, issueOf(source) + "期", "九肖资料：" + xiaoCodes(nine[index], 6) + "；平特一肖资料：" + xiaoCodes(flat[index], 1), resultText(source), source.result && source.result.isCorrect === true);
    });
  }
  function renderPt1wei(modules) { renderHistory("pt1wei", modules.title_66, function (row) { return contentWithLabel("五尾", tailLabels(row).join(" ")); }); }
  function renderWinner12(modules) { renderHistory("winner12", modules.selected_22_codes, function (row) { return contentWithLabel("精选22码", selectedCodes(row, 12)); }); }
  function renderJiuxiao(modules) { renderHistory("jiuxiao", modules["9xzt"], function (row) { return xiaoCodes(row, 9); }); }
  function renderLianma(modules) {
    var code = distinctRows(modules.ma24), segment = distinctRows(modules.siduanzhongte);
    historyRows(section("lianma")).forEach(function (row, index) {
      var source = code[index] || segment[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      writeRow(row, issueOf(source) + "期", "24码资料：" + selectedCodes(code[index], 12) + "；四段资料：" + groupLabels(segment[index]).join(" "), resultText(source), source.result && source.result.isCorrect === true);
    });
  }
  function renderNannv(modules) { renderHistory("nannv", modules.title_5, function (row) { return contentWithLabel("天地生肖", heavenly(row)); }); }
  function renderDanshuang(modules) {
    var parity = distinctRows(modules.title_132), size = distinctRows(modules.title_279);
    historyRows(section("danshuang")).forEach(function (row, index) {
      var source = parity[index] || size[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      writeRow(row, issueOf(source) + "期", "合数单双资料：" + predictionText(parity[index]) + "；合数大小资料：" + predictionText(size[index]), resultText(source), source.result && source.result.isCorrect === true);
    });
  }
  function renderDssx(modules) { renderHistory("dssx", modules.danshuang4xiao, function (row) { return xiaoCodes(row, 8); }); }
  function renderHblvxiao(modules) {
    var doubleWave = distinctRows(modules.shuangbo), singleWave = distinctRows(modules.title_143);
    historyRows(section("hblvxiao")).forEach(function (row, index) {
      var source = doubleWave[index] || singleWave[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      writeRow(row, issueOf(source) + "期", "双波资料：" + labels(doubleWave[index]).slice(0, 2).join(" ") + "；一波资料：" + predictionText(singleWave[index]), resultText(source), source.result && source.result.isCorrect === true);
    });
  }
  function headLabels(row, count) { var values = groupLabels(row); return (values.length ? values : labels(row)).slice(0, count); }
  function renderSantou(modules) { renderHistory("santou", modules["3tou"], function (row) { return headLabels(row, 3).join("."); }); }
  function renderQiw(modules) { renderHistory("qiw", modules.title_66, function (row) { return contentWithLabel("五尾", tailLabels(row).join(" ")); }); }
  function renderKill4xiao(modules) { renderHistory("kill4xiao", modules.sixiao_sima, function (row) { return contentWithLabel("四肖", xiaoCodes(row, 4)); }); }
  function renderKill3wei(modules) { renderHistory("kill3wei", modules.title_66, function (row) { return contentWithLabel("五尾", tailLabels(row).slice(0, 3).join(" ")); }); }
  function renderChengyu(modules) { renderHistory("chengyu", modules.qinqi, function (row) { return contentWithLabel("琴棋书画", xiaoCodes(row, 9)); }); }
  function renderShuangbo(modules) { renderHistory("shuangbo", modules.shuangbo, function (row) { return labels(row).slice(0, 2).join(""); }); }
  function renderKill1tou(modules) { renderHistory("kill1tou", modules["3tou"], function (row) { return contentWithLabel("三头", headLabels(row, 1).join("")); }); }
  function renderFiveNoHit(modules) { renderHistory("five_no_hit", modules.selected_22_codes, function (row) { return contentWithLabel("五码", selectedCodes(row, 5)); }); }
  function renderCompositeKill(modules) {
    var kill = distinctRows(modules.juesha3xiao);
    var tail = distinctRows(modules.title_66);
    var head = distinctRows(modules["3tou"]);
    var parity = distinctRows(modules.title_132);
    historyRows(section("composite_kill")).forEach(function (row, index) {
      var source = kill[index] || tail[index] || head[index] || parity[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      var content = "绝杀三肖：" + xiaoCodes(kill[index], 3) + "；五尾资料：" + tailLabels(tail[index]).join(" ") + "；三头资料：" + headLabels(head[index], 3).join(" ") + "；合数单双：" + predictionText(parity[index]);
      writeRow(row, issueOf(source) + "期", content, resultText(source), source.result && source.result.isCorrect === true);
    });
  }
  function renderPredictionImage(moduleKey, module) {
    var image = document.querySelector("img[data-prediction-image='" + moduleKey + "']");
    if (!image) return;
    var row = distinctRows(module)[0];
    var url = predictionImageUrl(row);
    image.setAttribute("src", url);
    if (url) image.removeAttribute("hidden"); else image.setAttribute("hidden", "hidden");
  }
  function renderTopXiaoCode(modules) {
    var xiao = distinctRows(modules["9xzt"]), ma = distinctRows(modules.ma24), names = ["八肖", "五肖", "三肖", "一肖", "10码", "6码", "1码"];
    var headerIssues = document.querySelectorAll("[data-prediction-draw-issue]");
    var headerResults = document.querySelectorAll("[data-prediction-draw-result]");
    Array.prototype.forEach.call(headerIssues, function (node, index) { var source = xiao[index] || ma[index]; node.textContent = source ? issueOf(source) + "期" : ""; if (headerResults[index]) headerResults[index].textContent = source ? resultText(source) : ""; });
    historyRows(section("top_xiao_code")).forEach(function (row, index) {
      var group = Math.floor(index / 7), slot = index % 7, source = slot < 4 ? xiao[group] : ma[group];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      var content = slot < 4 ? xiaoCodes(source, [8, 5, 3, 1][slot]) : selectedCodes(source, [10, 6, 1][slot - 4]);
      writeRow(row, issueOf(source) + "期 " + names[slot], content || "暂无后端资料", resultText(source), source.result && source.result.isCorrect === true);
    });
  }
  function renderPredictions(envelope) {
    var modules = modulesByKey(envelope);
    renderPredictionImage("pmtj_image", modules.pmtj_image); renderTopXiaoCode(modules); renderFslx(modules); renderM24(modules); renderDaxiao(modules); renderJiaye(modules); renderQixiao(modules); renderJiaye4xiao(modules); renderGold6xiao(modules); renderPt1wei(modules); renderWinner12(modules); renderPredictionImage("brainteaser", modules.brainteaser); renderJiuxiao(modules); renderLianma(modules); renderNannv(modules); renderDanshuang(modules); renderDssx(modules); renderHblvxiao(modules); renderSantou(modules); renderQiw(modules); renderKill4xiao(modules); renderKill3wei(modules); renderChengyu(modules); renderShuangbo(modules); renderKill1tou(modules); renderFiveNoHit(modules); renderCompositeKill(modules);
  }
  function updateTitles(type) {
    var lottery = siteConfig.lotteries.filter(function (item) { return item.lotteryType === type; })[0];
    Array.prototype.forEach.call(document.querySelectorAll("[data-lottery-title]"), function (node) { node.textContent = lottery.label; });
    Array.prototype.forEach.call(document.querySelectorAll("[data-site-domain]"), function (node) { node.textContent = siteConfig.siteDomain; });
  }
  function renderDraw(envelope) { var frame = knownDrawFrame && knownDrawFrame.contentDocument, target = frame && frame.querySelector("[data-current-issue]"), data = envelope && envelope.data && envelope.data.data || {}; if (target) target.textContent = String(data.issue || data.current_issue || ""); }
  function selectLottery(type) {
    type = Number(type); if (![1, 2, 3].includes(type)) return;
    activeLotteryType = type; updateTitles(type);
    client.loadDraw({lotteryType:type}).then(function (envelope) { if (activeLotteryType === type && envelope.data) renderDraw(envelope); });
    client.loadPredictions({lotteryType:type,historyLimit:20}).then(function (envelope) { if (activeLotteryType !== type || !envelope.data) return; renderPredictions(envelope); window.dispatchEvent(new window.CustomEvent("site-data:ready", { detail: { siteKey: siteConfig.siteKey, resource: "predictions", state: envelope.state } })); });
  }
  window.addEventListener("message", function (event) { if (event.origin !== window.location.origin || !knownDrawFrame || event.source !== knownDrawFrame.contentWindow) return; var message = event.data || {}; if (message.type === "lottery-change" && message.siteKey === siteConfig.siteKey) selectLottery(message.lotteryType); });
  window.TwsywSiteDataAdapter = { selectLottery: selectLottery, siteConfig: siteConfig };
  selectLottery(activeLotteryType);
})(window, document);
