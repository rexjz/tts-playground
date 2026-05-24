from __future__ import annotations

import base64
import json
import uuid
from pathlib import Path
from typing import Callable, Any, Iterable

from tts_playground.providers.base import (
    ProviderRuntimeError,
    SynthesisRequest,
    SynthesisResult,
)
from tts_playground.providers.config import VolcengineSeedTtsConfig
from tts_playground.providers.http import post_json_stream


class VolcengineSeedTtsProvider:
    id = "volcengine_seed_tts"

    def __init__(
        self,
        config: VolcengineSeedTtsConfig | None = None,
        *,
        post_stream: Callable[..., Iterable[dict[str, Any]]] = post_json_stream,
    ) -> None:
        self.config = config or VolcengineSeedTtsConfig.from_env()
        self._post_stream = post_stream

    @property
    def audio_file_extension(self) -> str:
        return self.config.audio_file_extension

    def synthesize(
        self,
        request: SynthesisRequest,
        *,
        output_path: Path,
    ) -> SynthesisResult:
        req_id = str(uuid.uuid4())
        payload = self._build_payload(request)
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self.config.api_key,
            "X-Api-Resource-Id": self.config.resource_id,
            "X-Api-Request-Id": req_id,
        }

        audio_chunks: list[bytes] = []
        sentences: list[dict[str, Any]] = []
        usage: dict[str, Any] | None = None
        finish_message: str | None = None
        for response_payload in self._post_stream(
            self.config.endpoint,
            body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            timeout_seconds=self.config.timeout_seconds,
        ):
            code = response_payload.get("code")
            message = response_payload.get("message") or response_payload.get("Message")
            if code == 0:
                data = response_payload.get("data")
                if data is not None:
                    audio_chunks.append(_decode_audio(data, "Volcengine Seed-TTS V3"))
                sentence = response_payload.get("sentence")
                if isinstance(sentence, dict):
                    sentences.append(sentence)
                continue
            if code == 20000000:
                usage_value = response_payload.get("usage")
                if isinstance(usage_value, dict):
                    usage = usage_value
                finish_message = str(message or "")
                continue
            raise ProviderRuntimeError(
                f"Volcengine Seed-TTS V3 failed with code {code}: {message}"
            )

        if not finish_message:
            raise ProviderRuntimeError("Volcengine Seed-TTS V3 stream ended early")

        audio = b"".join(audio_chunks)
        if not audio:
            raise ProviderRuntimeError("Volcengine Seed-TTS V3 returned no audio data")
        audio_path = Path(request.suggested_audio_path)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(audio)

        result_payload = {
            "kind": "utterance",
            "status": "synthesized",
            "request": request.to_dict(),
            "audio_path": audio_path.as_posix(),
            "provider_response": {
                "request_id": req_id,
                "finish_code": 20000000,
                "finish_message": finish_message,
                "audio_chunk_count": len(audio_chunks),
                "sentences": sentences,
                "usage": usage,
            },
        }
        _write_json(output_path, result_payload)

        return SynthesisResult(
            provider_id=self.id,
            status="synthesized",
            output_path=output_path.as_posix(),
            audio_path=audio_path.as_posix(),
            metadata={"request_id": req_id, "audio_chunk_count": len(audio_chunks)},
        )

    def _build_payload(
        self,
        request: SynthesisRequest,
    ) -> dict[str, Any]:
        voice = self.config.voice_for(request.speaker_slot)
        audio_params: dict[str, Any] = {
            "format": self.config.audio_format,
            "sample_rate": self.config.sample_rate,
            "speech_rate": (
                voice.speech_rate
                if voice.speech_rate is not None
                else self.config.speech_rate
            ),
            "loudness_rate": (
                voice.loudness_rate
                if voice.loudness_rate is not None
                else self.config.loudness_rate
            ),
            "enable_subtitle": self.config.enable_subtitle,
        }
        emotion = voice.emotion or self.config.emotion
        emotion_scale = (
            voice.emotion_scale
            if voice.emotion_scale is not None
            else self.config.emotion_scale
        )
        if self.config.bit_rate is not None:
            audio_params["bit_rate"] = self.config.bit_rate
        if emotion:
            audio_params["emotion"] = emotion
        if emotion_scale is not None:
            audio_params["emotion_scale"] = emotion_scale

        return {
            "user": {
                "uid": self.config.user_id,
            },
            "namespace": "BidirectionalTTS",
            "req_params": {
                "text": request.text,
                "speaker": voice.speaker,
                "audio_params": audio_params,
            },
        }


def _decode_audio(value: Any, provider_name: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ProviderRuntimeError(f"{provider_name} response did not include audio data")
    try:
        return base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise ProviderRuntimeError(f"{provider_name} returned invalid base64 audio") from exc


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
