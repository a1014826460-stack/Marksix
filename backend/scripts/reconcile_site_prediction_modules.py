from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db import connect  # noqa: E402
from tables import ensure_admin_tables  # noqa: E402
from domains.prediction.site_module_audit import (  # noqa: E402
    audit_frontend_fixed_mode_dependencies,
    parse_shengshi8800_document_mode_ids,
    audit_runtime_module_sets,
    parse_twcf888_document_mode_ids,
    reconcile_site_prediction_modules_to_blueprint,
)
from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key  # noqa: E402
from vendor.homepage_modules import get_vendor_module_source_mode_ids  # noqa: E402


def _parse_site_ids(value: str) -> list[int]:
    site_ids: list[int] = []
    for item in str(value or "").split(","):
        item = item.strip()
        if not item:
            continue
        parsed = int(item)
        if parsed <= 0:
            raise ValueError("site IDs must be positive integers")
        site_ids.append(parsed)
    return sorted(set(site_ids)) or [4, 5, 6, 7, 8, 9, 10]


def _project_root() -> Path:
    return ROOT.parent


def _run_audit(conn, site_ids: list[int]) -> dict:
    project_root = _project_root()
    twcf888_document = (
        project_root
        / "frontend"
        / "public"
        / "vendor"
        / "twcf888.com"
        / "TWCF888_PREDICTION_MODULES.md"
    )
    shengshi8800_document = (
        project_root
        / "frontend"
        / "public"
        / "vendor"
        / "shengshi8800"
        / "SHENGSHI8800_PREDICTION_MODULES.md"
    )
    twjinniu_source = project_root / "frontend" / "lib" / "twjinniu-homepage.ts"
    return {
        "runtime": audit_runtime_module_sets(conn, site_ids=site_ids),
        "twcf888_document_mode_ids": sorted(parse_twcf888_document_mode_ids(twcf888_document)),
        "twcf888_document_matches_blueprint": (
            parse_twcf888_document_mode_ids(twcf888_document)
            == set(required_mode_ids_for_site_key("twcf888"))
        ),
        "shengshi8800_document_mode_ids": sorted(
            parse_shengshi8800_document_mode_ids(shengshi8800_document)
        ),
        "shengshi8800_document_matches_blueprint": (
            parse_shengshi8800_document_mode_ids(shengshi8800_document)
            == set(required_mode_ids_for_site_key("shengshi8800"))
        ),
        "frontend_fixed_dependencies": audit_frontend_fixed_mode_dependencies(
            twjinniu_source_path=twjinniu_source,
            twcaibawang_source_mode_ids=get_vendor_module_source_mode_ids(),
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit or reconcile dedicated site prediction-module authorization."
    )
    parser.add_argument("--db-path", required=True, help="PostgreSQL DSN or explicit SQLite test path")
    parser.add_argument("--site-ids", default="4,5,6,7,8,9,10", help="Comma-separated managed_sites IDs")
    parser.add_argument("--apply", action="store_true", help="Enable blueprint rows and disable surplus active rows")
    args = parser.parse_args()
    site_ids = _parse_site_ids(args.site_ids)

    ensure_admin_tables(args.db_path)
    with connect(args.db_path) as conn:
        before = _run_audit(conn, site_ids)
        result = {
            "mode": "apply" if args.apply else "audit",
            "site_ids": site_ids,
            "before": before,
        }
        if args.apply:
            result["changes"] = reconcile_site_prediction_modules_to_blueprint(
                conn,
                site_ids=site_ids,
            )
            result["after"] = _run_audit(conn, site_ids)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
