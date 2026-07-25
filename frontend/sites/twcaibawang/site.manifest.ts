import { defineVendorSiteManifest } from "@/lib/site-platform/site-manifest"

export default defineVendorSiteManifest({
  identity: {
    siteKey: "twcaibawang",
    domains: ["www.twcaibawang.com", "twcaibawang.com"],
    routePath: "/twcaibawang",
    siteId: 5,
    webId: 5,
    defaultLotteryType: 3,
  },
  frontend: {
    renderMode: "react-template",
    vendorIndexPath: "/vendor/twcaibawang.com/index.html",
    legacyPublicBasePath: "/vendor/twcaibawang.com",
    defaultGame: "hongkong",
    forumTitle: "香港天天彩",
    metadataTitle: "台湾彩霸王：聚合全网高手",
    metadataDescription: "台湾彩霸王：聚合全网高手",
    faviconPath: "/vendor/twcaibawang.com/static/image/favicon.ico",
  },
  bridge: {
    api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" },
    autoLoad: { draw: true, prediction: true },
    predictionModuleKeys: ["wuxiao_wuma", "public_yixiao_yima", "shuangbo_12ma", "shujinguang", "daxiao_2tou", "tiandi_2xiao"],
    runtime: {
      drawSelector: "#twcaibawang-kj-iframe",
      predictionSelector: "#ptyx",
      footerSelector: ".foot-img",
      navigationSelector: "#nav2",
      legacyPredictionScripts: "enabled",
    },
  },
  brand: {
    siteName: "台湾彩霸王",
    faviconUrl: "/vendor/twcaibawang.com/static/image/favicon.ico",
    navigation: [],
    footer: { copyright: "台湾彩霸王" },
  },
  security: { externalScriptOrigins: [], externalNavigationOrigins: [] },
})
