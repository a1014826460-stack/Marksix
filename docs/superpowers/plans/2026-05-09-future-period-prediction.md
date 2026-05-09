# Future Period Prediction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `bulk_generate_site_prediction_data` to optionally generate predictions for 1-2 future (unopened) lottery periods after processing opened draws.

**Architecture:** Two-file change. `predict()` gains a `random_seed` param to differentiate adjacent future periods. `bulk_generate_site_prediction_data()` gains a `future_periods` payload field — after the existing opened-draw loop, it loops over computed future (year, term) pairs, calling `predict(res_code=None, random_seed=...)` for each.

**Tech Stack:** Python 3.12 stdlib (random, hashlib), existing PostgreSQL/SQLite via `db.connect`

---

### Task 1: Add `random_seed` parameter to `predict()`

**Files:**
- Modify: `d:/pythonProject/outsource/Liuhecai/backend/src/predict/common.py:496-503`

- [ ] **Step 1: Add `random_seed` to function signature and seed logic**

Replace the function signature and insert seed logic at line 503-508:

```python
def predict(
    config: PredictionConfig,
    res_code: str | None = None,
    content: str | None = None,
    source_table: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
    target_hit_rate: float = DEFAULT_TARGET_HIT_RATE,
    random_seed: str | None = None,
) -> dict[str, Any]:
    """统一预测入口，供脚本和前端 API 复用。

    :param random_seed: 可选随机种子字符串。传入时用于固定随机数生成器状态，
        确保同一种子产生相同预测结果，不同种子（如不同期号）产生不同结果。
        用于未来期预测的差异性保证。
    """
    if random_seed is not None:
        seed_int = int(hashlib.sha256(random_seed.encode()).hexdigest(), 16) % (2**32)
        random.seed(seed_int)

    table_name = source_table or config.default_table
```

The import `hashlib` must be added at the top of common.py. Check if it's already imported — if not, add:

```python
import hashlib
```

- [ ] **Step 2: Syntax check common.py**

Run: `cd d:/pythonProject/outsource/Liuhecai/backend/src && python -c "import ast; ast.parse(open('predict/common.py', encoding='utf-8').read()); print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/src/predict/common.py
git commit -m "feat: add random_seed parameter to predict() for future period differentiation"
```

---

### Task 2: Add `_compute_next_issue` helper and `future_periods` logic to `bulk_generate_site_prediction_data`

**Files:**
- Modify: `d:/pythonProject/outsource/Liuhecai/backend/src/admin/prediction.py:689-863`

- [ ] **Step 1: Add `_compute_next_issue` helper function**

Insert before `bulk_generate_site_prediction_data` (around line 662):

```python
def _compute_next_issue(year: int, term: int, offset: int) -> tuple[int, int]:
    """从当前 (year, term) 计算未来第 offset 期的期号。

    一期 = term + 1。term 上限按 365 期/年处理：超过后年份 +1，term 减去 365。

    :param year: 当前年份
    :param term: 当前期号
    :param offset: 偏移量（1 = T+1, 2 = T+2）
    :return: (next_year, next_term)
    """
    MAX_TERMS_PER_YEAR = 365
    new_term = term + offset
    new_year = year
    while new_term > MAX_TERMS_PER_YEAR:
        new_term -= MAX_TERMS_PER_YEAR
        new_year += 1
    return new_year, new_term
```

- [ ] **Step 2: Read `future_periods` from payload and compute future draws**

After line 727 (`if not draws: raise ValueError(...)`), insert the future draws construction:

```python
        # ── 未来期预测数据构造（res_code 为空，基于历史数据预测）──
        future_periods = int(payload.get("future_periods") or 0)
        future_draws: list[dict[str, Any]] = []
        if future_periods > 0:
            # 取最新一期已开奖记录作为基准
            latest = draws[-1]
            for offset in range(1, future_periods + 1):
                fy, ft = _compute_next_issue(latest["year"], latest["term"], offset)
                future_draws.append({
                    "year": fy,
                    "term": ft,
                    "numbers_str": "",  # 无开奖号码
                    "_future": True,    # 标记为未来期
                })
```

- [ ] **Step 3: Extend the per-draw loop to handle future draws**

After the existing `for draw in draws:` loop's closing (after line 848, before `module_reports.append`), add a parallel loop for future draws. The key differences from the existing loop:
- Uses `res_code=None` (not `safe_res_code`)
- Uses `random_seed=f"{draw['year']}{draw['term']:03d}"`
- Sets `res_code=""`, `res_sx=""`, `res_color=""` explicitly
- Skips `mode_id==65` (特码段数 needs actual winning numbers)
- Does NOT compute `res_sx`/`res_color` from `_compute_res_fields` (no draw data)

Insert this code block right after the closing of `for draw in draws:` (after line 841, before `module_reports.append(module_report)` at line 848):

