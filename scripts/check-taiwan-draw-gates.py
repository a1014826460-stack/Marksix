"""Run the fixed Taiwan draw release contracts without connecting to production."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND_TESTS = [
    "test_latest_draw_reveal_slice.py", "test_public_draw_full_release.py",
    "test_public_draw_history_delay.py", "test_api_contract_public_routes.py",
    "test_legacy_taiwan_result_gate.py", "test_legacy_frontend_compat.py",
    "test_legacy_frontend_compat_xiaoma2.py", "test_vendor_result_gate.py",
    "test_public_result_alias_gate.py",
    "test_prediction_response_result_gate.py", "test_api_contract_prediction_routes.py",
    "test_admin_result_release_boundary.py", "test_dashboard_operations.py",
    "test_taiwan_task_deadline_poll.py", "test_scheduler_worker_separation.py",
    "test_draw_reveal_probe.py",
]
FRONTEND_TESTS = [
    "kj-panel-loading-contract.mjs", "kj-panel-unification-contract.mjs",
    "kj-panel-reveal-anchor-contract.mjs", "kj-panel-reveal-timeline-contract.mjs",
    "kj-panel-server-reveal-contract.mjs", "kj-panel-recovery-contract.mjs",
    "kj-panel-timing-parity-contract.mjs", "history-unification-contract.mjs",
    "draw-history-gate-contract.mjs", "taiwan-draw-proxy-gate-contract.mjs",
    "draw-proxy-no-store-contract.mjs", "public-api-no-store-contract.mjs",
]


def main() -> int:
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    for key in ("DATABASE_URL", "TEST_DATABASE_URL", "DATABASE_WRITE_URL", "DATABASE_READ_URL"):
        env.pop(key, None)
    commands = [([sys.executable, "-m", "pytest", "-q", *[f"tests/unit/{name}" for name in BACKEND_TESTS]], ROOT / "backend/src")]
    commands.extend((["node", f"frontend/test/{name}"], ROOT) for name in FRONTEND_TESTS)
    commands.extend((["node", f"features/draws/{name}"], ROOT / "backend") for name in ("restricted-write-contract.mjs", "admin-proxy-no-store-contract.mjs"))
    for command, cwd in commands:
        print(f"CHECK {' '.join(command)}", flush=True)
        result = subprocess.run(command, cwd=cwd, env=env, check=False)
        if result.returncode:
            print("Taiwan draw gate checks failed; release is blocked.", flush=True)
            return result.returncode
    print("Taiwan draw gate contracts passed. Deployment and live-window checks are separate.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
