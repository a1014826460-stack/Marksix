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
      tr.setAttribute("data-prediction-row", String(index));
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
      writeResult: true
    });
  }

  function renderKillOneWave(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + ":绝杀①半波"; },
      formatter: function (row) { return String(rawValue(row, "wave") || formatLabels(row, "、")).split(/[|,，、\s]+/).filter(Boolean).slice(0, 1).join(""); },
      wrap: function (value) { return "【" + value + "】"; },
      writeResult: true
    });
  }

  function renderKillOneTail(section, module) {
    renderInlineSlots(section, module, {
      prefix: function (row) { return normalizedIssue(row) + ":绝杀"; },
      formatter: function (row) { return String(rawValue(row, "tail") || formatLabels(row, "、")).split(/[|,，、\s]+/).filter(Boolean).slice(0, 1).join(""); },
      writeResult: true
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
      tr.setAttribute("data-prediction-row", String(index));
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
      tr.setAttribute("data-prediction-row", String(index));
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
      tr.setAttribute("data-prediction-row", String(index));
    });
  }

  function renderNumberLines(section, module, count, separator) {
    Array.prototype.forEach.call(sectionRows(section), function (tr, index) {
      var row = rowData(module, index), cells = rowCells(tr);
      if (!row) { clearLeaves(tr); if (cells[0]) writeLeaf(cells[0], ""); return; }
      if (cells.length >= 3) {
        setText(cells[0], normalizedIssue(row));
        var numberCell = cells[1], numbers = tokenValues(row).slice(0, count);
        var slots = numberCell.querySelectorAll("font[color='#FF0000'] > font");
        Array.prototype.forEach.call(slots, function (slot, slotIndex) {
          setText(slot, numbers[slotIndex] || "");
        });
        setText(cells[2], resultText(row));
      } else {
        var fonts = tr.querySelectorAll("font"), detail = tr.querySelector("font[color='#0000ff']");
        setText(fonts[0], normalizedIssue(row) + ": ");
        setText(fonts[2], " " + resultText(row));
        setText(detail, "【" + tokenValues(row).slice(0, count).join(separator) + "】");
      }
      tr.setAttribute("data-prediction-row", String(index));
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
    });
  }

  function writeExistingTokens(root, values, hitValue) {
    if (!root) return;
    var slots = root.querySelectorAll(":scope > font, :scope > span");
    Array.prototype.forEach.call(slots, function (slot, index) {
      var value = values[index] || "";
      writeLeaf(slot, value);
      if (slot.style) slot.style.removeProperty("background-color");
      if (value && value === hitValue && slot.style) slot.style.backgroundColor = "#FFFF00";
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
      var hitXiao = result.isOpened ? resultToken(result.zodiac, false) : "";
      var hitCode = result.isOpened ? resultToken(result.code, true) : "";
      var firstCells = rowCells(rows[0]);
      writeExistingTokens(firstCells[0] && firstCells[0].querySelector(".xz2"), xiao, hitXiao);
      writeExistingTokens(firstCells[1] && firstCells[1].querySelector(".xz2"), codes, hitCode);
      var statusFonts = rows[1] && rows[1].querySelectorAll("font");
      if (statusFonts && statusFonts[0]) writeLeaf(statusFonts[0], row ? displayIssue(row) + "：内幕大公开-" : "");
      var marker = rows[1] && rows[1].querySelector(".xz3 > span");
      if (marker) writeLeaf(marker, !row || !result.isOpened ? "待开奖" : codes.indexOf(hitCode) !== -1 ? "五码中" : "五码错");
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
      if (cells.length === 1) setText(cells[0], issue + " " + value + " " + resultText(row));
      else {
        setText(cells[0], issue);
        setText(tr.querySelector(".zl") || cells[1], value);
        if (cells[2]) setText(cells[2], resultText(row));
      }
      tr.setAttribute("data-prediction-row", String(index));
    });
  }
  function renderFourCharacterFlatXiaoUnavailable(section) { clearUnavailableSlots(section); }
  function renderFourCharacterFlatXiao(section, module) {
    Array.prototype.forEach.call(sectionRows(section), function (tr, index) {
      var row = rowData(module, index), cells = rowCells(tr), group = tr.querySelector(".zl");
      if (!row) { clearLeaves(tr); if (cells[0]) writeLeaf(cells[0], ""); return; }
      setText(cells[0], normalizedIssue(row));
      setText(group, "【" + formatLabels(row, "").slice(0, 16) + "】");
      setText(cells[2], resultText(row));
      tr.setAttribute("data-prediction-row", String(index));
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
  function renderKillSevenCode(section, module) { renderNumberLines(section, module, 7, "."); }


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
    Array.prototype.forEach.call(window.document.querySelectorAll(".box.pad"), function (section) {
      if (!section.querySelector(".list-title")) return;
      updateTitle(section, lottery);
      renderSection(section, modules);
    });
    renderOneHeadOneCode(window.document, modules.sitouzhongte, modules);
    renderBeforeBetCards(modules.wuxiao_wuma);
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
