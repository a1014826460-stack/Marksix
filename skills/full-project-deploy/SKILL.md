---
name: full-project-deploy
description: Deploy the complete Liuhecai codebase and vendor static assets to its central backend server and frontend-only node while preserving production databases, generated prediction/draw data, uploads, certificates, and local Nginx configuration. Use for requests to sync, publish, or deploy all updated project code rather than a one-file emergency patch.
---

# Full Project Deploy

Use this for a full release. Do not replace it with selective `scp` unless the
user explicitly requests an emergency single-file patch.

## Scope

- Synchronize all Git-tracked project files, including `frontend/public/vendor/**`
  HTML, CSS, JS, images, manifests, adapters, backend mappings, tests, and
  deployment code.
- Preserve runtime state: Docker volumes/database, `backend/data/lottery_data`,
  `backend/data/api_data`, generated `backend/data/Images/mode_*/prediction`,
  uploads, logs, backups, `.env`, certificates, ACME webroots, and ignored
  local Nginx configuration.
- Never run `docker compose down -v`, delete Docker volumes, copy a database,
  or run the full Compose stack on a frontend-only node.

## Preflight

1. Require explicit current-message authorization for every remote operation.
2. Ensure local code is committed and pushed. Run targeted tests, site
   validation for changed sites, and `git diff --check`.
3. Confirm `git status --short` has no unintended changes. Do not deploy
   uncommitted code as a full release.
4. On each server, capture `HEAD`, service health, `nginx -t`, and a timestamped
   backup of modified tracked files plus untracked/ignored runtime paths.
5. Verify the backend server runs `docker-compose.yml` and the frontend-only
   node runs `docker-compose.frontend-node.yml` with central API URLs.

## Release Procedure

1. On each server, `git fetch origin main` and synchronize tracked files to the
   approved release commit. If local modifications would conflict, archive them
   first, then use `git reset --hard <release-commit>`.
2. Restore protected runtime paths from the backup before any service restart.
   In particular, restore certificates before `nginx -t`.
3. Central backend server: run database migrations only when the release
   includes schema changes; rebuild and restart the affected `python-api`,
   `scheduler-worker`, and `frontend` services. Do not overwrite database data.
4. Frontend-only node: rebuild and restart only `frontend` using
   `docker compose -f docker-compose.frontend-node.yml`; never start backend,
   worker, migration, or database services there.
5. Run `nginx -t`, reload Nginx only after it passes, then wait for all expected
   health checks.

## Required Verification

- Confirm both servers run the approved Git commit.
- Confirm central API `/health` and every hosted site return HTTP 200.
- For every changed static image, compare local and remote SHA-256, then fetch
  the public URL and require HTTP 200 with the expected content type.
- For changed vendor sites, verify entry HTML, console errors, draw endpoint,
  and prediction endpoint. For `twssz`, compare returned `canonical_modules`
  keys/counts against local expectations for all three `lottery_type` values.
- Report backups, commit, rebuilt services, Nginx result, and any residual
  runtime-only differences.

## Failure Handling

- Stop before rebuilding if a protected runtime path cannot be backed up or
  restored.
- If Nginx cannot load a certificate after synchronization, restore the saved
  certificate tree first, rerun `nginx -t`, then reload.
- If a full release is not possible, do not silently fall back to selected
  files. State the blocker and request approval for a scoped emergency patch.
