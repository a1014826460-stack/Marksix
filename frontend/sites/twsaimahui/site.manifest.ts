import { defineVendorSiteManifest } from "@/lib/site-platform/site-manifest"

export default defineVendorSiteManifest({
  identity: {
    siteKey: "twsaimahui",
    domains: ["www.twsaimahui.com", "twsaimahui.com"],
    routePath: "/twsaimahui",
    siteId: 6,
    webId: 6,
    defaultLotteryType: 3,
  },
  frontend: {
    renderMode: "iframe-vendor",
    vendorIndexPath: "/vendor/twsaimahui/index.html",
    legacyPublicBasePath: "/vendor/twsaimahui",
    defaultGame: "taiwan",
    forumTitle: "台湾赛马会",
    metadataTitle: "台湾赛马会：官方正版请认准唯一官方",
    metadataDescription: "台湾赛马会：官方正版请认准唯一官方",
    faviconPath: "/vendor/twsaimahui/static/image/favicon.ico",
  },
  bridge: {
    api: {
      httpApiBase: "",
      kaijiangApiBase: "/api/kaijiang",
    },
    autoLoad: {
      draw: true,
      prediction: true,
    },
    predictionModuleKeys: [
      "wuxiao_wuma",
      "public_yixiao_yima",
      "shuangbo_12ma",
      "shujinguang",
      "daxiao_2tou",
      "tiandi_2xiao",
    ],
    runtime: {
      drawSelector: ".KJ-TabBox",
      predictionSelector: "#content-area",
      footerSelector: "img[src='static/picture/log1.jpg']",
      navigationSelector: "#nav2",
      legacyPredictionScripts: "enabled",
    },
  },
  brand: {
    siteName: "台湾赛马会",
    logoUrl: "/vendor/twsaimahui/static/image/logo.png",
    faviconUrl: "/vendor/twsaimahui/static/image/favicon.ico",
    theme: {
      primary: "#d40000",
      accent: "#f4d000",
      background: "#ffffff",
    },
    navigation: [
      { label: "精华榜一", href: "#jhb" },
      { label: "精华榜二", href: "#jhb2" },
      { label: "封神图榜", href: "#fsb" },
      { label: "全网英雄榜", href: "#jgjp" },
      { label: "精品资料区", href: "#jpzlq" },
    ],
    footer: {
      copyright: "台湾赛马会",
      imageUrls: [
        "/vendor/twsaimahui/static/picture/log1.jpg",
        "/vendor/twsaimahui/static/picture/log5.jpg",
        "/vendor/twsaimahui/static/picture/log4.jpg",
        "/vendor/twsaimahui/static/picture/log8.jpg",
      ],
      contacts: [{ label: "台湾赛马会", href: "#top" }],
    },
  },
  security: {
    externalScriptOrigins: [
      "https://gy.123pmz.com:8443",
      "https://js.szly123.com",
      "https://libs.baidu.com",
      "https://x1.xn--hdcl2bk2m1bc.xn--gecrj9c:8443",
    ],
    externalNavigationOrigins: ["https://www.72965.com", "https://www-08200.com"],
  },
})
