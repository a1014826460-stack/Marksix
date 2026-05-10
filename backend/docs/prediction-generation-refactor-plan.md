# Prediction Generation Refactor Plan

## Goal

Unify prediction generation behind one admin-triggered entry and one shared core service, while enforcing deterministic exceptions and cross-term diversity rules for normal modules.

This document is the source of truth for:

- the only supported admin generation entry
- the shared core generation method
- diversity constraints for generated content
- exception rules for modules such as `mode_id=197`
- deprecation scope for legacy multi-entry generators

## Current-State Decision Summary

### Actual production path

The current production admin path is:

`management-pages.tsx`
-> `POST /admin/sites/{site_id}/prediction-modules/generate-all`
-> `bulk_generate_site_prediction_data()`
-> `predict()`
-> `build_generated_prediction_row_data()`
-> `upsert_created_prediction_row()`

Files:

- `backend/components/admin/management-pages.tsx`
- `backend/src/app.py`
- `backend/src/admin/prediction.py`
- `backend/src/utils/created_prediction_store.py`

### Why the old scripts are no longer authoritative

The following files contain overlapping generation logic and are no longer the canonical implementation:

- `backend/src/utils/generate_predictions.py`
- `backend/src/utils/generate_all_predictions.py`
- `backend/src/tools/generate_hk_macau_predictions_via_api.py`

Reasons:

- they each implement their own draw traversal and row assembly
- they can bypass current admin service defaults and future normalization rules
- they make it difficult to guarantee identical behavior across admin, automation, and CLI paths

## Final Target Architecture

### Single admin entry

Only one administrator-facing generation entry remains supported:

- Frontend button:
  `management-pages.tsx -> POST /admin/sites/{site_id}/prediction-modules/generate-all`

The frontend button is the user-facing trigger.
The backend route is its required transport layer, not a second business entry.

### Shared automatic entry

The automatic scheduler must call the same core service as the admin entry.

It may differ only in:

- `trigger="auto_task"`
- explicit input issue range chosen by scheduler policy

It must not differ in:

- mechanism selection semantics
- default `future_periods`
- content diversity handling
- special-module exception handling
- row normalization and storage logic

### Shared core service

Introduce a dedicated generation service module:

- `backend/src/prediction_generation/service.py`

Primary API:

```python
def generate_prediction_batch(
    db_path: str | Path,
    *,
    site_id: int,
    lottery_type: int,
    start_issue: tuple[int, int],
    end_issue: tuple[int, int],
    mechanism_keys: list[str] | None,
    future_periods: int,
    trigger: str,
) -> dict[str, Any]:
    ...
```

Secondary API:

```python
def generate_prediction_row(
    db_path: str | Path,
    *,
    site_id: int,
    mechanism_key: str,
    mode_id: int,
    table_name: str,
    lottery_type: int,
    year: int,
    term: int,
    res_code: str | None,
    web_value: str = "4",
    trigger: str,
) -> dict[str, Any]:
    ...
```

## Responsibility Split

### API / Trigger Layer

Files:

- `backend/src/app.py`
- `backend/components/admin/management-pages.tsx`
- `backend/src/crawler/crawler_service.py`

Responsibilities:

- authentication
- request validation
- trigger selection
- explicit parameter passing into the core service

### Generation Service Layer

File:

- `backend/src/prediction_generation/service.py`

Responsibilities:

- site module resolution
- draw-range expansion
- per-row generation orchestration
- diversity enforcement
- storage calls

### Diversity Layer

File:

- `backend/src/prediction_generation/diversity.py`

Responsibilities:

- parse array-like content
- compare with recent rows of same module
- enforce first-two-item variation for normal modules
- bypass exception modules

### Storage Layer

File:

- `backend/src/utils/created_prediction_store.py`

Responsibilities:

- upsert to created schema
- special-window normalization for `mode_id=197`
- whole-window synchronization for shared-window modules

## Diversity Rules

### Default rule

For normal modules, different terms must not reuse the same leading prediction pattern.

When `content` is an array-like sequence, enforce:

1. `content[0]` must differ from the immediately previous generated row of the same module.
2. `(content[0], content[1])` must differ from recent generated rows of the same module.
3. If the content has fewer than 2 items, enforce uniqueness on the full available prefix.

This rule applies to the same logical module scope:

- same `site_id`
- same `mode_id`
- same `type`
- same `web`

### Allowed repair actions

If the newly generated row violates diversity:

1. swap the first two items
2. rotate within the first four items
3. re-sample from prediction labels if the mechanism supports reformatting
4. retry at most 5 times

If still unresolved:

- persist the last candidate
- emit a warning in the generation report

### Exception modules

Modules are exempt from diversity enforcement when they intentionally share content across a logical window.

Current exception rule:

- `mode_id == 197`

Configuration-oriented form:

- `diversity_policy == "window_shared"`

Default policy for normal modules:

- `diversity_policy == "unique_first_two"`

Future optional policy:

- `diversity_policy == "free"`

### Exception rationale

`mode_id=197` is a three-period shared-window module.
Rows with the same `(type, year, web, start, end)` must share the exact same `content`.
This overrides cross-term diversity rules inside that window.

## Canonical Entry Policy

### Supported admin action

- Supported:
  `POST /admin/sites/{site_id}/prediction-modules/generate-all`

### Deprecated admin actions

- `POST /admin/sites/{site_id}/prediction-modules/run`
- `POST /admin/sites/{site_id}/mode-payload/{table}/regenerate`

These must be retired because they introduce alternate generation semantics and bypass the unified batch service contract.

## CLI Policy

CLI tools may remain for operations, but they must be thin wrappers over `generate_prediction_batch()`.

They must not:

- implement their own draw scanning
- implement their own content randomization
- implement their own direct fallback prediction logic

## Verification Standard

### Normal-module diversity example

Expected valid sample shape for a normal array-based module:

```json
[
  { "term": "201", "content": ["鼠|07", "猴|11", "鸡|10", "狗|09"] },
  { "term": "202", "content": ["牛|06", "鸡|10", "猴|11", "狗|09"] },
  { "term": "203", "content": ["虎|05", "鼠|07", "鸡|10", "狗|09"] }
]
```

### Shared-window exception example

Expected valid sample shape for `mode_id=197`:

```json
[
  {
    "term": "128",
    "start": "128",
    "end": "130",
    "content": ["狗|09,21,33,45", "虎|05,17,29,41", "鼠|07,19,31,43", "鸡|10,22,34,46"]
  },
  {
    "term": "129",
    "start": "128",
    "end": "130",
    "content": ["狗|09,21,33,45", "虎|05,17,29,41", "鼠|07,19,31,43", "鸡|10,22,34,46"]
  },
  {
    "term": "130",
    "start": "128",
    "end": "130",
    "content": ["狗|09,21,33,45", "虎|05,17,29,41", "鼠|07,19,31,43", "鸡|10,22,34,46"]
  }
]
```

## Execution Plan

1. Create `prediction_generation/service.py`
2. Create `prediction_generation/diversity.py`
3. Redirect `bulk_generate_site_prediction_data()` to the shared service
4. Redirect auto task generation to the same shared service
5. Convert CLI scripts into thin wrappers only
6. Retire deprecated admin/API entries
7. Validate normal diversity and shared-window exceptions
