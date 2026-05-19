from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db import connect  # noqa: E402
from domains.prediction.generation_service import get_site_prediction_module_blueprints  # noqa: E402
from domains.prediction.site_module_blueprints import (  # noqa: E402
    get_blocked_items_for_site,
    get_blueprint_name_for_site,
)
from predict.mechanisms import ensure_prediction_configs_loaded  # noqa: E402


def _load_site(conn, site_id: int) -> dict:
    columns = set(conn.table_columns("managed_sites"))
    select_fields = ["id", "name", "domain", "lottery_type_id", "start_web_id", "end_web_id"]
    if "web_id" in columns:
        select_fields.insert(4, "web_id")
    else:
        select_fields.append("start_web_id AS web_id")
    row = conn.execute(
        f"""
        SELECT {", ".join(select_fields)}
        FROM managed_sites
        WHERE id = ?
        """,
        (site_id,),
    ).fetchone()
    if not row:
        raise SystemExit(f"site_id={site_id} not found")
    return dict(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the resolved prediction-module blueprint for one site.")
    parser.add_argument("--db-path", required=True, help="PostgreSQL DSN or explicit SQLite path")
    parser.add_argument("--site-id", type=int, required=True, help="managed_sites.id")
    args = parser.parse_args()

    ensure_prediction_configs_loaded(args.db_path)

    with connect(args.db_path) as conn:
        site = _load_site(conn, args.site_id)
        blueprints = get_site_prediction_module_blueprints(site)
        blocked = get_blocked_items_for_site(site)

    print(f"site_id: {site['id']}")
    print(f"name: {site.get('name') or ''}")
    print(f"domain: {site.get('domain') or ''}")
    print(f"web_id: {site.get('web_id') or site.get('start_web_id') or ''}")
    print(f"lottery_type_id: {site.get('lottery_type_id') or ''}")
    print(f"blueprint: {get_blueprint_name_for_site(site)}")
    print()
    print("enabled_modules:")
    for item in blueprints:
        print(
            f"- mode_id={int(item['mode_id'])}"
            f" mechanism_key={item['key']}"
            f" title={item.get('title') or ''}"
            f" sort_order={int(item['sort_order'])}"
        )

    print()
    print("blocked_frontend_items:")
    if not blocked:
        print("- none")
    else:
        for item in blocked:
            print(
                f"- page_title={item.get('page_title') or ''}"
                f" endpoint={item.get('endpoint') or ''}"
                f" status={item.get('status') or ''}"
                f" reason={item.get('reason') or ''}"
            )


if __name__ == "__main__":
    main()
