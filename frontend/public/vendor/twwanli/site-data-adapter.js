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
    // 候选集合可能以整串 `标签|号码` 的形式出现在 tokens 里（含 JSON 包装），
    // 这里统一剥掉 `[` `]` `"` `'`，避免把原始 JSON 残留渲染到页面上（S5）。
    return tokenValues(row).map(function (value) {
      return String(value).split("|")[0].replace(/[\[\]"']/g, "").trim();
    }).filter(Boolean);
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
  function featuredRows() { return Array.prototype.slice.call(document.querySelectorAll("#jhtz a[data-prediction-module]")); }

  function clearHit(root) {
    Array.prototype.forEach.call(root.querySelectorAll("[data-prediction-hit]"), function (node) {
      node.removeAttribute("data-prediction-hit");
    });
  }

  // hitSlot 指定命中项落在哪一列：多分组模块（单双各四肖 / 天地生肖）必须高亮
  // 真正命中的那一组，否则会出现「第二组命中却点亮第一组」的错位高亮。
  // contentHtml 用于「一行多个候选项、只有一个命中」的模块（如波色）：此时必须
  // 只给命中的那一项加 data-prediction-hit，整块上黄底会把没命中的候选项也点亮（S2）。
  function writeRow(row, issue, content, result, secondary, hit, hitSlot, contentHtml) {
    var issueSlot = row.querySelector("[data-prediction-issue]");
    var contentSlot = row.querySelector("[data-prediction-content]");
    var secondarySlot = row.querySelector("[data-prediction-content-secondary]");
    var resultSlot = row.querySelector("[data-prediction-result]");
    clearHit(row);
    if (issueSlot) issueSlot.textContent = issue || "";
    if (contentSlot) {
      if (contentHtml) contentSlot.innerHTML = contentHtml;
      else contentSlot.textContent = content || "";
    }
    if (secondarySlot) secondarySlot.textContent = secondary || "";
    if (resultSlot) resultSlot.textContent = result || "";
    if (!hit) return;
    // contentHtml 调用方通常自己在候选项内部标命中项（整格不上黄底，见波色/买啥开啥）；
    // 「一肖一码」整格即候选项，调用方传 hitSlot="content" 显式要求整格高亮。
    if (contentHtml && hitSlot !== "content") return;
    var target = hitSlot === "secondary" ? secondarySlot : contentSlot;
    if (!target) target = contentSlot || secondarySlot;
    if (target) target.setAttribute("data-prediction-hit", "true");
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // 一行多个候选项时，只把真正命中的那一项包进 data-prediction-hit，
  // 没命中的候选项保持无高亮（S2：只有命中才高亮）。
  function highlightOnly(items, hitValue, separator) {
    return items.map(function (item) {
      var text = String(item == null ? "" : item);
      return text && text === hitValue
        ? '<span data-prediction-hit="true">' + escapeHtml(text) + "</span>"
        : escapeHtml(text);
    }).join(separator === undefined ? "+" : separator);
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

  // 号码展示区一行最多 4 码（`01.02.03.04` 在 26px 粗体下约 150px，放得进
  // 360px 视口下 #yxym 中列的 50% ≈ 176px）；超出就均衡折行（7 码 → 4+3，5 码 → 3+2）。
  var CODES_PER_LINE = 4;
  function codeLineHtml(codes) {
    var lineCount = Math.ceil(codes.length / CODES_PER_LINE);
    var perLine = Math.ceil(codes.length / lineCount);
    var lines = [];
    for (var index = 0; index < codes.length; index += perLine) {
      lines.push(codes.slice(index, index + perLine).map(escapeHtml).join("."));
    }
    return lines.join("<br>");
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
        var label = ["一码", "三码", "五码", "七码", "一肖", "二肖", "三肖", "四肖", "五肖", "六肖", "七肖", "九肖", "波色"][rowIndex] || "";
        var issue = issueOf(source) + "期:" + label;
        if (!codeCount && !xiaoCount) {
          // 波色行：候选是 mode 38（双波中特）的两个波色，落在 token 正文里
          // （`蓝波,绿波`），并不在 raw.wave 列。只读 raw.wave 会取到空值 →
          // 页面渲染兜底串「暂无后端资料」、还给它上了黄底并显示「对」，
          // 属 S1（未命中/无数据不得给判定）+ S2（兜底串不该高亮）违规。
          var waves = listValue(rawValue(source, "wave")).slice(0, 2);
          if (!waves.length) {
            waves = [];
            labels(source).forEach(function (label) {
              String(label).split(/[,，、\s]+/).forEach(function (part) {
                var value = part.trim();
                if (value && waves.indexOf(value) < 0) waves.push(value);
              });
            });
            waves = waves.slice(0, 2);
          }
          if (!waves.length) {
            // 真正的数据缺失：不给判定、不高亮。
            return writeRow(row, issue, "暂无后端资料", "");
          }
          var isHit = source.result && source.result.isCorrect === true;
          var hitWave = isHit ? specialWave(source) : "";
          return writeRow(
            row,
            issue,
            waves.join("+"),
            resultText(source),
            "",
            false,
            "content",
            // 只有命中的那个波色加黄底；没命中的波色保持无高亮（S2）。
            hitWave && waves.indexOf(hitWave) >= 0 ? highlightOnly(waves, hitWave) : waves.map(escapeHtml).join("+")
          );
        }
        var hit = Boolean(source.result && source.result.isCorrect === true);
        if (codeCount) {
          var codes = codeValues(source).slice(0, codeCount);
          if (!codes.length) return writeRow(row, issue, "暂无后端资料", resultText(source), "", hit);
          // 7 码在 26px 粗体下宽 269px、5 码 190px，360px 视口的中列只有 ~176px，
          // 必须显式折行；用 writeRow 既有的 contentHtml 通道插入 <br>（不新增 DOM 手法）。
          return writeRow(row, issue, "", resultText(source), "", hit, "content", codeLineHtml(codes));
        }
        var value = labels(source).slice(0, xiaoCount).join("");
        writeRow(row, issue, value || "暂无后端资料", resultText(source), "", hit);
      });
    });
  }

  function predictionText(row) {
    return String(row && row.prediction && row.prediction.text || rawValue(row, "content") || "").trim();
  }

  // mode 38（双波中特）的命中目标是**特码波色**：接口给的是 `red/blue/green`，
  // 展示层用的是 `红波/蓝波/绿波`。
  var WAVE_BY_COLOR = { red: "红波", blue: "蓝波", green: "绿波" };
  function specialWave(row) {
    var color = String(row && row.result && row.result.color || "").trim().toLowerCase();
    return WAVE_BY_COLOR[color] || "";
  }

  function resultParts(row) {
    var result = row && row.result || {};
    var last = function (value) {
      var values = String(value || "").split(/[,，、|\s]+/).filter(Boolean);
      return values.length ? values[values.length - 1] : "";
    };
    var code = last(result.code);
    var zodiac = last(result.zodiac);
    return { isOpened: result.isOpened === true, code: code || "00", zodiac: zodiac || "？" };
  }

  // 家禽 / 野兽的**固定分组**（与 `public.fixed_data` sign='家禽|野兽' 一致）。
  // 判定必须用这 6+6 全组，不能用本期 `jia`/`ye` 抽出的子集：例如 270 期预测
  // 〈〈家禽〉〉、特码 37 马 —— 马 ∈ 家禽全组，应为「对」；旧实现拿 jia/ye 子集
  // 反查「哪一列含特肖」，特肖没被抽中就得到空分类 → 误判「错」。
  var DOMESTIC_WILD_GROUPS = {
    "家禽": ["牛", "马", "羊", "鸡", "狗", "猪"],
    "野兽": ["鼠", "虎", "兔", "龙", "蛇", "猴"],
  };

  function canonicalDomesticWildCategory(zodiac) {
    var value = String(zodiac || "").trim();
    if (!value) return "";
    return ["家禽", "野兽"].filter(function (label) {
      return DOMESTIC_WILD_GROUPS[label].indexOf(value) >= 0;
    })[0] || "";
  }

  // 【买啥开啥】的数据源是 mode 63（家野中特，`modules.title_63`）：正文形如
  // `["家禽|牛,马,羊,鸡,狗,猪"]` —— **单个分类 + 该分类全组**，展示值就是 `|` 前的
  // 分类名（需剥掉 JSON 引号/方括号残留）。取不到分类即无数据，退回兜底文案：
  // 既不能用开奖分类 `domestic_wild_category` 反推（那是答案本身，卡片会恒「准」），
  // 也不能退回旧 title_14 的 `jia`/`ye` 4+4 子集反查（特肖没被抽中就会把「准」误判成「错」）。
  function predictionDomesticWildCategory(row) {
    var candidates = [];
    var rawContent = rawValue(row, "content");
    if (typeof rawContent === "string") candidates.push(rawContent);
    var text = row && row.prediction && row.prediction.text;
    if (typeof text === "string") candidates.push(text);
    labels(row).forEach(function (label) { candidates.push(String(label)); });
    for (var index = 0; index < candidates.length; index += 1) {
      var parts = String(candidates[index]).split(/[;；]/);
      for (var partIndex = 0; partIndex < parts.length; partIndex += 1) {
        var label = parts[partIndex].split("|")[0].replace(/[\[\]"']/g, "").trim();
        if (label === "家禽" || label === "野兽") return label;
      }
    }
    return "";
  }

  function renderBuyWhatOpens(modules) {
    // 后端模块「家野中特」= mode 63 → moduleKey `title_63`；不再读 title_14（家禽野兽）。
    var sourceRows = distinctRows(modules.title_63);
    rows(section("msks")).forEach(function (node, index) {
      var source = sourceRows[index];
      if (!source) return writeRow(node, "", "暂无后端资料", "");
      var parts = resultParts(source);
      // 预测内容与开奖状态**无关**：未开奖期（如 2026272）后端 mode 63 已生成正文，
      // 必须照常显示本期预测分类；「待开奖」只属于开奖槽，绝不能占用预测内容槽
      // （旧实现的 `!isOpened → 待开奖占位` 会把已生成的预测整块吞掉）。
      var category = predictionDomesticWildCategory(source);
      if (!category) return writeRow(node, issueOf(source) + "期:火爆家野", "〈〈暂无后端资料〉〉", "");
      if (!parts.isOpened) {
        return writeRow(node, issueOf(source) + "期:火爆家野", "〈〈" + escapeHtml(category) + "〉〉", "？00");
      }
      // 判定 = 特别号生肖是否落在该分类的固定分组里（fixed_data 家禽|野兽 全组）。
      var hit = canonicalDomesticWildCategory(parts.zodiac) === category;
      var verdict = hit ? "准" : "错";
      // 分类名写进预测内容槽，只有它是候选；命中时仅把分类名包进命中标记
      // （期号、〈〈 〉〉、「准/错」、开奖号码一律不黄）。
      var contentHtml = "〈〈" + (hit
        ? '<span data-prediction-hit="true">' + escapeHtml(category) + "</span>"
        : escapeHtml(category)) + "〉〉";
      writeRow(
        node,
        issueOf(source) + "期:火爆家野",
        "",
        parts.zodiac + parts.code + verdict,
        "",
        false,
        null,
        contentHtml
      );
    });
  }
  function renderKillThreeXiao(modules) { renderThreeColumnHistory("wsxx", modules.juesha3xiao, function (row) { return "杀三肖『" + labels(row).slice(0, 3).join("") + "』"; }); }
  function renderFourXiao(modules) { renderThreeColumnHistory("wl4x", modules.sixiao_sima, function (row) { return labels(row).slice(0, 4).join("") || "暂无后端资料"; }); }
  function renderBigSmall(modules) { renderThreeColumnHistory("dxzt", modules.daxiao, function (row) { var value = String(rawValue(row, "daxiao") || labels(row)[0] || ""); return value === "大" ? "大数" : value === "小" ? "小数" : value || "暂无后端资料"; }); }
  function renderFiveTail(modules) { renderThreeColumnHistory("5wzt", modules.title_66, function (row) { return listValue(rawValue(row, "tail")).slice(0, 5).join("-") || labels(row).slice(0, 5).join("-") || "暂无后端资料"; }); }
  function renderSelectedTwentyFour(modules) { renderThreeColumnHistory("jx24m", modules.ma24, function (row) { return codeValues(row).slice(0, 24).join("-") || "暂无后端资料"; }); }
  function renderFourSegments(modules) { renderThreeColumnHistory("sdzt", modules.siduanzhongte, function (row) { return labels(row).slice(0, 4).join("+") || "暂无后端资料"; }); }
  function renderOneWave(modules) { renderThreeColumnHistory("ybzt", modules.title_143, function (row) { return listValue(rawValue(row, "wave")).slice(0, 1).join("") || labels(row).slice(0, 1).join("") || "暂无后端资料"; }); }
  // 天地肖固定分组（与 `public.fixed_data` sign='天地肖' 及各站 sx.html 一致）。
  var TIANDI_GROUPS = {
    "天肖": ["兔", "马", "猴", "猪", "牛", "龙"],
    "地肖": ["鼠", "虎", "蛇", "羊", "鸡", "狗"],
  };

  function tiandiGroup(sideLabel) {
    var value = String(sideLabel || "");
    if (value.indexOf("天") === 0) return TIANDI_GROUPS["天肖"];
    if (value.indexOf("地") === 0) return TIANDI_GROUPS["地肖"];
    return [];
  }

  function renderHeavenEarth(modules) {
    var sourceRows = distinctRows(modules.title_5);
    rows(section("tdsx")).forEach(function (node, index) {
      var source = sourceRows[index];
      if (!source) return writeRow(node, "", "暂无后端资料", "");
      var parts = resultParts(source);
      var sideLabel = labels(source).slice(0, 1).join("") || "天地肖";
      var chosen = listValue(rawValue(source, "xiao"));
      // 同【买啥开啥】：未开奖期也要显示本期预测（天地组 + 两肖），只有开奖槽是待开奖。
      if (!parts.isOpened) {
        return writeRow(
          node,
          issueOf(source) + "期",
          "【" + escapeHtml(sideLabel) + (chosen.length ? "+" + escapeHtml(chosen.join("")) : "") + "】",
          "？00"
        );
      }
      // 天地生肖 = 天地选1 + 生肖选2：特肖落在**天地组**或**两肖**任一即命中。
      // vendor 接口的 is_correct 只比对那两肖（会让天地肖永远不参与判定，
      // 270 期「天肖+兔鸡」开 37 马应为对却显示错），所以这里本地复算，
      // 与 twcaibawang 的天地两肖并集口径一致。
      var inGroup = tiandiGroup(sideLabel).indexOf(parts.zodiac) >= 0;
      var inChosen = chosen.indexOf(parts.zodiac) >= 0;
      var hit = inGroup || inChosen;
      // 只点亮真正命中的那一项：命中两肖 → 点亮该生肖；命中天地组 → 点亮组名。
      var sideHtml = inGroup && !inChosen
        ? '<span data-prediction-hit="true">' + escapeHtml(sideLabel) + "</span>"
        : escapeHtml(sideLabel);
      var chosenHtml = highlightOnly(chosen, inChosen ? parts.zodiac : "", "");
      var contentHtml = "【" + sideHtml + (chosen.length ? "+" + chosenHtml : "") + "】";
      writeRow(
        node,
        issueOf(source) + "期",
        "",
        "开:" + parts.code + parts.zodiac + (hit ? "对" : "错"),
        "",
        false,
        null,
        contentHtml
      );
    });
  }
  function renderThreeHeads(modules) { renderThreeColumnHistory("3tzt", modules["3tou"], function (row) { return labels(row).slice(0, 3).join("-") || "暂无后端资料"; }); }
  function renderSumBigSmall(modules) { renderThreeColumnHistory("hsdx", modules.title_279, function (row) { return predictionText(row) || "暂无后端资料"; }); }
  function renderFlatOneXiao(modules) { renderThreeColumnHistory("pt1xiao", modules.pt1xiao, function (row) { return labels(row).slice(0, 1).join("") || "暂无后端资料"; }); }
  function renderSumOddEven(modules) { renderThreeColumnHistory("hsds", modules.title_132, function (row) { return predictionText(row).replace(/^合(单|双)$/, "合数$1") || "暂无后端资料"; }); }
  function renderMusicChess(modules) {
    var sourceRows = distinctRows(modules.qinqi);
    rows(section("qqsh")).forEach(function (node, index) {
      var source = sourceRows[index];
      if (!source) return writeRow(node, "", "暂无后端资料", "");
      var title = listValue(rawValue(source, "title")).join("") || "暂无后端资料";
      var reference = String(rawValue(source, "qinqi_reference") || "").trim();
      writeRow(
        node,
        index === 0 && reference ? reference + "\n" + issueOf(source) + "期:" : issueOf(source) + "期:",
        "琴棋书画→" + title,
        // 命中/未命中都要给判定：原先只渲染「开:生肖号码」，命中也没有「对」。
        resultText(source),
        "",
        source.result && source.result.isCorrect === true
      );
    });
  }
  function renderLuckyOminousSixXiao(modules) { renderThreeColumnHistory("jxzt", modules["6xzt"], function (row) { return labels(row).slice(0, 6).join("") || "暂无后端资料"; }); }
  function renderFiveElements(modules) { renderThreeColumnHistory("jz5x", modules["3hang"], function (row) { return labels(row).slice(0, 3).join("+") || "暂无后端资料"; }); }
  function renderOddEvenFourXiao(modules) {
    var sourceRows = distinctRows(modules.danshuang4xiao);
    rows(section("dssx")).forEach(function (row, index) {
      var source = sourceRows[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", "");
      var hit = Boolean(source.result && source.result.isCorrect === true);
      var zodiac = resultParts(source).zodiac;
      var xiao1 = String(rawValue(source, "xiao_1") || labels(source).slice(0, 4).join(""));
      var xiao2 = String(rawValue(source, "xiao_2") || labels(source).slice(4, 8).join(""));
      // 特肖落在第二组时把黄底打在第二组所在的单元格上。
      var hitSlot = zodiac && xiao2.indexOf(zodiac) >= 0 && xiao1.indexOf(zodiac) < 0 ? "secondary" : "content";
      writeRow(
        row,
        issueOf(source) + "期",
        xiao1,
        resultText(source),
        xiao2,
        hit,
        hitSlot
      );
    });
  }

  function formatFeaturedPost(moduleKey, source) {
    if (!source) return "暂无后端资料";
    if (moduleKey === "pt1wei") {
      return listValue(rawValue(source, "tail")).slice(0, 1).join("") || labels(source).slice(0, 1).join("") || "暂无后端资料";
    }
    if (moduleKey === "pt1xiao") {
      return labels(source).slice(0, 1).join("") || "暂无后端资料";
    }
    if (moduleKey === "sitouzhongte") {
      return labels(source).slice(0, 4).join("-") || "暂无后端资料";
    }
    if (moduleKey === "title_14") {
      var domestic = listValue(rawValue(source, "jia")).slice(0, 4).join("");
      var wild = listValue(rawValue(source, "ye")).slice(0, 4).join("");
      if (domestic || wild) return "家禽:" + (domestic || "暂无") + " 野兽:" + (wild || "暂无");
      return labels(source).slice(0, 8).join("") || "暂无后端资料";
    }
    return "暂无后端资料";
  }

  function renderFeaturedPosts(modules) {
    var sourceByKey = { pt1wei: modules.pt1wei, pt1xiao: modules.pt1xiao, title_14: modules.title_14, sitouzhongte: modules.sitouzhongte };
    var seenByModule = {};
    featuredRows().forEach(function (row) {
      var moduleKey = String(row.getAttribute("data-prediction-module") || "");
      var sourceRows = distinctRows(sourceByKey[moduleKey]);
      var rowIndex = seenByModule[moduleKey] || 0;
      seenByModule[moduleKey] = rowIndex + 1;
      var source = sourceRows[rowIndex];
      if (!source) return writeRow(row, "", "暂无后端资料", "");
      writeRow(row, issueOf(source) + "期", formatFeaturedPost(moduleKey, source), resultText(source), "", source.result && source.result.isCorrect === true);
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
    renderFeaturedPosts(modules);
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

  function syncFeaturedPostLinks(lotteryType) {
    featuredRows().forEach(function (link) {
      var href = String(link.getAttribute("href") || "").split("?")[0];
      if (href) link.setAttribute("href", href + "?lottery_type=" + lotteryType);
    });
  }

  function needsPredictionRefresh(envelope) {
    var modules = modulesByKey(envelope);
    return ["6xzt", "pt1wei", "sitouzhongte"].some(function (moduleKey) {
      return distinctRows(modules[moduleKey]).length === 0;
    });
  }

  function loadPredictions(lotteryType, retried) {
    client.loadPredictions({ lotteryType: lotteryType, historyLimit: 8 }).then(function (envelope) {
      if (activeLotteryType !== lotteryType || !envelope.data) return;
      if (!retried && needsPredictionRefresh(envelope)) {
        client.clear("predictions");
        loadPredictions(lotteryType, true);
        return;
      }
      renderPredictions(envelope);
      window.dispatchEvent(new window.CustomEvent("site-data:ready", { detail: { siteKey: siteConfig.siteKey, resource: "predictions", state: envelope.state } }));
    });
  }

  function selectLottery(lotteryType) {
    lotteryType = Number(lotteryType);
    if (![1, 2, 3].includes(lotteryType)) return;
    activeLotteryType = lotteryType;
    syncFeaturedPostLinks(lotteryType);
    client.loadDraw({ lotteryType: lotteryType }).then(function (envelope) {
      if (activeLotteryType === lotteryType && envelope.data) renderDrawPanel(envelope);
    });
    loadPredictions(lotteryType, false);
  }

  window.addEventListener("message", function (event) {
    if (event.origin !== window.location.origin || event.source !== knownDrawFrame.contentWindow) return;
    var message = event.data || {};
    if (message.type === "lottery-change" && message.siteKey === siteConfig.siteKey) selectLottery(message.lotteryType);
  });

  window.TwwanliSiteDataAdapter = { selectLottery: selectLottery, siteConfig: siteConfig };
  selectLottery(activeLotteryType);
})(window, document);


