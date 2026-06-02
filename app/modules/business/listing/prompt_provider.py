"""Prompt provider — Langfuse-managed prompts with a packaged file fallback.

Static prompts (e.g. the project-summary system prompt) are managed in Langfuse
(versioned + labeled). When Langfuse is disabled (local/test) or a prompt is
missing/unfetchable, falls back to the packaged ``prompts/<name>.txt`` asset, so
local and CI runs never require a live Langfuse.

Dynamic, code-assembled prompts (description / pair_address) are NOT managed
here — they are versioned via ``PROMPT_VERSION`` (stamped on each listing) and
captured per-call by Langfuse tracing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from loguru import logger

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class PromptProvider(Protocol):
    def get(self, name: str) -> str: ...


class FilePromptProvider:
    """Load a prompt from the packaged ``prompts/<name>.txt`` asset."""

    def __init__(self, base_dir: Path = _PROMPTS_DIR) -> None:
        self._base_dir = base_dir

    def get(self, name: str) -> str:
        return (self._base_dir / f"{name}.txt").read_text(encoding="utf-8")


class LangfusePromptProvider:
    """Fetch a labeled prompt from Langfuse; fall back to file on any failure.

    When ``LANGFUSE_ENABLED`` is false the tracker is disabled and ``get_prompt``
    raises — caught here and resolved from the file fallback.
    """

    def __init__(
        self,
        tracker: Any,
        *,
        label: str = "production",
        fallback: PromptProvider | None = None,
    ) -> None:
        self._tracker = tracker
        self._label = label
        self._fallback = fallback or FilePromptProvider()

    def get(self, name: str) -> str:
        try:
            prompt = self._tracker.get_prompt(name, label=self._label)
            text = (
                prompt.compile()
                if hasattr(prompt, "compile")
                else getattr(prompt, "prompt", None)
            )
            if isinstance(text, str) and text.strip():
                return text
            logger.warning("Langfuse prompt %r empty/non-text; using file", name)
        except Exception as exc:
            logger.warning(
                "Langfuse prompt %r fetch failed (%s); using file", name, exc
            )
        return self._fallback.get(name)
