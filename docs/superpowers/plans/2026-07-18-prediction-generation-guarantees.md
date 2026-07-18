# Prediction Generation Guarantees Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guarantee rolling future-period accuracy, rule-correct hit verification, cross-site prefix uniqueness, and same-site adjacent-period uniqueness without changing HTTP API payloads.

**Architecture:** A pure rule manifest converts `DrawTruth` into each module's actual outcome and defines canonical candidate signatures. A repository persists only control decisions and candidate-signature hashes; the generation service orchestrates those internal APIs before it writes existing created rows. Modules without a verified rule remain blocked from future controlled generation.

**Tech Stack:** Python 3, pytest, existing SQLite/PostgreSQL `ConnectionAdapter`, PostgreSQL advisory transaction locks, `PredictionConfig`, and the created-schema generator.

---

## Compatibility Rules

- Do not change HTTP paths, request fields, response fields, response order, status codes, or legacy wrappers.
- `/api/predict/{mechanism}` must not load `DrawTruth` or a future draw.
- Full future draw CSV, `res_code`, `res_sx`, `res_color`, `DrawTruth`, target decisions, verified decisions, and control signatures must not enter an API response, task report, log, exception, image text, or created prediction result field.
- A candidate may include one future-matching number, zodiac, tail, or category when it is a legal prediction value.
- The control table is internal. No route, legacy loader, public history loader, or response builder may read it.

## File Map

| File | Responsibility |
|---|---|
| `backend/src/domains/prediction/accuracy_plan.py` | Pure rolling-window target calculation and validation. |
| `backend/src/domains/prediction/generation_rules.py` | Per-module truth outcome, hit verification, and candidate signatures. |
| `backend/src/domains/prediction/generation_control_repository.py` | Internal control-table SQL and PostgreSQL advisory locking. |
| `backend/src/domains/prediction/candidate_control.py` | Deterministic candidate reselection against accuracy and diversity constraints. |
| `backend/src/database/schema/prediction.py` | `prediction_generation_controls` bootstrap schema. |
| `backend/src/prediction_generation/service.py` | Future-generation orchestration only; existing row/API shape remains unchanged. |
| `backend/src/domains/prediction/rule_documentation.py` | Stable Markdown rendering of registered rules. |
| `backend/docs/prediction-module-rules.md` | Generated rule review document. |

## Task 1: Build the Pure Rolling-Window Planner

**Files:**
- Create: `backend/src/domains/prediction/accuracy_plan.py`
- Test: `backend/src/tests/unit/test_prediction_accuracy_plan.py`

- [ ] **Step 1: Write the failing planner tests**

```python
from domains.prediction.accuracy_plan import AccuracyPolicy, choose_target_hit, validate_rolling_hit_rate


def test_sixty_percent_plan_has_six_hits_in_its_first_ten_terms():
    policy = AccuracyPolicy(window_size=10, minimum_hit_rate=0.6)
    outcomes: list[bool] = []
    for term in range(10):
        outcomes.append(choose_target_hit(outcomes, policy=policy, seed=f"term:{term}"))

    assert sum(outcomes) >= 6
    assert validate_rolling_hit_rate(outcomes, policy=policy) == []


def test_planner_forces_hit_after_four_misses_inside_the_current_window():
    policy = AccuracyPolicy(window_size=10, minimum_hit_rate=0.6)

    assert choose_target_hit([False, False, True, False, True, False], policy=policy, seed="must-hit") is True


def test_validator_returns_only_non_sensitive_window_counts():
    policy = AccuracyPolicy(window_size=10, minimum_hit_rate=0.6)

    assert validate_rolling_hit_rate([False] * 10, policy=policy) == [(0, 10, 0, 6)]
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_accuracy_plan.py
```

Expected: collection fails because `domains.prediction.accuracy_plan` is absent.

- [ ] **Step 3: Implement the minimal planner**

Create an immutable `AccuracyPolicy` with normalized `window_size`, `minimum_hit_rate`, `minimum_hits = ceil(window_size * minimum_hit_rate)`, and `maximum_misses`. `choose_target_hit(previous, policy, seed)` must inspect only the preceding `window_size - 1` verified booleans, force a hit when another miss would exceed `maximum_misses`, otherwise choose deterministically with SHA-256-seeded `random.Random`. `validate_rolling_hit_rate` must return `(start, end, actual_hits, required_hits)` for every failed complete window.

- [ ] **Step 4: Verify GREEN**

Run the command from Step 2. Expected: all planner tests pass.

## Task 2: Define Verified Per-Module Rules

**Files:**
- Create: `backend/src/domains/prediction/generation_rules.py`
- Test: `backend/src/tests/unit/test_prediction_generation_rules.py`

- [ ] **Step 1: Write the failing mode-470 and head-rule tests**

