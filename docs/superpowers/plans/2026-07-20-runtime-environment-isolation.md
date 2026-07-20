# Runtime Environment Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce distinct database targets for Windows development and Docker Compose production.

**Architecture:** A backend runtime-profile validator parses PostgreSQL DSNs and permits only loopback `:5432` in development and Compose `pgbouncer:6432` in production. The development PowerShell launcher and production shell/Compose launchers set and verify their own profiles before starting services.

**Tech Stack:** Python 3, pytest, PowerShell 7, Bash, Docker Compose, PostgreSQL.

---

### Task 1: Central runtime profile validation

**Files:**
- Create: `backend/src/runtime_environment.py`
- Modify: `backend/src/app.py`
- Modify: `backend/src/scheduler_worker.py`
- Test: `backend/src/tests/unit/test_runtime_environment.py`

- [ ] Write failing tests for development, production, missing-profile and cross-profile DSNs.
- [ ] Run the focused pytest file and confirm the new validator import fails.
- [ ] Implement `validate_runtime_database_target()` with password-redacted errors.
- [ ] Call it before API and worker initialization.
- [ ] Re-run focused tests and commit the task.

### Task 2: Development launcher guard

**Files:**
- Modify: `backend/scripts/restart-backend.ps1`
- Modify: `backend/src/tests/unit/test_scheduler_worker_separation.py`

- [ ] Write a failing script-contract assertion for `LIUHECAI_RUNTIME_ENV=development`
  and `postgresql-x64-18` status validation.
- [ ] Run the focused test and confirm failure.
- [ ] Add the development profile and native-service check before stopping processes.
- [ ] Re-run the focused test and commit the task.

### Task 3: Production launcher guard

**Files:**
- Modify: `docker-compose.yml`
- Modify: `deploy/deploy.sh`
- Modify: `deploy/verify.sh`
- Create: `deploy/tests/test-runtime-environment-isolation.sh`

- [ ] Write a failing static contract test for production profile injection and root
  `DATABASE_URL` rejection.
- [ ] Run the shell contract and confirm failure.
- [ ] Inject production profile into Compose backend services and add deployment/
  verification environment assertions.
- [ ] Re-run the shell contract and commit the task.

### Task 4: Templates and operational documentation

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `DEPLOY.md`

- [ ] Document the two exclusive profiles, their secret file locations and commands.
- [ ] Explicitly prohibit root `.env` `DATABASE_URL` and Docker Compose for Windows development.
- [ ] Run all tests, local development smoke test, whitespace check and commit.
