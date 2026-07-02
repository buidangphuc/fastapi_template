from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.config import Settings
from app.modules.ai.llm.langfuse import (
    LangfuseLLMTracker,
    LLMTraceContext,
    build_langfuse_tracker,
)
from app.modules.ai.llm.router import ModelBuilder, ModelRouter

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel


@dataclass(frozen=True)
class LLMInstance:
    chat_model: BaseChatModel
    tracker: LangfuseLLMTracker

    def trace_config(self, context: LLMTraceContext | None = None) -> dict[str, object]:
        return self.tracker.trace_config(context)


def build_chat_model(
    settings: Settings,
    *,
    model_builder: ModelBuilder | None = None,
) -> BaseChatModel:
    return ModelRouter(settings, model_builder=model_builder).chat_model()


def build_llm_instance(
    settings: Settings,
    *,
    instance_id: str,
    service_name: str,
    tags: tuple[str, ...] = (),
    model_builder: ModelBuilder | None = None,
) -> LLMInstance:
    chat_model = (
        build_chat_model(settings)
        if model_builder is None
        else build_chat_model(settings, model_builder=model_builder)
    )
    return LLMInstance(
        chat_model=chat_model,
        tracker=build_langfuse_tracker(
            settings,
            instance_id=instance_id,
            service_name=service_name,
            tags=tags,
        ),
    )
