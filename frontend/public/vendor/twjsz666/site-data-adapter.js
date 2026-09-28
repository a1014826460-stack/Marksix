(function (window) {
  "use strict";

  var siteConfig = window.Twjsz666SiteConfig;
  if (!siteConfig) return;

  var SECTION_CONTRACTS = Object.freeze([
    { id: "four-xiao-odds", titlePattern: "单双各四肖", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["danshuang4xiao"], rendererName: "renderFourXiaoOdds", issueGroups: 9, supplierSentinels: ["单肖"] },
    { id: "one-head-one-code", titlePattern: "单车变宝马", containerSelector: ".pad#yxym", classification: "composite", moduleKeys: ["sitouzhongte", "ma24"], rendererName: "renderOneHeadOneCode", issueGroups: 9, supplierSentinels: ["24码中特"] },
    { id: "fortune-nine-xiao", titlePattern: "发财⑨肖", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["9xzt"], rendererName: "renderFortuneNineXiao", issueGroups: 9, supplierSentinels: ["发财⑨肖"] },
    { id: "three-head-four-tail", titlePattern: "三头", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["three_head_four_tail"], rendererName: "renderThreeHeadFourTail", issueGroups: 9, supplierSentinels: ["三头"] },
    { id: "flat-one-xiao", titlePattern: "平特一肖", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["pt1xiao"], rendererName: "renderPingTeXiaoHistory", issueGroups: 9, supplierSentinels: ["平特一肖"] },
    { id: "four-character-flat-xiao", titlePattern: "四字解平特肖", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["sizixuanji"], rendererName: "renderFourCharacterFlatXiao", issueGroups: 9, supplierSentinels: ["四字解"] },
    { id: "expert-publications", titlePattern: "精准台湾高手", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["expert_publications"], rendererName: "renderExpertPublications", issueGroups: 1, supplierSentinels: ["临高高手", "060期"] },
    { id: "official-gallery", titlePattern: "正版图库", containerSelector: ".box.pad", classification: "static", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 0, supplierSentinels: ["正版图库"] },
    { id: "double-wave", titlePattern: "双波", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["shuangbo"], rendererName: "renderShuangBoHistory", issueGroups: 9, supplierSentinels: ["双波"] },
    { id: "poultry-versus-beast", titlePattern: "家禽VS野兽", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["title_14"], rendererName: "renderPoultryBeast", issueGroups: 9, supplierSentinels: ["家禽"] },
    { id: "flat-three-xiao", titlePattern: "平特③肖", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["pt3xiao"], rendererName: "renderFlatThreeXiao", issueGroups: 9, supplierSentinels: ["平特③肖"] },
    { id: "four-xiao-eight-code", titlePattern: "④肖⑧码", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["4xiao8ma"], rendererName: "renderFourXiaoEightCode", issueGroups: 9, supplierSentinels: ["④肖⑧码"] },
    { id: "big-small-special", titlePattern: "大小中特", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["daxiao"], rendererName: "renderDaXiaoHistory", issueGroups: 9, supplierSentinels: ["大小中特"] },
    { id: "seven-tail-special", titlePattern: "七尾中特", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["title_74"], rendererName: "renderSevenTail", issueGroups: 9, supplierSentinels: ["七尾"] },
    { id: "before-bet-selection", titlePattern: "小康早到来", containerSelector: ".box.pad", classification: "composite", moduleKeys: ["selected_22_codes", "9xzt", "danshuang4xiao", "6xzt", "4xiao8ma", "pt2xiao"], rendererName: "renderPublicCards", issueGroups: 9, supplierSentinels: ["精选："] },
    { id: "flat-one-tail", titlePattern: "平特一尾", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["pt1wei"], rendererName: "renderFlatOneTail", issueGroups: 9, supplierSentinels: ["平特一尾"] },
    { id: "selected-twenty-two-code", titlePattern: "精选22码", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["selected_22_codes"], rendererName: "renderSelectedTwentyTwo", issueGroups: 9, supplierSentinels: ["精选22码"] },
    { id: "kill-two-xiao", titlePattern: "绝杀二肖", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["juesha2xiao"], rendererName: "renderKillTwoXiao", issueGroups: 9, supplierSentinels: ["绝杀二肖"] },
    { id: "kill-one-wave", titlePattern: "绝杀①半波", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["jueshabanbo"], rendererName: "renderKillOneWave", issueGroups: 9, supplierSentinels: ["绝杀①半波"] },
    { id: "kill-one-tail", titlePattern: "绝杀①尾", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["juesha1wei"], rendererName: "renderKillOneTail", issueGroups: 9, supplierSentinels: ["绝杀①尾"] },
    { id: "kill-seven-code", titlePattern: "稳杀⑦码", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["steady_kill_7_codes"], rendererName: "renderKillSevenCode", issueGroups: 9, supplierSentinels: ["稳杀⑦码"] },
    { id: "one-sentence-special", titlePattern: "一句话中特码", containerSelector: ".box.pad", classification: "mapped", moduleKeys: ["yijuzhenyan"], rendererName: "renderOneSentenceSpecial", issueGroups: 9, supplierSentinels: ["一句话"] },
    { id: "zodiac-knowledge", titlePattern: "台湾金手指属性知识", containerSelector: ".box.pad", classification: "static", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 0, supplierSentinels: ["sx.html"] },
    { id: "fast-results-footer", titlePattern: "最快开奖", containerSelector: ".box.pad", classification: "static", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 0, supplierSentinels: ["白小姐"] },
    { id: "unified-attribute-footer", titlePattern: "属性知识", containerSelector: "#legacy-attribute-anchor", classification: "static", moduleKeys: [], rendererName: "renderStaticSection", issueGroups: 0, supplierSentinels: [] },
    { id: "public-before-bet-card-1", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(1)", classification: "composite", moduleKeys: ["wuxiao_wuma"], rendererName: "renderBeforeBetCards", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-2", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(2)", classification: "composite", moduleKeys: ["wuxiao_wuma"], rendererName: "renderBeforeBetCards", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-3", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(3)", classification: "composite", moduleKeys: ["wuxiao_wuma"], rendererName: "renderBeforeBetCards", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-4", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(4)", classification: "composite", moduleKeys: ["wuxiao_wuma"], rendererName: "renderBeforeBetCards", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-5", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(5)", classification: "composite", moduleKeys: ["wuxiao_wuma"], rendererName: "renderBeforeBetCards", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-6", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(6)", classification: "composite", moduleKeys: ["wuxiao_wuma"], rendererName: "renderBeforeBetCards", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-7", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(7)", classification: "composite", moduleKeys: ["wuxiao_wuma"], rendererName: "renderBeforeBetCards", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-8", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(8)", classification: "composite", moduleKeys: ["wuxiao_wuma"], rendererName: "renderBeforeBetCards", issueGroups: 1, supplierSentinels: ["㈤肖"] },
    { id: "public-before-bet-card-9", titlePattern: "买码之前先上", containerSelector: "table.qxtable:nth-of-type(9)", classification: "composite", moduleKeys: ["wuxiao_wuma"], rendererName: "renderBeforeBetCards", issueGroups: 1, supplierSentinels: ["㈤肖"] }
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

  function displayIssue(row) {
    var value = issueOf(row).replace(/^第/, "").replace(/期$/, "");
    var digits = value.replace(/\D/g, "");
    return (digits.length > 3 ? digits.slice(-3) : digits || value) + "期";
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

  function groupValues(row, key) {
    var groups = row && row.prediction && row.prediction.groups;
    if (!Array.isArray(groups)) return [];
    var group = groups.filter(function (item) { return item && item.key === key; })[0];
    return group && Array.isArray(group.tokens) ? group.tokens.map(String).filter(Boolean) : [];
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

  function renderShuangBoHistory(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + ":双波"; },
      formatter: function (row) { return listValue(rawValue(row, "wave")).slice(0, 2).join("+") || formatLabels(row, "+").slice(0, 30); },
      wrap: function (value) { return "【" + value + "】"; },
      writeResult: true
    });
  }

  function renderPingTeXiaoHistory(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + ":平特一肖"; },
      formatter: function (row) { return listValue(rawValue(row, "xiao")).slice(0, 1).join("") || formatLabels(row, "").slice(0, 12); },
      wrap: function (value) { return "【" + value + "】"; },
      writeResult: true
    });
  }

  function renderDaXiaoHistory(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + ": "; },
      formatter: function (row) {
        var value = String(rawValue(row, "daxiao") || formatLabels(row, "") || "");
        return value === "大" ? "大数" : value === "小" ? "小数" : value;
      },
      writeResult: true
    });
  }

  function clearUnavailableSlots(section) {
    sectionRows(section).forEach(function (tr) {
      var cells = rowCells(tr);
      for (var index = 0; index < cells.length; index += 1) clearLeaves(cells[index]);
      if (cells[0]) writeLeaf(cells[0], "");
    });
  }

  function ensureDataAttrs(fonts, group, writeResult) {
    // Assign data-prediction-* attributes so CSS can enforce display:block
    // and contracts can locate the three independent leaf nodes.
    if (fonts[0] && !fonts[0].hasAttribute("data-prediction-issue")) {
      fonts[0].setAttribute("data-prediction-issue", "");
    }
    if (group && !group.hasAttribute("data-prediction-content")) {
      group.setAttribute("data-prediction-content", "");
    }
    // Only mark the result leaf when the module actually writes a result;
    // a writeResult:false module must not carry an empty semantic slot.
    if (writeResult && fonts.length > 1 && fonts[fonts.length - 1] && !fonts[fonts.length - 1].hasAttribute("data-prediction-result")) {
      fonts[fonts.length - 1].setAttribute("data-prediction-result", "");
    }
  }

  function renderInlineSlots(section, module, options) {
    var warnedLegacyFallback = false;
    Array.prototype.forEach.call(sectionRows(section), function (tr, index) {
      var row = rowData(module, index), cell = rowCells(tr)[0];
      var fonts = cell ? cell.querySelectorAll(":scope > font") : [];
      var group = tr.querySelector(".zl");
      if (!row) { clearLeaves(tr); if (fonts[0]) writeLeaf(fonts[0], ""); return; }
      var value = options.formatter(row);
      if (!group) {
        // Three-line standard: prefer data-prediction-* slots declared in HTML.
        var issueSlot = cell && cell.querySelector("[data-prediction-issue]");
        var contentSlot = cell && cell.querySelector("[data-prediction-content]");
        var resultSlot = cell && cell.querySelector("[data-prediction-result]");
        if (issueSlot && contentSlot) {
          setText(issueSlot, options.prefix(row));
          setText(contentSlot, options.wrap ? options.wrap(value) : value);
          if (options.writeResult !== false && resultSlot) setText(resultSlot, resultText(row));
        } else {
          // Legacy fallback: intentionally render ONLY the issue prefix.
          // Content and result are deliberately dropped — never concatenated
          // into one text node — so a module whose entry HTML lacks the
          // three data-prediction-* leaf nodes is visibly incomplete and
          // must be restructured to restore full rendering. Update the
          // entry HTML with data-prediction-issue/content/result leaves.
          if (!warnedLegacyFallback) {
            warnedLegacyFallback = true;
            if (typeof console !== "undefined" && typeof console.warn === "function") {
              console.warn("prediction module without data-prediction-* leaves: content/result hidden, restructure the entry HTML");
            }
          }
          if (fonts[0]) {
            setText(fonts[0], options.prefix(row));
            fonts[0].setAttribute("data-prediction-issue", "");
          }
        }
      } else {
        ensureDataAttrs(fonts, group, options.writeResult);
        setText(fonts[0], options.prefix(row));
        setText(group, options.wrap ? options.wrap(value) : value);
        if (options.writeResult) setText(fonts[fonts.length - 1], resultText(row));
      }
      // 黄底只能落在候选节点上：三行结构用 data-prediction-content 槽，旧结构用 .zl 分组；
      // 排除玩法（绝杀/杀号）没有可命中的候选，传 [] 保证零黄底。宁可不亮，
      // 也不允许像旧实现那样飘到同一行的「开:22羊对」上。
      var candidate = group || (cell && cell.querySelector("[data-prediction-content]")) || [];
      markPredictionRow(tr, row, index, options.noHighlight ? [] : candidate);
    });
  }

  function renderFortuneNineXiao(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + ": "; },
      formatter: function (row) { return formatLabels(row, "").slice(0, 36); },
      wrap: function (value) { return "【" + value + "】"; },
      writeResult: true
    });
  }

  function renderFlatThreeXiao(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + ": 平特③肖"; },
      formatter: function (row) { return formatLabels(row, "").slice(0, 24); },
      wrap: function (value) { return "【" + value + "】"; },
      writeResult: false
    });
  }

  function renderFlatOneTail(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + " 平特一尾："; },
      formatter: function (row) { return String(rawValue(row, "tail") || formatLabels(row, "、")).split(/[|,，、\s]+/).filter(Boolean).slice(0, 8).join("、"); }
    });
  }

  function renderKillTwoXiao(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + ": 绝杀二肖"; },
      formatter: function (row) { return listValue(rawValue(row, "xiao")).slice(0, 2).join(".") || formatLabels(row, ".").slice(0, 12); },
      wrap: function (value) { return "【" + value + "】"; },
      writeResult: true,
      // 排除玩法：判定「准」= 开奖目标**不在**候选里，本来就没有命中的候选文字可点亮。
      noHighlight: true
    });
  }

  function renderKillOneWave(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + ":绝杀①半波"; },
      formatter: function (row) { return String(rawValue(row, "wave") || formatLabels(row, "、")).split(/[|,，、\s]+/).filter(Boolean).slice(0, 1).join(""); },
      wrap: function (value) { return "【" + value + "】"; },
      writeResult: true,
      noHighlight: true
    });
  }

  function renderKillOneTail(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + ":绝杀"; },
      formatter: function (row) { return String(rawValue(row, "tail") || formatLabels(row, "、")).split(/[|,，、\s]+/).filter(Boolean).slice(0, 1).join(""); },
      writeResult: true,
      noHighlight: true
    });
  }

  function renderOneSentenceSpecial(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + " 一句话"; },
      formatter: function (row) { return String(rawValue(row, "sentence") || row && row.prediction && row.prediction.text || formatLabels(row, " ")).replace(/[|]/g, " ").trim().slice(0, 80); },
      wrap: function (value) { return "「" + value + "」"; },
      writeResult: true
    });
  }

  function renderStaticSection() {}
  function renderExpertPublications(section, module) {
    var row = distinctRows(module)[0];
    var publications = [];
    try { publications = JSON.parse(String(rawValue(row, "content") || "{}")) .publications || []; } catch (_) { publications = tokenValues(row); }
    Array.prototype.forEach.call(section.querySelectorAll("li"), function (item, index) {
      var link = item.querySelector("a");
      if (!link) return;
      clearLeaves(link);
      writeLeaf(link, row ? displayIssue(row) + " " + (publications[index] || "后端资料") : "");
    });
  }

  function normalizedIssue(row) {
    return displayIssue(row);
  }

  function setText(root, value) {
    if (!root) return;
    clearLeaves(root);
    writeLeaf(root, value);
  }

  function rowData(module, index) {
    return distinctRows(module)[index] || null;
  }

  function renderFourXiaoOdds(section, module) {
    Array.prototype.forEach.call(sectionRows(section), function (tr, index) {
      var row = rowData(module, index);
      var fonts = tr.querySelectorAll("font");
      var groups = tr.querySelectorAll(".zl");
      if (!row) { clearLeaves(tr); if (fonts[0]) writeLeaf(fonts[0], ""); return; }
      var single = listValue(rawValue(row, "single_xiao")).slice(0, 4);
      var doubled = listValue(rawValue(row, "double_xiao")).slice(0, 4);
      if (!single.length || !doubled.length) {
        var values = tokenValues(row);
        single = values.slice(0, 4); doubled = values.slice(4, 8);
      }
      setText(fonts[0], normalizedIssue(row) + ":单肖");
      setText(groups[0], "【" + single.join("") + "】");
      setText(fonts[1], "双肖");
      setText(groups[1], "【" + doubled.join("") + "】");
      markPredictionRow(tr, row, index, [groups[0], groups[1]]);
    });
  }

  function renderPoultryBeast(section, module) {
    Array.prototype.forEach.call(sectionRows(section), function (tr, index) {
      var row = rowData(module, index), cells = rowCells(tr), groups = tr.querySelectorAll(".zl");
      if (!row) { clearLeaves(tr); if (cells[0]) writeLeaf(cells[0], ""); return; }
      setText(cells[0], normalizedIssue(row));
      var poultry = listValue(rawValue(row, "jia"));
      var beast = listValue(rawValue(row, "ye"));
      setText(groups[0], poultry.join(""));
      setText(groups[1], beast.join(""));
      setText(cells[2], resultText(row));
      // 只允许「家:…」「野:…」两格被点亮，开奖格（cells[2]）不参与高亮。
      markPredictionRow(tr, row, index, [groups[0], groups[1]]);
    });
  }

  function renderFourXiaoEightCode(section, module) {
    Array.prototype.forEach.call(sectionRows(section).slice(1), function (tr, index) {
      var row = rowData(module, index), fonts = tr.querySelectorAll("font"), detail = tr.querySelector(".zl");
      if (!row) { clearLeaves(tr); if (fonts[0]) writeLeaf(fonts[0], ""); return; }
      var zodiac = listValue(rawValue(row, "xiao")).slice(0, 4);
      var codes = listValue(rawValue(row, "code")).slice(0, 8);
      if (!zodiac.length || !codes.length) {
        zodiac = [];
        codes = [];
        tokenValues(row).slice(0, 4).forEach(function (group) {
          var parts = String(group).split("|");
          if (parts[0]) zodiac.push(parts[0]);
          if (parts[1]) codes = codes.concat(listValue(parts[1]));
        });
      }
      setText(fonts[0], normalizedIssue(row) + ": ");
      setText(fonts[2], " " + resultText(row));
      var leaves = textNodes(detail);
      if (leaves.length) leaves[0].nodeValue = "合肖（" + zodiac.join("") + "）";
      if (leaves.length > 1) leaves[1].nodeValue = codes.join(".");
      clearLeaves(detail, leaves.slice(0, 2));
      // 该模块的 DOM 里开奖段排在候选之前，旧实现按整行找第一个匹配 → 命中的
      // 生肖/号码会先命中开奖段。这里把范围钉死在候选格 detail 上。
      markPredictionRow(tr, row, index, detail);
    });
  }

  function renderNumberLines(section, module, count, separator, options) {
    var skipHighlight = Boolean(options && options.noHighlight);
    Array.prototype.forEach.call(sectionRows(section), function (tr, index) {
      var row = rowData(module, index), cells = rowCells(tr);
      if (!row) { clearLeaves(tr); if (cells[0]) writeLeaf(cells[0], ""); return; }
      var candidate = [];
      if (cells.length >= 3) {
        setText(cells[0], normalizedIssue(row));
        var numberCell = cells[1], numbers = tokenValues(row).slice(0, count);
        // 供应商快照把命中位置写成了 <span>（有的还带黄底）。它们同样是号码槽位，
        // 漏掉会让本期号码错位并残留供应商那一期的旧号码。
        var slots = numberCell.querySelectorAll("font[color='#FF0000'] > font, font[color='#FF0000'] > span");
        Array.prototype.forEach.call(slots, function (slot, slotIndex) {
          setText(slot, numbers[slotIndex] || "");
        });
        setText(cells[2], resultText(row));
        candidate = numberCell;
      } else {
        var fonts = tr.querySelectorAll("font"), detail = tr.querySelector("font[color='#0000ff']");
        setText(fonts[0], normalizedIssue(row) + ": ");
        setText(fonts[2], " " + resultText(row));
        setText(detail, "【" + tokenValues(row).slice(0, count).join(separator) + "】");
        candidate = detail || [];
      }
      // 号码玩法：只点亮候选号码格里的命中号码；「稳杀⑦码」这类排除玩法传 noHighlight。
      markPredictionRow(tr, row, index, skipHighlight ? [] : candidate);
    });
  }
  function renderFourXiaoOddsUnavailable(section) { clearUnavailableSlots(section); }
  function renderOneHeadOneCodeUnavailable(section) {
    Array.prototype.forEach.call(section.querySelectorAll(".bizhong1"), function (card) {
      Array.prototype.forEach.call(card.querySelectorAll(".bizhong1-l li, .bizhong1-r li, .bizhong1-foot"), function (slot) {
        clearLeaves(slot);
      });
      var firstSlot = card.querySelector(".bizhong1-l li");
      if (firstSlot) writeLeaf(firstSlot, "");
    });
  }

  function renderOneHeadOneCode(section, module, modules) {
    Array.prototype.forEach.call(window.document.querySelectorAll(".bizhong1"), function (card, index) {
      var headRow = rowData(module, index), codeRow = rowData(modules && modules.ma24, index);
      var heads = tokenValues(headRow).slice(0, 4).map(function (value) { return String(value).split("|", 1)[0]; });
      var codes = tokenValues(codeRow).slice(0, 24);
      Array.prototype.forEach.call(card.querySelectorAll(".bizhong1-l li"), function (slot, slotIndex) {
        setText(slot, headRow ? displayIssue(headRow) + "必中" + ["一", "二", "三", "四"][slotIndex] + "头：" + heads.slice(0, slotIndex + 1).join(",") : "");
      });
      Array.prototype.forEach.call(card.querySelectorAll(".bizhong1-r li"), function (slot, slotIndex) {
        setText(slot, codes.slice(slotIndex * 6, slotIndex * 6 + 6).join("."));
      });
      setText(card.querySelector(".bizhong1-foot"), heads.length ? "本期推荐一头：（" + heads[0] + "）" : "");
      // 该卡自带候选槽（左栏头数、右栏 24 码）：命中时点亮候选里的那个头/号码。
      // 旧实现从不给这些卡绑定预测行，所以它们「准」的时候永远零黄底。
      markPredictionRow(card, codeRow || headRow, index, [
        card.querySelector(".bizhong1-l"),
        card.querySelector(".bizhong1-r")
      ]);
    });
  }

  // ---------------------------------------------------------------------------
  // 命中高亮 MUST be derived from the live verdict of the displayed issue.
  //
  // The supplier's static HTML carries its own hit marker
  // (`<span style="background-color: #FFFF00">`) at the position that matched
  // *its* historical issue. The re-renderers only blank text nodes, so those
  // wrappers survive with a yellow background and make a row whose live
  // verdict is 错/输/不中 look highlighted. Every yellow background is therefore
  // stripped before rendering and re-applied afterwards, per issue, only when
  // that issue actually hit.
  // ---------------------------------------------------------------------------
  var HIT_BACKGROUND = "#FFFF00";
  var SUPPLIER_HIT_STYLE = /background(?:-color)?\s*:\s*(?:#ffff00|#ff0\b|yellow|rgb\(\s*255\s*,\s*255\s*,\s*0\s*\))/i;
  var SUPPLIER_HIT_DECL = /(?:^|;)\s*background(?:-color)?\s*:\s*(?:#ffff00|#ff0\b|yellow|rgb\(\s*255\s*,\s*255\s*,\s*0\s*\))\s*(?=;|$)/gi;

  function stripSupplierHitBackgrounds(scope) {
    var root = scope && scope.querySelectorAll ? scope : window.document;
    Array.prototype.forEach.call(root.querySelectorAll("[style]"), function (element) {
      var style = element.getAttribute("style");
      if (!style || !SUPPLIER_HIT_STYLE.test(style)) return;
      var cleaned = String(style).replace(SUPPLIER_HIT_DECL, "").replace(/^[\s;]+|[\s;]+$/g, "");
      // Defensive: never leave the supplier hit colour behind on a miss row.
      if (!cleaned || SUPPLIER_HIT_STYLE.test(cleaned)) element.removeAttribute("style");
      else element.setAttribute("style", cleaned);
    });
  }

  function dropRenderedHitMarkers(scope) {
    var root = scope && scope.querySelectorAll ? scope : window.document;
    Array.prototype.forEach.call(root.querySelectorAll("[data-prediction-hit]"), function (element) {
      if (element.parentNode) element.parentNode.removeChild(element);
    });
  }

  function resetHitHighlights() {
    dropRenderedHitMarkers(window.document);
    stripSupplierHitBackgrounds(window.document);
    // 本期渲染开始前清空上一轮的期次绑定：没有重新绑定到本期的行一律不许上色。
    Array.prototype.forEach.call(window.document.querySelectorAll("[data-prediction-row]"), function (element) {
      element.__twjsz666PredictionRow = null;
    });
    // 已存在槽位（买码之前先上）的高亮标记同样必须先清掉，否则某张卡当期没有
    // 重写槽位时会残留上一期的「命中」标记。
    Array.prototype.forEach.call(window.document.querySelectorAll("[data-prediction-hit-slot]"), function (element) {
      element.removeAttribute("data-prediction-hit-slot");
    });
  }

  function markPredictionRow(element, row, index, highlightScope) {
    if (!element || !element.setAttribute) return;
    if (index !== undefined) element.setAttribute("data-prediction-row", String(index));
    element.__twjsz666PredictionRow = row || null;
    // 高亮范围**必须**是承载预测候选的节点（单个元素或元素数组）：
    // 只有这样才能保证黄底落在「命中的候选文字」上，而不会落到同一行的
    // 期号、「开:22羊对」开奖段或判定字上。传 `[]` 表示该玩法没有可点亮的
    // 命中候选（绝杀/杀号这一类排除玩法），渲染后零黄底。
    element.__twjsz666HighlightScope = highlightScope || null;
  }

  // 命中值按优先级分组：
  //   1) 整颗标签：生肖 / 特码 / 波色「红波」 / 大小「大数」——这些是候选格里原样出现的写法；
  //   2) 带「头」「尾」的位与单字波色/大小；
  //   3) 最后才退化到裸数字（"45" 命中不会去点亮 22 码里的 "4"）。
  // 波色与大小由**特码**推导（标准波色分组；1-24 小、25-49 大），这样
  // 「双波中特」「大小中特」命中时点亮的是候选格里的波色/大小，而不是开奖号码。
  var COLOR_BY_CODE = (function () {
    var map = {};
    var red = ["01", "02", "07", "08", "12", "13", "18", "19", "23", "24", "29", "30", "34", "35", "40", "45", "46"];
    var blue = ["03", "04", "09", "10", "14", "15", "20", "25", "26", "31", "36", "37", "41", "42", "47", "48"];
    var green = ["05", "06", "11", "16", "17", "21", "22", "27", "28", "32", "33", "38", "39", "43", "44", "49"];
    function put(list, name) {
      for (var i = 0; i < list.length; i++) map[list[i]] = name;
    }
    put(red, "red");
    put(blue, "blue");
    put(green, "green");
    return map;
  })();
  var WAVE_FULL = { red: "红波", blue: "蓝波", green: "绿波" };
  var WAVE_SHORT = { red: "红", blue: "蓝", green: "绿" };

  function hitTokenGroups(row) {
    var result = row && row.result || {};
    if (!result || result.isOpened !== true || result.isCorrect !== true) return [];
    var zodiac = resultToken(result.zodiac, false);
    var code = resultToken(result.code, true);
    var primary = [];
    var secondary = [];
    var tertiary = [];
    var wave = COLOR_BY_CODE[code];
    var size = /^\d{2}$/.test(code) ? (parseInt(code, 10) >= 25 ? "大数" : "小数") : "";
    if (zodiac) primary.push(zodiac);
    if (code) {
      primary.push(code);
      var digits = String(code).replace(/\D/g, "");
      if (digits.length === 2) {
        secondary.push(digits.charAt(0) + "头");
        secondary.push(digits.charAt(0) + "頭");
        secondary.push(digits.charAt(1) + "尾");
        tertiary.push(digits.charAt(0));
        tertiary.push(digits.charAt(1));
      }
    }
    if (wave) {
      primary.push(WAVE_FULL[wave]);
      secondary.push(WAVE_SHORT[wave]);
    }
    if (size) {
      primary.push(size);
      secondary.push(size.charAt(0));
    }
    return [primary, secondary, tertiary];
  }

  function digitSidedBoundary(value, index, token) {
    if (!/^\d+$/.test(token)) return true;
    var before = index > 0 ? value.charAt(index - 1) : "";
    var after = value.charAt(index + token.length);
    return !/\d/.test(before) && !/\d/.test(after);
  }

  function highlightToken(root, token) {
    if (!root || !token) return false;
    var nodes = textNodes(root);
    for (var index = 0; index < nodes.length; index += 1) {
      var node = nodes[index];
      var parent = node.parentNode;
      if (!parent) continue;
      if (parent.closest && parent.closest("[data-prediction-hit]")) continue;
      var value = String(node.nodeValue || "");
      var at = value.indexOf(token);
      while (at !== -1 && !digitSidedBoundary(value, at, token)) at = value.indexOf(token, at + 1);
      if (at === -1) continue;
      node.splitText(at + token.length);
      var tokenNode = node.splitText(at);
      var marker = window.document.createElement("span");
      marker.setAttribute("data-prediction-hit", "");
      marker.setAttribute("style", "background-color: " + HIT_BACKGROUND);
      tokenNode.parentNode.insertBefore(marker, tokenNode);
      marker.appendChild(tokenNode);
      return true;
    }
    return false;
  }

  function highlightPredictionRow(element) {
    var row = element && element.__twjsz666PredictionRow;
    var groups = hitTokenGroups(row);
    var scope = element && element.__twjsz666HighlightScope || element;
    var scopes = Array.isArray(scope) ? scope : [scope];
    for (var index = 0; index < groups.length; index += 1) {
      var matched = false;
      scopes.forEach(function (scopeElement) {
        if (!scopeElement) return;
        groups[index].forEach(function (token) {
          if (highlightToken(scopeElement, token)) matched = true;
        });
      });
      if (matched) return;
    }
  }

  function applyPredictionHighlights() {
    Array.prototype.forEach.call(window.document.querySelectorAll("[data-prediction-row]"), highlightPredictionRow);
  }

  function writeExistingTokens(root, values, hitValue) {
    if (!root) return;
    var slots = root.querySelectorAll(":scope > font, :scope > span");
    Array.prototype.forEach.call(slots, function (slot, index) {
      var value = values[index] || "";
      writeLeaf(slot, value);
      if (slot.style) slot.style.removeProperty("background-color");
      // 已存在的槽位不能像 highlightToken 那样再包一层 span（会破坏供应商布局），
      // 因此用 data-prediction-hit-slot 标记「这一格是命中高亮」，
      // 供清理与展示审计识别：判定为「错」时该标记必须一并消失。
      slot.removeAttribute("data-prediction-hit-slot");
      if (value && value === hitValue && slot.style) {
        slot.style.backgroundColor = "#FFFF00";
        slot.setAttribute("data-prediction-hit-slot", "");
      }
    });
  }

  function beforeBetCards() {
    var titles = window.document.querySelectorAll(".list-title");
    var title = Array.prototype.filter.call(titles, function (item) {
      return String(item.textContent || "").indexOf("买码之前先上") !== -1;
    })[0];
    var cards = [];
    var sibling = title && title.nextElementSibling;
    while (sibling && !sibling.classList.contains("list-title")) {
      if (sibling.matches("table.qxtable") && !sibling.classList.contains("yxym")) cards.push(sibling);
      sibling = sibling.nextElementSibling;
    }
    return cards;
  }

  function renderBeforeBetCards(module) {
    Array.prototype.forEach.call(beforeBetCards(), function (card, index) {
      var row = rowData(module, index), rows = sectionRows(card);
      var xiao = groupValues(row, "xiao_5").slice(0, 5);
      var codes = groupValues(row, "code_5").slice(0, 5);
      var result = row && row.result || {};
      var opened = !!(row && result.isOpened);
      var hitXiao = opened ? resultToken(result.zodiac, false) : "";
      var hitCode = opened ? resultToken(result.code, true) : "";
      // 本期判定：「五码中」才允许黄色高亮；「五码错」的当期不得残留任何黄底。
      var isHit = opened && codes.indexOf(hitCode) !== -1;
      var firstCells = rowCells(rows[0]);
      writeExistingTokens(firstCells[0] && firstCells[0].querySelector(".xz2"), xiao, isHit ? hitXiao : "");
      writeExistingTokens(firstCells[1] && firstCells[1].querySelector(".xz2"), codes, isHit ? hitCode : "");
      var statusFonts = rows[1] && rows[1].querySelectorAll("font");
      if (statusFonts && statusFonts[0]) writeLeaf(statusFonts[0], row ? displayIssue(row) + "：内幕大公开-" : "");
      var marker = rows[1] && rows[1].querySelector(".xz3 > span");
      if (marker) writeLeaf(marker, !row || !opened ? "待开奖" : isHit ? "五码中" : "五码错");
      if (row) card.setAttribute("data-prediction-row", String(index));
    });
  }

  function renderPublicCards(section, module, modules) {
    var specs = [
      ["⑨肖", modules["9xzt"], 9], ["⑧肖", modules["danshuang4xiao"], 8],
      ["⑥肖", modules["6xzt"], 6], ["④肖", modules["4xiao8ma"], 4], ["②肖", modules["pt2xiao"], 2]
    ];
    Array.prototype.forEach.call(section.querySelectorAll("table.qxtable"), function (card, index) {
      var selected = rowData(module, index);
      setText(card.querySelector(".jx"), selected ? "精选：" + tokenValues(selected).slice(0, 10).join(".") : "");
      var rows = sectionRows(card).slice(1, 6);
      specs.forEach(function (spec, specIndex) {
        var row = rowData(spec[1], index), cells = rowCells(rows[specIndex]);
        var values = spec[0] === "④肖"
          ? tokenValues(row).slice(0, 4).map(function (value) { return String(value).split("|", 1)[0]; })
          : tokenValues(row).slice(0, spec[2]).map(function (value) { return String(value).split("|", 1)[0]; });
        setText(cells[0], row ? displayIssue(row) + ":" + spec[0] : "");
        setText(cells[1], values.join(""));
        setText(cells[2], row ? resultText(row).replace(/^开:/, "") : "");
        // 只点亮本行的候选格 cells[1]（开奖格 cells[2] 不参与）。
        markPredictionRow(rows[specIndex], row, specIndex, cells[1]);
      });
    });
  }

  function renderThreeHeadFourTailUnavailable(section) { clearUnavailableSlots(section); }
  function renderThreeHeadFourTail(section, module, modules) {
    var rows = distinctRows(module);
    sectionRows(section).forEach(function (tr, index) {
      var cells = rowCells(tr);
      var row = rows[index];
      if (!row) {
        for (var cellIndex = 0; cellIndex < cells.length; cellIndex += 1) clearLeaves(cells[cellIndex]);
        return;
      }
      var payload = {};
      try { payload = JSON.parse(String(rawValue(row, "content") || "{}")); } catch (_) { payload = {}; }
      var heads = listValue(payload.heads).slice(0, 3);
      var tails = listValue(payload.tails).slice(0, 4);
      if (tails.length < 4) {
        tails = tokenValues(rowData(modules && modules.gongshi_siw, index)).slice(0, 4);
      }
      var issue = displayIssue(row);
      var value = "三头【" + heads.join(".") + "】四尾【" + tails.join(".") + "】";
      var candidateSlot = tr.querySelector(".zl") || cells[1];
      if (cells.length === 1) setText(cells[0], issue + " " + value + " " + resultText(row));
      else {
        setText(cells[0], issue);
        setText(candidateSlot, value);
        if (cells[2]) setText(cells[2], resultText(row));
      }
      // 只点亮候选单元格里命中的头/尾（「错」的当期一个黄底都不留）。
      markPredictionRow(tr, row, index, candidateSlot);
    });
  }
  function renderFourCharacterFlatXiaoUnavailable(section) { clearUnavailableSlots(section); }
  /**
   * 四字资料的「解肖」生肖串。
   *
   * 供应商该 mode 的正文是 `成语|解肖生肖`（如 `黯然無光|牛羊马虎猴鼠猪`）。旧实现只用
   * `formatLabels()` 取 `|` 左侧，于是候选格只剩成语本身：命中时没有任何候选生肖可点亮，
   * 引擎只能退到同一行的开奖段 → 「命中却零高亮 + 开奖段被标黄」。这里把右侧解肖取回来。
   */
  function solvedZodiacs(row) {
    var direct = rawValue(row, "jiexi");
    if (direct) return listValue(direct).join("");
    var tokens = tokenValues(row);
    for (var index = 0; index < tokens.length; index += 1) {
      var parts = String(tokens[index]).split("|");
      if (parts.length > 1 && parts[1]) return listValue(parts[1]).join("");
    }
    var content = String(rawValue(row, "content") || "");
    if (content.indexOf("|") !== -1) return listValue(content.split("|")[1]).join("");
    return "";
  }
  function renderFourCharacterFlatXiao(section, module) {
    Array.prototype.forEach.call(sectionRows(section), function (tr, index) {
      var row = rowData(module, index), cells = rowCells(tr), group = tr.querySelector(".zl");
      if (!row) { clearLeaves(tr); if (cells[0]) writeLeaf(cells[0], ""); return; }
      setText(cells[0], normalizedIssue(row));
      var solved = solvedZodiacs(row);
      setText(group, "【" + formatLabels(row, "").slice(0, 16) + "】" + solved);
      setText(cells[2], resultText(row));
      markPredictionRow(tr, row, index, group);
    });
  }
  function renderPoultryBeastUnavailable(section) { clearUnavailableSlots(section); }

  function renderSevenTailUnavailable(section) { clearUnavailableSlots(section); }
  function renderSevenTail(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + ":七尾中特"; },
      formatter: function (row) { return tokenValues(row).slice(0, 7).map(function (value) { return String(value).split("|", 1)[0].replace(/尾$/, ""); }).join("-"); },
      wrap: function (value) { return "【" + value + "尾】"; },
      writeResult: true
    });
  }

  function renderSelectedTwentyTwoUnavailable(section) { clearUnavailableSlots(section); }
  function renderSelectedTwentyTwo(section, module) { renderNumberLines(section, module, 22, "-"); }

  function renderKillSevenCodeUnavailable(section) { clearUnavailableSlots(section); }
  function renderKillSevenCode(section, module) { renderNumberLines(section, module, 7, ".", { noHighlight: true }); }


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
      renderExpertPublications: renderExpertPublications,
      renderFourXiaoOddsUnavailable: renderFourXiaoOddsUnavailable,
      renderFourXiaoOdds: renderFourXiaoOdds,
      renderOneHeadOneCodeUnavailable: renderOneHeadOneCodeUnavailable,
      renderOneHeadOneCode: renderOneHeadOneCode,
      renderBeforeBetCards: renderBeforeBetCards,
      renderPublicCards: renderPublicCards,
      renderFortuneNineXiao: renderFortuneNineXiao,
      renderThreeHeadFourTailUnavailable: renderThreeHeadFourTailUnavailable,
      renderThreeHeadFourTail: renderThreeHeadFourTail,
      renderPingTeXiaoHistory: renderPingTeXiaoHistory,
      renderFourCharacterFlatXiaoUnavailable: renderFourCharacterFlatXiaoUnavailable,
      renderFourCharacterFlatXiao: renderFourCharacterFlatXiao,
      renderShuangBoHistory: renderShuangBoHistory,
      renderPoultryBeastUnavailable: renderPoultryBeastUnavailable,
      renderPoultryBeast: renderPoultryBeast,
      renderFlatThreeXiao: renderFlatThreeXiao,
      renderFourXiaoEightCode: renderFourXiaoEightCode,
      renderDaXiaoHistory: renderDaXiaoHistory,
      renderSevenTailUnavailable: renderSevenTailUnavailable,
      renderSevenTail: renderSevenTail,
      renderFlatOneTail: renderFlatOneTail,
      renderSelectedTwentyTwoUnavailable: renderSelectedTwentyTwoUnavailable,
      renderSelectedTwentyTwo: renderSelectedTwentyTwo,
      renderKillTwoXiao: renderKillTwoXiao,
      renderKillOneWave: renderKillOneWave,
      renderKillOneTail: renderKillOneTail,
      renderKillSevenCodeUnavailable: renderKillSevenCodeUnavailable,
      renderKillSevenCode: renderKillSevenCode,
      renderOneSentenceSpecial: renderOneSentenceSpecial
    };
    var renderer = renderers[contract.rendererName];
    if (!renderer) throw new Error("Unknown twjsz666 renderer: " + contract.rendererName);
    renderer(section, modules[contract.moduleKeys[0]], modules);
  }

  function renderPredictions(result, lotteryType) {
    var modules = moduleMap(result);
    var lottery = lotteryForType(lotteryType);
    // 先清掉供应商快照里的黄底（它是按供应商自己的期号写死的），
    // 渲染完再由本期数据重新判定并上色，保证「错」的当期不带黄底。
    resetHitHighlights();
    Array.prototype.forEach.call(window.document.querySelectorAll(".box.pad"), function (section) {
      if (!section.querySelector(".list-title")) return;
      updateTitle(section, lottery);
      renderSection(section, modules);
    });
    renderOneHeadOneCode(window.document, modules.sitouzhongte, modules);
    renderBeforeBetCards(modules.wuxiao_wuma);
    applyPredictionHighlights();
    clearSupplierIssueSnapshots();
  }

  function clearSupplierIssueSnapshots() {
    Array.prototype.forEach.call(window.document.querySelectorAll(".box.pad"), function (section) {
      var title = String((section.querySelector(".list-title") || {}).textContent || "");
      if (!title) return;
      textNodes(section).forEach(function (node) {
        if (/\b(?:0(?:5[2-9]|60)|136|323)期\b/.test(String(node.nodeValue || ""))) node.nodeValue = "";
      });
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

  if (/\/kai\.html$/.test(window.location.pathname)) {
    function renderDrawPanel(type, result) {
      var data = result && result.data || {};
      while (data && !data.current_issue && data.data) data = data.data;
      var panelIndex = siteConfig.lotteries.map(function (item) { return item.lotteryType; }).indexOf(Number(type));
      var panel = window.document.querySelectorAll(".KJ-TabBox > div")[panelIndex];
      if (!panel) return;
      var balls = Array.isArray(data.balls) ? data.balls : [];
      var special = balls.filter(function (ball) { return ball && ball.is_special; })[0] || balls[balls.length - 1] || {};
      var issue = String(data.current_issue || data.issue || "").trim();
      var values = balls.map(function (ball) { return String(ball.value || "").padStart(2, "0"); }).filter(Boolean);
      var content = panel.querySelector("[data-draw-value]");
      if (!content) return;
      content.textContent = issue
        ? "第" + issue + "期 开奖：" + values.join(" ") + (special.zodiac ? " 特别号" + String(special.value || "").padStart(2, "0") + special.zodiac : "")
        : "暂无开奖资料";
    }

    function bindDrawTabs() {
      Array.prototype.forEach.call(window.document.querySelectorAll(".KJ-TabBox li"), function (item) {
        item.addEventListener("click", function () {
          var type = Number(item.getAttribute("data-lottery-type"));
          if (isSupportedLotteryType(type) && window.LotterySiteDataClient) {
            window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey }).loadDraw({ lotteryType: type }).then(function (result) {
              renderDrawPanel(type, result);
            });
          }
          if (type && window.parent && typeof window.parent.postMessage === "function") {
            window.parent.postMessage({ type: "lottery-change", siteKey: siteConfig.siteKey, lotteryType: type }, window.location.origin);
          }
        });
      });
    }
    function initializeDrawTabs() {
      bindDrawTabs();
      if (window.LotterySiteDataClient) {
        window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey }).loadDraw({ lotteryType: 3 }).then(function (result) {
          renderDrawPanel(3, result);
        });
      }
    }
    if (window.document.readyState === "loading") window.addEventListener("DOMContentLoaded", initializeDrawTabs);
    else initializeDrawTabs();
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
