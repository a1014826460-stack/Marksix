# Site Prediction Page Authorization and Generation Assurance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Derive sites 5-8 prediction-module authorization from all accessible frontend prediction pages, while documenting exactly which page-backed modes have controlled future-generation guarantees.

**Architecture:** Add an internal immutable dependency manifest that records legacy vendor page endpoint/parameter mappings, React provider source modes, and twcf888 live article mappings. The existing site blueprint and reconciliation service consume its required mode sets; routes continue to consume only `site_prediction_modules(status=1)`, so API payloads do not change. A small assurance resolver combines the manifest with `generation_rules` to classify each mode as controlled, history-only, or blocked without exposing metadata through HTTP.

**Tech Stack:** Python 3, pytest, existing prediction domain services, PostgreSQL/SQLite test adapters, frontend static TypeScript/HTML/JS source inspection.

---

## Compatibility Rules

- Do not modify route success payloads, JSON field order, HTTP status behavior, legacy wrappers, or disabled-module empty `data`/`rows`/`history` shapes.
- Do not delete history. Reconciliation may only update `site_prediction_modules.status` and `updated_at`.
- Do not read or serialize future draw truth in the manifest, audit output, generation reports, or public APIs.
- A mode may be `controlled_future` only when `generation_rules.get_generation_rule()` returns a verified rule. Text/image/unknown modes remain `history_only`; unsupported page mappings remain `blocked`.
- All accessible non-commented vendor scripts and React/article providers count, even if a page is rarely used. Commented HTML script tags and orphan static files do not.

## File Map

| File | Responsibility |
|---|---|
| Create `backend/src/domains/prediction/site_page_dependencies.py` | Immutable page/module dependency manifest and assurance resolver. |
| Modify `backend/src/domains/prediction/site_module_blueprints.py` | Obtain site 5-8 fallback required mode IDs from the manifest; remove duplicate hand-maintained constants. |
| Modify `backend/src/domains/prediction/site_module_audit.py` | Compare manifest, blueprint, and active DB mode sets; reconcile to manifest-backed modes. |
| Modify `backend/scripts/reconcile_site_prediction_modules.py` | Include manifest and assurance results in its JSON audit; retain `--apply` semantics. |
| Modify `backend/docs/prediction-module-rules.md` | Generate/document assurance state and exact meaning. |
| Modify `backend/README_CN.md`, `backend/docs/API.md`, `backend/CLAUDE.md` | Document source-of-truth, audit command, and API compatibility constraints. |
| Modify `frontend/public/vendor/twsaimahui/TWSAIMAHUI_PREDICTION_MODULES.md` | Replace broad/dead mappings with the auditable reachable-page list and blocked items. |
| Test `backend/src/tests/unit/test_site_prediction_page_dependencies.py` | Source/live script parsing, exact mapping, assurance tests. |
| Modify `backend/src/tests/unit/test_site_prediction_module_audit.py` | Manifest/blueprint/database reconciliation regression cases. |
| Modify `backend/src/tests/unit/test_prediction_rule_documentation.py` | Rule document assurance column regression coverage. |

### Task 1: Build the Internal Page Dependency Manifest

**Files:**
- Create: `backend/src/domains/prediction/site_page_dependencies.py`
- Test: `backend/src/tests/unit/test_site_prediction_page_dependencies.py`

- [x] **Step 1: Write a failing test for live versus commented twsaimahui script dependencies**

```python
def test_twsaimahui_manifest_covers_live_scripts_but_not_commented_script():
    from domains.prediction.site_page_dependencies import dependencies_for_site

    dependencies = dependencies_for_site("twsaimahui")
    source_paths = {item.source_path for item in dependencies}
    mode_ids = {mode_id for item in dependencies for mode_id in item.mode_ids}

    assert "static/js/067sanzipw.js" in source_paths
    assert 470 in mode_ids
    assert "static/js/020nn4x.js" not in source_paths
    assert 24 not in mode_ids
```

