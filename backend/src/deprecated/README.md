# Deprecated Prediction Generators

This directory contains legacy prediction-generation scripts that are no longer authoritative.

## Why these files are deprecated

They were moved here because they each carried independent generation logic and could diverge from the production admin path.

Typical problems:

- their own draw traversal logic
- their own row assembly logic
- their own fallback/random behavior
- potential mismatch with current admin defaults and normalization rules

## Canonical replacement

The supported generation path is documented in:

- `backend/docs/prediction-generation-refactor-plan.md`

Target canonical flow:

- Admin button
  -> `/admin/sites/{site_id}/prediction-modules/generate-all`
  -> shared generation service

Automatic generation must call the same shared service.

## Files currently deprecated

- `utils/generate_predictions.py`
- `utils/generate_all_predictions.py`
- `tools/generate_hk_macau_predictions_via_api.py`

These files should not be used as references for future feature work except during migration or historical debugging.
