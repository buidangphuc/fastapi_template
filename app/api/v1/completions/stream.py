import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.api.v1.completions.dependencies import get_completion_pipeline
from app.modules.business.completions.pipeline import CompletionPipeline
from app.modules.business.completions.schemas import (
    CompletionRequest,
    CompletionStreamChunk,
)

router = APIRouter()


@router.post("/stream")
async def stream(
    payload: CompletionRequest,
    request: Request,
) -> StreamingResponse:
    pipeline = get_completion_pipeline(request)
    return StreamingResponse(
        stream_completion_events(pipeline, payload),
        media_type="text/event-stream",
    )


async def stream_completion_events(
    pipeline: CompletionPipeline,
    payload: CompletionRequest,
) -> AsyncIterator[str]:
    async for chunk in pipeline.stream(payload):
        stream_chunk = normalize_stream_chunk(chunk)
        if stream_chunk.delta:
            yield sse_event(
                {
                    "type": "content.delta",
                    "delta": stream_chunk.delta,
                    "metadata": stream_chunk.metadata,
                }
            )
    yield sse_event({"type": "done"})


def normalize_stream_chunk(
    chunk: CompletionStreamChunk | str,
) -> CompletionStreamChunk:
    if isinstance(chunk, str):
        return CompletionStreamChunk(delta=chunk)
    return chunk


def sse_event(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"
