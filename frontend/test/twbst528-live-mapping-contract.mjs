import fs from "node:fs"

const index = fs.readFileSync("frontend/public/vendor/twbst528/index.html", "utf8")
const config = fs.readFileSync("frontend/public/vendor/twbst528/site-config.js", "utf8")
const adapter = fs.readFileSync("frontend/public/vendor/twbst528/site-data-adapter.js", "utf8")

for (const token of [
  '台湾百事通',
  'www.twbst528.com',
  '/vendor/_shared/lottery-site-data-client.js',
  'site-config.js',
  'site-data-adapter.js',
  'data-site-key="twbst528"',
]) {
  if (!index.includes(token)) throw new Error(`homepage missing ${token}`)
}
for (const token of ['siteKey: "twbst528"', 'siteName: "台湾百事通"', 'siteDomain: "www.twbst528.com"', 'lotteryType: 3', 'lotteryType: 2', 'lotteryType: 1']) {
  if (!config.includes(token)) throw new Error(`site configuration missing ${token}`)
}
for (const token of [
  'loadDraw',
  'loadPredictions',
  'historyLimit: 6',
  'renderThreeColumnRows',
  'renderDoubleWaveHistory',
  'selectLottery',
  'data-prediction-section',
  'clearMarkers',
  'renderYijuZhongpingHistory',
  'renderLiangboTuweiHistory',
  'renderBaxiaoLaixiHistory',
  'activateDrawPanel',
]) {
  if (!adapter.includes(token)) throw new Error(`adapter missing ${token}`)
}
for (const token of [
  '/vendor/shengshi8800/kj/local.html?lottery_type=3',
  '/vendor/shengshi8800/kj/local.html?lottery_type=2',
  '/vendor/shengshi8800/kj/local.html?lottery_type=1',
  'id="legacy-attribute-anchor"',
  'id="legacy-attribute-gallery"',
  '/uploads/image/20250322/1742580086567063.png',
  '/uploads/image/20250322/1742580119746508.jpg',
  '/uploads/image/20250322/1742580130762983.jpg',
]) {
  if (!index.includes(token)) throw new Error(`homepage missing unified site component ${token}`)
}
if (index.includes("url':'about:blank'")) throw new Error("draw tabs must not retain blank supplier iframes")
if (index.includes('id="jinfang"') || index.includes("function hidediv")) {
  throw new Error("supplier notification window must be removed")
}
for (const sentinel of ['第233期', '开:????', '台湾百事通【两波突围】']) {
  if (!index.includes(sentinel)) throw new Error(`supplier DOM baseline missing ${sentinel}`)
}
