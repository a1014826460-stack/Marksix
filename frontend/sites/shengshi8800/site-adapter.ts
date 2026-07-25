import type { ExistingDomAdapter } from "@/lib/site-platform/site-adapter"

const adapter: ExistingDomAdapter = {
  siteKey: "shengshi8800",
  mode: "existing-dom-only",
  draw: { resource: "draw", selectors: [".KJ-TabBox"] },
  predictions: { resource: "predictions", selectors: ["#legacy-result-anchor"] },
  navigation: { selector: ".legacy-shell-frame", fixedBehavior: "css-sticky" },
  footer: { selector: ".foot-img", imageUrls: [], behavior: "existing-markup" },
}

export default adapter
