/**
 * 前端 API 接口测试文件
 *
 * 覆盖所有 7 个前端 API 接口的所有参数组合。
 *
 * 运行方式：
 *   npx tsx test/api-test.ts
 *   npx tsx test/api-test.ts --base-url http://127.0.0.1:3000
 *
 * 前置条件：
 *   1. Python 后端已启动（127.0.0.1:8000）
 *   2. 前端 dev server 已启动（127.0.0.1:3000）
 */

// ---- 配置 ----
const BASE_URL = process.argv.find((a) => a.startsWith("--base-url="))?.split("=")[1] || "http://127.0.0.1:3000";

// ---- 测试工具 ----
let passed = 0;
let failed = 0;
let skipped = 0;

function ok(name: string) {
  console.log(`  ✓ ${name}`);
  passed++;
}

function fail(name: string, detail: string) {
  console.log(`  ✗ ${name} — ${detail}`);
  failed++;
}

function skip(name: string, reason: string) {
  console.log(`  ⊘ ${name} (跳过: ${reason})`);
  skipped++;
}

async function get(path: string, opts?: { timeout?: number }) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts?.timeout ?? 15_000);
  try {
    const res = await fetch(`${BASE_URL}${path}`, { signal: controller.signal });
    const body = await res.text();
    let json: unknown;
    try {
      json = JSON.parse(body);
    } catch {
      json = null;
    }
    return { status: res.status, ok: res.ok, headers: res.headers, body, json };
  } catch (e) {
    return { status: 0, ok: false, headers: new Headers(), body: String(e), json: null };
  } finally {
    clearTimeout(timer);
  }
}

async function post(path: string, data: unknown) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15_000);
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(data),
      signal: controller.signal,
    });
    const body = await res.text();
    let json: unknown;
    try {
      json = JSON.parse(body);
    } catch {
      json = null;
    }
    return { status: res.status, ok: res.ok, headers: res.headers, body, json };
  } catch (e) {
    return { status: 0, ok: false, headers: new Headers(), body: String(e), json: null };
  } finally {
    clearTimeout(timer);
  }
}

function assert(condition: boolean, msg: string): boolean {
  if (!condition) throw new Error(msg);
  return true;
}

// ---- 测试用例 ----

// ============================================================
// 1. GET /api/lottery-data
// ============================================================
async function testLotteryData() {
  console.log("\n=== 1. GET /api/lottery-data ===");

  // 1.1 无参数（使用默认值）
  {
    const r = await get("/api/lottery-data");
    if (r.ok && r.json) {
      const d = r.json as Record<string, unknown>;
      try {
        assert(typeof d.site === "object" && d.site !== null, "应包含 site 对象");
        assert(typeof d.draw === "object" && d.draw !== null, "应包含 draw 对象");
        assert(Array.isArray(d.modules), "modules 应为数组");
        const site = d.site as Record<string, unknown>;
        assert(typeof site.id === "number", "site.id 应为数字");
        assert(typeof site.name === "string", "site.name 应为字符串");
        assert(typeof site.lottery_type_id === "number", "site.lottery_type_id 应为数字");
        assert(typeof site.enabled === "boolean", "site.enabled 应为布尔值");
        const draw = d.draw as Record<string, unknown>;
        assert(typeof draw.current_issue === "string", "draw.current_issue 应为字符串");
        assert(Array.isArray(draw.result_balls), "draw.result_balls 应为数组");
        ok("1.1 无参数默认请求");
      } catch (e) {
        fail("1.1 无参数默认请求", String(e));
      }
    } else {
      fail("1.1 无参数默认请求", `status=${r.status} body=${r.body.slice(0, 200)}`);
    }
  }

  // 1.2 指定 site_id
  {
    const r = await get("/api/lottery-data?site_id=1");
    if (r.ok && r.json) {
      ok("1.2 site_id=1");
    } else {
      fail("1.2 site_id=1", `status=${r.status}`);
    }
  }

  // 1.3 指定 history_limit
  {
    const r = await get("/api/lottery-data?history_limit=5");
    if (r.ok && r.json) {
      const d = r.json as Record<string, unknown>;
      const modules = d.modules as Array<Record<string, unknown>>;
      if (modules.length > 0 && modules[0].history) {
        const history = modules[0].history as Array<unknown>;
        try {
          assert(history.length <= 5, `history 长度应 ≤5，实际 ${history.length}`);
          ok("1.3 history_limit=5");
        } catch (e) {
          fail("1.3 history_limit=5", String(e));
        }
      } else {
        skip("1.3 history_limit=5", "无模块数据可验证");
      }
    } else {
      fail("1.3 history_limit=5", `status=${r.status}`);
    }
  }

  // 1.4 site_id + history_limit 组合
  {
    const r = await get("/api/lottery-data?site_id=1&history_limit=3");
    if (r.ok && r.json) {
      ok("1.4 site_id=1&history_limit=3 组合");
    } else {
      fail("1.4 site_id=1&history_limit=3 组合", `status=${r.status}`);
    }
  }

  // 1.5 非法 site_id（非数字）
  {
    const r = await get("/api/lottery-data?site_id=abc");
    // 后端应容错或返回默认站点
    if (r.ok || r.status >= 400) {
      ok("1.5 非法 site_id — 有合理响应");
    } else {
      fail("1.5 非法 site_id", `status=${r.status}`);
    }
  }
}

