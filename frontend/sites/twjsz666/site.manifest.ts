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
    faviconPath: "/vendor/twjsz666/static/picture/favicon.ico",
  },
  bridge: {
    api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" },
    autoLoad: { draw: true, prediction: true },
    predictionModuleKeys: [
      "yijuzhenyan", "shuangbo", "jueshabanbo", "pt1wei", "daxiao",
      "4xiao8ma", "pt1xiao", "pt3xiao", "juesha1wei", "juesha2xiao", "9xzt",
      "sitouzhongte", "juesha1xiao", "qinqi",
      "danshuang4xiao", "three_head_four_tail", "gongshi_siw", "title_14", "title_74",
      "sizixuanji", "selected_22_codes", "steady_kill_7_codes", "expert_publications",
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
