(function (window) {
  "use strict";

  var siteConfig = Object.freeze({
    siteKey: "twjsz666",
    siteName: "台湾金手指",
    siteDomain: "www.twjsz666.com",
    lotteries: Object.freeze([
      Object.freeze({ key: "taiwan", lotteryType: 3, label: "台湾彩", titlePrefix: "台湾精选", titleRegionPrefix: "台湾" }),
      Object.freeze({ key: "macau", lotteryType: 2, label: "澳门彩", titlePrefix: "澳门精选", titleRegionPrefix: "澳门" }),
      Object.freeze({ key: "hong-kong", lotteryType: 1, label: "香港彩", titlePrefix: "香港精选", titleRegionPrefix: "香港" })
    ])
  });

  window.Twjsz666SiteConfig = siteConfig;
})(window);
