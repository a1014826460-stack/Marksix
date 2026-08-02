import { defineVendorSiteManifest } from "@/lib/site-platform/site-manifest"

export default defineVendorSiteManifest({
  identity: { siteKey: "twssz", domains: ["www.twssz.com", "twssz.com"], routePath: "/twssz", siteId: 9, webId: 9, defaultLotteryType: 3 },
  frontend: { renderMode: "iframe-vendor", vendorIndexPath: "/vendor/twssz/index.html", legacyPublicBasePath: "/vendor/twssz", defaultGame: "taiwan", forumTitle: "台湾神算子", metadataTitle: "台湾神算子，算无遗漏", metadataDescription: "台湾神算子", faviconPath: "/vendor/twssz/static/file/favicon.ico" },
  bridge: {
    api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" },
    autoLoad: { draw: true, prediction: true },
    predictionModuleKeys: ["7xiao7ma", "sixiao_sima", "wensha10ma", "3zxt", "4xiao8ma", "pt2xiao", "title_66", "title_5", "ma24", "daxiao", "3tou", "juesha1wei", "juesha1xiao", "juesha2xiao", "jueshabanbo", "title_74", "danshuangtema", "juesha3xiao", "title_48", "9xzt", "pt1xiao", "shuangbo", "pt3xiao", "title_279", "sitouzhongte", "pt1wei", "9xiao12ma", "6xzt", "3hang", "title_132", "title_143", "sanxiao_siwei_xiao", "sanxiao_siwei_wei", "wuzhong5ma", "title_47", "sxztu"],
    runtime: { drawSelector: "iframe[src='kai.html']", predictionSelector: "#top_15", footerSelector: "#legacy-attribute-anchor", navigationSelector: "#nav2", legacyPredictionScripts: "enabled" },
  },
  brand: { siteName: "台湾神算子", navigation: [], footer: { copyright: "台湾神算子" } },
  security: { externalScriptOrigins: [], externalNavigationOrigins: [] },
})
