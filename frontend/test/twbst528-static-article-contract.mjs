import fs from "node:fs"

const pages = [
  "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "27",
  "30", "31", "32", "33", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44",
  "45", "46", "47", "48", "49", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60",
  "77", "78", "79", "80",
  "141", "142", "143", "144", "145", "146", "147", "148", "149", "150", "151", "152", "153", "154", "155", "156",
]
const expectedModules = {
  141: "title_198", 142: "juesha1wei", 143: "sitouzhongte", 144: "title_14",
  145: "title_5", 146: "title_47", 147: "title_279", 148: "title_47",
  149: "title_66", 150: "3hang", 151: "title_132", 152: "qinqi",
  153: "pt3xiao", 154: "3tou", 155: "3hang", 156: "yijuzhenyan",
}

for (const page of pages) {
  const source = fs.readFileSync(`frontend/public/vendor/twbst528/${page}.html`, "utf8")
  for (const token of [
    "site-config.js",
    "/vendor/_shared/lottery-site-data-client.js",
    "static-article-data-adapter.js",
    'class="article-content"',
  ]) {
    if (!source.includes(token)) throw new Error(`${page}.html missing ${token}`)
  }
}

const adapter = fs.readFileSync("frontend/public/vendor/twbst528/static-article-data-adapter.js", "utf8")
const legacyHomepage = fs.readFileSync("frontend/public/vendor/twbst528/index1.html", "utf8")
const homepage = fs.readFileSync("frontend/public/vendor/twbst528/index.html", "utf8")
for (const moduleKey of Object.values(expectedModules)) {
  if (!adapter.includes(`"${moduleKey}"`)) throw new Error(`article adapter missing ${moduleKey}`)
}
for (const page of pages) {
  if (!adapter.includes(`"${page}":`)) throw new Error(`article adapter missing page contract ${page}`)
}
for (const token of ["loadPredictions", "historyLimit: 8", "PAGE_CONTRACTS", "writeArticleRow", "暂无后端资料"]) {
  if (!adapter.includes(token)) throw new Error(`article adapter missing ${token}`)
}
if (!homepage.includes('href="/history?type=3"')) throw new Error("homepage must use the standard history page")
if (fs.existsSync("frontend/public/vendor/twbst528/history.html")) throw new Error("independent history template remains")
if (!legacyHomepage.includes('window.location.replace("index.html")')) {
  throw new Error("legacy static homepage must redirect to the data-backed homepage")
}
