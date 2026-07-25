import type { ExistingDomAdapter } from "@/lib/site-platform/site-adapter"

const adapter: ExistingDomAdapter = {
  siteKey: "twcf888",
  mode: "existing-dom-only",
  draw: { resource: "draw", selectors: ["#twcf888-kj-iframe"] },
  predictions: { resource: "predictions", selectors: [] },
  navigation: { selector: "#nav2", fixedBehavior: "existing-script" },
  footer: { selector: ".pop-xyz-footer", imageUrls: [], behavior: "existing-markup" },
}

export default adapter