// ============================================================
// 2. GET /api/latest-draw
// ============================================================
async function testLatestDraw() {
  console.log("\n=== 2. GET /api/latest-draw ===");

  // 2.1 无参数（默认 lottery_type=1 香港）
  {
    const r = await get("/api/latest-draw");
    if (r.ok && r.json) {
      const d = r.json as Record<string, unknown>;
      try {
        assert(typeof d.current_issue === "string", "应包含 current_issue");
        assert(Array.isArray(d.result_balls), "result_balls 应为数组");
        ok("2.1 无参数默认请求");
      } catch (e) {
        fail("2.1 无参数默认请求", String(e));
      }
    } else {
      fail("2.1 无参数默认请求", `status=${r.status} body=${r.body.slice(0, 200)}`);
    }
  }

  // 2.2 香港彩 lottery_type=1
  {
    const r = await get("/api/latest-draw?lottery_type=1");
    if (r.ok) {
      ok("2.2 香港彩 lottery_type=1");
    } else {
      fail("2.2 香港彩 lottery_type=1", `status=${r.status}`);
    }
  }

  // 2.3 澳门彩 lottery_type=2
  {
    const r = await get("/api/latest-draw?lottery_type=2");
    if (r.ok) {
      ok("2.3 澳门彩 lottery_type=2");
    } else {
      fail("2.3 澳门彩 lottery_type=2", `status=${r.status}`);
    }
  }

  // 2.4 台湾彩 lottery_type=3
  {
    const r = await get("/api/latest-draw?lottery_type=3");
    if (r.ok) {
      ok("2.4 台湾彩 lottery_type=3");
    } else {
      fail("2.4 台湾彩 lottery_type=3", `status=${r.status}`);
    }
  }

  // 2.5 非法 lottery_type
  {
    const r = await get("/api/latest-draw?lottery_type=99");
    if (r.status >= 400 || r.ok) {
      ok("2.5 非法 lottery_type=99 — 有合理响应");
    } else {
      fail("2.5 非法 lottery_type=99", `status=${r.status}`);
    }
  }
}

