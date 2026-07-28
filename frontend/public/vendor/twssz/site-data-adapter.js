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
  // The supplied 连肖连尾 section has sixteen existing issue groups. Each
  // renderer still stops at its own existing group count.
  // Individual renderers still stop at their own existing group count.
  var TWSSZ_HISTORY_LIMIT = 16;

  // Each renderer owns a vendor-specific slot contract. The targets are only
  // existing vendor nodes; no renderer may replace an entire row or container.
  var COMPLETE_SECTION_MAPPINGS = [
    { key: "sanxiao_siwei_xiao", title: "2组连肖连尾", renderer: renderLinkedGroups, moduleKeys: ["sanxiao_siwei_xiao", "sanxiao_siwei_wei"] },
    { key: "ma24", title: "精选24码", renderer: renderMa24Grid, moduleKeys: ["ma24"] },
    { key: "daxiao", title: "极品大小", renderer: renderDaxiaoHistory },
    // title_66 (5尾中特) is the approved closest backend replacement for the
    // supplied 15码中特 cards; shiwu_mazhong is not a public API module.
    { key: "title_66", title: "15码中特", renderer: renderFifteenCodeHistory },
    { key: "title_48", title: "AI心水玄机论坛", renderer: renderAiForumHistory },
    { key: "pt2xiao", title: "家野二肖", renderer: renderJiaYeErXiaoHistory },
    { key: "3tou", title: "三头中特", target: function () { return targetAfter("top_8", 1, 2); }, rows: allRows, renderer: renderStructuredHistory },
    { key: "title_5", title: "精准天地+两肖", renderer: renderTiandiHistory },
    { key: "juesha2xiao", title: "综合绝杀", target: compositeTable, renderer: renderCompositeKillHistory },
    { key: "juesha1wei", title: "精选特料专区", renderer: renderTeLiaoHistory },
    { key: "pt1wei", title: "平特一尾", target: function () { return targetAfter("top_3", 0, 3); }, rows: allRows, renderer: renderStructuredHistory },
    { key: "pt1xiao", title: "平特一肖", target: function () { return targetAfter("top_3", 0, 6); }, rows: allRows, renderer: renderStructuredHistory },
    { key: "title_48", title: "8肖16码", renderer: renderEightXiaoHistory },
    { key: "wuzhong5ma", title: "内幕⑤不中", renderer: renderFiveNotHistory },
    { key: "juesha1xiao", title: "绝杀7码", target: function () { return followingParagraphs("top_4", 0, 0, 1)[0]; }, rows: function () { return followingParagraphs("top_4", 0, 0, 8); }, renderer: renderStructuredHistory },
    { key: "juesha2xiao", title: "绝杀二肖", target: function () { return followingParagraphs("top_4", 0, 8, 1)[0]; }, rows: function () { return followingParagraphs("top_4", 0, 8, 8); }, renderer: renderStructuredHistory },
    { key: "jueshabanbo", title: "绝杀半波", target: function () { return followingParagraphs("top_4", 0, 16, 1)[0]; }, rows: function () { return followingParagraphs("top_4", 0, 16, 8); }, renderer: renderStructuredHistory },
    { key: "3hang", title: "综合资料", target: function () { return targetAfter("top_2", 0, 2); }, rows: allRows, renderer: renderStructuredHistory },
    { key: "pt3xiao", title: "三肖六码", renderer: renderThreeXiaoHistory },
    { key: "shuangbo", title: "双波10码", renderer: renderDoubleWaveHistory },
    { key: "title_47", title: "四肖中特", target: function () { return targetAfter("top_8", 2, 2); }, rows: allRows, renderer: renderStructuredHistory },
    { key: "danshuangtema", title: "单双中特", renderer: renderDanShuangHistory },
    { key: "title_143", title: "一波中特", target: function () { return window.document.querySelector("#con_jihuadanshuang50000ww_2"); }, rows: allParagraphs, renderer: renderStructuredHistory },
    { key: "3tou", title: "一头一码", renderer: renderOneHeadHistory }
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
    var rows = distinctModuleRows(module);
    return rows[index] || null;
  }

  function distinctModuleRows(module) {
    var seen = {};
    return (module && Array.isArray(module.rows) ? module.rows : []).filter(function (row) {
      var issue = String(row && (row.issue || row.term || "")).replace(/期$/, "");
      if (!issue || seen[issue]) return false;
      seen[issue] = true;
      return true;
    });
  }

  function moduleRowForTerm(module, referenceRow, fallbackIndex) {
    var term = referenceRow && String(referenceRow.term || referenceRow.issue || "").replace(/期$/, "");
    var rows = distinctModuleRows(module);
    if (term) {
      var matched = rows.filter(function (row) {
        return String(row.term || row.issue || "").replace(/期$/, "") === term;
      })[0];
      if (matched) return matched;
    }
    return moduleRow(module, fallbackIndex);
  }

  function resultLabel(row) {
    var result = row && row.result || {};
    if (!result.isOpened) return "待开奖";
    return result.isCorrect ? "对" : "错";
  }

  function predictionTokens(row) {
    var tokens = row && row.prediction && row.prediction.tokens;
    return Array.isArray(tokens) ? tokens : [];
  }

  function firstValue(value) {
    return String(value == null ? "" : value).split("|")[0].replace(/[【】]/g, "").trim();
  }

  function numberValue(value) {
    var raw = String(value == null ? "" : value);
    var match = raw.match(/\d{1,2}/);
    return match ? (match[0].length === 1 ? "0" + match[0] : match[0]) : firstValue(raw);
  }

  function zodiacValues(row) {
    return predictionTokens(row).map(firstValue).filter(Boolean);
  }

  function numberValues(row) {
    return predictionTokens(row).map(numberValue).filter(Boolean);
  }

  function numericTokenValues(row) {
    return predictionTokens(row).reduce(function (values, token) {
      var matches = String(token == null ? "" : token).match(/\d{1,2}/g) || [];
      return values.concat(matches.map(function (value) {
        return value.length === 1 ? "0" + value : value;
      }));
    }, []);
  }

  function termValue(row) {
    var term = row && (row.term || row.issue);
    return term ? String(term).replace(/期$/, "") + "期" : "";
  }

  function drawValue(row) {
    var result = row && row.result || {};
    return result.text || "待开奖";
  }

  function resultCode(row) {
    var result = row && row.result || {};
    var code = String(result.code || "").match(/\d{1,2}/);
    if (!code) code = String(result.text || "").match(/(?:开奖|开)\D*(\d{1,2})(?!\d)/);
    var value = code && (code[1] || code[0]);
    return value ? String(value).padStart(2, "0") : "";
  }

  function displayResult(row, hitLabel) {
    if (!row || !(row.result && row.result.isOpened)) return "待开奖";
    return drawValue(row) + (row.result.isCorrect ? (hitLabel || "对") : "错");
  }

  function slot(root, name, find) {
    if (!root) return null;
    var existing = root.querySelector('[data-site-slot="' + name + '"]');
    if (existing) return existing;
    var node = find && find(root);
    if (node) node.setAttribute("data-site-slot", name);
    return node || null;
  }

  function setNodeText(node, value) {
    if (!node) return;
    var texts = textNodes(node).filter(function (text) { return String(text.nodeValue || "").trim(); });
    if (texts.length) {
      texts[0].nodeValue = value;
      return;
    }
    node.textContent = value;
  }

  function clearNodeText(node) {
    if (!node) return;
    textNodes(node).forEach(function (text) { text.nodeValue = ""; });
  }

  function predictionLeaves(root) {
    if (!root) return [];
    return Array.prototype.filter.call(root.querySelectorAll("font"), function (node) {
      return !node.children.length;
    });
  }

  function writeSlots(root, values) {
    var valuesToWrite = values.length ? values : [""];
    predictionLeaves(root).forEach(function (node, index) {
      node.textContent = valuesToWrite[index] || "";
    });
  }

  function termSlot(cell) {
    return slot(cell, "term", function (root) {
      return Array.prototype.filter.call(root.querySelectorAll("span"), function (node) {
        return /^(?:\d+|待加载)期$/.test(String(node.textContent || "").trim());
      })[0];
    });
  }

  function gradeValueRoot(cell) {
    return slot(cell, "prediction", function (root) {
      var spans = root.querySelectorAll("span");
      return spans.length ? spans[spans.length - 1] : null;
    });
  }

  function formatGroupedTokens(row, type) {
    return (type === "number" ? numberValues(row) : zodiacValues(row)).join(type === "number" ? "." : "");
  }

  function renderGradeValue(cell, row, kind) {
    var term = termSlot(cell);
    if (!term) {
      var label = Array.prototype.filter.call(cell.querySelectorAll("span"), function (node) {
        return /^(?:七肖|四肖|三肖|二肖)/.test(String(node.textContent || "").trim());
      })[0];
      if (label) {
        label.setAttribute("data-site-slot", "term-label");
        var leadingText = Array.prototype.filter.call(label.childNodes, function (node) { return node.nodeType === 3; })[0];
        if (leadingText) leadingText.nodeValue = termValue(row) + " ";
        else label.insertBefore(window.document.createTextNode(termValue(row) + " "), label.firstChild);
      }
    } else {
      var leading = textNodes(term).filter(function (text) { return String(text.nodeValue || "").trim(); })[0];
      if (leading) leading.nodeValue = termValue(row) + " " + String(leading.nodeValue || "").replace(/^\s*\d*期?\s*/, "");
      else term.textContent = termValue(row);
    }
    writeSlots(gradeValueRoot(cell), kind === "number" ? numberValues(row) : zodiacValues(row));
  }

  function renderGradeResult(cell, row) {
    var recommendation = zodiacValues(row).slice(0, 1).join("");
    var recommendationSlot = slot(cell, "special", function (root) { return root.querySelector(".dbt9"); });
    var resultSlot = slot(cell, "result", function (root) {
      return Array.prototype.filter.call(root.querySelectorAll("span"), function (node) {
        return String(node.textContent || "").indexOf("开：") !== -1;
      })[0];
    });
    if (recommendationSlot) {
      textNodes(recommendationSlot).filter(function (text) {
        return String(text.nodeValue || "").indexOf("『") !== -1;
      }).forEach(function (text, index) {
        if (!index) text.nodeValue = "『" + recommendation + recommendation + recommendation + "』";
      });
    }
    if (resultSlot) resultSlot.textContent = row ? "开：" + displayResult(row) : "";
  }

  function gradeModules(moduleByKey) {
    return [
      moduleByKey["7xiao7ma"], moduleByKey["sixiao_sima"], moduleByKey["wensha10ma"], moduleByKey["3zxt"],
      moduleByKey["4xiao8ma"], moduleByKey["pt2xiao"], moduleByKey["title_66"]
    ];
  }

  // A级猛料 has seven independently formatted cells. Keep its vendor labels
  // and colours; only the term, value and result slots receive API data.
  function renderGradeHistory(moduleByKey) {
    var anchor = matchingAnchor("top_15", 0);
    if (!anchor || !anchor.parentElement) return;
    var target = anchor.parentElement;
    var modules = gradeModules(moduleByKey || {});
    preserveFiveNumberLabel();
    target.setAttribute("data-prediction-section", "grade-a");
    Array.prototype.slice.call(target.querySelectorAll("table")).forEach(function (table, historyIndex) {
      table.setAttribute("data-prediction-row", String(historyIndex));
      var rows = table.querySelectorAll("tr");
      if (rows.length < 5) return;
      setNodeText(slot(rows[0], "title", function (root) { return root.querySelector("span"); }), activeLottery.titleRegionPrefix + " A级猛料大公开");
      var cells = rows[1].querySelectorAll("td");
      var referenceRow = moduleRow(modules[0], historyIndex);
      renderGradeValue(cells[0], referenceRow, "zodiac");
      renderGradeResult(cells[1], moduleRowForTerm(modules[5], referenceRow, historyIndex));
      cells = rows[2].querySelectorAll("td");
      renderGradeValue(cells[0], moduleRowForTerm(modules[1], referenceRow, historyIndex), "zodiac");
      writeSlots(slot(cells[1], "prediction", function (root) { return root.querySelector("span[style*='rgb(255']"); }), numberValues(moduleRowForTerm(modules[2], referenceRow, historyIndex)));
      cells = rows[3].querySelectorAll("td");
      renderGradeValue(cells[0], moduleRowForTerm(modules[3], referenceRow, historyIndex), "zodiac");
      writeSlots(slot(cells[1], "prediction", function (root) { return root.querySelector("font[color='#ff0000']"); }), numberValues(moduleRowForTerm(modules[4], referenceRow, historyIndex)));
      cells = rows[4].querySelectorAll("td");
      renderGradeValue(cells[0], moduleRowForTerm(modules[5], referenceRow, historyIndex), "zodiac");
      writeSlots(gradeValueRoot(cells[1]), numberValues(moduleRowForTerm(modules[6], referenceRow, historyIndex)));
    });
  }

  function rowSummary(row, title) {
    if (!row) return "";
    return termValue(row) + " " + title + "：" + predictionTokens(row).map(firstValue).join("·") + " 开：" + drawValue(row) + resultLabel(row);
  }

  function clearOtherLeafText(root, retained) {
    Array.prototype.filter.call(root.querySelectorAll("font, span, p"), function (node) {
      return !node.children.length && node !== retained;
    }).forEach(function (node) { node.textContent = ""; });
    textNodes(root).filter(function (node) {
      return node.parentElement !== retained && String(node.nodeValue || "").trim();
    }).forEach(function (node) { node.nodeValue = ""; });
  }

  // Fallback for vendor tables with one pre-existing text field per history row.
  // It writes that field only, never a table/div/container, and has a named
  // renderer entry so a new vendor layout cannot silently use raw API tokens.
  function renderStructuredHistory(mapping, module, moduleByKey) {
    var target = mapping.target && mapping.target();
    if (!target) return;
    if ((!module || !module.rows || !module.rows.length) && mapping.fallbackKey) module = moduleByKey[mapping.fallbackKey];
    var sectionKey = target.getAttribute("data-prediction-section") ? mapping.key + "-" + mapping.title : mapping.key;
    target.setAttribute("data-prediction-section", sectionKey);
    var apiRows = module && Array.isArray(module.rows) ? module.rows : [];
    (mapping.rows ? mapping.rows(target) : []).forEach(function (node, index) {
      if (!node || node.nodeType === 3) return;
      node.setAttribute("data-prediction-row", String(index));
      var valueSlot = slot(node, "history-value", function (root) {
        return Array.prototype.filter.call(root.querySelectorAll("font, span, p"), function (candidate) {
          return !candidate.children.length && String(candidate.textContent || "").trim();
        })[0];
      });
      clearOtherLeafText(node, valueSlot);
      // Extra vendor rows are deliberately blank: reusing a previous API row
      // would falsely display the same issue multiple times.
      if (valueSlot) valueSlot.textContent = apiRows[index] ? rowSummary(apiRows[index], mapping.title) : "";
    });
  }

  function pairValues(row) {
    var values = zodiacValues(row);
    if (!values.length) return ["", ""];
    if (values.length >= 4) return [values.slice(0, 2).join(""), values.slice(2, 4).join("")];
    if (values.length === 3) return [values.slice(0, 2).join(""), values.slice(2).join("")];
    return [values.join(""), ""];
  }

  function tailPairValues(row) {
    var values = predictionTokens(row).map(function (token) {
      return String(token == null ? "" : token).replace(/尾/g, "").split("|")[0].replace(/[^0-9]/g, "");
    }).filter(Boolean);
    if (!values.length) return ["", ""];
    if (values.length >= 4) return [values.slice(0, 2).join("."), values.slice(2, 4).join(".")];
    return [values.slice(0, 2).join("."), values.slice(2).join(".") || ""];
  }

  // 两组连肖连尾 is a two-row contract per issue. Its two backend mechanisms
  // are aligned by historical index and rendered into their own existing rows.
  function renderLinkedGroups(mapping, module, moduleByKey) {
    var anchor = matchingAnchor("top_14", 0);
    var target = anchor && anchor.nextElementSibling && anchor.nextElementSibling.nextElementSibling;
    if (!target) return;
    target.setAttribute("data-prediction-section", mapping.key);
    var xiao = moduleByKey.sanxiao_siwei_xiao;
    var wei = moduleByKey.sanxiao_siwei_wei;
    var rows = target.querySelectorAll("tr");
    var maxGroups = Math.min(rows.length / 2, (xiao && xiao.rows || []).length, (wei && wei.rows || []).length);
    for (var index = 0; index < maxGroups * 2; index += 2) {
      var historyIndex = index / 2;
      var xiaoRow = moduleRow(xiao, historyIndex);
      var weiRow = moduleRow(wei, historyIndex);
      var header = rows[index];
      var detail = rows[index + 1];
      header.setAttribute("data-prediction-row", String(historyIndex));
      if (detail) detail.setAttribute("data-prediction-row", String(historyIndex));
      var headerFont = slot(header, "linked-header", function (root) { return root.querySelector("font"); });
      var resultFont = slot(header, "linked-result", function (root) { return root.querySelector("font[color='#FF0000']"); });
      if (headerFont) {
        var headerText = Array.prototype.filter.call(headerFont.childNodes, function (node) { return node.nodeType === 3; });
        if (headerText.length) headerText[0].nodeValue = (termValue(xiaoRow) || "") + " ";
        if (headerText.length > 1) headerText[headerText.length - 1].nodeValue = "开 ";
      }
      if (resultFont) resultFont.textContent = xiaoRow ? displayResult(xiaoRow) : "";
      if (detail) {
        var detailFont = slot(detail, "linked-groups", function (root) { return root.querySelector("font"); });
        if (detailFont) detailFont.textContent = tailPairValues(weiRow).map(function (value) { return "【" + value + "尾】"; }).join("") + "\n" + pairValues(xiaoRow).map(function (value) { return "【" + value + "】"; }).join("");
      }
    }
    for (var remainder = maxGroups * 2; remainder < rows.length; remainder += 1) replaceExistingText(rows[remainder], "");
  }

  // 精选24码 is a fixed vendor grid: update its existing 24 cells in order.
  function renderMa24Grid(mapping, module) {
    var anchor = matchingAnchor("top_9", 0);
    if (!anchor) return;
    var scope = anchor.parentElement;
    var rows = scope ? scope.querySelectorAll("tr.zt24mtr") : [];
    if (!rows.length) return;
    scope.setAttribute("data-prediction-section", mapping.key);
    var historyIndex = 0;
    for (var index = 0; index < rows.length; index += 2) {
      var row = moduleRow(module, historyIndex);
      var values = numberValues(row);
      // The supplied grid has a three-row issue group: one heading followed
      // by two .zt24mtr rows. Locate the heading from the pair's table rows,
      // not from sibling offsets that can cross into the prior issue.
      var headingRow = rows[index].previousElementSibling;
      if (headingRow) {
        headingRow.setAttribute("data-site-slot", "ma24-heading");
        // Each issue heading is the existing row directly before its first
        // 12-number row. Preserve its layout and replace only its text slot.
        var headingCell = headingRow.querySelector("td");
        if (headingCell) setNodeText(headingCell, row ? termValue(row) + " 精选24码;准确率绝对100%;大胆下注!" : "");
      }
      Array.prototype.slice.call(rows[index].querySelectorAll("td")).concat(
        rows[index + 1] ? Array.prototype.slice.call(rows[index + 1].querySelectorAll("td")) : []
      ).forEach(function (cell, cellIndex) {
        cell.setAttribute("data-prediction-row", String(historyIndex));
        setNodeText(cell, values[cellIndex] || "");
      });
      historyIndex += 1;
    }
  }

  function tablesAfterTop8() {
    var anchor = matchingAnchor("top_8", 0);
    var heading = anchor && anchor.nextElementSibling;
    var scope = heading && heading.nextElementSibling;
    return scope ? scope.querySelectorAll("table") : [];
  }

  // 家野二肖 has eight one-row cards followed by a fixed livestock legend.
  // The term, category, zodiac pair and draw result each retain their supplied
  // slot instead of collapsing the card into a generic API summary.
  function renderJiaYeErXiaoHistory(mapping, module) {
    var tables = tablesAfterTop8();
    var domestic = ["牛", "马", "羊", "鸡", "狗", "猪"];
    Array.prototype.slice.call(tables, 1, 9).forEach(function (table, index) {
      var row = moduleRow(module, index);
      var cell = table.querySelector("td");
      if (!cell) return;
      table.setAttribute("data-prediction-section", mapping.key);
      table.setAttribute("data-prediction-row", String(index));
      var zodiacs = zodiacValues(row).slice(0, 2);
      var category = zodiacs.some(function (value) { return domestic.indexOf(value) >= 0; }) ? "家禽" : "野兽";
      var term = slot(cell, "jia-ye-term", function (root) { return root.querySelector("p > font b"); });
      var value = slot(cell, "jia-ye-value", function (root) { return root.querySelector("font[color='#0000FF']"); });
      var result = slot(cell, "jia-ye-result", function (root) { return root.querySelector("font[color='#ff0000']"); });
      if (term) term.textContent = row ? termValue(row) : "";
      if (value) value.textContent = row ? "【" + category + "+" + zodiacs.join("") + "】" : "";
      if (result) result.textContent = row ? openedResult(row) : "";
    });
  }

  function teLiaoTable() {
    var anchor = matchingAnchor("top_1", 0);
    return anchor && anchor.nextElementSibling && anchor.nextElementSibling.nextElementSibling;
  }

  // 特料专区 keeps its supplied one-row announcement layout. The API has one
  // approved replacement stream, so absent entries remain explicit blanks.
  function renderTeLiaoHistory(mapping, module) {
    var table = teLiaoTable();
    if (!table) return;
    table.setAttribute("data-prediction-section", mapping.key);
    Array.prototype.forEach.call(table.querySelectorAll("tr"), function (tr, index) {
      var row = moduleRow(module, index);
      var cell = tr.querySelector("td");
      if (!cell) return;
      tr.setAttribute("data-prediction-row", String(index));
      var issue = slot(cell, "teliao-term", function (root) { return root.querySelector("a strong span span span span span"); });
      var value = slot(cell, "teliao-value", function (root) { return Array.prototype.filter.call(root.querySelectorAll("span"), function (node) { return String(node.textContent || "").trim() && node !== issue; })[0]; });
      var status = slot(cell, "teliao-status", function (root) { return root.querySelector("td > strong:last-child"); });
      if (issue) issue.textContent = row ? termValue(row).replace("期", "") : "";
      if (value) value.textContent = row ? predictionTokens(row).map(firstValue).join("·") : "";
      if (status) status.textContent = row ? (row.result && row.result.isOpened ? openedResult(row) : "待开奖") : "";
    });
  }

  function renderDanShuangHistory(mapping, module) {
    var target = window.document.querySelector("#con_jihuadanshuang50000ww_1");
    if (!target) return;
    target.setAttribute("data-prediction-section", mapping.key);
    Array.prototype.forEach.call(target.querySelectorAll("p"), function (line, index) {
      var row = moduleRow(module, index);
      line.setAttribute("data-prediction-row", String(index));
      var values = predictionTokens(row).map(firstValue);
      var label = values.join("") || "";
      replaceExistingText(line, row ? termValue(row) + "《" + label + "》" + openedResult(row, "√") : "");
    });
  }

  function vendorPredictionScopes() {
    return Array.prototype.slice.call(window.document.querySelectorAll(
      "#top_15, #top_14, #top_13, #top_12, #top_11, #top_10, #top_9, #top_8, #top_6, #top_4, #top_3, #top_2, #top_1, [id^='con_jihuadanshuang'], .bbzhong122, .bizhong1"
    ));
  }

  // Some supplied blocks have no approved backend formatter yet. Clear their
  // historical source payload immediately; dedicated renderers replace them
  // as their canonical mapping is added.
  function clearUnmappedStaticPredictionText() {
    vendorPredictionScopes().forEach(function (scope) {
      var root = scope.tagName === "TABLE" ? scope.parentElement : scope;
      if (!root) return;
      textNodes(root).forEach(function (node) {
        if (/\b(?:19\d|20\d|\d{3})期/.test(String(node.nodeValue || ""))) node.nodeValue = "";
      });
    });
  }

  function tailGroups(row) {
    return predictionTokens(row).map(function (token) {
      var parts = String(token == null ? "" : token).split("|");
      var tail = (parts[0].match(/\d/) || [""])[0];
      var numbers = (parts.slice(1).join("|").match(/\d{1,2}/g) || []).map(function (number) {
        return number.length === 1 ? "0" + number : number;
      });
      return { tail: tail, numbers: numbers };
    }).filter(function (group) { return group.tail; });
  }

  function replaceExistingText(root, value) {
    var nodes = textNodes(root);
    if (!nodes.length) {
      root.textContent = value;
      return;
    }
    nodes.forEach(function (node, index) { node.nodeValue = index ? "" : value; });
  }

  // The card below "精准四肖" is semantically a 15码中特 card, not a four-xiao
  // table. Its vendor li/footer nodes are fixed slots and must be rendered
  // independently rather than selected through a sibling-offset heuristic.
  function renderFifteenCodeHistory(mapping, module) {
    var cards = window.document.querySelectorAll(".bbzhong122");
    Array.prototype.forEach.call(cards, function (card, index) {
      var row = moduleRow(module, index);
      var groups = tailGroups(row);
      var tails = groups.map(function (group) { return group.tail; });
      var numbers = [];
      groups.forEach(function (group) { numbers = numbers.concat(group.numbers); });
      var title = card.querySelector(".bbzhong122-tit");
      var lines = card.querySelectorAll(".bbzhong122-l li");
      var footer = card.querySelector(".bbzhong122-foot");
      card.setAttribute("data-prediction-section", mapping.key + "-" + index);
      card.setAttribute("data-prediction-row", String(index));
      if (title) {
        title.setAttribute("data-site-slot", "fifteen-code-title");
        replaceExistingText(title, activeLottery.titleRegionPrefix + " 15码中特");
      }
      var term = termValue(row);
      var threeTails = tails.slice(0, 3).join("-");
      var fiveTails = tails.slice(0, 5).join("-");
      var codes15 = numbers.slice(0, 15).join(".");
      var codes9 = numbers.slice(0, 9).join(".");
      var oneCode = numbers[0] || "";
      var values = [
        row ? term + "必中三尾：" + threeTails : "",
        row ? term + "必中五尾：" + fiveTails : "",
        row ? "必中15码：" + codes15 : "",
        row ? "必中九码：" + codes9 : ""
      ];
      Array.prototype.forEach.call(lines, function (line, lineIndex) {
        line.setAttribute("data-site-slot", "fifteen-code-line-" + lineIndex);
        if (lineIndex < 2) {
          replaceExistingText(line, values[lineIndex] || "");
          return;
        }
        // The two number lines have existing child fonts for every number.
        // Keep those slots so the special code can retain its yellow styling.
        var leading = textNodes(line).filter(function (node) { return String(node.nodeValue || "").trim(); })[0];
        if (leading) leading.nodeValue = lineIndex === 2 ? "必中15码：" : "必中九码：";
        else if (line.firstChild && line.firstChild.nodeType === 1) {
          // The label belongs in the existing outer font's leading text slot.
          line.firstChild.insertBefore(window.document.createTextNode(lineIndex === 2 ? "必中15码：" : "必中九码："), line.firstChild.firstChild);
        }
        var leaves = predictionLeaves(line);
        var codeValues = lineIndex === 2 ? numbers.slice(0, 15) : numbers.slice(0, 9);
        leaves.forEach(function (leaf, leafIndex) {
          leaf.textContent = (codeValues[leafIndex] || "") + (leafIndex < codeValues.length - 1 ? "." : "");
          if (leafIndex < codeValues.length) leaf.setAttribute("color", "#FF0000");
          // The `bgcolor` marker belongs to the supplied number node, so
          // updating it preserves the vendor's own yellow hit treatment.
          leaf.removeAttribute("bgcolor");
        });
      });
      // The supplied line already contains nested number fonts. Reuse the
      // matching existing one for a yellow special-number highlight.
      var specialNumber = row && row.result && row.result.isOpened && resultCode(row);
      Array.prototype.forEach.call(lines, function (line) {
        var numberFont = Array.prototype.filter.call(line.querySelectorAll("font"), function (node) {
          return !node.children.length && String(node.textContent || "").replace(/\D/g, "") === specialNumber;
        })[0];
        if (numberFont) numberFont.setAttribute("bgcolor", "#FFFF00");
      });
      if (footer) {
        footer.setAttribute("data-site-slot", "fifteen-code-footer");
        replaceExistingText(footer, row ? term + "一尾一码：（" + oneCode + "）" : "");
      }
    });
  }

  function aiForumRoot() {
    var titleText = textNodes(window.document.body).filter(function (node) {
      return String(node.nodeValue || "").indexOf("AI心水玄机论坛") !== -1;
    })[0];
    var root = titleText && titleText.parentElement;
    while (root && !(root.classList && root.classList.contains("contentbox_01"))) {
      root = root.parentElement;
    }
    return root || null;
  }

  function aiForumDataTable(root) {
    return Array.prototype.filter.call(root ? root.querySelectorAll("table") : [], function (table) {
      // This table remains identifiable after the first deferred clear, when
      // all supplied prediction text has deliberately been blanked.
      return table.querySelectorAll("tr").length >= 8;
    })[0] || null;
  }

  function waveForNumber(value) {
    return ["红波", "蓝波", "绿波"].filter(function (wave) {
      return (WAVE_NUMBERS[wave] || []).indexOf(value) >= 0;
    })[0] || "";
  }

  function aiNumbers(row) {
    return numericTokenValues(row).slice(0, 10);
  }

  function aiLabelSlot(cell, name, prefix) {
    return slot(cell, name, function (root) {
      return Array.prototype.filter.call(root.querySelectorAll("font"), function (candidate) {
        return String(candidate.textContent || "").trim().indexOf(prefix) === 0;
      })[0];
    });
  }

  // AI心水 has a multi-line vendor card, so its title, term, zodiac and number
  // slots are updated independently. A generic one-line renderer corrupts
  // this layout by writing summary text into a sibling table.
  function renderAiForumHistory(mapping, module) {
    var root = aiForumRoot();
    if (!root) return;
    root.setAttribute("data-prediction-section", mapping.key + "-ai");
    var title = root.querySelector("table font");
    if (title) replaceExistingText(title, activeLottery.titlePrefix + "『AI心水玄机论坛』");
    var official = Array.prototype.filter.call(root.querySelectorAll("span"), function (node) {
      return String(node.textContent || "").indexOf("官方网址") !== -1;
    })[0];
    if (official) replaceExistingText(official, activeLottery.titlePrefix + " 官方网址 " + siteConfig.siteDomain);
    var table = aiForumDataTable(root);
    if (!table) return;
    Array.prototype.forEach.call(table.querySelectorAll("tr"), function (card, index) {
      var row = moduleRow(module, index);
      var cell = card.querySelector("td");
      if (!cell) return;
      card.setAttribute("data-prediction-row", String(index));
      var term = slot(cell, "ai-term", function (node) {
        return Array.prototype.filter.call(node.querySelectorAll("span"), function (candidate) {
          return /^(?:\d+)?期$/.test(String(candidate.textContent || "").trim());
        })[0] || node.querySelector("span span");
      });
      if (term) term.textContent = termValue(row);
      var zodiac = slot(cell, "ai-zodiac", function (node) {
        var labels = Array.prototype.filter.call(node.querySelectorAll("font"), function (candidate) {
          return String(candidate.textContent || "").indexOf("生肖:") === 0;
        });
        return labels[0] || node.querySelector("span[style*='font-family: 12pt'] font");
      });
      if (zodiac) replaceExistingText(zodiac, row ? "生肖:" + zodiacValues(row).slice(0, 6).join("") : "");
      var numbers = slot(cell, "ai-numbers", function (node) {
        return node.querySelector("font[color='#333333'] b");
      });
      var selectedNumbers = aiNumbers(row);
      if (numbers) replaceExistingText(numbers, row ? selectedNumbers.join(".") : "");
      var waves = selectedNumbers.map(waveForNumber).filter(Boolean).filter(function (wave, waveIndex, all) {
        return all.indexOf(wave) === waveIndex;
      }).join("");
      var largeCount = selectedNumbers.filter(function (number) { return Number(number) >= 25; }).length;
      var tails = selectedNumbers.map(function (number) { return number.charAt(1); }).filter(function (tail, tailIndex, all) {
        return all.indexOf(tail) === tailIndex;
      }).slice(0, 5).join("");
      // Label slots are captured before static content is cleared, then reused
      // on subsequent lottery switches without rediscovering by old text.
      var waveSlot = aiLabelSlot(cell, "ai-wave", "波色:");
      var sizeSlot = aiLabelSlot(cell, "ai-size", "大小:");
      var tailSlot = aiLabelSlot(cell, "ai-tail", "尾数:");
      if (waveSlot) replaceExistingText(waveSlot, "波色:" + (row ? waves : ""));
      if (sizeSlot) replaceExistingText(sizeSlot, "大小:" + (row ? (largeCount >= 5 ? "大" : "小") : ""));
      if (tailSlot) replaceExistingText(tailSlot, "尾数:" + (row ? tails : ""));
    });
  }
  function killSummary(row, label) {
    if (!row) return "";
    var values = predictionTokens(row).map(firstValue).filter(Boolean).join("·");
    return termValue(row) + "稳杀" + label + "【" + values + "】开" + displayResult(row);
  }

  // 综合绝杀 contains four fixed historical text blocks in one vendor cell.
  // Preserve the existing headings and write each approved mechanism into its
  // own text-node run so no source result can remain visible.
  function renderCompositeKillHistory(mapping, _module, moduleByKey) {
    var target = mapping.target && mapping.target();
    if (!target) return;
    target.setAttribute("data-prediction-section", mapping.key);
    var blocks = [
      { sourceHeading: "绝杀二肖", heading: "绝杀二肖", key: "juesha2xiao", label: "(2)肖" },
      { sourceHeading: "绝杀二尾", heading: "绝杀二尾", key: "juesha1wei", label: "(2)尾" },
      { sourceHeading: "绝杀一头", heading: "绝杀一头", key: "juesha1xiao", label: "(1)头" },
      { sourceHeading: "绝杀一行", heading: "绝杀一行", key: "jueshabanbo", label: "(1)行" }
    ];
    var text = textNodes(target);
    blocks.forEach(function (block) {
      var headingIndex = -1;
      text.some(function (node, index) {
        if (String(node.nodeValue || "").indexOf(block.sourceHeading) === -1) return false;
        headingIndex = index;
        return true;
      });
      if (headingIndex < 0) return;
      var headingNode = text[headingIndex];
      headingNode.nodeValue = headingNode.nodeValue.replace(block.sourceHeading, block.heading);
      var nextHeadingIndex = text.length;
      for (var nextIndex = headingIndex + 1; nextIndex < text.length; nextIndex += 1) {
        if (/绝杀(?:二肖|二尾|一头|一行|一肖|半波)/.test(String(text[nextIndex].nodeValue || ""))) {
          nextHeadingIndex = nextIndex;
          break;
        }
      }
      // The supplied table has a heading font followed by eight empty font
      // slots. Static cleanup clears their text, so identify the slots from
      // the original BR/font structure rather than their current content.
      var headingFont = headingNode.parentElement;
      var historyNodes = [];
      for (var nodeIndex = headingIndex + 1; nodeIndex < nextHeadingIndex; nodeIndex += 1) {
        var candidate = text[nodeIndex];
        if (candidate.parentElement && candidate.parentElement.tagName === "FONT" && candidate.parentElement !== headingFont) {
          historyNodes.push(candidate);
        }
      }
      historyNodes = historyNodes.slice(0, 8);
      historyNodes.forEach(function (node, index) {
        var row = moduleRow(moduleByKey[block.key], index);
        node.parentElement.setAttribute("data-prediction-row", block.key + "-" + index);
        node.nodeValue = row ? killSummary(row, block.label) : "";
      });
      text.slice(headingIndex + 1, nextHeadingIndex).filter(function (node) {
        return historyNodes.indexOf(node) === -1;
      }).forEach(function (node) { node.nodeValue = ""; });
    });
  }

  function openedResult(row, hitLabel) {
    if (!row) return "";
    if (!(row.result && row.result.isOpened)) return "待开奖";
    return drawValue(row) + (row.result.isCorrect ? (hitLabel || "对") : "错");
  }

  function tableInsideAfter(anchor, occurrence, steps) {
    var target = targetAfter(anchor, occurrence, steps);
    return target && (target.tagName === "TABLE" ? target : target.querySelector("table"));
  }

  function pairedHistoryRows(table, module, renderPair) {
    if (!table) return;
    var rows = Array.prototype.slice.call(table.querySelectorAll("tr"));
    for (var index = 0; index + 1 < rows.length; index += 2) {
      var row = moduleRow(module, index / 2);
      rows[index].setAttribute("data-prediction-row", String(index / 2));
      rows[index + 1].setAttribute("data-prediction-row", String(index / 2));
      renderPair(rows[index], rows[index + 1], row, index / 2);
    }
  }

  function renderDaxiaoHistory(mapping, module) {
    var table = tableInsideAfter("top_13", 0, 1);
    if (!table) return;
    table.setAttribute("data-prediction-section", mapping.key);
    // The first vendor row is a decorative separator beneath the title.
    // It has no prediction slot and must remain untouched.
    Array.prototype.slice.call(table.querySelectorAll("tr")).slice(1).forEach(function (tr, index) {
      var row = moduleRow(module, index);
      var cell = tr.querySelector("td");
      if (!cell) return;
      tr.setAttribute("data-prediction-row", String(index));
      var size = firstValue(predictionTokens(row)[0] || "");
      replaceExistingText(cell, row ? termValue(row) + ": 特码大小 【" + size + size + size + "】 开:" + openedResult(row) : "");
    });
  }

  function renderTiandiHistory(mapping, module) {
    var table = tableAfterHeading("精准天地+两肖");
    if (!table) return;
    table.setAttribute("data-prediction-section", mapping.key);
    Array.prototype.slice.call(table.querySelectorAll("tr")).forEach(function (tr, index) {
      var row = moduleRow(module, index);
      var cell = tr.querySelector("td");
      if (!cell) return;
      tr.setAttribute("data-prediction-row", String(index));
      var nature = firstValue(predictionTokens(row)[0] || "");
      var pair = row && row.raw && row.raw.xiao ? String(row.raw.xiao).split(/[,，]/).join("") : zodiacValues(row).slice(1, 3).join("");
      replaceExistingText(cell, row ? termValue(row) + ": 天地 【" + nature + "+" + pair + "】 开:" + openedResult(row) : "");
    });
  }

  var ZODIAC_NUMBERS = {
    "鼠": ["07", "19", "31", "43"], "牛": ["06", "18", "30", "42"], "虎": ["05", "17", "29", "41"],
    "兔": ["04", "16", "28", "40"], "龙": ["03", "15", "27", "39"], "蛇": ["02", "14", "26", "38"],
    "马": ["01", "13", "25", "37", "49"], "羊": ["12", "24", "36", "48"], "猴": ["11", "23", "35", "47"],
    "鸡": ["10", "22", "34", "46"], "狗": ["09", "21", "33", "45"], "猪": ["08", "20", "32", "44"]
  };

  function zodiacNumberGroups(row, maximum) {
    var values = [];
    predictionTokens(row).forEach(function (token) {
      var raw = String(token == null ? "" : token);
      var zodiac = firstValue(raw);
      var numbers = (raw.split("|").slice(1).join("|").match(/\d{1,2}/g) || []).map(function (value) {
        return value.length === 1 ? "0" + value : value;
      });
      if (!numbers.length) numbers = ZODIAC_NUMBERS[zodiac] || [];
      if (zodiac) values.push({ zodiac: zodiac, numbers: numbers.slice(0, 2) });
    });
    return values.slice(0, maximum || values.length);
  }

  function renderEightXiaoHistory(mapping, module) {
    var table = tableInsideAfter("top_11", 0, 1);
    if (!table) return;
    table.setAttribute("data-prediction-section", mapping.key);
    pairedHistoryRows(table, module, function (header, detail, row) {
      var groups = zodiacNumberGroups(row, 8);
      replaceExistingText(header, row ? termValue(row) + " ╔8肖16码╗开 " + openedResult(row) : "");
      var lines = [groups.slice(0, 4), groups.slice(4, 8)].map(function (line) {
        return line.map(function (group) { return group.zodiac + group.numbers.join("."); }).join("");
      });
      replaceExistingText(detail, row ? lines.join("\n") : "");
    });
  }

  function renderFiveNotHistory(mapping, module) {
    var table = tableInsideAfter("top_10", 0, 1);
    if (!table) return;
    table.setAttribute("data-prediction-section", mapping.key);
    pairedHistoryRows(table, module, function (header, detail, row) {
      var numbers = numericTokenValues(row).slice(0, 5);
      replaceExistingText(header, row ? termValue(row) + " 『内幕⑤不中』开 " + openedResult(row, "准") : "");
      replaceExistingText(detail, row ? "【" + numbers.join(".") + "】" : "");
    });
  }

  function xiaoNumbers(row) {
    return zodiacNumberGroups(row, 3).reduce(function (all, group) {
      return all.concat(group.numbers);
    }, []).slice(0, 6);
  }

  function renderThreeXiaoHistory(mapping, module) {
    var table = tableInsideAfter("top_2", 0, 4);
    if (!table) return;
    table.setAttribute("data-prediction-section", mapping.key);
    pairedHistoryRows(table, module, function (header, detail, row) {
      var zodiacs = zodiacValues(row).slice(0, 3);
      var category = zodiacs.some(function (value) { return "鼠牛虎猴狗猪".indexOf(value) >= 0; }) ? "凶丑" : "吉美";
      replaceExistingText(header, row ? termValue(row) + " ╔三肖六码╗开 " + openedResult(row) : "");
      replaceExistingText(detail, row ? "【" + category + "】【" + zodiacs.join("") + "】\n【" + xiaoNumbers(row).join("-") + "】" : "");
    });
  }

  var WAVE_NUMBERS = {
    "红波": ["01", "02", "07", "08", "12", "13", "18", "19", "23", "24", "29", "30", "34", "35", "40", "45", "46"],
    "蓝波": ["03", "04", "09", "10", "14", "15", "20", "25", "26", "31", "36", "37", "41", "42", "47", "48"],
    "绿波": ["05", "06", "11", "16", "17", "21", "22", "27", "28", "32", "33", "38", "39", "43", "44", "49"]
  };

  function renderDoubleWaveHistory(mapping, module) {
    var table = tableInsideAfter("top_6", 0, 2);
    if (!table) return;
    table.setAttribute("data-prediction-section", mapping.key);
    pairedHistoryRows(table, module, function (header, detail, row) {
      var tokens = predictionTokens(row);
      var groups = [];
      tokens.forEach(function (token) {
        var raw = String(token == null ? "" : token);
        var label = firstValue(raw);
        var values = (raw.split("|").slice(1).join("|").match(/\d{1,2}/g) || []).map(function (value) {
          return value.length === 1 ? "0" + value : value;
        });
        if (label && values.length) groups.push(label + ":" + values.slice(0, 10).join("."));
      });
      replaceExistingText(header, row ? termValue(row) + " 『双波10码』开 " + openedResult(row) : "");
      replaceExistingText(detail, row ? groups.slice(0, 2).join("\n") : "");
    });
  }

  function headGroups(row) {
    var groups = predictionTokens(row).map(function (token) {
      var raw = String(token == null ? "" : token);
      var label = (raw.match(/\d(?=头)/) || raw.match(/\d/) || [""])[0];
      var numbers = (raw.split("|").slice(1).join("|").match(/\d{1,2}/g) || []).map(function (value) {
        return value.length === 1 ? "0" + value : value;
      });
      if (!numbers.length && label) numbers = Array.from({ length: 10 }, function (_, index) { return label + index; });
      return { label: label, numbers: numbers.slice(0, 6) };
    }).filter(function (group) { return group.label; });
    // The source module supplies three heads. The fourth existing presentation
    // slot is deterministically completed from the remaining head pool.
    ["0", "1", "2", "3", "4"].some(function (label) {
      if (groups.length >= 4 || groups.some(function (group) { return group.label === label; })) return false;
      groups.push({ label: label, numbers: Array.from({ length: 6 }, function (_, index) {
        return label === "0" ? "0" + (index + 1) : label + index;
      }) });
      return true;
    });
    return groups;
  }

  function renderOneHeadHistory(mapping, module) {
    var cards = window.document.querySelectorAll(".bizhong1");
    Array.prototype.forEach.call(cards, function (card, index) {
      var row = moduleRow(module, index);
      var groups = headGroups(row);
      card.setAttribute("data-prediction-section", mapping.key + "-head");
      card.setAttribute("data-prediction-row", String(index));
      var title = card.querySelector(".bizhong1-tit");
      var left = card.querySelectorAll(".bizhong1-l li");
      var right = card.querySelectorAll(".bizhong1-r li");
      var foot = card.querySelector(".bizhong1-foot");
      if (title) replaceExistingText(title, "一头一码（" + siteConfig.siteDomain + "）");
      Array.prototype.forEach.call(left, function (line, lineIndex) {
        replaceExistingText(line, row ? termValue(row) + "必中" + ["一", "二", "三", "四"][lineIndex] + "头：" + groups.slice(0, lineIndex + 1).map(function (group) { return group.label; }).join(",") : "");
      });
      Array.prototype.forEach.call(right, function (line, lineIndex) {
        replaceExistingText(line, row ? ["①", "②", "③", "④"][lineIndex] + (groups[lineIndex] ? groups[lineIndex].numbers.join(".") : "") : "");
      });
      if (foot) replaceExistingText(foot, row ? "本期推荐一头：（" + (groups[0] ? groups[0].label : "") + "头）" : "");
    });
  }

  function aaaTables() {
    var captured = window.document.querySelectorAll("[data-site-slot='aaa-grade-card']");
    if (captured.length) return captured;
    return Array.prototype.filter.call(window.document.querySelectorAll(".dz_content08ab2d table"), function (table) {
      var rows = table.querySelectorAll("tr");
      return rows.length === 5 && /AAA级大公开/.test(String(rows[0] && rows[0].textContent || ""));
    });
  }

  function captureAaaTables() {
    Array.prototype.forEach.call(aaaTables(), function (table) {
      table.setAttribute("data-site-slot", "aaa-grade-card");
    });
  }

  function aaaCardRoot(table) {
    var root = table;
    while (root && !(root.classList && root.classList.contains("dz_content08ab2d"))) root = root.parentElement;
    return root || table;
  }

  function aaaZodiacs(row) {
    var selected = zodiacValues(row).slice(0, 7);
    ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"].forEach(function (value) {
      if (selected.indexOf(value) === -1) selected.push(value);
    });
    return selected.slice(0, 9);
  }

  function clearDynamicPredictionText(root) {
    if (!root) return;
    textNodes(root).forEach(function (node) {
      var value = String(node.nodeValue || "");
      if (/\b(?:19\d|20\d|\d{3})期|待开奖|\?{3,}|(?:\d{2}[鼠牛虎兔龙蛇马羊猴鸡狗猪](?:对|错)?)/.test(value)) node.nodeValue = "";
    });
  }

  function renderAaaGradeHistory(moduleByKey) {
    var module = moduleByKey["7xiao7ma"];
    aaaTables().forEach(function (table, index) {
      var row = moduleRow(module, index);
      var rows = table.querySelectorAll("tr");
      aaaCardRoot(table).setAttribute("data-prediction-section", "aaa-grade");
      table.setAttribute("data-prediction-row", String(index));
      if (rows[0]) replaceExistingText(rows[0], row ? termValue(row) + " AAA级大公开;准确率绝对100%;大胆下注!" : "");
      [9, 8, 7, 6].forEach(function (count, rowIndex) {
        if (!rows[rowIndex + 1]) return;
        replaceExistingText(rows[rowIndex + 1], row ? termValue(row) + "⑨⑧⑦⑥".charAt(rowIndex) + "肖中特:" + aaaZodiacs(row).slice(0, count).join("") : "");
      });
    });
  }

  function renderCompleteSections(moduleByKey) {
    moduleByKey = moduleByKey || {};
    renderGradeHistory(moduleByKey);
    renderAaaGradeHistory(moduleByKey);
    COMPLETE_SECTION_MAPPINGS.forEach(function (mapping) {
      mapping.renderer(mapping, moduleByKey[mapping.key], moduleByKey);
    });
  }

  function clearStaticPredictionPayload() {
    // During deferred loading, no vendor prediction, result or hit text is exposed.
    window.document.querySelectorAll("[data-site-slot='aaa-grade-card']").forEach(function (table) {
      clearDynamicPredictionText(table);
    });
    clearUnmappedStaticPredictionText();
    renderCompleteSections({});
  }

  function loadLatestPredictions(lottery) {
    lottery = lottery || activeLottery;
    return preload("predictions", { lotteryType: lottery.lotteryType, historyLimit: 1, includeVendor: false }).then(function (result) {
      var modules = modulesFrom(result);
      if (modules) latestModulesByLottery[lottery.lotteryType] = modules;
      if (modules && activeLottery.lotteryType === lottery.lotteryType) {
        renderGradeHistory(modules);
       renderFifteenCodeHistory({ key: "title_66" }, modules.title_66);
      }
      return result;
    });
  }

  function loadHistoricalPredictions(lottery) {
    lottery = lottery || activeLottery;
    var lotteryType = lottery.lotteryType;
    if (historicalRequestsByLottery[lotteryType]) return historicalRequestsByLottery[lotteryType];
    historicalRequestsByLottery[lotteryType] = preload("predictions", { lotteryType: lotteryType, historyLimit: TWSSZ_HISTORY_LIMIT, includeVendor: false }).then(function (result) {
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
    // Capture the supplied cards before static prediction text is cleared.
    captureAaaTables();
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