- [x] **Step 2: Run the test to verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_site_prediction_page_dependencies.py::test_twsaimahui_manifest_covers_live_scripts_but_not_commented_script
```

Expected: FAIL because `site_page_dependencies` does not exist.

- [x] **Step 3: Implement immutable manifest types and twsaimahui dependencies**

```python
@dataclass(frozen=True)
class SitePageDependency:
    site_key: str
    page_path: str
    source_path: str
    mode_ids: tuple[int, ...]
    kind: Literal["page_module", "composite_source"]
    endpoint: str = ""
    params: tuple[tuple[str, str], ...] = ()
    blocked_reason: str = ""

def dependencies_for_site(site_key: str) -> tuple[SitePageDependency, ...]:
    return tuple(item for item in _DEPENDENCIES if item.site_key == site_key)
```

Declare each live `<script src="static/js/...">` in
`frontend/public/vendor/twsaimahui/index.html` with its exact compatibility
route mapping from `frontend/app/api/kaijiang/[[...path]]/route.ts`. Do not
include commented `020nn4x.js`, `032ma20.js`, `069lxbm.js`, or
`029yizixuanji.js`. Add six-not-in as a dependency with `mode_ids=()` and a
`blocked_reason`; it must never enter the required mode set.

- [x] **Step 4: Run the focused test to verify GREEN**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_site_prediction_page_dependencies.py::test_twsaimahui_manifest_covers_live_scripts_but_not_commented_script
```

Expected: PASS.

- [ ] **Step 5: Commit the manifest foundation**

```powershell
git add backend/src/domains/prediction/site_page_dependencies.py backend/src/tests/unit/test_site_prediction_page_dependencies.py
git commit -m "feat: add site prediction page dependency manifest"
```

### Task 2: Cover React and Article Dependencies

**Files:**
- Modify: `backend/src/domains/prediction/site_page_dependencies.py`
- Test: `backend/src/tests/unit/test_site_prediction_page_dependencies.py`

- [x] **Step 1: Write failing tests for twjinniu and twcf888 dependencies**

```python
def test_twjinniu_manifest_matches_its_homepage_provider_sources():
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    assert {56, 49, 151, 117, 123, 474, 476, 484} <= set(
        required_mode_ids_for_site_key("twjinniu")
    )


def test_twcf888_manifest_includes_live_articles_but_not_snapshot_or_blocked_articles():
    from domains.prediction.site_page_dependencies import dependencies_for_site, required_mode_ids_for_site_key

    dependencies = dependencies_for_site("twcf888")
    assert 470 in required_mode_ids_for_site_key("twcf888")
    assert any(item.blocked_reason and "广东5兄弟" in item.blocked_reason for item in dependencies)
```

- [x] **Step 2: Run tests to verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_site_prediction_page_dependencies.py -k "twjinniu or twcf888"
```

Expected: FAIL because those sites are absent from the manifest.

- [x] **Step 3: Add exact provider and article mappings**

Add `twjinniu` dependencies from every `loadLegacyModeRows(<id>, ...)` call
in `frontend/lib/twjinniu-homepage.ts`. Add `twcaibawang` composite source IDs
from `vendor.homepage_modules.get_vendor_module_source_mode_ids()` as
`kind="composite_source"`. Add `twcf888` live-backed article IDs from
`frontend/lib/twcf888-articles.ts` and its documented composite pairs.

Use `blocked_reason` for twcf888 snapshot-only gallery and Guangdong-five-
brothers entries; do not give either an enabled mode ID.

- [x] **Step 4: Run focused tests to verify GREEN**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_site_prediction_page_dependencies.py
```

Expected: PASS.

- [ ] **Step 5: Commit the cross-site inventory**

```powershell
git add backend/src/domains/prediction/site_page_dependencies.py backend/src/tests/unit/test_site_prediction_page_dependencies.py
git commit -m "feat: inventory accessible site prediction dependencies"
```

### Task 3: Derive Blueprints and Reconciliation from the Manifest

**Files:**
- Modify: `backend/src/domains/prediction/site_module_blueprints.py`
- Modify: `backend/src/domains/prediction/site_module_audit.py`
- Modify: `backend/scripts/reconcile_site_prediction_modules.py`
- Modify: `backend/src/tests/unit/test_site_prediction_module_audit.py`

- [x] **Step 1: Write a failing manifest/blueprint equivalence test**