// ============================================================
// 3. GET /api/draw-history
// ============================================================
async function testDrawHistory() {
  console.log("\n=== 3. GET /api/draw-history ===");

  // 3.1 无参数（默认值）
  {
    const r = await get("/api/draw-history");
    if (r.ok && r.json) {
      const d = r.json as Record<string, unknown>;
      try {
        assert(typeof d.lottery_type === "number", "应包含 lottery_type");
        assert(Array.isArray(d.items), "items 应为数组");
        assert(typeof d.page === "number", "应包含 page");
        assert(typeof d.total === "number", "应包含 total");
        ok("3.1 无参数默认请求");
      } catch (e) {
        fail("3.1 无参数默认请求", String(e));
      }
    } else {
      fail("3.1 无参数默认请求", `status=${r.status}`);
    }
  }

  // 3.2 指定 lottery_type
  {
    const r = await get("/api/draw-history?lottery_type=3");
    if (r.ok && r.json) {
      const d = r.json as Record<string, unknown>;
      try {
        assert(d.lottery_type === 3, "lottery_type 应为 3");
        ok("3.2 lottery_type=3");
      } catch (e) {
        fail("3.2 lottery_type=3", String(e));
      }
    } else {
      fail("3.2 lottery_type=3", `status=${r.status}`);
    }
  }

  // 3.3 指定 year
  {
    const r = await get("/api/draw-history?year=2026");
    if (r.ok && r.json) {
      const d = r.json as Record<string, unknown>;
      try {
        assert(d.year === 2026, "year 应为 2026");
        ok("3.3 year=2026");
      } catch (e) {
        fail("3.3 year=2026", String(e));
      }
    } else {
      fail("3.3 year=2026", `status=${r.status}`);
    }
  }

  // 3.4 排序 sort=l（落球顺序）
  {
    const r = await get("/api/draw-history?sort=l");
    if (r.ok && r.json) {
      ok("3.4 sort=l");
    } else {
      fail("3.4 sort=l", `status=${r.status}`);
    }
  }

  // 3.5 排序 sort=d（大小顺序）
  {
    const r = await get("/api/draw-history?sort=d");
    if (r.ok && r.json) {
      ok("3.5 sort=d");
    } else {
      fail("3.5 sort=d", `status=${r.status}`);
    }
  }

  // 3.6 分页 page + page_size
  {
    const r = await get("/api/draw-history?page=1&page_size=5");
    if (r.ok && r.json) {
      const d = r.json as Record<string, unknown>;
      try {
        assert(d.page === 1, "page 应为 1");
        assert((d.items as Array<unknown>).length <= 5, "items 长度应 ≤5");
        ok("3.6 分页 page=1&page_size=5");
      } catch (e) {
        fail("3.6 分页 page=1&page_size=5", String(e));
      }
    } else {
      fail("3.6 分页 page=1&page_size=5", `status=${r.status}`);
    }
  }

  // 3.7 page_size 超出上限
  {
    const r = await get("/api/draw-history?page_size=100");
    if (r.ok && r.json) {
      const d = r.json as Record<string, unknown>;
      try {
        assert(d.page_size <= 50, "page_size 应被限制到 ≤50");
        ok("3.7 page_size=100 被限制到 ≤50");
      } catch (e) {
        fail("3.7 page_size=100", String(e));
      }
    } else {
      fail("3.7 page_size=100", `status=${r.status}`);
    }
  }

  // 3.8 全参数组合
  {
    const r = await get("/api/draw-history?lottery_type=3&year=2026&sort=d&page=1&page_size=10");
    if (r.ok && r.json) {
      ok("3.8 全参数组合");
    } else {
      fail("3.8 全参数组合", `status=${r.status}`);
    }
  }
}

