"""Legacy response envelope, ported byte-compatibly from bds-genai-dgl
``common/response`` (response_schema.py + response_code.py).

Output shape is intentionally identical to legacy: ``{"code", "message",
"data"}`` with datetimes serialized as ``%Y-%m-%d %H:%M:%S``. Internally the
platform raises typed ``AppError``s; legacy routes translate them into this
envelope at the edge only (wired in later phases).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict

# Legacy serialized datetimes with this exact format (settings.DATETIME_FORMAT).
LEGACY_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class LegacyCodeBase(Enum):
    @property
    def code(self) -> int:
        return self.value[0]

    @property
    def message(self) -> str:
        return self.value[1]


class LegacyResponseCode(LegacyCodeBase):
    HTTP_200 = (200, "OK")
    HTTP_201 = (201, "Created")
    HTTP_202 = (202, "Accepted")
    HTTP_204 = (204, "No Content")
    HTTP_400 = (400, "Bad Request")
    HTTP_401 = (401, "Unauthorized")
    HTTP_403 = (403, "Forbidden")
    HTTP_404 = (404, "Not Found")
    HTTP_405 = (405, "Method Not Allowed")
    HTTP_406 = (406, "Not Acceptable")
    HTTP_408 = (408, "Request Timeout")
    HTTP_409 = (409, "Conflict")
    HTTP_410 = (410, "Gone")
    HTTP_411 = (411, "Length Required")
    HTTP_412 = (412, "Precondition Failed")
    HTTP_413 = (413, "Request Entity Too Large")
    HTTP_414 = (414, "Request-URI Too Long")
    HTTP_415 = (415, "Unsupported Media Type")
    HTTP_416 = (416, "Requested Range Not Satisfiable")
    HTTP_417 = (417, "Expectation Failed")
    HTTP_429 = (429, "Too Many Requests")
    HTTP_500 = (500, "Internal Server Error")
    HTTP_501 = (501, "Not Implemented")
    HTTP_502 = (502, "Bad Gateway")
    HTTP_503 = (503, "Service Unavailable")
    HTTP_504 = (504, "Gateway Timeout")
    HTTP_505 = (505, "HTTP Version Not Supported")


class LegacyResponseModel(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: lambda x: x.strftime(LEGACY_DATETIME_FORMAT)},
        arbitrary_types_allowed=True,
    )
    code: int = LegacyResponseCode.HTTP_200.code
    message: str = LegacyResponseCode.HTTP_200.message
    data: Any | None = None


class LegacyResponseBase:
    @staticmethod
    async def _response(
        *,
        response_code: LegacyResponseCode,
        message: str | None = None,
        data: Any | None = None,
    ) -> LegacyResponseModel:
        return LegacyResponseModel(
            code=response_code.code,
            message=message or response_code.message,
            data=data,
        )

    async def success(
        self,
        *,
        response_code: LegacyResponseCode = LegacyResponseCode.HTTP_200,
        message: str | None = None,
        data: Any | None = None,
    ) -> LegacyResponseModel:
        return await self._response(
            response_code=response_code,
            message=message,
            data=data,
        )

    async def fail(
        self,
        *,
        response_code: LegacyResponseCode = LegacyResponseCode.HTTP_500,
        message: str | None = None,
        data: Any | None = None,
    ) -> LegacyResponseModel:
        return await self._response(
            response_code=response_code,
            message=message,
            data=data,
        )


legacy_response = LegacyResponseBase()
