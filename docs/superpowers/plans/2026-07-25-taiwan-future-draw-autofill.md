# Taiwan Future Draw Autofill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an administrator create a requested number of new, future Taiwan lottery draw records (default 12) without changing any existing future record, while enforcing secure random seven-number draws and the ten-issue positional safeguards.

**Architecture:** Add a lottery-domain service operation that runs as one database transaction and is called by a guarded admin endpoint. The operation begins after the latest Taiwan issue, advances daily/term-by-term, preserves any already-existing future issue, and continues until it has inserted N new records. It chooses each candidate with `secrets.SystemRandom`, validates it against the ten immediately preceding persisted/generated records, and returns a compact creation report. The existing React page invokes this endpoint from a count input and button beside “新增开奖记录”, then reloads page one.

**Tech Stack:** Python 3, existing `db.ConnectionAdapter` (SQLite tests and PostgreSQL runtime), custom `app_http.Router`, Next.js/React 19, TypeScript, Sonner, pytest, Node contract tests.

---

## File Structure

- Modify: `backend/src/domains/lottery/service.py` — owns the atomic Taiwan-only future-draw generation and its invariant helpers.
- Modify: `backend/src/routes/admin_draw_routes.py` — registers and validates the authenticated `POST /api/admin/draws/auto-fill-future` endpoint.
- Modify: `backend/src/tests/unit/test_admin_crud_lottery_compat.py` — regression coverage for the service using isolated SQLite databases.
- Modify: `backend/src/tests/unit/test_api_contract_admin_routes.py` — route contract and bounded count validation coverage.
- Modify: `backend/features/draws/DrawsPage.tsx` — default-12 count input, guarded action button, feedback and reload behavior.
- Create: `backend/features/draws/draws-auto-fill-contract.mjs` — lightweight UI contract so the page cannot lose the endpoint/default/count controls.
- Modify: `backend/package.json` — exposes the UI contract as `test:draws-auto-fill-contract`.

## Contract and Rules

- Endpoint: `POST /api/admin/draws/auto-fill-future`, request JSON `{ "count": 12 }`; missing `count` defaults to `12`, allowed range is `1..60`.
- The endpoint is admin-guarded, Taiwan-only, and does not accept a client-provided lottery ID.
- Response: `{ "ok": true, "data": { "requested_count": 12, "created_count": 12, "preserved_existing_count": 2, "created": [{ "year": 2026, "term": 201, "numbers": "01,02,03,04,05,06,07", "draw_time": "..." }] } }`.
- “Future” is every Taiwan issue after the latest **opened** issue. Existing future rows are read-only: they are counted as preserved, never updated or deleted. The generator scans past them until it has inserted exactly `count` new rows.
- Each new row has `lottery_type_id=3`, `status=1`, `is_opened=0`, seven zero-padded comma-separated values in draw order, `next_term` set to the next issue, its calendar draw time at the configured Taiwan daily time, and `next_time` pointing at the following calendar draw time.
- The first candidate issue is the issue immediately after the latest opened Taiwan row. If no opened Taiwan record exists, return a clear `ValueError` instead of inventing a starting period.
- Issue rollover uses the existing runtime config key `prediction.max_terms_per_year` (default `365`), not a second hardcoded annual maximum.
- A candidate is valid only if: it has seven different values in `1..49`; its complete ordered seven-number sequence differs from each preceding ten record that has valid numbers; its positions 1, 2, 3, and 7 each differ from that same position of every preceding ten record. Position 7 is the special number.
- Candidate sampling uses `secrets.SystemRandom().sample(range(1, 50), 7)`. Retry a bounded `10_000` times; raise an error if the impossible/abnormal constraint cannot be satisfied. Never use a deterministic seed in production.
- PostgreSQL uses a transaction-scoped advisory lock for this Taiwan generator before reading the baseline. SQLite begins an immediate write transaction. This guarantees two admins cannot allocate the same future issue concurrently; the table’s unique key remains the final integrity barrier.

### Task 1: Specify and test the pure candidate safeguards

**Files:**
- Modify: `backend/src/tests/unit/test_admin_crud_lottery_compat.py`
- Modify: `backend/src/domains/lottery/service.py`

- [ ] **Step 1: Write failing tests for number parsing and the ten-row positional rule**

Add tests next to the lottery-service tests with explicitly ordered historic records. Test a valid candidate, an equal first number, an equal second number, an equal third number, an equal seventh/special number, a duplicate candidate tuple, and a candidate containing a repeated value. The tests call the new internal helpers directly:

```python
def test_taiwan_future_draw_candidate_enforces_recent_positional_constraints():
    from domains.lottery.service import _is_valid_taiwan_future_candidate

    recent = [
        [1, 2, 3, 4, 5, 6, 7],
        [8, 9, 10, 11, 12, 13, 14],
    ]

    assert _is_valid_taiwan_future_candidate([15, 16, 17, 18, 19, 20, 21], recent)
    assert not _is_valid_taiwan_future_candidate([1, 16, 17, 18, 19, 20, 21], recent)
    assert not _is_valid_taiwan_future_candidate([15, 2, 17, 18, 19, 20, 21], recent)
    assert not _is_valid_taiwan_future_candidate([15, 16, 3, 18, 19, 20, 21], recent)
    assert not _is_valid_taiwan_future_candidate([15, 16, 17, 18, 19, 20, 7], recent)
    assert not _is_valid_taiwan_future_candidate([1, 2, 3, 4, 5, 6, 7], recent)
    assert not _is_valid_taiwan_future_candidate([15, 15, 17, 18, 19, 20, 21], recent)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
D:\python\python.exe -m pytest backend/src/tests/unit/test_admin_crud_lottery_compat.py -k future_draw_candidate -q
```

Expected: FAIL because `_is_valid_taiwan_future_candidate` does not exist.

- [ ] **Step 3: Implement the small pure helpers in `service.py`**

Add `_parse_taiwan_draw_numbers(raw: str) -> list[int] | None` and `_is_valid_taiwan_future_candidate(candidate: list[int], recent: list[list[int]]) -> bool` above `save_draw`. The acceptance predicate must be structurally equivalent to:

```python
def _is_valid_taiwan_future_candidate(candidate, recent):
    if len(candidate) != 7 or len(set(candidate)) != 7:
        return False
    if any(number < 1 or number > 49 for number in candidate):
        return False
    for previous in recent[-10:]:
        if len(previous) != 7:
            continue
        if candidate == previous:
            return False
        if any(candidate[index] == previous[index] for index in (0, 1, 2, 6)):
            return False
    return True
```

Use the existing comma-separated storage format and zero-pad only when formatting a newly selected candidate.

- [ ] **Step 4: Run the focused test to verify it passes**

Run the command from Step 2. Expected: PASS.

- [ ] **Step 5: Commit the isolated safeguard work**

```powershell
git add backend/src/domains/lottery/service.py backend/src/tests/unit/test_admin_crud_lottery_compat.py
git commit -m "test: cover Taiwan future draw safeguards"
```

### Task 2: Implement atomic future-record generation and preservation

**Files:**
- Modify: `backend/src/domains/lottery/service.py`
- Modify: `backend/src/tests/unit/test_admin_crud_lottery_compat.py`

- [ ] **Step 1: Write failing service tests for the full generation report**

Create a fixture with one opened Taiwan draw and an existing future Taiwan draw. Call `autofill_taiwan_future_draws(db_path, count=12, rng=Random(7))` (the optional RNG is test-only dependency injection; production passes `None`). Assert:

```python
assert result["requested_count"] == 12
assert result["created_count"] == 12
assert result["preserved_existing_count"] == 1
assert len(result["created"]) == 12
assert existing_numbers_after == existing_numbers_before
assert all(row["is_opened"] is False for row in result["created"])
assert all(len(row["numbers"].split(",")) == 7 for row in result["created"])
```

Query all Taiwan rows in issue order and assert every newly generated row has a unique 1–49 sequence, while every row’s positions 0, 1, 2, and 6 differ from each of its up-to-ten prior rows. Add a second test where an existing future record occupies the first candidate term; assert that term is not in `created`, its original numbers survive, and the service still creates the requested number of *new* rows. Add a third test that `count=0` and `count=61` raise `ValueError` and that no opened baseline raises the documented error.

- [ ] **Step 2: Run the full-generation tests to verify they fail**