```python
from domains.prediction.generation_rules import get_generation_rule
from domains.prediction.models import DrawTruth
from predict.mechanisms import PREDICTION_CONFIGS


def _truth() -> DrawTruth:
    return DrawTruth(("01", "02", "03", "04", "05", "06", "27"), "27", "虎", "绿波")


def test_mode_470_hits_when_any_of_its_three_zodiacs_matches_special_zodiac():
    config = PREDICTION_CONFIGS["pt3xiao"]
    rule = get_generation_rule(config)

    assert rule.supported is True
    assert rule.cross_site_prefix_width == 1
    assert rule.verify_hit(config, ("鼠", "虎", "羊"), _truth(), conn=None) is True
    assert rule.verify_hit(config, ("鼠", "猪", "羊"), _truth(), conn=None) is False
    assert rule.signature(("鼠", "猪", "羊")) == ("鼠", "猪", "羊")
    assert rule.prefix_signature(("鼠", "猪", "羊")) == ("鼠",)


def test_head_rule_uses_special_head_instead_of_generic_zodiac_or_number_outcome():
    config = PREDICTION_CONFIGS["3tou"]
    rule = get_generation_rule(config)

    assert rule.verify_hit(config, ("2头", "3头", "4头"), _truth(), conn=None) is True
    assert rule.verify_hit(config, ("0头", "1头", "3头"), _truth(), conn=None) is False
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_generation_rules.py
```

Expected: import failure for `generation_rules`.

- [ ] **Step 3: Implement explicit rule adapters**

Create frozen `PredictionGenerationRule` with `rule_id`, `rule_revision`, `supported`, `block_reason`, `cross_site_prefix_width`, `truth_outcome`, `verify_hit`, `signature`, and `prefix_signature`. Implement explicit adapters for zodiac, number, head, tail, size, parity, wave, category, and known mixed modules. `verify_hit` must call the actual config `hit_checker(outcome, labels)`, not generic `PredictionCategory` matching. Return a blocked rule with `block_reason="missing_verified_rule"` for unknown dynamic configs.

- [ ] **Step 4: Add and verify exclusion semantics**

Add this test before the exclusion adapter implementation:

```python
def test_exclusion_rule_hits_only_when_special_zodiac_is_absent():
    config = PREDICTION_CONFIGS["juesha1xiao"]
    rule = get_generation_rule(config)

    assert rule.verify_hit(config, ("鼠",), _truth(), conn=None) is True
    assert rule.verify_hit(config, ("虎",), _truth(), conn=None) is False
```

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_generation_rules.py tests/unit/test_prediction_hit_policy.py
```

Expected: all pass.

## Task 3: Add the Internal Control Ledger

**Files:**
- Modify: `backend/src/database/schema/prediction.py`
- Create: `backend/src/domains/prediction/generation_control_repository.py`
- Test: `backend/src/tests/unit/test_prediction_generation_control_repository.py`

- [ ] **Step 1: Write the failing reservation test**

```python
def test_cross_site_same_prefix_cannot_be_reserved(tmp_path):
    db_path = str(tmp_path / "controls.sqlite3")
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        first = reserve_control(
            conn, lottery_type_id=3, year=2026, term=131, mode_id=470, web_id=4,
            rule_id="zodiac", rule_revision=1, target_hit=True, verified_hit=True,
            signature=("虎", "猪", "羊"), prefix_signature=("虎",), created_at="2026-07-18T00:00:00Z",
        )
        second = reserve_control(
            conn, lottery_type_id=3, year=2026, term=131, mode_id=470, web_id=5,
            rule_id="zodiac", rule_revision=1, target_hit=True, verified_hit=True,
            signature=("虎", "鼠", "马"), prefix_signature=("虎",), created_at="2026-07-18T00:00:00Z",
        )

    assert first["reserved"] is True
    assert second == {"reserved": False, "reason": "cross_site_prefix_conflict"}
```

Also test `load_adjacent_controls` returns both terms 198 and 200 for a same-site term 199 query, without returning raw stored candidates.

- [ ] **Step 2: Verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_generation_control_repository.py
```

Expected: import failure for the control repository.

- [ ] **Step 3: Add portable table schema**

In `ensure_prediction_tables`, create `prediction_generation_controls` with the unique keys `(lottery_type_id, year, term, mode_id, web_id)` and `(lottery_type_id, year, term, mode_id, prefix_hash)`. Store only `rule_id`, revision, `target_hit`, `verified_hit`, SHA-256 signature hash, SHA-256 prefix hash, timestamps, and issue/site identifiers. Do not store `DrawTruth` or full draw numbers.

- [ ] **Step 4: Implement repository APIs**

