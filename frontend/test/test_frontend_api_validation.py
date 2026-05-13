"""
Frontend API validation script.

Usage:
  1. Start the frontend app, for example:
       npm run dev
  2. Run with pytest:
       pytest frontend/test/test_frontend_api_validation.py -q
  3. Or run directly:
       python frontend/test/test_frontend_api_validation.py
       python frontend/test/test_frontend_api_validation.py --base-url http://127.0.0.1:3000

Environment variables:
  FRONTEND_API_TEST_BASE_URL   default: http://127.0.0.1:3000
  FRONTEND_API_TEST_TIMEOUT    default: 5
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin

import pytest
import requests


FRONTEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = FRONTEND_ROOT.parent
TEST_ROOT = FRONTEND_ROOT / "test"
APP_ROOT = FRONTEND_ROOT / "app"
UPLOADS_SOURCE_DIR = PROJECT_ROOT / "backend" / "data" / "Images"

REQUEST_TIMEOUT_SECONDS = float(os.getenv("FRONTEND_API_TEST_TIMEOUT", "5"))
RESPONSE_TIME_THRESHOLD_SECONDS = 5.0
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULTS_FILE = TEST_ROOT / f"test_results_{TIMESTAMP}.json"

DISCOVERED_ROUTE_FILES = sorted(
    [
        path.relative_to(FRONTEND_ROOT).as_posix()
        for path in APP_ROOT.rglob("route.ts")
        if "/api/" in path.as_posix().replace("\\", "/")
        or "/uploads/" in path.as_posix().replace("\\", "/")
    ]
)


def get_base_url() -> str:
    return os.getenv("FRONTEND_API_TEST_BASE_URL", "http://127.0.0.1:3000").rstrip("/")


def route_file_to_pattern(route_file: str) -> str:
    parts = Path(route_file).parts[1:-1]
    normalized: list[str] = []
    for part in parts:
        if part.startswith("[[...") and part.endswith("]]"):
            normalized.append("{" + part[5:-2] + "}")
        elif part.startswith("[") and part.endswith("]"):
            normalized.append("{" + part[1:-1] + "}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized)


def require_dict(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise AssertionError(f"expected JSON object, got {type(payload).__name__}")
    return payload


def require_list(payload: Any, field_name: str) -> list[Any]:
    if not isinstance(payload, list):
        raise AssertionError(f"expected '{field_name}' to be a list, got {type(payload).__name__}")
    return payload


def require_key(payload: dict[str, Any], key: str, expected_type: type | tuple[type, ...]) -> Any:
    if key not in payload:
        raise AssertionError(f"missing key '{key}'")
    value = payload[key]
    if not isinstance(value, expected_type):
        if isinstance(expected_type, tuple):
            expected_name = ", ".join(t.__name__ for t in expected_type)
        else:
            expected_name = expected_type.__name__
        raise AssertionError(
            f"key '{key}' expected {expected_name}, got {type(value).__name__}"
        )
    return value


def validate_lottery_data(case: "ApiCase", response: requests.Response) -> None:
    payload = require_dict(response.json())
    site = require_key(payload, "site", dict)
    draw = require_key(payload, "draw", dict)
    require_key(site, "id", int)
    require_key(site, "name", str)
    require_key(draw, "current_issue", str)
    require_key(draw, "result_balls", list)
    require_key(payload, "modules", list)


def validate_latest_draw(case: "ApiCase", response: requests.Response) -> None:
    payload = require_dict(response.json())
    require_key(payload, "current_issue", str)
    require_key(payload, "result_balls", list)


def validate_next_draw_deadline(case: "ApiCase", response: requests.Response) -> None:
    payload = require_dict(response.json())
    if "next_time" not in payload:
        raise AssertionError("missing key 'next_time'")
    if not isinstance(payload["next_time"], (int, float, str)):
        raise AssertionError("key 'next_time' must be int, float, or string")


def validate_draw_history(case: "ApiCase", response: requests.Response) -> None:
    payload = require_dict(response.json())
    require_key(payload, "lottery_type", int)
    require_key(payload, "items", list)
    require_key(payload, "page", int)
    require_key(payload, "page_size", int)
    require_key(payload, "total", int)
    require_key(payload, "total_pages", int)


def validate_post_get_list(case: "ApiCase", response: requests.Response) -> None:
    payload = require_dict(response.json())
    data = require_key(payload, "data", list)
    if data:
        first = require_dict(data[0])
        require_key(first, "file_name", str)


def validate_predict(case: "ApiCase", response: requests.Response) -> None:
    payload = require_dict(response.json())
    if payload.get("ok") is not True:
        raise AssertionError("expected payload.ok to be true")
    data = require_key(payload, "data", dict)
    require_key(data, "mechanism", dict)
    require_key(data, "prediction", dict)


def validate_kaijiang_cur_term(case: "ApiCase", response: requests.Response) -> None:
    payload = require_dict(response.json())
    inner = payload.get("data", payload)
    inner = require_dict(inner)
    if "term" not in inner:
        raise AssertionError("missing key 'term'")
    if not isinstance(inner["term"], (str, int, float)):
        raise AssertionError("key 'term' must be string or number")
    require_key(inner, "issue", str)


def validate_kaijiang_rows(case: "ApiCase", response: requests.Response) -> None:
    payload = require_dict(response.json())
    data = require_key(payload, "data", list)
    require_list(data, "data")


def validate_upload_image(case: "ApiCase", response: requests.Response) -> None:
    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        raise AssertionError(f"expected image content-type, got '{content_type}'")
    if not response.content:
        raise AssertionError("empty image body")


def validate_json_object(case: "ApiCase", response: requests.Response) -> None:
    require_dict(response.json())


VALIDATORS: dict[str, Callable[["ApiCase", requests.Response], None]] = {
    "lottery_data": validate_lottery_data,
    "latest_draw": validate_latest_draw,
    "next_draw_deadline": validate_next_draw_deadline,
    "draw_history": validate_draw_history,
    "post_get_list": validate_post_get_list,
    "predict": validate_predict,
    "kaijiang_cur_term": validate_kaijiang_cur_term,
    "kaijiang_rows": validate_kaijiang_rows,
    "upload_image": validate_upload_image,
    "json_object": validate_json_object,
}


@dataclass(frozen=True)
class ApiCase:
    case_id: str
    interface_name: str
    route_file: str
    route_pattern: str
    method: str
    path: str
    query_params: dict[str, Any] = field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    success_status_codes: tuple[int, ...] = (200,)
    validator: str = "json_object"
    timeout_seconds: float = REQUEST_TIMEOUT_SECONDS


def build_url(path: str) -> str:
    return urljoin(get_base_url() + "/", path.lstrip("/"))


def build_lottery_data_cases(route_file: str) -> list[ApiCase]:
    pattern = route_file_to_pattern(route_file)
    return [
        ApiCase(
            case_id="lottery-data-default",
            interface_name="/api/lottery-data",
            route_file=route_file,
            route_pattern=pattern,
            method="GET",
            path="/api/lottery-data",
            validator="lottery_data",
        ),
        ApiCase(
            case_id="lottery-data-site-and-history",
            interface_name="/api/lottery-data",
            route_file=route_file,
            route_pattern=pattern,
            method="GET",
            path="/api/lottery-data",
            query_params={"site_id": 1, "history_limit": 5},
            validator="lottery_data",
        ),
    ]


def build_latest_draw_cases(route_file: str) -> list[ApiCase]:
    pattern = route_file_to_pattern(route_file)
    cases = [
        ApiCase(
            case_id="latest-draw-default",
            interface_name="/api/latest-draw",
            route_file=route_file,
            route_pattern=pattern,
            method="GET",
            path="/api/latest-draw",
            validator="latest_draw",
        )
    ]
    for lottery_type in (1, 2, 3):
        cases.append(
            ApiCase(
                case_id=f"latest-draw-type-{lottery_type}",
                interface_name="/api/latest-draw",
                route_file=route_file,
                route_pattern=pattern,
                method="GET",
                path="/api/latest-draw",
                query_params={"lottery_type": lottery_type},
                validator="latest_draw",
            )
        )
    return cases


def build_next_draw_deadline_cases(route_file: str) -> list[ApiCase]:
    pattern = route_file_to_pattern(route_file)
    cases: list[ApiCase] = []
    for lottery_type in (1, 2, 3):
        cases.append(
            ApiCase(
                case_id=f"next-draw-deadline-type-{lottery_type}",
                interface_name="/api/next-draw-deadline",
                route_file=route_file,
                route_pattern=pattern,
                method="GET",
                path="/api/next-draw-deadline",
                query_params={"lottery_type": lottery_type},
                validator="next_draw_deadline",
            )
        )
    return cases


def build_draw_history_cases(route_file: str) -> list[ApiCase]:
    pattern = route_file_to_pattern(route_file)
    return [
        ApiCase(
            case_id="draw-history-default",
            interface_name="/api/draw-history",
            route_file=route_file,
            route_pattern=pattern,
            method="GET",
            path="/api/draw-history",
            validator="draw_history",
        ),
        ApiCase(
            case_id="draw-history-type-year-sort",
            interface_name="/api/draw-history",
            route_file=route_file,
            route_pattern=pattern,
            method="GET",
            path="/api/draw-history",
            query_params={"lottery_type": 3, "year": 2026, "sort": "d"},
            validator="draw_history",
        ),
        ApiCase(
            case_id="draw-history-type-alias-limit",
            interface_name="/api/draw-history",
            route_file=route_file,
            route_pattern=pattern,
            method="GET",
            path="/api/draw-history",
            query_params={"type": 2, "page": 1, "limit": 10},
            validator="draw_history",
        ),
        ApiCase(
            case_id="draw-history-page-size",
            interface_name="/api/draw-history",
            route_file=route_file,
            route_pattern=pattern,
            method="GET",
            path="/api/draw-history",
            query_params={"lottery_type": 1, "page": 1, "page_size": 5, "sort": "l"},
            validator="draw_history",
        ),
    ]


def build_post_get_list_cases(route_file: str) -> list[ApiCase]:
    pattern = route_file_to_pattern(route_file)
    cases = [
        ApiCase(
            case_id="post-get-list-default",
            interface_name="/api/post/getList",
            route_file=route_file,
            route_pattern=pattern,
            method="GET",
            path="/api/post/getList",
            validator="post_get_list",
        )
    ]
    for lottery_type in (1, 2, 3):
        cases.append(
            ApiCase(
                case_id=f"post-get-list-type-{lottery_type}",
                interface_name="/api/post/getList",
                route_file=route_file,
                route_pattern=pattern,
                method="GET",
                path="/api/post/getList",
                query_params={"type": lottery_type, "web": 4, "pc": 1},
                validator="post_get_list",
            )
        )
    return cases


def build_predict_cases(route_file: str) -> list[ApiCase]:
    pattern = route_file_to_pattern(route_file)
    mechanism = "pt2xiao"
    return [
        ApiCase(
            case_id="predict-get-pt2xiao",
            interface_name="/api/predict/[mechanism]",
            route_file=route_file,
            route_pattern=pattern,
            method="GET",
            path=f"/api/predict/{mechanism}",
            query_params={
                "res_code": "01,02,03,04,05,06,07",
                "source_table": "mode_payload_43",
                "target_hit_rate": 0.8,
                "lottery_type": 3,
                "year": "2026",
                "term": "127",
                "web": "4",
            },
            validator="predict",
        ),
        ApiCase(
            case_id="predict-post-pt2xiao",
            interface_name="/api/predict/[mechanism]",
            route_file=route_file,
            route_pattern=pattern,
            method="POST",
            path=f"/api/predict/{mechanism}",
            json_body={
                "res_code": "01,02,03,04,05,06,07",
                "content": "虎羊",
                "source_table": "mode_payload_43",
                "target_hit_rate": 0.8,
                "lottery_type": 3,
                "year": "2026",
                "term": "127",
                "web": "4",
            },
            validator="predict",
        ),
    ]


def build_legacy_kaijiang_cases(route_file: str) -> list[ApiCase]:
    pattern = route_file_to_pattern(route_file)
    endpoint_specs = [
        ("curTerm", {}, "kaijiang_cur_term"),
        ("getPingte", {}, "kaijiang_rows"),
        ("getSanqiXiao4new", {}, "kaijiang_rows"),
        ("sbzt", {}, "kaijiang_rows"),
        ("getXiaoma", {"num": 7}, "kaijiang_rows"),
        ("getHbnx", {}, "kaijiang_rows"),
        ("getYjzy", {}, "kaijiang_rows"),
        ("lxzt", {}, "kaijiang_rows"),
        ("getHllx", {}, "kaijiang_rows"),
        ("getDxzt", {}, "kaijiang_rows"),
        ("getDxztt1", {}, "kaijiang_rows"),
        ("getJyzt", {"num": 2}, "kaijiang_rows"),
        ("ptyw", {}, "kaijiang_rows"),
        ("getXmx1", {}, "kaijiang_rows"),
        ("getTou", {}, "kaijiang_rows"),
        ("getXingte", {}, "kaijiang_rows"),
        ("sxbm", {}, "kaijiang_rows"),
        ("danshuang", {}, "kaijiang_rows"),
        ("dssx", {}, "kaijiang_rows"),
        ("getCodeDuan", {}, "kaijiang_rows"),
        ("getJuzi", {}, "kaijiang_rows"),
        ("getJuzi", {"num": "yqmtm"}, "kaijiang_rows"),
        ("getShaXiao", {}, "kaijiang_rows"),
        ("getCode", {"num": 24}, "kaijiang_rows"),
        ("qqsh", {}, "kaijiang_rows"),
        ("getShaBanbo", {"num": 1}, "kaijiang_rows"),
        ("getShaWei", {"num": 1}, "kaijiang_rows"),
        ("getSzxj", {}, "kaijiang_rows"),
        ("getDjym", {}, "kaijiang_rows"),
        ("getSjsx", {}, "kaijiang_rows"),
        ("getRccx", {"num": 2}, "kaijiang_rows"),
        ("yyptj", {}, "kaijiang_rows"),
        ("wxzt", {}, "kaijiang_rows"),
        ("getWei", {"num": 6}, "kaijiang_rows"),
        ("jxzt", {}, "kaijiang_rows"),
        ("qxbm", {}, "kaijiang_rows"),
        ("getPmxjcz", {}, "kaijiang_rows"),
    ]

    cases: list[ApiCase] = []
    for endpoint_name, extra_params, validator in endpoint_specs:
        type_values = (3,) if endpoint_name == "curTerm" else (1, 2, 3)
        for lottery_type in type_values:
            query_params: dict[str, Any] = {"type": lottery_type}
            if endpoint_name != "curTerm":
                query_params["web"] = 4
            query_params.update(extra_params)
            suffix = f"type-{lottery_type}"
            if extra_params.get("num") is not None:
                suffix += f"-num-{extra_params['num']}"
            cases.append(
                ApiCase(
                    case_id=f"kaijiang-{endpoint_name}-{suffix}",
                    interface_name=f"/api/kaijiang/{endpoint_name}",
                    route_file=route_file,
                    route_pattern=pattern,
                    method="GET",
                    path=f"/api/kaijiang/{endpoint_name}",
                    query_params=query_params,
                    validator=validator,
                )
            )
    return cases


def build_upload_cases(route_file: str) -> list[ApiCase]:
    pattern = route_file_to_pattern(route_file)
    image_candidates = sorted(
        [
            path.name
            for path in UPLOADS_SOURCE_DIR.iterdir()
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        ]
    )
    filename = image_candidates[0] if image_candidates else "1742580086567063.png"
    return [
        ApiCase(
            case_id="uploads-image-valid-file",
            interface_name="/uploads/image/[bucket]/[filename]",
            route_file=route_file,
            route_pattern=pattern,
            method="GET",
            path=f"/uploads/image/20250322/{filename}",
            validator="upload_image",
        )
    ]


def build_generic_route_case(route_file: str) -> list[ApiCase]:
    pattern = route_file_to_pattern(route_file)
    if "{" in pattern:
        return []
    return [
        ApiCase(
            case_id=f"generic-{route_file.replace('/', '-').replace('.', '-')}",
            interface_name=pattern,
            route_file=route_file,
            route_pattern=pattern,
            method="GET",
            path=pattern,
            validator="json_object",
        )
    ]


CASE_BUILDERS: dict[str, Callable[[str], list[ApiCase]]] = {
    "app/api/lottery-data/route.ts": build_lottery_data_cases,
    "app/api/latest-draw/route.ts": build_latest_draw_cases,
    "app/api/next-draw-deadline/route.ts": build_next_draw_deadline_cases,
    "app/api/draw-history/route.ts": build_draw_history_cases,
    "app/api/post/getList/route.ts": build_post_get_list_cases,
    "app/api/predict/[mechanism]/route.ts": build_predict_cases,
    "app/api/kaijiang/[[...path]]/route.ts": build_legacy_kaijiang_cases,
    "app/uploads/image/[bucket]/[filename]/route.ts": build_upload_cases,
}


def build_all_cases() -> list[ApiCase]:
    cases: list[ApiCase] = []
    for route_file in DISCOVERED_ROUTE_FILES:
        builder = CASE_BUILDERS.get(route_file, build_generic_route_case)
        cases.extend(builder(route_file))
    return cases


ALL_CASES = build_all_cases()
TEST_RESULTS: list[dict[str, Any]] = []


def serialize_response_body(response: requests.Response) -> Any:
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("image/"):
        return {
            "content_type": content_type,
            "content_length": len(response.content),
        }

    if "application/json" in content_type:
        try:
            return response.json()
        except Exception:
            pass

    text = response.text
    if len(text) > 20000:
        return {
            "truncated": True,
            "preview": text[:20000],
            "full_length": len(text),
        }
    return text


def execute_case(session: requests.Session, case: ApiCase) -> dict[str, Any]:
    url = build_url(case.path)
    request_kwargs: dict[str, Any] = {
        "params": case.query_params or None,
        "timeout": case.timeout_seconds,
    }
    if case.json_body is not None:
        request_kwargs["json"] = case.json_body

    started_at = time.perf_counter()
    response: requests.Response | None = None
    error_message = ""
    passed = False

    try:
        response = session.request(case.method, url, **request_kwargs)
        elapsed_seconds = time.perf_counter() - started_at

        if response.status_code not in case.success_status_codes:
            raise AssertionError(
                f"unexpected status code {response.status_code}, expected {case.success_status_codes}"
            )

        if elapsed_seconds > RESPONSE_TIME_THRESHOLD_SECONDS:
            raise AssertionError(
                f"response time {elapsed_seconds:.3f}s exceeded {RESPONSE_TIME_THRESHOLD_SECONDS:.1f}s"
            )

        VALIDATORS[case.validator](case, response)
        passed = True
    except Exception as exc:  # noqa: BLE001
        elapsed_seconds = time.perf_counter() - started_at
        error_message = str(exc)

    result: dict[str, Any] = {
        "interface_name": case.interface_name,
        "case_id": case.case_id,
        "route_file": case.route_file,
        "route_pattern": case.route_pattern,
        "request": {
            "method": case.method,
            "url": url,
            "query_params": case.query_params,
            "json_body": case.json_body,
        },
        "response_status_code": response.status_code if response is not None else None,
        "response_time_ms": round(elapsed_seconds * 1000, 3),
        "passed": passed,
        "error_message": error_message,
        "response_body": serialize_response_body(response) if response is not None else None,
    }
    return result


@pytest.fixture(scope="session")
def http_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "frontend-api-pytest/1.0"})
    yield session
    session.close()


@pytest.fixture(scope="session", autouse=True)
def write_results_file() -> None:
    yield
    summary_counter = Counter(result["passed"] for result in TEST_RESULTS)
    payload = {
        "generated_at": datetime.now().isoformat(),
        "base_url": get_base_url(),
        "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "response_time_threshold_seconds": RESPONSE_TIME_THRESHOLD_SECONDS,
        "discovered_routes": DISCOVERED_ROUTE_FILES,
        "summary": {
            "total": len(TEST_RESULTS),
            "passed": int(summary_counter.get(True, 0)),
            "failed": int(summary_counter.get(False, 0)),
        },
        "results": TEST_RESULTS,
    }
    RESULTS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda case: case.case_id)
def test_frontend_api_cases(http_session: requests.Session, case: ApiCase) -> None:
    result = execute_case(http_session, case)
    TEST_RESULTS.append(result)
    assert result["passed"], (
        f"{case.case_id} failed: {result['error_message']} "
        f"(status={result['response_status_code']}, time_ms={result['response_time_ms']})"
    )


def test_discovered_routes_have_cases() -> None:
    covered_route_files = {case.route_file for case in ALL_CASES}
    missing = [route_file for route_file in DISCOVERED_ROUTE_FILES if route_file not in covered_route_files]
    assert not missing, f"missing generated cases for routes: {missing}"


def _run_as_script() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run frontend API validation tests.")
    parser.add_argument("--base-url", default=None, help="Frontend base URL, e.g. http://127.0.0.1:3000")
    parser.add_argument("pytest_args", nargs="*", help="Extra arguments forwarded to pytest")
    args = parser.parse_args()

    if args.base_url:
        os.environ["FRONTEND_API_TEST_BASE_URL"] = args.base_url

    return pytest.main([__file__, "-q", *args.pytest_args])


if __name__ == "__main__":
    raise SystemExit(_run_as_script())
