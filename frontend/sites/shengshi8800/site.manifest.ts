import { defineVendorSiteManifest } from "@/lib/site-platform/site-manifest"

export default defineVendorSiteManifest({
  identity: {
    siteKey: "shengshi8800",
    domains: ["www.tw8800.com", "tw8800.com", "localhost", "127.0.0.1"],
    routePath: "/shengshi8800",
    siteId: 4,
    webId: 4,
    defaultLotteryType: 3,
  },
  frontend: {
    renderMode: "legacy-dom",
    vendorIndexPath: "/vendor/shengshi8800/embed.html",
    legacyPublicBasePath: "/vendor/shengshi8800",
    defaultGame: "taiwan",
    forumTitle: "台湾六合彩论坛",
    metadataTitle: "全网最准尽在台湾六合彩论坛",
    metadataDescription: "全网最准尽在台湾六合彩论坛",
    faviconPath: "/vendor/shengshi8800/static/picture/favicon.ico",
  },
  bridge: {
    api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" },
    autoLoad: { draw: true, prediction: true },
    predictionModuleKeys: [],
    runtime: {
      drawSelector: ".KJ-TabBox",
      predictionSelector: "",
      footerSelector: ".foot-img",
      navigationSelector: ".legacy-shell-frame",
      legacyPredictionScripts: "enabled",
    },
  },
  brand: {
    siteName: "盛世台湾六合彩",
    logoUrl: "/vendor/shengshi8800/static/picture/header.jpg",
    faviconUrl: "/vendor/shengshi8800/static/picture/favicon.ico",
    navigation: [],
    footer: { copyright: "台湾六合彩论坛" },
  },
  security: { externalScriptOrigins: [], externalNavigationOrigins: [] },
})
