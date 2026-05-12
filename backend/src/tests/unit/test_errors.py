"""core.errors 单元测试。"""

from __future__ import annotations

from core.errors import (
    AppError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ValidationError,
    ConflictError,
)


def test_app_error_defaults():
    err = AppError("something wrong")
    assert err.status_code == 400
    assert err.code == "APP_ERROR"
    assert err.message == "something wrong"


def test_app_error_custom():
    err = AppError("not found", status_code=404, code="CUSTOM")
    assert err.status_code == 404
    assert err.code == "CUSTOM"


def test_not_found_error():
    err = NotFoundError("站点不存在")
    assert err.status_code == 404
    assert err.code == "NOT_FOUND"


def test_unauthorized_error():
    err = UnauthorizedError("未登录")
    assert err.status_code == 401
    assert err.code == "UNAUTHORIZED"


def test_forbidden_error():
    err = ForbiddenError("无权限")
    assert err.status_code == 403
    assert err.code == "FORBIDDEN"


def test_validation_error():
    err = ValidationError("参数无效")
    assert err.status_code == 400
    assert err.code == "VALIDATION_ERROR"


def test_conflict_error():
    err = ConflictError("重复创建")
    assert err.status_code == 409
    assert err.code == "CONFLICT"


def test_error_to_dict():
    err = NotFoundError("site_id=99 不存在")
    d = err.to_dict()
    assert d["error"] is True
    assert d["code"] == "NOT_FOUND"
    assert d["status"] == 404


def test_app_error_is_exception():
    err = AppError("test")
    assert isinstance(err, Exception)
    try:
        raise err
    except AppError as e:
        assert e.status_code == 400