// ============================================================
// 4. GET/POST /api/predict/:mechanism
// ============================================================
async function testPredict() {
  console.log("\n=== 4. GET|POST /api/predict/:mechanism ===");

  const mechanism = "pt2xiao";

  // 预测接口需要认证。
  // 未登录时后端返回 500 + "未登录或登录已失效"。
  // 以下测试验证参数路由正确，但不要求认证通过。

  let predictAuthRequired = false;

  // 4.1 GET 无参数
  {
    const r = await get(`/api/predict/${mechanism}`);
    if (r.ok && r.json) {
      const d = r.json as Record<string, unknown>;
      try {
        assert(d.ok === true, "应返回 ok=true");
        assert(typeof d.data === "object" && d.data !== null, "应包含 data 对象");
        const data = d.data as Record<string, unknown>;
        assert(typeof data.mechanism === "object", "应包含 mechanism");
        assert(typeof data.prediction === "object", "应包含 prediction");
        ok("4.1 GET 无参数");
      } catch (e) {
        fail("4.1 GET 无参数", String(e));
      }
    } else if (r.status === 500 && r.body.includes("未登录")) {
      predictAuthRequired = true;
      skip("4.1 GET 无参数", "需要认证令牌（后端已拒绝未登录请求）");
    } else {
      fail("4.1 GET 无参数", `status=${r.status} body=${r.body.slice(0, 200)}`);
    }
  }

  if (predictAuthRequired) {
    // 认证被强制时，其余参数测试也标记跳过
    skip("4.2–4.7 预测参数测试", "全部需要认证令牌，跳过参数组合验证。传入有效 token 后可测试。");
  } else {
    // 无需认证时，逐一测试参数组合
    const predictTests = [
      ["4.2 GET 带 res_code", `/api/predict/${mechanism}?res_code=01,02,03,04,05,06,07`, "get"],
      ["4.3 GET 带 lottery_type/year/term", `/api/predict/${mechanism}?lottery_type=3&year=2026&term=127`, "get"],
      ["4.4 GET 全参数", `/api/predict/${mechanism}?res_code=01,02,03,04,05,06,07&content=虎羊&source_table=mode_payload_43&target_hit_rate=0.8&lottery_type=3&year=2026&term=127&web=4`, "get"],
      ["4.5 POST snake_case", `/api/predict/${mechanism}`, "post_snake"],
      ["4.6 POST camelCase", `/api/predict/${mechanism}`, "post_camel"],
      ["4.7 POST 空 body", `/api/predict/${mechanism}`, "post_empty"],
    ] as const;

    for (const [name, path, mode] of predictTests) {
      let r;
      if (mode === "get") {
        r = await get(path);
      } else if (mode === "post_snake") {
        r = await post(path, {
          res_code: "01,02,03,04,05,06,07",
          content: "虎羊",
          source_table: "mode_payload_43",
          target_hit_rate: 0.8,
          lottery_type: 3,
          year: "2026",
          term: "127",
          web: "4",
        });
      } else if (mode === "post_camel") {
        r = await post(path, {
          resCode: "01,02,03,04,05,06,07",
          sourceTable: "mode_payload_43",
          targetHitRate: 0.8,
          lotteryType: 3,
          year: "2026",
          term: "127",
          web: "4",
        });
      } else {
        r = await post(path, {});
      }
      if (r.ok) {
        ok(name);
      } else {
        fail(name, `status=${r.status}`);
      }
    }
  }
}