```python
@pytest.mark.parametrize("site_key", ("twcaibawang", "twsaimahui", "twjinniu", "twcf888"))
def test_site_blueprint_equals_manifest_required_modes(site_key):
    from domains.prediction.site_module_blueprints import get_required_mode_ids_for_site
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    site = {"web_id": {"twcaibawang": 5, "twsaimahui": 6, "twjinniu": 7, "twcf888": 8}[site_key]}
    assert set(get_required_mode_ids_for_site(site)) == set(required_mode_ids_for_site_key(site_key))
```

- [x] **Step 2: Run the test to verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_site_prediction_module_audit.py -k blueprint_equals_manifest
```

Expected: FAIL because site blueprint constants are independently maintained.

- [x] **Step 3: Make the manifest the fallback blueprint source**

Replace dedicated fallback tuples in `site_module_blueprints.py` with calls to
`required_mode_ids_for_site_key()`. Preserve database stored blueprint profiles
as the first lookup, but update their seed/migration values from the manifest
so runtime and fallback remain equal. In `site_module_audit.py`, return
`manifest_mode_ids` and `blocked_dependency_sources` alongside the existing
audit keys. `reconcile_site_prediction_modules_to_blueprint()` must use the
manifest-backed required set and must continue to only set status/timestamps.

- [x] **Step 4: Add a failing reconciliation test for a non-manifest row**

```python
def test_reconcile_disables_active_mode_absent_from_manifest(tmp_path):
    # Create site 6 plus one active row for mode 475, which its accessible
    # vendor page does not load, and one required row for mode 470.
    # After reconciliation, 475 is disabled and 470 remains enabled.
    assert statuses == {470: 1, 475: 0}
```

- [x] **Step 5: Run the new reconciliation test to verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_site_prediction_module_audit.py::test_reconcile_disables_active_mode_absent_from_manifest
```

Expected: FAIL before reconciliation switches to the manifest-backed set.

- [x] **Step 6: Implement minimal reconciliation wiring and verify GREEN**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_site_prediction_module_audit.py tests/unit/test_site_prediction_module_authorization.py tests/unit/test_site_prediction_modules_db_source.py
```

Expected: PASS. Existing disabled-module empty response contracts remain
unchanged.

- [ ] **Step 7: Extend command output and commit**

Include `manifest_mode_ids`, `active_database_mode_ids`, and
`blocked_dependency_sources` in the command's JSON audit, without changing
`--apply` to delete any row.

```powershell
git add backend/src/domains/prediction/site_module_blueprints.py backend/src/domains/prediction/site_module_audit.py backend/scripts/reconcile_site_prediction_modules.py backend/src/tests/unit/test_site_prediction_module_audit.py
git commit -m "feat: derive site module authorization from page dependencies"
```

### Task 4: Make Future-Generation Assurance Explicit

**Files:**
- Modify: `backend/src/domains/prediction/site_page_dependencies.py`
- Modify: `backend/docs/prediction-module-rules.md` generation source/renderer
- Modify: `backend/src/tests/unit/test_prediction_rule_documentation.py`
- Modify: `backend/src/tests/unit/test_site_prediction_page_dependencies.py`

- [x] **Step 1: Write failing assurance-state tests**

```python
def test_manifest_only_marks_verified_generation_rules_as_controlled_future():
    from domains.prediction.site_page_dependencies import generation_assurance_for_mode

    assert generation_assurance_for_mode(470) == "controlled_future"
    assert generation_assurance_for_mode(50) == "history_only"
    assert generation_assurance_for_mode(476) == "history_only"
    assert generation_assurance_for_mode(None, blocked_reason="no exact source") == "blocked"
```

- [x] **Step 2: Run the assurance test to verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_site_prediction_page_dependencies.py -k assurance
```

Expected: FAIL because no assurance resolver exists.

- [x] **Step 3: Implement the resolver without changing generation payloads**

```python
def generation_assurance_for_mode(mode_id: int | None, *, blocked_reason: str = "") -> str:
    if blocked_reason or mode_id is None:
        return "blocked"
    config = _prediction_config_for_mode(mode_id)
    return "controlled_future" if config and get_generation_rule(config) else "history_only"
```

Use the existing rule document renderer to add an `assurance` column. Keep
existing `future control` text, but require `history_only` when no rule exists.
Do not add this status to any HTTP response or stored prediction business row.

