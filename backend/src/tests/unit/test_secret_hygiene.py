from __future__ import annotations

import re
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SENSITIVE_SOURCE_FILES = (
    "backend/scripts/restart-backend.ps1",
    "ops/frp-target-b/frpc.toml",
    "ops/frp-target-b/install-frpc-target-b.ps1",
    "backend/src/deprecated/tools/generate_missing_types.py",
    "backend/src/deprecated/tools/repair_created_mode_payload_197.py",
    "backend/src/tests/brain_teaser_image_generator.py",
)
_POSTGRES_DSN_WITH_PASSWORD = re.compile(r"postgres(?:ql)?://[^:\s]+:[^@\s]+@", re.IGNORECASE)
_FRP_TOKEN_ASSIGNMENT = re.compile(r"^\s*auth\.token\s*=\s*[\"'][0-9a-f]{24,}[\"']", re.IGNORECASE | re.MULTILINE)


def test_sensitive_operational_files_do_not_embed_credentials():
    findings: list[str] = []
    for relative_path in _SENSITIVE_SOURCE_FILES:
        content = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        if _POSTGRES_DSN_WITH_PASSWORD.search(content):
            findings.append(f"{relative_path}: PostgreSQL password embedded in DSN")
        if _FRP_TOKEN_ASSIGNMENT.search(content):
            findings.append(f"{relative_path}: FRP token embedded in config")

    assert not findings, "\n".join(findings)