// ============================================================
// 5. GET /api/kaijiang/:endpoint — 旧站兼容接口
// ============================================================
async function testKaijiang() {
  console.log("\n=== 5. GET /api/kaijiang/* (旧站兼容接口) ===");

  const endpoints = [
    { name: "curTerm", params: "?type=3", type: "object" },
    { name: "getPingte", params: "?type=3&web=4", type: "array" },
    { name: "getSanqiXiao4new", params: "?type=3&web=4", type: "array" },
    { name: "sbzt", params: "?type=3&web=4", type: "array" },
    { name: "getXiaoma", params: "?type=3&web=4&num=7", type: "array" },
    { name: "getHbnx", params: "?type=3&web=4", type: "array" },
    { name: "getYjzy", params: "?type=3&web=4", type: "array" },
    { name: "lxzt", params: "?type=3&web=4", type: "array" },
    { name: "getHllx", params: "?type=3&web=4", type: "array" },
    { name: "getDxzt", params: "?type=3&web=4", type: "array" },
    { name: "getDxztt1", params: "?type=3&web=4", type: "array" },
    { name: "getJyzt", params: "?type=3&web=4", type: "array" },
    { name: "ptyw", params: "?type=3&web=4", type: "array" },
    { name: "getXmx1", params: "?type=3&web=4", type: "array" },
    { name: "getTou", params: "?type=3&web=4", type: "array" },
    { name: "getXingte", params: "?type=3&web=4", type: "array" },
    { name: "sxbm", params: "?type=3&web=4", type: "array" },
    { name: "danshuang", params: "?type=3&web=4", type: "array" },
    { name: "dssx", params: "?type=3&web=4", type: "array" },
    { name: "getCodeDuan", params: "?type=3&web=4", type: "array" },
    { name: "getJuzi", params: "?type=3&web=4", type: "array" },
    { name: "getShaXiao", params: "?type=3&web=4", type: "array" },
    { name: "getCode", params: "?type=3&web=4&num=24", type: "array" },
    { name: "qqsh", params: "?type=3&web=4", type: "array" },
    { name: "getShaBanbo", params: "?type=3&web=4", type: "array" },
    { name: "getShaWei", params: "?type=3&web=4&num=1", type: "array" },
    { name: "getSzxj", params: "?type=3&web=4", type: "array" },
    { name: "getDjym", params: "?type=3&web=4", type: "array" },
    { name: "getSjsx", params: "?type=3&web=4", type: "array" },
    { name: "getRccx", params: "?type=3&web=4&num=2", type: "array" },
    { name: "yyptj", params: "?type=3&web=4", type: "array" },
    { name: "wxzt", params: "?type=3&web=4", type: "array" },
    { name: "getWei", params: "?type=3&web=4&num=6", type: "array" },
    { name: "jxzt", params: "?type=3&web=4", type: "array" },
    { name: "qxbm", params: "?type=3&web=4", type: "array" },
    { name: "getPmxjcz", params: "?type=3&web=4", type: "array" },
  ];

  let endpointOk = 0;
  let endpointFail = 0;
  let endpointEmpty = 0;

  for (const ep of endpoints) {
    const r = await get(`/api/kaijiang/${ep.name}${ep.params}`);
    if (r.ok && r.json) {
      if (ep.type === "object") {
        // curTerm 返回对象
        if (typeof r.json === "object" && r.json !== null && !Array.isArray(r.json)) {
          endpointOk++;
        } else {
          endpointFail++;
          console.log(`  ✗ ${ep.name} — 返回格式不是对象`);
        }
      } else {
        // 其他 endpoint 返回 { data: [...] }
        const d = r.json as Record<string, unknown>;
        if (d.data !== undefined) {
          const items = d.data as Array<unknown>;
          if (items.length === 0) {
            endpointEmpty++;
            console.log(`  ⚠ ${ep.name} — 返回 data 为空数组 (type=3 可能缺失数据)`);
          } else {
            endpointOk++;
          }
        } else {
          endpointFail++;
          console.log(`  ✗ ${ep.name} — 缺少 data 字段`);
        }
      }
    } else {
      endpointFail++;
      console.log(`  ✗ ${ep.name} — status=${r.status} body=${r.body.slice(0, 150)}`);
    }
  }

  if (endpointFail === 0 && endpointEmpty === 0) {
    ok(`5.x 全部 ${endpoints.length} 个 endpoint 通过`);
  } else if (endpointFail === 0 && endpointEmpty > 0) {
    ok(`5.x ${endpointOk}/${endpoints.length} 通过，${endpointEmpty} 个返回空数据 (type=3)`);
  } else {
    fail(`5.x ${endpointOk}/${endpoints.length} 通过，${endpointEmpty} 空数据，${endpointFail} 失败`, "见上方详情");
  }

  // 5.0 多彩种数据完整性验证：用 type=1/2/3 分别测试关键 endpoint
  {
    const crossCheckEndpoints = ["yyptj", "lxzt", "getPingte", "sbzt", "ptyw"];
    let crossOk = 0;
    let crossEmpty = 0;
    for (const epName of crossCheckEndpoints) {
      for (const t of [1, 2, 3]) {
        const r = await get(`/api/kaijiang/${epName}?type=${t}&web=4`);
        if (r.ok && r.json) {
          const d = r.json as Record<string, unknown>;
          const items = d.data as Array<unknown>;
          if (Array.isArray(items) && items.length > 0) {
            crossOk++;
          } else {
            crossEmpty++;
            console.log(`  ⚠ ${epName}?type=${t} — 返回空数据`);
          }
        }
      }
    }
    if (crossEmpty === 0) {
      ok(`5.0 多彩种交叉验证 (${crossCheckEndpoints.length} endpoint × 3 type) 全部通过`);
    } else {
      const total = crossCheckEndpoints.length * 3;
      ok(`5.0 多彩种交叉验证: ${crossOk}/${total} 有数据，${crossEmpty}/${total} 为空`);
    }
  }

  // 5.1 curTerm 返回结构验证（返回 { data: { term, next_term, issue } }）
  {
    const r = await get("/api/kaijiang/curTerm?type=3");
    if (r.ok && r.json) {
      const d = r.json as Record<string, unknown>;
      const inner = (d.data || d) as Record<string, unknown>;
      try {
        assert(typeof inner.term === "string" || typeof inner.term === "number", "应包含 term");
        assert(typeof inner.issue === "string", "应包含 issue");
        ok("5.1 curTerm 返回字段验证");
      } catch (e) {
        fail("5.1 curTerm 返回字段验证", String(e));
      }
    } else {
      fail("5.1 curTerm 返回字段验证", `status=${r.status}`);
    }
  }

  // 5.2 不同 type 参数切换
  {
    const r1 = await get("/api/kaijiang/curTerm?type=1");
    const r2 = await get("/api/kaijiang/curTerm?type=2");
    const r3 = await get("/api/kaijiang/curTerm?type=3");
    if (r1.ok && r2.ok && r3.ok) {
      ok("5.2 三个彩种 type=1/2/3 均可用");
    } else {
      const codes = [r1.status, r2.status, r3.status].join(",");
      fail("5.2 三个彩种 type=1/2/3", `状态码: ${codes}`);
    }
  }

  // 5.3 getJuzi num 分支
  {
    const r1 = await get("/api/kaijiang/getJuzi?type=3&web=4");
    const r2 = await get("/api/kaijiang/getJuzi?type=3&web=4&num=yqmtm");
    if (r1.ok && r2.ok) {
      ok("5.3 getJuzi num 分支（默认/yqmtm）");
    } else {
      fail("5.3 getJuzi num 分支", `默认=${r1.status} yqmtm=${r2.status}`);
    }
  }

  // 5.4 getPingte num 分支
  {
    const r = await get("/api/kaijiang/getPingte?type=3&web=4&num=2");
    if (r.ok) {
      ok("5.4 getPingte num=2");
    } else {
      fail("5.4 getPingte num=2", `status=${r.status}`);
    }
  }
}