Implement `acquire_issue_mode_lock`, `reserve_control`, `list_recent_verified_outcomes`, `load_adjacent_controls`, `load_controls_for_issue`, and `validate_affected_windows`. `reserve_control` uses `INSERT ... ON CONFLICT DO NOTHING` and reports only `reserved` plus a safe conflict reason. Advisory lock executes `SELECT pg_advisory_xact_lock(?)` only for PostgreSQL and is a SQLite no-op.

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_generation_control_repository.py tests/unit/test_prediction_generation_repository.py
```

Expected: all pass.

## Task 4: Select Legal Controlled Candidates

**Files:**
- Create: `backend/src/domains/prediction/candidate_control.py`
- Test: `backend/src/tests/unit/test_prediction_candidate_control.py`

- [ ] **Step 1: Write failing cross-site and adjacent tests**

```python
def test_mode_470_keeps_a_hit_but_changes_its_first_zodiac_for_another_site():
    config = PREDICTION_CONFIGS["pt3xiao"]
    result = choose_controlled_labels(
        config=config, rule=get_generation_rule(config), truth=_truth("虎"),
        predicted_labels=("虎", "猪", "羊"), should_hit=True,
        forbidden_prefixes={("虎",)}, forbidden_signatures=set(), seed="web:5",
    )

    assert result.labels[0] != "虎"
    assert "虎" in result.labels


def test_mode_470_changes_an_adjacent_duplicate_full_signature():
    config = PREDICTION_CONFIGS["pt3xiao"]
    result = choose_controlled_labels(
        config=config, rule=get_generation_rule(config), truth=_truth("虎"),
        predicted_labels=("虎", "猪", "羊"), should_hit=True,
        forbidden_prefixes=set(), forbidden_signatures={("虎", "猪", "羊")}, seed="term:199",
    )

    assert result.signature != ("虎", "猪", "羊")
    assert "虎" in result.labels
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_candidate_control.py
```

Expected: import failure for `candidate_control`.

- [ ] **Step 3: Implement deterministic bounded reselection**

Generate deterministic permutations and substitutions from the rule/config candidate space with a local `random.Random`. Evaluate every candidate through `rule.verify_hit`, reject forbidden prefixes and full signatures, and return `ControlledCandidate(labels, signature, prefix_signature, verified_hit)` only when its verified hit equals `should_hit`. For exclusions, include truth only for controlled misses. On exhaustion raise `ControlledCandidateUnavailable` with a mode ID and a safe reason only.

- [ ] **Step 4: Verify GREEN**

Run the Task 4 test command plus `tests/unit/test_prediction_generation_rules.py`. Expected: all pass.

## Task 5: Integrate Ledger-Controlled Future Generation

**Files:**
- Modify: `backend/src/prediction_generation/service.py`
- Test: `backend/src/tests/unit/test_prediction_generation_control_integration.py`

- [ ] **Step 1: Write failing integration tests**

Use a controlled `pt3xiao` config and future truth sequence. Generate 20 terms in two independent calls, then read only control booleans and assert every rolling 10-term window has at least six verified hits. Generate the same term for web IDs 4 and 5 and assert their mode-470 first zodiac differs. Generate terms 198, 199, and 200 for one site and assert adjacent complete signatures differ.

Add a dynamic unverified-mode test that verifies the existing module-report shape contains a warning and writes neither a created row nor a control row for a future term.

- [ ] **Step 2: Verify RED**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_generation_control_integration.py
```

Expected: current in-memory simulation has no persisted controls and fails the rolling or cross-site assertion.

- [ ] **Step 3: Implement future-only control flow**

For Taiwan future rows with a supported rule, acquire the issue/mode lock, read preceding verified outcomes, choose a target with `AccuracyPolicy`, load same-issue prefix conflicts and both adjacent same-site signatures, select a candidate, re-verify its hit, reserve its control row, then persist the existing created row. Retry candidate selection after a reservation collision. If no candidate is legal, rollback that row and append only a non-sensitive warning to the existing `warnings` list.

Retain the current opened-draw and non-Taiwan paths. Preserve the current `simulation` report keys; populate its hit/miss counts from verified results and do not add target, truth, or signature values.

