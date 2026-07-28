---
name: prediction-release-review
description: Review every Liuhecai update that can affect prediction generation, scheduler behavior, draw publication, public APIs, or data safety. Use before merging, releasing, or deploying changes to predictions, lottery draws, scheduler workers, alerts, site modules, and public data routes. Requires the generation, missing-data alert, scheduled draw, and public redaction regression suites to pass.
---

# Prediction Release Review

Run this review after every relevant update. This is a release gate: do not
approve, merge, deploy, or claim the changed behavior is safe until all four
required regression groups pass. Work locally only; do not connect to or alter
any server unless the user explicitly authorizes that operation in the current
task.

Run the bundled script from the repository root:

```powershell
pwsh -File .\skills\prediction-release-review\scripts\run-regression.ps1
```

## Hard Release Rules

1. **Future prediction must generate.** For every enabled site and required
   prediction module, the issue after the latest opened draw must have a
   non-empty prediction payload. Accuracy, diversity, deduplication, candidate
   pools, and formatting constraints are quality constraints; none may turn a
   generation request into a skipped or permanently failed future issue.
2. **Missing future predictions must alert.** After the configured automatic
   generation time, the singleton `scheduler-worker` must check every enabled
   site's required module for the target future issue. A missing payload must
   create a durable failed/audit record and send an email alert. It must not
   inspect only the first module. Retry/cooldown may prevent duplicate email,
   but may not hide the persisted failure or suppress the next scheduled check.
3. **Draw opening must be durable and on time.** A due draw is opened only by
   the durable scheduler task with worker lease/locking. Restarting after the
   scheduled time must recover the task without duplicate opening; opening must
   advance the effective next issue/deadline and enqueue the required follow-up
   work.
4. **Never leak future draw truth.** A record with `is_opened=0` is not draw
   truth for public clients. Public latest-draw, draw-history, prediction, site
   page, compatibility, error, and log responses must omit future numbers and
   all result fields (`res_code`, zodiac, color, hit/result status). Only
   authenticated administrator write/read paths may access editable future draw
   records, and even those must not be forwarded into public responses.

## Review Procedure

1. Inspect the diff and identify changes affecting generation, `lottery_draws`,
   scheduler tasks, alert/email delivery, module authorization, or public
   serializers. Read the full call path, not just the modified function.
2. Identify the latest opened issue and the target future issue using the same
   year/term rollover logic as production. Verify enabled sites and all required
   modules, not a representative module.
3. Inspect every rejection path in candidate selection and diversity controls.
   It must either produce a valid fallback candidate or return a visible failure
   that the worker records and alerts on; it must never quietly omit the target
   payload.
4. Verify the scheduled post-generation audit uses durable tasks, server time,
   worker lease locking, persisted run records, retry behavior, and email
   delivery. Verify an audit after the configured time catches a missing target
   payload even when another module is present.
5. Trace public data from database query through serializer and route. For a
   future row, prove no number/result field can reach any unauthenticated
   response, client cache, exception message, or log payload.
6. Run all four test groups with the script. If code changes add a branch,
   failure mode, public route, scheduler task, or module mapping not covered by
   these tests, add a focused regression test before approval.

## Required Test Evidence

The script runs these groups and fails fast on any failure:

- `generation`: future issue generation and generation controls, including a
  constrained candidate path that still creates a payload.
- `missing-alert`: prediction-gap detection and email dispatch for a missing
  required module after automatic generation.
- `scheduled-draw`: durable task creation, due-task execution, restart/retry,
  and Taiwan scheduled opening behavior.
- `public-redaction`: future draw/result redaction in prediction and public
  API serialization.

Record the command and test result in the change/PR description. A green suite
does not waive manual review of a new site/module: add its enabled-module case
to the generation and missing-alert suites first.

## Review Findings Format

Report findings before any summary, ordered by severity, with file and line.
For every blocker, state the broken invariant, reachable trigger, and the test
that must be added or changed. If no findings remain, explicitly state that all
four regression groups passed and list any untested external dependency.
