export type ExistingDomAdapter = {
  siteKey: string
  mode: "existing-dom-only"
  draw: { resource: "draw"; selectors: readonly string[] }
  predictions: { resource: "predictions"; selectors: readonly string[] }
  navigation: { selector: string; fixedBehavior: "existing-script" | "css-sticky" }
  footer: { selector: string; imageUrls: readonly string[]; behavior: "existing-markup" }
}
