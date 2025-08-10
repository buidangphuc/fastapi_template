from typing import Any

from fastapi import HTTPException
from starlette.background import BackgroundTask

from common.response.response_code import CustomErrorCode, StandardResponseCode


class BaseExceptionMixin(Exception):
    code: int

    def __init__(
        self,
        *,
        msg: str = None,
        data: Any = None,
        background: BackgroundTask | None = None,
    ):
        self.msg = msg
        self.data = data
        # The original background task: https://www.starlette.io/background/
        self.background = background


class HTTPError(HTTPException):
    def __init__(
        self, *, code: int, msg: Any = None, headers: dict[str, Any] | None = None
    ):
        super().__init__(status_code=code, detail=msg, headers=headers)


class CustomError(BaseExceptionMixin):
    def __init__(
        self,
        *,
        error: CustomErrorCode,
        data: Any = None,
        background: BackgroundTask | None = None,
    ):
        self.code = error.code
        super().__init__(msg=error.msg, data=data, background=background)


class RequestError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_400

    def __init__(
        self,
        *,
        msg: str = "Bad Request",
        data: Any = None,
        background: BackgroundTask | None = None,
    ):
        super().__init__(msg=msg, data=data, background=background)


class ForbiddenError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_403

    def __init__(
        self,
        *,
        msg: str = "Forbidden",
        data: Any = None,
        background: BackgroundTask | None = None,
    ):
        super().__init__(msg=msg, data=data, background=background)


class NotFoundError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_404

    def __init__(
        self,
        *,
        msg: str = "Not Found",
        data: Any = None,
        background: BackgroundTask | None = None,
    ):
        super().__init__(msg=msg, data=data, background=background)


class ServerError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_500

    def __init__(
        self,
        *,
        msg: str = "Internal Server Error",
        data: Any = None,
        background: BackgroundTask | None = None,
    ):
        super().__init__(msg=msg, data=data, background=background)


class GatewayError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_502

    def __init__(
        self,
        *,
        msg: str = "Bad Gateway",
        data: Any = None,
        background: BackgroundTask | None = None,
    ):
        super().__init__(msg=msg, data=data, background=background)


class AuthorizationError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_401

    def __init__(
        self,
        *,
        msg: str = "Permission Denied",
        data: Any = None,
        background: BackgroundTask | None = None,
    ):
        super().__init__(msg=msg, data=data, background=background)


class TokenError(HTTPError):
    code = StandardResponseCode.HTTP_401

    def __init__(
        self, *, msg: str = "Not Authenticated", headers: dict[str, Any] | None = None
    ):
        super().__init__(
            code=self.code, msg=msg, headers=headers or {"WWW-Authenticate": "Bearer"}
        )


class DebugError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_500

    def __init__(
        self,
        *,
        msg: str = "Debug Error",
        data: Any = None,
        background: BackgroundTask | None = None,
        debug_info: dict = None,
    ):
        self.debug_info = debug_info or {}
        super().__init__(msg=msg, data=data, background=background)


class ProcessingError(DebugError):
    def __init__(
        self,
        *,
        step: str,
        error: Exception,
        msg: str = "Processing Error",
        data: Any = None,
    ):
        debug_info = {
            "step": step,
            "error_type": type(error).__name__,
            "error_details": str(error),
        }
        super().__init__(msg=msg, data=data, debug_info=debug_info)


class StorageError(ServerError):
    """Base exception for storage operations."""

    def __init__(
        self,
        *,
        operation: str,
        entity: str | None = None,
        msg: str = "Storage operation failed",
        data: Any = None,
        background: BackgroundTask | None = None,
    ):
        error_msg = f"{msg} - Operation: {operation}"
        if entity:
            error_msg += f", Entity: {entity}"
        super().__init__(msg=error_msg, data=data, background=background)


class EntityCreationError(StorageError):
    """Raised when entity creation fails."""

    def __init__(
        self, *, entity: str, msg: str = "Failed to create entity", data: Any = None
    ):
        super().__init__(operation="create", entity=entity, msg=msg, data=data)
