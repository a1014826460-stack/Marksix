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

  function predictionImageUrl(row) {
    var prediction = row && row.prediction || {};
    return String(prediction.imageUrl || row && row.image_url || row && row.raw && row.raw.image_url || "").trim();
  }

  // 狗头传密 has one supplied image leaf. It is only shown when this site's
  // exact sxztu image payload exists; no unrelated static image is retained.
  function renderSxztuImage(module) {
    var image = window.document.querySelector("img[data-prediction-image='sxztu']");
    if (!image) return;
    var url = predictionImageUrl(moduleRow(module, 0));
    image.setAttribute("src", url);
    if (url) image.removeAttribute("hidden");
    else image.setAttribute("hidden", "hidden");
  }

  var latestModulesByLottery = {};
  var historicalModulesByLottery = {};
  var historicalRequestsByLottery = {};
  var compositeLineSlots = [];
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
    { key: "juesha2xiao-steady", title: "只是有点帅【稳杀二肖】", renderer: renderSteadyJueshaTwoXiaoHistory },
    { key: "juesha1wei", title: "精选特料专区", renderer: renderTeLiaoHistory },
    { key: "pt1wei", title: "平特一尾", target: function () { return targetAfter("top_3", 0, 3); }, rows: allRows, hitScope: "drawn", renderer: renderStructuredHistory },
    { key: "pt1xiao", title: "平特一肖", target: function () { return targetAfter("top_3", 0, 6); }, rows: allRows, hitScope: "drawn", renderer: renderStructuredHistory },
    { key: "title_48", title: "8肖16码", renderer: renderEightXiaoHistory },
    { key: "wuzhong5ma", title: "内幕⑤不中", renderer: renderFiveNotHistory },
    // 综合资料 = mode 53（三行/精准五行）：「候选」就是五行标签本身，命中行只能由
    // 特码的**号码五行**决定（hitElement），不能用正文里的号码清单反推 —— 见下面
    // `elementOfCode` 的说明。
    { key: "3hang", title: "综合资料", target: function () { return targetAfter("top_2", 0, 2); }, rows: allRows, hitElement: true, renderer: renderStructuredHistory },
    { key: "pt3xiao", title: "三肖六码", renderer: renderThreeXiaoHistory },
    { key: "shuangbo", title: "双波10码", renderer: renderDoubleWaveHistory },
    { key: "title_47", title: "四肖中特", target: fourZodiacHistoryTarget, rows: allRows, renderer: renderStructuredHistory },
    { key: "danshuangtema", title: "单双中特", renderer: renderDanShuangHistory },
    { key: "title_143", title: "一波中特", target: function () { return window.document.querySelector("#con_jihuadanshuang50000ww_2"); }, rows: allParagraphs, mergeTokens: true, renderer: renderStructuredHistory },
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

  // A card is one issue. When a module's own history does not cover that issue,
  // falling back to its first row would print another issue's candidates (and
  // another issue's 期号) inside this card — which is also how a cross-issue
  // "对" could be produced. Such a cell stays explicitly blank for this issue.
  function blankModuleRow(referenceRow) {
    return {
      term: String(referenceRow && (referenceRow.term || referenceRow.issue) || "").replace(/期$/, ""),
      prediction: { tokens: [] },
      result: {}
    };
  }

  function moduleRowForTerm(module, referenceRow, fallbackIndex) {
    var term = referenceRow && String(referenceRow.term || referenceRow.issue || "").replace(/期$/, "");
    var rows = distinctModuleRows(module);
    if (term) {
      var matched = rows.filter(function (row) {
        return String(row.term || row.issue || "").replace(/期$/, "") === term;
      })[0];
      if (matched) return matched;
      if (rows.length) return blankModuleRow(referenceRow);
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

  // Some supplied slots begin with whitespace-only nodes. Reuse those nodes
  // so rendering never replaces the vendor's element hierarchy.
  function setExistingText(node, value) {
    var nodes = textNodes(node);
    if (!nodes.length) {
      node.textContent = value;
      return;
    }
    nodes[0].nodeValue = value;
    nodes.slice(1).forEach(function (text) { text.nodeValue = ""; });
  }

  function setDirectText(node, value) {
    if (!node) return;
    var text = Array.prototype.filter.call(node.childNodes, function (child) {
      return child.nodeType === 3;
    })[0];
    if (text) text.nodeValue = value;
  }

  function directTextNodes(node) {
    return Array.prototype.filter.call(node && node.childNodes || [], function (child) {
      return child.nodeType === 3;
    });
  }

  // Paired vendor cards keep the issue, blue module label, "开", and result
  // in four existing slots. Updating the card font instead of its <tr> keeps
  // the supplied alignment and result colours intact.
  function writePairedHeader(header, row, title, hitLabel) {
    var outer = header && header.querySelector("td > p > b > font");
    if (!outer) return;
    var label = outer.querySelector("font[color='#0000FF']");
    var result = outer.querySelector("font[color='#FF0000']");
    var text = directTextNodes(outer);
    if (text[0]) text[0].nodeValue = row ? termValue(row) + " " : "";
    if (label) setExistingText(label, title);
    if (text.length > 1) text[1].nodeValue = row ? "开 " : "";
    if (result) setExistingText(result, row ? openedResult(row, hitLabel) : "");
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

  // Chrome does not paint `bgcolor` on the supplied `font` / `span` leaves, so
  // the supplier's yellow hit treatment is applied through the leaf's own
  // inline style while every other declaration (for example its red number
  // colour) is preserved. Misses, pending rows and lottery switches clear it
  // again, so an obsolete hit can never survive a render pass.
  var HIT_BACKGROUND = "background-color: #FFFF00";

  function markHitLeaf(node, hit) {
    if (!node) return;
    var declarations = String(node.getAttribute("style") || "").split(";").filter(function (part) {
      return String(part).trim() && !/^background(-color)?\s*:/i.test(String(part).trim());
    });
    if (hit) declarations.push(HIT_BACKGROUND);
    if (declarations.length) node.setAttribute("style", declarations.join("; ") + ";");
    else node.removeAttribute("style");
  }

  // Every supplier history row was authored with its own sample hit marker:
  // either an inline `background-color: #FFFF00` or the legacy `color="#FFFF00"`
  // attribute. Those markers belong to the sample draw, not to the issue the row
  // currently displays, so the row's own judgement decides whether one may stay.
  var YELLOW_MARK = /#ffff00|rgb\(\s*255\s*,\s*255\s*,\s*0\s*\)/i;

  // A row is only a hit when the current draw actually matched its own
  // recommendation; pending and missed rows must never keep a yellow marker.
  function isHitRow(row) {
    var result = row && row.result || {};
    return Boolean(result.isOpened && result.isCorrect);
  }

  // The deferred clear pass renders every mapping with an empty module while it
  // blanks the supplied payload. Such a pass holds no judgement and therefore
  // must leave the supplier's markers untouched, otherwise the later pass that
  // really carries the rows could no longer show a hit.
  function moduleHasRows(module) {
    return Boolean(module && Array.isArray(module.rows) && module.rows.length);
  }

  // Removes the yellow hit treatment from one element while preserving every
  // other declaration, so unrelated vendor styling (backgrounds, colours,
  // borders) survives untouched.
  function clearYellowMark(node) {
    if (!node || node.nodeType !== 1) return;
    var style = String(node.getAttribute("style") || "");
    if (style && YELLOW_MARK.test(style)) {
      var kept = style.split(";").filter(function (part) {
        var declaration = String(part).trim();
        return declaration && !YELLOW_MARK.test(declaration);
      });
      if (kept.length) node.setAttribute("style", kept.join("; ") + ";");
      else node.removeAttribute("style");
    }
    ["color", "bgcolor", "background"].forEach(function (name) {
      var value = node.getAttribute(name);
      if (value && YELLOW_MARK.test(value)) node.removeAttribute(name);
    });
  }

  // Scrubs every yellow marker inside one vendor row container.
  function clearRowHighlight(root) {
    if (!root) return;
    clearYellowMark(root);
    Array.prototype.forEach.call(root.querySelectorAll("*"), clearYellowMark);
  }

  // Applies the module display rule to one rendered vendor row: a miss (or a row
  // that carries no API row at all) is scrubbed of every yellow marker, while a
  // hit keeps the marker the supplier's template already provides.
  function applyRowHighlight(root, row, module) {
    if (!root || !moduleHasRows(module) || isHitRow(row)) return;
    clearRowHighlight(root);
  }

  function termSlot(cell) {
    return slot(cell, "term", function (root) {
      return Array.prototype.filter.call(root.querySelectorAll("span"), function (node) {
        return /^(?:\d+|待加载)期$/.test(String(node.textContent || "").trim());
      })[0];
    });
  }

  // The value span owns the cell's `font` leaves. A childless span inside the
  // same cell is the supplier's static hit marker, so it must never be selected
  // as the value slot.
  function valueSpanWithLeaves(root) {
    var spans = Array.prototype.filter.call(root.querySelectorAll("span"), function (node) {
      return Array.prototype.some.call(node.querySelectorAll("font"), function (font) {
        return !font.children.length;
      });
    });
    return spans.length ? spans[spans.length - 1] : null;
  }

  function gradeValueRoot(cell) {
    return slot(cell, "prediction", valueSpanWithLeaves);
  }

  // A grade-A value cell keeps one zodiac or number inside the supplier's own
  // highlight span, so its value slots are every childless `font` / `span` node
  // in document order. Writing all of them also erases the supplier's static
  // hit markers before the current draw is judged.
  function gradeValueLeaves(root) {
    if (!root) return [];
    return Array.prototype.filter.call(root.querySelectorAll("font, span"), function (node) {
      return !node.children.length;
    });
  }

  function writeGradeSlots(root, values) {
    var valuesToWrite = values.length ? values : [""];
    gradeValueLeaves(root).forEach(function (node, index) {
      node.textContent = valuesToWrite[index] || "";
    });
  }

  function formatGroupedTokens(row, type) {
    return (type === "number" ? numberValues(row) : zodiacValues(row)).join(type === "number" ? "." : "");
  }

  function renderGradeValue(cell, row, kind) {
    var term = termSlot(cell);
    if (!term) {
      var label = Array.prototype.filter.call(cell.querySelectorAll("span"), function (node) {
        return /^(?:\d+期\s*)?(?:七肖|四肖|三肖|二肖)/.test(String(node.textContent || "").trim());
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
    writeGradeSlots(gradeValueRoot(cell), kind === "number" ? numberValues(row) : zodiacValues(row));
  }

  // The A级猛料 card is one vendor issue whose seven cells share a single drawn
  // special ball, so its judgement is read from the zodiac and number values the
  // card itself displays instead of the recommending mechanism's own flag. A
  // value that equals the special zodiac or the special code keeps the
  // supplier's yellow background and makes the card "对"; a miss prints the
  // drawn special only and never prints "错".
  function gradeDrawRow(referenceRow, recommendationRow, numberRow) {
    var candidates = [referenceRow, recommendationRow, numberRow];
    for (var index = 0; index < candidates.length; index += 1) {
      var row = candidates[index];
      if (row && row.result && row.result.isOpened) return row;
    }
    return referenceRow || recommendationRow || numberRow || null;
  }

  function gradeResultText(drawRow, hit) {
    var result = drawRow && drawRow.result || {};
    if (!result.isOpened) return "开：待开奖";
    var drawn = drawValue(drawRow);
    if (!drawn || drawn === "待开奖") return "开：待开奖";
    return "开：" + drawn + (hit ? "对" : "");
  }

  var ZODIAC_CHARS = "鼠牛虎兔龙蛇马羊猴鸡狗猪";

  // Compatibility payloads may only carry `result.text` (for example 猪08), so
  // the drawn zodiac is read from the canonical field first and from the drawn
  // text afterwards.
  function gradeSpecialZodiac(drawRow) {
    var result = drawRow && drawRow.result || {};
    var zodiac = String(result.zodiac || "").trim();
    if (zodiac) return zodiac;
    var match = String(result.text || "").match(new RegExp("[" + ZODIAC_CHARS + "]"));
    return match ? match[0] : "";
  }

  // `verdictScope` is the set of value slots whose candidates own the card's
  // result text (the 七肖 cell and the 平特 cell of the same vendor row). Every
  // other cell of the card is still marked — a hit must always be visible — but
  // it no longer decides the verdict, so the "对" always has a highlighted value
  // inside the very row it is printed in.
  function markGradeHits(table, drawRow, verdictScope) {
    var result = drawRow && drawRow.result || {};
    var opened = Boolean(result.isOpened);
    var zodiac = gradeSpecialZodiac(drawRow);
    var code = opened ? resultCode(drawRow) : "";
    var scope = verdictScope || [];
    var hit = false;
    Array.prototype.forEach.call(table.querySelectorAll('[data-site-slot="prediction"]'), function (root) {
      // Every value slot was just overwritten, so an obsolete supplier hit can
      // never survive: only the current special ball keeps the yellow marker.
      var inScope = scope.indexOf(root) >= 0;
      Array.prototype.forEach.call(gradeValueLeaves(root), function (leaf) {
        var value = String(leaf.textContent || "").trim();
        var matched = Boolean(value) && opened && ((zodiac && value === zodiac) || (code && value === code));
        if (matched && inScope) hit = true;
        markHitLeaf(leaf, matched);
      });
    });
    var recommendationSlot = table.querySelector('[data-site-slot="special"]');
    if (recommendationSlot) {
      var recommendationInScope = scope.indexOf(recommendationSlot) >= 0;
      Array.prototype.forEach.call(recommendationSlot.querySelectorAll("span"), function (span) {
        if (span.children.length) return;
        var value = String(span.textContent || "").trim();
        if (!value || value.indexOf("开") !== -1) return;
        var matched = Boolean(opened && zodiac && value === zodiac + zodiac + zodiac);
        if (matched && recommendationInScope) hit = true;
        markHitLeaf(span, matched);
      });
    }
    return hit;
  }

  // ── 行内命中项标记工具 ────────────────────────────────────────────────
  // 判定与高亮必须同源：先按该行**自己展示的候选**与真实开奖复算，再把真正
  // 命中的那一项标黄；供应商静态模板留下的样例黄标一律先清除（见
  // clearRowHighlight），否则「未命中却留着旧高亮」永远清不干净。

  function zodiacOfNumber(number) {
    var value = String(number == null ? "" : number);
    if (value.length === 1) value = "0" + value;
    var found = "";
    Object.keys(ZODIAC_NUMBERS).some(function (zodiac) {
      if ((ZODIAC_NUMBERS[zodiac] || []).indexOf(value) >= 0) {
        found = zodiac;
        return true;
      }
      return false;
    });
    return found;
  }

  // 平特类玩法（平特 N 肖 / 平特 N 尾）的命中要看开奖的**全部 7 个号码**，
  // 所以除了特码与特肖，还要拿到整期号码与整期生肖。兼容载荷可能只带
  // result.text，这时按号码补算生肖。
  function drawnAtoms(row) {
    var raw = row && row.raw || {};
    var numbers = (String(raw.res_code || "").match(/\d{1,2}/g) || []).map(function (value) {
      return value.length === 1 ? "0" + value : value;
    });
    var zodiacs = String(raw.res_sx || "").split(/[,，、\s|]+/).map(function (value) {
      return String(value).trim();
    }).filter(Boolean);
    if (!zodiacs.length) zodiacs = numbers.map(zodiacOfNumber).filter(Boolean);
    return {
      opened: Boolean(row && row.result && row.result.isOpened),
      code: resultCode(row),
      zodiac: gradeSpecialZodiac(row),
      numbers: numbers,
      zodiacs: zodiacs
    };
  }

  // 生肖类玩法：候选肖 == 特肖即为命中项。
  function isSpecialZodiac(draw, value) {
    return Boolean(value) && value === draw.zodiac;
  }

  // 号码类玩法：候选码 == 特码即为命中项。
  function isSpecialNumber(draw, value) {
    return Boolean(value) && value === draw.code;
  }

  // 平特类玩法：候选肖出现在**任何**一个开奖号码的生肖里即为命中项。
  function isFlatZodiac(draw, value) {
    return Boolean(value) && draw.zodiacs.indexOf(String(value)) >= 0;
  }

  // 平特类玩法展示的候选码：出现在任何一个开奖号码里即为命中项。
  function isDrawnNumber(draw, value) {
    return Boolean(value) && draw.numbers.indexOf(String(value)) >= 0;
  }

  function clearNodeChildren(node) {
    if (!node) return;
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  // 一个展示候选一个 span；只有真正命中的那一个带黄底。
  function appendValueSpan(root, text, hit) {
    var span = window.document.createElement("span");
    span.textContent = String(text == null ? "" : text);
    markHitLeaf(span, Boolean(hit));
    root.appendChild(span);
    return span;
  }

  function appendTextNode(root, text) {
    if (text) root.appendChild(window.document.createTextNode(text));
  }

  function renderGradeResult(cell, row) {
    var recommendation = zodiacValues(row).slice(0, 1).join("");
    var recommendationSlot = slot(cell, "special", function (root) { return root.querySelector(".dbt9"); });
    var resultSlot = slot(cell, "result", function (root) {
      // The 平特 slot wraps the result leaf, so the innermost match owns the
      // "开：…" text and must keep the vendor's red result styling.
      var matches = Array.prototype.filter.call(root.querySelectorAll("span"), function (node) {
        return String(node.textContent || "").indexOf("开：") !== -1;
      });
      return matches.length ? matches[matches.length - 1] : null;
    });
    if (recommendationSlot) writeGradeRecommendation(recommendationSlot, recommendation);
    return resultSlot;
  }

  // The 平特 recommendation keeps the vendor's triple and reuses its existing
  // highlight element when the supplied card has one; the plain cards write the
  // triple into their existing text node.
  function writeGradeRecommendation(recommendationSlot, zodiac) {
    var triple = zodiac ? zodiac + zodiac + zodiac : "";
    var marker = null;
    Array.prototype.forEach.call(recommendationSlot.querySelectorAll("span"), function (span) {
      if (String(span.textContent || "").indexOf("开") !== -1) return;
      markHitLeaf(span, false);
      if (span.children.length) return;
      if (marker) {
        span.textContent = "";
        return;
      }
      marker = span;
      span.textContent = triple;
    });
    if (marker) {
      if (marker.previousSibling && marker.previousSibling.nodeType === 3) marker.previousSibling.nodeValue = "『";
      if (marker.nextSibling && marker.nextSibling.nodeType === 3) marker.nextSibling.nodeValue = "』";
      return;
    }
    // Several supplied 平特 cards carry the 『』 recommendation as bare text with
    // no child element, so the hit treatment had nowhere to live and an issue
    // that really matched could not be shown as a hit. The triple gets its own
    // span inside the supplier's existing text run; 『』 stay as text nodes so
    // the wording and the later re-renders are unchanged.
    var anchor = textNodes(recommendationSlot).filter(function (text) {
      return String(text.nodeValue || "").indexOf("『") !== -1;
    })[0];
    if (!anchor || !anchor.parentNode) return;
    var valueSpan = window.document.createElement("span");
    valueSpan.setAttribute("data-site-slot", "grade-special-value");
    valueSpan.textContent = triple;
    anchor.nodeValue = "『";
    anchor.parentNode.insertBefore(valueSpan, anchor.nextSibling);
    anchor.parentNode.insertBefore(window.document.createTextNode("』"), valueSpan.nextSibling);
  }

  function gradeModules(moduleByKey) {
    return [
      moduleByKey["7xiao7ma"], moduleByKey["sixiao_sima"], moduleByKey["wensha10ma"], moduleByKey["3zxt"],
      moduleByKey["4xiao8ma"], moduleByKey["pt2xiao"], moduleByKey["title_66"]
    ];
  }

  // A级猛料 has seven independently formatted cells. Keep its vendor labels
  // and colours; only the term, value and result slots receive API data. The
  // card is judged as a whole against the drawn special ball, so a hit keeps the
  // supplier's yellow background and a miss prints the drawn special without any
  // judgement suffix.
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
      var referenceRow = moduleRow(modules[0], historyIndex);
      var recommendationRow = moduleRowForTerm(modules[5], referenceRow, historyIndex);
      var numberRow = moduleRowForTerm(modules[2], referenceRow, historyIndex);
      var drawRow = gradeDrawRow(referenceRow, recommendationRow, numberRow);
      var cells = rows[1].querySelectorAll("td");
      renderGradeValue(cells[0], referenceRow, "zodiac");
      var resultSlot = renderGradeResult(cells[1], recommendationRow);
      // 判定归属 = 本期结果文字所在的那一行（七肖格 + 平特格）。同一张卡的其它格子
      // （四肖/三肖/二肖/⑩⑧⑤码）照样按各自的候选标黄，但不再替这一行决定对/错：
      // 否则会出现「结果印在平特格、命中项落在三肖格」这种判而无据的行。
      var verdictScope = [
        gradeValueRoot(cells[0]),
        slot(cells[1], "special", function (root) { return root.querySelector(".dbt9"); })
      ].filter(Boolean);
      cells = rows[2].querySelectorAll("td");
      renderGradeValue(cells[0], moduleRowForTerm(modules[1], referenceRow, historyIndex), "zodiac");
      // ⑩码 is 稳杀10码（排除型）：开奖号码出现在杀号集合里说明这一格**没中**，
      // 所以它不属于可高亮的命中项，单独用一个 slot 名把它排除在命中扫描之外。
      writeGradeSlots(slot(cells[1], "exclusion", function (root) { return root.querySelector("span[style*='rgb(255']"); }), numberValues(numberRow));
      cells = rows[3].querySelectorAll("td");
      renderGradeValue(cells[0], moduleRowForTerm(modules[3], referenceRow, historyIndex), "zodiac");
      writeGradeSlots(slot(cells[1], "prediction", function (root) { return root.querySelector("font[color='#ff0000']"); }), numberValues(moduleRowForTerm(modules[4], referenceRow, historyIndex)));
      cells = rows[4].querySelectorAll("td");
      renderGradeValue(cells[0], recommendationRow, "zodiac");
      writeGradeSlots(gradeValueRoot(cells[1]), numberValues(moduleRowForTerm(modules[6], referenceRow, historyIndex)));
      // Every displayed value is written before the card is judged, so the
      // result text and the yellow hit leaves always describe this card. The
      // supplier's own sample marker belongs to the sample draw and is scrubbed
      // on every pass; markGradeHits then marks exactly the values this issue
      // matched, so a hit is always visible and a miss keeps nothing.
      clearRowHighlight(table);
      var gradeHit = markGradeHits(table, drawRow, verdictScope);
      setNodeText(resultSlot, gradeResultText(drawRow, gradeHit));
    });
  }

  function clearOtherLeafText(root, retained) {
    Array.prototype.filter.call(root.querySelectorAll("font, span, p"), function (node) {
      return !node.children.length && node !== retained;
    }).forEach(function (node) { node.textContent = ""; });
    textNodes(root).filter(function (node) {
      return node.parentElement !== retained && String(node.nodeValue || "").trim();
    }).forEach(function (node) { node.nodeValue = ""; });
  }

  // ── 号码五行（号码 → 五行）───────────────────────────────────────────────
  // 权威源：`backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS`
  // = `canonical_element_number_map()` = `public.fixed_data` sign='五行'
  // （49 码全覆盖、互不重叠），与前端权威源 `frontend/lib/element-number-groups.ts`
  // 逐项一致。本文件是浏览器原生 `<script src>`，不能 import ESM，所以按仓库分层约定
  // **自包含**一份拷贝；`frontend/test/element-number-groups-contract.mjs` 会从后端
  // 权威值逐项比对（本文件已登记进它的 KNOWN_VENDOR_COPIES），任何漂移都会 FAIL。
  //
  // ⚠️ `fixed_data` 里另有一份 sign='五行肖'，那是**生肖五行**（只覆盖 48 码），对同一个
  // 号码给出不同结果：24 → 号码五行 木（生肖羊 → 生肖五行 土）、37 → 土（马 → 火）、
  // 45 → 水（狗 → 土）、04 → 金（兔 → 木）。历史遗留的 mode 53 正文（未修复的
  // `public.mode_payload_53` 行）里，「五行标签|号码清单」的清单就是按**生肖五行**拼的，
  // 所以五行类玩法（mode 53「综合资料」三行/精准五行）的命中行**只能**拿特码号码查本表，
  // **禁止**用正文清单反推 —— 否则 24 的黄底会点在【土】上。
  //
  // 2026-09-29 整体改判为「新表」：相对上一版 25 个号码换组，规律为 `new(x) = old(x-1)`、
  // 01 归水。
  var ELEMENT_NUMBER_GROUPS = {
    金: ["04", "05", "12", "13", "26", "27", "34", "35", "42", "43"],
    木: ["08", "09", "16", "17", "24", "25", "38", "39", "46", "47"],
    水: ["01", "14", "15", "22", "23", "30", "31", "44", "45"],
    火: ["02", "03", "10", "11", "18", "19", "32", "33", "40", "41", "48", "49"],
    土: ["06", "07", "20", "21", "28", "29", "36", "37"]
  };
  var ELEMENT_ORDER = ["金", "木", "水", "火", "土"];
  var ELEMENT_BY_CODE = (function () {
    var map = {};
    for (var elementIndex = 0; elementIndex < ELEMENT_ORDER.length; elementIndex += 1) {
      var codes = ELEMENT_NUMBER_GROUPS[ELEMENT_ORDER[elementIndex]];
      for (var codeIndex = 0; codeIndex < codes.length; codeIndex += 1) map[codes[codeIndex]] = ELEMENT_ORDER[elementIndex];
    }
    return map;
  })();

  // 号码 → 五行；号码缺失或非法（空、00、50…）返回 ''，**绝不**回退到生肖五行。
  function elementOfCode(code) {
    var digits = String(code == null ? "" : code).replace(/[^0-9]/g, "");
    if (!digits) return "";
    var normalized = digits.length === 1 ? "0" + digits : digits;
    return ELEMENT_BY_CODE[normalized] || "";
  }

  // 特码**号码**的五行：特码 = `raw.res_code` 的最后一项（后端
  // `mechanisms.py` 的 mode 53 命中也按「res_code 最后一个号码按特码处理」）。
  // 未开奖（res_code 为空）或指到非法号码时返回 ''，此时不高亮任何行。
  function specialElementOfCode(row) {
    var codes = String(row && row.raw && row.raw.res_code || "").match(/\d{1,2}/g) || [];
    return codes.length ? elementOfCode(codes[codes.length - 1]) : "";
  }

  // 正文五行标签归一化：去掉引号/括号/空白与后缀「行」（`土行`、`【木】` → `土`/`木`）。
  // 与 `frontend/lib/element-number-groups.ts::normalizeElementLabel` 同口径。
  function normalizeElementLabel(value) {
    return String(value == null ? "" : value)
      .replace(/[[\](){}「」【】"'“”‘’　\s]/g, "")
      .replace(/行$/, "");
  }

  // Fallback for vendor tables with one pre-existing text field per history row.
  // It writes that field only, never a table/div/container, and has a named
  // renderer entry so a new vendor layout cannot silently use raw API tokens.
  //
  // 展示规范 S2/S3：只有**本期命中的那一项**（生肖/号码/波色/段位/文字）带黄底，
  // 期号、模块名、开奖结果与未命中项一律不允许高亮。所以候选值不再整行标黄，
  // 而是「一个候选一个 span」，命中的那一个由本行自己的候选与真实开奖复算决定。
  function tokenNumberList(token) {
    return (String(token == null ? "" : token).split("|").slice(1).join("|").match(/\d{1,2}/g) || []).map(function (value) {
      return value.length === 1 ? "0" + value : value;
    });
  }

  // scope = "special"：候选与特码/特肖比（三头中特、综合资料、四肖中特、一波中特…）
  // scope = "drawn"  ：候选与整期 7 个开奖号码比（平特一尾、平特一肖…）
  function candidateHit(draw, token, scope) {
    if (!draw || !draw.opened) return false;
    var label = firstValue(token);
    var numbers = tokenNumberList(token);
    if (scope === "drawn") {
      if (numbers.length) return numbers.some(function (number) { return draw.numbers.indexOf(number) >= 0; });
      return Boolean(label) && draw.zodiacs.indexOf(label) >= 0;
    }
    if (numbers.length) return Boolean(draw.code) && numbers.indexOf(draw.code) >= 0;
    return Boolean(label) && label === draw.zodiac;
  }

  function structuredCandidates(row, mapping) {
    var tokens = predictionTokens(row);
    if (!tokens.length && row && row.prediction && row.prediction.text) {
      tokens = String(row.prediction.text).split(/[,\s]+/).filter(Boolean);
    }
    // 一波中特的 content 是 `蓝波`，兼容层把它拆成两个单字 token（显示成 `蓝·波`）。
    // 这里按「一个波色一个候选」合并展示，命中判定才落在一个完整的波色上。
    if (mapping.mergeTokens) return [{ text: tokens.map(firstValue).join(""), token: tokens.join("") }];
    return tokens.map(function (token) {
      return { text: firstValue(token), token: token };
    }).filter(function (item) { return item.text; });
  }

  function structuredHit(draw, mapping, item, row) {
    if (mapping.mergeTokens) return Boolean(draw.opened && draw.code && waveForNumber(draw.code) === item.text);
    // 五行类玩法（mode 53「综合资料」三行/精准五行）：候选就是一个五行标签，
    // 命中的那一行只由特码的**号码五行**决定。这里**不读**正文里的号码清单：
    // 历史 mode 53 正文的清单是按生肖五行拼的（24∈土、37∈火、04∈木），拿它定位
    // 会把黄底点在错行上（应当 24/37/45=木、04=金）。未开奖 / 特码缺失 / 标签不是
    // 五行名 → 不高亮。判定本身仍只来自接口的 `is_correct`，本函数只决定黄底。
    if (mapping.hitElement) {
      if (!draw || !draw.opened) return false;
      var element = specialElementOfCode(row);
      return Boolean(element) && normalizeElementLabel(item.text) === element;
    }
    return candidateHit(draw, item.token, mapping.hitScope || "special");
  }

  function writeStructuredLine(valueSlot, row, mapping) {
    clearNodeChildren(valueSlot);
    if (!row) return;
    var draw = drawnAtoms(row);
    var rowHit = isHitRow(row);
    appendTextNode(valueSlot, termValue(row) + " " + mapping.title + "：");
    structuredCandidates(row, mapping).forEach(function (item, index) {
      if (index) appendTextNode(valueSlot, "·");
      appendValueSpan(valueSlot, item.text, rowHit && structuredHit(draw, mapping, item, row));
    });
    appendTextNode(valueSlot, " 开：" + openedResult(row));
  }

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
      // 少数行（一波中特的第一个 `<p>《红红红》</p>`）只有裸文本、没有可复用的
      // `font/span` 叶子，于是整行永远写不进去、屏幕上是空行 —— 最新一期就凭空消失。
      // 首次清空之后这一行就再也没有文字，所以用一个持久标记记住「这一行自己就是值槽」；
      // 供应商的装饰性空行（如三头中特的第一行）从未有过文字，不会被标记，仍然保持空白。
      var valueRow = node.getAttribute("data-site-valuerow") === "true";
      if (!valueSlot && !node.children.length && (valueRow || String(node.textContent || "").trim())) {
        node.setAttribute("data-site-valuerow", "true");
        valueSlot = node;
      }
      var apiRow = apiRows[index];
      // 供应商模板为样例那一期预埋的黄标先无条件清除：判定为「错」的期因此整行零黄底，
      // 判定为「准」的期也只保留下面重新点亮的命中项。
      clearRowHighlight(node);
      clearOtherLeafText(node, valueSlot);
      // Extra vendor rows are deliberately blank: reusing a previous API row
      // would falsely display the same issue multiple times.
      if (valueSlot) writeStructuredLine(valueSlot, apiRow, mapping);
      applyRowHighlight(node, apiRow, module);
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
      applyRowHighlight(header, xiaoRow, xiao);
      if (detail) {
        var detailFont = slot(detail, "linked-groups", function (root) { return root.querySelector("font"); });
        if (detailFont) detailFont.textContent = tailPairValues(weiRow).map(function (value) { return "【" + value + "尾】"; }).join("") + "\n" + pairValues(xiaoRow).map(function (value) { return "【" + value + "】"; }).join("");
        applyRowHighlight(detail, weiRow, wei);
      }
    }
    for (var remainder = maxGroups * 2; remainder < rows.length; remainder += 1) {
      replaceExistingText(rows[remainder], "");
      applyRowHighlight(rows[remainder], null, xiao || wei);
    }
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
      // Each vendor issue group keeps its heading, an image row, then the two
      // number rows. Walk to the preceding single-cell heading rather than
      // treating that image row as the title.
      var headingRow = rows[index];
      while ((headingRow = headingRow.previousElementSibling)) {
        if (headingRow.querySelectorAll("td").length === 1) break;
      }
      if (headingRow) {
        headingRow.setAttribute("data-site-slot", "ma24-heading");
        var headingSlot = headingRow.querySelector("td span[style*='color: #000000']") || headingRow.querySelector("td");
        if (headingSlot) setExistingText(headingSlot, row ? termValue(row) + " 精选24码;准确率绝对100%;大胆下注!" : "");
        applyRowHighlight(headingRow, row, module);
      }
      Array.prototype.slice.call(rows[index].querySelectorAll("td")).concat(
        rows[index + 1] ? Array.prototype.slice.call(rows[index + 1].querySelectorAll("td")) : []
      ).forEach(function (cell, cellIndex) {
        cell.setAttribute("data-prediction-row", String(historyIndex));
        setNodeText(cell, values[cellIndex] || "");
        applyRowHighlight(cell, row, module);
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

  // The vendor template repeats id="top_8" twice before the actual four-zodiac
  // table. Identify the supplied title table first, then use its existing
  // sibling content block rather than a fragile duplicate-ID occurrence.
  function fourZodiacHistoryTarget() {
    var titleTable = Array.prototype.filter.call(window.document.querySelectorAll("table"), function (table) {
      return String(table.textContent || "").indexOf("『四肖中特』") !== -1;
    })[0];
    var target = titleTable && titleTable.nextElementSibling;
    // The title's immediate sibling is an inline vendor style node.
    while (target && !(target.matches && target.matches(".dz_content08ab2d"))) target = target.nextElementSibling;
    return target || null;
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
      applyRowHighlight(cell, row, module);
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
      applyRowHighlight(cell, row, module);
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
      // 供应商模板在《单单单》/《双双双》里预埋了黄底 span；写值只会清空它的文字，
      // 空 span 的黄底仍会被算成高亮，所以这里连黄底一起清掉。
      clearRowHighlight(line);
      replaceExistingText(line, row ? termValue(row) + "《" + label + "》" + openedResult(row, "√") : "");
      applyRowHighlight(line, row, module);
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
          var inRange = leafIndex < codeValues.length;
          leaf.textContent = inRange ? codeValues[leafIndex] : "";
          // 分隔符 "." 放在叶子之外的文本节点里，命中的号码叶子因此只含两位数字，
          // 黄底不会连尾随的点号一起点亮（改前是 `<font>10.</font>` 整块变黄）。
          var separator = leaf.nextSibling;
          if (inRange && leafIndex < codeValues.length - 1) {
            if (separator && separator.nodeType === 3) separator.nodeValue = ".";
            else leaf.parentNode.insertBefore(window.document.createTextNode("."), leaf.nextSibling);
          } else if (separator && separator.nodeType === 3) {
            separator.nodeValue = "";
          }
          if (inRange) leaf.setAttribute("color", "#FF0000");
          // Obsolete hits from the previous issue or lottery are cleared here;
          // the current special number is marked after every value is written.
          markHitLeaf(leaf, false);
        });
      });
      // The supplied line already contains nested number fonts. Reuse the
      // matching existing one for a visible yellow special-number highlight.
      // Only an issue that actually hit may carry that marker, so a miss row
      // never keeps a stale one.
      var specialNumber = isHitRow(row) ? resultCode(row) : "";
      if (specialNumber) {
        Array.prototype.forEach.call(lines, function (line) {
          var numberFont = Array.prototype.filter.call(line.querySelectorAll("font"), function (node) {
            return !node.children.length && String(node.textContent || "").replace(/\D/g, "") === specialNumber;
          })[0];
          if (numberFont) markHitLeaf(numberFont, true);
        });
      }
      if (footer) {
        footer.setAttribute("data-site-slot", "fifteen-code-footer");
        replaceExistingText(footer, row ? term + "一尾一码：（" + oneCode + "）" : "");
      }
      applyRowHighlight(card, row, module);
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
      // 供应商模板在「波色:」「尾数:」里预埋了黄底 span；清空文字不会去掉黄底，
      // 空黄底仍会被审计按计算样式算成高亮，所以整格先清一次。
      clearRowHighlight(cell);
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
      applyRowHighlight(cell, row, module);
    });
  }
  function killSummary(row, label) {
    if (!row) return "";
    var values = predictionTokens(row).map(firstValue).filter(Boolean).join("·");
    return termValue(row) + "稳杀" + label + "【" + values + "】开" + (row.result && row.result.isOpened ? "" : "?????");
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
    var container = target.querySelector("span[style*='font-size: 13pt']");
    if (!container) return;
    var nodes = Array.prototype.slice.call(container.childNodes);
    nodes.forEach(function (node, index) {
      if (node.nodeType === 1 && node.tagName === "FONT" && /绝杀(?:二肖|二尾|一头|一行)/.test(node.textContent || "")) {
        var blockIndex = blocks.map(function (block) { return block.sourceHeading; }).indexOf((node.textContent || "").replace(/[（）()]/g, ""));
        if (blockIndex >= 0) node.textContent = "（" + blocks[blockIndex].heading + "）";
        if (blockIndex < 0) return;
        var nextHeading = nodes.slice(index + 1).findIndex(function (candidate) {
          return candidate.nodeType === 1 && candidate.tagName === "FONT" && /绝杀(?:二肖|二尾|一头|一行)/.test(candidate.textContent || "");
        });
        var blockNodes = nodes.slice(index + 1, nextHeading < 0 ? nodes.length : index + 1 + nextHeading);
        if (!compositeLineSlots[blockIndex]) {
          compositeLineSlots[blockIndex] = blockNodes.filter(function (candidate) {
            return candidate.nodeType === 3 && /稳杀/.test(String(candidate.nodeValue || ""));
          }).slice(0, 8);
        }
        var lines = compositeLineSlots[blockIndex];
        lines.forEach(function (lineNode, rowIndex) {
          var row = moduleRow(moduleByKey[blocks[blockIndex].key], rowIndex);
          lineNode.nodeValue = row ? killSummary(row, blocks[blockIndex].label) : "";
          var resultNode = nodes[nodes.indexOf(lineNode) + 1];
          if (resultNode && resultNode.nodeType === 1 && resultNode.tagName === "FONT") {
            setExistingText(resultNode, row && row.result && row.result.isOpened ? displayResult(row) : "");
            resultNode.setAttribute("data-prediction-row", blocks[blockIndex].key + "-" + rowIndex);
            applyRowHighlight(resultNode, row, moduleByKey[blocks[blockIndex].key]);
          }
        });
      }
    });
  }

  // The later "只是有点帅" card is a separate vendor block, despite sharing
  // the exact juesha2xiao backend mechanism with 综合绝杀. Keep its eight
  // supplied paragraphs and write issue/content/result into their declared
  // leaf slots independently.
  function renderSteadyJueshaTwoXiaoHistory(_mapping, _module, moduleByKey) {
    var anchor = window.document.querySelector("p[data-prediction-section='juesha2xiao-steady']");
    if (!anchor) return;
    var rows = [anchor];
    var node = anchor.nextElementSibling;
    while (node && rows.length < 8) {
      if (node.tagName === "P") rows.push(node);
      node = node.nextElementSibling;
    }
    var module = moduleByKey && moduleByKey.juesha2xiao;
    rows.forEach(function (paragraph, index) {
      paragraph.setAttribute("data-prediction-row", String(index));
      var row = moduleRow(module, index);
      var issue = paragraph.querySelector("[data-prediction-issue]");
      var content = paragraph.querySelector("[data-prediction-content]");
      var result = paragraph.querySelector("[data-prediction-result]");
      setExistingText(issue, row ? termValue(row) + " " : "");
      setExistingText(content, row ? "绝杀二肖: 【" + zodiacValues(row).slice(0, 2).join("") + "】开:" : "");
      setExistingText(result, row ? displayResult(row) : "");
      applyRowHighlight(paragraph, row, module);
      if (result) {
        if (row && row.result && row.result.isCorrect) result.setAttribute("color", "#FF0000");
        else result.removeAttribute("color");
      }
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
      // Both vendor rows carry one issue. The supplier authored each history row
      // with a sample hit marker, and that marker describes the sample draw, not
      // this issue. The whole pair is therefore scrubbed **before** the renderer
      // writes its values, so a miss can never keep a yellow mark and a hit is
      // marked on the value it actually matched instead of on the sample cell.
      if (moduleHasRows(module)) {
        clearRowHighlight(rows[index]);
        clearRowHighlight(rows[index + 1]);
      }
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
      applyRowHighlight(tr, row, module);
    });
  }

  // The value run lives in the deepest supplier text node of the cell; rebuilding
  // inside that node's parent keeps the supplied font colour and background, and
  // gives every displayed candidate its own span so a hit can be marked.
  function firstTextParent(root) {
    var nodes = textNodes(root);
    return nodes.length && nodes[0].parentElement ? nodes[0].parentElement : root;
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

  // 本期候选肖 = `raw.xiao` 的 2 肖；兼容载荷缺该列时退回 tokens 里天地分组之后的肖。
  function tiandiPair(row) {
    var raw = row && row.raw && row.raw.xiao;
    var values = [];
    if (Array.isArray(raw)) values = raw.map(String);
    else if (typeof raw === "string") values = raw.split(/[,，、|\s]+/);
    values = values.map(function (value) { return String(value).trim(); }).filter(function (value) {
      return /^[鼠牛虎兔龙蛇马羊猴鸡狗猪]$/.test(value);
    });
    return values.length ? values : zodiacValues(row).slice(1, 3);
  }

  // 站点既有的命中助手是 `markHitLeaf`（只写内联 `#FFFF00`，页面靠可见黄底呈现）。
  // 这里在同一个节点上补跨站标准标记 `data-prediction-hit="true"`，让「只标命中项」
  // 既可看见又可被契约/审计断言；复用既有 span，不新增任何元素。
  function appendTiandiSpan(root, text, hit) {
    var span = appendValueSpan(root, text, hit);
    if (hit) span.setAttribute("data-prediction-hit", "true");
    return span;
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
      var pair = tiandiPair(row);
      var valueRoot = slot(cell, "tiandi-value", firstTextParent);
      clearRowHighlight(tr);
      clearNodeChildren(valueRoot);
      if (!row) return;
      // 天地生肖（mode 5）的候选是双维度：`content` 的天地组（6 肖）+ `xiao` 的
      // 本期 2 个候选肖。vendor/接口的 `is_correct` 只比对那 2 肖（后端 `title_5`
      // 是 contains_hit），天地组永远不参与判定 → 270 期「天肖+兔鸡」开 37 马，
      // 组里明明含马却显示「错」。这里本地复算并集：特肖 ∈ 天地组 ∪ 两肖 任一
      // 即命中，与 twwanli `#tdsx` / twsyw `#nannv` 同口径；未开奖或拿不到特肖的
      // 行不做判定，也绝不标黄。
      var draw = drawnAtoms(row);
      var decided = Boolean(draw.opened && draw.zodiac);
      var inGroup = decided && tiandiGroup(nature).indexOf(draw.zodiac) >= 0;
      var inPair = decided && pair.indexOf(draw.zodiac) >= 0;
      var hit = inGroup || inPair;
      var verdict = decided ? (hit ? "对" : "错") : "";
      var drawn = drawValue(row);
      appendTextNode(valueRoot, termValue(row) + ": 天地 【");
      // 只点亮真正命中的那一项：命中两肖 → 点亮那个生肖；命中天地组 → 点亮组名；
      // 两项都命中时优先点亮生肖（与 twwanli `renderHeavenEarth` 一致）。
      appendTiandiSpan(valueRoot, nature, inGroup && !inPair);
      appendTextNode(valueRoot, "+");
      pair.forEach(function (zodiac) {
        appendTiandiSpan(valueRoot, zodiac, inPair && zodiac === draw.zodiac);
      });
      appendTextNode(
        valueRoot,
        "】 开:" + (draw.opened && drawn && drawn !== "待开奖" ? drawn + verdict : "待开奖")
      );
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
      writePairedHeader(header, row, "╔8肖16码╗");
      var detailSlot = detail.querySelector("td > p > b > font");
      if (!detailSlot) return;
      var draw = drawnAtoms(row);
      // 8肖中特（mode 48）：候选肖 == 特肖即命中。每组的肖与码各占一个 span，
      // 肖按特肖命中、码按特码命中，所以只有真正命中的那一项带黄底。标黄以本行
      // 自己的判定为前提：判定为「错」的期一律不留黄底（S3）。
      var rowHit = isHitRow(row);
      clearNodeChildren(detailSlot);
      groups.forEach(function (group, groupIndex) {
        if (groupIndex === 4) detailSlot.appendChild(window.document.createElement("br"));
        appendValueSpan(detailSlot, group.zodiac, rowHit && isSpecialZodiac(draw, group.zodiac));
        appendValueSpan(detailSlot, group.numbers.join("."), rowHit && group.numbers.some(function (number) {
          return isSpecialNumber(draw, number);
        }));
      });
    });
  }

  function renderFiveNotHistory(mapping, module) {
    var table = tableInsideAfter("top_10", 0, 1);
    if (!table) return;
    table.setAttribute("data-prediction-section", mapping.key);
    pairedHistoryRows(table, module, function (header, detail, row) {
      var numbers = numericTokenValues(row).slice(0, 5);
      writePairedHeader(header, row, "『内幕⑤不中』", "准");
      var slots = predictionLeaves(detail);
      slots.forEach(function (slot, valueIndex) { slot.textContent = row ? numbers[valueIndex] || "" : ""; });
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
      writePairedHeader(header, row, "╔三肖六码╗");
      var detailSlot = detail.querySelector("td > p > b > font");
      if (!detailSlot) return;
      var draw = drawnAtoms(row);
      // 平特3肖（mode 470）的命中口径是「任何一个开奖号码的生肖落在候选肖里」，
      // 所以展示的候选肖/候选码逐个与**整期 7 个号码**比对：命中的肖与命中的码
      // 才带黄底，分组说明（凶丑/吉美）本身永远不高亮；标黄仍以本行判定为前提。
      var rowHit = isHitRow(row);
      clearNodeChildren(detailSlot);
      if (!row) return;
      appendTextNode(detailSlot, "【");
      appendValueSpan(detailSlot, category, false);
      appendTextNode(detailSlot, "】【");
      zodiacs.forEach(function (zodiac) {
        appendValueSpan(detailSlot, zodiac, rowHit && isFlatZodiac(draw, zodiac));
      });
      appendTextNode(detailSlot, "】");
      detailSlot.appendChild(window.document.createElement("br"));
      appendTextNode(detailSlot, "【");
      xiaoNumbers(row).forEach(function (number, numberIndex) {
        if (numberIndex) appendTextNode(detailSlot, "-");
        appendValueSpan(detailSlot, number, rowHit && isDrawnNumber(draw, number));
      });
      appendTextNode(detailSlot, "】");
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
      if (!tokens.length && row && row.prediction && row.prediction.text) tokens = [row.prediction.text];
      var groups = [];
      tokens.forEach(function (token) {
        var raw = String(token == null ? "" : token);
        var labelMatch = raw.match(/(?:红波|蓝波|绿波)/);
        var label = labelMatch ? labelMatch[0] : firstValue(raw);
        var values = ((labelMatch ? raw.slice(raw.indexOf(label) + label.length) : raw.split("|").slice(1).join("|")).match(/\d{1,2}/g) || []).map(function (value) {
          return value.length === 1 ? "0" + value : value;
        });
        // The shuangbo backend payload carries wave labels only ("红波,蓝波").
        // Fill each selected wave with its canonical ten numbers so the
        // vendor's 双波10码 card renders a complete two-wave row.
        if (!values.length && WAVE_NUMBERS[label]) values = WAVE_NUMBERS[label].slice(0, 10);
        if (/^(?:红波|蓝波|绿波)$/.test(label) && values.length) groups.push(label + ":" + values.slice(0, 10).join("."));
      });
      writePairedHeader(header, row, "『双波10码』");
      var waveSlots = Array.prototype.filter.call(detail.querySelectorAll("td > p > font > font"), function (node) {
        return /^(?:blue|green|red)$/i.test(node.getAttribute("color") || "");
      });
      if (waveSlots.length !== 2) return;
      var draw = drawnAtoms(row);
      var waveHit = isHitRow(row) ? waveForNumber(draw.code) : "";
      waveSlots.forEach(function (slot, groupIndex) {
        var waveName = groups[groupIndex] ? groups[groupIndex].split(":", 1)[0] : "";
        var label = waveName ? waveName + ":" : "";
        var directText = Array.prototype.filter.call(slot.childNodes, function (child) {
          return child.nodeType === 3;
        });
        // 双波中特（mode 38）的命中口径是「特码落在候选波色里」：命中的波色才
        // 高亮，所以波色标签也放进自己的 span（供应商模板里标签只是裸文本，
        // 没有可标注的元素），未命中的波色与其中的号码一律不带黄底。
        var labelSlot = slot.querySelector('[data-site-slot="wave-label"]');
        if (!labelSlot) {
          labelSlot = window.document.createElement("span");
          labelSlot.setAttribute("data-site-slot", "wave-label");
          slot.insertBefore(labelSlot, slot.firstChild);
        }
        // 只有波色名本身属于命中项，分隔用的冒号留在文本节点里，
        // 这样黄底不会连标点一起点亮。
        labelSlot.textContent = row ? waveName : "";
        markHitLeaf(labelSlot, Boolean(waveHit && waveName && waveHit === waveName));
        // Vendor dots (or previously converted commas) between number slots
        // become commas; any other stale text run is blanked so it can never
        // concatenate with the label. The conversion runs once with an empty
        // module during the initial clear pass, so it must stay idempotent.
        directText.slice(1).forEach(function (text) {
          text.nodeValue = /^\s*[.,]\s*$/.test(text.nodeValue || "") ? "," : "";
        });
        if (directText.length) directText[0].nodeValue = row && waveName ? ":" : "";
        // Vendor highlight spans may carry a stale wave label; blank them so
        // the label never concatenates with the freshly written one. The label
        // span is the one element this adapter owns and must stay untouched.
        Array.prototype.forEach.call(slot.querySelectorAll("span"), function (span) {
          if (span === labelSlot) return;
          if (!span.children.length) span.textContent = "";
        });
        predictionLeaves(slot).forEach(function (numberSlot, numberIndex) {
          var values = groups[groupIndex] ? groups[groupIndex].split(":")[1].split(".") : [];
          var value = row ? values[numberIndex] || "" : "";
          numberSlot.textContent = value;
          markHitLeaf(numberSlot, Boolean(waveHit) && isSpecialNumber(draw, value));
        });
      });
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

  // 复用供应商既有的叶子节点写值：颜色/字号（例如 `<font color="#FF0000" size="4">`）
  // 全部保持原样，只把值写进去，并让等于本期命中项的那一个叶子带黄底。
  // `separator` 用于补回写值时被清空的标点（`必中二头：2,3` 的逗号），
  // 逗号留在叶子外的文本节点里，所以黄底只包住数字本身。
  function writeLeafValues(root, values, hitValue, separator) {
    var leaves = Array.prototype.filter.call(root.querySelectorAll("font, span"), function (node) {
      return !node.children.length;
    });
    leaves.forEach(function (leaf, index) {
      var value = values[index] || "";
      var keepSeparator = Boolean(separator) && Boolean(value) && index < values.length - 1;
      leaf.textContent = value;
      markHitLeaf(leaf, Boolean(hitValue && value && value === hitValue));
      var next = leaf.nextSibling;
      if (keepSeparator) {
        if (next && next.nodeType === 3) next.nodeValue = separator;
        else leaf.parentNode.insertBefore(window.document.createTextNode(separator), leaf.nextSibling);
      } else if (next && next.nodeType === 3) {
        next.nodeValue = "";
      }
    });
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
      // 供应商样例里那个黄色数字属于样例那一期，先无条件清除；本期是否命中另行点亮。
      clearRowHighlight(card);
      var draw = drawnAtoms(row);
      var rowHit = isHitRow(row);
      var headHit = rowHit && draw.opened && draw.code ? draw.code.charAt(0) : "";
      Array.prototype.forEach.call(left, function (line, lineIndex) {
        var heads = groups.slice(0, lineIndex + 1).map(function (group) { return group.label; });
        replaceExistingText(line, row ? termValue(row) + "必中" + ["一", "二", "三", "四"][lineIndex] + "头：" : "");
        writeLeafValues(line, row ? heads : [], headHit, ",");
        applyRowHighlight(line, row, module);
      });
      Array.prototype.forEach.call(right, function (line, lineIndex) {
        var numbers = row && groups[lineIndex] ? groups[lineIndex].numbers : [];
        replaceExistingText(line, row ? ["①", "②", "③", "④"][lineIndex] : "");
        var container = line.querySelector("font") || line;
        clearNodeChildren(container);
        numbers.forEach(function (number, numberIndex) {
          if (numberIndex) appendTextNode(container, ".");
          appendValueSpan(container, number, rowHit && draw.opened && number === draw.code);
        });
        applyRowHighlight(line, row, module);
      });
      if (foot) {
        replaceExistingText(foot, row ? "本期推荐一头：（" + (groups[0] ? groups[0].label : "") + "头）" : "");
        applyRowHighlight(foot, row, module);
      }
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
    // ⑨⑧⑦⑥肖中特都是「**九肖中特**」的前 N 肖。数据源优先取 mode 49（`9xzt`，真 9 肖）；
    // 只有该模块没有行时才退回 mode 44（`7xiao7ma`，7 肖）并用固定顺序补齐到 9，
    // 保证卡片不会因为缺 9 肖数据整块空掉。
    var selected = zodiacValues(row).slice(0, 9);
    ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"].forEach(function (value) {
      if (selected.indexOf(value) === -1) selected.push(value);
    });
    return selected.slice(0, 9);
  }

  /** 标题行的开奖段：`开:03龙`；未开奖 `开:待开奖`。 */
  function aaaResultText(row) {
    var result = row && row.result || {};
    if (!result.isOpened) return "开:待开奖";
    var draw = drawnAtoms(row);
    var code = resultCode(row);
    return "开:" + (code && draw.zodiac ? code + draw.zodiac : drawValue(row));
  }

  /**
   * 每行末尾的判定字：已开奖写「对 / 错」，未开奖留空（S1）。
   *
   * 判定字挂在 `<strong>` 上（不是那个装生肖槽的 `font[color='#fa035a']`），
   * 免得把判定字混进「候选槽」里被下游当成第 10 个生肖读走。
   */
  function aaaVerdictSlot(detailRow, opened, hit) {
    var strong = detailRow && detailRow.querySelector("strong");
    if (!strong) return;
    var node = strong.querySelector("[data-site-slot='aaa-verdict']");
    if (!node) {
      node = window.document.createElement("font");
      node.setAttribute("data-site-slot", "aaa-verdict");
      strong.appendChild(node);
    }
    node.setAttribute("color", hit ? "#FF0000" : "#000000");
    node.textContent = opened ? (hit ? " 对" : " 错") : "";
  }

  function clearDynamicPredictionText(root) {
    if (!root) return;
    textNodes(root).forEach(function (node) {
      var value = String(node.nodeValue || "");
      if (/\b(?:19\d|20\d|\d{3})期|待开奖|\?{3,}|(?:\d{2}[鼠牛虎兔龙蛇马羊猴鸡狗猪](?:对|错)?)/.test(value)) node.nodeValue = "";
    });
  }

  function renderAaaGradeHistory(moduleByKey) {
    // 需求（2026-10-03 报障）：这一块要能看出命中与判定 —— 「命中的生肖标黄 + 每行有对/错」。
    // 数据源换成 mode 49（`9xzt` 九肖中特）；判定**逐行按本行展示的前 N 肖复算**，
    // 不能用整份 9 肖的接口判定（旧实现连「⑥肖」行没含特肖也会跟着整份判定上黄底）。
    var module = moduleHasRows(moduleByKey["9xzt"]) ? moduleByKey["9xzt"] : moduleByKey["7xiao7ma"];
    aaaTables().forEach(function (table, index) {
      var row = moduleRow(module, index);
      var rows = table.querySelectorAll("tr");
      table.setAttribute("data-prediction-section", "aaa-grade");
      table.setAttribute("data-prediction-row", String(index));
      // 供应商为样例那一期在每个 ⑨⑧⑦⑥肖 行里预埋了一处黄标。那处黄标与本期无关，
      // 过去只在「判定为错」的期才被清掉，于是命中的期会把样例的**别的生肖**留在屏上。
      // 现在无条件先清，再按本期特肖重新点亮：命中的肖才有黄底，其余一律没有。
      clearRowHighlight(table);
      if (rows[0]) setExistingText(rows[0].querySelector("strong") || rows[0], row ? termValue(row) + " AAA级大公开;准确率绝对100%;大胆下注! " + aaaResultText(row) : "");
      var draw = drawnAtoms(row);
      var zodiacs = row ? aaaZodiacs(row) : [];
      [9, 8, 7, 6].forEach(function (count, rowIndex) {
        if (!rows[rowIndex + 1]) return;
        var outer = rows[rowIndex + 1].querySelector("font[color='#fa035a']");
        if (!outer) return;
        setDirectText(outer, row ? termValue(row) + "⑨⑧⑦⑥".charAt(rowIndex) + "肖中特:" : "");
        // 本行候选 = 九肖的前 count 个；命中 = 本期特肖出现在**本行**候选里。
        var candidates = zodiacs.slice(0, count);
        var hit = Boolean(row && draw.opened && draw.zodiac && candidates.indexOf(draw.zodiac) >= 0);
        Array.prototype.filter.call(outer.children, function (child) {
          return child.tagName === "FONT" || child.tagName === "SPAN";
        }).forEach(function (valueSlot, valueIndex) {
          var value = candidates[valueIndex] || "";
          setExistingText(valueSlot, value);
          markHitLeaf(valueSlot, Boolean(hit && value && value === draw.zodiac));
        });
        aaaVerdictSlot(rows[rowIndex + 1], Boolean(row && draw.opened), hit);
      });
      // 这里**不能**再调 `applyRowHighlight`：它按整份模块的判定清黄底，
      // 会把「⑥肖这一行自身命中」的黄底一起抹掉。
    });
  }

  function renderCompleteSections(moduleByKey) {
    moduleByKey = moduleByKey || {};
    renderGradeHistory(moduleByKey);
    renderAaaGradeHistory(moduleByKey);
    COMPLETE_SECTION_MAPPINGS.forEach(function (mapping) {
      mapping.renderer(mapping, moduleByKey[mapping.key], moduleByKey);
    });
    markPredictionContainers();
  }

  // 需求1：把预测内容的**祖先容器**（`.box.pad` / `.contentbox_01` /
  // `.dz_content08ab2d` / `.Contentbox50000` / `#table1` …）标记出来，由页面里的
  // 展示规范样式表统一居中。只标记真正包住预测模块的容器，页脚（属性知识 /
  // 免责声明）与图纸导航因为不含预测模块而不受影响。
  function markPredictionContainers() {
    Array.prototype.forEach.call(window.document.querySelectorAll("[data-prediction-section]"), function (section) {
      var node = section.parentElement;
      while (node && node !== window.document.body) {
        var cls = String(node.className || "");
        if (cls.indexOf("cgi-body") >= 0 || cls.indexOf("legacy-site-footer") >= 0) break;
        node.setAttribute("data-prediction-center", "true");
        node = node.parentElement;
      }
    });
  }

  function clearStaticPredictionPayload() {
    // During deferred loading, no vendor prediction, result or hit text is exposed.
    window.document.querySelectorAll("[data-site-slot='aaa-grade-card']").forEach(function (table) {
      clearDynamicPredictionText(table);
    });
    clearUnmappedStaticPredictionText();
    renderCompleteSections({});
    renderSxztuImage();
  }

  function loadLatestPredictions(lottery) {
    lottery = lottery || activeLottery;
    return preload("predictions", { lotteryType: lottery.lotteryType, historyLimit: 1, includeVendor: false }).then(function (result) {
      var modules = modulesFrom(result);
      if (modules) latestModulesByLottery[lottery.lotteryType] = modules;
      // Race guard: the latest (1-issue) response may arrive after the
      // historical (16-issue) response. Re-rendering grade and fifteen-code
      // sections with the 1-issue payload would wipe the already-rendered
      // history back to a single issue, so skip when history is complete.
      if (modules && activeLottery.lotteryType === lottery.lotteryType && !historicalModulesByLottery[lottery.lotteryType]) {
        renderGradeHistory(modules);
       renderFifteenCodeHistory({ key: "title_66" }, modules.title_66);
        renderSxztuImage(modules.sxztu);
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
      if (activeLottery.lotteryType === lotteryType) renderSxztuImage(modules.sxztu);
      return modules;
    }, function () {
      var modules = latestModulesByLottery[lotteryType] || {};
      if (activeLottery.lotteryType === lotteryType) renderCompleteSections(modules);
      if (activeLottery.lotteryType === lotteryType) renderSxztuImage(modules.sxztu);
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
        renderSxztuImage(historicalModules.sxztu);
      } else {
        clearStaticPredictionPayload();
        // A draw-tab selection must replace every visible historical module,
        // not leave the previous lottery on screen until the next scroll.
        loadHistoricalPredictions(lottery);
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
      // These sections expose eight fixed vendor history cards above the
      // fold; load their matching rows without requiring a user scroll.
      observeDeferredMappings();
    });
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