Run:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
D:\python\python.exe -m pytest backend/src/tests/unit/test_admin_crud_lottery_compat.py -k autofill_taiwan_future -q
```

Expected: FAIL because `autofill_taiwan_future_draws` is absent.

- [ ] **Step 3: Implement `autofill_taiwan_future_draws` in the lottery domain**

Implement:

```python
def autofill_taiwan_future_draws(
    db_path: str | Path,
    *,
    count: int = 12,
    rng: random.Random | None = None,
) -> dict[str, Any]:
```

Implementation requirements:

1. Reject counts outside `1..60`; call `ensure_admin_tables`.
2. Open exactly one `connect(db_path)` context. On PostgreSQL execute `SELECT pg_advisory_xact_lock(?)` with a stable Taiwan-autofill integer key; on SQLite execute `BEGIN IMMEDIATE` before reading. Do not catch unique-constraint failures and silently report success.
3. Read `prediction.max_terms_per_year` through `runtime_config.get_config_from_conn`; read Taiwan’s configured daily time from `lottery_types.draw_time`, falling back to `draw.taiwan_default_draw_time` then `22:30` only when absent/invalid.
4. Read the latest opened Taiwan row in `(year, term, id)` order. Start from the immediate successor using one local `_next_issue(year, term, max_terms)` helper and the day after its Beijing `draw_time`.
5. Read all future Taiwan rows at/after the initial successor once into a `(year, term) -> row` map. On every cursor issue, retain an existing row exactly as-is, increment `preserved_existing_count`, append valid existing numbers to the rolling recent list, advance one issue/day, and continue. Never call `save_draw` for an existing row.
6. For an empty cursor issue, sample until `_is_valid_taiwan_future_candidate(candidate, recent)` passes. Use `rng or secrets.SystemRandom()`, `range(1, 50)`, a 10,000-attempt cap, and `','.join(f'{number:02d}' for number in candidate)`.
7. Insert `status=1`, `is_opened=0`, `next_term` from the successor, `draw_time` at the resolved daily time, and `next_time` as the following day’s Unix milliseconds (use existing `draw_time_to_unix_ms`). Append the inserted row to both `created` and the rolling last-ten source.
8. Continue until `created_count == count`; then call `_sync_lottery_type_next_time(conn, 3, now)` once and return only public result fields.

Do not alter `save_draw` behavior and do not mark generated future records as opened.

- [ ] **Step 4: Run the service tests to verify they pass**

Run the command from Step 2, then:

```powershell
D:\python\python.exe -m pytest backend/src/tests/unit/test_admin_crud_lottery_compat.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the domain operation**

```powershell
git add backend/src/domains/lottery/service.py backend/src/tests/unit/test_admin_crud_lottery_compat.py
git commit -m "feat: generate future Taiwan draw records"
```

### Task 3: Expose a narrow admin endpoint

**Files:**
- Modify: `backend/src/routes/admin_draw_routes.py`
- Modify: `backend/src/tests/unit/test_api_contract_admin_routes.py`

- [ ] **Step 1: Write failing route-contract tests**

Add one test that provides `{ "count": 8 }`, patches `routes.admin_draw_routes.autofill_taiwan_future_draws`, and asserts the route calls it as `autofill_taiwan_future_draws(ctx.db_path, count=8)` and sends `{ "ok": True, "data": payload }`. Add one test for `{}` asserting the default `count=12`, and parameterize `0`, `61`, and a non-integer value to assert a `ValueError` before service invocation.

- [ ] **Step 2: Run the route tests to verify they fail**

Run:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
D:\python\python.exe -m pytest backend/src/tests/unit/test_api_contract_admin_routes.py -k autofill_future -q
```

Expected: FAIL because the route and imported service callable do not exist.

- [ ] **Step 3: Register and implement the handler**

In `register`, add the exact route before `add_prefix`:

```python
router.add("POST", "/api/admin/draws/auto-fill-future", autofill_future_draws, guard=require_admin)
```

Import `autofill_taiwan_future_draws`. Implement the handler with a local integer parser that defaults missing `count` to `12`, rejects booleans/non-integers, and raises `ValueError("自动填写期数必须在 1 到 60 之间")` outside the range:

```python
def autofill_future_draws(ctx: RequestContext) -> None:
    payload = ctx.read_json()
    count = _parse_autofill_count(payload.get("count", 12))
    result = autofill_taiwan_future_draws(ctx.db_path, count=count)
    ctx.send_json({"ok": True, "data": result}, HTTPStatus.CREATED)
```

The handler must not expose a lottery type parameter.

- [ ] **Step 4: Run the route tests to verify they pass**

Run the command from Step 2. Expected: PASS.

- [ ] **Step 5: Commit the API boundary**

```powershell
git add backend/src/routes/admin_draw_routes.py backend/src/tests/unit/test_api_contract_admin_routes.py
git commit -m "feat: add Taiwan future draw autofill API"
```

### Task 4: Add the draw-management control and UI contract

**Files:**
- Modify: `backend/features/draws/DrawsPage.tsx`
- Create: `backend/features/draws/draws-auto-fill-contract.mjs`
- Modify: `backend/package.json`

- [ ] **Step 1: Write a failing page contract test**

Create `backend/features/draws/draws-auto-fill-contract.mjs`:

```js
import fs from "node:fs"

