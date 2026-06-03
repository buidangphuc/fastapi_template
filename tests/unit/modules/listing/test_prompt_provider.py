from types import SimpleNamespace

from app.modules.business.listing.generation.prompt_provider import (
    FilePromptProvider,
    LangfusePromptProvider,
)


class _DisabledTracker:
    def get_prompt(self, name, **kwargs):
        raise RuntimeError("Langfuse is disabled for this LLM instance")


class _OkTracker:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_prompt(self, name, **kwargs):
        return SimpleNamespace(compile=lambda: self._text)


def test_file_provider_reads_packaged_prompt():
    text = FilePromptProvider().get("project_summary")
    assert text.strip()
    assert "Output Format" in text


def test_langfuse_provider_falls_back_to_file_when_disabled():
    provider = LangfusePromptProvider(_DisabledTracker(), fallback=FilePromptProvider())
    text = provider.get("project_summary")
    assert "Output Format" in text  # resolved from the packaged file


def test_langfuse_provider_uses_langfuse_when_available():
    provider = LangfusePromptProvider(
        _OkTracker("MANAGED PROMPT"), fallback=FilePromptProvider()
    )
    assert provider.get("project_summary") == "MANAGED PROMPT"
