from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from prediction_generation.brain_teaser import (
    format_brain_teaser_issue_text,
    load_brain_teaser_record_for_issue,
    load_previous_brain_teaser_record_for_issue,
)
from prediction_generation.brain_teaser_image import (
    DEFAULT_BACKGROUND_PATH,
    DEFAULT_FONT_PATH,
    DEFAULT_OUTPUT_PATH,
    render_brain_teaser_image,
)


DEFAULT_DB_DSN = os.environ.get("TEST_DATABASE_URL", "").strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a brain teaser image from PostgreSQL data.")
    parser.add_argument("--db-dsn", default=DEFAULT_DB_DSN, help="PostgreSQL DSN.")
    parser.add_argument("--background", type=Path, default=DEFAULT_BACKGROUND_PATH, help="Background image path.")
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT_PATH, help="Unified font path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Output image path.")
    parser.add_argument("--year", type=int, default=2026, help="Issue year.")
    parser.add_argument("--term", type=int, default=1, help="Issue term.")
    parser.add_argument("--web-id", type=int, default=4, help="Business web_id.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.db_dsn:
        raise SystemExit("TEST_DATABASE_URL or --db-dsn must be set before generating an image")
    with psycopg.connect(args.db_dsn, row_factory=dict_row, connect_timeout=10) as conn:
        current_record = load_brain_teaser_record_for_issue(
            conn,
            year=args.year,
            term=args.term,
            site_web_id=args.web_id,
        )
        previous_record = load_previous_brain_teaser_record_for_issue(
            conn,
            year=args.year,
            term=args.term,
            site_web_id=args.web_id,
        )

    output_path = render_brain_teaser_image(
        current_record=current_record,
        previous_record=previous_record,
        current_issue_text=format_brain_teaser_issue_text(args.term),
        previous_issue_text=format_brain_teaser_issue_text(max(1, args.term - 1)),
        background_path=args.background,
        font_path=args.font,
        output_path=args.output,
    )
    print(f"Generated brain teaser image: {output_path}")
    print(f"Current issue record id: {current_record.id}")
    print(f"Previous issue record id: {previous_record.id}")


if __name__ == "__main__":
    main()
