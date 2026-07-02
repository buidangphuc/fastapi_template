"""Prompt-template builder (ported from bds-genai-dgl core/generator/prompt.py).

Behavior-frozen string assembly. ``tiktoken``-based ``count_tokens`` is dropped
(unused by generation). ``to_api_message`` returns role/content dicts that
langchain chat models accept directly.
"""

from __future__ import annotations

from string import Template as StringTemplate
from typing import Any


class PromptSectionTemplate:
    def __init__(
        self,
        name: str,
        contents: list[str] | None = None,
        role: str = "system",
    ) -> None:
        self.name = name
        self.contents = contents or []
        self.role = role
        self.sections: list[PromptSectionTemplate] = []
        self.variables: dict[str, Any] = {}

    def _convert_to_template(self, template: str) -> StringTemplate:
        return StringTemplate(template)

    def add_variables(self, variables: dict[str, Any]) -> None:
        self.variables.update(variables)

    def add_variable(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def add_section(self, section: PromptSectionTemplate) -> None:
        self.sections.append(section)

    def add_content(self, content: str) -> None:
        self.contents.append(content)

    def add_contents(self, contents: list[str]) -> None:
        self.contents.extend(contents)

    def to_str(self) -> str:
        name = self._convert_to_template(self.name).substitute(**self.variables)
        contents = "\n".join(
            self._convert_to_template(content).substitute(**self.variables)
            for content in self.contents
            if content
        )
        section = "\n".join(section.to_str() for section in self.sections)
        return f"{name}\n{contents}\n{section}"


class OpenAIPromptTemplate:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name
        self.sections: list[PromptSectionTemplate] = []
        self.variables: dict[str, Any] = {}
        self.user_message: str | None = None

    def add_user_message(self, message: str) -> None:
        self.user_message = message

    def add_section(self, section: PromptSectionTemplate) -> None:
        self.sections.append(section)

    def add_variables(self, variables: dict[str, Any]) -> None:
        self.variables.update(variables)

    def add_variable(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def to_str(self) -> str:
        out = ""
        for section in self.sections:
            section.add_variables(self.variables)
            out += section.to_str() + "\n"
        return out.strip()

    def to_api_message(self) -> list[dict[str, str]]:
        if self.user_message is not None:
            return [
                {"role": "system", "content": self.to_str()},
                {"role": "user", "content": self.user_message or ""},
            ]
        return [{"role": "user", "content": self.to_str()}]
