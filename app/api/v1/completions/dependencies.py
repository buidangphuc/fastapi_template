"""Dependency adapters for the completions surface."""

from __future__ import annotations

from fastapi import Request

from app.bootstrap.state import get_app_resources
from app.core.errors import AppError
from app.modules.business.completions.pipeline import CompletionPipeline


def get_completion_pipeline(request: Request) -> CompletionPipeline:
    pipeline = get_app_resources(request.app).completion_pipeline
    if pipeline is None:
        raise AppError(
            code="completion_handler_not_configured",
            message="Completion handler is not configured",
            status_code=501,
        )
    return pipeline
