from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db import connect, quote_identifier, utc_now  # noqa: E402
from domains.prediction.generation_service import sync_site_prediction_modules  # noqa: E402
from helpers import load_fixed_data_maps  # noqa: E402
from predict.common import predict  # noqa: E402
from predict.mechanisms import ensure_prediction_configs_loaded, get_prediction_config  # noqa: E402
from tables import ensure_admin_tables  # noqa: E402


MODULES: tuple[dict[str, Any], ...] = (
    {"mode_id": 470, "mechanism_key": "pt3xiao", "title": "平特3肖"},
    {"mode_id": 471, "mechanism_key": "liangtouzxt", "title": "两头中特"},
    {"mode_id": 472, "mechanism_key": "juesha1xiao", "title": "绝杀1肖"},
    {"mode_id": 473, "mechanism_key": "juesha2xiao", "title": "绝杀2肖"},
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap twsaimahui site-specific public mode_payload history for "
            "new prediction modules. This is a manual ops script and does not "
            "change the core scheduler/generation pipeline."
        )
    )
    parser.add_argument("--db-path", required=True, help="PostgreSQL DSN or explicit SQLite path")
    parser.add_argument("--site-id", type=int, default=6, help="managed_sites.id to sync after bootstrap")
    parser.add_argument("--lottery-type", type=int, default=3, help="lottery_draws.lottery_type_id")
    parser.add_argument("--web-id", type=int, default=6, help="public mode_payload target web_id")
    parser.add_argument("--start-year", type=int, default=None, help="optional lower year bound")
    parser.add_argument("--start-term", type=int, default=None, help="optional lower term bound within start-year")
    parser.add_argument(
        "--modules",
        default="pt3xiao,liangtouzxt,juesha1xiao,juesha2xiao",
        help="comma-separated mechanism keys to process",
    )
    parser.add_argument("--replace-existing", action="store_true", help="overwrite existing public rows")
    parser.add_argument("--dry-run", action="store_true", help="preview without writing")
    return parser.parse_args()


def load_opened_draws(
    conn: Any,
    *,
    lottery_type: int,
    start_year: int | None,
    start_term: int | None,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT year, term, numbers
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND is_opened = 1
        ORDER BY year ASC, term ASC, id ASC
        """,
        (int(lottery_type),),
    ).fetchall()

    draws: list[dict[str, Any]] = []
    for row in rows:
        year = int(row["year"] or 0)
        term = int(row["term"] or 0)
        if start_year is not None:
            if year < int(start_year):
                continue
            if year == int(start_year) and start_term is not None and term < int(start_term):
                continue

        numbers = []
        for raw_value in str(row["numbers"] or "").split(","):
            raw_value = raw_value.strip()
            if not raw_value:
                continue
            try:
                numbers.append(f"{int(raw_value):02d}")
            except (TypeError, ValueError):
                continue
        if len(numbers) < 7:
            continue

        draws.append(
            {
                "year": year,
                "term": term,
                "numbers_str": ",".join(numbers),
            }
        )
    return draws


def compute_result_fields(numbers_str: str, zodiac_map: dict[str, str], color_map: dict[str, str]) -> tuple[str, str]:
    zodiacs: list[str] = []
    colors: list[str] = []
    for raw_value in str(numbers_str or "").split(","):
        code = raw_value.strip()
        if not code:
            continue
        zodiacs.append(str(zodiac_map.get(code) or ""))
        colors.append(str(color_map.get(code) or ""))
    return ",".join(zodiacs), ",".join(colors)


def build_public_row(
    *,
    mode_id: int,
    web_id: int,
    lottery_type: int,
    draw: dict[str, Any],
    generated_content: Any,
    zodiac_map: dict[str, str],
    color_map: dict[str, str],
) -> dict[str, Any]:
    res_sx, res_color = compute_result_fields(draw["numbers_str"], zodiac_map, color_map)
    return {
        "web": str(web_id),
        "type": str(lottery_type),
        "year": str(draw["year"]),
        "term": str(draw["term"]),
        "res_code": str(draw["numbers_str"]),
        "res_sx": res_sx,
        "res_color": res_color,
        "status": 1,
        "content": generated_content if isinstance(generated_content, str) else __import__("json").dumps(generated_content, ensure_ascii=False),
        "web_id": int(web_id),
        "modes_id": int(mode_id),
        "source_record_id": f"-{mode_id}{draw['year']}{draw['term']:03d}",
        "fetched_at": utc_now(),
    }


def find_existing_public_row(conn: Any, table_name: str, row_data: dict[str, Any]) -> dict[str, Any] | None:
    row = conn.execute(
        f"""
        SELECT id
        FROM {quote_identifier(table_name)}
        WHERE type = ?
          AND year = ?
          AND term = ?
          AND (
            (web_id IS NOT NULL AND CAST(web_id AS TEXT) = ?)
            OR (web IS NOT NULL AND CAST(web AS TEXT) = ?)
          )
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            str(row_data["type"]),
            str(row_data["year"]),
            str(row_data["term"]),
            str(row_data["web_id"]),
            str(row_data["web"]),
        ),
    ).fetchone()
    return dict(row) if row else None


