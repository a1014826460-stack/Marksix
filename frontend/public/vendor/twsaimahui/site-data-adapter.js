(function (window) {
  "use strict";

  var client = window.LotterySiteDataClient.create({ siteKey: "twsaimahui" });

  function announce(resource, result) {
    if (typeof window.CustomEvent !== "function" || typeof window.dispatchEvent !== "function") return result;
    window.dispatchEvent(new window.CustomEvent("site-data:ready", {
      detail: { siteKey: "twsaimahui", resource: resource, state: result.state }
    }));
    return result;
  }

  window.TwsaimahuiSiteData = {
    preloadDraw: function () {
      return client.loadDraw({ lotteryType: 3 }).then(function (result) {
        return announce("draw", result);
      });
    },
    preloadPredictions: function () {
      return client.loadPredictions({ lotteryType: 3, historyLimit: 8 }).then(function (result) {
        return announce("predictions", result);
      });
    }
  };

  window.setTimeout(function () {
    window.TwsaimahuiSiteData.preloadDraw();
    window.TwsaimahuiSiteData.preloadPredictions();
  }, 0);
})(window);