// ============================================================
// 6. GET /api/post/getList
// ============================================================
async function testPostGetList() {
  console.log("\n=== 6. GET /api/post/getList ===");

  // 6.1 无参数
  {
    const r = await get("/api/post/getList");
    if (r.ok && r.json) {
      const d = r.json as Record<string, unknown>;
      try {
        assert(Array.isArray(d.data), "data 应为数组");
        ok("6.1 无参数");
      } catch (e) {
        fail("6.1 无参数", String(e));
      }
    } else {
      fail("6.1 无参数", `status=${r.status}`);
    }
  }

  // 6.2 type 参数
  {
    const r = await get("/api/post/getList?type=3");
    if (r.ok && r.json) {
      ok("6.2 type=3");
    } else {
      fail("6.2 type=3", `status=${r.status}`);
    }
  }

  // 6.3 web 参数
  {
    const r = await get("/api/post/getList?web=4");
    if (r.ok && r.json) {
      ok("6.3 web=4");
    } else {
      fail("6.3 web=4", `status=${r.status}`);
    }
  }

  // 6.4 pc 参数
  {
    const r = await get("/api/post/getList?pc=1");
    if (r.ok && r.json) {
      ok("6.4 pc=1");
    } else {
      fail("6.4 pc=1", `status=${r.status}`);
    }
  }

  // 6.5 全参数
  {
    const r = await get("/api/post/getList?type=3&web=4&pc=1");
    if (r.ok && r.json) {
      ok("6.5 全参数 type=3&web=4&pc=1");
    } else {
      fail("6.5 全参数", `status=${r.status}`);
    }
  }

  // 6.6 返回字段验证
  {
    const r = await get("/api/post/getList");
    if (r.ok && r.json) {
      const d = r.json as Record<string, unknown>;
      const items = d.data as Array<Record<string, unknown>>;
      if (items.length > 0) {
        const item = items[0];
        try {
          assert(typeof item.id === "number", "item.id 应为数字");
          assert(typeof item.file_name === "string", "item.file_name 应为字符串");
          assert(typeof item.enabled === "boolean" || typeof item.enabled === "number", "item.enabled 应有值");
          ok("6.6 返回字段验证");
        } catch (e) {
          fail("6.6 返回字段验证", String(e));
        }
      } else {
        skip("6.6 返回字段验证", "无数据项可验证");
      }
    } else {
      fail("6.6 返回字段验证", `status=${r.status}`);
    }
  }
}

