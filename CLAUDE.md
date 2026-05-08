# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

六合彩 (Mark Six Lottery) platform with three components:
- **Python API** — lightweight HTTP server (stdlib only, no FastAPI/Django) for data fetching, normalization, and prediction
- **Backend Admin UI** — Next.js app for CMS (sites, users, draws, lottery types, prediction modules)
- **Frontend Public Site** — Next.js app serving the public lottery data display

## Commands

### Python Backend API
```powershell
# Start API server (default: SQLite)
python backend/src/app.py --host 127.0.0.1 --port 8000

# Start with PostgreSQL
python backend/src/app.py --host 127.0.0.1 --port 8000 --db-path "postgresql://postgres:pass@localhost:5432/liuhecai"

# Run prediction via CLI
python backend/src/predict/run_prediction.py --mechanism title_234 --json
python backend/src/predict/run_prediction.py --list-mechanisms

# Migrate SQLite → PostgreSQL
python backend/src/utils/migrate_sqlite_to_postgres.py --source-sqlite backend/data/lottery_modes.sqlite3 --target-dsn "postgresql://user:pass@host:5432/liuhecai"
```

### Backend Admin UI (port 3002)
```powershell
cd backend
npm run dev -- --hostname 127.0.0.1 --port 3002
npm run build
npm run lint
```

### Frontend Public Site (port 3000)
```powershell
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
npm run build
npm run lint
```

Public entry note:
- Use `http://127.0.0.1:3000/legacy-shell?t=3` as the main frontend entry.
- `http://127.0.0.1:3000/` now only redirects to `/legacy-shell?t=3`.
- The old React homepage previously mounted at `/` is archived at `frontend/app/_archived/root-home-page.tsx` and is paused. Avoid using `/` as the working or acceptance URL.
- Query param mapping for `legacy-shell`: `t=3` Taiwan, `t=2` Macau, `t=1` Hong Kong.

### Testing
```powershell
# Run API smoke test (requires server running on port 8000)
python backend/src/test/api_test.py
```

## Architecture

### Directory Structure
```
Liuhecai/
├── backend/
│   ├── src/
│   │   ├── app.py                 # Python HTTP API server (ThreadingHTTPServer) + built-in admin SPA
│   │   ├── config.py              # Config loader (reads config.yaml)
│   │   ├── config.yaml            # YAML config file with defaults (passwords, URLs, tokens)
│   │   ├── db.py                  # SQLite/PostgreSQL compatibility layer
│   │   ├── predict/
│   │   │   ├── mechanisms.py      # All prediction algorithms (single file, ~30+ mechanisms)
│   │   │   ├── common.py          # Shared prediction utilities, zodiac/number maps
│   │   │   └── run_prediction.py  # CLI entry point for predictions
│   │   ├── utils/
│   │   │   ├── data_fetch.py              # Fetch lottery data from remote sites
│   │   │   ├── normalize_sqlite.py        # Normalize raw data into mode_payload_* tables
│   │   │   ├── build_text_history_mappings.py  # Build text history mapping pool
│   │   │   └── migrate_sqlite_to_postgres.py
│   │   └── test/
│   │       └── api_test.py        # Quick API smoke test
│   ├── app/                       # Next.js admin CMS pages (port 3002)
│   │   ├── api/python/[...path]/route.ts  # Proxy → Python API
│   │   ├── login/, users/, draws/, sites/, numbers/, lottery-types/
│   │   └── globals.css            # Green theme CSS variables
│   ├── components/                # shadcn/ui components
│   ├── data/                      # Default SQLite DB + images
│   └── lib/                       # Shared utilities
├── frontend/
│   ├── app/                       # Next.js public site pages (port 3000)
│   │   ├── api/lottery-data/route.ts  # Proxy → Python API
│   │   ├── legacy-shell/page.tsx  # Main public entry, uses t=3/2/1 route param
│   │   ├── _archived/root-home-page.tsx # Archived old React homepage, paused
│   │   └── page.tsx               # Root redirect → /legacy-shell?t=3
│   ├── components/                # UI components (Header, LotteryResult, etc.)
│   ├── lib/
│   │   ├── backend-api.ts         # Centralized API client for Python backend
│   │   ├── site-page.ts           # TypeScript types for public API responses
│   │   └── api/predictionRunner.ts
│   └── public/                    # Static assets
├── .claude/settings.json
└── readme.md
```

### Two Admin Interfaces

The system has **two admin interfaces** — use the correct one:

1. **Python API Built-in Admin** (`http://127.0.0.1:8000/admin`) — Full-featured SPA built into app.py with sidebar navigation. Covers all management functions: dashboard, users, lottery types, draws, sites, numbers, prediction modules, and site data management. Authentication via localStorage token.

2. **Next.js Admin UI** (`http://127.0.0.1:3002/login`) — Alternative admin interface using shadcn/ui components. Runs as a separate Next.js dev server. Has same functional coverage.

### Configuration System

All hardcoded constants and defaults are in `backend/src/config.yaml`:
- Database DSN, admin credentials, JWT settings
- Site defaults (URLs, tokens, request limits)
- Legacy image paths and IDs

The config is loaded by `backend/src/config.py` with a built-in YAML parser (stdlib only, no pyyaml dependency). Missing keys fall back to sensible defaults.

### Admin API Endpoints (all prefixed with `/api/admin/`)
| Entity | GET | POST | PUT/PATCH | DELETE |
|--------|-----|------|-----------|--------|
| Users | /users | /users | /users/{id} | /users/{id} |
| Lottery Types | /lottery-types | /lottery-types | /lottery-types/{id} | /lottery-types/{id} |
| Draws | /draws | /draws | /draws/{id} | /draws/{id} |
| Numbers | /numbers | /numbers | /numbers/{id} | /numbers/{id} |
| Sites | /sites | /sites | /sites/{id} | /sites/{id} |
| Prediction Modules | /sites/{id}/prediction-modules | POST (add) | PATCH {id} (update) | DELETE {id} |
| Run Prediction | — | /sites/{id}/prediction-modules/run | — | — |
| Fetch Data | — | /sites/{id}/fetch | — | — |
