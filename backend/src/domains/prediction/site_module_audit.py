"""Audit and explicit reconciliation for site prediction-module authorization."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from db import utc_now
from domains.sites.repository import find_site_by_id
from .generation_service import get_site_prediction_module_blueprints
from .site_module_blueprints import (
    get_blueprint_name_for_site,
    get_required_mode_ids_for_site,
)
from .site_page_dependencies import (
    blocked_dependencies_for_site,
    required_mode_ids_for_site_key,
)


def _normalize_site_ids(site_ids: Iterable[int] | None) -> list[int]:
    if site_ids is None:
        return [5, 6, 7, 8]
    return sorted({int(site_id) for site_id in site_ids if int(site_id) > 0})


def _load_enabled_mode_ids(conn: Any, site_id: int) -> list[int]:
    rows = conn.execute(
        """
        SELECT DISTINCT mode_id
        FROM site_prediction_modules
        WHERE site_id = ?
          AND status = 1
          AND mode_id IS NOT NULL
        ORDER BY mode_id
        """,
        (int(site_id),),
    ).fetchall()
    return [int(row["mode_id"]) for row in rows]


def _manifest_site_key(site: dict[str, Any] | None) -> str | None:
    """Resolve one of the page-manifest sites from the immutable business ID."""
    try:
        web_id = int((site or {}).get("web_id") or 0)
    except (TypeError, ValueError):
        return None
    return {
        4: "shengshi8800",
        5: "twcaibawang",
        6: "twsaimahui",
        7: "twjinniu",
        8: "twcf888",
    }.get(web_id)


def audit_runtime_module_sets(
    conn: Any,
    *,
    site_ids: Iterable[int] | None = None,
) -> list[dict[str, Any]]:
    """Compare enabled runtime mode IDs with each site's declarative blueprint."""
    reports: list[dict[str, Any]] = []
    for site_id in _normalize_site_ids(site_ids):
        site = find_site_by_id(conn, site_id)
        if not site:
            continue
        blueprint_mode_ids = list(get_required_mode_ids_for_site(site))
        manifest_site_key = _manifest_site_key(site)
        manifest_mode_ids = list(
            required_mode_ids_for_site_key(manifest_site_key)
            if manifest_site_key
            else blueprint_mode_ids
        )
        enabled_mode_ids = _load_enabled_mode_ids(conn, site_id)
        enabled_set = set(enabled_mode_ids)
        blueprint_set = set(blueprint_mode_ids)
        manifest_set = set(manifest_mode_ids)
        blocked_dependency_sources = [
            item.source_path
            for item in blocked_dependencies_for_site(manifest_site_key)
        ] if manifest_site_key else []
        reports.append(
            {
                "site_id": int(site_id),
                "web_id": int(site.get("web_id") or 0),
                "blueprint_name": get_blueprint_name_for_site(site),
                "blueprint_mode_ids": blueprint_mode_ids,
                "manifest_mode_ids": manifest_mode_ids,
                "enabled_mode_ids": enabled_mode_ids,
                "missing_from_runtime": [
                    mode_id for mode_id in blueprint_mode_ids if mode_id not in enabled_set
                ],
                "enabled_outside_blueprint": sorted(enabled_set - blueprint_set),
                "vendor_dependency_mode_ids": [],
                "enabled_outside_authorized_sources": sorted(enabled_set - manifest_set),
                "blocked_dependency_sources": blocked_dependency_sources,
            }
        )
    return reports


