# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

六合彩 (Mark Six Lottery) platform with three active components:

- **Python API** — lightweight stdlib HTTP server for data fetching, normalization, prediction, and backend business APIs
- **Backend Admin UI** — Next.js app for CMS/admin workflows
- **Frontend Public Site** — Next.js app serving the public lottery site and compatibility API layer

## Commands

### Python Backend API

```powershell
# Start API server
python backend/src/app.py --host 127.0.0.1 --port 8000

# Start API server with explicit PostgreSQL DSN
python backend/src/app.py --host 127.0.0.1 --port 8000 --db-path "postgresql://postgres:pass@localhost:5432/liuhecai"

# Run prediction via CLI
python backend/src/predict/run_prediction.py --mechanism title_234 --json
python backend/src/predict/run_prediction.py --list-mechanisms
```

Important:

- Production runtime uses PostgreSQL
- Do not document or assume SQLite as the default production database
- The current refactored repo does not include a ready-to-run SQLite -> PostgreSQL migration script

### Backend Admin UI

```powershell
cd backend
npm run dev -- --hostname 127.0.0.1 --port 3002
npm run build
npm run lint
```

Browser entry:

- `http://127.0.0.1:3002/admin/login`

Admin API flow:

- Browser -> `/admin/api/python/*`
- Next.js proxy -> Python `/api/*`

### Frontend Public Site

```powershell
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
npm run build
npm run lint
```

Public entry note:

- Canonical local entry is `http://127.0.0.1:3000/?t=3`
- Query param mapping: `t=3` Taiwan, `t=2` Macau, `t=1` Hong Kong
- Root `/` is normalized to `/?t=3`
- The production-facing foreground path is the legacy shell under `frontend/public/vendor/shengshi8800/**`
- `frontend/app/legacy-shell/page.tsx` is mainly for debug/fallback, not the main documented public entry

Frontend API note:

- Browser-facing `/api/*` on the frontend is a compatibility layer implemented in `frontend/app/api/**/route.ts`
- Do not assume frontend `/api/*` is the same thing as Python native `/api/*`

### Testing

```powershell
# Run API smoke test (requires server running on port 8000)
python backend/src/test/api_test.py
```

## Architecture

### Directory Structure

```text
Liuhecai/
├── backend/
│   ├── src/
│   │   ├── app.py                 # Python HTTP API server
│   │   ├── config.py              # Config loader
│   │   ├── config.yaml            # YAML defaults
│   │   ├── db.py                  # Database access layer
│   │   ├── predict/
│   │   │   ├── mechanisms.py
│   │   │   ├── common.py
│   │   │   └── run_prediction.py
│   │   ├── utils/
│   │   │   ├── normalize_payload_tables.py
│   │   │   └── build_text_history_mappings.py
│   │   └── test/
│   │       └── api_test.py
│   ├── app/                       # Next.js admin app
│   │   ├── api/python/[...path]/route.ts  # Proxy -> Python API
│   │   └── ...
│   ├── components/
│   ├── data/                      # Images + legacy data artifacts
│   └── lib/
├── frontend/
│   ├── app/
│   │   ├── api/                   # Frontend compatibility API routes
│   │   ├── legacy-shell/          # Debug/fallback shell
│   │   └── page.tsx               # Canonical root redirect -> /?t=3
│   ├── lib/
│   │   ├── backend-api.ts
│   │   └── site-page.ts
│   ├── public/
│   │   └── vendor/shengshi8800/** # Active legacy foreground assets
│   └── ...
├── deploy/
├── DEPLOY.md
└── readme.md
```

## Admin Interfaces

Use the Next.js admin as the main documented admin surface:

1. **Next.js Admin UI** at `http://127.0.0.1:3002/admin/login`
2. **Python API native endpoints** behind `/api/admin/*`

If you refer to browser usage, prefer the Next.js admin entry and its `/admin/api/python/*` proxy path.

## Configuration System

Bootstrap defaults primarily live in `backend/src/runtime_config.py`, with runtime overrides coming from the database-backed `system_config` table and environment variables where appropriate.

## API Notes

- Python native API paths are `/api/*`
- Admin browser proxy paths are `/admin/api/python/*`
- Frontend browser-facing `/api/*` is a compatibility layer and may map to Python public or legacy endpoints internally

When documenting or debugging requests, always distinguish those three layers.
