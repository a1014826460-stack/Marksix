from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def _service_block(compose: str, service: str, next_service: str) -> str:
    return compose.split(f"  {service}:", 1)[1].split(f"\n  {next_service}:", 1)[0]


def test_python_api_container_uses_dependency_free_liveness_probe():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    api_block = _service_block(compose, "python-api", "scheduler-worker")

    assert "http://127.0.0.1:8000/health/live" in api_block
    assert "/api/health" not in api_block


def test_nginx_exposes_exact_liveness_and_readiness_proxies():
    for relative_path in ("deploy/nginx.conf", "deploy/nginx.domain.ssl.conf.example"):
        nginx = (ROOT / relative_path).read_text(encoding="utf-8")

        assert "location = /health/live" in nginx
        assert "proxy_pass http://python-api:8000/health/live;" in nginx
        assert "location = /health/ready" in nginx
        assert "proxy_pass http://python-api:8000/health/ready;" in nginx


def test_environment_template_documents_managed_database_endpoint_contract():
    environment = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "DATABASE_WRITE_URL" in environment
    assert "DATABASE_READ_URL" in environment
    assert "LIUHECAI_DATABASE_MODE=managed" in environment


def test_scheduler_worker_remains_separate_from_python_api_in_compose():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    api_block = _service_block(compose, "python-api", "scheduler-worker")
    worker_block = _service_block(compose, "scheduler-worker", "db-migrate")

    assert "scheduler_worker" not in api_block
    assert "python -m scheduler_worker" in worker_block
