(function (window, document) {
  "use strict";

  function text(value) { return value == null ? "" : String(value); }
  function lotteryType() {
    var selected = window.localStorage && window.localStorage.getItem("selectedLottery");
    return selected === "macau" ? 2 : selected === "hongkong" ? 1 : 3;
  }
  function selector(config, key) { return config.bridge.runtime[key] || ""; }
  function target(config, key) {
    var value = selector(config, key);
    return value ? document.querySelector(value) : null;
  }
  function node(tag, className, value) {
    var element = document.createElement(tag);
    if (className) element.className = className;
    if (value != null) element.textContent = text(value);
    return element;
  }
  function clear(element) { while (element && element.firstChild) element.removeChild(element.firstChild); }
  function mergeDraw(previous, incoming) {
    if (window.LotterySiteDrawState && typeof window.LotterySiteDrawState.merge === "function") return window.LotterySiteDrawState.merge(previous, incoming);
    if (!incoming) return previous || null;
    var issue = text(incoming.current_issue || incoming.issue).trim();
    var oldIssue = text(previous && (previous.current_issue || previous.issue)).trim();
    if (oldIssue && issue && oldIssue !== issue) return Object.assign({}, incoming, { balls: (incoming.balls || []).slice() });
    var balls = previous && Array.isArray(previous.balls) ? previous.balls.slice() : [];
    (incoming.balls || []).forEach(function (ball, index) { if (ball && text(ball.value).trim()) balls[index] = ball; });
    return Object.assign({}, previous || {}, incoming, { balls: balls });
  }

  function renderDraw(config, draw, loading) {
    var mount = target(config, "draw_selector");
    if (!mount) return;
    clear(mount);
    var box = node("section", "vendor-shared-draw");
    var title = node("div", "vendor-shared-draw-title", draw ? "第 " + text(draw.current_issue) + " 期开奖号码" : "开奖资料");
    box.appendChild(title);
    var balls = node("div", "vendor-shared-draw-balls");
    if (draw && draw.balls && draw.balls.length) {
      draw.balls.forEach(function (ball) {
        var ballNode = node("span", "vendor-shared-ball vendor-shared-ball-" + (ball.color || "red") + (ball.is_special ? " is-special" : ""));
        ballNode.appendChild(node("b", "vendor-shared-ball-value", ball.value));
        ballNode.appendChild(node("small", "vendor-shared-ball-zodiac", ball.zodiac));
        balls.appendChild(ballNode);
      });
    } else {
      balls.appendChild(node("span", "vendor-shared-loading", loading ? "开奖数据加载中..." : "暂无开奖结果"));
    }
    box.appendChild(balls);
    if (draw && draw.next_issue) box.appendChild(node("div", "vendor-shared-next", "下期：" + text(draw.next_issue)));
    mount.appendChild(box);
  }

  function renderPredictions(config, modules, loading, error) {
    var mount = target(config, "prediction_selector");
    if (!mount) return;
    clear(mount);
    var root = node("section", "vendor-shared-predictions");
    root.appendChild(node("h2", "vendor-shared-predictions-title", "精选预测资料"));
    if (error) root.appendChild(node("p", "vendor-shared-error", "资料暂时无法刷新，正在保留最近可用内容。"));
    if (loading && !modules) root.appendChild(node("p", "vendor-shared-loading", "预测资料加载中..."));
    (modules || []).forEach(function (module) {
      var card = node("article", "vendor-shared-prediction-card");
      card.appendChild(node("h3", "vendor-shared-prediction-title", module.title || module.moduleKey));
      var rows = node("div", "vendor-shared-prediction-rows");
      (module.rows || []).slice(0, 3).forEach(function (row) {
        var line = node("p", "vendor-shared-prediction-row");
        line.appendChild(node("strong", "", text(row.issue) + "期："));
        var groups = row.prediction && row.prediction.groups || [];
        var tokens = groups.length
          ? groups.map(function (group) { return group.tokens.join(" "); }).join(" / ")
          : ((row.prediction && row.prediction.tokens || []).join(" ") || (row.prediction && row.prediction.text));
        line.appendChild(node("span", "", tokens || "待发布"));
        rows.appendChild(line);
      });
      if (!rows.childNodes.length) rows.appendChild(node("p", "vendor-shared-prediction-row", "暂无资料"));
      card.appendChild(rows);
      root.appendChild(card);
    });
    mount.appendChild(root);
  }

  function renderFooter(config) {
    var mount = target(config, "footer_selector");
    if (!mount) return;
    clear(mount);
    var footer = node("footer", "vendor-shared-footer");
    var footerConfig = config.brand.footer || {};
    (footerConfig.imageUrls || []).forEach(function (url) {
      var image = document.createElement("img");
      image.src = url;
      image.alt = config.brand.siteName || "";
      image.loading = "lazy";
      footer.appendChild(image);
    });
    footer.appendChild(node("p", "vendor-shared-footer-copyright", footerConfig.copyright || ""));
    (footerConfig.contacts || []).forEach(function (contact) {
      var link = document.createElement("a");
      link.href = contact.href;
      link.textContent = contact.label;
      footer.appendChild(link);
    });
    mount.appendChild(footer);
  }

  function enableStickyNavigation(config) {
    var navigation = target(config, "navigation_selector");
    if (!navigation || navigation.dataset.vendorSticky === "1") return;
    navigation.dataset.vendorSticky = "1";
    var spacer = document.createElement("div");
    spacer.className = "vendor-shared-nav-spacer";
    navigation.parentNode.insertBefore(spacer, navigation);
    function refresh() { spacer.style.height = navigation.offsetHeight + "px"; }
    navigation.classList.add("vendor-shared-nav-fixed");
    refresh();
    window.addEventListener("resize", refresh);
    navigation.addEventListener("click", function (event) {
      var link = event.target.closest && event.target.closest("a[href^='#']");
      if (!link) return;
      var destination = document.querySelector(link.getAttribute("href"));
      if (!destination) return;
      event.preventDefault();
      window.scrollTo({ top: Math.max(0, destination.getBoundingClientRect().top + window.scrollY - navigation.offsetHeight - 8), behavior: "smooth" });
    });
  }

  function installStyles() {
    if (document.getElementById("vendor-shared-runtime-style")) return;
    var style = document.createElement("style");
    style.id = "vendor-shared-runtime-style";
    style.textContent = ".vendor-shared-nav-fixed{position:fixed!important;top:0;left:0;right:0;z-index:10001}.vendor-shared-kj-tabs{height:auto;overflow:visible;color:#333;background:#fff;font-family:Arial,sans-serif}.vendor-shared-kj-tabs ul{display:flex;list-style:none;margin:0;padding:8px;border-bottom:2px solid #fff}.vendor-shared-kj-tabs li{flex:1;margin:0 4px;padding:6px;text-align:center;border-radius:4px;background:#eee;cursor:pointer}.vendor-shared-kj-tabs li.cur{color:#fff;background:#1fb61d}.vendor-shared-kj-tabs li:nth-child(2).cur{background:#e71607}.vendor-shared-kj-tabs li:nth-child(3).cur{background:#2389e9}.vendor-shared-draw,.vendor-shared-predictions,.vendor-shared-footer{max-width:800px;margin:8px auto;text-align:center}.vendor-shared-draw{padding:8px;background:#fff;border:1px solid #ddd}.vendor-shared-draw-title,.vendor-shared-predictions-title{font-weight:bold;color:#fff;background:#0a5cda;padding:7px}.vendor-shared-draw-balls{display:flex;justify-content:center;gap:6px;padding:8px;flex-wrap:wrap}.vendor-shared-ball{display:inline-flex;flex-direction:column;justify-content:center;width:38px;height:38px;border-radius:50%;color:#fff}.vendor-shared-ball-red{background:#d71920}.vendor-shared-ball-blue{background:#1677d2}.vendor-shared-ball-green{background:#1ca64c}.vendor-shared-ball.is-special{box-shadow:0 0 0 3px #f4d000}.vendor-shared-ball-zodiac{font-size:10px}.vendor-shared-prediction-card{border:1px solid #ddd;background:#fff;margin:8px 0}.vendor-shared-prediction-title{color:#333;background:#fff6bf}.vendor-shared-prediction-row{padding:8px;border-top:1px solid #eee}.vendor-shared-loading{padding:12px;color:#777}.vendor-shared-error{padding:8px;color:#c00}.vendor-shared-footer img{display:block;width:100%;margin:8px 0}.vendor-shared-footer a{display:inline-block;margin:0 8px}.vendor-shared-footer-copyright{padding:8px;color:#666}";
    document.head.appendChild(style);
  }

  function mount(options) {
    var bridge = options && options.bridge || window.LotterySiteBridge;
    if (!bridge || window.LotterySiteRuntimeMounted) return;
    window.LotterySiteRuntimeMounted = true;
    var activationEpoch = 0;
    var drawState = null;
    function scheduleIdle(callback) {
      if (typeof window.requestIdleCallback === "function") return window.requestIdleCallback(callback, { timeout: 120 });
      return window.setTimeout(callback, 0);
    }
    function activate(config) {
      var epoch = ++activationEpoch;
      drawState = null;
      installStyles();
      enableStickyNavigation(config);
      renderFooter(config);
      var query = "lottery_type=" + lotteryType();
      if (config.bridge.auto_load.draw) {
        renderDraw(config, null, true);
        bridge.getDraw(query).then(function (draw) {
          if (epoch !== activationEpoch) return;
          drawState = mergeDraw(drawState, draw);
          renderDraw(config, drawState, false);
        }).catch(function () { if (epoch === activationEpoch) renderDraw(config, null, false); });
      }
      if (config.bridge.auto_load.prediction) {
        renderPredictions(config, null, true, false);
        bridge.getPredictionModules(query).then(function (data) {
          if (epoch !== activationEpoch) return;
          scheduleIdle(function () {
            if (epoch === activationEpoch) renderPredictions(config, data.canonical_modules || [], false, false);
          });
        }).catch(function () {
          if (epoch === activationEpoch) scheduleIdle(function () { if (epoch === activationEpoch) renderPredictions(config, null, false, true); });
        });
      }
    }
    function activateWhenReady(config) {
      function start() {
        activate(config);
        window.addEventListener("lottery:game-changed", function () { activate(config); });
      }
      if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
      else start();
    }
    bridge.ready.then(activateWhenReady);
  }

  window.LotterySiteRuntime = { mount: mount };
})(window, document);
