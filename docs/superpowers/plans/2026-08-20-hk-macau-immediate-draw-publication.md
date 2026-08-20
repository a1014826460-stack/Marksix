# HK/Macau Immediate Draw Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish Hong Kong and Macau draw results immediately when a complete new upstream record is observed, while chasing stale upstream data and using the verified csjid fallback source.

**Architecture:** The scheduler normalizes both upstream response shapes into the existing record contract, upserts a complete new record, opens it in the same scheduler cycle, and writes its normal outbox publication. A precise check that finds the primary source stale polls through chase mode and probes the configured csjid fallback; all draw latency arithmetic treats `draw_time` as Beijing time and event instants as UTC.

**Tech Stack:** Python 3.11, requests, existing SQLite/PostgreSQL data adapter, pytest.

---

### Task 1: Normalize csjid responses

**Files:**
- Modify: `backend/src/crawler/result_crawler.py`
- Test: `backend/src/tests/unit/test_scheduler_hk_macau_fast_open.py`

- [x] Parse `result.data.preDrawIssue`, `preDrawCode`, and `preDrawTime` into the existing `issue/open_time/result` contract.
- [x] Preserve `preDrawTime` without timezone conversion because it is Beijing time.
- [x] Omit legacy `lottery_id` and `action` query parameters for csjid URLs.
- [x] Verify the response fixture and request-shape tests.

### Task 2: Publish a new HK/Macau draw in its fetch cycle

**Files:**
- Modify: `backend/src/crawler/scheduler.py`
- Modify: `backend/src/tests/unit/test_hk_macau_precise_open_state.py`
- Test: `backend/src/tests/unit/test_scheduler_hk_macau_fast_open.py`

- [x] Make `_auto_crawl()` call `_open_specific_records()` after an insert/update.
- [x] Retain the existing publication outbox write performed by `_open_specific_records()`.
- [x] Test the new Macau and Hong Kong records are both `is_opened=1` and published in the same cycle.

### Task 3: Chase stale primary results and use fallback

**Files:**
- Modify: `backend/src/crawler/scheduler.py`
- Modify: `.env.example`
- Test: `backend/src/tests/unit/test_scheduler_hk_macau_fast_open.py`

- [x] Set chase mode on a precise primary-source old period so auto-crawl uses the five-second interval.
- [x] Probe the fallback source immediately when the primary source is still on the prior period.
- [x] Fetch the complete record from the fallback after it matches the expected period.
- [x] Read fallback URLs from `DRAW_HK_BACKUP_COLLECT_URL` and `DRAW_MACAU_BACKUP_COLLECT_URL` deployment-secret environment variables.

### Task 4: Beijing-time latency metrics

**Files:**
- Modify: `backend/src/crawler/scheduler.py`
- Test: `backend/src/tests/unit/test_scheduler_hk_macau_fast_open.py`

- [x] Add a helper converting Beijing `draw_time` to UTC before calculating delay.
- [x] Log `public_open_delay_seconds` in the scheduler audit record when a record opens.
- [x] Verify an `21:30:00` Beijing draw and `13:30:05Z` event produces five seconds.

### Task 5: Regression verification

**Files:**
- Test: `backend/src/tests/unit/test_scheduler_hk_macau_fast_open.py`
- Test: `backend/src/tests/unit/test_hk_macau_precise_open_state.py`
- Test: `backend/src/tests/unit/test_scheduler_draw_publication.py`

- [x] Run the focused scheduler and outbox suite.
- [x] Run `pwsh -File .\\scripts\\check-no-secrets.ps1`.