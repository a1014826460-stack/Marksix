import type { ExistingDomAdapter } from "@/lib/site-platform/site-adapter"

const adapter: ExistingDomAdapter = {
  siteKey: "twssz",
  mode: "existing-dom-only",
  draw: { resource: "draw", selectors: ["iframe[src='kai.html']", ".KJ-TabBox"] },
  predictions: { resource: "predictions", selectors: ["#top_15", "#top_14", "#top_9", "#top_13", "#top_11", "#top_10", "#top_6", "#top_4", "#top_1", "#top_2", "#top_12"] },
  navigation: { selector: "#nav2", fixedBehavior: "existing-script" },
  footer: { selector: ".cgi-body", imageUrls: [], behavior: "existing-markup" },
}

export default adapter
