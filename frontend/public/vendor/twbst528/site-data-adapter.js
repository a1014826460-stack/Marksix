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

  function clearMarkers(cell) {
    Array.prototype.forEach.call(cell.querySelectorAll("span[style*='background-color']"), function (marker) {
      marker.style.backgroundColor = "";
    });
  }

  function writeCell(cell, value, hitValues) {
    var leaves = textNodes(cell);
    var marker = cell.querySelector("span[style*='background-color']");
    var markerLeaf = marker && textNodes(marker)[0];
    var text = String(value || "");
    clearMarkers(cell);
    if (!markerLeaf || !hitValues || !hitValues.length) {
      if (leaves[0]) leaves[0].nodeValue = text;
      clearLeaves(cell, leaves[0] ? [leaves[0]] : []);
      return;
    }

    var matchingValue = hitValues.filter(function (value) { return value && text.indexOf(value) !== -1; })[0];
    if (!matchingValue || !leaves[0]) {
      leaves[0].nodeValue = text;
      clearLeaves(cell, [leaves[0]]);
      return;
    }

    var index = text.indexOf(matchingValue);
    var markerIndex = leaves.indexOf(markerLeaf);
    var suffix = leaves[markerIndex + 1];
    leaves[0].nodeValue = text.slice(0, index);
    markerLeaf.nodeValue = matchingValue;
    if (suffix) suffix.nodeValue = text.slice(index + matchingValue.length);
    clearLeaves(cell, suffix ? [leaves[0], markerLeaf, suffix] : [leaves[0], markerLeaf]);
    marker.style.backgroundColor = "#FFFF00";
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

  function writeLineGroup(group, value) {
    if (!group || !group.length) return;
    group[0].nodeValue = String(value || "");
    group.slice(1).forEach(function (leaf) { leaf.nodeValue = ""; });
  }

  function writeLineValues(root, values) {
    var groups = lineGroups(root);
    groups.forEach(function (group, index) {
      writeLineGroup(group, values[index] || "");
    });
  }

  function resultValue(row) {
    var result = row && row.result || {};
    if (!result.isOpened) return "开:待开奖";
    var number = resultToken(result.code, true);
    var zodiac = resultToken(result.zodiac, false);
    var drawn = number && zodiac ? number + zodiac : String(result.text || "");
    return "开:" + drawn + (result.isCorrect === true ? "对" : result.isCorrect === false ? "错" : "");
  }

  function resultToken(value, padNumber) {
    var values = String(value || "").split(/[,，、|]+/).map(function (item) {
      return item.trim();
    }).filter(Boolean);
    var token = values.length ? values[values.length - 1] : "";
    return padNumber && /^\d{1,2}$/.test(token) ? token.padStart(2, "0") : token;
  }

  function hitValues(row) {
    if (!row || !row.result || !row.result.isOpened || row.result.isCorrect !== true) return [];
    return [resultToken(row.result.code, true), resultToken(row.result.zodiac, false), resultToken(row.result.color, false)].filter(Boolean);
  }

  function sectionByTitle(title) {
    return Array.prototype.filter.call(window.document.querySelectorAll(".lxlm, .tzlb"), function (section) {
      return String(section.querySelector(".pb-tit") && section.querySelector(".pb-tit").textContent || "").indexOf(title) !== -1;
    })[0] || null;
  }

  function rowsFor(section) {
    return Array.prototype.slice.call(section ? section.querySelectorAll("table.mtbl tbody > tr") : []).filter(function (row) {
      return row.querySelectorAll(":scope > td").length === 3;
    });
  }

  // Shared low-level writer for the identical three-column supplier topology.
  // Each public module below owns its selector and value formatter.
  function renderThreeColumnRows(section, module, formatter) {
    if (!section) return;
    var data = distinctRows(module);
    rowsFor(section).forEach(function (tr, index) {
      var cells = tr.querySelectorAll(":scope > td");
      var row = data[index];
      writeCell(cells[0], row ? termValue(row) : "");
      writeCell(cells[1], row ? formatter(row) : "暂无后端资料", row ? hitValues(row) : []);
      writeResultCell(cells[2], row);
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
    });
  }

  function renderBaxiaoLaixiHistory(module) {
    var section = sectionByTitle("八肖来袭");
    if (section) section.setAttribute("data-prediction-section", "7xiao7ma");
    renderThreeColumnRows(section, module, function (row) {
      return tokens(row).join("");
    });
  }

  function renderJiayeZhongteHistory(module) {
    renderThreeColumnRows(sectionByTitle("家野中特"), module, function (row) {
      return tokens(row).join("+");
    });
  }

  function renderShaliangbanboHistory(module) {
    renderThreeColumnRows(sectionByTitle("杀两半波"), module, function (row) {
      return tokens(row).join("+");
    });
  }

  function renderPingteYiweiHistory(module) {
    renderThreeColumnRows(sectionByTitle("平特一尾"), module, function (row) {
      var value = displayLabels(row, "").replace(/尾/g, "");
      return value ? value + value + value + "尾" : "";
    });
  }

  function renderDaxiaoZhongteHistory(module) {
    renderThreeColumnRows(sectionByTitle("大小中特"), module, function (row) {
      var value = String(rawValue(row, "daxiao") || displayLabels(row, "") || labelTokens(row)[0] || "");
      return value === "大" ? "大数" : value === "小" ? "小数" : value;
    });
  }

  function renderBaofuQixiaoHistory(module) {
    renderThreeColumnRows(sectionByTitle("暴富⑦肖"), module, function (row) {
      return tokens(row).join("");
    });
  }

  function renderHuobaoSitourHistory(module) {
    renderThreeColumnRows(sectionByTitle("火爆④头"), module, function (row) {
      return displayLabels(row, "-").replace(/头/g, "") + "头";
    });
  }

  function renderPingteYixiaoHistory(module) {
    renderThreeColumnRows(sectionByTitle("平特①肖"), module, function (row) {
      var value = tokens(row)[0] || "";
      return value;
    });
  }

  function renderTiandiErxiaoHistory(module) {
    renderThreeColumnRows(sectionByTitle("天地+②肖"), module, function (row) {
      var tiandi = String(rawValue(row, "tiandi") || "");
      var pair = rawValue(row, "xiao_pair");
      if (tiandi && Array.isArray(pair)) return tiandi + "+" + pair.join("");
      var labels = displayLabels(row, "");
      var picks = valueList(rawValue(row, "xiao")).slice(0, 2).join("");
      return labels && picks ? labels + "+" + picks : labels;
    });
  }

  function renderTaiwanPmtImage(module) {
    var image = document.querySelector("img[data-prediction-image='tw_pmt_image']");
    if (!image) return;
    var row = distinctRows(module)[0];
    var url = String(row && row.prediction && row.prediction.imageUrl || "").trim();
    if (!url) {
      image.setAttribute("src", "");
      image.setAttribute("hidden", "hidden");
      return;
    }
    image.setAttribute("src", url);
    image.removeAttribute("hidden");
  }

  function renderSizhongteHistory(module) {
    renderThreeColumnRows(sectionByTitle("四肖中特"), module, function (row) {
      return tokens(row).join("");
    });
  }

  function renderSanxiaoLiumaHistory(module) {
    var section = sectionByTitle("三肖六码");
    if (!section) return;
    var data = distinctRows(module);
    rowsFor(section).forEach(function (tr, index) {
      var cells = tr.querySelectorAll(":scope > td");
      var row = data[index];
      var values = row ? tokens(row) : [];
      var firstLine = values.slice(0, 3).join("");
      var secondLine = values.slice(3, 9).join("-");
      writeCell(cells[0], row ? termValue(row) : "");
      var lineLeaves = textNodes(cells[1]);
      clearMarkers(cells[1]);
      if (!row) {
        if (lineLeaves[0]) lineLeaves[0].nodeValue = "暂无后端资料";
        clearLeaves(cells[1], lineLeaves[0] ? [lineLeaves[0]] : []);
      } else {
        if (lineLeaves[0]) lineLeaves[0].nodeValue = "【" + firstLine + "】";
        if (lineLeaves[1]) lineLeaves[1].nodeValue = secondLine ? "【" + secondLine + "】" : "";
        clearLeaves(cells[1], lineLeaves.slice(0, 2));
      }
      writeResultCell(cells[2], row);
      tr.setAttribute("data-prediction-row", String(index));
    });
  }

  function renderJueshaYixiaoHistory(module) {
    renderThreeColumnRows(sectionByTitle("绝杀①肖"), module, function (row) { return tokens(row).join(""); });
  }

  function renderJueshaYiboHistory(module) {
    renderThreeColumnRows(sectionByTitle("绝杀①波"), module, function (row) { return tokens(row).join(""); });
  }

  function renderDanshuangErxiaoHistory(module) {
    renderThreeColumnRows(sectionByTitle("单双二肖"), module, function (row) { return displayLabels(row, "+"); });
  }

  function renderJueshaYixiaoYiweiHistory(module) {
    renderThreeColumnRows(sectionByTitle("绝杀一肖一尾"), module, function (row) { return tokens(row).join(""); });
  }

  function renderRemainingThreeColumnHistory(title, module, formatter) {
    renderThreeColumnRows(sectionByTitle(title), module, formatter || function (row) {
      return String(row.prediction.text || tokens(row).join(" ")).replace(/\|/g, " ");
    });
  }

  function renderDaimingXiaoHistory(module) {
    renderRemainingThreeColumnHistory("代号生肖", module, function (row) {
      return tokens(row).map(function (value) {
        return String(value).indexOf("|") >= 0 ? String(value).split("|", 2)[1] : String(value);
      }).join("、");
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

  function renderHongLanLvXiaoHistory(module) {
    renderRemainingThreeColumnHistory("红蓝绿肖", module, function (row) {
      return predictionText(row, " ");
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
    });
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

  function renderDaxiaoYitouHistory(module) {
    renderRemainingThreeColumnHistory("大小+①头", module, function (row) {
      return displayLabels(row, "+").replace(/^大$/, "大数").replace(/^小$/, "小数");
    });
  }

  function renderCategoryHistory(title, module, labelMap) {
    renderRemainingThreeColumnHistory(title, module, function (row) {
      var value = displayLabels(row, "");
      Object.keys(labelMap || {}).forEach(function (source) {
        value = value.replace(new RegExp(source, "g"), labelMap[source]);
      });
      return value;
    });
  }

  function renderQiweiSixingHistory(tailModule, lineModule) {
    var tailRows = distinctRows(tailModule);
    var lineRows = distinctRows(lineModule);
    var section = sectionByTitle("七尾四行");
    if (!section) return;
    rowsFor(section).forEach(function (tr, index) {
      var cells = tr.querySelectorAll(":scope > td");
      var tailRow = tailRows[index];
      var lineRow = lineRows[index];
      writeCell(cells[0], tailRow ? termValue(tailRow) : "");
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
    var seasonRows = distinctRows(seasonModule);
    var zodiacRows = distinctRows(zodiacModule);
    var section = sectionByTitle("四季九肖");
    if (!section) return;
    rowsFor(section).forEach(function (tr, index) {
      var cells = tr.querySelectorAll(":scope > td");
      var seasonRow = seasonRows[index];
      var zodiacRow = zodiacRows[index];
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
    var data = distinctRows(module);
    cardRows(section).forEach(function (tr, index) {
      var row = data[index];
      var cell = tr.querySelector("td");
      writeCardHeader(cell, row);
      var detail = cell && cell.querySelector(":scope > span");
      if (detail) writeLineValues(detail, row ? formatter(row) : ["暂无后端资料"]);
      tr.setAttribute("data-prediction-row", String(index));
    });
  }

  function renderLiuxiaoLiumaHistory(module) {
    renderPairedCardHistory("六肖六码", module, function (row) {
      var xiao = valueList(rawValue(row, "xiao"));
      var code = valueList(rawValue(row, "code"));
      if (xiao.length === 6 && code.length === 6) {
        var pairs = xiao.map(function (label, index) {
          return label + String(code[index] || "").padStart(2, "0");
        });
        return [pairs.slice(0, 3).join(""), pairs.slice(3, 6).join("")];
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

  function renderSanxiaoFangSanmaHistory(zodiacModule, codeModule) {
    var zodiacRows = distinctRows(zodiacModule);
    var codeRows = distinctRows(codeModule);
    var section = sectionByTitle("③肖防③码");
    cardRows(section).forEach(function (tr, index) {
      var row = zodiacRows[index];
      var codeRow = codeRows[index];
      var cell = tr.querySelector("td");
      writeCardHeader(cell, row || codeRow);
      var detail = cell && cell.querySelector(":scope > span");
      if (detail) writeLineValues(detail, row && codeRow
        ? [predictionText(row, "") + "+" + predictionText(codeRow, ",")]
        : ["暂无后端资料"]);
    });
  }

  function renderBaxiaoShiliumaHistory(module) {
    renderPairedCardHistory("8肖16码", module, function (row) {
      return splitCardLines(row, 2, "");
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
    var data = distinctRows(module);
    Array.prototype.forEach.call(section ? section.querySelectorAll("table tbody > tr") : [], function (tr, index) {
      var row = data[index];
      var cell = tr.querySelector("td");
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
    var data = distinctRows(module);
    Array.prototype.forEach.call(section ? section.querySelectorAll("table.mtbl") : [], function (table, issueIndex) {
      var row = data[issueIndex];
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

  function renderMayouLailiaoHistory(modules) {
    var section = sectionByTitle("码友来料参考");
    var moduleList = [modules["3zxt"] || modules.sanxiaozhongte, modules.title_47, modules["6xzt"]];
    Array.prototype.forEach.call(section ? section.querySelectorAll("table tbody > tr td") : [], function (cell, cardIndex) {
      var data = distinctRows(moduleList[cardIndex]);
      var groups = lineGroups(cell);
      var issueGroups = groups.filter(function (group) {
        return /\d+期/.test(group.map(function (leaf) { return leaf.nodeValue; }).join(""));
      });
      issueGroups.forEach(function (group, index) {
        var row = data[index];
        writeLineGroup(group, row ? termValue(row).replace(/^第/, "") + "【" + predictionText(row, "") + "】" : "暂无后端资料");
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
      var rows = distinctRows(moduleList[Math.min(Math.max(moduleIndex, 0), moduleList.length - 1)]);
      var row = rows[rowIndex];
      writeLineGroup(group, row ? formatter(row, moduleIndex) : "暂无后端资料");
      rowIndex += 1;
    });
  }

  function renderDujiaGongshiHistory(module) {
    var section = sectionByTitle("独家公式");
    if (!section) return;
    var rows = distinctRows(module);
    var blocks = Array.prototype.slice.call(section.querySelectorAll("td > p > b > font[face]")).filter(function (font) {
      return String(font.textContent || "").indexOf("独家") >= 0 || String(font.textContent || "").indexOf("公式四尾") >= 0;
    });
    ["parity", "size", "tails"].forEach(function (kind, blockIndex) {
      var block = blocks[blockIndex];
      if (!block) return;
      var groups = lineGroups(block).filter(function (group) {
        return /\d+期/.test(group.map(function (leaf) { return String(leaf.nodeValue || ""); }).join(""));
      });
      groups.forEach(function (group, rowIndex) {
        var row = rows[rowIndex];
        var formula = row && rawValue(row, "formula");
        var entry = formula && formula[kind];
        var labels = entry && Array.isArray(entry.labels) ? entry.labels : [];
        var firstLabel = String(labels[0] || "").replace(/[\[\]"]/g, "");
        var value = kind === "tails"
          ? compactLabels(labels, "") + "尾"
          : firstLabel.split("|", 1)[0].trim() + "数";
        var rawCodes = valueList(rawValue(row, "res_code"));
        var opened = Boolean(row && row.result && row.result.isOpened);
        var prefix = opened
          ? rawCodes.slice(0, 6).join("-") + " T" + resultToken(row.result.code, true)
          : "--------------------- T--";
        var marker = !opened ? "?" : row.result.isCorrect === true ? "√" : "x";
        writeLineGroup(group, row ? termValue(row).replace(/^第/, "") + " " + prefix + " 【" + value + "】" + marker : "暂无后端资料");
      });
    });
  }

  function renderSanqiJihuaHistory(modules) {
    renderCompositeLines("三期计划", [modules.shuangbo, modules.danshuangtema, modules.pt1xiao, modules["3zxt"] || modules.sanxiaozhongte], function (row) {
      return termValue(row).replace(/^第/, "") + "【" + displayLabels(row, "") + "】" + resultValue(row);
    });
  }

  function renderZongheJueshaHistory(modules) {
    renderCompositeLines("综合绝杀", [modules.juesha2xiao, modules.juesha1wei, modules["3tou"], modules["3hang"]], function (row) {
      return termValue(row).replace(/^第/, "") + "稳杀【" + displayLabels(row, "") + "】" + resultValue(row);
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
    var data = distinctRows(module);
    Array.prototype.forEach.call(section.querySelectorAll("table tbody > tr"), function (tr, index) {
      var row = data[index];
      var headerFonts = tr.querySelectorAll("td p b > font");
      if (headerFonts.length >= 3) {
        writeLeaf(headerFonts[0], row ? termValue(row) : "");
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
    Array.prototype.forEach.call(window.document.querySelectorAll(".lxlm, .tzlb"), renderPredictionTitle);
    renderYijuZhongpingHistory(modules.yijuzhenyan);
    renderLiangboTuweiHistory(modules.shuangbo);
    renderBaxiaoLaixiHistory(modules["7xiao7ma"]);
    renderJiayeZhongteHistory(modules.pt2xiao);
    renderShaliangbanboHistory(modules.shaliangbanbo);
    renderPingteYiweiHistory(modules.pt1wei);
    renderDaxiaoZhongteHistory(modules.daxiao);
    renderBaofuQixiaoHistory(modules["7xiao7ma"]);
    renderHuobaoSitourHistory(modules.sitouzhongte);
    renderPingteYixiaoHistory(modules.pt1xiao);
    renderTiandiErxiaoHistory(moduleWithRows(modules.tiandi_2xiao, modules.title_5));

    renderTaiwanPmtImage(modules.tw_pmt_image);
    renderSizhongteHistory(modules.title_47);
    renderSanxiaoLiumaHistory(modules.pt3xiao);
    renderJueshaYixiaoHistory(modules.juesha1xiao);
    renderJueshaYiboHistory(modules.jueshabanbo);
    renderDanshuangErxiaoHistory(modules.danshuangtema);
    renderJueshaYixiaoYiweiHistory(modules.juesha1wei);
    renderRemainingThreeColumnHistory("杀肖杀码", modules.juesha3xiao);
    renderToudanshuangHistory(modules.toudanshuang);
    renderRemainingThreeColumnHistory("琴棋书画", modules.qinqi);
    renderRemainingThreeColumnHistory("本期输尽光", modules.shujinguang);
    renderForumHistory(modules);
    renderDaimingXiaoHistory(modules.daimingxiao);
    renderDujiaGongshiHistory(modules.dujia_gongshi);
    renderLiuweiChuteHistory(modules.liuweichute);
    renderLiuxiaoLiumaHistory(modules.liuxiaoliuma);
    renderYixiaoYimaHistory(moduleWithRows(modules.public_yixiao_yima, modules["9xiao12ma"]));
    renderMayouLailiaoHistory(modules);
    renderShuhaQiweiHistory(modules.title_74);
    renderLiuxiaoShibamaHistory(modules.liuxiao18ma);
    renderSiduanzhongteHistory(modules.siduanzhongte);
    renderHongLanLvXiaoHistory(modules.hllx);
    renderWuxingLailiaoHistory(modules["3hang"]);
    renderJueshaShimaHistory(modules.wensha10ma);
    renderLiuxiaoShiermaHistory(modules["9xiao12ma"]);
    renderHeibaiSanxiaoHistory(moduleWithRows(modules.heibai3xiao, modules.title_45));
    renderCategoryHistory("阴阳⑧码中特", modules.title_48, {});
    renderShibamaHistory(modules.liuxiao18ma);
    renderSanxiaoFangSanmaHistory(modules.pt3xiao, modules.pt3xiao);
    renderBaxiaoShiliumaHistory(modules.liuxiao18ma);
    renderSanqiJihuaHistory(modules);
    renderWuxiaoShimaHistory(moduleWithRows(modules.wuxiao_wuma, modules["4xiao8ma"]));
    renderWenzhongDanshuangHistory(modules.danshuangtema);
    renderZongheJueshaHistory(modules);
    renderDaxiaoYitouHistory(modules.dxztt1);
    renderSixiaoBamaHistory(modules["4xiao8ma"]);
    renderCategoryHistory("日夜特肖", modules.qianhou_texiao, {});
    renderCategoryHistory("左右中特", modules.title_5, {});
    renderCategoryHistory("前后中特", modules.qianhou_texiao, {});
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
        historyLimit: HISTORY_LIMIT
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
    bindLotteryTabs();
    selectLottery(activeLottery.lotteryType);
  });
})(window);
