from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Base error for provider configuration or runtime failures."""


class ProviderConfigError(ProviderError):
    """Raised when a provider is missing required local configuration."""


class ProviderRuntimeError(ProviderError):
    """Raised when a provider request fails after configuration is valid."""


@dataclass(frozen=True)
class SynthesisRequest:
    provider_id: str
    language: str
    script_id: str
    turn_index: int
    speaker_slot: str
    speaker_name: str
    text: str
    tts_instructions: str
    suggested_audio_path: str
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SynthesisResult:
    provider_id: str
    status: str
    output_path: str
    audio_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Provider(Protocol):
    id: str
    audio_file_extension: str

    def synthesize(
        self,
        request: SynthesisRequest,
        *,
        output_path: Path,
    ) -> SynthesisResult:
        """Plan or perform synthesis for one utterance."""
