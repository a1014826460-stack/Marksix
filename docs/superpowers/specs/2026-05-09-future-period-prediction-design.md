# Future Period Prediction Generation — Design Spec

Date: 2026-05-09 | Status: Approved

## Context

The existing `bulk_generate_site_prediction_data` generates predictions only for already-opened lottery draws (where `res_code` is known). Users need the ability to predict 1-2 future (unopened) periods where winning numbers are unknown.

## Design Decisions (from brainstorming)

- **Trigger**: Extend `bulk_generate_site_prediction_data` with optional `future_periods` param (no new API endpoint)
- **Issue numbering**: Simple increment from latest draw (term+1, term+2), year carries over at boundary
- **Empty res_code**: Reuse existing `res_code=None` path in `predict()` — algorithms already handle this
- **Performance target**: ≤ 2 seconds for full site (35 modules × 2 periods)
- **Difference mechanism**: Term-aware random seed passed to `predict()`

## Files to Modify

| File | Change |
|------|--------|
| `src/predict/common.py` | `predict()` — add `random_seed: str | None = None` parameter |
| `src/admin/prediction.py` | `bulk_generate_site_prediction_data()` — add `future_periods` handling |

No new files. No API schema changes. No database schema changes.

## Data Flow

```
bulk_generate_site_prediction_data(db_path, site_id, payload)
  payload may include: future_periods (int, default 0)

  ── Phase 1: Existing logic (unchanged) ──
  For each opened draw in range → predict with res_code → upsert

  ── Phase 2: Future periods (NEW, only if future_periods > 0) ──
  latest_draw = last opened draw for lottery_type
  For p in 1..future_periods:
    next_year, next_term = compute_next(latest_draw, offset=p)
    For each enabled module:
      result = predict(config, res_code=None, random_seed=f"{next_year}{next_term:03d}")
      row_data = build_generated_prediction_row_data(
        res_code="",  # forced empty for future
        ...
      )
      upsert_created_prediction_row(conn, table_name, row_data)
```

## Random Seed for Differentiation

`predict()` signature change:
```python
def predict(*, config, res_code, content, source_table,
            db_path, target_hit_rate, random_seed=None):
```

When `random_seed` is not None, call `random.seed(hash(random_seed))` before prediction logic. Different seeds (e.g. "2026128" vs "2026129") produce different random selections, guaranteeing adjacent periods differ.

## Record Format

| Field | T period (existing) | T+1/T+2 (new) |
|-------|---------------------|---------------|
| type | filled | filled (same lottery type) |
| year | draw value | computed future year |
| term | draw value | computed future term |
| web | "4" | "4" |
| content | prediction result | prediction result |
| res_code | winning numbers | **empty string** |
| res_sx | zodiac | **empty string** |
| res_color | wave color | **empty string** |

## API Compatibility

- Path: `POST /api/admin/sites/{id}/prediction-modules/generate-all` — unchanged
- Request body: new optional field `future_periods` (int, default 0)
- Response body: unchanged structure, counts reflect additional records
- Backward compatible: omitting `future_periods` preserves existing behavior

## Verification

1. Call generate-all with `future_periods: 2` → verify T+1/T+2 records exist in created schema
2. Verify T+1/T+2 have `res_code = ""`, `res_sx = ""`, `res_color = ""`
3. Verify T+1 content ≠ T+2 content (different random seeds)
4. Verify existing behavior unchanged (future_periods omitted or 0)
5. Syntax check + server start + API smoke test
