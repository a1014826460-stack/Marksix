(function (window) {
  "use strict";
  var client = window.LotterySiteDataClient.create({ siteKey: "twcf888" });

  function preload(resource, query) {
    return client[resource === "draw" ? "loadDraw" : "loadPredictions"](query).then(function (result) {
      if (typeof window.CustomEvent === "function" && typeof window.dispatchEvent === "function") {
        window.dispatchEvent(new window.CustomEvent("site-data:ready", {
          detail: { siteKey: "twcf888", resource: resource, state: result.state }
        }));
      }
      return result;
    });
  }

  window.Twcf888SiteData = {
    preloadDraw: function () { return preload("draw", { lotteryType: 3 }); },
    preloadPredictions: function () { return preload("predictions", { lotteryType: 3, historyLimit: 8 }); }
  };

  window.setTimeout(function () {
    window.Twcf888SiteData.preloadDraw();
    window.Twcf888SiteData.preloadPredictions();
  }, 0);
})(window);
