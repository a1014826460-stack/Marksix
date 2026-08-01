import { defineVendorSiteManifest } from "@/lib/site-platform/site-manifest"

export default defineVendorSiteManifest({
  identity: { siteKey: "twsyw", domains: ["www.twsyw.com", "twsyw.com"], routePath: "/twsyw", siteId: 13, webId: 13, defaultLotteryType: 3 },
  frontend: {
    renderMode: "iframe-vendor", vendorIndexPath: "/vendor/twsyw/index.html", legacyPublicBasePath: "/vendor/twsyw",
    defaultGame: "taiwan", forumTitle: "台湾神预网", metadataTitle: "台湾神预网", metadataDescription: "台湾神预网",
    faviconPath: "/vendor/twsyw/static/picture/18d310a363f7a6a0d82a09afd2953d21.jpg",
  },
  bridge: {
    api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" }, autoLoad: { draw: true, prediction: true },
    predictionModuleKeys: ["title_14", "juesha3xiao", "9xzt", "selected_22_codes", "shuangbo", "sixiao_sima", "daxiao", "title_66", "ma24", "danshuang4xiao", "siduanzhongte", "title_143", "title_5", "3tou", "title_279", "pt1xiao", "title_132", "qinqi"],
    runtime: { drawSelector: ".haoju iframe[src='kai.html']", predictionSelector: "[data-prediction-section]", footerSelector: "#legacy-attribute-anchor", navigationSelector: ".nav", legacyPredictionScripts: "enabled" },
  },
  brand: { siteName: "台湾神预网", logoUrl: "/vendor/twsyw/static/picture/18d310a363f7a6a0d82a09afd2953d21.jpg", faviconUrl: "/vendor/twsyw/static/picture/18d310a363f7a6a0d82a09afd2953d21.jpg", navigation: [], footer: { copyright: "台湾神预网" } },
  security: { externalScriptOrigins: [], externalNavigationOrigins: ["https://www.sharecy.net", "https://xgg3.cp567.cc", "http://xg8388.com"] },
})
