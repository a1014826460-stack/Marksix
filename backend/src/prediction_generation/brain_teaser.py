from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


STATIC_MAPPING_BRAIN_TEST_TABLE = "public.static_mapping_brain_test"
MODE_475_ID = 475


@dataclass(frozen=True)
class BrainTeaserRecord:
    id: int
    question: str
    answer: str
    tips: str
    analysis: str
    mapping_path: str


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def format_brain_teaser_issue_text(term: int) -> str:
    return f"{int(term):03d}期："


def _build_issue_seed(*, year: int, term: int, site_web_id: int) -> int:
    payload = f"{MODE_475_ID}|{year}|{term}|{site_web_id}"
    return int(hashlib.sha256(payload.encode("utf-8")).hexdigest(), 16)


def _row_to_record(row: Any) -> BrainTeaserRecord:
    return BrainTeaserRecord(
        id=int(row["id"]),
        question=_normalize_text(row.get("question")),
        answer=_normalize_text(row.get("answer")),
        tips=_normalize_text(row.get("tips")),
        analysis=_normalize_text(row.get("analysis")),
        mapping_path=_normalize_text(row.get("mapping_path")),
    )


def load_brain_teaser_record_for_issue(
    conn: Any,
    *,
    year: int,
    term: int,
    site_web_id: int,
) -> BrainTeaserRecord:
    count_row = conn.execute(
        f"SELECT COUNT(*) AS total FROM {STATIC_MAPPING_BRAIN_TEST_TABLE}"
    ).fetchone()
    total = int((count_row or {}).get("total") or 0)
    if total <= 0:
        raise ValueError("public.static_mapping_brain_test 中没有可用脑筋急转弯数据")

    offset = _build_issue_seed(year=year, term=term, site_web_id=site_web_id) % total
    row = conn.execute(
        f"""
        SELECT id, question, answer, tips, analysis, mapping_path
        FROM {STATIC_MAPPING_BRAIN_TEST_TABLE}
        ORDER BY id ASC
        OFFSET ? LIMIT 1
        """,
        (offset,),
    ).fetchone()
    if not row:
        raise ValueError("未能从 public.static_mapping_brain_test 读取脑筋急转弯记录")
    return _row_to_record(row)


def load_previous_brain_teaser_record_for_issue(
    conn: Any,
    *,
    year: int,
    term: int,
    site_web_id: int,
) -> BrainTeaserRecord:
    current = load_brain_teaser_record_for_issue(
        conn,
        year=year,
        term=term,
        site_web_id=site_web_id,
    )
    previous_term = int(term) - 1 if int(term) > 1 else 1
    previous = load_brain_teaser_record_for_issue(
        conn,
        year=year,
        term=previous_term,
        site_web_id=site_web_id,
    )
    if previous.id != current.id:
        return previous

    total_row = conn.execute(
        f"SELECT COUNT(*) AS total FROM {STATIC_MAPPING_BRAIN_TEST_TABLE}"
    ).fetchone()
    total = int((total_row or {}).get("total") or 0)
    if total <= 1:
        return previous

    current_offset = _build_issue_seed(year=year, term=term, site_web_id=site_web_id) % total
    fallback_offset = (current_offset - 1) % total
    row = conn.execute(
        f"""
        SELECT id, question, answer, tips, analysis, mapping_path
        FROM {STATIC_MAPPING_BRAIN_TEST_TABLE}
        ORDER BY id ASC
        OFFSET ? LIMIT 1
        """,
        (fallback_offset,),
    ).fetchone()
    if not row:
        return previous
    return _row_to_record(row)


def build_brain_teaser_generated_content(
    conn: Any,
    *,
    year: int,
    term: int,
    site_web_id: int,
) -> dict[str, Any]:
    record = load_brain_teaser_record_for_issue(
        conn,
        year=year,
        term=term,
        site_web_id=site_web_id,
    )
    issue_text = format_brain_teaser_issue_text(int(term))
    return {
        "title": "脑筋急转弯",
        "content": f"{issue_text}{record.question}",
        "answer": record.answer,
        "tips": record.tips,
        "jiexi": record.analysis,
        "source_record_id": str(record.id),
    }
