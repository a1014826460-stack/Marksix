import { defineVendorSiteManifest } from "@/lib/site-platform/site-manifest"

export default defineVendorSiteManifest({
  identity: {
    siteKey: "twjinniu",
    domains: ["www.twtongtian.com", "twtongtian.com", "www.twjinniu.com", "twjinniu.com"],
    routePath: "/twjinniu",
    siteId: 7,
    webId: 7,
    defaultLotteryType: 3,
  },
  frontend: {
    renderMode: "react-template",
    vendorIndexPath: "/vendor/twjinniu/index.html",
    legacyPublicBasePath: "/vendor/twjinniu",
    defaultGame: "taiwan",
    forumTitle: "台湾通天网",
    metadataTitle: "台湾通天网",
    metadataDescription: "台湾通天网 | 聚合全网高手",
    faviconPath: "/vendor/twjinniu/static/favicon.ico",
  },
  bridge: {
    api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" },
    autoLoad: { draw: true, prediction: true },
    predictionModuleKeys: [],
    runtime: {
      drawSelector: "#twjinniu-kj-iframe",
      predictionSelector: "#twjinniu-formula-ptx",
      footerSelector: ".foot-img",
      navigationSelector: "#nav2",
      legacyPredictionScripts: "enabled",
    },
  },
  brand: { siteName: "台湾通天网", navigation: [], footer: { copyright: "台湾通天网" } },
  security: { externalScriptOrigins: [], externalNavigationOrigins: [] },
})
