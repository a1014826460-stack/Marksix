# Prediction Generation Guarantees Continuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the next safe increment of future-draw prediction control: make the control reservation and created-row write atomic, retry a legal candidate after a reservation race, validate cross-year adjacent periods, and extend future-truth taint regression coverage without changing any HTTP API payload.

**Architecture:** Keep `prediction_generation/service.py` as an orchestrator. The control repository owns control-row lifecycle and issue adjacency; the service wraps a future control reservation plus existing created-row persistence in one savepoint, so a failed or skipped created-row write removes the matching reservation. Replanning after a collision reuses the existing verified-rule/candidate APIs and never exposes control metadata.

**Tech Stack:** Python 3, pytest, existing `ConnectionAdapter`, SQLite fixtures, PostgreSQL production adapter, existing created prediction store.

---

## Compatibility Rules

- Do not modify any route, HTTP status, request field, response field, JSON order, or legacy wrapper.
- `prediction_generation_controls` remains internal and stores only candidate-signature hashes and booleans.
- Future draw truth, full draw CSV, target decisions, verified decisions, signatures, and retry details must not enter created-row business fields, HTTP payloads, logs, task reports, or image renderer arguments.
- A failed, skipped, or rolled-back created-row write must leave no new control reservation.

## File Map

| File | Responsibility |
|---|---|
| `backend/src/domains/prediction/generation_control_repository.py` | Control-row deletion, cross-year adjacency lookup, safe savepoint helpers if required. |
| `backend/src/prediction_generation/service.py` | Atomic reservation/persistence orchestration and bounded candidate replan after a reservation collision. |
| `backend/src/tests/unit/test_prediction_generation_control_repository.py` | Cross-year predecessor/successor lookup and internal-only record assertions. |
| `backend/src/tests/unit/test_prediction_generation_control_integration.py` | Atomic rollback and retry integration coverage. |
| `backend/src/tests/unit/test_prediction_future_truth_taint.py` | Verify generated reports and external serializer entry points never contain a full future draw sentinel. |
| `backend/docs/prediction-module-rules.md` | Record the verified-control lifecycle and unsupported module status. |
| `backend/CLAUDE.md` | Record the atomicity and API-compatibility rule for future control changes. |

### Task 1: Make Control Reservation and Created Persistence Atomic

**Files:**
- Modify: `backend/src/prediction_generation/service.py:1893-1992`
- Test: `backend/src/tests/unit/test_prediction_generation_control_integration.py`

- [x] **Step 1: Write the failing rollback/skip tests**

```python
def test_process_module_removes_control_when_created_row_persistence_fails(monkeypatch, tmp_path):
    # Set up a supported mode-470 future row exactly as the existing control test.
    # Make `_persist_generated_row` raise `RuntimeError("write failed")`.
    # Run `_process_single_module`, then query only COUNT(*) from the control table.
    assert report["errors"] == 1
    assert control_count == 0
```

- [x] **Step 2: Verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_generation_control_integration.py::test_process_module_removes_control_when_created_row_persistence_fails
```

Expected: FAIL because the current code reserves the control before persistence and retains it after the persistence exception.

- [x] **Step 3: Implement deferred-commit persistence and cleanup**

Add local savepoint helpers inside `prediction_generation/service.py`:

```python
def _savepoint_name(year: int, term: int, mode_id: int) -> str:
    return f"prediction_control_{year}_{term}_{mode_id}"

# Before reserve_control:
conn.execute(f"SAVEPOINT {savepoint}")
# When reservation cannot be made, created write is skipped, or persistence raises:
conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
conn.execute(f"RELEASE SAVEPOINT {savepoint}")
# Only after `_persist_generated_row` returns inserted or updated:
conn.execute(f"RELEASE SAVEPOINT {savepoint}")
```

Use a generated identifier containing only integer components. Wrap only the controlled-future reservation/persistence block. Do not call `conn.commit()` from this orchestration block; existing persistence may commit in production, so update the created-store API only if the failing test proves a commit prevents savepoint rollback.

- [x] **Step 4: Verify GREEN**

Run the test from Step 2 and the existing control integration file:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_generation_control_integration.py
```

Expected: all pass.

### Task 2: Replan Once After a Reservation Race

**Files:**
- Modify: `backend/src/prediction_generation/service.py:597-688`
- Modify: `backend/src/prediction_generation/service.py:1893-1916`
- Test: `backend/src/tests/unit/test_prediction_generation_control_integration.py`

- [x] **Step 1: Write the failing retry test**

```python
def test_process_module_replans_after_a_single_control_reservation_conflict(monkeypatch, tmp_path):
    # Build a supported mode-470 future row. Make the first `reserve_control`
    # return {"reserved": False, "reason": "reservation_conflict"}; delegate
    # subsequent calls to the real repository function.
    # Capture the persisted row and assert one row is inserted with no
    # `_generation_control` field and `report["errors"] == 0`.
    assert reserve_calls == 2
    assert report["inserted"] == 1
```

- [x] **Step 2: Verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_generation_control_integration.py::test_process_module_replans_after_a_single_control_reservation_conflict
```

Expected: FAIL because the current flow skips after the first reservation conflict.

- [x] **Step 3: Implement a bounded replan**

Pass a deterministic `attempt` suffix into `_plan_persisted_future_control` and its candidate seed. On `reservation_conflict` or `cross_site_prefix_conflict`, release/rollback the savepoint, reload same-issue and adjacent hashes, rebuild the controlled row once with `attempt=1`, and reserve/persist it. Keep `site_issue_already_reserved` as a safe skip: it means another execution already owns this site/issue.

```python
for attempt in range(2):
    # attempt=0 uses the initial row/control plan; attempt=1 regenerates/replans.
    # Reload conflicts before reselecting; do not reuse a stale candidate.
    ...