def upsert_public_row(
    conn: Any,
    table_name: str,
    row_data: dict[str, Any],
    *,
    replace_existing: bool,
) -> str:
    existing = find_existing_public_row(conn, table_name, row_data)
    columns = set(conn.table_columns(table_name))
    filtered = {key: value for key, value in row_data.items() if key in columns and key != "id"}

    if existing:
        if not replace_existing:
            return "skipped_existing"
        assignments = ", ".join(f"{quote_identifier(key)} = ?" for key in filtered)
        conn.execute(
            f"""
            UPDATE {quote_identifier(table_name)}
            SET {assignments}
            WHERE id = ?
            """,
            [filtered[key] for key in filtered] + [existing["id"]],
        )
        return "updated"

    insert_columns = list(filtered.keys())
    placeholders = ", ".join(["?"] * len(insert_columns))
    conn.execute(
        f"""
        INSERT INTO {quote_identifier(table_name)} (
            {", ".join(quote_identifier(key) for key in insert_columns)}
        )
        VALUES ({placeholders})
        """,
        [filtered[key] for key in insert_columns],
    )
    return "inserted"


def update_record_count(conn: Any, mode_id: int, table_name: str) -> None:
    row = conn.execute(
        f"SELECT COUNT(*) AS total FROM {quote_identifier(table_name)}"
    ).fetchone()
    total = int(row["total"] or 0) if row else 0
    conn.execute(
        """
        UPDATE mode_payload_tables
        SET record_count = ?
        WHERE modes_id = ?
        """,
        (total, int(mode_id)),
    )


def main() -> None:
    args = parse_args()
    requested_keys = {item.strip() for item in str(args.modules or "").split(",") if item.strip()}

    ensure_prediction_configs_loaded(args.db_path)
    ensure_admin_tables(args.db_path)

    with connect(args.db_path) as conn:
        zodiac_map, color_map = load_fixed_data_maps(conn)
        draws = load_opened_draws(
            conn,
            lottery_type=int(args.lottery_type),
            start_year=args.start_year,
            start_term=args.start_term,
        )
        if not draws:
            raise SystemExit("No opened draws found for the requested range.")

        summary: list[dict[str, Any]] = []
        for module in MODULES:
            mechanism_key = str(module["mechanism_key"])
            if requested_keys and mechanism_key not in requested_keys:
                continue

            config = get_prediction_config(mechanism_key)
            table_name = str(config.default_table)
            inserted = 0
            updated = 0
            skipped = 0

            for draw in draws:
                result = predict(
                    config=config,
                    res_code=draw["numbers_str"],
                    source_table=table_name,
                    db_path=args.db_path,
                )
                row_data = build_public_row(
                    mode_id=int(config.default_modes_id),
                    web_id=int(args.web_id),
                    lottery_type=int(args.lottery_type),
                    draw=draw,
                    generated_content=result["prediction"]["content"],
                    zodiac_map=zodiac_map,
                    color_map=color_map,
                )

                action = "dry_run"
                if not args.dry_run:
                    action = upsert_public_row(
                        conn,
                        table_name,
                        row_data,
                        replace_existing=bool(args.replace_existing),
                    )
                if action == "inserted":
                    inserted += 1
                elif action == "updated":
                    updated += 1
                else:
                    skipped += 1

            if not args.dry_run:
                update_record_count(conn, int(config.default_modes_id), table_name)
                conn.commit()

            summary.append(
                {
                    "mechanism_key": mechanism_key,
                    "table_name": table_name,
                    "inserted": inserted,
                    "updated": updated,
                    "skipped": skipped,
                }
            )

        if not args.dry_run and args.site_id > 0 and conn.table_exists("managed_sites"):
            sync_site_prediction_modules(conn, site_id=int(args.site_id))
            conn.commit()

    print("bootstrap_twsaimahui_prediction_history:")
    for item in summary:
        print(
            f"- {item['mechanism_key']} -> {item['table_name']}: "
            f"inserted={item['inserted']} updated={item['updated']} skipped={item['skipped']}"
        )


if __name__ == "__main__":
    main()
