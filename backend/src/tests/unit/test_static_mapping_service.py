from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.errors import ValidationError
from domains.static_mappings.service import (
    StaticMappingDatasetConfig,
    _build_dataset_path,
    _build_db_target,
    _infer_column_sql_type,
    _read_json_records,
    load_import_config,
)


def test_build_dataset_path() -> None:
    assert _build_dataset_path("brain_test", 7, "json_data") == "json_data/brain_test/7"


def test_infer_column_sql_type() -> None:
    assert _infer_column_sql_type([1, 2, 3]) == "BIGINT"
    assert _infer_column_sql_type([1.0, 2.5]) == "DOUBLE PRECISION"
    assert _infer_column_sql_type([True, False]) == "BOOLEAN"
    assert _infer_column_sql_type(["a", "b"]) == "TEXT"


def test_build_db_target_from_split_parts() -> None:
    assert (
        _build_db_target(
            host="localhost",
            port="5432",
            db_name="liuhecai",
            user="tester",
            password="secret",
        )
        == "postgresql://tester:secret@localhost:5432/liuhecai"
    )


def test_read_json_records_success(tmp_path: Path) -> None:
    json_path = tmp_path / "brain_test.json"
    json_path.write_text(
        json.dumps(
            [
                {"id": 1, "question": "Q1", "answer": "A1", "tips": "T1", "analysis": "X1"},
                {"id": 2, "question": "Q2", "answer": "A2", "tips": "T2", "analysis": "X2"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    dataset = StaticMappingDatasetConfig(
        name="brain_test",
        json_path=json_path,
        table_name="static_mapping_brain_test",
    )

    rows = _read_json_records(dataset)

    assert len(rows) == 2
    assert rows[0]["mapping_path"] == "json_data/brain_test/1"
    assert rows[1]["mapping_path"] == "json_data/brain_test/2"


def test_read_json_records_empty_file(tmp_path: Path) -> None:
    json_path = tmp_path / "sx_verse.json"
    json_path.write_text("", encoding="utf-8")
    dataset = StaticMappingDatasetConfig(
        name="sx_verse",
        json_path=json_path,
        table_name="static_mapping_sx_verse",
    )

    with pytest.raises(ValidationError, match="源文件为空"):
        _read_json_records(dataset)


def test_load_import_config_from_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "static_mappings.yaml"
    config_path.write_text(
        "\n".join(
            [
                "database:",
                "  host: localhost",
                "  port: '5432'",
                "  name: liuhecai",
                "  user: user",
                "  password: pass",
                "  schema: public",
                "static_mappings:",
                "  datasets:",
                "    - name: brain_test",
                "      json_path: data/json_data/brain_test.json",
                "      table_name: static_mapping_brain_test",
                "      key_field: id",
                "      path_field: mapping_path",
            ]
        ),
        encoding="utf-8",
    )

    config = load_import_config(config_path=config_path, incremental=True)

    assert config.incremental is True
    assert config.schema_name == "public"
    assert config.db_target == "postgresql://user:pass@localhost:5432/liuhecai"
    assert config.datasets[0].name == "brain_test"
