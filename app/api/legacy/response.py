"""Legacy response envelope, ported byte-compatibly from bds-genai-dgl
``common/response`` (response_schema.py + response_code.py).

Output shape is intentionally identical to legacy: ``{"code", "message",
"data"}`` with datetimes serialized as ``%Y-%m-%d %H:%M:%S``. Internally the
platform raises typed ``AppError``s; legacy routes translate them into this
envelope at the edge only (wired in later phases).
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict

# Legacy serialized datetimes with this exact format (settings.DATETIME_FORMAT).
LEGACY_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class CustomCodeBase(Enum):
    @property
    def code(self) -> int:
        return self.value[0]

    @property
    def message(self) -> str:
        return self.value[1]


class CustomResponseCode(CustomCodeBase):
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


@dataclasses.dataclass
class CustomResponse:
    """Return response status codes instead of enumerations."""

    code: int
    message: str


class ResponseModel(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: lambda x: x.strftime(LEGACY_DATETIME_FORMAT)},
        arbitrary_types_allowed=True,
    )
    code: int = CustomResponseCode.HTTP_200.code
    message: str = CustomResponseCode.HTTP_200.message
    data: Any | None = None


class ResponseBase:
    @staticmethod
    async def _response(
        *,
        res: CustomResponseCode | CustomResponse,
        data: Any | None = None,
    ) -> ResponseModel:
        return ResponseModel(code=res.code, message=res.message, data=data)

    async def success(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_200,
        data: Any | None = None,
    ) -> ResponseModel:
        return await self._response(res=res, data=data)

    async def fail(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_500,
        data: Any | None = None,
    ) -> ResponseModel:
        return await self._response(res=res, data=data)


response_base = ResponseBase()
