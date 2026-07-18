# Prediction Category Completion and DAO Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the incremental `predict.mechanisms` category split and move the remaining prediction persistence SQL behind explicit repository/service APIs without changing HTTP response payloads or legacy compatibility exports.

**Architecture:** `predict.mechanisms` remains the compatibility registry and configuration catalogue. Category modules own category-specific formatters, parsers, and outcome helpers; `domains.prediction` repositories own SQL; `prediction_generation` remains an orchestration layer. Existing function names continue to be re-exported from `predict.mechanisms` while callers migrate incrementally.

**Tech Stack:** Python 3, stdlib `sqlite3`/PostgreSQL adapter, pytest, existing `PredictionConfig` registry, `domains.prediction` repository pattern.

---

## Non-Negotiable Compatibility Rules

- Do not change HTTP response fields, field order, status codes, or legacy payload wrappers.
- Do not expose `DrawTruth`, future draw numbers, `res_code`, or simulation-only state in API responses, logs, summaries, or persistence payloads.
- Keep existing `predict.mechanisms` public function names available as category-module re-exports until all callers are migrated.
- Keep `backend/docs/API.md` as the canonical API document; `backend/API.md` is intentionally retired.

### Task 1: Stabilize Existing Text Mapping Extraction

**Files:**
- Modify: `backend/src/predict/mechanisms.py`
- Test: `backend/src/tests/unit/test_predict_text_mapping_category.py`

- [ ] **Step 1: Run the text/category regression suite**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_predict_text_mapping_category.py tests/unit/test_predict_structured_mapping_category.py tests/unit/test_predict_size_parity_category.py tests/unit/test_predict_mixed_category.py tests/unit/test_predict_zodiac_category.py
```

Expected: the suite is green. If collection fails, identify whether a formatter is bound after `PREDICTION_CONFIGS` is initialized.

- [ ] **Step 2: Keep text formatter names bound before configuration construction**

Import the five text formatter helpers from `predict.categories.text_mapping` beside the other category imports:

```python
from predict.categories.text_mapping import (
    format_humor_tail_groups,
    format_juzi_title,
    format_text_history_mapping,
    format_text_pool_jiexi,
    random_text_pool_row,
)
```

Keep file-end aliases only as compatibility documentation; configuration construction must use names available at import time.

- [ ] **Step 3: Verify category behaviour**

Run the command from Step 1. Expected: all tests pass.

### Task 2: Make Existing Category Modules the Active Configuration Dependencies

**Files:**
- Modify: `backend/src/predict/mechanisms.py`
- Test: `backend/src/tests/unit/test_predict_size_parity_category.py`
- Test: `backend/src/tests/unit/test_predict_mixed_category.py`
- Test: `backend/src/tests/unit/test_predict_zodiac_category.py`
- Test: `backend/src/tests/unit/test_predict_structured_mapping_category.py`

- [ ] **Step 1: Add failing configuration-binding tests**

Add tests that assert representative `PREDICTION_CONFIGS` entries use category functions before the file-end compatibility aliases execute:

```python
assert mechanisms.PREDICTION_CONFIGS["danshuangtema"].outcome_loader is size_parity.special_parity_from_row
assert mechanisms.PREDICTION_CONFIGS["pt3xiao"].content_formatter is zodiac.format_zodiac_csv
assert mechanisms.PREDICTION_CONFIGS["rcca"].content_formatter is structured_mapping.format_dynamic_pipe_groups("mode_payload_3")
```

For formatter factories, assert generated output from a fake connection rather than object identity when the factory creates a closure.

- [ ] **Step 2: Run the new tests to verify the old local definitions are still selected**

Run the exact new tests with `python -m pytest -q <test-nodeids>`. Expected: failure showing configuration captured a local `mechanisms.py` function.

- [ ] **Step 3: Bind category implementations before `PREDICTION_CONFIGS`**

After each category module receives its required injected dependency, bind category functions before the `PREDICTION_CONFIGS` literal is evaluated. Keep a local helper only when it composes category functions with a `mechanisms.py`-specific dependency.

- [ ] **Step 4: Remove dead duplicate function definitions**

Remove only functions whose definitions have a like-for-like category replacement and whose configuration bindings are covered by tests. Do not remove configuration factories or dynamic classifier functions in this task.

- [ ] **Step 5: Run category and configuration regressions**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_predict_*_category.py tests/unit/test_predict_registry.py tests/unit/test_prediction_predict_repository.py
python -m py_compile predict/mechanisms.py
```

