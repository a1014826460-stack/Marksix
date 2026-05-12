"""统一业务异常类型。

后续 routes 和 service 尽量抛这些异常，
不要在业务代码里到处抛裸 KeyError / ValueError。
"""

from __future__ import annotations


class AppError(Exception):
    """业务异常基类，所有自定义异常均继承自此类。"""
    status_code: int = 400
    code: str = "APP_ERROR"

    def __init__(self, message: str = "", status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code

    def to_dict(self) -> dict[str, object]:
        return {
            "error": True,
            "code": self.code,
            "message": self.message or str(self),
            "status": self.status_code,
        }


class NotFoundError(AppError):
    """资源不存在（实体未找到）。"""
    status_code = 404
    code = "NOT_FOUND"


class UnauthorizedError(AppError):
    """未认证（缺少有效登录凭证）。"""
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    """无权限（已认证但权限不足）。"""
    status_code = 403
    code = "FORBIDDEN"


class ValidationError(AppError):
    """参数校验失败（请求参数格式或取值不合法）。"""
    status_code = 400
    code = "VALIDATION_ERROR"


class ConflictError(AppError):
    """资源冲突（如重复创建、并发修改冲突）。"""
    status_code = 409
    code = "CONFLICT"
