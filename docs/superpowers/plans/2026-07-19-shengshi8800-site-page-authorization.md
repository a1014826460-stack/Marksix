# Shengshi8800 Site Page Authorization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Derive site 4 (`shengshi8800`) prediction-module authorization from every non-commented, reachable legacy vendor page dependency, then safely reconcile the development database without changing HTTP payloads.

**Architecture:** Extend the immutable `site_page_dependencies` manifest with non-commented prediction scripts from `frontend/public/vendor/shengshi8800/index.html`. Add a dedicated `shengshi8800` blueprint profile and versioned migration 3; reconciliation continues to update only `site_prediction_modules.status` and timestamps.

**Tech Stack:** Python 3, pytest, PostgreSQL versioned migrations, Next.js compatibility route, static HTML/JavaScript inspection.

---

## Compatibility Rules

- Keep every existing API path, success payload field/order, legacy wrapper, and disabled-module empty response unchanged.
- Do not delete prediction history or `created` rows. Reconciliation may only update authorization `status` and `updated_at`.
- Count only scripts loaded from non-commented Shengshi8800 `index.html`. Utility, draw-only, image-only, and commented scripts never authorize generation.
- `web=4` is a fixed legacy page parameter, not a backend default or arbitrary query authorization key.

## Confirmed Mapping

The required unique mode set, derived from live page script endpoints and the
Next compatibility route, is:

```text
2, 3, 8, 12, 20, 26, 28, 31, 34, 38, 42, 43, 45, 46, 48, 49, 50, 51, 52, 53, 54, 56, 57, 58, 59, 61, 62, 63, 65, 68, 108, 151, 197, 244, 246, 331
```

Key mappings include: `027ptw.js -> getPingte?num=2 -> 43`,
`023sqzt.js -> 197`, `tp5.js -> getPmxjcz -> 331`,
`019ma24.js -> getCode?num=24 -> 34`, `016teduan.js -> 65`, and
`011yqjt.js -> getJuzi?num=yqmtm -> 68`. Duplicate page sections resolve to
one required mode. The current `index.html` does not load modes such as 64,
66, 67, 69, 88, 116, 123, 132, 141, 143, 144, 145, 147, 149, 152, 155, 157,
158, 159, 251, 295, 333, 336, 470-478; they must not remain authorized only
because of historical database rows.

### Task 1: Lock the Vendor Source Inventory

**Files:**
- Modify: `backend/src/tests/unit/test_site_prediction_page_dependencies.py`
- Modify: `backend/src/domains/prediction/site_page_dependencies.py`

- [x] **Step 1: Write the failing site-4 manifest test**

```python
def test_shengshi8800_manifest_matches_live_vendor_scripts_only():
    dependencies = dependencies_for_site("shengshi8800")
    mode_ids = {mode_id for item in dependencies for mode_id in item.mode_ids}

    assert {2, 3, 8, 12, 20, 26, 28, 31, 34, 38, 42, 43, 45, 46, 48, 49, 50, 51, 52, 53, 54, 56, 57, 58, 59, 61, 62, 63, 65, 68, 108, 151, 197, 244, 246, 331} == mode_ids
    assert "static/js/018shu3x.js" in {item.source_path for item in dependencies}
    assert 64 not in mode_ids
```

- [x] **Step 2: Run RED**

Run: `cd backend/src; python -m pytest -q tests/unit/test_site_prediction_page_dependencies.py -k shengshi8800`

Expected: failure because the site-4 manifest is absent.

- [x] **Step 3: Add exact dependency entries**

Add a `shengshi8800` item for each live prediction script in the confirmed
mapping, using `page_path="/vendor/shengshi8800/index.html"`. Preserve
separate source records but let `required_mode_ids_for_site_key()` deduplicate
mode IDs. Exclude `kj.js`, `djck.js`, utilities, image-only scripts, and
commented `/cj/*` resources.

- [x] **Step 4: Run GREEN**

Run: `cd backend/src; python -m pytest -q tests/unit/test_site_prediction_page_dependencies.py -k shengshi8800`

Expected: PASS.

### Task 2: Use a Dedicated Blueprint and Explicit Migration

**Files:**
- Modify: `backend/src/domains/prediction/site_module_blueprints.py`
- Modify: `backend/src/database/schema/prediction.py`
- Modify: `backend/src/database/versioned_migrations.py`
- Modify: `backend/src/domains/prediction/site_module_audit.py`
- Modify: `backend/src/tests/unit/test_site_prediction_module_audit.py`
- Modify: `backend/src/tests/unit/test_versioned_migrations.py`

- [x] **Step 1: Write failing blueprint and stale-profile reconciliation tests**

```python
def test_shengshi8800_blueprint_equals_its_page_manifest():
    assert set(get_required_mode_ids_for_site({"web_id": 4})) == set(
        required_mode_ids_for_site_key("shengshi8800")
    )

def test_reconcile_site_four_disables_an_active_non_manifest_mode(tmp_path):
    # A site-4 row for mode 64 becomes status=0 while mode 331 remains status=1.
    assert statuses == {64: 0, 331: 1}
```

- [x] **Step 2: Run RED**

Run: `cd backend/src; python -m pytest -q tests/unit/test_site_prediction_module_audit.py -k shengshi8800`

Expected: failure because site 4 still resolves to the default blueprint.

- [x] **Step 3: Implement dedicated profile and migration 3**

Add the `shengshi8800` profile seed from the manifest. Migration 3 must upsert
that profile and change `managed_sites.web_id=4` from `default` to
`shengshi8800`. Add `web_id=4` to audit site-key resolution. No migration or
reconciliation operation may delete history.

- [x] **Step 4: Run GREEN**

Run: `cd backend/src; python -m pytest -q tests/unit/test_site_prediction_module_audit.py tests/unit/test_site_prediction_modules_db_source.py tests/unit/test_versioned_migrations.py`

Expected: PASS.

### Task 3: Document, Verify, and Synchronize Site 4

**Files:**
- Create: `frontend/public/vendor/shengshi8800/SHENGSHI8800_PREDICTION_MODULES.md`
- Modify: `backend/README_CN.md`
- Modify: `backend/docs/API.md`
- Modify: `backend/CLAUDE.md`

- [x] **Step 1: Document the manifest boundary**

Write the required mode set twice in the vendor document for parser/audit
validation. Document why utility/draw/commented resources do not authorize
prediction modules and that sync preserves history and API response shapes.

- [x] **Step 2: Run development migration and no-write audit**

```powershell
Push-Location backend/src
python -m database.versioned_migrations --db-path "$env:DATABASE_URL"
Pop-Location
python backend/scripts/reconcile_site_prediction_modules.py --db-path "$env:DATABASE_URL" --site-ids 4
```

- [x] **Step 3: Apply reconciliation after inspecting the audit**

```powershell
python backend/scripts/reconcile_site_prediction_modules.py --db-path "$env:DATABASE_URL" --site-ids 4 --apply
```

Expected: `missing_from_runtime` and `enabled_outside_authorized_sources` are
empty; only status/timestamps change.

- [x] **Step 4: Run final verification**

```powershell
cd backend/src
python -m pytest -q

cd ../..
pnpm --dir frontend exec tsc --noEmit
git diff --check
```

Expected: all checks pass without API serializer/payload changes.
