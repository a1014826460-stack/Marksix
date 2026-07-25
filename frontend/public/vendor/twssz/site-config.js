(function (window) {
  "use strict";

  // The vendor shell and its draw iframe read the same immutable site identity.
  window.TwsszSiteConfig = Object.freeze({
    siteKey: "twssz",
    siteName: "台湾神算子",
    siteDomain: "twssz.com",
    frontendBasePath: "/twssz",
    drawFramePath: "/vendor/shengshi8800/kj/local.html",
    lotteries: Object.freeze([
      Object.freeze({ key: "taiwan", lotteryType: 3, label: "台湾彩", titlePrefix: "台湾精选", titleRegionPrefix: "台湾" }),
      Object.freeze({ key: "macau", lotteryType: 2, label: "澳门彩", titlePrefix: "澳门精选", titleRegionPrefix: "澳门" }),
      Object.freeze({ key: "hong-kong", lotteryType: 1, label: "香港彩", titlePrefix: "香港精选", titleRegionPrefix: "香港" })
    ])
  });
})(window);
