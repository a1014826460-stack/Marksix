/**
 * twcaibawang 首屏契约 — 服务端并发取数 + 内容图片懒加载
 * ---------------------------------------------------------------
 * 1. /twcaibawang 的服务端组件原先串行 await 两次后端聚合
 *    （/api/public/site-page 与 /api/vendor/homepage-modules），把首屏 HTML
 *    （以及其中的开奖面板 iframe）推迟一个完整往返。契约要求两次聚合并发。
 * 2. 首页内容模板里的 /static/picture/** 图片必须带 loading="lazy"，
 *    首次访问不再一次性拉取全部大图。
 */
import fs from "node:fs"

const page = fs.readFileSync("frontend/app/twcaibawang/page.tsx", "utf8")
if (!page.includes("await Promise.all([")) {
  throw new Error("twcaibawang page still awaits its two backend aggregations serially")
}
if (!/getPublicSitePageData\(\{[\s\S]*?\}\),\s*getVendorHomepageModules\(\{/.test(page)) {
  throw new Error("twcaibawang page does not start both aggregations in the same Promise.all")
}
if (!page.includes("siteData.site.lottery_type_id === defaultLotteryTypeId")) {
  throw new Error("twcaibawang page lost the lottery-type fallback for homepage modules")
}

const client = fs.readFileSync("frontend/components/twcaibawang/TwcaibawangHomeClient.tsx", "utf8")
const pictureTags = [...client.matchAll(/<img\b[^>]*static\/picture\/[^>]*>/g)].map((match) => match[0])
if (pictureTags.length === 0) throw new Error("twcaibawang template no longer renders content images")
const eager = pictureTags.filter((tag) => !/\bloading="lazy"/.test(tag))
if (eager.length > 0) {
  throw new Error(`twcaibawang still has ${eager.length} eager content pictures`)
}
if (!pictureTags.every((tag) => tag.includes('decoding="async"'))) {
  throw new Error("twcaibawang content pictures should decode asynchronously")
}

console.log("twcaibawang first paint contract passed")