- [x] **Step 4: Run assurance/documentation tests to verify GREEN**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_site_prediction_page_dependencies.py tests/unit/test_prediction_rule_documentation.py tests/unit/test_prediction_accuracy_plan.py tests/unit/test_prediction_candidate_control.py tests/unit/test_prediction_generation_control_repository.py tests/unit/test_prediction_generation_control_integration.py
```

Expected: PASS.

- [ ] **Step 5: Commit assurance documentation support**

```powershell
git add backend/src/domains/prediction/site_page_dependencies.py backend/docs/prediction-module-rules.md backend/src/tests/unit/test_site_prediction_page_dependencies.py backend/src/tests/unit/test_prediction_rule_documentation.py
git commit -m "docs: classify prediction generation assurances"
```

### Task 5: Synchronize Documentation, Reconcile Database, and Verify Compatibility

**Files:**
- Modify: `frontend/public/vendor/twsaimahui/TWSAIMAHUI_PREDICTION_MODULES.md`
- Modify: `backend/README_CN.md`
- Modify: `backend/docs/API.md`
- Modify: `backend/CLAUDE.md`
- Modify: `docs/superpowers/plans/2026-07-19-site-prediction-page-authorization-and-generation-assurance.md`

- [x] **Step 1: Update operational documentation**

Document the three assurance states, that all accessible pages count, and the
two-step operation below. State that `--apply` only changes authorization
status and preserves history.

```powershell
python backend/scripts/reconcile_site_prediction_modules.py --db-path "$env:DATABASE_URL" --site-ids 5,6,7,8
python backend/scripts/reconcile_site_prediction_modules.py --db-path "$env:DATABASE_URL" --site-ids 5,6,7,8 --apply
```

- [ ] **Step 2: Run a no-write production audit and inspect the JSON sets**

Run:

```powershell
python backend/scripts/reconcile_site_prediction_modules.py --db-path "$env:DATABASE_URL" --site-ids 5,6,7,8
```

Expected: each site's `enabled_outside_authorized_sources` is empty after
reconciliation, and every blocked dependency is absent from active modes.

- [ ] **Step 3: Apply authorization reconciliation once the audit is clean**

Run:

```powershell
python backend/scripts/reconcile_site_prediction_modules.py --db-path "$env:DATABASE_URL" --site-ids 5,6,7,8 --apply
```

Expected: only `status`/timestamp changes; no prediction history deletes.

- [ ] **Step 4: Run final regression and contract verification**

Run:

```powershell
cd backend/src
python -m pytest -q

cd ../..
pnpm --dir frontend exec tsc --noEmit
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/check-no-secrets.ps1
docker compose config --quiet
git diff --check
```

Expected: Python tests pass, TypeScript compiles, secret/Compose/diff checks
pass, and no route response implementation requires a payload change.

- [ ] **Step 5: Commit documentation and audit record**

```powershell
git add frontend/public/vendor/twsaimahui/TWSAIMAHUI_PREDICTION_MODULES.md backend/README_CN.md backend/docs/API.md backend/CLAUDE.md docs/superpowers/plans/2026-07-19-site-prediction-page-authorization-and-generation-assurance.md
git commit -m "docs: record site prediction authorization audit"
```


## Execution Record (2026-07-19)

- [x] Implemented the immutable reachable-page manifest for sites 5-8 and
  added the Twjinniu article sources that are reachable outside its homepage.
- [x] Confirmed the Twcf888 vendor `MODULE_SECTION_META` is uncalled legacy
  metadata; it is documented but does not authorize stale mode IDs.
- [x] Fixed the `getCode?num=16` compatibility mapping to `mode_id=9` without
  changing the response wrapper or fields.
- [x] Added migration 2, `sync_site_prediction_page_authorization`, which
  updates existing PostgreSQL blueprint profiles only through the versioned
  migration ledger.
- [x] Added internal-only generation assurance documentation. It is never
  serialized into public, legacy, vendor, or admin success payloads.
- [x] Focused regression completed: `75 passed`.
- [ ] Production audit/apply remains an operator step after running migration
  2 against the target PostgreSQL database; it is intentionally not executed
  from this workspace because the database target is not printed or persisted.