const source = fs.readFileSync("features/draws/DrawsPage.tsx", "utf8")
for (const token of [
  "自动填写开奖记录",
  'useState("12")',
  '"/admin/draws/auto-fill-future"',
  "setAutoFillCount",
  "setAutoFilling",
  "created_count",
  "preserved_existing_count",
]) {
  if (!source.includes(token)) throw new Error(`draw autofill UI missing ${token}`)
}
```

Add `"test:draws-auto-fill-contract": "node features/draws/draws-auto-fill-contract.mjs"` to `backend/package.json`.

- [ ] **Step 2: Run the UI contract to verify it fails**

Run:

```powershell
pnpm --dir backend test:draws-auto-fill-contract
```

Expected: FAIL because the auto-fill controls are absent.

- [ ] **Step 3: Implement the page behavior without changing existing table/form behavior**

In `DrawsPage.tsx`:

1. Import `WandSparkles` from `lucide-react`.
2. Add state exactly as follows:

```tsx
const [autoFillCount, setAutoFillCount] = useState("12")
const [autoFilling, setAutoFilling] = useState(false)
```

3. Add `autoFillFutureDraws`. Parse `autoFillCount` as an integer, reject values outside `1..60` with `toast.error`, ask confirmation including the requested N and “已有未来期号将跳过保留”, POST `jsonBody({ count })` to `/admin/draws/auto-fill-future`, disable duplicate clicks using `autoFilling`, reload with `await load(1)`, and show:

```tsx
toast.success(`已新增 ${result.data.created_count} 期；保留已有未来期 ${result.data.preserved_existing_count} 期`)
```

4. In the existing top action row, place a numeric `Input` with `min={1}`, `max={60}`, `aria-label="自动填写未来期数"`, and the auto-fill `Button` immediately before the existing “新增开奖记录” button. The input’s initial value must remain `12`; both controls disable while the request is running. The button renders `WandSparkles` and uses the exact label “自动填写开奖记录”.

Do not alter edit/delete locking, manually entered draw validation, existing column widths, or paging.

- [ ] **Step 4: Run the UI contract and TypeScript validation**

Run:

```powershell
pnpm --dir backend test:draws-auto-fill-contract
pnpm exec tsc --noEmit -p backend/tsconfig.json
```

Expected: both commands exit 0.

- [ ] **Step 5: Commit the management UI**

```powershell
git add backend/features/draws/DrawsPage.tsx backend/features/draws/draws-auto-fill-contract.mjs backend/package.json
git commit -m "feat: add Taiwan draw autofill control"
```

### Task 5: Full regression and manual verification

**Files:**
- Verify only; do not modify production code unless a failing test identifies a defect.

- [ ] **Step 1: Run focused Python and browser-independent contracts**

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
D:\python\python.exe -m pytest backend/src/tests/unit/test_admin_crud_lottery_compat.py backend/src/tests/unit/test_api_contract_admin_routes.py -q
pnpm --dir backend test:draws-auto-fill-contract
pnpm --dir backend test:admin-shell-contract
pnpm exec tsc --noEmit -p backend/tsconfig.json
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 2: Perform the admin acceptance sequence against the development backend**

1. Open the draw-management page and verify the numeric field defaults to 12 and is immediately beside “新增开奖记录”.
2. Create or identify at least one opened Taiwan row and one manually entered future Taiwan row; record the future row’s ID and numbers.
3. Click “自动填写开奖记录”, confirm 12, then refresh the table.
4. Verify 12 new `is_opened=否` rows exist; the previously future row has exactly its original ID/numbers; no existing future row was edited or deleted.
5. Export/order all affected Taiwan rows by issue and verify each generated row has seven distinct 01–49 values; compare each with its preceding ten rows at positions 1, 2, 3, and 7.
6. Click again with N=1 and verify exactly one additional new row is created, demonstrating the action fills new future capacity rather than overwriting records.

- [ ] **Step 3: Commit only verified files**

```powershell
git add backend/src/domains/lottery/service.py backend/src/routes/admin_draw_routes.py backend/src/tests/unit/test_admin_crud_lottery_compat.py backend/src/tests/unit/test_api_contract_admin_routes.py backend/features/draws/DrawsPage.tsx backend/features/draws/draws-auto-fill-contract.mjs backend/package.json docs/superpowers/plans/2026-07-25-taiwan-future-draw-autofill.md
git commit -m "feat: automate future Taiwan draw records"
```

Do not stage or revert unrelated pre-existing workspace changes.
