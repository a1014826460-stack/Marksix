import type { ExistingDomAdapter } from "@/lib/site-platform/site-adapter"

const adapter: ExistingDomAdapter = {
  siteKey: "twjsz666",
  mode: "existing-dom-only",
  draw: { resource: "draw", selectors: [".KJ-TabBox", "iframe[src='kai.html']"] },
  predictions: {
    resource: "predictions",
    selectors: [
      "#yxym", "#pttj", "#jzlx", "#ptyx", "#sqbz", ".bizhong1", ".duilianpt",
      ".qxtable", ".xjct", ".pnzl", ".gongshi", ".list-title",
    ],
  },
  navigation: { selector: ".nav", fixedBehavior: "existing-script" },
  footer: { selector: ".foot-img", imageUrls: [], behavior: "existing-markup" },
}

export default adapter
