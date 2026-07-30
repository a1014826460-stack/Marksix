import { defineVendorSiteManifest } from "@/lib/site-platform/site-manifest"

export default defineVendorSiteManifest({
  identity: {
    siteKey: "twjsz666",
    domains: ["www.twjsz666.com", "twjsz666.com"],
    routePath: "/twjsz666",
    siteId: 11,
    webId: 11,
    defaultLotteryType: 3,
  },
  frontend: {
    renderMode: "iframe-vendor",
    vendorIndexPath: "/vendor/twjsz666/index.html",
    legacyPublicBasePath: "/vendor/twjsz666",
    defaultGame: "taiwan",
    forumTitle: "台湾金手指",
    metadataTitle: "台湾金手指",
    metadataDescription: "台湾金手指预测资料",
  },
  bridge: {
    api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" },
    autoLoad: { draw: true, prediction: true },
    predictionModuleKeys: [
      "yijuzhenyan", "shuangbo", "7xiao7ma", "pt2xiao", "jueshabanbo",
      "pt1wei", "daxiao", "4xiao8ma", "pt1xiao", "title_5", "title_47",
      "pt3xiao", "juesha1xiao", "danshuangtema", "sixiao_sima", "juesha1wei",
    ],
    runtime: {
      drawSelector: ".KJ-TabBox",
      predictionSelector: "#yxym, #pttj, #jzlx, #ptyx, #sqbz, .xjct, .pnzl, .gongshi",
      footerSelector: ".foot-img",
      navigationSelector: ".nav",
      legacyPredictionScripts: "enabled",
    },
  },
  brand: {
    siteName: "台湾金手指",
    navigation: [],
    footer: { copyright: "台湾金手指" },
  },
  security: { externalScriptOrigins: [], externalNavigationOrigins: [] },
})
