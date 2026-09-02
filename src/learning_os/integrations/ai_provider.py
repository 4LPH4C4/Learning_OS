"""Optional AI provider boundary. Core learning works without an AI SDK or key."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


class AIProviderError(RuntimeError):
    """Raised when an AI provider cannot answer."""


@dataclass(frozen=True)
class AIContext:
    prompt: str
    course_id: str | None = None
    lesson_id: str | None = None
    content: str = ""
    history: tuple[Mapping[str, str], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


class AIProvider(Protocol):
    def answer(self, context: AIContext) -> str:
        """Return an answer for the supplied learning context."""


class DisabledAIProvider:
    """Provider used when optional AI integration is not configured."""

    def answer(self, context: AIContext) -> str:
        raise AIProviderError(
            "AI Tutor가 비활성화되어 있다. AI provider SDK를 설치하고 API 키를 설정한 뒤 다시 시도해라."
        )
