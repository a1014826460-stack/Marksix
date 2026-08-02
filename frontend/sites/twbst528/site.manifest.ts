import { defineVendorSiteManifest } from "@/lib/site-platform/site-manifest"

export default defineVendorSiteManifest({
  identity: {
    siteKey: "twbst528",
    domains: ["www.twbst528.com", "twbst528.com"],
    routePath: "/twbst528",
    siteId: 10,
    webId: 10,
    defaultLotteryType: 3,
  },
  frontend: {
    renderMode: "iframe-vendor",
    vendorIndexPath: "/vendor/twbst528/index.html",
    legacyPublicBasePath: "/vendor/twbst528",
    defaultGame: "taiwan",
    forumTitle: "台湾百事通",
    metadataTitle: "台湾百事通",
    metadataDescription: "台湾百事通",
    faviconPath: "/vendor/twbst528/static/picture/logo.png",
  },
  bridge: {
    api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" },
    autoLoad: { draw: true, prediction: true },
    predictionModuleKeys: [
      "yijuzhenyan", "shuangbo", "7xiao7ma", "pt2xiao", "jueshabanbo", "sxztu", "pmtj_image",
      "pt1wei", "daxiao", "4xiao8ma", "pt1xiao", "title_5", "title_47",
      "pt3xiao", "juesha1xiao", "danshuangtema", "sixiao_sima", "juesha1wei",
    ],
    runtime: {
      drawSelector: ".KJ-TabBox",
      predictionSelector: ".content",
      footerSelector: ".footer",
      navigationSelector: ".KJ-TabBox",
      legacyPredictionScripts: "enabled",
    },
  },
  brand: {
    siteName: "台湾百事通",
    logoUrl: "/vendor/twbst528/static/picture/logo.png",
    faviconUrl: "/vendor/twbst528/static/picture/logo.png",
    navigation: [],
    footer: { copyright: "台湾百事通" },
  },
  security: { externalScriptOrigins: [], externalNavigationOrigins: [] },
})
