import { defineVendorSiteManifest } from "@/lib/site-platform/site-manifest"

export default defineVendorSiteManifest({
  identity: { siteKey: "twwanli", domains: ["www.twwanli.com", "twwanli.com"], routePath: "/twwanli", siteId: 12, webId: 12, defaultLotteryType: 3 },
  frontend: {
    renderMode: "iframe-vendor", vendorIndexPath: "/vendor/twwanli/index.html", legacyPublicBasePath: "/vendor/twwanli",
    defaultGame: "taiwan", forumTitle: "台湾万利网", metadataTitle: "台湾万利网", metadataDescription: "台湾万利网",
    faviconPath: "/vendor/twwanli/static/picture/18d310a363f7a6a0d82a09afd2953d21.jpg",
  },
  bridge: {
    api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" }, autoLoad: { draw: true, prediction: true },
    predictionModuleKeys: ["title_14", "juesha3xiao", "9xzt", "selected_22_codes", "shuangbo", "sixiao_sima", "daxiao", "title_66", "ma24", "danshuang4xiao", "siduanzhongte", "title_143", "title_5", "3tou", "title_279", "pt1xiao", "pt1wei", "sitouzhongte", "title_132", "qinqi", "3hang", "6xzt"],
    runtime: { drawSelector: ".haoju iframe[src='kai.html']", predictionSelector: "[data-prediction-section]", footerSelector: "#legacy-attribute-anchor", navigationSelector: ".nav", legacyPredictionScripts: "enabled" },
  },
  brand: { siteName: "台湾万利网", logoUrl: "/vendor/twwanli/static/picture/18d310a363f7a6a0d82a09afd2953d21.jpg", faviconUrl: "/vendor/twwanli/static/picture/18d310a363f7a6a0d82a09afd2953d21.jpg", navigation: [], footer: { copyright: "台湾万利网" } },
  security: { externalScriptOrigins: ["https://static.cloudflareinsights.com"], externalNavigationOrigins: ["https://www.sharecy.net", "https://xgg3.cp567.cc", "http://xg8388.com"] },
})