raise _PersistedFutureControlUnavailable("mode_id=<id>: controlled reservation conflict")
```

Do not report retry counts, hashes, labels, target decisions, or truth values through `module_report`.

- [x] **Step 4: Verify GREEN**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_generation_control_integration.py tests/unit/test_prediction_candidate_control.py
```

Expected: all pass.

### Task 3: Compare Adjacent Issues Across a Year Boundary

**Files:**
- Modify: `backend/src/domains/prediction/generation_control_repository.py:95-126`
- Test: `backend/src/tests/unit/test_prediction_generation_control_repository.py`

- [x] **Step 1: Write the failing cross-year lookup test**

```python
def test_adjacent_control_lookup_includes_previous_year_last_term(tmp_path):
    # Reserve (2025, 999) and query adjacency for (2026, 1).
    rows = load_adjacent_controls(..., year=2026, term=1, ...)
    assert {(row["year"], row["term"])} == {(2025, 999)}
```

- [x] **Step 2: Verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_generation_control_repository.py::test_adjacent_control_lookup_includes_previous_year_last_term
```

Expected: FAIL because the current query only compares `year = current year` and `term +/- 1`.

- [x] **Step 3: Implement issue-order adjacency lookup**

Fetch the closest predecessor and closest successor using separate ordered queries scoped to lottery, mode, and web:

```sql
SELECT year, term, signature_hash
FROM prediction_generation_controls
WHERE lottery_type_id = ? AND mode_id = ? AND web_id = ?
  AND (year < ? OR (year = ? AND term < ?))
ORDER BY year DESC, term DESC
LIMIT 1
```

Use the symmetric ascending predicate for the successor. Return the same `{year, term, signature_hash}` dictionaries and no raw signature. This treats the stored issue sequence as the authoritative boundary rather than guessing the last term number.

- [x] **Step 4: Verify GREEN**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_generation_control_repository.py tests/unit/test_prediction_generation_control_integration.py
```

Expected: all pass.

### Task 4: Expand Full-Future-Draw Taint Coverage

**Files:**
- Modify: `backend/src/tests/unit/test_prediction_future_truth_taint.py`
- Modify only if a failing test identifies an escaping boundary: `backend/src/prediction_generation/service.py`

- [x] **Step 1: Write report and serializer-boundary regression tests**

Add a fixture with `truth_csv = "01,02,03,04,05,06,49"`. Generate a supported future mode-470 row through `_process_single_module`, capture the module report, persisted input, and a public/legacy serializer entry point using a row with empty result fields.

```python
for value in (module_report, persisted_row, public_payload, legacy_payload):
    assert truth_csv not in repr(value)
assert persisted_row["res_code"] == ""
assert persisted_row["res_sx"] == ""
assert persisted_row["res_color"] == ""
assert "_generation_control" not in persisted_row
```

Mock only I/O boundaries; exercise real serializer functions where their test setup permits.

- [x] **Step 2: Verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_future_truth_taint.py
```

Expected: the new test must fail only if a complete-draw value or private control field escapes. If it already passes, retain it as a regression proof and do not modify production code.

- [x] **Step 3: Retain the passing regression test without changing a clean boundary**

If red identifies an escape, remove the sensitive value at the exact boundary while retaining all existing payload keys and order. Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_future_truth_taint.py tests/unit/test_api_contract_prediction_routes.py
```

Expected: all pass.

### Task 5: Update Operational Documentation and Verify the Increment

**Files:**
- Modify: `backend/docs/prediction-module-rules.md`
- Modify: `backend/CLAUDE.md`
- Modify: `docs/superpowers/plans/2026-07-18-prediction-generation-guarantees-continuation.md`

- [x] **Step 1: Document verified guarantees and deliberate blocks**

Add concise Chinese sections stating:

```markdown
- 控制账本预约与 created 预测行写入必须在同一事务/保存点中完成；写入失败、跳过或冲突后不得遗留控制记录。
- 发生跨站签名预约竞争时，生成器最多重新选择一次；仍无合法候选时安全跳过，不输出真值或签名。
- 相邻期按同彩种、同模块、同站点的实际期号序列比较，包含跨年边界。
- 尚无可验证候选规则的文本、图片和未知动态模块保持“未来受控生成跳过”，不宣称满足滚动正确率。
```

- [x] **Step 2: Run focused verification**

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_accuracy_plan.py tests/unit/test_prediction_generation_rules.py tests/unit/test_prediction_candidate_control.py tests/unit/test_prediction_generation_control_repository.py tests/unit/test_prediction_generation_control_integration.py tests/unit/test_prediction_generation_simulation_integration.py tests/unit/test_prediction_future_truth_taint.py tests/unit/test_prediction_rule_documentation.py tests/unit/test_api_contract_prediction_routes.py
git -C ../.. diff --check
```

Expected: no test failures and no whitespace errors.

- [x] **Step 3: Run final compatibility checks**

```powershell
cd backend/src
python -m compileall .
rg -n --glob '*.py' 'truth\.numbers|DrawTruth.*to_public' routes public legacy app_http
rg -n --glob '*.py' 'conn\.execute|\.execute\(|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b' predict/mechanisms.py predict/common.py
git -C ../.. diff -- backend/src/routes backend/src/domains/prediction/api_response.py backend/docs/API.md
```

Expected: compilation succeeds, no future-truth serialization is found, no direct SQL remains in the checked prediction algorithm files, and no API schema implementation file changes occur.

