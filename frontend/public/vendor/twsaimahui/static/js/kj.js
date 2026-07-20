(function (window, document) {
  "use strict";

  function gameForType(type) {
    return type === 2 ? "macau" : type === 1 ? "hongkong" : "taiwan";
  }

  function render() {
    document.write(
      '<div class="KJ-TabBox vendor-shared-kj-tabs">' +
        '<ul>' +
          '<li data-lottery-type="3">台湾彩</li>' +
          '<li data-lottery-type="2">澳门彩</li>' +
          '<li data-lottery-type="1">香港彩</li>' +
        '</ul>' +
        '<div class="vendor-shared-draw-mount"></div>' +
      '</div>'
    );
  }

  render();
  document.addEventListener("DOMContentLoaded", function () {
    var root = document.querySelector(".vendor-shared-kj-tabs");
    if (!root) return;
    function updateActive() {
      var selected = window.localStorage && window.localStorage.getItem("selectedLottery") || "taiwan";
      root.querySelectorAll("li").forEach(function (item) {
        item.classList.toggle("cur", gameForType(Number(item.dataset.lotteryType)) === selected);
      });
    }
    root.addEventListener("click", function (event) {
      var tab = event.target.closest("li[data-lottery-type]");
      if (!tab) return;
      var key = gameForType(Number(tab.dataset.lotteryType));
      if (window.localStorage) window.localStorage.setItem("selectedLottery", key);
      updateActive();
      window.dispatchEvent(new CustomEvent("lottery:game-changed", { detail: { lottery_type: Number(tab.dataset.lotteryType) } }));
    });
    updateActive();
  });
})(window, document);