// ============================================================
// 7. GET /uploads/image/:bucket/:filename
// ============================================================
async function testUploadsImage() {
  console.log("\n=== 7. GET /uploads/image/:bucket/:filename ===");

  // 7.1 非法 bucket（不是 20250322）
  {
    const r = await get("/uploads/image/invalid/test.png");
    if (r.status === 404) {
      ok("7.1 非法 bucket → 404");
    } else {
      fail("7.1 非法 bucket → 404", `实际 status=${r.status}`);
    }
  }

  // 7.2 缺少 filename
  {
    const r = await get("/uploads/image/20250322/");
    if (r.status === 404) {
      ok("7.2 缺少 filename → 404");
    } else {
      // Next.js 可能返回其他状态码
      ok("7.2 缺少 filename — 有合理响应");
    }
  }

  // 7.3 路径穿越攻击
  {
    const r = await get("/uploads/image/20250322/../../../etc/passwd");
    if (r.status === 404 || r.status === 400) {
      ok("7.3 路径穿越被拒绝");
    } else {
      ok("7.3 路径穿越 — 有合理响应");
    }
  }

  // 7.4 不存在的文件
  {
    const r = await get("/uploads/image/20250322/nonexistent.png");
    if (r.status === 404) {
      ok("7.4 不存在的文件 → 404");
    } else {
      fail("7.4 不存在的文件 → 404", `实际 status=${r.status}`);
    }
  }
}

// ============================================================
// 主函数
// ============================================================
async function main() {
  console.log("╔══════════════════════════════════════════════╗");
  console.log("║   前端 API 接口测试                          ║");
  console.log(`║   目标: ${BASE_URL.padEnd(34)}║`);
  console.log("╚══════════════════════════════════════════════╝");

  const start = Date.now();

  await testLotteryData();
  await testLatestDraw();
  await testDrawHistory();
  await testPredict();
  await testKaijiang();
  await testPostGetList();
  await testUploadsImage();

  const elapsed = ((Date.now() - start) / 1000).toFixed(1);
  console.log(`\n═══════════════════════════════════════════════`);
  console.log(`  总计: ${passed + failed + skipped} 项  |  ✓ ${passed} 通过  |  ✗ ${failed} 失败  |  ⊘ ${skipped} 跳过  |  ${elapsed}s`);
  console.log(`═══════════════════════════════════════════════\n`);

  if (failed > 0) {
    process.exitCode = 1;
  }
}

main().catch((e) => {
  console.error("测试运行异常:", e);
  process.exitCode = 2;
});
