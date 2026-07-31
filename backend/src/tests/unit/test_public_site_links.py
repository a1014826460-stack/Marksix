"""Public site-links service tests — enabled/domain filtering, current-site exclusion,
id ordering, host deduplication, domain parsing, and field projection."""

from __future__ import annotations

import pytest
from db import connect
from domains.sites import service
from tables import ensure_admin_tables

# Use high IDs to avoid collisions with default sites inserted by
# ensure_admin_tables.
_ID_BASE = 100


def _make_site(
    conn,
    *,
    site_id: int,
    web_id: int,
    name: str,
    domain: str,
    blueprint_name: str,
    enabled: int = 1,
) -> None:
    conn.execute(
        """
        INSERT INTO managed_sites (
            id, web_id, name, domain, lottery_type_id, enabled,
            blueprint_name, announcement, notes, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            site_id,
            web_id,
            name,
            domain,
            3,
            enabled,
            blueprint_name,
            "",
            "",
            "2026-08-01T00:00:00+00:00",
            "2026-08-01T00:00:00+00:00",
        ),
    )


# ── service-level tests ──────────────────────────────────────────────


def test_filters_disabled_sites(tmp_path):
    db_path = tmp_path / "filter_disabled.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="Site A", domain="a.example.com", blueprint_name="a", enabled=1)
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="Site B", domain="b.example.com", blueprint_name="b", enabled=0)
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    # Default sites from ensure_admin_tables also have enabled=1 and domains,
    # so we check that our enabled site is present and the disabled one is not.
    keys = [link["site_key"] for link in result["links"]]
    assert "a" in keys
    assert "b" not in keys


def test_filters_empty_domain(tmp_path):
    db_path = tmp_path / "filter_empty_domain.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="Has Domain", domain="a.example.com", blueprint_name="a")
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="Empty", domain="", blueprint_name="b")
        _make_site(conn, site_id=_ID_BASE + 2, web_id=_ID_BASE + 2, name="Spaces", domain="   ", blueprint_name="c")
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    keys = [link["site_key"] for link in result["links"]]
    assert "a" in keys
    assert "b" not in keys
    assert "c" not in keys


def test_excludes_current_site_by_blueprint_name(tmp_path):
    db_path = tmp_path / "exclude_blueprint.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="Current", domain="current.example.com", blueprint_name="mysite")
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="Other", domain="other.example.com", blueprint_name="other-x")
        conn.commit()

    result = service.get_public_site_links(db_path, "mysite")
    keys = [link["site_key"] for link in result["links"]]
    assert "mysite" not in keys
    assert "other-x" in keys


def test_excludes_current_site_by_domain_match(tmp_path):
    db_path = tmp_path / "exclude_domain.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="Current", domain="shared-uniq.example.com", blueprint_name="mysite")
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="SameDomain", domain="https://shared-uniq.example.com/", blueprint_name="other-y")
        conn.commit()

    result = service.get_public_site_links(db_path, "mysite")
    keys = [link["site_key"] for link in result["links"]]
    assert "other-y" not in keys  # excluded by domain match


def test_orders_by_id_asc(tmp_path):
    db_path = tmp_path / "order_id.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE + 10, web_id=_ID_BASE + 10, name="Third", domain="cid3.example.com", blueprint_name="cid3")
        _make_site(conn, site_id=_ID_BASE + 5, web_id=_ID_BASE + 5, name="First", domain="cid1.example.com", blueprint_name="cid1")
        _make_site(conn, site_id=_ID_BASE + 7, web_id=_ID_BASE + 7, name="Second", domain="cid2.example.com", blueprint_name="cid2")
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    # Filter to only our test sites
    keys = [link["site_key"] for link in result["links"] if link["site_key"] in ("cid1", "cid2", "cid3")]
    assert keys == ["cid1", "cid2", "cid3"]


def test_deduplicates_by_hostname_keeping_first_by_id(tmp_path):
    db_path = tmp_path / "dedup_host.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="First", domain="dup-uniq.example.com", blueprint_name="first-z")
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="Second", domain="https://dup-uniq.example.com/", blueprint_name="second-z")
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    links = [link for link in result["links"] if link["site_key"] in ("first-z", "second-z")]
    assert len(links) == 1
    assert links[0]["site_key"] == "first-z"
    assert links[0]["name"] == "First"


def test_accepts_pure_hostname_input(tmp_path):
    db_path = tmp_path / "pure_hostname.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="Pure", domain="www.pure-host.example.com", blueprint_name="pure-z")
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    links = [link for link in result["links"] if link["site_key"] == "pure-z"]
    assert len(links) == 1
    link = links[0]
    assert link["domain"] == "www.pure-host.example.com"
    assert link["url"] == "https://www.pure-host.example.com/"


def test_accepts_https_url_input_and_normalizes(tmp_path):
    db_path = tmp_path / "https_url.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="HTTPS", domain="https://www.https-url.example.com/", blueprint_name="https-z")
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    links = [link for link in result["links"] if link["site_key"] == "https-z"]
    assert len(links) == 1
    link = links[0]
    assert link["domain"] == "www.https-url.example.com"
    assert link["url"] == "https://www.https-url.example.com/"


def test_rejects_credentials_in_url(tmp_path):
    db_path = tmp_path / "reject_creds.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="Creds", domain="https://user:pass@creds.example.com/", blueprint_name="creds-z")
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="Valid", domain="valid-creds.example.com", blueprint_name="valid-z")
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    keys = [link["site_key"] for link in result["links"]]
    assert "creds-z" not in keys
    assert "valid-z" in keys


def test_rejects_query_string_in_url(tmp_path):
    db_path = tmp_path / "reject_query.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="Query", domain="https://query.example.com/?t=1", blueprint_name="query-z")
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="Valid", domain="valid-query.example.com", blueprint_name="valid-z")
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    keys = [link["site_key"] for link in result["links"]]
    assert "query-z" not in keys
    assert "valid-z" in keys


def test_rejects_fragment_in_url(tmp_path):
    db_path = tmp_path / "reject_frag.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="Frag", domain="https://frag.example.com/#section", blueprint_name="frag-z")
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="Valid", domain="valid-frag.example.com", blueprint_name="valid-z")
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    keys = [link["site_key"] for link in result["links"]]
    assert "frag-z" not in keys
    assert "valid-z" in keys


def test_rejects_non_http_protocol(tmp_path):
    db_path = tmp_path / "reject_proto.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="FTP", domain="ftp://ftp.example.com/", blueprint_name="ftp-z")
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="Valid", domain="valid-proto.example.com", blueprint_name="valid-z")
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    keys = [link["site_key"] for link in result["links"]]
    assert "ftp-z" not in keys
    assert "valid-z" in keys


def test_rejects_illegal_hostname(tmp_path):
    db_path = tmp_path / "reject_illegal.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="Bad", domain="not a valid host!", blueprint_name="bad-z")
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="Valid", domain="valid-illegal.example.com", blueprint_name="valid-z")
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    keys = [link["site_key"] for link in result["links"]]
    assert "bad-z" not in keys
    assert "valid-z" in keys


def test_empty_array_when_no_legal_links(tmp_path):
    db_path = tmp_path / "empty_links.sqlite3"
    ensure_admin_tables(db_path)
    # Default sites have legal domains, so we need to not use default sites.
    # Delete all existing rows first, then insert only illegal ones.
    with connect(db_path) as conn:
        conn.execute("DELETE FROM managed_sites")
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="Disabled", domain="a.example.com", blueprint_name="a-z", enabled=0)
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="EmptyDomain", domain="", blueprint_name="b-z")
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    assert result == {"links": []}


def test_public_response_only_exposes_four_fields(tmp_path):
    db_path = tmp_path / "four_fields.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="Test", domain="four-fields.example.com", blueprint_name="test-z")
        conn.commit()

    result = service.get_public_site_links(db_path, "nonexistent")
    assert len(result) == 1  # only "links" key at top level
    our_links = [link for link in result["links"] if link["site_key"] == "test-z"]
    assert len(our_links) == 1
    link = our_links[0]
    assert set(link.keys()) == {"site_key", "name", "domain", "url"}
    assert link["site_key"] == "test-z"
    assert link["name"] == "Test"
    assert link["domain"] == "four-fields.example.com"
    assert link["url"] == "https://four-fields.example.com/"


def test_current_site_not_in_enabled_set_still_excluded_by_blueprint_match(tmp_path):
    """When the current site is disabled or has empty domain, it should still be
    excluded from results by blueprint_name match (if enabled+domain rows with
    the same blueprint exist). Domain-based exclusion won't apply since the
    current site's domain can't be determined, but blueprint_name exclusion must
    work."""

    db_path = tmp_path / "exclude_disabled_current.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        # Current site: disabled
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="CurrentDisabled", domain="disabled-uniq.example.com", blueprint_name="mysite-disabled", enabled=0)
        # Another site with same blueprint_name but enabled with domain
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="SameBP", domain="samebp.example.com", blueprint_name="mysite-disabled", enabled=1)
        _make_site(conn, site_id=_ID_BASE + 2, web_id=_ID_BASE + 2, name="Other", domain="other-uniq.example.com", blueprint_name="other-z")
        conn.commit()

    result = service.get_public_site_links(db_path, "mysite-disabled")
    keys = [link["site_key"] for link in result["links"]]
    assert "mysite-disabled" not in keys
    assert "other-z" in keys


def test_lowercase_hostname_for_domain_match(tmp_path):
    db_path = tmp_path / "case_insensitive_domain.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _make_site(conn, site_id=_ID_BASE, web_id=_ID_BASE, name="Current", domain="CaseDomain.COM", blueprint_name="mysite-case")
        _make_site(conn, site_id=_ID_BASE + 1, web_id=_ID_BASE + 1, name="Other", domain="https://casedomain.com/", blueprint_name="other-z")
        conn.commit()

    result = service.get_public_site_links(db_path, "mysite-case")
    keys = [link["site_key"] for link in result["links"]]
    assert "other-z" not in keys  # excluded by case-insensitive domain match