Expected: all pass.

### Task 3: Extract Number and Image Category Helpers

**Files:**
- Create: `backend/src/predict/categories/number.py`
- Create: `backend/src/predict/categories/image.py`
- Modify: `backend/src/predict/categories/__init__.py`
- Modify: `backend/src/predict/mechanisms.py`
- Test: `backend/src/tests/unit/test_predict_number_category.py`
- Test: `backend/src/tests/unit/test_predict_image_category.py`

- [ ] **Step 1: Write failing number-category tests**

Test `special_number_from_row`, `format_24_numbers`, segment formatters, and fixed mapping fallbacks using only fake rows/connections. The test must import `predict.categories.number` and assert the legacy `mechanisms` exports remain callable.

- [ ] **Step 2: Verify the test fails because the category module is absent**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_predict_number_category.py
```

Expected: import failure for `predict.categories.number`.

- [ ] **Step 3: Implement the minimal number category**

Move only pure number/segment helpers. Inject any fixed-map or row helper dependency rather than importing `predict.mechanisms`.

- [ ] **Step 4: Repeat TDD for image helper boundaries**

Extract only formatter/rendering metadata helpers used by image modes. Leave image database writes and batch orchestration in `prediction_generation`.

- [ ] **Step 5: Verify category compatibility**

Run the two new tests plus existing image generation tests. Expected: all pass and public `mechanisms` names still resolve.

### Task 4: Move Prediction State and Generation Log Persistence Behind DAO APIs

**Files:**
- Create or modify: `backend/src/domains/prediction/state_repository.py`
- Create or modify: `backend/src/domains/prediction/generation_log_repository.py`
- Modify: `backend/src/predict/mechanism_status.py`
- Modify: `backend/src/prediction_generation/service.py`
- Test: `backend/src/tests/unit/test_prediction_state_repository.py`
- Test: `backend/src/tests/unit/test_prediction_generation_log_repository.py`

- [ ] **Step 1: Write failing repository tests**

Cover:

```python
assert get_mechanism_statuses(conn) == {"pt3xiao": 1}
set_mechanism_status(conn, "pt3xiao", 0)
assert get_mechanism_statuses(conn)["pt3xiao"] == 0
```

and verify a generation error log writer accepts only an allowlisted payload (`message`, `module`, `task_key`, issue identifiers) and rejects/sanitizes truth-bearing keys such as `numbers` and `res_code`.

- [ ] **Step 2: Run the tests and verify they fail for absent repository APIs**

Run the exact two test files. Expected: import or missing-function failures.

- [ ] **Step 3: Implement repositories and thin compatibility delegates**

`predict.mechanism_status` delegates to a state repository. `prediction_generation.service` delegates error-log persistence to a generation-log repository. Preserve transaction semantics and all existing caller-visible exception behaviour.

- [ ] **Step 4: Verify the state/log tests and existing generation tests**

Run:

```powershell
cd backend/src
python -m pytest -q tests/unit/test_prediction_state_repository.py tests/unit/test_prediction_generation_log_repository.py tests/unit/test_prediction_generation_simulation_integration.py
```

Expected: all pass.

### Task 5: Documentation and Full Regression

**Files:**
- Modify: `backend/README_CN.md`
- Modify: `backend/CLAUDE.md`
- Modify: `backend/docs/API.md`

- [ ] **Step 1: Document the category/DAO boundaries**

Record the active category modules, compatibility-export rule, repository-only SQL rule, truth-safety rule, and canonical API document location. Do not alter endpoint examples or response schemas.

- [ ] **Step 2: Run static SQL ownership scans**

Run:

```powershell
cd backend/src
rg -n --glob '*.py' 'conn\.execute|\.execute\(|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b' predict/mechanisms.py predict/common.py predict/_db_helpers.py
```

Expected: no business SQL in the three algorithm/compatibility files.

- [ ] **Step 3: Run compilation and full regression**

Run:

```powershell
cd backend/src
python -m compileall .
python -m pytest -q
```

Expected: no compilation failures and no regression below the pre-task baseline.
