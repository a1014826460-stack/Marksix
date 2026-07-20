# Runtime Environment Isolation Design

## Goal

Prevent a development process from connecting to the production container database,
and prevent a production deployment from using a workstation PostgreSQL DSN.

## Decision

Two explicit runtime profiles are the only supported service-start modes:

- `development`: Windows host processes use the native PostgreSQL 18 service at
  `127.0.0.1:5432`. Local secrets live only in ignored `backend/.env.local`.
- `production`: Docker Compose services use `pgbouncer:6432` on the Compose network.
  Production secrets live only in ignored root `.env` or deployment secrets.

The backend process requires `LIUHECAI_RUNTIME_ENV` and validates its PostgreSQL DSN
before opening a connection. Development accepts only the loopback host and port
5432. Production accepts only host `pgbouncer` and port 6432. A missing or invalid
profile is a startup error.

## Boundaries

- `backend/scripts/restart-backend.ps1` is development-only. It sets
  `LIUHECAI_RUNTIME_ENV=development`, loads `backend/.env.local`, requires the
  Windows `postgresql-x64-18` service to be running, and rejects Compose DSNs.
- `docker-compose.yml`, `deploy/deploy.sh`, and `deploy/verify.sh` are
  production-only. Compose injects `LIUHECAI_RUNTIME_ENV=production` into API,
  worker, and migration containers; the deployment scripts reject a root `.env`
  that defines a host-side `DATABASE_URL`.
- Runtime validation is implemented centrally in `backend/src/runtime_environment.py`
  so command-line services cannot bypass the shell-script checks.

## Error Handling

Validation errors name the expected profile, accepted DSN endpoint, and the actual
endpoint without exposing passwords. The development restart script checks its
profile and Windows service before terminating existing managed processes.

## Verification

- Unit tests cover accepted and rejected DSNs for both profiles and required profile
  presence.
- Script contract tests assert the development script assigns the development profile
  and checks `postgresql-x64-18`; deployment scripts and Compose assert production
  profile injection plus rejection of root `DATABASE_URL`.
- Development smoke test runs `/api/health` after restarting against the native
  PostgreSQL service.
