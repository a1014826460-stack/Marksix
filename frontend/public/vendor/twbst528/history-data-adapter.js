(function (window) {
  "use strict";

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

  function clearElement(element) {
    textNodes(element).forEach(function (node) { node.nodeValue = ""; });
  }

  function historyItems(payload) {
    return Array.isArray(payload && payload.items) ? payload.items : [];
  }

  function renderItem(element, item) {
    if (!item) {
      clearElement(element);
      return;
    }
    writeLeaf(element.querySelector("h3"), "第" + String(item.issue || "") + "期开奖结果");
    writeLeaf(element.querySelector(".time"), item.date || "");
    var balls = (Array.isArray(item.balls) ? item.balls : []).slice(0, 6);
    var special = item.specialBall || null;
    Array.prototype.forEach.call(element.querySelectorAll("li"), function (node, index) {
      if (index === 6) {
        writeLeaf(node.querySelector(".jia"), "+");
        return;
      }
      var ball = index === 7 ? special : balls[index];
      if (!ball) {
        clearElement(node);
        return;
      }
      node.className = "ball-" + (ball.color || "red");
      writeLeaf(node.querySelector(".num"), String(ball.value || "").padStart(2, "0"));
      writeLeaf(node.querySelector(".content"), ball.zodiac || "");
    });
  }

  function initialize() {
    var list = window.document.querySelector("#lishi");
    if (!list) return;
    var config = window.Twbst528SiteConfig || {};
    window.document.title = String(config.siteName || "开奖") + "开奖记录";
    writeLeaf(window.document.querySelector(".location_to"), "【首页" + String(config.siteName || "") + "】 开奖历史记录");
    window.fetch("/api/draw-history?lottery_type=3&page=1&page_size=20", {
      credentials: "same-origin", headers: { Accept: "application/json" }
    }).then(function (response) {
      if (!response.ok) throw new Error("request failed");
      return response.json();
    }).then(function (payload) {
      Array.prototype.forEach.call(list.querySelectorAll(".open-item"), function (element, index) {
        renderItem(element, historyItems(payload)[index]);
      });
    }).catch(function () {
      Array.prototype.forEach.call(list.querySelectorAll(".open-item"), function (element) { clearElement(element); });
    });
  }

  if (window.document.readyState === "loading") window.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})(window);
