import type { ExistingDomAdapter } from "@/lib/site-platform/site-adapter"

const adapter: ExistingDomAdapter = {
  siteKey: "twcaibawang",
  mode: "existing-dom-only",
  draw: { resource: "draw", selectors: [".KJ-TabBox"] },
  predictions: { resource: "predictions", selectors: [] },
  navigation: { selector: "#nav2", fixedBehavior: "existing-script" },
  footer: { selector: ".foot-img", imageUrls: [], behavior: "existing-markup" },
}

export default adapter
