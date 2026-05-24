from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SynthesisRequest:
    provider_id: str
    language: str
    script_id: str
    turn_index: int
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


class Provider(Protocol):
    id: str

    def synthesize(
        self,
        request: SynthesisRequest,
        *,
        output_path: Path,
    ) -> SynthesisResult:
        """Plan or perform synthesis for one utterance."""
