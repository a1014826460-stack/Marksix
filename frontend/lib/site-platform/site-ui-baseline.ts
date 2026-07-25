export type SiteUiBaseline = {
  routePath: string
  vendorEntry: string
  drawSentinel: string
  navigationSentinel: string
  footerSentinel: string
}

export const SITE_UI_BASELINES: Readonly<Record<string, SiteUiBaseline>> = Object.freeze({
  shengshi8800: {
    routePath: "/",
    vendorEntry: "/vendor/shengshi8800/embed.html",
    drawSentinel: ".KJ-TabBox",
    navigationSentinel: ".legacy-shell-frame",
    footerSentinel: ".foot-img",
  },
  twsaimahui: {
    routePath: "/twsaimahui",
    vendorEntry: "/vendor/twsaimahui/index.html",
    drawSentinel: ".KJ-TabBox",
    navigationSentinel: "#nav2",
    footerSentinel: "static/picture/log1.jpg",
  },
  twcaibawang: {
    routePath: "/twcaibawang",
    vendorEntry: "/vendor/twcaibawang.com/index.html",
    drawSentinel: ".KJ-TabBox",
    navigationSentinel: "#nav2",
    footerSentinel: ".foot-img",
  },
  twjinniu: {
    routePath: "/twjinniu",
    vendorEntry: "/vendor/twjinniu/index.html",
    drawSentinel: "#twjinniu-kj-iframe",
    navigationSentinel: "#nav2",
    footerSentinel: ".foot-img",
  },
  twcf888: {
    routePath: "/twcf888",
    vendorEntry: "/vendor/twcf888.com/index.html",
    drawSentinel: "#twcf888-kj-iframe",
    navigationSentinel: "#nav2",
    footerSentinel: ".pop-xyz-footer",
  },
  twssz: {
    routePath: "/twssz",
    vendorEntry: "/vendor/twssz/index.html",
    drawSentinel: "iframe[src='kai.html']",
    navigationSentinel: "#nav2",
    footerSentinel: ".cgi-body",
  },
})
