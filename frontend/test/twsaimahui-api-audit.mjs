import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const BASE_URL = process.argv.find((arg) => arg.startsWith("--base-url="))?.split("=")[1] || "http://127.0.0.1:3000";
const WEB_ID = 6;
const TYPE_ID = 3;
const MAX_EXPECTED_ROWS = 10;

const now = new Date();
const pad = (value) => String(value).padStart(2, "0");
const timestamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
const RESULTS_FILE = path.join(path.dirname(fileURLToPath(import.meta.url)), `twsaimahui_api_audit_${timestamp}.json`);

const STRING_FIELDS = new Set([
  "content",
  "res_code",
  "res_sx",
  "term",
  "xiao",
  "dan",
  "shuang",
  "nan",
  "nv",
  "title",
  "xiao_1",
  "xiao_2",
  "code",
  "jiexi",
  "zi",
  "image_url",
  "name",
  "u6_code",
]);

function kaijiangCase(module, apiPath, num, expectedFields, options = {}) {
  return {
    module,
    path: apiPath,
    query: { web: WEB_ID, type: TYPE_ID, num: String(num) },
    expectedFields,
    contentJson: Boolean(options.contentJson),
    topLevelKeys: ["data"],
  };
}

function buildCases() {
  return [
    kaijiangCase("061jy2x.js", "/api/kaijiang/getJyxiao2", 2, ["content", "res_code", "res_sx", "term", "xiao"], { contentJson: true }),
    kaijiangCase("033zuoyou.js", "/api/kaijiang/getZyx", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("012liuxiao.js", "/api/kaijiang/getXiaoma2", 6, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("044yinyang.js", "/api/kaijiang/getYysx", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("027six8m.js", "/api/kaijiang/getXiaoma2", 4, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("003ds4w.js", "/api/kaijiang/getDsWei", 4, ["dan", "res_code", "res_sx", "shuang", "term"]),
    kaijiangCase("071ds.js", "/api/kaijiang/danshuang", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("073sixiao.js", "/api/kaijiang/getZhongte", 4, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("006heshuds.js", "/api/kaijiang/getHeds", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("043tiandi.js", "/api/kaijiang/getTdsx1", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("049rccx.js", "/api/kaijiang/getRccx", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("040jiaye.js", "/api/kaijiang/getJyzt", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("042ycwx.js", "/api/kaijiang/getZhongte", 5, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("039heibai.js", "/api/kaijiang/getHbx", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("014jiuxiao.js", "/api/kaijiang/getZhongte", 9, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("031wuxiao.js", "/api/kaijiang/getZhongte", 3, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("060ds4x.js", "/api/kaijiang/getDsnx", 4, ["res_code", "res_sx", "term", "xiao_1", "xiao_2"]),
    kaijiangCase("011jiepaoma.js", "/api/kaijiang/getXiaoma2", 7, ["content", "image_url", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("030lflx.js", "/api/kaijiang/getZhongte", 4, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("068chengyupw.js", "/api/kaijiang/getCyptwei", 2, ["res_code", "res_sx", "term", "title"]),
    kaijiangCase("023sanqibizhong.js", "/api/kaijiang/getSanqiXiao4new", 7, ["content", "name", "res_code", "res_sx"], { contentJson: true }),
    kaijiangCase("075tiandi.js", "/api/kaijiang/getTdsx1", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("038ma10.js", "/api/kaijiang/getCode", 10, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("050siji.js", "/api/kaijiang/getSjsx", 3, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("004danshuang.js", "/api/kaijiang/getDsxiao", 2, ["content", "res_code", "res_sx", "term", "xiao"]),
    kaijiangCase("032ma20.js", "/api/kaijiang/getCode", 20, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("036ma12.js", "/api/kaijiang/getYbzt", 2, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("026siw8m.js", "/api/kaijiang/getWeima2", 4, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("035ma16.js", "/api/kaijiang/getCode", 16, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("065yiziptx.js", "/api/kaijiang/getPingte", 1, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("047liuxiao.js", "/api/kaijiang/getZhongte", 6, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("046wenwu.js", "/api/kaijiang/getWwx", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("002daxiao.js", "/api/kaijiang/getDxzt", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("045youwu.js", "/api/kaijiang/getYwx", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("067sanzipw.js", "/api/kaijiang/getPingte", 3, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("062linbei6x.js", "/api/kaijiang/getZhongte", 6, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("053wfsb.js", "/api/kaijiang/getBmzy", 3, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("057s1x.js", "/api/kaijiang/getShaXiao", 1, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("069lxbm.js", "/api/kaijiang/getX2jiam8", 2, ["code", "content", "res_code", "res_sx", "term"]),
    kaijiangCase("022pt1w.js", "/api/kaijiang/getPtWei", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("072liangtou.js", "/api/kaijiang/getTou", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("056s7m.js", "/api/kaijiang/getShama", 7, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("058s2x.js", "/api/kaijiang/getShaXiao", 2, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("051fyld.js", "/api/kaijiang/getFyld", 3, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("029yizixuanji.js", "/api/kaijiang/getYzxj", 6, ["jiexi", "res_code", "res_sx", "term", "xiao", "zi"]),
    kaijiangCase("066chengyupx.js", "/api/kaijiang/getCypt", 2, ["res_code", "res_sx", "term", "title"]),
    {
      module: "019liubuzhong.js",
      path: "/api/kaijiang/rd70i73lziizczak/0gmqnw/1",
      query: {},
      expectedFields: ["res_code", "res_sx", "term", "u6_code"],
      contentJson: false,
      topLevelKeys: ["data"],
    },
    kaijiangCase("020nn4x.js", "/api/kaijiang/getNnnx", 4, ["nan", "nv", "res_code", "res_sx", "term"]),
    kaijiangCase("013jiux1m.js", "/api/kaijiang/getXysxma", 9, ["code", "res_code", "res_sx", "term", "xiao"]),
    kaijiangCase("024santou.js", "/api/kaijiang/getTou", 3, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("025sanhang.js", "/api/kaijiang/getXingte", 3, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("001sb.js", "/api/kaijiang/sbzt", 2, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("018sha1tou.js", "/api/kaijiang/getShatou", 1, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("041meichou.js", "/api/kaijiang/getJmxc", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("015sha3w.js", "/api/kaijiang/getShaWei", 3, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("016sha3x.js", "/api/kaijiang/getShaXiao", 3, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("034feishou.js", "/api/kaijiang/getFsx", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("074ptyx.js", "/api/kaijiang/getPingte", 1, ["content", "res_code", "res_sx", "term"]),
    kaijiangCase("037dandaxiao.js", "/api/kaijiang/getDxd", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("048hllx.js", "/api/kaijiang/getHllx", 2, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("052qqsh.js", "/api/kaijiang/qqsh", 3, ["content", "res_code", "res_sx", "term", "title"]),
    {
      module: "zx.js",
      path: "/api/post/getList",
      query: { web: WEB_ID, type: TYPE_ID, pc: 72 },
      expectedFields: ["id", "title"],
      contentJson: false,
      topLevelKeys: ["data"],
    },
    kaijiangCase("054sbanbo.js", "/api/kaijiang/getShaBanbo", 1, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    kaijiangCase("055sbands.js", "/api/kaijiang/getShaBds", 1, ["content", "res_code", "res_sx", "term"], { contentJson: true }),
    {
      module: "index.html",
      path: "/api/index/notice",
      query: { web: WEB_ID },
      expectedFields: ["content"],
      contentJson: false,
      topLevelKeys: ["code", "data"],
    },
  ];
}

function buildUrl(baseUrl, apiPath, query) {
  const url = new URL(apiPath, `${baseUrl}/`);
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    url.searchParams.set(key, String(value));
  }
  return url.toString();
}

function validateJsonStringArray(content, issues, rowIndex) {
  try {
    const parsed = JSON.parse(content);
    if (!Array.isArray(parsed)) {
      issues.push(`row ${rowIndex}: content JSON should decode to array, got ${typeof parsed}`);
      return;
    }
    if (!parsed.every((item) => typeof item === "string")) {
      issues.push(`row ${rowIndex}: content JSON array items should all be strings`);
    }
  } catch (error) {
    issues.push(`row ${rowIndex}: content should be valid JSON string array: ${error}`);
  }
}

function validateRow(row, testCase, issues, rowIndex) {
  if (!row || typeof row !== "object" || Array.isArray(row)) {
    issues.push(`row ${rowIndex}: expected object, got ${Array.isArray(row) ? "array" : typeof row}`);
    return [];
  }

  const actualKeys = Object.keys(row);
  if (JSON.stringify(actualKeys) !== JSON.stringify(testCase.expectedFields)) {
    issues.push(`row ${rowIndex}: field order/keys mismatch, expected ${JSON.stringify(testCase.expectedFields)}, got ${JSON.stringify(actualKeys)}`);
  }

  for (const fieldName of testCase.expectedFields) {
    if (!(fieldName in row)) {
      issues.push(`row ${rowIndex}: missing field '${fieldName}'`);
      continue;
    }

    const value = row[fieldName];
    if (fieldName === "id") {
      if (!Number.isInteger(value)) {
        issues.push(`row ${rowIndex}: field 'id' should be integer, got ${typeof value}`);
      }
      continue;
    }

    if (STRING_FIELDS.has(fieldName) && typeof value !== "string") {
      issues.push(`row ${rowIndex}: field '${fieldName}' should be string, got ${typeof value}`);
      continue;
    }

    if ((fieldName === "res_code" || fieldName === "res_sx") && value === null) {
      issues.push(`row ${rowIndex}: field '${fieldName}' should not be null`);
    }

    if (fieldName === "content" && typeof value === "string" && testCase.contentJson) {
      validateJsonStringArray(value, issues, rowIndex);
    }
  }

  return actualKeys;
}

function auditStandardResponse(testCase, payload) {
  const issues = [];

  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { outcome: "fail", issues: [`top-level payload should be object, got ${Array.isArray(payload) ? "array" : typeof payload}`] };
  }

  const topLevelKeys = Object.keys(payload);
  if (JSON.stringify(topLevelKeys) !== JSON.stringify(testCase.topLevelKeys)) {
    issues.push(`top-level keys mismatch, expected ${JSON.stringify(testCase.topLevelKeys)}, got ${JSON.stringify(topLevelKeys)}`);
  }

  if (!("data" in payload)) {
    issues.push("missing top-level key 'data'");
    return { outcome: "fail", issues, topLevelKeys };
  }

  if (!Array.isArray(payload.data)) {
    issues.push(`top-level 'data' should be array, got ${typeof payload.data}`);
    return { outcome: "fail", issues, topLevelKeys };
  }

  const rowCount = payload.data.length;
  if (rowCount > MAX_EXPECTED_ROWS) {
    issues.push(`row count should be <= ${MAX_EXPECTED_ROWS}, got ${rowCount}`);
  }

  if (rowCount === 0) {
    issues.push("data is empty; row-level contract could not be validated");
    return { outcome: "warning", issues, rowCount, topLevelKeys };
  }

  let firstRowKeys = null;
  payload.data.forEach((row, index) => {
    const actualKeys = validateRow(row, testCase, issues, index);
    if (!firstRowKeys) firstRowKeys = actualKeys;
  });

  return {
    outcome: issues.length === 0 ? "pass" : "fail",
    issues,
    rowCount,
    topLevelKeys,
    firstRowKeys,
  };
}

function auditNoticeResponse(testCase, payload) {
  const issues = [];

  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { outcome: "fail", issues: [`top-level payload should be object, got ${Array.isArray(payload) ? "array" : typeof payload}`] };
  }

  const topLevelKeys = Object.keys(payload);
  if (JSON.stringify(topLevelKeys) !== JSON.stringify(testCase.topLevelKeys)) {
    issues.push(`top-level keys mismatch, expected ${JSON.stringify(testCase.topLevelKeys)}, got ${JSON.stringify(topLevelKeys)}`);
  }

  if (payload.code !== 600) {
    issues.push(`notice code should be 600, got ${JSON.stringify(payload.code)}`);
  }

  if (!payload.data || typeof payload.data !== "object" || Array.isArray(payload.data)) {
    issues.push(`notice data should be object, got ${Array.isArray(payload.data) ? "array" : typeof payload.data}`);
    return { outcome: "fail", issues, topLevelKeys };
  }

  const dataKeys = Object.keys(payload.data);
  if (JSON.stringify(dataKeys) !== JSON.stringify(testCase.expectedFields)) {
    issues.push(`notice data keys mismatch, expected ${JSON.stringify(testCase.expectedFields)}, got ${JSON.stringify(dataKeys)}`);
  }

  if (typeof payload.data.content !== "string") {
    issues.push(`notice content should be string, got ${typeof payload.data.content}`);
  }

  return {
    outcome: issues.length === 0 ? "pass" : "fail",
    issues,
    topLevelKeys,
    firstRowKeys: dataKeys,
  };
}

async function auditCase(baseUrl, testCase) {
  const url = buildUrl(baseUrl, testCase.path, testCase.query);

  try {
    const response = await fetch(url);
    const text = await response.text();

    let payload;
    try {
      payload = JSON.parse(text);
    } catch {
      return {
        module: testCase.module,
        path: testCase.path,
        query: testCase.query,
        url,
        statusCode: response.status,
        outcome: "fail",
        issues: ["response body is not valid JSON"],
      };
    }

    if (response.status !== 200) {
      return {
        module: testCase.module,
        path: testCase.path,
        query: testCase.query,
        url,
        statusCode: response.status,
        outcome: "fail",
        issues: [`expected HTTP 200, got ${response.status}`],
      };
    }

    const audited = testCase.path === "/api/index/notice"
      ? auditNoticeResponse(testCase, payload)
      : auditStandardResponse(testCase, payload);

    return {
      module: testCase.module,
      path: testCase.path,
      query: testCase.query,
      url,
      statusCode: response.status,
      outcome: audited.outcome,
      issues: audited.issues,
      rowCount: audited.rowCount ?? null,
      topLevelKeys: audited.topLevelKeys ?? null,
      firstRowKeys: audited.firstRowKeys ?? null,
    };
  } catch (error) {
    return {
      module: testCase.module,
      path: testCase.path,
      query: testCase.query,
      url,
      statusCode: 0,
      outcome: "fail",
      issues: [`request failed: ${error}`],
    };
  }
}

async function main() {
  const cases = buildCases();
  const results = [];
  for (const testCase of cases) {
    results.push(await auditCase(BASE_URL, testCase));
  }

  const summary = {
    baseUrl: BASE_URL,
    webId: WEB_ID,
    type: TYPE_ID,
    generatedAt: new Date().toISOString(),
    totalCases: results.length,
    passCount: results.filter((item) => item.outcome === "pass").length,
    warningCount: results.filter((item) => item.outcome === "warning").length,
    failCount: results.filter((item) => item.outcome === "fail").length,
    results,
  };

  fs.writeFileSync(RESULTS_FILE, `${JSON.stringify(summary, null, 2)}\n`, "utf8");

  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Cases: ${summary.totalCases}`);
  console.log(`Pass: ${summary.passCount}  Warning: ${summary.warningCount}  Fail: ${summary.failCount}`);
  console.log(`Report: ${RESULTS_FILE}`);
  console.log("");

  for (const item of results) {
    if (item.outcome === "pass") continue;
    console.log(`[${item.outcome.toUpperCase()}] ${item.module} ${item.path} ${JSON.stringify(item.query)}`);
    for (const issue of item.issues) {
      console.log(`  - ${issue}`);
    }
  }

  process.exit(summary.failCount === 0 ? 0 : 1);
}

await main();