```python
            # ── 未来期生成（T+1, T+2 ...）──
            for fdraw in future_draws:
                try:
                    # mode_id=65 特码段数依赖真实开奖号码，未来期跳过
                    if mode_id == 65:
                        continue

                    fy_year = str(fdraw["year"])
                    fy_term = str(fdraw["term"])
                    fy_seed = f"{fdraw['year']}{fdraw['term']:03d}"

                    result = predict(
                        config=config,
                        res_code=None,
                        source_table=table_name,
                        db_path=db_path,
                        target_hit_rate=DEFAULT_TARGET_HIT_RATE,
                        random_seed=fy_seed,
                    )
                    row_data = build_generated_prediction_row_data(
                        mode_id=mode_id,
                        lottery_type=str(lottery_type),
                        year=fy_year,
                        term=fy_term,
                        web_value="4",
                        res_code="",
                        generated_content=result["prediction"]["content"],
                    )
                    # 未来期无开奖数据，res_sx/res_color 强制为空
                    row_data["res_sx"] = ""
                    row_data["res_color"] = ""
                    stored = upsert_created_prediction_row(conn, table_name, row_data)
                    if stored.get("action") == "inserted":
                        module_report["inserted"] += 1
                        total_inserted += 1
                    else:
                        module_report["updated"] += 1
                        total_updated += 1
                except Exception as exc:
                    conn.rollback()
                    module_report["errors"] += 1
                    total_errors += 1
                    if not module_report["error_message"]:
                        module_report["error_message"] = str(exc)
```

- [ ] **Step 4: Add `future_periods` to the return dict**

After line 856 (`"web_id": 4,`), add:

```python
            "future_periods": future_periods,
```

- [ ] **Step 5: Syntax check admin/prediction.py**

Run: `cd d:/pythonProject/outsource/Liuhecai/backend/src && python -c "import ast; ast.parse(open('admin/prediction.py', encoding='utf-8').read()); print('OK')"`

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/src/admin/prediction.py
git commit -m "feat: add future_periods support to bulk_generate_site_prediction_data"
```

---

### Task 3: Verification

**Files:**
- Modify: none (verification only)

- [ ] **Step 1: Full syntax check of all affected files**

Run: `cd d:/pythonProject/outsource/Liuhecai/backend/src && python -c "
import ast
for f in ['predict/common.py', 'admin/prediction.py']:
    ast.parse(open(f, encoding='utf-8').read())
    print(f'OK: {f}')
"`

Expected: Both files `OK`

- [ ] **Step 2: Start server and test existing behavior (backward compat)**

```bash
cd d:/pythonProject/outsource/Liuhecai/backend/src
python app.py --host 127.0.0.1 --port 8000 &
sleep 3
```

Verify health:
```bash
curl -s http://127.0.0.1:8000/api/health | python -c "import sys,json; d=json.load(sys.stdin); print('OK:', d['ok'])"
```
Expected: `OK: True`

- [ ] **Step 3: Test generate-all without future_periods (existing path)**

```bash
TOKEN=$(curl -s http://127.0.0.1:8000/api/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")
curl -s -X POST http://127.0.0.1:8000/api/admin/sites/1/prediction-modules/generate-all \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"lottery_type":3,"start_issue":"2026127","end_issue":"2026127","mechanism_keys":["title_234"]}' \
  | python -c "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('ok') else 'FAIL')"
```
Expected: `OK` (returns `{"ok":true,"job_id":"...","message":"..."}`)

- [ ] **Step 4: Check job status**

```bash
sleep 5
JOB_ID=$(curl -s http://127.0.0.1:8000/api/admin/sites/1/prediction-modules/generate-all -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"lottery_type":3,"start_issue":"2026127","end_issue":"2026127","mechanism_keys":["title_234"]}' | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
sleep 3
curl -s "http://127.0.0.1:8000/api/admin/jobs/$JOB_ID" -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; d=json.load(sys.stdin); print('Status:', d.get('status'), 'Inserted:', d.get('result',{}).get('inserted',0))"
```
Expected: `Status: done Inserted: >= 1`

- [ ] **Step 5: Test generate-all WITH future_periods=2 (new feature)**

```bash
curl -s -X POST http://127.0.0.1:8000/api/admin/sites/1/prediction-modules/generate-all \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"lottery_type":3,"start_issue":"2026127","end_issue":"2026127","mechanism_keys":["title_234"],"future_periods":2}' \
  | python -c "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('ok') else 'FAIL', '| job_id:', d.get('job_id','')[:12])"
```
Expected: `OK | job_id: ...`

- [ ] **Step 6: Verify future records exist in DB**

After the job completes, query the created schema for T+1/T+2 records:

```bash
python -c "
from db import connect
conn = connect('postgresql://postgres:2225427@localhost:5432/liuhecai')
rows = conn.execute(
    \"SELECT year, term, res_code, res_sx, res_color, content IS NOT NULL as has_content FROM created.mode_payload_8 WHERE term IN ('128','129') AND year = '2026'\"
).fetchall()
for r in rows:
    print(f'year={r[\"year\"]} term={r[\"term\"]} res_code={r[\"res_code\"]!r} res_sx={r[\"res_sx\"]!r} has_content={r[\"has_content\"]}')
"
```
Expected: Two rows with `res_code=''`, `res_sx=''`, `has_content=True`

- [ ] **Step 7: Run API smoke test**

```bash
cd d:/pythonProject/outsource/Liuhecai/backend/src && python test/api_test.py
```
Expected: Tests pass

- [ ] **Step 8: Commit verification**

```bash
git commit -m "test: verify future_periods prediction generation"
```
(if any test files were modified)
