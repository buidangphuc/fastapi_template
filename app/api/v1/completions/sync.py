from uuid import uuid4

from fastapi import APIRouter, Request

from app.api.v1.completions.dependencies import get_completion_pipeline
from app.modules.business.completions.schemas import (
    CompletionRequest,
    CompletionResponse,
)

router = APIRouter()


@router.post("", response_model=CompletionResponse)
async def complete(
    payload: CompletionRequest,
    request: Request,
) -> CompletionResponse:
    pipeline = get_completion_pipeline(request)
    result = await pipeline.complete(payload)
    return CompletionResponse(
        id=f"cmpl_{uuid4().hex}",
        content=result.content,
        model=result.model,
        metadata=result.metadata,
    )