def reconcile_site_prediction_modules_to_blueprint(
    conn: Any,
    *,
    site_ids: Iterable[int] | None = None,
) -> list[dict[str, int]]:
    """Enable blueprint modes and disable surplus active rows without deleting history."""
    results: list[dict[str, int]] = []
    now = utc_now()
    for site_id in _normalize_site_ids(site_ids):
        site = find_site_by_id(conn, site_id)
        if not site:
            continue
        manifest_site_key = _manifest_site_key(site)
        # Reconciliation must not preserve an old stored profile when the
        # page manifest has narrowed authorization. Strip joined profile data
        # solely while constructing insertable config rows; the migration is
        # still responsible for persisting the refreshed profile itself.
        blueprint_site = dict(site)
        if manifest_site_key:
            for key in (
                "blueprint_required_mode_ids_json",
                "blueprint_known_unavailable_mode_ids_json",
                "blueprint_blocked_items_json",
                "_blueprint_profile",
            ):
                blueprint_site.pop(key, None)
        blueprint_rows = get_site_prediction_module_blueprints(blueprint_site, conn=conn)
        # Authorization follows the declarative blueprint even when a legacy
        # mode has no currently registered generator configuration. Vendor
        # composites must return their existing empty history when a source is
        # disabled; they do not widen the site's enabled module set.
        blueprint_mode_ids = {
            int(mode_id)
            for mode_id in (
                required_mode_ids_for_site_key(manifest_site_key)
                if manifest_site_key
                else get_required_mode_ids_for_site(site)
            )
        }
        existing_rows = conn.execute(
            """
            SELECT id, mode_id, status
            FROM site_prediction_modules
            WHERE site_id = ?
            ORDER BY id
            """,
            (int(site_id),),
        ).fetchall()
        existing_mode_ids = {int(row["mode_id"]) for row in existing_rows if row["mode_id"] is not None}

        enabled = 0
        for row in existing_rows:
            mode_id = row["mode_id"]
            if mode_id is None or int(mode_id) not in blueprint_mode_ids or int(row["status"] or 0) == 1:
                continue
            conn.execute(
                "UPDATE site_prediction_modules SET status = 1, updated_at = ? WHERE id = ?",
                (now, int(row["id"])),
            )
            enabled += 1

        inserted = 0
        for item in blueprint_rows:
            mode_id = int(item["mode_id"])
            if mode_id in existing_mode_ids:
                continue
            conn.execute(
                """
                INSERT INTO site_prediction_modules (
                    site_id, mechanism_key, mode_id, status, sort_order, created_at, updated_at, title
                )
                VALUES (?, ?, ?, 1, ?, ?, ?, ?)
                ON CONFLICT(site_id, mechanism_key) DO UPDATE SET
                    mode_id = excluded.mode_id,
                    status = 1,
                    updated_at = excluded.updated_at
                """,
                (
                    int(site_id),
                    str(item["key"]),
                    mode_id,
                    int(item["sort_order"]),
                    now,
                    now,
                    str(item.get("title") or ""),
                ),
            )
            inserted += 1

        disabled = 0
        for row in existing_rows:
            mode_id = row["mode_id"]
            if mode_id is None or int(mode_id) in blueprint_mode_ids or int(row["status"] or 0) != 1:
                continue
            conn.execute(
                "UPDATE site_prediction_modules SET status = 0, updated_at = ? WHERE id = ?",
                (now, int(row["id"])),
            )
            disabled += 1

        results.append(
            {
                "site_id": int(site_id),
                "enabled": enabled,
                "disabled": disabled,
                "inserted": inserted,
            }
        )
    return results


def parse_twcf888_document_mode_ids(document_path: str | Path) -> set[int]:
    """Read the two declared live-ID lists and require them to agree."""
    text = Path(document_path).read_text(encoding="utf-8")
    blocks = re.findall(r"```text\s*(.*?)\s*```", text, flags=re.DOTALL)
    if len(blocks) < 2:
        raise ValueError("twcf888 module document must contain two live mode-id lists")
    parsed = [{int(value) for value in re.findall(r"\d+", block)} for block in blocks[:2]]
    if parsed[0] != parsed[1]:
        raise ValueError("twcf888 module document contains inconsistent live mode-id lists")
    return parsed[0]


def parse_twsaimahui_document_mode_ids(document_path: str | Path) -> set[int]:
    """Read the two auditable Twsaimahui mode-ID blocks and require agreement."""
    text = Path(document_path).read_text(encoding="utf-8")
    blocks = re.findall(r"```text\s*(.*?)\s*```", text, flags=re.DOTALL)
    if len(blocks) < 2:
        raise ValueError("twsaimahui module document must contain two live mode-id lists")
    parsed = [{int(value) for value in re.findall(r"\d+", block)} for block in blocks[:2]]
    if parsed[0] != parsed[1]:
        raise ValueError("twsaimahui module document contains inconsistent live mode-id lists")
    return parsed[0]


def parse_shengshi8800_document_mode_ids(document_path: str | Path) -> set[int]:
    """Read the two auditable Shengshi8800 mode-ID blocks and require agreement."""
    text = Path(document_path).read_text(encoding="utf-8")
    blocks = re.findall(r"```text\s*(.*?)\s*```", text, flags=re.DOTALL)
    if len(blocks) < 2:
        raise ValueError("shengshi8800 module document must contain two live mode-id lists")
    parsed = [{int(value) for value in re.findall(r"\d+", block)} for block in blocks[:2]]
    if parsed[0] != parsed[1]:
        raise ValueError("shengshi8800 module document contains inconsistent live mode-id lists")
    return parsed[0]


def parse_twjinniu_homepage_mode_ids(source_path: str | Path) -> set[int]:
    """Extract fixed legacy source modes from the static homepage loader."""
    text = Path(source_path).read_text(encoding="utf-8")
    return {
        int(mode_id)
        for mode_id in re.findall(r"loadLegacyModeRows\((\d+)", text)
    }


def audit_frontend_fixed_mode_dependencies(
    *,
    twjinniu_source_path: str | Path,
    twcaibawang_source_mode_ids: dict[str, tuple[int, ...]],
) -> dict[str, Any]:
    """Report fixed frontend dependencies without conflating composites with site modules."""
    twjinniu_mode_ids = parse_twjinniu_homepage_mode_ids(twjinniu_source_path)
    twcaibawang_mode_ids = sorted(
        {
            mode_id
            for mode_ids in twcaibawang_source_mode_ids.values()
            for mode_id in mode_ids
        }
    )
    return {
        "twjinniu": {
            "fixed_mode_ids": sorted(twjinniu_mode_ids),
            "missing_from_blueprint": sorted(
                twjinniu_mode_ids - set(required_mode_ids_for_site_key("twjinniu"))
            ),
        },
        "twcaibawang": {
            "composite_source_mode_ids": twcaibawang_mode_ids,
            "authorization": "runtime_site_prediction_modules",
        },
    }
