# middleware/request_id_middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.conf import settings
from utils.request_id import clear_request_id, set_request_id


class RequestIdMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, app, header_name: str | None = settings.TRACE_ID_REQUEST_HEADER_KEY
    ):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        request_id = set_request_id(request.headers.get(self.header_name))
        try:
            response: Response = await call_next(request)
            response.headers[self.header_name] = request_id
            return response
        finally:
            clear_request_id()
