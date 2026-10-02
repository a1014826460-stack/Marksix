(function (window) {
  "use strict";

  var siteConfig = window.Twbst528SiteConfig;
  var client = window.LotterySiteDataClient.create({ siteKey: siteConfig.siteKey });
  var activeLottery = siteConfig.lotteries[0];
  var historyByLottery = {};
  var historyRequests = {};
  // The largest reviewed supplier section has six complete issue groups.
  var HISTORY_LIMIT = 6; // historyLimit: 6

  function announce(resource, result) {
    if (typeof window.CustomEvent === "function" && typeof window.dispatchEvent === "function") {
      window.dispatchEvent(new window.CustomEvent("site-data:ready", {
        detail: { siteKey: siteConfig.siteKey, resource: resource, state: result.state }
      }));
    }
    return result;
  }

  function lotteryForType(type) {
    return siteConfig.lotteries.filter(function (lottery) {
      return lottery.lotteryType === Number(type);
    })[0] || siteConfig.lotteries[0];
  }

  function textNodes(root) {
    var nodes = [];
    if (!root || !window.document.createTreeWalker) return nodes;
    var walker = window.document.createTreeWalker(root, window.NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) nodes.push(node);
    return nodes;
  }

  function writeLeaf(element, value) {
    var leaf = textNodes(element)[0];
    if (leaf) leaf.nodeValue = String(value || "");
  }

  function clearLeaves(element, retained) {
    textNodes(element).forEach(function (leaf) {
      if (retained.indexOf(leaf) === -1) leaf.nodeValue = "";
    });
  }

  function clearMarkers(cell, unwrapMarkers) {
    // 黄底与命中标记属性**同生共死**：只清背景色会在重置后留下「无黄底却仍带
    // data-prediction-hit」的幽灵标记，让展示契约/审计把未命中行误判成命中。
    var markers = Array.prototype.slice.call(cell.querySelectorAll("span[style*='background-color'], span[data-prediction-hit]"));
    Array.prototype.forEach.call(markers, function (marker) {
      marker.style.backgroundColor = "";
      marker.removeAttribute("data-prediction-hit");
    });
    // 只清样式还不够：供应商 CSS（home.css `.mtbl td:nth-child(2) span`）给候选列里
    // **任何** span 兜底 `background-color:#d1be18`（rgb(209,190,24)）。清掉内联 #FFFF00
    // 后 marker span 仍在，而 writeCell 的 leaves[0] 往往正好落在它里面，整段候选文本
    // 被写回这个 span，视觉上整行被染成芥末黄（线上实测：代号生肖 268 期「错」行、
    // 两波突围/六尾出特/头数单双/家野中特等模板预埋 span 的板块全部中招）。
    // 拆包（子节点前移、删掉空壳）让候选文本回到单元格层级，命中项由 writeCell
    // 重建的独立 marker 承载。writeWaveNumbers 复用模板 marker span 存命中底色，
    // 不能拆，所以拆包只在 writeCell 路径开启。
    if (unwrapMarkers) {
      Array.prototype.forEach.call(markers, function (marker) {
        if (!marker.parentNode) return;
        while (marker.firstChild) marker.parentNode.insertBefore(marker.firstChild, marker);
        marker.parentNode.removeChild(marker);
      });
    }
  }

  // A supplier template may pack several issues into one element and bake its
  // own yellow hit markers into that markup. Multi-issue lines must be judged
  // per issue (S3/S4), so every rewritten line gets its own element and every
  // stale #FFFF00 marker on the way to it is cleared before the line is written.
  var YELLOW_MARKER = /#ffff00|rgb\(\s*255\s*,\s*255\s*,\s*0\s*\)/i;
  var LINE_HOST_ATTRIBUTE = "data-prediction-line";
  // 命中标记的标准属性（《预测模块展示规范》：`[data-prediction-hit="true"]` 即命中项）。
  // 本站历史实现只写内联 `background-color:#FFFF00`，模板里**没有**预埋该属性，
  // 于是展示契约/审计无法把「命中项」与「模板残留黄底」区分开。自建 marker 时补上属性，
  // 视觉不变，但让「只有命中项带黄底」可被机器校验。
  var HIT_MARKER_ATTRIBUTE = "data-prediction-hit";

  function hasYellowMarker(node) {
    if (!node || node.nodeType !== 1 || !node.getAttribute) return false;
    if (YELLOW_MARKER.test(String(node.getAttribute("color") || ""))) return true;
    if (YELLOW_MARKER.test(String(node.getAttribute("bgcolor") || ""))) return true;
    var style = node.style;
    if (!style) return false;
    return YELLOW_MARKER.test(String(style.backgroundColor || "")) || YELLOW_MARKER.test(String(style.color || ""));
  }

  function clearYellowMarker(node) {
    if (YELLOW_MARKER.test(String(node.getAttribute("color") || ""))) node.removeAttribute("color");
    if (YELLOW_MARKER.test(String(node.getAttribute("bgcolor") || ""))) node.removeAttribute("bgcolor");
    if (node.style) {
      if (YELLOW_MARKER.test(String(node.style.backgroundColor || ""))) node.style.backgroundColor = "";
      if (YELLOW_MARKER.test(String(node.style.color || ""))) node.style.color = "";
    }
  }

  function commonAncestor(leaves) {
    var node = leaves[0].parentNode;
    while (node && !leaves.every(function (leaf) { return node.contains(leaf); })) node = node.parentNode;
    return node;
  }

  function clearLineMarkers(group) {
    var container = commonAncestor(group);
    if (!container) return;
    group.forEach(function (leaf) {
      var node = leaf.parentNode;
      while (node) {
        if (hasYellowMarker(node)) clearYellowMarker(node);
        if (node === container) break;
        node = node.parentNode;
      }
    });
  }

  function lineHost(leaf) {
    var parent = leaf && leaf.parentNode;
    if (!parent || parent.nodeType !== 1) return null;
    if (parent.getAttribute(LINE_HOST_ATTRIBUTE) !== null) return parent;
    var host = leaf.ownerDocument.createElement("span");
    host.setAttribute(LINE_HOST_ATTRIBUTE, "");
    parent.insertBefore(host, leaf);
    return host;
  }

  // Only a hit issue carries a mark: the matched token inside the 【candidate】
  // bracket is wrapped in the supplier's hit background (#FFFF00).
  function markLineHit(host, text, hitTokens) {
    if (!host || !hitTokens || !hitTokens.length) return;
    var bracket = /【([^】]*)】/.exec(text);
    var start = bracket ? bracket.index + 1 : 0;
    var end = bracket ? start + bracket[1].length : text.length;
    var token = "";
    var index = -1;
    hitTokens.forEach(function (value) {
      if (index !== -1 || !value) return;
      var found = text.indexOf(value, start);
      if (found === -1 || found + String(value).length > end) return;
      token = String(value);
      index = found;
    });
    if (index === -1) return;
    var doc = host.ownerDocument;
    var marker = doc.createElement("span");
    marker.style.backgroundColor = "#FFFF00";
    marker.setAttribute(HIT_MARKER_ATTRIBUTE, "true");
    marker.appendChild(doc.createTextNode(token));
    host.textContent = text.slice(0, index);
    host.appendChild(marker);
    if (index + token.length < text.length) host.appendChild(doc.createTextNode(text.slice(index + token.length)));
  }

  /**
   * 写入一个候选单元格，并只把 `hitValues` 里命中的那一段标黄。
   *
   * 旧实现的「markerLeaf + leaves[0] + suffix」三段式还原是**不可靠**的：上一次渲染
   * 留下的 marker span 会成为下一次渲染的 markerLeaf，它的文本只有上一期标黄的那一项，
   * 于是整个候选串会被截断在那一项上（线上实测：`鼠,牛,狗,兔,蛇,鸡,虎,龙,马` 只剩 `蛇`）。
   *
   * 现在固定为「前缀文本 → marker → 后缀文本」的结构，三者**平级插在同一个宿主**里：
   *   `<cell> …前缀… <span 黄底>命中项</span> …后缀… </cell>`
   * 之所以不再复用模板预埋的 marker：`clearMarkers()` 只清掉背景色、span 仍在，
   * 而它往往嵌在别的 font 里、文档顺序也不在候选文本之后，复用它会让元素/文本叶子
   * 的顺序错位（出现换行丢失、候选被截断）。每次重建一个干净的 marker 更稳。
   */
  function writeCell(cell, value, hitValues) {
    var text = String(value || "");
    if (!cell) return;
    var doc = cell.ownerDocument;
    // writeCell 路径拆包残留 marker span：候选列 CSS 会给任何 span 兜底芥末黄底（见 clearMarkers）。
    clearMarkers(cell, true);

    var leaves = textNodes(cell);
    if (leaves.length === 0) return;

    var matchingValue = (hitValues || []).filter(function (item) {
      return item && text.indexOf(item) !== -1;
    })[0];

    if (!matchingValue) {
      // 没有可标黄项：整段纯文本，清掉其它叶子与残留 marker。
      var plain = leaves[0];
      leaves.forEach(function (leaf) { if (leaf !== plain) leaf.nodeValue = ""; });
      plain.nodeValue = text;
      return;
    }

    var index = text.indexOf(matchingValue);
    var prefix = text.slice(0, index);
    var suffix = text.slice(index + matchingValue.length);

    // 宿主：优先沿用第一个叶子所在的元素（常见是 font），否则退回 cell。
    var host = leaves[0].parentNode || cell;

    // 清空既有文本，并移除本单元格内所有旧的黄底/空 marker，保证结构可预测。
    Array.prototype.forEach.call(cell.querySelectorAll("span"), function (span) {
      var style = String(span.getAttribute("style") || "");
      if (!span.textContent && !YELLOW_MARKER.test(style)) span.parentNode.removeChild(span);
    });

    var marker = doc.createElement("span");
    marker.style.backgroundColor = "#FFFF00";
    marker.setAttribute(HIT_MARKER_ATTRIBUTE, "true");
    marker.appendChild(doc.createTextNode(matchingValue));

    leaves.forEach(function (leaf) { leaf.nodeValue = ""; });
    var anchor = leaves[0];
    anchor.nodeValue = prefix;
    if (anchor.parentNode !== host) host.appendChild(anchor);
    if (anchor.nextSibling) host.insertBefore(marker, anchor.nextSibling);
    else host.appendChild(marker);
    host.insertBefore(doc.createTextNode(suffix), marker.nextSibling);
  }

  function writeResultCell(cell, row) {
    var leaves = textNodes(cell);
    var result = row && row.result || {};
    var leading = leaves[0];
    var detail = leaves.filter(function (leaf) { return leaf !== leading; })[0];
    if (!leading) return;
    if (!row) {
      leading.nodeValue = "";
      clearLeaves(cell, []);
      return;
    }
    if (!result.isOpened) {
      leading.nodeValue = "开:待开奖";
      clearLeaves(cell, [leading]);
      return;
    }
    var number = resultToken(result.code, true);
    var zodiac = resultToken(result.zodiac, false);
    var drawn = number && zodiac ? number + zodiac : String(result.text || "");
    var suffix = result.isCorrect === true ? "对" : result.isCorrect === false ? "错" : "";
    leading.nodeValue = "开:";
    if (detail) {
      detail.nodeValue = drawn + suffix;
      detail.parentElement.style.color = result.isCorrect === true ? "#FF0000" : "#000000";
      clearLeaves(cell, [leading, detail]);
    } else {
      leading.nodeValue = "开:" + drawn + suffix;
      clearLeaves(cell, [leading]);
    }
  }

  function modulesFrom(result) {
    var envelope = result && result.data;
    while (envelope && !Array.isArray(envelope.canonical_modules) && envelope.data) envelope = envelope.data;
    return Array.isArray(envelope && envelope.canonical_modules) ? envelope.canonical_modules.reduce(function (all, module) {
      all[String(module.moduleKey || module.module_key || "")] = module;
      return all;
    }, {}) : {};
  }

  function distinctRows(module) {
    var seen = {};
    return Array.isArray(module && module.rows) ? module.rows.filter(function (row) {
      var key = String(row && (row.issue || row.term || (row.year + "-" + row.term)) || "");
      if (!key || seen[key]) return false;
      seen[key] = true;
      return true;
    }) : [];
  }

  function termValue(row) {
    var term = String(row && (row.term || row.issue) || "").replace(/^第|期$/g, "");
    return term ? "第" + term + "期" : "";
  }

  // ── 按期号配对（不要把不同期数挤在一起）────────────────────────────────
  // 供应商模板把**静态样例期号**烤进 DOM（233/323/322…），适配器过去按「行号 index」
  // 把数据写进第 N 行；只要模板期号列表与接口期号列表的长度或顺序不完全一致，
  // 后一行就会串到别的期号位置（线上实测「码友来料参考」第 3 张卡出现 271/0/269/0/267/0）。
  // 现在统一改成**按「年+期」配对**：先读该行模板里的期号，再用它去接口数据里找同一期。
  function templateTermKey(text) {
    var source = String(text || "");
    var match = /(\d{6})\s*期/.exec(source);
    if (match) return match[1].slice(0, 4) + "|" + String(Number(match[1].slice(4)));
    match = /(\d{3})\s*期/.exec(source);
    return match ? "*|" + String(Number(match[1])) : "";
  }

  function rowTermKey(row) {
    var issue = String(row && row.issue || "").replace(/\D/g, "");
    if (issue.length >= 6) return issue.slice(0, 4) + "|" + String(Number(issue.slice(4)));
    var year = String(row && row.year || "").replace(/\D/g, "");
    var term = String(row && (row.term || issue) || "").replace(/\D/g, "");
    if (!term) return "";
    return year ? year + "|" + String(Number(term)) : "*|" + String(Number(term));
  }

  /** 返回「模板期号 → 数据行」的解析器；模板里读不到期号时退回按行号。 */
  function makeRowResolver(module) {
    var rows = distinctRows(module);
    var byKey = {};
    rows.forEach(function (row) {
      var key = rowTermKey(row);
      if (key && !byKey[key]) byKey[key] = row;
    });
    return function (templateText, index) {
      var key = templateTermKey(templateText);
      if (key && byKey[key]) return byKey[key];
      return rows[index] || null;
    };
  }

  /** 单元格当前可见文本，用于读出模板里的期号。 */
  function cellText(cell) {
    return String(cell && cell.textContent || "");
  }

  function tokens(row) {
    var values = row && row.prediction && row.prediction.tokens;
    if (Array.isArray(values) && values.length) return values.map(String).filter(Boolean);
    var text = String(row && row.prediction && row.prediction.text || "").replace(/[【】]/g, "");
    return text.split(/[|,，、\s]+/).map(function (value) { return value.trim(); }).filter(Boolean);
  }

  function predictionText(row, separator) {
    var values = tokens(row);
    return values.length ? values.join(separator || "") : String(row && row.prediction && row.prediction.text || "");
  }

  function rawValue(row, key) {
    var raw = row && row.raw || {};
    var extra = row && row.prediction && row.prediction.extra || {};
    return raw[key] !== undefined ? raw[key] : extra[key];
  }

  function valueList(value) {
    if (Array.isArray(value)) return value.map(String).filter(Boolean);
    if (typeof value === "string") {
      try {
        var parsed = JSON.parse(value);
        if (Array.isArray(parsed)) return parsed.map(String).filter(Boolean);
      } catch (_) {
        // Legacy rows can contain comma-separated values instead of JSON.
      }
      return value.split(/[，,\s]+/).map(function (item) { return item.trim(); }).filter(Boolean);
    }
    return [];
  }

  function moduleWithRows(primary, fallback) {
    return distinctRows(primary).length ? primary : fallback;
  }

  function labelTokens(row) {
    return tokens(row).filter(function (value) {
      return /[\u4e00-\u9fff]/.test(value) && !/^\d+$/.test(value);
    });
  }

  // Payload rows frequently encode a visible label and its source numbers as
  // `label|numbers`. Table cells display only the compact label sequence.
  function displayLabels(row, separator) {
    return tokens(row).map(function (value) {
      return String(value).replace(/[\[\]"]/g, "").split("|", 1)[0].trim();
    }).filter(Boolean).join(separator === undefined ? "" : separator);
  }

  function compactLabels(values, separator) {
    return (Array.isArray(values) ? values : []).map(function (value) {
      return String(value).replace(/[\[\]"]/g, "").split("|", 1)[0].trim();
    }).filter(Boolean).join(separator === undefined ? "" : separator);
  }


  // ── 固定分组（来源：public.fixed_data，权威口径）──────────────────────
  // 四艺生肖 / 大小胆肖 / 凶丑吉美生肖。用于第 4/5/6 项的语义展示。
  var SIYI_ZODIAC_ORDER = ["琴", "棋", "书", "画"];
  var SIYI_ZODIAC = {
    "琴": ["兔", "蛇", "鸡"],
    "棋": ["鼠", "牛", "狗"],
    "书": ["虎", "龙", "马"],
    "画": ["羊", "猴", "猪"],
  };
  var DANXIAO_GROUP = { "胆大": ["牛", "虎", "马", "猴", "狗", "猪"], "胆小": ["鼠", "兔", "龙", "蛇", "羊", "鸡"] };
  var XIONGJI_GROUP = { "吉美肖": ["兔", "龙", "蛇", "马", "羊", "鸡"], "丑凶肖": ["鼠", "牛", "虎", "猴", "狗", "猪"] };

  function zodiactsOf(row) {
    return tokens(row).map(function (value) {
      return String(value).replace(/[\[\]"]/g, "").split("|")[0].trim();
    }).filter(Boolean);
  }

  function matchesAny(zodiacs, group) {
    var set = {};
    group.forEach(function (z) { set[z] = true; });
    return zodiacs.some(function (z) { return set[z]; });
  }

  /** 第 4 项：候选生肖 → 四艺里出现的艺，取三种组成「书棋琴」这样的三字串。 */
  function siyiTriple(row) {
    var present = siyiArtsOf(row);
    if (!present.length) return "";
    // 必须始终是三个字：不足时按 琴→棋→书→画 固定顺序回补。
    var result = present.slice(0, 3);
    for (var i = 0; result.length < 3 && i < SIYI_ZODIAC_ORDER.length; i += 1) {
      if (result.indexOf(SIYI_ZODIAC_ORDER[i]) === -1) result.push(SIYI_ZODIAC_ORDER[i]);
    }
    return result.join("");
  }

  /** 候选生肖命中的四艺（按 琴棋书画 固定顺序）。 */
  function siyiArtsOf(row) {
    var zodiacs = zodiactsOf(row);
    if (!zodiacs.length) return [];
    return SIYI_ZODIAC_ORDER.filter(function (art) {
      return matchesAny(zodiacs, SIYI_ZODIAC[art]);
    });
  }

  /**
   * 第 4 项的标黄：展示的是艺名（不是生肖），所以要标黄**开奖特肖所属的那个艺**，
   * 例如开奖是「狗」→ 狗属「棋」→ 标黄三字串里的「棋」。
   */
  function siyiHitArts(row) {
    if (!row || !row.result || !row.result.isOpened || row.result.isCorrect !== true) return [];
    var zodiac = resultToken(row.result.zodiac, false);
    if (!zodiac) return [];
    return siyiArtsOf(row).filter(function (art) {
      return SIYI_ZODIAC[art].indexOf(zodiac) !== -1;
    });
  }

  /** 第 5/6 项：候选生肖 → 所属分组标签（如 胆大 / 胆小 / 吉美肖 / 丑凶肖）。 */
  /**
   * 第 5/6 项：候选生肖 → 所属分组标签（胆大 / 胆小 / 吉美肖 / 丑凶肖）。
   *
   * 候选可能跨两个分组（如「龙兔虎」里 龙兔 属吉美、虎 属凶丑），此时按**多数**归属；
   * 平票时取候选里更靠前的那一项所属的分组，保证结果与候选顺序一致。
   */
  function groupLabelFor(row, groups, fallback) {
    var zodiacs = zodiactsOf(row);
    if (!zodiacs.length) return fallback || "";
    var labels = Object.keys(groups);
    var bestLabel = "";
    var bestScore = -1;
    labels.forEach(function (label) {
      var score = 0;
      zodiacs.forEach(function (zodiac, index) {
        if (groups[label].indexOf(zodiac) === -1) return;
        // 越靠前的候选权重越高，用于平票时打破僵局。
        score += zodiacs.length - index;
      });
      if (score > bestScore) {
        bestScore = score;
        bestLabel = label;
      }
    });
    return bestLabel || fallback || "";
  }

  function unavailableThreeColumn(title) {
    renderThreeColumnRows(sectionByTitle(title), null, function () { return ""; });
  }

  function unavailablePairedCardHistory(title) {
    renderPairedCardHistory(title, null, function () { return ["暂无后端资料"]; });
  }

  function unavailableCompositeLines(title) {
    var section = sectionByTitle(title);
    if (!section) return;
    Array.prototype.forEach.call(section.querySelectorAll("table tbody > tr td"), function (cell) {
      lineGroups(cell).forEach(function (group) {
        var text = group.map(function (leaf) { return String(leaf.nodeValue || ""); }).join("");
        if (/\d+(?:-\d+)?期/.test(text)) writeLineGroup(group, "暂无后端资料");
      });
    });
  }

  function lineGroups(root) {
    var groups = [[]];
    function visit(node) {
      if (node.nodeType === 3) {
        groups[groups.length - 1].push(node);
        return;
      }
      if (node.nodeType !== 1) return;
      if (String(node.tagName).toUpperCase() === "BR") {
        groups.push([]);
        return;
      }
      Array.prototype.forEach.call(node.childNodes, visit);
    }
    Array.prototype.forEach.call(root ? root.childNodes : [], visit);
    return groups.filter(function (group) {
      return group.some(function (leaf) { return String(leaf.nodeValue || "").trim(); });
    });
  }

  function writeLineGroup(group, value, hitTokens) {
    if (!group || !group.length) return;
    clearLineMarkers(group);
    var text = String(value || "");
    var host = lineHost(group[0]);
    group.slice(1).forEach(function (leaf) { leaf.nodeValue = ""; });
    if (!host) {
      group[0].nodeValue = text;
      return;
    }
    // 配对卡片模板把行内容放在**占位 span 之后**：
    //   <span data-prediction-line=""></span>龙蛇兔马牛<br>
    // 只写 host.textContent 会把内容留在 span 外面（旧模板数字因此清不掉，
    // 实测「⑤肖⑩码」出现「暂无后端资料」+ 48.17.36… 同时存在）。
    // 这里把紧随其后的同一个文本节点并进 host，host 从此独占该行文本。
    var next = host.nextSibling;
    if (next && next.nodeType === 3) {
      next.nodeValue = "";
      group.push(next);
    }
    host.textContent = text;
    markLineHit(host, text, hitTokens);
  }

  /**
   * 逐行写配对卡片正文；`hitTokens`（可选）只作用于**第一行**（候选行），
   * 命中项由 `writeLineGroup → markLineHit` 标黄，其余行保持零黄底。
   */
  function writeLineValues(root, values, hitTokens) {
    var groups = lineGroups(root);
    groups.forEach(function (group, index) {
      writeLineGroup(group, values[index] || "", index === 0 ? hitTokens : null);
    });
  }

  /**
   * 把一个文本叶子里的命中项包进黄底 marker（**不新建宿主 span**）。
   *
   * 用途：【吉美丑凶】的候选格是 `.mtbl td:nth-child(2)`，供应商 CSS
   * （home.css `.mtbl td:nth-child(2) span{background-color:#d1be18}`）会给**任何**
   * 落在候选格里的 span 兜底芥末黄底 —— `writeLineGroup` 的 `lineHost()` 会新建这样一个
   * span，于是「候选行整行发黄」。这里改为只写文本叶子、命中项单独插入一个带
   * inline `background-color:#FFFF00` 的 marker（inline 覆盖 CSS 兜底色），
   * 未命中的期次一个 span 都不留。
   */
  function markTokenInLeaf(leaf, text, hitTokens) {
    var token = (hitTokens || []).filter(function (value) {
      return value && String(text).indexOf(value) !== -1;
    })[0];
    if (!leaf || !token) return false;
    var parent = leaf.parentNode;
    var doc = leaf.ownerDocument;
    if (!parent || !doc) return false;
    var index = String(text).indexOf(token);
    var marker = doc.createElement("span");
    marker.style.backgroundColor = "#FFFF00";
    marker.setAttribute(HIT_MARKER_ATTRIBUTE, "true");
    marker.appendChild(doc.createTextNode(token));
    parent.insertBefore(doc.createTextNode(String(text).slice(0, index)), leaf);
    parent.insertBefore(marker, leaf);
    leaf.nodeValue = String(text).slice(index + token.length);
    return true;
  }

  /** 与 `writeLineGroup` 同口径，但**不新建宿主 span**（见 `markTokenInLeaf`）。 */
  function writePlainLine(group, value, hitTokens) {
    if (!group || !group.length) return;
    clearLineMarkers(group);
    var text = String(value || "");
    group.slice(1).forEach(function (leaf) { leaf.nodeValue = ""; });
    group[0].nodeValue = text;
    markTokenInLeaf(group[0], text, hitTokens);
  }

  /**
   * 「开:38蛇对」开奖段。
   *
   * `invert` 只给**展示层按排除型重做的模块**用（见 `renderZongheJushaHistory`）：
   * 这些小节在「综合绝杀」面板里按杀号语义展示，而后端 `is_correct` 是**命中型**
   * （`true` = 开奖目标落在候选集合里 = 杀失败）。取反后：
   *   · 接口 `true`  → 杀失败 → 「错」
   *   · 接口 `false` → 杀中   → 「对」
   *   · 未开奖 / 接口没有判定值 → 不给判定文字。
   * 不传 `invert` 的老调用（含其它面板）行为完全不变。
   */
  function resultValue(row, invert) {
    var result = row && row.result || {};
    if (!result.isOpened) return "开:待开奖";
    var number = resultToken(result.code, true);
    var zodiac = resultToken(result.zodiac, false);
    var drawn = number && zodiac ? number + zodiac : String(result.text || "");
    var correct = result.isCorrect;
    if (invert === true) {
      correct = result.isCorrect === true ? false : result.isCorrect === false ? true : result.isCorrect;
    }
    return "开:" + drawn + (correct === true ? "对" : correct === false ? "错" : "");
  }

  function resultToken(value, padNumber) {
    var values = String(value || "").split(/[,，、|]+/).map(function (item) {
      return item.trim();
    }).filter(Boolean);
    var token = values.length ? values[values.length - 1] : "";
    return padNumber && /^\d{1,2}$/.test(token) ? token.padStart(2, "0") : token;
  }

  /** 候选 token（`土|03,06,…` / `3头|30,…`）声明的号码清单并集。 */
  function candidateNumberLists(row) {
    var codes = [];
    tokens(row).forEach(function (value) {
      var parts = String(value).replace(/[\[\]"]/g, "").split("|");
      if (parts.length < 2) return;
      parts.slice(1).join("|").split(/[,，、\s]+/).forEach(function (item) {
        var digits = String(item).replace(/\D/g, "");
        if (!digits || digits.length > 2) return;
        codes.push(String(Number(digits)).padStart(2, "0"));
      });
    });
    return codes;
  }

  /**
   * 「开奖目标是否落在**被杀集合**里」——排除型小节的命中判定（命中型语义）。
   *
   * 口径：被杀集合就是**本行候选自己声明的号码清单**（`土|05,06,…` / `3头|30,…`），
   * 所以判定 = 特码号码是否出现在这些清单里。
   *
   * 为什么按清单复算而不是只信接口 `is_correct`：五行正文的分组口径已于 2026-09-28
   * 统一到 `public.fixed_data` sign='五行'（号码五行，37→木）——与后端 outcome
   * （`special_element_from_row`）同一套划分，正文清单不再自相矛盾。此函数保留为
   * **按展示内容复算**的一致性护栏：一旦正文清单与后端口径再次漂移，展示仍与页面上
   * 列出的候选自洽；两者一致时结果与「接口判定取反」完全相同。
   *
   * 返回 `true`（含＝杀失败）/ `false`（不含＝杀中）/ `null`（拿不到清单或特码，
   * 调用方退回接口判定）。
   */
  function killedSetContainsTarget(row) {
    var code = resultToken(row && row.result && row.result.code, true);
    if (!code) return null;
    var codes = candidateNumberLists(row);
    if (!codes.length) return null;
    return codes.indexOf(code) !== -1;
  }

  /** 复制一行并覆盖 `result.isCorrect`（不改原 payload 行）。 */
  function withResultCorrect(row, correct) {
    if (!row) return null;
    var copy = {};
    Object.keys(row).forEach(function (key) { copy[key] = row[key]; });
    var result = {};
    Object.keys(row.result || {}).forEach(function (key) { result[key] = row.result[key]; });
    result.isCorrect = correct;
    copy.result = result;
    return copy;
  }

  // ── 平特口径：命中看**七个开奖号码**（六个平码 + 特码）─────────────────
  // 需求（2026-09-30）：所有平特玩法（平特①肖 / 平特一尾 / 平特 N 肖）的命中判定
  // 都要看开奖的七个号码，而不是只看最后一个特码。
  //
  // 为什么在展示层复算：接口的 `result.is_correct` 在部分数据源上仍是**特码口径**
  // （例：189 期「平特①肖 龙」，龙以平码开出，特码是狗 —— 只比特码就会判成「错」）。
  // 展示层直接用 payload 里的完整开奖串复算，页面上的「对/错」始终是平特口径。
  //
  // 完整开奖串的三种形态（按长度取最长的那一份，避免只拿到特码）：
  //   · `result.code` / `result.zodiac`：本地站点接口给的是**七码/七肖**；
  //   · `raw.res_code` / `raw.res_sx`：站点接口给的是七码/七肖；
  //   · `raw.raw.res_code` / `raw.raw.res_sx`：供应商模块（独家公式等）外层只留特码，
  //     完整串嵌套在 `raw.raw` 里。
  function longestDrawnList(lists) {
    return lists.reduce(function (best, list) {
      return list.length > best.length ? list : best;
    }, []);
  }

  /** 七个开奖号码（`20,19,38,35,23,42,45` → `["20",…,"45"]`，末位为特码）。 */
  function fullDrawnCodes(row) {
    var raw = row && row.raw || {};
    var nested = raw.raw || {};
    return longestDrawnList([
      valueList(row && row.result && row.result.code),
      valueList(raw.res_code),
      valueList(nested.res_code),
    ]).map(function (value) {
      var digits = String(value).replace(/\D/g, "");
      return digits ? digits.padStart(2, "0") : "";
    }).filter(Boolean);
  }

  /** 七个开奖号码对应的生肖（末位为特肖）。 */
  function fullDrawnZodiacs(row) {
    var raw = row && row.raw || {};
    var nested = raw.raw || {};
    return longestDrawnList([
      valueList(row && row.result && row.result.zodiac),
      valueList(raw.res_sx),
      valueList(nested.res_sx),
    ]).map(function (value) {
      return String(value).replace(/[\[\]"]/g, "").trim();
    }).filter(Boolean);
  }

  /**
   * 平特肖命中：预测的任一生肖出现在**七个开奖生肖**里。拿不到开奖串返回 null。
   *
   * 候选必须能解析成生肖字（`狗` / `狗|09`）才做复算：拿不到可解析候选时返回 `null`
   * 沿用接口判定，避免把「候选形态不认识」的期次一律压成「错」。
   */
  function flatZodiacHit(row) {
    var drawn = fullDrawnZodiacs(row);
    var picked = zodiactsOf(row).filter(function (zodiac) { return ZODIAC_CHAR_SET[zodiac]; });
    if (!drawn.length || !picked.length) return null;
    return picked.some(function (zodiac) { return drawn.indexOf(zodiac) !== -1; });
  }

  /** 平特尾命中：预测尾数出现在**七个开奖号码**的任一尾数里。拿不到开奖串返回 null。 */
  function flatTailHit(row) {
    var codes = fullDrawnCodes(row);
    var tails = tokens(row).map(function (value) {
      var digits = String(value).split("|")[0].replace(/\D/g, "");
      return digits ? digits.charAt(digits.length - 1) : "";
    }).filter(Boolean);
    if (!codes.length || !tails.length) return null;
    return codes.some(function (code) {
      return tails.indexOf(code.charAt(code.length - 1)) !== -1;
    });
  }

  /**
   * 复制一行并按平特口径重算 `result.isCorrect`（拿不到开奖串时原样返回）。
   *
   * 同时挂上 `flatDraw`：平特的命中项可能来自**平码**（不是特码），标黄链路
   * （`highlightTokens`）必须按整组开奖值判断，否则「命中却零黄底」。
   */
  function withFlatVerdict(row, kind) {
    if (!row || !row.result || !row.result.isOpened) return row;
    var hit = kind === "tail" ? flatTailHit(row) : flatZodiacHit(row);
    if (hit === null) return row;
    var copy = withResultCorrect(row, hit);
    copy.flatDraw = { zodiacs: fullDrawnZodiacs(row), codes: fullDrawnCodes(row) };
    return copy;
  }

  // 平特类模块（机制名里带「平特」）→ 判定口径。所有用到这些模块的**平特面板**
  // （平特①肖 / 平特一尾 / 三期计划的平特计划·平尾计划 / 静态文章【平特③肖连】）
  // 都在渲染入口前统一改写一次，避免各面板各写一套。
  //
  // `pt3xiao`（平特3肖，mode 470）**不在这里**：本站首页没有任何「平特③肖」面板，
  // 它只作为【吉美丑凶】【③肖防③码】的数据源，这两个面板不是平特玩法，按
  // `zodiacPanelJudgement` 的**中特口径**判定（见下方「面板级中特口径」）。
  // 需要七码口径的【平特③肖连】在 `static-article-data-adapter.js` 里，不受这里影响。
  var FLAT_MODULE_KINDS = {
    pt1xiao: "zodiac",
    pt1wei: "tail",
    pt2xiao: "zodiac",
  };

  function applyFlatVerdicts(modules) {
    Object.keys(FLAT_MODULE_KINDS).forEach(function (key) {
      var module = modules[key];
      if (!module || !Array.isArray(module.rows)) return;
      module.rows = module.rows.map(function (row) {
        return withFlatVerdict(row, FLAT_MODULE_KINDS[key]);
      });
    });
  }

  // ── 面板级「中特」口径（展示即候选）────────────────────────────────────
  // 【吉美丑凶】【③肖防③码】【前后中特】三个面板**不是平特玩法**：面板展示的就是本期
  // 押的生肖（或前/后肖分组），命中口径是「**特肖**落在展示候选里」（③肖防③码/三肖六码
  // 形态还含展示的码组，按特码比对）。它们的接口判定却是**另一种口径**：
  //   · 数据源 `pt3xiao`（平特3肖，mode 470）后端是七码平特口径 → 三个生肖里只要有一个
  //     以平码开出就判「对」：线上 274 期【吉美丑凶】「丑凶肖【牛蛇鼠】」开 24 羊仍显示
  //     「对」、273 期「吉美肖【鸡牛龙】」开 19 鼠仍显示「对」；【③肖防③码】同样
  //     （274 期「牛蛇鼠+…」开 24 羊显示「对」）。实测该口径下这两块 20 期里 19 期恒「对」。
  //   · 数据源 `qianhou_texiao`（前后特肖，mode 219）后端只比 `xiao` 那 2 肖 →
  //     面板展示的是「后肖」，开奖特肖是羊（∈ 后肖：马羊猴鸡狗猪）却判「错」（274 期）。
  // 供应商模板的对/错列就是本口径，且**逐个可复核**：
  //   吉美丑凶 323「【吉美】【马鸡龙】」开 12 马→对、320「【凶丑】【虎猴鼠】」开 34 猴→对、
  //   319「【凶丑】【鼠猴狗】」开 47 羊→错、322/321 开马/牛（不在三肖里）→错；
  //   前后中特 323/322/320/319「后肖」开 12/36/34/47 马马猴羊→对、321「后肖」开 41 牛→错。
  // 展示层复算的理由与 `tiandiJudgement` 相同：接口口径与展示候选不一致时，
  // 页面必须与**自己列出的候选**自洽。
  //
  // 前/后肖的分组**从行内容自己解析**（`["后肖|马,羊,猴,鸡,狗,猪"]`），
  // 不写死分组表；内容缺成员时退回面板图例（`QIANHOU_GROUP`，与 index.html 图例一致）。
  var QIANHOU_GROUP = {
    "前肖": ["鼠", "牛", "虎", "兔", "龙", "蛇"],
    "后肖": ["马", "羊", "猴", "鸡", "狗", "猪"],
  };

  /** 展示候选里的生肖（`牛` / `牛|06` 都算牛；非生肖 token 全部丢掉）。 */
  function displayedZodiacList(row, limit) {
    return zodiactsOf(row).filter(function (zodiac) {
      return ZODIAC_CHAR_SET[zodiac];
    }).slice(0, limit || 99);
  }

  /**
   * 展示候选里的号码（三肖六码 / ③肖防③码 的码组）。
   *
   * 与展示链路同口径：取 token 里的数字（`牛|06` → `06`）。**生肖名不产生号码** ——
   * 拿不到码组时 `pt3xiao` 会退化成 `牛蛇鼠+牛,蛇,鼠`，那时码组为空，
   * 判定只能靠生肖，绝不能把「牛」当成一个号码去比开奖号码。
   */
  function displayedNumberList(row, offset, limit) {
    return tokens(row).slice(offset || 0).map(function (value) {
      var digits = String(value).replace(/[^\d]/g, "");
      return digits && digits.length <= 2 ? digits.padStart(2, "0") : "";
    }).filter(Boolean).slice(0, limit || 99);
  }

  /** 开奖**特肖** / **特码**（`result.code` / `result.zodiac` 可能是七码串，末位才是特码）。 */
  function specialZodiacOf(row) {
    return resultToken(row && row.result && row.result.zodiac, false);
  }

  function specialCodeOf(row) {
    return resultToken(row && row.result && row.result.code, true);
  }

  /**
   * 「三肖 + N 码」面板的中特判定：特肖 ∈ 展示生肖，或特码 ∈ 展示号码。
   *
   * @param {object} row         判定所依据的行（拿开奖与生肖候选）
   * @param {number} zodiacLimit 展示的生肖个数（三肖面板 = 3）
   * @param {number} codeOffset  码组在 token 串里的起点（`三肖六码` = 3）
   * @param {number} codeLimit   码组个数（`三肖六码` = 6、`③肖防③码` = 3）
   * @returns {{correct: boolean, token: string}|null} null = 不做本地判定（沿用接口判定）
   */
  function zodiacPanelJudgement(row, zodiacLimit, codeOffset, codeLimit) {
    var result = row && row.result || {};
    if (!result.isOpened) return null;
    var zodiac = specialZodiacOf(row);
    var code = specialCodeOf(row);
    if (!zodiac && !code) return null;
    var zodiacs = displayedZodiacList(row, zodiacLimit);
    var codes = displayedNumberList(row, codeOffset, codeLimit);
    if (!zodiacs.length && !codes.length) return null;
    var zodiacHit = Boolean(zodiac) && zodiacs.indexOf(zodiac) !== -1;
    var codeHit = Boolean(code) && codes.indexOf(code) !== -1;
    return {
      correct: zodiacHit || codeHit,
      // 只点亮真正命中的那一项：命中生肖 → 点亮那个生肖；命中码组 → 点亮那个号码。
      token: zodiacHit ? zodiac : codeHit ? code : ""
    };
  }

  /** 【③肖防③码】：生肖来自三肖模块，码组来自码模块（拿不到号码时退化为生肖文本）。 */
  function sanxiaoFangSanmaJudgement(row, codeRow) {
    var result = row && row.result || {};
    if (!result.isOpened) return null;
    var zodiac = specialZodiacOf(row);
    var code = specialCodeOf(row);
    var zodiacs = displayedZodiacList(row, 3);
    var codes = displayedNumberList(codeRow || row, 0, 3);
    if ((!zodiacs.length && !codes.length) || (!zodiac && !code)) return null;
    var zodiacHit = Boolean(zodiac) && zodiacs.indexOf(zodiac) !== -1;
    var codeHit = Boolean(code) && codes.indexOf(code) !== -1;
    return {
      correct: zodiacHit || codeHit,
      token: zodiacHit ? zodiac : codeHit ? code : ""
    };
  }

  /** 行内容里的「前肖/后肖」分组（`["后肖|马,羊,猴,鸡,狗,猪"]` → 标签 + 6 肖）。 */
  function qianhouGroup(row) {
    var source = String(rawValue(row, "content") || displayLabels(row, "") || "")
      .replace(/[【】\[\]"]/g, "");
    var found = { label: "", members: [] };
    source.split(/[;；]/).forEach(function (piece) {
      var parts = String(piece).split("|");
      var name = String(parts[0] || "").trim();
      if (!QIANHOU_GROUP[name]) return;
      found = {
        label: name,
        members: String(parts[1] || "").split(/[,，、\s]+/).map(function (value) {
          return value.trim();
        }).filter(Boolean)
      };
    });
    return found;
  }

  /**
   * 【前后中特】的中特判定：特肖 ∈ 展示的「前肖 / 后肖」分组成员。
   *
   * 接口（mode 219）只比 `xiao` 那 2 肖，与本面板展示的分组不是一回事，必须本地复算。
   */
  function qianhouJudgement(row) {
    var result = row && row.result || {};
    var zodiac = specialZodiacOf(row);
    var group = qianhouGroup(row);
    var members = group.members.length ? group.members : QIANHOU_GROUP[group.label] || [];
    if (!result.isOpened || !zodiac || !members.length) return null;
    var hit = members.indexOf(zodiac) !== -1;
    // 展示的候选就是「前肖 / 后肖」这个分组名，命中时点亮分组名（与供应商模板一致）。
    return { correct: hit, token: hit ? group.label : "" };
  }

  // ── 标黄口径 ─────────────────────────────────────────────────────────
  // 规则：**只有预测命中的生肖 / 号码 / 波色 / 文字可以标黄，其余文字一律不标黄。**
  //
  // 命中型（HIT_RULES）：判定为「对」时，把候选里**真正被开出的那一项**标黄
  //   （不是整组候选都标）。
  // 绝杀/排除型（KILL_RULES）：**一律零黄底** —— 杀中（判定「对」）时开奖值本就不在
  //   被杀集合里，没有可高亮的命中项；杀失败（判定「错」）时开奖值正落在被杀集合里，
  //   但那属于 S3 明令禁止标黄的情形（判定「错」的整期必须零黄底）。
  //
  // S3 是硬门槛：**判定为「错」的那一期整期零黄底**，命中型也不能靠「值出现在候选串里」
  //   绕过本期判定 —— 候选串常常同时列出本期**没有**命中的另一组/另一个组合
  //   （红蓝绿肖两组、头数单双五个「N头X」组合、绝杀类被杀集合…），
  //   只按「值出现」标黄正是 twbst528 线上 5 处 R3 的根因。
  //
  // 依据：仓库《预测模块展示规范》S2/S3，与 twcf888 已确认的同口径实现。
  var HIT_RULE_KEYS = [
    "yijuzhenyan", "shuangbo", "shuangbo_12ma", "7xiao7ma", "pt2xiao", "pt1wei",
    "daxiao", "4xiao8ma", "pt1xiao", "title_5", "title_47", "pt3xiao", "danshuangtema",
    "3tou", "qinqi", "9xzt", "title_15", "title_74", "6xzt",
    "liuxiao18ma", "hllx", "9xiao12ma", "heibai3xiao", "title_48", "3zxt", "title_197",
    "dxztt1", "qianhou_texiao", "sihangzhongte", "siji3", "siduanzhongte", "wuzhong5ma",
    "daimingxiao", "liuweichute", "toudanshuang", "liuxiaoliuma", "gongshi_siw",
    "title_198", "title_14", "title_279", "title_66", "3hang", "title_132", "dujia_gongshi",
  ];
  // 绝杀/稳杀/输尽光全是排除型（后端 `excludes_hit`）：杀中才显示「对」，开奖值落在
  // 被杀集合里显示「错」。`juesha1wei`（绝杀一尾）原先被误列进命中型，本轮归位。
  var KILL_RULE_KEYS = [
    "juesha3xiao", "juesha1xiao", "juesha2xiao", "juesha1wei", "wensha10ma",
    "shaliangbanbo", "jueshabanbo", "shujinguang",
  ];
  var HIT_RULES = {};
  var KILL_RULES = {};
  HIT_RULE_KEYS.forEach(function (key) { HIT_RULES[key] = true; });
  KILL_RULE_KEYS.forEach(function (key) { KILL_RULES[key] = true; });

  function highlightRuleFor(moduleKey) {
    if (moduleKey && KILL_RULES[moduleKey]) return "kill";
    return "hit";
  }

  /**
   * `4头单` / `2尾双` 这类候选自带**单双后缀**，后缀必须与开奖号码的奇偶一致才算命中。
   *
   * 旧实现只比头/尾数字，于是同一个头数的**另一个组合**会被抢先标黄
   * （线上实测：开 42 = `4头双`，却把候选里排在前面的 `4头单` 标黄）。
   * 没有后缀的候选（`7尾` / `2头`）行为不变。
   */
  function parityHit(suffix, digits) {
    var flag = String(suffix || "").trim();
    if (!flag) return true;
    if (!digits) return false;
    var value = Number(digits);
    if (!isFinite(value)) return false;
    if (flag === "单") return value % 2 === 1;
    if (flag === "双") return value % 2 === 0;
    return true;
  }

  /** 接口的波色是 `red/blue/green`，而候选展示的是 `红波/蓝波/绿波`。 */
  var WAVE_LABELS = { red: "红波", blue: "蓝波", green: "绿波" };

  function drawnWave(row) {
    var raw = String(resultToken((row && row.result || {}).color, false) || "").toLowerCase();
    return WAVE_LABELS[raw] || "";
  }

  /**
   * 归一化候选标签，消除「展示加字 / 重复 / 单双后缀」造成的差异：
   *   `777尾` → `7尾`、`大数` → `大`、`4头单` → `4头`、`5尾` → `5尾`。
   */
  function normalizeCandidateLabel(value) {
    var label = String(value || "").replace(/[\[\]"'\s]/g, "");
    label = label.replace(/(.)\1+/g, "$1");
    if (label.length > 1 && /[头尾]$/.test(label)) {
      var body = label.slice(0, -1).replace(/[单双]$/, "");
      label = body + label.slice(-1);
    }
    return label;
  }

  /**
   * 候选所属的号码清单：候选 token 常写作 `5尾|05,15,25,35,45`、`大|25,…,49`、
   * `4头|40,…,49`。号码清单比展示文本更可靠 —— 展示文本会把分隔符换成 `-`
   * （`0-4-3-2头`）或把标签加字（`大` → `大数`、`7` → `777尾`），
   * 只按展示文本全等匹配会整块标不出黄底。
   */
  function candidateCodeList(row, candidate) {
    var want = normalizeCandidateLabel(candidate);
    if (!want) return [];
    var found = [];
    tokens(row).forEach(function (value) {
      var parts = String(value).replace(/[\[\]"]/g, "").split("|");
      if (parts.length < 2) return;
      if (normalizeCandidateLabel(parts[0]) !== want) return;
      parts.slice(1).join("|").split(/[,，\s]+/).forEach(function (item) {
        var code = String(item).trim();
        if (code) found.push(code);
      });
    });
    return found;
  }

  /** 大/小按号码区间；单/双只对纯单双候选判定（避免 `4头单` 被当成单双）。 */
  function semanticHit(candidate, digits) {
    var label = String(candidate || "").trim().replace(/[\s数肖]/g, "");
    if (!digits || label.length !== 1) return false;
    var value = Number(digits);
    if (label === "大") return value >= 25;
    if (label === "小") return value >= 1 && value <= 24;
    if (label === "单") return value % 2 === 1;
    if (label === "双") return value % 2 === 0;
    return false;
  }

  /** 该模块本期允许标黄的 token；不在此列表里的文字一律不标黄。 */
  function highlightTokens(row, rule, candidates) {
    if (!row || !row.result || !row.result.isOpened) return [];
    // S3：判定为「错」的那一期整期零黄底。开奖值出现在候选串里**不等于**本期命中
    // （候选串会同时列出本期没命中的另一组/另一个组合），所以判定「错」时
    // 无论命中型还是排除型都不给任何标记。
    if (row.result.isCorrect === false) return [];
    if (rule === "kill") {
      // 排除型没有「可高亮的命中项」：杀中（对）时开奖值本就不在被杀集合里，
      // 杀失败（错）已由上面的 S3 分支拦掉 —— 故排除型一律零黄底。
      return [];
    }
    // 命中型的候选是**候选集合**：开奖值落在集合里就是命中项。这里只用
    // `isCorrect === false` 做否定门槛，**不能**改成 `isCorrect !== true`
    // （部分模块该字段为空，例如 六肖十八码 / ⑤肖⑩码，以 true 为门槛会导致整块
    // 永远标不出黄底）。
    var code = resultToken(row.result.code, true);
    var zodiac = resultToken(row.result.zodiac, false);
    var wave = drawnWave(row);
    // 平特行（见 withFlatVerdict）：判定值已经按七个开奖号码重算过，标黄也要按整组开奖值比对。
    var flatDraw = row.flatDraw || null;
    var digits = String(code || "").replace(/\D/g, "");
    var tailDigit = digits ? digits.charAt(digits.length - 1) : "";
    // 一位数（如 09）的头数是 0，`0头` 必须能匹配上。
    var headDigit = digits ? (digits.length > 1 ? digits.charAt(0) : "0") : "";
    return (Array.isArray(candidates) ? candidates : []).map(String).filter(function (candidate) {
      if (!candidate) return false;
      // 只有真正被开出的那一项可以标黄，不能把整组候选都标上。
      if (code && candidate === code) return true;
      if (zodiac && candidate === zodiac) return true;
      if (wave && candidate === wave) return true;
      // 平特：命中项可能来自平码而不是特码，候选直接与七个开奖生肖 / 号码比对。
      if (flatDraw && flatDraw.zodiacs.indexOf(candidate) !== -1) return true;
      if (flatDraw && flatDraw.codes.indexOf(candidate) !== -1) return true;
      // 头/尾候选写作 `4头` / `4头单` / `7尾` / `2尾双`，
      // 与开奖号码的头数 / 尾数比较（候选里还带单双后缀，所以用正则取头尾数字，
      // 并让后缀参与判定，避免把同头数的另一个单双组合标黄）。
      var headMatch = /^(\d)\s*头([单双]?)/.exec(candidate);
      if (headMatch && headDigit && headMatch[1] === headDigit && parityHit(headMatch[2], digits)) return true;
      var tailMatch = /^(\d)\s*尾([单双]?)/.exec(candidate);
      if (tailMatch && tailDigit && tailMatch[1] === tailDigit && parityHit(tailMatch[2], digits)) return true;
      // `777尾` / `555尾`：模板把尾数重复了三次，取重复的数字再比尾数。
      var repeatTail = /^(\d)\1+\s*尾([单双]?)/.exec(candidate);
      if (repeatTail && tailDigit && repeatTail[1] === tailDigit && parityHit(repeatTail[2], digits)) return true;
      // 大/小、单/双 这类语义标签按号码区间 / 奇偶判定。
      if (semanticHit(candidate, digits)) return true;
      // `5尾|05,15,25,35,45`、`大|25,…,49` 直接用号码清单命中判定。
      if (code && candidateCodeList(row, candidate).indexOf(code) !== -1) return true;
      // 「一肖一码」「四肖四码」这类候选写作 `生肖|号码`，按生肖命中。
      return Boolean(zodiac) && candidate.split("|")[0].trim() === zodiac;
    });
  }

  /**
   * 从**已经格式化好的展示文本**里回推候选，避免二次猜测。
   *
   * 参数写法与内容声明（`红单|01,…` 的标签、`黑肖：` 这类分组说明）不是候选，
   * 必须排除，否则会把说明文字标黄。
   *
   * 注意：展示文本里生肖常常**连写**（`天肖+龙狗`、`猪鸡龙猴蛇鼠马狗`、`牛鸡`），
   * 如果只按分隔符切，会把 `龙狗` 当成一个候选，导致 `candidate === "狗"` 永远不成立、
   * 命中项标不出黄底。因此这里把「纯生肖串」再拆成单字。
   */
  var ZODIAC_CHARS = "鼠牛虎兔龙蛇马羊猴鸡狗猪";
  var ZODIAC_CHAR_SET = {};
  ZODIAC_CHARS.split("").forEach(function (char) { ZODIAC_CHAR_SET[char] = true; });

  function splitCandidateToken(item) {
    var token = String(item).split("|")[0].trim();
    if (!token) return [];
    if (token.length < 2) return [token];
    // 只有当整串都由生肖字组成时才拆成单字（`龙狗` → 龙、狗）；
    // 含数字/五行/艺名的候选（`4头单`、`土`、`琴棋书`）保持原样。
    var chars = token.split("");
    var allZodiac = chars.every(function (char) { return ZODIAC_CHAR_SET[char]; });
    return allZodiac ? chars : [token];
  }

  function allowMarkedTokens(text) {
    var source = String(text || "");
    var bracket = /【([^】]*)】/.exec(source);
    var scope = bracket ? bracket[1] : source;
    var parts = scope.replace(/[\[\]"]/g, "")
      .split(/[+＋,，、.\-–—/\s]+/)
      .map(function (item) { return item.split("|")[0].trim(); })
      .filter(function (item) { return Boolean(item) && !/[:：]/.test(item); });
    var out = [];
    parts.forEach(function (part) {
      splitCandidateToken(part).forEach(function (token) {
        if (token && out.indexOf(token) === -1) out.push(token);
      });
    });
    return out;
  }

  /**
   * 按标题找板块。**先精确匹配 `【标题】`**，再退回子串匹配。
   *
   * 为什么需要精确优先：面板标题都被包在 `【】` 里，而子串匹配会让短标题
   * 命中更长的标题 —— 例如 `sectionByTitle("大小")` 在「大小中特」排在
   * 「大小」之前时会先命中「大小中特」，把数据写进错误的板块。
   */
  function sectionByTitle(title) {
    var sections = Array.prototype.filter.call(window.document.querySelectorAll(".lxlm, .tzlb"), function (section) {
      var head = section.querySelector(".pb-tit");
      return head && /【[^】]*】/.test(String(head.textContent || ""));
    });
    var wanted = String(title || "");
    var exact = sections.filter(function (section) {
      var match = /【([^】]*)】/.exec(section.querySelector(".pb-tit").textContent);
      return match && match[1].trim() === wanted.trim();
    })[0];
    if (exact) return exact;
    return sections.filter(function (section) {
      return String(section.querySelector(".pb-tit").textContent || "").indexOf(wanted) !== -1;
    })[0] || null;
  }

  function rowsFor(section) {
    return Array.prototype.slice.call(section ? section.querySelectorAll("table.mtbl tbody > tr") : []).filter(function (row) {
      return row.querySelectorAll(":scope > td").length === 3;
    });
  }

  // Shared low-level writer for the identical three-column supplier topology.
  // Each public module below owns its selector and value formatter.
  //
  // `resultResolver(row)` 是**可选**的第六个钩子：接口的 `is_correct` 口径与展示口径
  // 不一致时（见 `tiandiJudgement`），由模块本地复算并返回一个带覆盖后 `result` 的行；
  // 返回假值时沿用原始行（`null` 行也原样透传）。既有调用方只传 ≤5 个参数，
  // 因此该钩子对它们是**完全无行为变化**的。
  function renderThreeColumnRows(section, module, formatter, moduleKey, hitResolver, resultResolver) {
    if (!section) return;
    var resolveRow = makeRowResolver(module);
    var rule = highlightRuleFor(moduleKey);
    var render = formatter || function (row) {
      return String(row.prediction.text || tokens(row).join(" ")).replace(/\|/g, " ");
    };
    rowsFor(section).forEach(function (tr, index) {
      var cells = tr.querySelectorAll(":scope > td");
      var row = resolveRow(cellText(cells[0]), index);
      var value = row ? render(row) : "暂无后端资料";
      var tokensToMark = row
        ? (hitResolver ? hitResolver(row, value) : highlightTokens(row, rule, allowMarkedTokens(value)))
        : [];
      writeCell(cells[0], row ? termValue(row) : "暂无后端资料");
      writeCell(cells[1], value, tokensToMark);
      writeResultCell(cells[2], resultResolver ? (resultResolver(row) || row) : row);
      tr.setAttribute("data-prediction-row", String(index));
    });
  }

  function renderYijuZhongpingHistory(module) {
    var section = sectionByTitle("一句中平特");
    if (section) section.setAttribute("data-prediction-section", "yijuzhenyan");
    renderThreeColumnRows(section, module, function (row) {
      return String(row.prediction.text || tokens(row).join(" ")).replace(/\|/g, " ");
    });
  }

  function renderLiangboTuweiHistory(module) {
    var section = sectionByTitle("两波突围");
    if (section) section.setAttribute("data-prediction-section", "shuangbo");
    renderThreeColumnRows(section, module, function (row) {
      return tokens(row).join("+");
    }, "shuangbo");
  }

  // 【八肖来袭】已按需求改名为【七肖来袭】：数据源仍是 mode 44（`7xiao7ma`），
  // 面板标题与站点真实玩法「七肖」对齐。候选是 `生肖|号码`，面板只显示生肖
  // （供应商模板同样是纯生肖串，号码不进正文）。
  function renderBaxiaoLaixiHistory(module) {
    var section = sectionByTitle("七肖来袭");
    if (section) section.setAttribute("data-prediction-section", "7xiao7ma");
    renderThreeColumnRows(section, module, function (row) {
      return zodiactsOf(row).join("");
    }, "7xiao7ma");
  }

  var DOMESTIC_WILD_LABELS = ["家禽", "野兽"];

  /**
   * 【家野中特】的分组正文：`家禽|猪,鸡,羊,马;野兽|猴,龙,鼠,兔` → 两组（各 4 肖）。
   *
   * tokens 的形态不稳定（组名可能单独成项，也可能用 `;` 粘在上一组最后一个生肖后面
   * —— `["家禽","猪","鸡","羊","马;野兽","猴",…]`），所以按「组名为界」逐项切分，
   * 两种形态都能还原出「组名 + 生肖串」。
   */
  function domesticWildGroups(row) {
    var groups = [];
    tokens(row).forEach(function (value) {
      String(value).replace(/[【】\[\]"]/g, "").split(/[|;；]/).forEach(function (piece) {
        var label = DOMESTIC_WILD_LABELS.filter(function (name) {
          return piece.indexOf(name) === 0;
        })[0];
        if (label) {
          groups.push({ label: label, values: [] });
          piece = piece.slice(label.length);
        }
        if (!groups.length) return;
        piece.replace(/[|,，、\s]/g, "").split("").forEach(function (char) {
          if (char) groups[groups.length - 1].values.push(char);
        });
      });
    });
    return groups.filter(function (group) { return group.label; });
  }

  // 「家野中特」：数据源换成站内已授权的 mode 14「家禽野兽」（`title_14`）。
  // 需求（2026-09-30）：显示【家禽】/【野兽】两组组名 + 各自生肖，不再只显示生肖串
  // （旧实现借「平特2肖」的两个生肖顶替，面板里只有 `兔+猴`，看不出家野分组）。
  // 判定沿用 mode 14 的接口口径（特肖 ∈ 家禽 4 肖 ∪ 野兽 4 肖），
  // 标黄只落在开出的那个特肖上。
  function renderJiayeZhongteHistory(module) {
    renderThreeColumnRows(sectionByTitle("家野中特"), module, function (row) {
      var groups = domesticWildGroups(row);
      if (!groups.length) return "";
      return groups.map(function (group) {
        return group.label + "：" + group.values.join("");
      }).join("+");
    }, "title_14", function (row, text) {
      if (!row || !row.result || row.result.isCorrect !== true) return [];
      var zodiac = resultToken(row.result.zodiac, false);
      return zodiac && text.indexOf(zodiac) !== -1 ? [zodiac] : [];
    });
  }

  function renderShaliangbanboHistory(module) {
    renderThreeColumnRows(sectionByTitle("杀两半波"), module, function (row) {
      return tokens(row).join("+");
    }, "shaliangbanbo");
  }

  function renderPingteYiweiHistory(module) {
    renderThreeColumnRows(sectionByTitle("平特一尾"), module, function (row) {
      var value = displayLabels(row, "").replace(/尾/g, "");
      return value ? value + value + value + "尾" : "";
    }, "pt1wei", function (row, text) {
      // 判定已由 applyFlatVerdicts 按**七个开奖号码**重算；命中时按模板口径只把尾数数字标黄
      // （`<span>222</span>尾`），「尾」字不标。
      if (!row || !row.result || row.result.isCorrect !== true || !text) return [];
      return [text.replace(/尾$/, "") || text];
    });
  }

  function renderDaxiaoZhongteHistory(module) {
    renderThreeColumnRows(sectionByTitle("大小中特"), module, function (row) {
      var value = String(rawValue(row, "daxiao") || displayLabels(row, "") || labelTokens(row)[0] || "");
      return value === "大" ? "大数" : value === "小" ? "小数" : value;
    });
  }

  // 「暴富⑦肖」：候选是 `生肖|号码`（`猪|08`），面板只展示生肖串。
  // 需求（2026-09-30）：去除号码展示，只保留生肖（供应商模板同样是纯生肖串）。
  function renderBaofuQixiaoHistory(module) {
    renderThreeColumnRows(sectionByTitle("暴富⑦肖"), module, function (row) {
      return zodiactsOf(row).join("");
    }, "7xiao7ma");
  }

  function renderHuobaoSitourHistory(module) {
    renderThreeColumnRows(sectionByTitle("火爆④头"), module, function (row) {
      return displayLabels(row, "-").replace(/头/g, "") + "头";
    });
  }

  // 「平特①肖」：供应商模板把单个生肖重复三次（牛牛牛/鸡鸡鸡），照原样保留三次。
  // 判定由 applyFlatVerdicts 统一按**七个开奖号码**重算（平特口径），不是只看特码。
  function renderPingteYixiaoHistory(module) {
    renderThreeColumnRows(sectionByTitle("平特①肖"), module, function (row) {
      var value = zodiactsOf(row)[0] || "";
      return value ? value + value + value : "";
    }, "pt1xiao", function (row, text) {
      // 命中时整段候选（三个重复生肖）一起标黄，与供应商模板的整段黄底一致。
      return row && row.result && row.result.isCorrect === true && text ? [text] : [];
    });
  }

  // ── 天地生肖固定分组（权威口径）────────────────────────────────────────
  // 来源：`public.fixed_data` sign='天地肖'，与 twwanli/twsyw/twcaibawang 各站的
  // `sx.html` 一致。天肖 6 肖 + 地肖 6 肖 = 12 生肖，不重不漏。
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

  /**
   * 天地两肖（mode 5 / `title_5`）的**本地**判定；返回 `null` = 「不做本地判定」。
   *
   * 为什么要本地复算：供应商/接口的 `is_correct` 只比对 mode 5 的 `xiao` 那 2 肖
   * （后端 `mechanisms.py` 里 `title_5` 的 `hit_checker=contains_hit`，候选就是
   * 「生肖选 2」），**天地组（6 肖）永远不参与判定** —— 于是「天肖里含开奖特肖」
   * 的期会显示「错」（270 期「天肖+兔鸡」开 37 马：马 ∈ 天肖，接口却给 false）。
   *
   * 正确口径（与 twwanli `#tdsx`、twsyw `#nannv`、twcaibawang 一致）：特肖落在
   * **天地组 ∪ 本期 2 个候选肖** 任一即命中。未开奖、拿不到特肖、或缺天地组/两肖
   * 资料时返回 `null`，沿用既有接口判定，不凭空造「错」。
   *
   * 天地组/两肖的两个来源（2026-09-30 起面板改绑 `title_5`）：
   *   · `title_5`（mode 5 天地生肖）：天地组写在**正文标签**里（`["地肖|蛇,羊,…"]`），
   *     两肖在 `xiao` 列；
   *   · `tiandi_2xiao`（供应商模块，本站 0 行）：组在 `tiandi` 列，两肖在 `xiao_pair` 列。
   */
  function tiandiJudgement(row) {
    var result = row && row.result || {};
    var zodiac = resultToken(result.zodiac, false);
    var picked = String(rawValue(row, "tiandi") || displayLabels(row, "") || "");
    var group = tiandiGroup(picked);
    var pair = valueList(rawValue(row, "xiao_pair"));
    if (!pair.length) pair = valueList(rawValue(row, "xiao"));
    if (!result.isOpened || !zodiac || !group.length || !pair.length) return null;
    var inGroup = group.indexOf(zodiac) >= 0;
    var inPair = pair.indexOf(zodiac) >= 0;
    return {
      correct: inGroup || inPair,
      // 只点亮真正命中的那一项：命中两肖 → 点亮那个生肖；命中天地组 → 点亮组名。
      // 两项都命中时优先点亮生肖（与 twwanli / twsyw 的 `inGroup && !inChosen` 分支一致）。
      token: inPair ? zodiac : inGroup ? picked : ""
    };
  }

  /** 复制一行并覆盖 `result.isCorrect`，把本地判定交给 `writeResultCell`（不改原 payload 行）。 */
  function withTiandiCorrect(row, correct) {
    if (!row) return null;
    var copy = {};
    Object.keys(row).forEach(function (key) { copy[key] = row[key]; });
    var result = {};
    Object.keys(row.result || {}).forEach(function (key) { result[key] = row.result[key]; });
    result.isCorrect = correct;
    copy.result = result;
    return copy;
  }

  /**
   * 【天地+②肖】= 天地组选 1 + 生肖选 2，绑定站内已授权的 mode 5「天地生肖」（`title_5`）。
   *
   * 2026-09-30 修正：此前该面板绑的是供应商模块 `tiandi_2xiao`（本站全站 0 行 → 面板只能
   * 隐藏），而 `title_5`（mode 5「天地生肖（天地选1，生肖选2）」）的正文就是
   * `["地肖|蛇,羊,鸡,狗,鼠,虎"]` + `xiao` 两肖 —— 与面板图例/样例（`天肖+狗鼠`）完全对应，
   * 且 web=10 有真实历史行。所以改绑 `title_5`：面板恢复显示，内容与判定都按天地口径。
   *
   * 判定由 `tiandiJudgement` 本地复算（特肖 ∈ 天地组 ∪ 两肖），不靠接口那套「只比两肖」的口径。
   */
  function renderTiandiErxiaoHistory(module) {
    renderThreeColumnRows(sectionByTitle("天地+②肖"), module, function (row) {
      var tiandi = String(rawValue(row, "tiandi") || "");
      var pair = rawValue(row, "xiao_pair");
      if (tiandi && Array.isArray(pair)) return tiandi + "+" + pair.join("");
      var labels = displayLabels(row, "");
      var picks = valueList(rawValue(row, "xiao")).slice(0, 2).join("");
      return labels && picks ? labels + "+" + picks : labels;
    }, null, function (row) {
      var judged = tiandiJudgement(row);
      return judged && judged.token ? [judged.token] : [];
    }, function (row) {
      var judged = tiandiJudgement(row);
      return judged ? withTiandiCorrect(row, judged.correct) : null;
    });
  }

  function renderPredictionImage(moduleKey, module) {
    var image = document.querySelector("img[data-prediction-image='" + moduleKey + "']");
    if (!image) return;
    var row = distinctRows(module)[0];
    var url = String(row && row.prediction && row.prediction.imageUrl || row && row.image_url || row && row.raw && row.raw.image_url || "").trim();
    if (!url) {
      image.setAttribute("src", "");
      image.setAttribute("hidden", "hidden");
      return;
    }
    image.setAttribute("src", url);
    image.removeAttribute("hidden");
  }

  function renderTaiwanPmtImage(module) {
    renderPredictionImage("tw_pmt_image", module);
  }

  // 第 5 项：【四肖中特】改名【胆大胆小】，展示“胆大”或“胆小”。
  function renderSizhongteHistory(module) {
    renderThreeColumnRows(sectionByTitle("胆大胆小"), module, function (row) {
      return groupLabelFor(row, DANXIAO_GROUP, "胆大");
    }, "title_47");
  }

  // 第 6 项：【三肖六码】改名【吉美丑凶】，展示“吉美肖”或“丑凶肖”+ 三个生肖（+ 有码组时第二行）。
  //
  // 判定：**中特口径**（`zodiacPanelJudgement`：特肖 ∈ 展示的三个生肖，或有码组时特码 ∈ 码组），
  // 与数据源模块 `pt3xiao`（平特3肖，mode 470）的七码平特口径**无关** —— 详见文件上方
  // 「面板级中特口径」的说明与供应商模板的对/错列。
  function renderSanxiaoLiumaHistory(module) {
    var section = sectionByTitle("吉美丑凶");
    if (!section) return;
    var resolveRow = makeRowResolver(module);
    rowsFor(section).forEach(function (tr, index) {
      var cells = tr.querySelectorAll(":scope > td");
      var row = resolveRow(cellText(cells[0]), index);
      var values = row ? tokens(row) : [];
      var zodiacs = row ? displayedZodiacList(row, 3) : [];
      // 第 6 项：显示「吉美肖【龙猪鼠】」/「丑凶肖【虎猪鼠】」；`三肖六码` 形态第二行是码组。
      var firstLine = row ? groupLabelFor(row, XIONGJI_GROUP, "") + "【" + zodiacs.join("") + "】" : "";
      var secondLine = values.slice(3, 9).join("-");
      var judged = row ? zodiacPanelJudgement(row, 3, 3, 6) : null;
      writeCell(cells[0], row ? termValue(row) : "暂无后端资料");
      // 候选格是 `.mtbl td:nth-child(2)`：必须先把模板预埋的黄底 span **拆包**（只清样式会
      // 留下空黄底 → 判定「错」的期次照样有黄底、R3），再按行写纯文本叶子，
      // 命中项用 inline 黄底 marker 单独标出（不新建宿主 span，见 `markTokenInLeaf`）。
      clearMarkers(cells[1], true);
      var groups = lineGroups(cells[1]);
      var hits = judged && judged.correct && judged.token ? [judged.token] : [];
      if (!row) {
        writePlainLine(groups[0], "暂无后端资料");
        writePlainLine(groups[1], "");
      } else {
        writePlainLine(groups[0], firstLine, hits);
        writePlainLine(groups[1], secondLine ? "【" + secondLine + "】" : "", secondLine ? hits : []);
      }
      writeResultCell(cells[2], judged ? withResultCorrect(row, judged.correct) : row);
      tr.setAttribute("data-prediction-row", String(index));
    });
  }

  // 「绝杀①肖 / 绝杀①波 / 绝杀一肖一尾」都是**排除型**：必须显式把模块键交给
  // highlightRuleFor，否则会退回默认的「命中型」口径 —— 判定为「错」（杀失败）时
  // 开奖值恰好等于候选，会被当成命中项标黄（线上 twbst528 `?|狗` 一处 R3 的根因）。
  //
  // 【绝杀①肖】内容显示按需求（2026-09-30）与【平特①肖】统一成「生肖重复三次」
  // （供应商模板里平特①肖就是 `牛牛牛` / `鸡鸡鸡` 的写法）；判定口径**不变**：
  // 用户明确要求绝杀①肖仍按最后一个开奖号码（特码）判定，不做七码复算。
  function renderJueshaYixiaoHistory(module) {
    renderThreeColumnRows(sectionByTitle("绝杀①肖"), module, function (row) {
      var values = tokens(row);
      var value = values.length ? String(values[0]).split("|")[0].trim() : "";
      return value ? value + value + value : "";
    }, "juesha1xiao");
  }

  function renderJueshaYiboHistory(module) {
    renderThreeColumnRows(sectionByTitle("绝杀①波"), module, function (row) { return tokens(row).join(""); }, "jueshabanbo");
  }

  function renderDanshuangErxiaoHistory(module) {
    renderThreeColumnRows(sectionByTitle("单双二肖"), module, function (row) { return displayLabels(row, "+"); });
  }

  function renderJueshaYixiaoYiweiHistory(module) {
    renderThreeColumnRows(sectionByTitle("绝杀一肖一尾"), module, function (row) { return tokens(row).join(""); }, "juesha1wei");
  }

  function renderRemainingThreeColumnHistory(title, module, formatter, moduleKey, hitResolver) {
    // `hitResolver(row, displayedText)` 允许模块自定义「展示文本里哪些片段可标黄」，
    // 例如【琴棋书画】展示的是艺名（琴棋书画）而不是生肖，需要把特肖映射成艺名再标黄。
    if (hitResolver) {
      renderThreeColumnRows(sectionByTitle(title), module, formatter, moduleKey, hitResolver);
      return;
    }
    renderThreeColumnRows(sectionByTitle(title), module, formatter, moduleKey);
  }

  // 「代号生肖」的候选是「生肖|代号」成对出现的（`狗|狗牙`），但单元格只显示代号本身
  // （狗牙）。命中项是**开奖特肖**，所以标黄必须按「代号 → 所属生肖」反查，
  // 否则 allowMarkedTokens 只会拿到代号串，`candidate === "狗"` 永不成立、整个板块 0 标记。
  function daimingPairName(value) {
    var parts = String(value || "").split("|");
    return (parts.length > 1 ? parts[1] : parts[0]).replace(/[\[\]"]/g, "").trim();
  }

  function daimingDrawnNames(row) {
    var zodiac = String(row && row.result && row.result.zodiac || "").trim();
    if (!zodiac) return [];
    return tokens(row).filter(function (value) {
      var parts = String(value || "").split("|");
      return parts.length > 1 && parts[0].replace(/[\[\]"]/g, "").trim() === zodiac;
    }).map(daimingPairName);
  }

  function renderDaimingXiaoHistory(module) {
    renderRemainingThreeColumnHistory("代号生肖", module, function (row) {
      return tokens(row).map(daimingPairName).join("、");
    }, "daimingxiao", function (row) {
      return daimingDrawnNames(row);
    });
  }

  function renderLiuweiChuteHistory(module) {
    renderRemainingThreeColumnHistory("六尾出特", module, function (row) {
      return predictionText(row, "-") + "尾";
    });
  }

  function renderToudanshuangHistory(module) {
    renderRemainingThreeColumnHistory("头数单双", module, function (row) {
      return tokens(row).join(".");
    });
  }

  function renderShuhaQiweiHistory(module) {
    renderRemainingThreeColumnHistory("梭哈⑦尾", module, function (row) {
      return displayLabels(row, "-").replace(/尾/g, "") + "尾";
    });
  }

  /**
   * 红蓝绿肖的命中项（标黄用）：开奖特肖落在该行声明的某个分类分组里 → 标黄该生肖。
   *
   * 为什么要专门给一个 resolver：候选写作 `蓝肖|蛇,虎,猪,猴`，通用 `allowMarkedTokens`
   * 按分隔符切分时会把**紧跟在标签后的第一个成员**（`蓝肖|蛇` → `蓝肖`）丢掉，
   * 于是命中项恰好是该分类首肖时整块标不出黄底（实测 188 期开 38 蛇、候选
   * `蓝肖|蛇,虎,猪,猴`，判定「对」却 0 黄底）。
   */
  function hllxHitZodiacs(row) {
    if (!row || !row.result || !row.result.isOpened || row.result.isCorrect !== true) return [];
    var zodiac = resultToken(row.result.zodiac, false);
    if (!zodiac) return [];
    var found = false;
    tokens(row).forEach(function (value) {
      var parts = String(value).replace(/[\[\]"]/g, "").split("|");
      if (parts.length < 2) return;
      var members = parts.slice(1).join("|").split(/[,，、\s]+/).map(function (item) {
        return item.trim();
      });
      if (members.indexOf(zodiac) !== -1) found = true;
    });
    return found ? [zodiac] : [];
  }

  function renderHongLanLvXiaoHistory(module) {
    renderRemainingThreeColumnHistory("红蓝绿肖", module, function (row) {
      return predictionText(row, " ");
    }, "hllx", function (row) {
      return hllxHitZodiacs(row);
    });
  }

  function renderWuxingLailiaoHistory(module) {
    renderRemainingThreeColumnHistory("五行来料", module, function (row) {
      return displayLabels(row, "-") + "行";
    });
  }

  function renderJueshaShimaHistory(module) {
    renderRemainingThreeColumnHistory("绝杀⑩码", module, function (row) {
      return predictionText(row, ".");
    }, "wensha10ma");
  }

  function renderHeibaiSanxiaoHistory(module) {
    renderRemainingThreeColumnHistory("黑白三肖", module, function (row) {
      var hei = valueList(rawValue(row, "hei"));
      var bai = valueList(rawValue(row, "bai"));
      if (hei.length || bai.length) return (hei.length ? "黑肖：" + hei.join("") : "") + (bai.length ? " 白肖：" + bai.join("") : "");
      return predictionText(row, "");
    });
  }

  function renderWenzhongDanshuangHistory(module) {
    renderRemainingThreeColumnHistory("稳中单双", module, function (row) {
      return displayLabels(row, "+");
    });
  }

  function renderSiduanzhongteHistory(module) {
    renderRemainingThreeColumnHistory("四段中特", module, function (row) {
      return tokens(row).map(function (value) {
        return String(value).split("|", 1)[0].replace(/段$/, "");
      }).filter(Boolean).join(".") + "段";
    });
  }

  /** 取 raw 字段里可能以 JSON 数组 / 逗号串形式存放的值，返回第一项。 */
  function firstRawItem(value) {
    if (Array.isArray(value)) return String(value[0] || "").trim();
    var text = String(value || "").trim();
    if (!text) return "";
    if (text.charAt(0) === "[") {
      try {
        var parsed = JSON.parse(text);
        if (Array.isArray(parsed) && parsed.length) return String(parsed[0] || "").trim();
      } catch (error) {
        var quoted = /"([^"]*)"/.exec(text);
        if (quoted) return quoted[1].trim();
      }
    }
    if (text.indexOf("|") !== -1) text = text.split("|", 2)[1];
    return text.split(/[,，]/)[0].trim();
  }

  function renderDaxiaoYitouHistory(module) {
    // 面板已由「大小+①头」改名为「大小」：`dxztt1` 本身只提供大小
    // （raw.content = `["大|45"]`），原来的「+①头」并没有对应的数据列，
    // 显示出来的是用预测号码推出来的头数，与标题承诺的「一个头」不是一回事。
    // 因此这里只显示「大数 / 小数」，与同类面板「大小中特」保持一致。
    renderRemainingThreeColumnHistory("大小", module, function (row) {
      var size = firstRawItem(rawValue(row, "daxiao")) || firstRawItem(rawValue(row, "content"));
      if (size.indexOf("|") !== -1) size = size.split("|", 2)[0].trim();
      size = size.replace(/^大$/, "大数").replace(/^小$/, "小数");
      if (size) return size;
      return displayLabels(row, "").replace(/^大$/, "大数").replace(/^小$/, "小数");
    });
  }

  /**
   * 【前后中特】：三列 = 期号 / 「前肖|后肖」/ 开奖与判定。
   *
   * 判定走**中特口径** `qianhouJudgement`（特肖 ∈ 展示分组的成员，成员从行内容解析），
   * 而不是 mode 219 接口那套「只比 `xiao` 两肖」的判定 —— 否则「后肖」里含开奖特肖
   * （274 期开 24 羊）也会显示「错」。命中时点亮分组名（供应商模板同样是黄底包住
   * 「后肖」两字）。
   */
  function renderQianhouZhongteHistory(module) {
    renderThreeColumnRows(sectionByTitle("前后中特"), module, function (row) {
      return displayLabels(row, "");
    }, "qianhou_texiao", function (row, text) {
      var judged = qianhouJudgement(row);
      return judged && judged.correct && judged.token ? [judged.token] : [];
    }, function (row) {
      var judged = qianhouJudgement(row);
      return judged ? withResultCorrect(row, judged.correct) : null;
    });
  }

  function renderQiweiSixingHistory(tailModule, lineModule) {
    var resolveTailRow = makeRowResolver(tailModule);
    var resolveLineRow = makeRowResolver(lineModule);
    var section = sectionByTitle("七尾四行");
    if (!section) return;
    rowsFor(section).forEach(function (tr, index) {
      var cells = tr.querySelectorAll(":scope > td");
      var templateText = cellText(cells[0]);
      var tailRow = resolveTailRow(templateText, index);
      var lineRow = resolveLineRow(templateText, index);
      writeCell(cells[0], tailRow ? termValue(tailRow) : "暂无后端资料");
      var tails = tailRow ? tokens(tailRow).map(function (value) {
        return String(value).replace(/尾.*/, "").replace(/\D/g, "");
      }).filter(Boolean).slice(0, 7) : [];
      var lines = lineRow ? tokens(lineRow).map(function (value) {
        return String(value).replace(/\|.*$/, "").replace(/[0-9,，.\s]/g, "");
      }).filter(Boolean).slice(0, 4) : [];
      writeCell(cells[1], tails.length && lines.length
        ? tails.join("") + "尾 + " + lines.join("") + "行"
        : "暂无后端资料");
      writeResultCell(cells[2], tailRow || lineRow);
    });
  }

  function renderSijiJiuxiaoHistory(seasonModule, zodiacModule) {
    var resolveSeasonRow = makeRowResolver(seasonModule);
    var resolveZodiacRow = makeRowResolver(zodiacModule);
    var section = sectionByTitle("四季九肖");
    if (!section) return;
    rowsFor(section).forEach(function (tr, index) {
      var cells = tr.querySelectorAll(":scope > td");
      var templateText = cellText(cells[0]);
      var seasonRow = resolveSeasonRow(templateText, index);
      var zodiacRow = resolveZodiacRow(templateText, index);
      writeCell(cells[0], seasonRow ? termValue(seasonRow) : "");
      writeCell(cells[1], seasonRow && zodiacRow
        ? displayLabels(seasonRow, "")
        : "暂无后端资料");
      writeResultCell(cells[2], seasonRow || zodiacRow);
    });
  }

  function cardRows(section) {
    return Array.prototype.filter.call(section ? section.querySelectorAll("table tbody > tr") : [], function (tr) {
      var header = tr.querySelector("td p b");
      return Boolean(header && /\d+期/.test(header.textContent || "") && /开/.test(header.textContent || ""));
    });
  }

  function writeCardHeader(cell, row) {
    var header = cell && cell.querySelector("p b");
    if (!header) return;
    var leaves = textNodes(header);
    var termLeaf = leaves.filter(function (leaf) { return /\d+期?/.test(String(leaf.nodeValue || "").trim()); })[0];
    if (termLeaf) termLeaf.nodeValue = row ? termValue(row).replace(/^第/, "") : "";
    var openIndex = leaves.findIndex(function (leaf) { return /开[:：]?|\?{2,}/.test(String(leaf.nodeValue || "").trim()); });
    if (openIndex < 0) return;
    var openLeaf = leaves[openIndex];
    var openText = String(openLeaf.nodeValue || "").trim();
    var resultText = row ? resultValue(row) : "开:暂无后端资料";
    if (/^开[:：]?$/.test(openText) && leaves[openIndex + 1]) {
      openLeaf.nodeValue = "开:";
      leaves[openIndex + 1].nodeValue = resultText.replace(/^开:/, "");
      leaves.slice(openIndex + 2).forEach(function (leaf) { leaf.nodeValue = ""; });
    } else {
      openLeaf.nodeValue = resultText.replace(/^开:/, "开");
      leaves.slice(openIndex + 1).forEach(function (leaf) { leaf.nodeValue = ""; });
    }
  }

  function splitCardLines(row, lineCount, separator) {
    var values = tokens(row);
    if (!values.length) return [String(row && row.prediction && row.prediction.text || "")];
    if (lineCount <= 1) return [values.join(separator || "")];
    var midpoint = Math.ceil(values.length / lineCount);
    var lines = [];
    for (var index = 0; index < lineCount; index += 1) {
      lines.push(values.slice(index * midpoint, (index + 1) * midpoint).join(separator || ""));
    }
    return lines;
  }

  function renderPairedCardHistory(title, module, formatter) {
    var section = sectionByTitle(title);
    if (!section) return;
    var resolveRow = makeRowResolver(module);
    cardRows(section).forEach(function (tr, index) {
      var cell = tr.querySelector("td");
      var header = cell && cell.querySelector("p b");
      var row = resolveRow(String(header && header.textContent || cellText(cell)), index);
      writeCardHeader(cell, row);
      var detail = cell && cell.querySelector(":scope > span");
      if (detail) {
        var groups = lineGroups(detail);
        if (row) {
          writeLineValues(detail, formatter(row));
        } else {
          // 没有后端行时必须把**每一行**都清掉再写占位：过去只写第一行，
          // 模板里烤死的样例号码会留在第二/第三行（实测「⑤肖⑩码」显示
          // 「暂无后端资料」后面还跟着 48.17.36… 的旧模板码）。
          groups.forEach(function (group) { writeLineGroup(group, "暂无后端资料"); });
        }
      }
      tr.setAttribute("data-prediction-row", String(index));
    });
  }

  // 第 3 项：六肖六码用 `-` 分隔生肖对，不要把文字挤在一起。
  function renderLiuxiaoLiumaHistory(module) {
    renderPairedCardHistory("六肖六码", module, function (row) {
      var xiao = valueList(rawValue(row, "xiao"));
      var code = valueList(rawValue(row, "code"));
      if (xiao.length === 6 && code.length === 6) {
        var pairs = xiao.map(function (label, index) {
          return label + String(code[index] || "").padStart(2, "0");
        });
        return [pairs.slice(0, 3).join("-"), pairs.slice(3, 6).join("-")];
      }
      return ["暂无后端资料"];
    });
  }

  function renderLiuxiaoShiermaHistory(module) {
    renderPairedCardHistory("⑥肖12码", module, function (row) {
      return splitCardLines(row, 2, ".");
    });
  }

  function renderShibamaHistory(module) {
    renderPairedCardHistory("18码中特", module, function (row) {
      return splitCardLines(row, 2, ".");
    });
  }

  // 第 3 项：③肖防③码 = 「三个生肖 + 三个防码」。候选是两个模块的行：
  // 生肖用 `+` 与码组分开，码之间用 `.` 分隔，避免 `虎猪鼠+虎,猪,鼠` 这种重复挤在一起的输出。
  //
  // 判定：**中特口径**（特肖 ∈ 展示的三个生肖，或有真号码时特码 ∈ 三个防码），
  // 与数据源模块 `pt3xiao`（平特3肖，mode 470）的七码平特口径无关 —— 详见文件上方
  // 「面板级中特口径」的说明与供应商模板的对/错列。
  // 注意：本站 `pt3xiao` 只有生肖、没有号码，所以码组会退化成生肖名（`牛蛇鼠+牛,蛇,鼠`），
  // 此时 `displayedNumberList` 拿不到号码，判定只按生肖。
  function renderSanxiaoFangSanmaHistory(zodiacModule, codeModule) {
    var resolveZodiacRow = makeRowResolver(zodiacModule);
    var resolveCodeRow = makeRowResolver(codeModule);
    var section = sectionByTitle("③肖防③码");
    cardRows(section).forEach(function (tr, index) {
      var cell = tr.querySelector("td");
      var header = cell && cell.querySelector("p b");
      var templateText = String(header && header.textContent || cellText(cell));
      var row = resolveZodiacRow(templateText, index);
      var codeRow = resolveCodeRow(templateText, index);
      // 判定必须走**中特口径**本地复算（`sanxiaoFangSanmaJudgement`），不能沿用
      // `pt3xiao` 的七码平特判定；拿不到开奖/候选时返回 null，沿用接口判定。
      var judged = row ? sanxiaoFangSanmaJudgement(row, codeRow) : null;
      var resultRow = row || codeRow;
      writeCardHeader(cell, judged ? withResultCorrect(resultRow, judged.correct) : resultRow);
      var detail = cell && cell.querySelector(":scope > span");
      if (!detail) return;
      if (!row) {
        writeLineValues(detail, ["暂无后端资料"]);
        return;
      }
      var zodiacs = displayedZodiacList(row, 3).join("");
      var codes = tokens(codeRow || {}).map(function (value) {
        var digits = String(value).replace(/[^\d]/g, "");
        return digits ? digits.padStart(2, "0") : "";
      }).filter(Boolean);
      // 码组取前三个有效号码；拿不到号码时退化为原有的 `生肖+号码` 文本。
      var codeText = codes.length ? codes.slice(0, 3).join(".") : predictionText(codeRow || row, ",");
      writeLineValues(
        detail,
        [zodiacs + "+" + codeText],
        judged && judged.correct && judged.token ? [judged.token] : []
      );
    });
  }

  // 第 3 项：8肖16码 / 六肖十八码 一类的正文是「N 个生肖 + 每肖 2~3 个号码」
  // （`raw.xiao` 与 `raw.code` 两列对齐）。展示成 `猪08.10鸡01.09鼠20.22`，
  // 即「生肖 + 该肖号码、组内用 `.`」；生肖之间靠号码尾巴自然分隔，不再挤成一团。
  function renderBaxiaoShiliumaHistory(module) {
    renderPairedCardHistory("8肖16码", module, function (row) {
      var groups = zodiacCodeGroups(row);
      if (!groups.length) return ["暂无后端资料"];
      var half = Math.ceil(groups.length / 2);
      return [groups.slice(0, half).join(""), groups.slice(half).join("")];
    });
  }

  /** 把 `raw.xiao` / `raw.code` 两列对齐成 `生肖` + 该肖号码（每肖 2~3 码）。 */
  function zodiacCodeGroups(row) {
    var xiao = valueList(rawValue(row, "xiao"));
    var code = valueList(rawValue(row, "code"));
    if (!xiao.length || !code.length) return [];
    var per = Math.max(1, Math.round(code.length / xiao.length));
    return xiao.map(function (label, index) {
      var codes = code.slice(index * per, (index + 1) * per).map(function (value) {
        var digits = String(value).replace(/\D/g, "");
        return digits ? digits.padStart(2, "0") : "";
      }).filter(Boolean);
      return codes.length ? label + codes.join(".") : label;
    });
  }

  function renderWuxiaoShimaHistory(module) {
    renderPairedCardHistory("⑤肖⑩码", module, function (row) {
      var groups = row && row.prediction && row.prediction.groups || [];
      var xiao = groups.filter(function (group) { return group.key === "xiao_5"; })[0];
      var code = groups.filter(function (group) { return group.key === "code_5"; })[0];
      if (xiao && code) return [xiao.tokens.join(""), code.tokens.join(".")];
      var values = tokens(row);
      var pairs = values.map(function (value) {
        var parts = String(value).replace(/[\[\]"]/g, "").split("|");
        return { xiao: String(parts[0] || "").trim(), codes: valueList(parts[1]) };
      }).filter(function (pair) { return pair.xiao; });
      var xiaos = pairs.map(function (pair) { return pair.xiao; }).slice(0, 5);
      var codes = pairs.reduce(function (all, pair) { return all.concat(pair.codes); }, []).slice(0, 10);
      return [xiaos.join(""), codes.join(".")];
    });
  }

  function renderSixiaoBamaHistory(module) {
    renderPairedCardHistory("四肖八码", module, function (row) {
      var values = tokens(row);
      return [values.slice(0, 4).join(""), values.slice(4, 12).join(".")];
    });
  }

  function writeInlineCardHeader(cell, row) {
    var directFonts = cell ? cell.querySelectorAll(":scope > font") : [];
    if (directFonts.length < 2) return;
    writeLeaf(directFonts[0], row ? termValue(row).replace(/^第|期$/g, "") : "");
    var headerLeaves = textNodes(directFonts[1]);
    var openIndex = headerLeaves.findIndex(function (leaf) { return /开[:：]?/.test(String(leaf.nodeValue || "")); });
    if (openIndex >= 0) {
      headerLeaves[openIndex].nodeValue = "开:";
      var resultLeaf = headerLeaves[openIndex + 1] || headerLeaves[openIndex];
      resultLeaf.nodeValue = row ? resultValue(row).replace(/^开:/, "") : "暂无后端资料";
      headerLeaves.slice(openIndex + 2).forEach(function (leaf) { leaf.nodeValue = ""; });
    }
  }

  function renderLiuxiaoShibamaHistory(module) {
    var section = sectionByTitle("六肖十八码");
    var resolveRow = makeRowResolver(module);
    Array.prototype.forEach.call(section ? section.querySelectorAll("table tbody > tr") : [], function (tr, index) {
      var cell = tr.querySelector("td");
      var header = cell && cell.querySelector("p b");
      var row = resolveRow(String(header && header.textContent || cellText(cell)), index);
      writeInlineCardHeader(cell, row);
      var directFonts = cell ? cell.querySelectorAll(":scope > font") : [];
      var xiao = row ? rawValue(row, "xiao") : null;
      var code = row ? rawValue(row, "code") : null;
      var lines = Array.isArray(xiao) && Array.isArray(code)
        ? [xiao.map(String).join(""), code.map(String).join(".")]
        : row ? splitCardLines(row, 2, ".") : ["暂无后端资料", ""];
      if (directFonts[2]) writeCell(directFonts[2], lines[0]);
      if (directFonts[3]) writeCell(directFonts[3], lines[1]);
    });
  }

  function renderYixiaoYimaHistory(module) {
    var section = sectionByTitle("一肖一码");
    var resolveRow = makeRowResolver(module);
    Array.prototype.forEach.call(section ? section.querySelectorAll("table.mtbl") : [], function (table, tableIndex) {
      var firstCell = table.querySelector("tbody > tr > td");
      var row = resolveRow(cellText(firstCell), tableIndex);
      var codes = valueList(rawValue(row, "code"));
      var xiaos = valueList(rawValue(row, "xiao"));
      Array.prototype.forEach.call(table.querySelectorAll("tbody > tr"), function (tr, stageIndex) {
        var cells = tr.querySelectorAll(":scope > td");
        if (cells.length !== 3) return;
        var source = stageIndex < 5 ? codes : xiaos;
        var size = [1, 3, 5, 7, 10, 1, 2, 3, 5, 7, 9][stageIndex] || 1;
        var bestValue = source.slice(0, size).join(stageIndex < 5 ? "." : "");
        writeCell(cells[0], row ? termValue(row) : "");
        writeCell(cells[1], row && bestValue ? bestValue : "暂无后端资料");
        writeResultCell(cells[2], row);
      });
    });
  }

  // 「码友来料参考」：每期一行，且必须给出开奖与判定
  // （用户要求：不要把不同期数挤在一起；每期显示「开xxx」和「对/错」）。
  function renderMayouLailiaoHistory(modules) {
    var section = sectionByTitle("码友来料参考");
    var moduleList = [
      { key: "3zxt", module: modules["3zxt"] || modules.sanxiaozhongte },
      { key: "title_47", module: modules.title_47 },
      { key: "6xzt", module: modules["6xzt"] }
    ];
    Array.prototype.forEach.call(section ? section.querySelectorAll("table tbody > tr td") : [], function (cell, cardIndex) {
      var entry = moduleEntryAt(moduleList, cardIndex);
      var resolveRow = makeRowResolver(entry && entry.module);
      var rule = highlightRuleFor(entry && entry.key);
      var groups = lineGroups(cell);
      var issueGroups = groups.filter(function (group) {
        return /\d+期/.test(group.map(function (leaf) { return leaf.nodeValue; }).join(""));
      });
      issueGroups.forEach(function (group, index) {
        var templateText = group.map(function (leaf) { return String(leaf.nodeValue || ""); }).join("");
        var row = resolveRow(templateText, index);
        if (!row) {
          writeLineGroup(group, "暂无后端资料");
          return;
        }
        var text = termValue(row).replace(/^第/, "") + "【" + predictionText(row, "") + "】" + resultValue(row);
        writeLineGroup(group, text, highlightTokens(row, rule, allowMarkedTokens(text)));
      });
    });
  }

  function renderForumHistory(modules) {
    var section = sectionByTitle("高手论坛");
    if (!section) return;
    var fallback = Object.keys(modules).reduce(function (latest, key) {
      var row = distinctRows(modules[key])[0];
      var rowIssue = Number(String(row && (row.issue || (row.year + row.term) || row.term) || "").replace(/\D/g, ""));
      var latestIssue = Number(String(latest && (latest.issue || (latest.year + latest.term) || latest.term) || "").replace(/\D/g, ""));
      return rowIssue > latestIssue ? row : latest;
    }, null);
    Array.prototype.forEach.call(section.querySelectorAll("li"), function (item) {
      var leaves = textNodes(item);
      var prefixLeaf = leaves.filter(function (leaf) { return /\d+期:/.test(String(leaf.nodeValue || "")); })[0];
      if (prefixLeaf && fallback) prefixLeaf.nodeValue = termValue(fallback).replace(/^第/, "") + ":" + activeLottery.titlePrefix;
    });
  }

  // 供应商的「三期计划」/「综合绝杀」面板里，每个玩法是面板内的一个「（玩法名）」小节。
  // moduleList 必须与小节**一一对应**：越界的小节（站点没有该玩法的授权模块）一律
  // 渲染成「暂无后端资料」，绝不允许回退到上一小节的数据，否则同一个小节序列会把同一个
  // 模块的行重复写多份（线上实测 twbst528「三期计划」的 271 期出现三条一模一样的行）。
  // `moduleList` 的每一项是 `{key, module}`：key 用来选标黄口径，module 提供行。
  function moduleEntryAt(moduleList, index) {
    return index >= 0 && index < moduleList.length ? moduleList[index] : null;
  }

  function renderCompositeLines(title, moduleList, formatter) {
    var section = sectionByTitle(title);
    var cell = section && section.querySelector("table tbody > tr td");
    if (!cell) return;
    var groups = lineGroups(cell);
    var moduleIndex = -1;
    var rowIndex = 0;
    groups.forEach(function (group) {
      var current = group.map(function (leaf) { return String(leaf.nodeValue || ""); }).join("").trim();
      if (/^[（(].+[）)]$/.test(current) || (!/\d+期/.test(current) && /【.+】/.test(current))) {
        moduleIndex += 1;
        rowIndex = 0;
        return;
      }
      if (!/\d+(?:-\d+)?期/.test(current)) return;
      var entry = moduleEntryAt(moduleList, moduleIndex);
      if (!entry) return;   // 越界小节不渲染任何东西（不回退到上一小节的数据）
      var row = makeRowResolver(entry.module)(current, rowIndex);
      if (!row) {
        // 模板里多出来的静态样例期号（如 233期）必须清掉，避免与真实期号挤在一起。
        writeLineGroup(group, "");
        return;
      }
      var text = formatter(row, moduleIndex, entry);
      // 标黄口径按**小节**决定：`entry.rule` 显式指定时优先（`{key:"3tou", rule:"kill"}`
      // 这类「面板内按排除型重做」的小节），否则沿用按 key 查规则表的老口径。
      writeLineGroup(group, text, highlightTokens(row, entry.rule || highlightRuleFor(entry.key), allowMarkedTokens(text)));
      rowIndex += 1;
    });
  }

  /** 「独家公式」单行展示值：`单` → `单数`；`["5","2","1","3"]` → `5213尾`。 */
  function dujiaGongshiValue(kind, labels) {
    if (kind === "tails") return compactLabels(labels, "") + "尾";
    var first = String(labels[0] || "").replace(/[\[\]"]/g, "");
    return first.split("|", 1)[0].trim() + "数";
  }

  /** 「开：20-19-38-35-23-42-45狗」：完整开奖串（前六平码 + 末位特码 + 特肖，全部用 `-` 连接）。 */
  function drawnSummary(row) {
    var codes = fullDrawnCodes(row);
    var zodiac = resultToken(row && row.result && row.result.zodiac, false);
    if (codes.length > 1) return codes.join("-") + zodiac;
    var single = resultToken(row && row.result && row.result.code, true);
    if (single) return single + zodiac;
    return String(row && row.result && row.result.text || "").replace(/^开[:：]?/, "");
  }

  /** 维度命中时要标黄的那一段（`markLineHit` 只在 `【…】` 范围内找，不会污染开奖号码）。 */
  function dujiaGongshiHitTokens(kind, row, value) {
    if (!value) return [];
    if (kind === "tails") {
      var tail = String(resultToken(row.result.code, true)).replace(/\D/g, "").slice(-1);
      return tail && value.indexOf(tail) !== -1 ? [tail] : [];
    }
    return [value];
  }

  /**
   * 【独家公式】：三个小节（独家单双 / 独家大小 / 公式四尾），每节 6 期。
   *
   * 需求（2026-09-30）：
   *   · 去掉无意义的 `T37`（`T` 只是模板占位字母，号码本身就是开奖特码）；
   *   · 删掉模板烤死的「整体准确率：96.96%。参弃随意」；
   *   · 每行补「开：xx」并统一排版：`第190期 开：20-19-38-35-23-42-45狗 【5213尾】√`。
   *
   * 判定取 `raw.formula[kind].is_correct`：这个供应商模块行的 `result.isCorrect` 恒为
   * null（每个维度各自判定），所以 √/x 必须用维度判定，否则命中期也会显示成 `x`。
   * 标黄只落在维度值上（`单数` / `大数` / 命中的那个尾数数字），与供应商模板一致。
   */
  function renderDujiaGongshiHistory(module) {
    var section = sectionByTitle("独家公式");
    if (!section) return;
    var resolveRow = makeRowResolver(module);
    var blocks = Array.prototype.slice.call(section.querySelectorAll("td > p > b > font[face]")).filter(function (font) {
      return String(font.textContent || "").indexOf("独家") >= 0 || String(font.textContent || "").indexOf("公式四尾") >= 0;
    });
    ["parity", "size", "tails"].forEach(function (kind, blockIndex) {
      var block = blocks[blockIndex];
      if (!block) return;
      var rowIndex = 0;
      lineGroups(block).forEach(function (group) {
        var templateText = group.map(function (leaf) { return String(leaf.nodeValue || ""); }).join("");
        // 模板烤死的整行说明文字（每个小节末尾一条）不是数据行，必须清空。
        if (/整体准确率|参弃随意/.test(templateText)) {
          writeLineGroup(group, "");
          return;
        }
        if (!/\d+(?:-\d+)?\s*期/.test(templateText)) return;
        var row = resolveRow(templateText, rowIndex);
        rowIndex += 1;
        if (!row) {
          writeLineGroup(group, "暂无后端资料");
          return;
        }
        var formula = rawValue(row, "formula") || {};
        var entry = formula[kind] || {};
        var labels = Array.isArray(entry.labels) ? entry.labels : [];
        var value = labels.length ? dujiaGongshiValue(kind, labels) : "";
        var opened = Boolean(row.result && row.result.isOpened);
        var marker = !opened ? "?" : entry.is_correct === true ? "√" : "x";
        var line = termValue(row) + " 开：" + (opened ? drawnSummary(row) : "待开奖") +
          (value ? " 【" + value + "】" : "") + marker;
        writeLineGroup(group, line, opened && entry.is_correct === true
          ? dujiaGongshiHitTokens(kind, row, value)
          : []);
      });
    });
  }

  function renderSanqiJihuaHistory(modules) {
    // 面板小节顺序：一波中特 / 单双计划 / 平特计划 / 3.肖中特 / 必出3码 / 平尾计划。
    // 「必出3码」站点没有授权任何 3 码玩法，用 null 占位（渲染「暂无后端资料」），
    // 不能省掉这一位——省掉会让「平尾计划」错位拿到「3.肖中特」的数据。
    renderCompositeLines("三期计划", [
      { key: "shuangbo", module: modules.shuangbo },
      { key: "danshuangtema", module: modules.danshuangtema },
      { key: "pt1xiao", module: modules.pt1xiao },
      { key: "3zxt", module: modules["3zxt"] || modules.sanxiaozhongte },
      { key: null, module: null },
      { key: "pt1wei", module: modules.pt1wei }
    ], function (row) {
      return termValue(row).replace(/^第/, "") + "【" + displayLabels(row, "") + "】" + resultValue(row);
    });
  }

  function renderZongheJueshaHistory(modules) {
    // 「综合绝杀」面板：四个小节统一按排除型（杀号）口径展示与判定。
    // 口径依据（backend/docs/prediction-module-rules.md）：
    //   · juesha2xiao(mode 473) / juesha1wei(mode 20) 后端本身就是 excludes_hit：
    //     杀掉的集合里没有开奖目标 → is_correct=true → 「对」。接口判定直接用，不取反。
    //   · 3tou(3头中特 mode 12) / 3hang(3行中特 mode 53) 后端是命中型
    //     （特码头 / 特码五行落入候选 → is_correct=true），而本面板把它们作为「稳杀」
    //     展示（文案是 NNN期稳杀【…】）。按面板口径必须取反：
    //     被杀集合不含开奖目标（特码头 / 特码五行）→ 「对」，含 → 「错」。
    // 取反只做在展示层（invertVerdict + resultValue(row, true)）：后端 is_correct
    // 是 mode 12/53 的公共语义，还被别的面板/站点使用（本站「五行来料」面板就把 3hang
    // 当命中型渲染），不能为这个面板改后端。
    // 高亮：排除型一律零黄底 ——「对」= 没有可高亮的命中项；「错」= 开奖目标正落在被杀的
    // 集合里，属于 S3 明令禁止标黄的情形。故这两个小节显式传 rule:"kill"，而不能把
    // 3tou/3hang 加进全局 KILL_RULE_KEYS（那会连带改掉「五行来料」等命中型面板的口径）。
    //
    // 判定取值：`killedSetContainsTarget()` 按**本行候选自己声明的号码清单**
    // （`土|05,06,…` / `3头|30,…`）复算「开奖号码 ∈ 被杀集合」，与面板上列出的候选完全
    // 自洽；清单缺失时才退回接口 `is_correct` 再取反。五行正文口径已统一到
    // `fixed_data` sign='五行'（号码五行，37→木），与后端 outcome 同一套划分，
    // 两个来源的结果一致（见 `killedSetContainsTarget` 注释）。
    renderCompositeLines("综合绝杀", [
      { key: "juesha2xiao", module: modules.juesha2xiao },
      { key: "juesha1wei", module: modules.juesha1wei },
      { key: "3tou", module: modules["3tou"], rule: "kill", invertVerdict: true },
      { key: "3hang", module: modules["3hang"], rule: "kill", invertVerdict: true }
    ], function (row, moduleIndex, entry) {
      // 排除型小节：先按**本行候选清单**复算「开奖目标是否落在被杀集合里」
      // （命中型语义），拿不到清单时退回接口判定；两者都再取反成排除型判定。
      var invert = Boolean(entry && entry.invertVerdict);
      var hitInKillSet = invert ? killedSetContainsTarget(row) : null;
      var judged = hitInKillSet === null ? row : withResultCorrect(row, hitInKillSet);
      return termValue(row).replace(/^第/, "") + "稳杀【" + displayLabels(row, "") + "】" +
        resultValue(judged, invert);
    });
  }

  function waveGroups(row) {
    return Array.isArray(row && row.prediction && row.prediction.groups) ? row.prediction.groups.filter(function (group) {
      return Array.isArray(group.tokens) && group.tokens.length;
    }) : [];
  }

  function writeWaveNumbers(line, group, row) {
    var lineLeaves = textNodes(line);
    var labelNode = lineLeaves[0];
    var numberLeaves = lineLeaves.slice(1);
    var values = group ? group.tokens.map(String) : [];
    clearMarkers(line);
    if (labelNode) labelNode.nodeValue = (group && group.label ? group.label : "波色") + ":";
    numberLeaves.forEach(function (leaf, index) {
      leaf.nodeValue = values[index] ? (index ? "." : "") + values[index] : "";
    });
    var code = String(row && row.result && row.result.code || "").padStart(2, "0");
    if (row && row.result && row.result.isCorrect === true && values.indexOf(code) !== -1) {
      var matching = numberLeaves.filter(function (leaf) { return leaf.nodeValue.indexOf(code) !== -1; })[0];
      var marker = matching && matching.parentElement && matching.parentElement.closest("span[style*='background-color']");
      if (marker) marker.style.backgroundColor = "#FFFF00";
    }
  }

  function renderDoubleWaveHistory(module) {
    var section = sectionByTitle("双波⑩码");
    if (!section) return;
    section.setAttribute("data-prediction-section", "shuangbo_12ma");
    var resolveRow = makeRowResolver(module);
    Array.prototype.forEach.call(section.querySelectorAll("table tbody > tr"), function (tr, index) {
      var headerFonts = tr.querySelectorAll("td p b > font");
      var templateText = String(headerFonts[0] && headerFonts[0].textContent || cellText(tr));
      var row = resolveRow(templateText, index);
      if (headerFonts.length >= 3) {
        writeLeaf(headerFonts[0], row ? termValue(row) : "暂无后端资料");
        writeLeaf(headerFonts[1], "【双波⑩码】");
        writeCell(headerFonts[2], row ? resultValue(row) : "暂无后端资料");
      }
      var lines = tr.querySelectorAll("td > span font[color='red'], td > span font[color='blue'], td > span font[color='green']");
      var groups = waveGroups(row);
      Array.prototype.forEach.call(lines, function (line, lineIndex) {
        writeWaveNumbers(line, groups[lineIndex], row);
      });
      tr.setAttribute("data-prediction-row", String(index));
    });
  }

  function renderPredictionTitle(section) {
    var title = section.querySelector(".pb-tit");
    if (!title || !/台湾百事通|澳门百事通|香港百事通/.test(title.textContent || "")) return;
    var leaf = textNodes(title)[0];
    if (leaf) leaf.nodeValue = String(leaf.nodeValue).replace(/(?:台湾|澳门|香港)百事通/g, activeLottery.titlePrefix);
  }

  function renderPredictions(result) {
    var modules = modulesFrom(result);
    // 平特类模块（pt1xiao / pt1wei / pt2xiao）先把判定统一改成**七码口径**；
    // 之后所有用到这些模块的**平特面板**（平特①肖 / 平特一尾 / 三期计划的平特·平尾计划）
    // 拿到的都是同一套判定，不必各写一份。
    // `pt3xiao`（平特3肖）不在其中：本站首页没有平特③肖面板，它只作为【吉美丑凶】
    // 【③肖防③码】的数据源，这两个面板走各自的中特口径（`zodiacPanelJudgement`）。
    applyFlatVerdicts(modules);
    // 没有后端数据的板块（天地+②肖 / 18码中特）整块隐藏，不留「暂无后端资料」空壳。
    hideUnbackedPanels(modules);
    Array.prototype.forEach.call(window.document.querySelectorAll(".lxlm, .tzlb"), renderPredictionTitle);
    renderYijuZhongpingHistory(modules.yijuzhenyan);
    renderLiangboTuweiHistory(modules.shuangbo);
    renderBaxiaoLaixiHistory(modules["7xiao7ma"]);
    renderJiayeZhongteHistory(modules.title_14);
    renderShaliangbanboHistory(modules.shaliangbanbo);
    renderPingteYiweiHistory(modules.pt1wei);
    renderDaxiaoZhongteHistory(modules.daxiao);
    renderBaofuQixiaoHistory(modules["7xiao7ma"]);
    renderHuobaoSitourHistory(modules.sitouzhongte);
    renderPingteYixiaoHistory(modules.pt1xiao);
    renderTiandiErxiaoHistory(modules.title_5);

    renderTaiwanPmtImage(modules.tw_pmt_image);
    renderPredictionImage("sxztu", modules.sxztu);
    renderPredictionImage("pmtj_image", modules.pmtj_image);
    renderSizhongteHistory(modules.title_47);
    renderSanxiaoLiumaHistory(modules.pt3xiao);
    renderJueshaYixiaoHistory(modules.juesha1xiao);
    renderJueshaYiboHistory(modules.jueshabanbo);
    renderDanshuangErxiaoHistory(modules.danshuangtema);
    renderJueshaYixiaoYiweiHistory(modules.juesha1wei);
    renderRemainingThreeColumnHistory("杀肖杀码", modules.juesha3xiao, null, "juesha3xiao");
    renderToudanshuangHistory(modules.toudanshuang);
    // 第 4 项：【琴棋书画】显示四艺中的三种（如「书棋琴」），而不是直接显示生肖；
    // 标黄也改成「开奖特肖所属的艺」。
    renderRemainingThreeColumnHistory("琴棋书画", modules.qinqi, function (row) {
      return siyiTriple(row);
    }, "qinqi", function (row) {
      return siyiHitArts(row);
    });
    renderRemainingThreeColumnHistory("本期输尽光", modules.shujinguang, null, "shujinguang");
    renderForumHistory(modules);
    renderDaimingXiaoHistory(modules.daimingxiao);
    renderDujiaGongshiHistory(modules.dujia_gongshi);
    renderLiuweiChuteHistory(modules.liuweichute);
    renderLiuxiaoLiumaHistory(modules.liuxiaoliuma);
    // 不给跨模块兜底：`public_yixiao_yima` 缺失时应显示「暂无后端资料」，
    // 过去兜到 `9xiao12ma` 会把「9肖12码」的 12 个号码画进「一肖一码」面板（实测 11 行/期）。
    renderYixiaoYimaHistory(modules.public_yixiao_yima);
    renderMayouLailiaoHistory(modules);
    renderShuhaQiweiHistory(modules.title_74);
    renderLiuxiaoShibamaHistory(modules.liuxiao18ma);
    renderSiduanzhongteHistory(modules.siduanzhongte);
    renderHongLanLvXiaoHistory(modules.hllx);
    renderWuxingLailiaoHistory(modules["3hang"]);
    renderJueshaShimaHistory(modules.wensha10ma);
    renderLiuxiaoShiermaHistory(modules["9xiao12ma"]);
    renderHeibaiSanxiaoHistory(moduleWithRows(modules.heibai3xiao, modules.title_45));
    // 【阴阳⑧码中特】本站没有对应数据：面板图例要求「阴肖/阳肖 + 4 肖 + 8 码」，
    // 而站内唯一沾边的 `title_48` 是「8肖中特」（8 个生肖、无阴阳分组），画上去就是
    // 「图例与内容不符」。按「无数据 → 不借别的模块」处理，板块在 hideEmptyPanels() 里整块隐藏。
    // 18码中特 在 site_module_blueprints 里是 blocked_requires_backend_work：
    // 后端没有确认 mechanism/mode_id，所以不能拿六肖十八码的数据顶上。
    // 该板块在 hideEmptyPanels() 里整块隐藏（保留 DOM 与这条「必须空态」的渲染路径，
    // 防止将来有人把别的模块接进来）。
    renderShibamaHistory(null);
    renderSanxiaoFangSanmaHistory(modules.pt3xiao, modules.pt3xiao);
    // site_page_dependencies 把「8肖16码」面板绑到 mode_id 60 = `9xiao12ma`
    // （不是 `liuxiao18ma`；后者属于「六肖十八码」面板，复用会让两个面板显示同一组 18 码）。
    renderBaxiaoShiliumaHistory(modules["9xiao12ma"]);
    renderSanqiJihuaHistory(modules);
    renderWuxiaoShimaHistory(modules.wuxiao_wuma);
    renderWenzhongDanshuangHistory(modules.danshuangtema);
    renderZongheJueshaHistory(modules);
    renderDaxiaoYitouHistory(modules.dxztt1);
    renderSixiaoBamaHistory(modules["4xiao8ma"]);
    // 【日夜特肖】/【左右中特】本站没有「日夜肖 / 左右肖」数据（`created.mode_payload_164`
    // 全站 0 行、`created.mode_payload_152` 只有 web 1/4/6/7/8），过去分别借
    // `qianhou_texiao`（前后肖）与 `title_5`（天地肖）顶上 → 面板图例是日/夜、左/右，
    // 内容却是前/后、天/地。现按「无数据 → 不借别的模块」处理：两个板块在
    // hideEmptyPanels() 里整块隐藏（保留 DOM，后端补数据后可还原映射）。
    // 【前后中特】的 `qianhou_texiao` 本身就是「前后特肖」：模块键保持不变，
    // 但判定改由 `qianhouJudgement` 本地复算（特肖 ∈ 展示分组），不沿用接口的两肖口径。
    renderQianhouZhongteHistory(modules.qianhou_texiao);
    renderQiweiSixingHistory(modules.title_74, modules.sihangzhongte);
    renderSijiJiuxiaoHistory(modules.siji3, modules.siji3);
    renderDoubleWaveHistory(modules.shuangbo_12ma);
  }

  function activateDrawPanel(item) {
    // Re-dispatch to the supplier KJTB handler so it owns iframe creation and
    // the supplied tab/panel DOM remains the only draw UI.
    if (item && !item.classList.contains("cur")) item.click();
  }

  function selectLottery(type) {
    activeLottery = lotteryForType(type);
    var selectedType = activeLottery.lotteryType;
    var draw = client.loadDraw({ lotteryType: selectedType }).then(function (result) {
      return announce("draw", result);
    });
    var predictions;
    if (historyByLottery[selectedType]) {
      predictions = Promise.resolve(historyByLottery[selectedType]);
    } else if (historyRequests[selectedType]) {
      predictions = historyRequests[selectedType];
    } else {
      predictions = client.loadPredictions({
        lotteryType: selectedType,
        historyLimit: HISTORY_LIMIT,
        // 必须带上 includeVendor：共享数据客户端在缺这个标记时会强制 include_vendor=0，
        // 于是「独家公式 / 一肖一码 / 本期输尽光 / 双波⑩码 / ⑤肖⑩码 / 天地+②肖」
        // 这些**供应商模块**根本不会返回，面板只能显示「暂无后端资料」或模板旧数据。
        includeVendor: true
      }).then(function (result) {
        historyByLottery[selectedType] = result;
        return result;
      });
      historyRequests[selectedType] = predictions;
    }
    predictions.then(function (result) {
      if (activeLottery.lotteryType === selectedType) renderPredictions(result);
      announce("predictions", result);
    });
    return Promise.all([draw, predictions]);
  }

  // ── 无数据支撑板块：整块隐藏 ──────────────────────────────────────────
  // 两类：
  //   1) 静态（EMPTY_PANEL_TITLES）：payload 里**恒定**没有任何数据的模块 ——
  //      public_yixiao_yima（公开一肖一码）/ wuxiao_wuma（五肖五码）都依赖 mode 151，全表 0 行；
  //      18码中特 在 `site_module_blueprints` 里是 `blocked_requires_backend_work`
  //      （后端 mechanism/mode_id 都没确认，连模块都没有）；
  //      日夜特肖 / 左右中特 / 阴阳⑧码中特（2026-09-30 追加）在本站没有对应分类数据
  //      （`created.mode_payload_164` 全站 0 行；`created.mode_payload_152` 只有
  //      web 1/4/6/7/8；阴阳肖也没有 web=10 的生成行），过去是借别的模块顶上的，
  //      现在不再借 —— 板块整块隐藏，避免「图例是日/夜、内容是前/后」这类错位。
  //   2) 动态（UNBACKED_PANELS）：按 payload 行数判断 —— 【天地+②肖】绑 `title_5`
  //      （mode 5 天地生肖），有行就渲染、没行就隐藏，不做永久删除。
  // 都按「有壳无数据 → 删」处理；保留 DOM 与后端引用，便于数据源补齐后还原。
  var EMPTY_PANEL_TITLES = ["一肖一码", "⑤肖⑩码", "18码中特", "日夜特肖", "左右中特", "阴阳⑧码中特"];
  var UNBACKED_PANELS = [
    { title: "天地+②肖", moduleKey: "title_5" },
  ];

  function hidePanel(section, name) {
    if (!section) return false;
    section.setAttribute("data-prediction-empty", name);
    section.hidden = true;
    // 供应商样式表可能给 .lxlm/.tzlb 设了带 !important 的 display，
    // 内联 display:none 会被压过去，所以用 setProperty(..., "important")。
    section.style.setProperty("display", "none", "important");
    return true;
  }

  function sectionTitle(section) {
    var head = section && section.querySelector(".pb-tit");
    return String(head && head.textContent || "");
  }

  function hideEmptyPanels() {
    Array.prototype.forEach.call(window.document.querySelectorAll(".lxlm, .tzlb"), function (section) {
      var title = sectionTitle(section);
      var matched = EMPTY_PANEL_TITLES.filter(function (name) { return title.indexOf(name) !== -1; })[0];
      if (matched) hidePanel(section, matched);
    });
  }

  /** 模块缺行（或缺模块）的板块整块隐藏；有数据时保持原样。 */
  function hideUnbackedPanels(modules) {
    UNBACKED_PANELS.forEach(function (panel) {
      if (panel.moduleKey && distinctRows(modules[panel.moduleKey]).length) return;
      hidePanel(sectionByTitle(panel.title), panel.title);
    });
  }

  function bindLotteryTabs() {
    Array.prototype.forEach.call(window.document.querySelectorAll(".KJ-TabBox li"), function (item) {
      item.addEventListener("click", function (event) {
        var anchor = event.target && event.target.closest && event.target.closest("a[data-lottery-type]");
        if (!anchor) return;
        event.preventDefault();
        activateDrawPanel(item);
        selectLottery(Number(anchor.getAttribute("data-lottery-type")));
      });
    });
  }

  window.Twbst528SiteData = { selectLottery: selectLottery };
  window.addEventListener("DOMContentLoaded", function () {
    // 先隐藏有壳无数据（静态已知）的板块，再渲染其余板块；
    // 需要看 payload 行数的板块（天地+②肖）在 renderPredictions 里隐藏。
    hideEmptyPanels();
    bindLotteryTabs();
    selectLottery(activeLottery.lotteryType);
  });
})(window);
