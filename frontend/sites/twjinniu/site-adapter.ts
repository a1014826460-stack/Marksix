import type { ExistingDomAdapter } from "@/lib/site-platform/site-adapter"

const adapter: ExistingDomAdapter = {
  siteKey: "twjinniu",
  mode: "existing-dom-only",
  draw: { resource: "draw", selectors: ["#twjinniu-kj-iframe"] },
  predictions: { resource: "predictions", selectors: [] },
  navigation: { selector: "#nav2", fixedBehavior: "existing-script" },
  footer: { selector: ".foot-img", imageUrls: [], behavior: "existing-markup" },
}

export default adapter
