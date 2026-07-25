import { defineVendorSiteManifest } from "@/lib/site-platform/site-manifest"

export default defineVendorSiteManifest({
  identity: {
    siteKey: "twcf888",
    domains: ["www.twcf888.com", "twcf888.com"],
    routePath: "/twcf888",
    siteId: 8,
    webId: 8,
    defaultLotteryType: 3,
  },
  frontend: {
    renderMode: "react-template",
    vendorIndexPath: "/vendor/twcf888.com/index.html",
    legacyPublicBasePath: "/vendor/twcf888.com",
    defaultGame: "taiwan",
    forumTitle: "台湾创富网",
    metadataTitle: "台湾创富网",
    metadataDescription: "台湾创富网 | 聚合全网高手资料",
    faviconPath: "/vendor/twcf888.com/static/favicon.ico",
  },
  bridge: {
    api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" },
    autoLoad: { draw: true, prediction: true },
    predictionModuleKeys: [],
    runtime: {
      drawSelector: "#twcf888-kj-iframe",
      predictionSelector: "#twcf888-dynamic-homepage",
      footerSelector: ".pop-xyz-footer",
      navigationSelector: "#nav2",
      legacyPredictionScripts: "enabled",
    },
  },
  brand: { siteName: "台湾创富网", navigation: [], footer: { copyright: "台湾创富网" } },
  security: { externalScriptOrigins: [], externalNavigationOrigins: [] },
})
