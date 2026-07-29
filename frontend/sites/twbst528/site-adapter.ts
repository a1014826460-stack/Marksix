import type { ExistingDomAdapter } from "@/lib/site-platform/site-adapter"

const adapter: ExistingDomAdapter = {
  siteKey: "twbst528",
  mode: "existing-dom-only",
  draw: { resource: "draw", selectors: [".KJ-TabBox"] },
  predictions: {
    resource: "predictions",
    selectors: ["#zhenyan_ping_xiao", "#bose", "#daimingxiao", "#xiaoma_xiaoma", "#jiaye", ".article-content > p"],
  },
  navigation: { selector: ".KJ-TabBox", fixedBehavior: "existing-script" },
  footer: {
    selector: "#legacy-attribute-anchor",
    imageUrls: [
      "/uploads/image/20250322/1742580086567063.png",
      "/uploads/image/20250322/1742580119746508.jpg",
      "/uploads/image/20250322/1742580130762983.jpg",
    ],
    behavior: "existing-markup",
  },
}

export default adapter
