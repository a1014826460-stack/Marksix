from __future__ import annotations

import sys
from pathlib import Path


_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import db
from psycopg.pq import TransactionStatus


class _FakePgConn:
    def __init__(self, status: TransactionStatus = TransactionStatus.IDLE):
        self.closed = False
        self.broken = False
        self.commits = 0
        self.rollbacks = 0
        self.pgconn = type("PgConn", (), {"transaction_status": status})()

    def execute(self, sql_text, params=()):
        return type(
            "FakeCursor",
            (),
            {
                "fetchone": lambda self: None,
                "fetchall": lambda self: [],
                "rowcount": 0,
            },
        )()

    def cursor(self):
        return self

    def executemany(self, sql_text, seq_of_params):
        return self

    def commit(self):
        self.commits += 1
        self.pgconn.transaction_status = TransactionStatus.IDLE

    def rollback(self):
        self.rollbacks += 1
        self.pgconn.transaction_status = TransactionStatus.IDLE

    def close(self):
        self.closed = True


def _reset_pool_state() -> None:
    db._POSTGRES_POOL._idle_by_target.clear()
    db._POSTGRES_POOL._total_by_target.clear()


def test_postgres_connect_reuses_pooled_connections(monkeypatch):
    _reset_pool_state()
    created: list[_FakePgConn] = []

    def fake_connect(target, row_factory=None, connect_timeout=10, prepare_threshold=None):
        conn = _FakePgConn()
        created.append(conn)
        return conn

    monkeypatch.setattr(db.psycopg, "connect", fake_connect)
    monkeypatch.setenv("POSTGRES_POOL_MAX_SIZE", "2")
    target = "postgresql://postgres:test@localhost:5432/liuhecai"

    with db.connect(target) as conn1:
        assert conn1.engine == "postgres"

    with db.connect(target) as conn2:
        assert conn2.engine == "postgres"

    assert len(created) == 1
    assert created[0].closed is False
    assert created[0].commits == 2


def test_postgres_connect_discards_broken_connection(monkeypatch):
    _reset_pool_state()
    created: list[_FakePgConn] = []

    def fake_connect(target, row_factory=None, connect_timeout=10, prepare_threshold=None):
        conn = _FakePgConn()
        created.append(conn)
        return conn

    monkeypatch.setattr(db.psycopg, "connect", fake_connect)
    monkeypatch.setenv("POSTGRES_POOL_MAX_SIZE", "2")
    target = "postgresql://postgres:test@localhost:5432/liuhecai"

    with db.connect(target) as conn1:
        raw = conn1._raw
        raw.broken = True

    with db.connect(target) as conn2:
        assert conn2.engine == "postgres"

    assert len(created) == 2
    assert created[0].closed is True
    assert created[1].closed is False


def test_pool_rolls_back_an_unfinished_transaction_instead_of_committing_it():
    raw = _FakePgConn(TransactionStatus.INTRANS)

    db._PooledPostgresConnectionManager._reset_connection(raw)

    assert raw.rollbacks == 1
    assert raw.commits == 0
