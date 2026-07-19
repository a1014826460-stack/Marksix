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
      draw: false,
      prediction: false,
    },
    predictionModuleKeys: [],
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
    navigation: [],
    footer: {
      copyright: "台湾赛马会",
      contacts: [],
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
