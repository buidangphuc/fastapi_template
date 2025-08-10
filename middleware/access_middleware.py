#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from common.log import log
from utils.timezone import timezone


class AccessMiddleware(BaseHTTPMiddleware):
    """Request log middleware"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process requests and record access logs

        :param request: FastAPI request object
        :param call_next: Next middleware or route handler function
        :return:
        """
        start_time = timezone.now()
        response = await call_next(request)
        end_time = timezone.now()
        log.info(
            f"{request.client.host: <15} | {request.method: <8} | {response.status_code: <6} | "
            f"{request.url.path} | {round((end_time - start_time).total_seconds(), 3) * 1000.0}ms"
        )
        return response
