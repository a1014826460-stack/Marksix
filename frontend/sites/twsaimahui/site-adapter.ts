import type { ExistingDomAdapter } from "@/lib/site-platform/site-adapter"

const adapter: ExistingDomAdapter = {
  siteKey: "twsaimahui",
  mode: "existing-dom-only",
  draw: { resource: "draw", selectors: [".KJ-TabBox"] },
  predictions: { resource: "predictions", selectors: ["#content-area"] },
  navigation: { selector: "#nav2", fixedBehavior: "existing-script" },
  footer: {
    selector: "img[src='static/picture/log1.jpg']",
    imageUrls: [
      "/vendor/twsaimahui/static/picture/log1.jpg",
      "/vendor/twsaimahui/static/picture/log5.jpg",
      "/vendor/twsaimahui/static/picture/log4.jpg",
      "/vendor/twsaimahui/static/picture/log8.jpg",
    ],
    behavior: "existing-markup",
  },
}

export default adapter
