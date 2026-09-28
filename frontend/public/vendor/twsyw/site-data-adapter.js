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
  // 多段资料**逐段分行**（2026-09-30）：一行里用「；」拼起来的每一份资料各占一行 ——
  // 段间保留「；」分隔符再插入 `<br>`。这样 `textContent` 与旧版逐字相同（既有文本断言不受
  // 影响），换行只体现在 `innerText` 与视觉上（`[data-prediction-content]` 是 `display:block`）。
  function segmentLines(segments) {
    return (segments || []).map(function (segment) { return String(segment == null ? "" : segment); }).join("；<br>");
  }
  // 「展示的候选就是该机制的**完整**候选集」的模块（家禽野兽 / 24码 / 大小 / 四肖 / 五尾 /
  // 九肖 / 三头 / 双波 / 琴棋书画 …）：判定字继续透传后端 `is_correct`（不改口径），
  // 但高亮只在本行判定为「对」**且**展示的候选项里确实能对上本期开奖属性时，才打给那一项。
  // 于是「错」与「未开奖」恒为零黄底，且绝不会再出现整块/整串黄底。
  function hitWhenCorrect(row, matched) {
    return Boolean(row && row.result && row.result.isCorrect === true) && matched === true;
  }
  // `verdict(row) -> { hit, html, text? }` 可选：给了就按**本单元格展示的候选**复算判定与
  // 高亮（`html` 里只包命中项，`hit` 只控制兜底整块标记、给了 `html` 时不会用到），不再
  // 透传 `result.isCorrect`；`text` 给了就原样作为判定字（用于「判定仍透传」的模块）。
  // 不给 `verdict` 则沿用整份资料的既有口径。
  function renderHistory(id, module, formatter, verdict) {
    var source = distinctRows(module);
    historyRows(section(id)).forEach(function (row, index) {
      var current = source[index];
      if (!current) return writeRow(row, "", "暂无后端资料", "", false);
      var content = formatter(current) || "暂无后端资料";
      if (!verdict) return writeRow(row, issueOf(current) + "期", content, resultText(current), current.result && current.result.isCorrect === true);
      var outcome = verdict(current) || {};
      var hit = outcome.hit === true;
      var text = outcome.text == null ? displayedResultText(current, hit) : outcome.text;
      writeRow(row, issueOf(current) + "期", content, text, hit, outcome.html || "");
    });
  }
  function domesticWildGroups(row) {
    var parts = predictionText(row).split(";");
    function group(index, prefix) {
      return String(parts[index] || "").replace(new RegExp("^" + prefix + "\\|?"), "")
        .split(/[|,，、\s]+/).map(function (value) { return value.trim(); }).filter(Boolean);
    }
    return { domestic: group(0, "家禽"), wild: group(1, "野兽") };
  }
  function domesticWild(row) {
    var groups = domesticWildGroups(row);
    return "家禽野兽资料：家禽 " + groups.domestic.join("") + "；野兽 " + groups.wild.join("");
  }
  // 家禽野兽（`#fslx` / `#jiaye`）：两段资料各占一行，只点亮生肖组里等于本期**特肖**的那一个字
  // （旧写法给整个内容槽位打标记，`display:block` 下等于整行黄底）。
  function domesticWildOutcome(row) {
    var groups = domesticWildGroups(row), zodiac = specialParts(row).zodiac;
    var domesticMatched = Boolean(zodiac) && groups.domestic.indexOf(zodiac) >= 0;
    var wildMatched = Boolean(zodiac) && groups.wild.indexOf(zodiac) >= 0;
    var hit = hitWhenCorrect(row, domesticMatched || wildMatched);
    return {
      hit: hit,
      text: resultText(row),
      html: segmentLines([
        "家禽野兽资料：家禽 " + highlightOnly(groups.domestic, hit && domesticMatched ? zodiac : "", ""),
        "野兽 " + highlightOnly(groups.wild, hit && wildMatched ? zodiac : "")
      ])
    };
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

  // ── 本期**七个**开奖号码 / 七肖（平特口径用）──────────────────────────────
  // `result.code` / `result.zodiac` 只给特码/特肖，整期开奖串在 `raw.res_code` /
  // `raw.res_sx`（与 lottery_draws.numbers 同序，末位即特码/特肖）。
  // 平特玩法（平特 N 肖 / 平特 N 尾）的命中要跟这七个比，不是只比特码。
  function drawnList(row, key) {
    var raw = rawField(row, key);
    var values = String(raw == null ? "" : raw).split(/[,，、|\s]+/).map(function (value) {
      return String(value).trim();
    }).filter(Boolean);
    return values;
  }
  function drawnCodes(row) {
    var codes = drawnList(row, "res_code").map(function (value) {
      var digits = value.replace(/[^0-9]/g, "");
      return digits ? ("0" + digits).slice(-2) : "";
    }).filter(Boolean);
    if (codes.length) return codes;
    var single = specialParts(row).code;
    return single ? [single] : [];
  }
  function drawnZodiacs(row) {
    var zodiacs = drawnList(row, "res_sx");
    if (zodiacs.length) return zodiacs;
    var single = specialParts(row).zodiac;
    return single ? [single] : [];
  }

  // ── 「展示即候选」判定工具（2026-09-29）──────────────────────────────
  // 凡是一行只展示某份资料的一部分的单元格，判定必须只用**展示出来的那一份**：
  // 展示子集就是候选集，判定字也按展示候选本地复算、不再透传 `result.isCorrect`。
  // 旧写法的两种症状都源于此：
  //   · 「显示对却没有黄底」——展示被裁到前 N 个，判定却用整份资料（命中落在被裁掉的部分）；
  //   · 「另一个维度命中却显示错」——一行展示多路候选，判定只取第一路（或多路里的第一份）。
  var WAVE_LABELS = ["红波", "蓝波", "绿波"];
  // 与 backend `predict.number_maps.WAVE_COLOR_NUMBER_MAP` / `public.fixed_data` sign='波色' 一致。
  var WAVE_NUMBERS = {
    "红波": ["01", "02", "07", "08", "12", "13", "18", "19", "23", "24", "29", "30", "34", "35", "40", "45", "46"],
    "蓝波": ["03", "04", "09", "10", "14", "15", "20", "25", "26", "31", "36", "37", "41", "42", "47", "48"],
    "绿波": ["05", "06", "11", "16", "17", "21", "22", "27", "28", "32", "33", "38", "39", "43", "44", "49"]
  };
  function inList(list, value) { return Boolean(value) && (list || []).indexOf(value) >= 0; }
  // 固定词表的候选标签：兼容 tokens 被拆成单字（`合双` → `合`、`双`）与整串两种形状。
  function vocabularyLabels(row, vocabulary) {
    var rest = labels(row).join("");
    var found = [];
    while (rest) {
      var bestAt = -1, bestLabel = "";
      vocabulary.forEach(function (label) {
        var at = rest.indexOf(label);
        if (at < 0) return;
        if (bestAt < 0 || at < bestAt || (at === bestAt && label.length > bestLabel.length)) { bestAt = at; bestLabel = label; }
      });
      if (bestAt < 0) break;
      found.push(bestLabel);
      rest = rest.slice(bestAt + bestLabel.length);
    }
    return found;
  }
  // 特码派生属性（与 backend `predict.categories.size_parity` / `number` 一致）：
  // 头 = 十位（01-09 记 0头）；尾 = 个位；段 = 每 7 码一段（1段=01-07 … 7段=43-49）；
  // 合数 = 十位 + 个位之和（≥7 合数大，否则合数小；奇 合单，偶 合双）。
  function specialAttributes(row) {
    var parts = specialParts(row);
    var digits = String(parts.code || "").replace(/[^0-9]/g, "");
    var number = digits ? parseInt(digits, 10) : -1;
    var tens = digits ? Number(digits.charAt(0)) : -1;
    var tail = digits ? Number(digits.charAt(digits.length - 1)) : -1;
    var combined = tens >= 0 && tail >= 0 ? tens + tail : -1;
    var wave = "";
    if (digits.length >= 2) {
      WAVE_LABELS.forEach(function (label) { if (!wave && WAVE_NUMBERS[label].indexOf(digits) >= 0) wave = label; });
    }
    return {
      code: digits.length >= 2 ? digits.slice(-2) : (digits ? ("0" + digits).slice(-2) : ""),
      zodiac: parts.zodiac,
      head: number > 0 ? (number < 10 ? "0头" : Math.floor(number / 10) + "头") : "",
      tail: tail >= 0 ? tail + "尾" : "",
      segment: number > 0 ? Math.floor((number - 1) / 7) + 1 + "段" : "",
      combinedParity: combined >= 0 ? (combined % 2 === 1 ? "合单" : "合双") : "",
      combinedSize: combined >= 0 ? (combined >= 7 ? "合数大" : "合数小") : "",
      wave: wave
    };
  }
  // 判定字：未开奖 → 待开奖；特码与特肖都拿不到（无从复算）时才回退到后端文本。
  function displayedResultText(row, hit) {
    var result = row && row.result || {};
    if (!result.isOpened) return "开:待开奖";
    var parts = specialParts(row);
    if (!parts.code && !parts.zodiac) return resultText(row);
    return "开:" + parts.code + parts.zodiac + (hit ? "对" : "错");
  }

  function renderFslx(modules) { renderHistory("fslx", modules.title_14, domesticWild, domesticWildOutcome); }
  // 二十四码：展示的就是该机制的完整 24 码 —— 判定透传，高亮只点特码那一个号（旧写法整串 24 码全黄）。
  function renderM24(modules) {
    renderHistory("m24", modules.ma24, function (row) { return selectedCodes(row, 24); }, function (row) {
      var shown = numbers(row).slice(0, 24);
      var code = specialAttributes(row).code;
      var hit = hitWhenCorrect(row, inList(shown, code));
      return { hit: hit, text: resultText(row), html: highlightOnly(shown, hit ? code : "", ".") };
    });
  }
  // 大小中特：候选项是维度标签「大/小」（01-24 为小、25-49 为大），只点亮与特码大小一致的那一个。
  function renderDaxiao(modules) {
    renderHistory("daxiao", modules.daxiao, function (row) { return labels(row).slice(0, 1).join(""); }, function (row) {
      var shown = labels(row).slice(0, 1);
      var digits = String(specialParts(row).code || "").replace(/[^0-9]/g, "");
      var size = digits ? (parseInt(digits, 10) >= 25 ? "大" : "小") : "";
      var hit = hitWhenCorrect(row, inList(shown, size));
      return { hit: hit, text: resultText(row), html: highlightOnly(shown, hit ? size : "") };
    });
  }
  function renderJiaye(modules) { renderHistory("jiaye", modules.title_14, domesticWild, domesticWildOutcome); }
  // 七肖中特：只展示 9 肖的前 7 肖 —— 判定只用这 7 肖（第 8、9 肖被裁掉，不算候选）。
  function renderQixiao(modules) {
    renderHistory("qixiao", modules["9xzt"], function (row) { return xiaoCodes(row, 7); }, function (row) {
      var shown = labels(row).slice(0, 7);
      var zodiac = specialParts(row).zodiac;
      var hit = inList(shown, zodiac);
      return { hit: hit, html: highlightOnly(shown, hit ? zodiac : "", "") };
    });
  }
  // 「候选 = 生肖字」类模块（四肖四码 / 九肖中特 / 单双四肖 / 绝杀四肖）逐字点亮：
  // 只给等于本期**特肖**的那一个字打标记，标签（如「四肖资料：」）永不黄底
  // （旧写法给整个内容槽位打标记，`display:block` 下等于整行黄底）。
  function zodiacItemsOutcome(row, count, label) {
    var shown = labels(row).slice(0, count);
    var zodiac = specialParts(row).zodiac;
    var hit = hitWhenCorrect(row, inList(shown, zodiac));
    var body = highlightOnly(shown, hit ? zodiac : "");
    return { hit: hit, text: resultText(row), html: label ? contentWithLabel(label, body) : body };
  }
  // 「候选 = 尾数」类模块（平特一尾 / 7尾中特）逐尾点亮：只给等于**特码尾**的那一个尾数打标记。
  function tailsOutcome(row) {
    var shown = tailLabels(row);
    var tail = specialAttributes(row).tail;
    var hit = hitWhenCorrect(row, inList(shown, tail));
    return { hit: hit, text: resultText(row), html: contentWithLabel("五尾", highlightOnly(shown, hit ? tail : "", " ")) };
  }
  // 成语平特（琴棋书画）：候选项是艺名（琴/棋/书/画），命中的艺名 = 其生肖组含本期特肖。
  // canonical row 的 `raw.title` / `raw.content` 与后端 `format_qinqi_content` 同源
  // （title = 选中的艺名，content = 按艺名顺序**等长展开**的生肖），按等分块还原每个艺名的
  // 生肖组；拿不到这两列时不点亮（宁可零黄底，也不整串黄）。
  function qinqiGroupMap(row) {
    var map = {};
    var titles = String(rawField(row, "title") == null ? "" : rawField(row, "title"))
      .split(/[,，]/).map(function (value) { return value.trim(); }).filter(Boolean);
    var zodiacs = String(rawField(row, "content") == null ? "" : rawField(row, "content"))
      .split(/[,，]/).map(function (value) { return value.trim(); }).filter(Boolean);
    if (!titles.length || !zodiacs.length || zodiacs.length % titles.length !== 0) return map;
    var size = zodiacs.length / titles.length;
    titles.forEach(function (name, index) { map[name] = zodiacs.slice(index * size, (index + 1) * size); });
    return map;
  }
  function chengyuOutcome(row) {
    var shown = labels(row).slice(0, 9);
    var zodiac = specialParts(row).zodiac;
    var groups = qinqiGroupMap(row);
    var hitName = zodiac ? shown.filter(function (name) {
      return (groups[name] || []).indexOf(zodiac) >= 0;
    })[0] || "" : "";
    var hit = hitWhenCorrect(row, Boolean(hitName));
    return {
      hit: hit,
      text: resultText(row),
      html: contentWithLabel("琴棋书画", highlightOnly(shown, hit ? hitName : ""))
    };
  }
  function renderJiaye4xiao(modules) {
    renderHistory("jiaye4xiao", modules.sixiao_sima,
      function (row) { return contentWithLabel("四肖四码", xiaoCodes(row, 4)); },
      function (row) { return zodiacItemsOutcome(row, 4, "四肖四码"); });
  }
  // 黄金六肖：展示 = 九肖资料前 6 肖 + 平特一肖资料前 1 肖（两路候选，任一命中即「对」，
  // 只点亮真正命中的那一路的那一项）。旧写法只拿九肖那一份的 isCorrect，平特一肖命中时显示错。
  function renderGold6xiao(modules) {
    var nine = distinctRows(modules["9xzt"]), flat = distinctRows(modules.pt1xiao);
    historyRows(section("gold6xiao")).forEach(function (row, index) {
      var source = nine[index] || flat[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      var six = labels(nine[index]).slice(0, 6), one = labels(flat[index]).slice(0, 1);
      var zodiac = specialParts(source).zodiac;
      // 九肖资料 = 「九肖中特」：特肖落在展示的 6 肖里即命中（中特口径）。
      var sixHit = inList(six, zodiac);
      // 平特一肖资料 = **平特**：开奖七个号码的生肖里任一命中候选肖即命中（不是只看特肖）。
      var drawnZodiacList = drawnZodiacs(flat[index] || source);
      var oneHitToken = one.filter(function (zodiacName) {
        return drawnZodiacList.indexOf(zodiacName) !== -1;
      })[0] || "";
      var oneHit = Boolean(oneHitToken);
      writeRow(
        row,
        issueOf(source) + "期",
        "九肖资料：" + six.join("") + "；平特一肖资料：" + one.join(""),
        displayedResultText(source, sixHit || oneHit),
        false,
        segmentLines([
          "九肖资料：" + highlightOnly(six, sixHit ? zodiac : "", ""),
          // 只点亮真正命中的那一项：平特一肖命中的可能是**平码**，不能拿特肖去比对。
          "平特一肖资料：" + highlightOnly(one, oneHitToken)
        ])
      );
    });
  }
  function renderPt1wei(modules) { renderHistory("pt1wei", modules.title_66, function (row) { return contentWithLabel("五尾", tailLabels(row).join(" ")); }, tailsOutcome); }
  // 赢钱12码：只展示精选22码的前 12 码 —— 判定只用这 12 码（第 13-22 码被裁掉）。
  function renderWinner12(modules) {
    renderHistory("winner12", modules.selected_22_codes, function (row) { return contentWithLabel("精选22码", selectedCodes(row, 12)); }, function (row) {
      var shown = numbers(row).slice(0, 12);
      var code = specialParts(row).code;
      var hit = inList(shown, code);
      return { hit: hit, html: contentWithLabel("精选22码", highlightOnly(shown, hit ? code : "", ".")) };
    });
  }
  function renderJiuxiao(modules) {
    renderHistory("jiuxiao", modules["9xzt"], function (row) { return xiaoCodes(row, 9); },
      function (row) { return zodiacItemsOutcome(row, 9, ""); });
  }
  // 复试连码：展示 = 24码资料前 12 码 + 四段资料的四段（两路候选，任一命中即「对」）。
  function renderLianma(modules) {
    var code = distinctRows(modules.ma24), segment = distinctRows(modules.siduanzhongte);
    historyRows(section("lianma")).forEach(function (row, index) {
      var source = code[index] || segment[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      var shownCodes = numbers(code[index]).slice(0, 12);
      var shownSegments = groupLabels(segment[index]);
      var attributes = specialAttributes(source);
      var codeHit = inList(shownCodes, attributes.code);
      var segmentHit = inList(shownSegments, attributes.segment);
      writeRow(
        row,
        issueOf(source) + "期",
        "24码资料：" + shownCodes.join(".") + "；四段资料：" + shownSegments.join(" "),
        displayedResultText(source, codeHit || segmentHit),
        false,
        segmentLines([
          "24码资料：" + highlightOnly(shownCodes, codeHit ? attributes.code : "", "."),
          "四段资料：" + highlightOnly(shownSegments, segmentHit ? attributes.segment : "", " ")
        ])
      );
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
  // 单双中特：一行两路候选（合数单双 + 合数大小），任一维度命中即「对」，
  // 只点亮命中的那一个维度。旧写法只取第一份资料（title_132）的 isCorrect，
  // 于是「合数大小命中、合数单双没中」的期显示错。
  function renderDanshuang(modules) {
    var parity = distinctRows(modules.title_132), size = distinctRows(modules.title_279);
    historyRows(section("danshuang")).forEach(function (row, index) {
      var source = parity[index] || size[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      var parityShown = vocabularyLabels(parity[index], ["合单", "合双"]);
      var sizeShown = vocabularyLabels(size[index], ["合数大", "合数小"]);
      var attributes = specialAttributes(source);
      var parityHit = inList(parityShown, attributes.combinedParity);
      var sizeHit = inList(sizeShown, attributes.combinedSize);
      writeRow(
        row,
        issueOf(source) + "期",
        "合数单双资料：" + parityShown.join("") + "；合数大小资料：" + sizeShown.join(""),
        displayedResultText(source, parityHit || sizeHit),
        false,
        segmentLines([
          "合数单双资料：" + highlightOnly(parityShown, parityHit ? attributes.combinedParity : "", ""),
          "合数大小资料：" + highlightOnly(sizeShown, sizeHit ? attributes.combinedSize : "")
        ])
      );
    });
  }
  function renderDssx(modules) {
    renderHistory("dssx", modules.danshuang4xiao, function (row) { return xiaoCodes(row, 8); },
      function (row) { return zodiacItemsOutcome(row, 8, ""); });
  }
  // 红蓝绿肖：一行两路候选（双波 + 一波），任一维度命中即「对」，只点亮命中的那一项。
  // 双波只展示 3 波里的 2 波：命中落在被裁掉的第 3 波时，只有一波那一路能救回来。
  function renderHblvxiao(modules) {
    var doubleWave = distinctRows(modules.shuangbo), singleWave = distinctRows(modules.title_143);
    historyRows(section("hblvxiao")).forEach(function (row, index) {
      var source = doubleWave[index] || singleWave[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      var doubleShown = vocabularyLabels(doubleWave[index], WAVE_LABELS).slice(0, 2);
      var singleShown = vocabularyLabels(singleWave[index], WAVE_LABELS).slice(0, 1);
      var attributes = specialAttributes(source);
      var doubleHit = inList(doubleShown, attributes.wave);
      var singleHit = inList(singleShown, attributes.wave);
      writeRow(
        row,
        issueOf(source) + "期",
        "双波资料：" + doubleShown.join(" ") + "；一波资料：" + singleShown.join(""),
        displayedResultText(source, doubleHit || singleHit),
        false,
        segmentLines([
          "双波资料：" + highlightOnly(doubleShown, doubleHit ? attributes.wave : "", " "),
          "一波资料：" + highlightOnly(singleShown, singleHit ? attributes.wave : "")
        ])
      );
    });
  }
  function headLabels(row, count) { var values = groupLabels(row); return (values.length ? values : labels(row)).slice(0, count); }
  function renderSantou(modules) {
    renderHistory("santou", modules["3tou"], function (row) { return headLabels(row, 3).join("."); }, function (row) {
      var shown = headLabels(row, 3);
      var head = specialAttributes(row).head;
      var hit = hitWhenCorrect(row, inList(shown, head));
      return { hit: hit, text: resultText(row), html: highlightOnly(shown, hit ? head : "", ".") };
    });
  }
  function renderQiw(modules) { renderHistory("qiw", modules.title_66, function (row) { return contentWithLabel("五尾", tailLabels(row).join(" ")); }, tailsOutcome); }
  function renderKill4xiao(modules) {
    renderHistory("kill4xiao", modules.sixiao_sima,
      function (row) { return contentWithLabel("四肖", xiaoCodes(row, 4)); },
      function (row) { return zodiacItemsOutcome(row, 4, "四肖"); });
  }
  // 绝杀三尾：只展示五尾资料的前 3 尾 —— 判定只用这 3 尾（第 4、5 尾被裁掉）。
  function renderKill3wei(modules) {
    renderHistory("kill3wei", modules.title_66, function (row) { return contentWithLabel("五尾", tailLabels(row).slice(0, 3).join(" ")); }, function (row) {
      var shown = tailLabels(row).slice(0, 3);
      var tail = specialAttributes(row).tail;
      var hit = inList(shown, tail);
      return { hit: hit, html: contentWithLabel("五尾", highlightOnly(shown, hit ? tail : "", " ")) };
    });
  }
  function renderChengyu(modules) {
    renderHistory("chengyu", modules.qinqi, function (row) { return contentWithLabel("琴棋书画", xiaoCodes(row, 9)); }, chengyuOutcome);
  }
  // 双波中特：候选项是波色标签（同一行展示 2 波）——逐波点亮，只给等于**特码波色**的那一个打标记。
  // 波色候选统一走 `vocabularyLabels`（兼容 tokens 被拆成单字 `红`/`波` 的历史形态，
  // 与 `#hblvxiao` 同口径），旧写法用 `labels(row).slice(0,2)` 会把单字形态显示成「红波」。
  function renderShuangbo(modules) {
    renderHistory("shuangbo", modules.shuangbo, function (row) { return vocabularyLabels(row, WAVE_LABELS).slice(0, 2).join(""); }, function (row) {
      var shown = vocabularyLabels(row, WAVE_LABELS).slice(0, 2);
      var wave = specialAttributes(row).wave;
      var hit = hitWhenCorrect(row, inList(shown, wave));
      return { hit: hit, text: resultText(row), html: highlightOnly(shown, hit ? wave : "") };
    });
  }
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
  // 平特5不中：只展示精选22码的前 5 码 —— 判定只用这 5 码（第 6-22 码被裁掉）。
  // 2026-09-30（站点负责人确认）：按**不中语义 + 平特口径**判定 —— 这 5 个号码在
  // 本期**七个开奖号码**里**一个都不出现**才算「对」；出现任意一个即「错」。
  // 排除型没有可点亮的命中项（「对」= 开奖里没有候选，「错」= 候选落在开奖里但 S3 禁止标黄），
  // 因此整块零黄底。
  // 行内没有 `res_code` 时 `drawnCodes` 回退特码，判定至少不弱于「特码不中」。
  function renderFiveNoHit(modules) {
    renderHistory("five_no_hit", modules.selected_22_codes, function (row) { return contentWithLabel("五码", selectedCodes(row, 5)); }, function (row) {
      var shown = numbers(row).slice(0, 5);
      var drawn = drawnCodes(row);
      var appeared = shown.filter(function (number) { return drawn.indexOf(number) !== -1; });
      var hit = drawn.length > 0 && appeared.length === 0;
      return { hit: hit, html: contentWithLabel("五码", shown.map(escapeHtml).join(".")) };
    });
  }
  // 综合绝杀：四路候选（绝杀三肖 / 五尾 / 三头 / 合数单双）分别按**展示出来的那一份**复算，
  // 任一路命中即整格「对」，并且只点亮真正命中的那一项。旧实现只取第一个可用 source 的
  // isCorrect（即绝杀三肖那一路），「五尾/三头/合数单双命中而绝杀三肖没中」的期一律显示错。
  // 绝杀三肖是排除型玩法（backend `juesha3xiao`：hit_checker=excludes_hit）：特肖**不在**
  // 展示的三肖里才算这一路杀中；杀中没有可点亮的候选项（与 twbst528「杀中不给标记」一致）。
  function renderCompositeKill(modules) {
    var kill = distinctRows(modules.juesha3xiao);
    var tail = distinctRows(modules.title_66);
    var head = distinctRows(modules["3tou"]);
    var parity = distinctRows(modules.title_132);
    historyRows(section("composite_kill")).forEach(function (row, index) {
      var source = kill[index] || tail[index] || head[index] || parity[index];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      var killShown = labels(kill[index]).slice(0, 3);
      var tailShown = tailLabels(tail[index]);
      var headShown = headLabels(head[index], 3);
      var parityShown = vocabularyLabels(parity[index], ["合单", "合双"]);
      var attributes = specialAttributes(source);
      var killHit = Boolean(attributes.zodiac) && !inList(killShown, attributes.zodiac);
      var tailHit = inList(tailShown, attributes.tail);
      var headHit = inList(headShown, attributes.head);
      var parityHit = inList(parityShown, attributes.combinedParity);
      writeRow(
        row,
        issueOf(source) + "期",
        "绝杀三肖：" + killShown.join("") + "；五尾资料：" + tailShown.join(" ") +
          "；三头资料：" + headShown.join(" ") + "；合数单双：" + parityShown.join(""),
        displayedResultText(source, killHit || tailHit || headHit || parityHit),
        false,
        segmentLines([
          "绝杀三肖：" + escapeHtml(killShown.join("")),
          "五尾资料：" + highlightOnly(tailShown, tailHit ? attributes.tail : "", " "),
          "三头资料：" + highlightOnly(headShown, headHit ? attributes.head : "", " "),
          "合数单双：" + highlightOnly(parityShown, parityHit ? attributes.combinedParity : "")
        ])
      );
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
  // 特码开奖结果（56 行 = 8 组 × 7 格）：每组用同一份 9 肖 / 24 码，但 7 个格子只展示其中
  // 前 8/5/3/1 肖与前 10/6/1 码 —— 判定必须逐格用**该格展示的那几个候选**，
  // 旧写法 7 个格子共用整份 9 肖 / 24 码的 isCorrect（命中落在被裁掉的部分就「显示对却没有黄底」）。
  function renderTopXiaoCode(modules) {
    var xiao = distinctRows(modules["9xzt"]), ma = distinctRows(modules.ma24), names = ["八肖", "五肖", "三肖", "一肖", "10码", "6码", "1码"];
    var headerIssues = document.querySelectorAll("[data-prediction-draw-issue]");
    var headerResults = document.querySelectorAll("[data-prediction-draw-result]");
    Array.prototype.forEach.call(headerIssues, function (node, index) { var source = xiao[index] || ma[index]; node.textContent = source ? issueOf(source) + "期" : ""; if (headerResults[index]) headerResults[index].textContent = source ? resultText(source) : ""; });
    historyRows(section("top_xiao_code")).forEach(function (row, index) {
      var group = Math.floor(index / 7), slot = index % 7, source = slot < 4 ? xiao[group] : ma[group];
      if (!source) return writeRow(row, "", "暂无后端资料", "", false);
      var isXiao = slot < 4;
      var shown = isXiao ? labels(source).slice(0, [8, 5, 3, 1][slot]) : numbers(source).slice(0, [10, 6, 1][slot - 4]);
      var target = isXiao ? specialParts(source).zodiac : specialParts(source).code;
      var hit = inList(shown, target);
      var joiner = isXiao ? "" : ".";
      var content = shown.join(joiner);
      writeRow(
        row,
        issueOf(source) + "期 " + names[slot],
        content || "暂无后端资料",
        displayedResultText(source, hit),
        false,
        content ? highlightOnly(shown, hit ? target : "", joiner) : ""
      );
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
