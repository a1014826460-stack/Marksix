import type { ExistingDomAdapter } from "@/lib/site-platform/site-adapter"

const adapter: ExistingDomAdapter = {
  siteKey: "twsyw",
  mode: "existing-dom-only",
  draw: { resource: "draw", selectors: ["iframe[src='kai.html']"] },
  predictions: { resource: "predictions", selectors: ["[data-prediction-section]"] },
  navigation: { selector: "#nav2", fixedBehavior: "existing-script" },
  footer: { selector: "#legacy-attribute-anchor", imageUrls: ["/uploads/image/20250322/1742580086567063.png", "/uploads/image/20250322/1742580119746508.jpg", "/uploads/image/20250322/1742580130762983.jpg"], behavior: "existing-markup" },
}

export default adapter