- [ ] **Step 4: Verify GREEN and API contracts**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_generation_control_integration.py tests/unit/test_prediction_generation_simulation_integration.py tests/unit/test_api_contract_prediction_routes.py
```

Expected: all pass.

## Task 6: Cover Complex Rules and Safely Block Unverifiable Families

**Files:**
- Modify: `backend/src/domains/prediction/generation_rules.py`
- Modify: `backend/src/domains/prediction/candidate_control.py`
- Modify: `backend/src/prediction_generation/service.py`
- Test: `backend/src/tests/unit/test_prediction_generation_rules.py`
- Test: `backend/src/tests/unit/test_mode_474_prediction_module.py`
- Test: `backend/src/tests/unit/test_mode_475_prediction_module.py`
- Test: `backend/src/tests/unit/test_mode_476_prediction_module.py`
- Test: `backend/src/tests/unit/test_mode_478_prediction_module.py`

- [ ] **Step 1: Add failing family tests**

Add tests proving five-element/category/mixed adapters use actual outcome atoms and their config hit checker. Add tests requiring brain teaser and image rules to be `supported is False` with `block_reason="no_verifiable_future_candidate"` until a candidate-to-outcome mapping is explicit. Add image tests that a full truth sentinel is absent from renderer arguments.

- [ ] **Step 2: Verify RED**

Run the new node IDs before adding adapters. Expected: unsupported statuses or outcome assertions fail.

- [ ] **Step 3: Implement only proven adapters**

Add adapters for mappings whose outcome can be derived from `DrawTruth` and fixed mapping data. Keep prose-only text and image modes blocked; do not infer truth from text or image pixels. Preserve their existing non-controlled generation behavior.

- [ ] **Step 4: Verify GREEN**

Run the selected mode tests and the control integration test. Expected: all pass.

## Task 7: Add Truth-Taint Regression Tests

**Files:**
- Create: `backend/src/tests/unit/test_prediction_future_truth_taint.py`
- Modify only if a failing test proves an escaping boundary: `backend/src/prediction_generation/service.py`

- [ ] **Step 1: Write the failing sentinel test**

Use `truth_csv = "01,02,03,04,05,06,49"`. Generate a supported future row, serialize public and legacy history, capture generation logs and image-renderer arguments, then assert:

```python
for value in (row_data, public_payload, legacy_payload, report, captured_logs, image_args):
    assert truth_csv not in repr(value)
assert row_data["res_code"] == ""
assert row_data["res_sx"] == ""
assert row_data["res_color"] == ""
```

Permit the legal single candidate `"49"` in `content`; prohibit only the complete draw and internal control data.

- [ ] **Step 2: Verify RED, then fix only the escaping boundary**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_future_truth_taint.py
```

Expected: any discovered escape fails with its exact boundary. Remove truth-bearing data at that boundary without changing response shape or redacting legal prediction candidates.

- [ ] **Step 3: Verify GREEN**

Run the taint test plus public, legacy, and prediction contract tests. Expected: all pass.

## Task 8: Generate Module Rule Documentation

**Files:**
- Create: `backend/src/domains/prediction/rule_documentation.py`
- Create: `backend/docs/prediction-module-rules.md`
- Test: `backend/src/tests/unit/test_prediction_rule_documentation.py`
- Modify: `backend/CLAUDE.md`
- Modify: `backend/docs/prediction-mechanisms.md`

- [ ] **Step 1: Write the failing renderer test**

```python
def test_rule_document_lists_mode_470_and_blocked_dynamic_configs():
    document = render_prediction_module_rules(PREDICTION_CONFIGS.values())

    assert "| 470 | pt3xiao | 平特3肖 |" in document
    assert "special zodiac is in any candidate" in document
    assert "cross-site prefix: 1" in document
    assert "blocked_pending_rule" in document
```

- [ ] **Step 2: Verify RED**

Run `python -m pytest -q tests/unit/test_prediction_rule_documentation.py`. Expected: import failure.

- [ ] **Step 3: Implement renderer and write document**

Sort by mode ID, deduplicate aliases, and include rule ID/revision, outcome semantics, inclusion/exclusion semantics, candidate count, support status, prefix width, adjacent signature strategy, and future-truth boundary. Write UTF-8 Markdown to `backend/docs/prediction-module-rules.md`. Update `backend/CLAUDE.md` with the mandatory registered-rule/control-reservation boundary, and remove the obsolete statement in `prediction-mechanisms.md` that accuracy is not a goal.

- [ ] **Step 4: Verify GREEN**

Run the documentation test and `git diff --check`. Expected: all pass without whitespace errors.

## Task 9: Full Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run security and ownership scans**

```powershell
cd backend/src
rg -n --glob '*.py' 'truth\.numbers|DrawTruth.*to_public' routes public legacy app_http
rg -n --glob '*.py' 'conn\.execute|\.execute\(|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b' predict/mechanisms.py predict/common.py
```

Expected: no route/public/legacy serialization of future truth; no business SQL in prediction algorithm files.

- [ ] **Step 2: Compile and run the full suite**

```powershell
cd backend/src
python -m compileall .
python -m pytest -q
```

Expected: compilation succeeds and the suite has no failures.

- [ ] **Step 3: Inspect API compatibility**

```powershell
git diff --check
git diff -- backend/src/routes backend/src/domains/prediction/api_response.py backend/docs/API.md
```

Expected: no response-schema change.
