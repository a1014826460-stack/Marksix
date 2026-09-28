(function (window, document) {
  "use strict";

  var siteConfig = window.TwsywSiteConfig;
  if (!siteConfig || !window.LotterySiteDataClient) return;

  var client = window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey });
  var activeLotteryType = 3;
  // 开奖标签页与面板已内联进本页（原先在独立开奖页里），面板 iframe 由 KJTB 在本页创建，
  // 因此这里惰性查找，不能在脚本加载时就抓那个中间 frame。
  function drawPanelFrame() {
    return document.querySelector(".KJ-TabBox .KJ-IFRAME");
  }

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
  // 读取「不在 tokens 里」的候选列（如 mode 5 天地生肖的 `xiao`）。
  // tokens 是对外契约不能改，候选列只能从 canonical row 的 raw / prediction.extra 里取。
  function rawField(row, key) {
    var raw = row && row.raw;
    if (raw && raw[key] !== undefined && raw[key] !== null && String(raw[key]).trim() !== "") return raw[key];
    var extra = row && row.prediction && row.prediction.extra;
    return extra ? extra[key] : undefined;
  }
  function tokens(row) {
    var value = row && row.prediction && row.prediction.tokens;
    return Array.isArray(value) ? value.map(String).filter(Boolean) : predictionText(row).split(/[|,，、\s]+/).filter(Boolean);
  }
  // 候选集合可能以整串 `标签|号码` 的形式出现在 tokens 里（含 JSON 包装），
  // 统一剥掉 `[` `]` `"` `'`，避免把原始 JSON 残留渲染到页面上（S5）。
  function labels(row) { return tokens(row).map(function (value) { return String(value).split("|")[0].replace(/[\[\]"']/g, "").split(";").pop().trim(); }).filter(Boolean); }
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
  function writeRow(row, term, content, opened, hit, contentHtml) {
    var issue = row.querySelector("[data-prediction-issue]");
    var value = row.querySelector("[data-prediction-content]");
    var result = row.querySelector("[data-prediction-result]");
    Array.prototype.forEach.call(row.querySelectorAll("[data-prediction-hit]"), function (node) { node.removeAttribute("data-prediction-hit"); });
    issue.textContent = term || "";
    // contentHtml 用于「一行多个候选项、只有一个命中」的模块：只能给命中的那一项
    // 加 data-prediction-hit，整块上黄底会把没命中的候选项也点亮（S2）。
    if (contentHtml) value.innerHTML = contentHtml;
    else value.textContent = content || "";
    result.textContent = opened || "";
    if (hit && !contentHtml) value.setAttribute("data-prediction-hit", "true");
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // 一行多个候选项时，只把真正命中的那一项包进 data-prediction-hit。
  function highlightOnly(items, hitValue, joiner) {
    return items.map(function (item) {
      var text = String(item == null ? "" : item);
      return text && text === hitValue
        ? '<span data-prediction-hit="true">' + escapeHtml(text) + "</span>"
        : escapeHtml(text);
    }).join(joiner == null ? "" : joiner);
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
  // 天地生肖（mode 5）的真实候选是 `xiao` 列的 2 个生肖；`content` 只是静态的
  // 「天肖/地肖」分组定义（整组 6 肖）。后端正是按 `xiao` 判定的，
  // 直接渲染 content 会让展示值几乎恒定（S7），并且出现「天肖里含开奖特肖却显示错」。
  function chosenZodiacs(row) {
    var values = [];
    var raw = rawField(row, "xiao");
    if (Array.isArray(raw)) values = raw.map(String).filter(Boolean);
    else if (typeof raw === "string") values = raw.split(/[|,，、\s]+/).map(function (v) { return v.trim(); }).filter(Boolean);
    if (!values.length) {
      labels(row).forEach(function (label) {
        String(label).split(/[,，、\s]+/).forEach(function (part) {
          var value = part.trim();
          if (/^[鼠牛虎兔龙蛇马羊猴鸡狗猪]$/.test(value) && values.indexOf(value) < 0) values.push(value);
        });
      });
    }
    return values;
  }
  function selectedCodes(row, count) { return numbers(row).slice(0, count).join("."); }
  function xiaoCodes(row, count) { return labels(row).slice(0, count).join(""); }
  function contentWithLabel(label, value) { return label + "资料：" + (value || "暂无后端资料"); }
  // 特码 / 特肖（canonical row 的 result 字段）。
  function specialParts(row) {
    var result = row && row.result || {};
    var last = function (value) {
      var items = String(value || "").split(/[,，、|\s]+/).filter(Boolean);
      return items.length ? items[items.length - 1] : "";
    };
    var code = last(result.code);
    if (/^\d$/.test(code)) code = "0" + code;
    return { code: code, zodiac: last(result.zodiac) };
  }

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
  // 天地肖固定分组（与 `public.fixed_data` sign='天地肖' 及各站 sx.html 一致）。
  var TIANDI_GROUPS = {
    "天肖": ["兔", "马", "猴", "猪", "牛", "龙"],
    "地肖": ["鼠", "虎", "蛇", "羊", "鸡", "狗"]
  };
  function tiandiGroup(sideLabel) {
    var value = String(sideLabel || "");
    if (value.indexOf("天") === 0) return TIANDI_GROUPS["天肖"];
    if (value.indexOf("地") === 0) return TIANDI_GROUPS["地肖"];
    return [];
  }

  // 男女中特（`#nannv`）由 mode 5（天地生肖）供数：展示「天肖/地肖 + 本期 2 个候选生肖」。
  // 该机制的候选是双维度：`content` 的天地分组（天肖/地肖各 6 肖）+ `xiao` 列的 2 个候选肖。
  // vendor/接口的 `is_correct` 只比对 `xiao`（`mechanisms.py` 的 hit_checker=contains_hit），
  // 天地组永远不参与判定，于是「天肖里含开奖特肖」的期会显示「错」（270 期「天肖+兔鸡」
  // 开 37 马）。这里本地复算并集：特肖 ∈ 天地组 ∪ 两肖 任一即命中，与 twwanli /
  // twcaibawang 的天地两肖口径一致；未开奖不做判定也不高亮。
  function renderNannv(modules) {
    var sourceRows = distinctRows(modules.title_5);
    historyRows(section("nannv")).forEach(function (row, index) {
      var source = sourceRows[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      var side = labels(source).slice(0, 1).join("") || "天地肖";
      var chosen = chosenZodiacs(source);
      if (!chosen.length) return writeRow(row, "", "暂无后端资料", "", false);
      var parts = specialParts(source);
      // 未开奖 / 拿不到特肖时不做本地复算，沿用既有口径（待开奖或原始判定）。
      var opened = Boolean(source.result && source.result.isOpened && parts.zodiac);
      var inGroup = opened && tiandiGroup(side).indexOf(parts.zodiac) >= 0;
      var inChosen = opened && chosen.indexOf(parts.zodiac) >= 0;
      var hit = inGroup || inChosen;
      // 只点亮真正命中的那一项：命中两肖 → 点亮那个生肖；命中天地组 → 点亮组名。
      // 两项都命中时优先点亮生肖（与 twwanli `renderHeavenEarth` 一致）。
      var sideHtml = inGroup && !inChosen
        ? '<span data-prediction-hit="true">' + escapeHtml(side) + "</span>"
        : escapeHtml(side);
      var chosenHtml = highlightOnly(chosen, inChosen ? parts.zodiac : "", "");
      writeRow(
        row,
        issueOf(source) + "期",
        "",
        opened ? "开:" + (parts.code ? parts.code : "") + parts.zodiac + (hit ? "对" : "错") : resultText(source),
        false,
        "天地生肖资料：【" + sideHtml + "+" + chosenHtml + "】"
      );
    });
  }
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
  function renderKill1tou(modules) {
    // 绝杀一头（`#kill1tou`）由 mode 3tou（三头中特）供数，后端判定是
    // 「特码头落在 3 个候选头之内」。因此必须把 3 个候选头都展示出来：
    // 只显示第一个候选会让展示值连续多期完全相同（S7，审计 R5：
    // 线上 270/269/268/267 四期都是「3头」），而且判定依据的第 2、3 个候选项
    // 根本不可见，命中时也无从高亮。命中时只给命中的那个头上黄底。
    var sourceRows = distinctRows(modules["3tou"]);
    historyRows(section("kill1tou")).forEach(function (row, index) {
      var source = sourceRows[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      var heads = headLabels(source, 3);
      if (!heads.length) return writeRow(row, "", "暂无后端资料", "", false);
      var isHit = source.result && source.result.isCorrect === true;
      var digits = String(specialParts(source).code || "").replace(/[^0-9]/g, "");
      var hitHead = isHit && digits ? digits.charAt(0) + "头" : "";
      var body = hitHead && heads.indexOf(hitHead) >= 0
        ? highlightOnly(heads, hitHead, ".")
        : heads.map(escapeHtml).join(".");
      writeRow(row, issueOf(source) + "期", "", resultText(source), false, contentWithLabel("三头", body));
    });
  }
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
  function renderDraw(envelope) { var target = document.querySelector("[data-current-issue]"), data = envelope && envelope.data && envelope.data.data || {}; if (target) target.textContent = String(data.issue || data.current_issue || ""); }
  function selectLottery(type) {
    type = Number(type); if (![1, 2, 3].includes(type)) return;
    activeLotteryType = type; updateTitles(type);
    client.loadDraw({lotteryType:type}).then(function (envelope) { if (activeLotteryType === type && envelope.data) renderDraw(envelope); });
    client.loadPredictions({lotteryType:type,historyLimit:20}).then(function (envelope) { if (activeLotteryType !== type || !envelope.data) return; renderPredictions(envelope); window.dispatchEvent(new window.CustomEvent("site-data:ready", { detail: { siteKey: siteConfig.siteKey, resource: "predictions", state: envelope.state } })); });
  }
  // 彩种切换：标签页点击由内联脚本直接调用 selectLottery（原先靠 kai.html 的 postMessage）。
  // 这里仍保留对面板自身消息的兼容处理，但不依赖任何中间 iframe。
  window.addEventListener("message", function (event) { if (event.origin !== window.location.origin) return; var message = event.data || {}; if (message.type !== "lottery-change" || message.siteKey !== siteConfig.siteKey) return; var frame = drawPanelFrame(); if (frame && event.source !== frame.contentWindow) return; selectLottery(message.lotteryType); });
  window.TwsywSiteDataAdapter = { selectLottery: selectLottery, siteConfig: siteConfig };
  selectLottery(activeLotteryType);
})(window, document);
