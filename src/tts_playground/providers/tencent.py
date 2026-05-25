from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from pathlib import Path
from typing import Callable, Any

from tts_playground.providers.base import (
    ProviderRuntimeError,
    SynthesisRequest,
    SynthesisResult,
)
from tts_playground.providers.config import TencentTtsConfig
from tts_playground.providers.http import HttpResponse, post_bytes


TENCENT_TTS_ENDPOINT = "https://tts.tencentcloudapi.com"
TENCENT_TTS_HOST = "tts.tencentcloudapi.com"
TENCENT_TTS_SERVICE = "tts"
TENCENT_TTS_VERSION = "2019-08-23"
TENCENT_TTS_ACTION = "TextToVoice"


class TencentTtsProvider:
    id = "tencent_tts"

    def __init__(
        self,
        config: TencentTtsConfig | None = None,
        *,
        post: Callable[..., HttpResponse] = post_bytes,
        now: Callable[[], int] | None = None,
    ) -> None:
        self.config = config or TencentTtsConfig.from_env()
        self._post = post
        self._now = now or (lambda: int(time.time()))

    @property
    def audio_file_extension(self) -> str:
        return self.config.audio_file_extension

    def synthesize(
        self,
        request: SynthesisRequest,
        *,
        output_path: Path,
    ) -> SynthesisResult:
        payload = self._build_payload(request)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        timestamp = self._now()
        headers = self._build_headers(body, timestamp)

        response = self._post(
            self.config.endpoint,
            body=body,
            headers=headers,
            timeout_seconds=self.config.timeout_seconds,
        )
        response_payload = _read_json_response(response)
        response_body = response_payload.get("Response")
        if not isinstance(response_body, dict):
            raise ProviderRuntimeError("Tencent Cloud TTS returned no Response object")
        if "Error" in response_body:
            error = response_body["Error"]
            raise ProviderRuntimeError(
                "Tencent Cloud TTS failed: "
                f"{error.get('Code')} {error.get('Message')}"
            )

        audio = _decode_audio(response_body.get("Audio"), "Tencent Cloud TTS")
        audio_path = Path(request.suggested_audio_path)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(audio)

        result_payload = {
            "kind": "utterance",
            "status": "synthesized",
            "request": request.to_dict(),
            "audio_path": audio_path.as_posix(),
            "provider_response": {
                "request_id": response_body.get("RequestId"),
                "session_id": response_body.get("SessionId"),
                "subtitles": response_body.get("Subtitles", []),
            },
        }
        _write_json(output_path, result_payload)

        return SynthesisResult(
            provider_id=self.id,
            status="synthesized",
            output_path=output_path.as_posix(),
            audio_path=audio_path.as_posix(),
            metadata={"request_id": response_body.get("RequestId")},
        )

    def _build_payload(self, request: SynthesisRequest) -> dict[str, Any]:
        voice = self.config.voice_for(request.speaker_slot)
        payload: dict[str, Any] = {
            "Text": request.text,
            "SessionId": str(uuid.uuid4()),
            "VoiceType": voice.voice_type,
            "Codec": self.config.codec,
            "SampleRate": self.config.sample_rate,
            "Speed": voice.speed if voice.speed is not None else self.config.speed,
            "Volume": voice.volume if voice.volume is not None else self.config.volume,
            "PrimaryLanguage": self.config.primary_language,
            "ModelType": self.config.model_type,
            "EnableSubtitle": self.config.enable_subtitle,
        }
        fast_voice_type = voice.fast_voice_type or self.config.fast_voice_type
        emotion_category = voice.emotion_category or self.config.emotion_category
        emotion_intensity = (
            voice.emotion_intensity
            if voice.emotion_intensity is not None
            else self.config.emotion_intensity
        )
        if fast_voice_type:
            payload["FastVoiceType"] = fast_voice_type
        if emotion_category:
            payload["EmotionCategory"] = emotion_category
        if emotion_intensity is not None:
            payload["EmotionIntensity"] = emotion_intensity
        return payload

    def _build_headers(self, body: bytes, timestamp: int) -> dict[str, str]:
        date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
        authorization = _tc3_authorization(
            secret_id=self.config.secret_id,
            secret_key=self.config.secret_key,
            date=date,
            timestamp=timestamp,
            payload=body,
        )
        return {
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": TENCENT_TTS_HOST,
            "X-TC-Action": TENCENT_TTS_ACTION,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": TENCENT_TTS_VERSION,
            "X-TC-Region": self.config.region,
        }


def _tc3_authorization(
    *,
    secret_id: str,
    secret_key: str,
    date: str,
    timestamp: int,
    payload: bytes,
) -> str:
    canonical_headers = (
        "content-type:application/json; charset=utf-8\n"
        f"host:{TENCENT_TTS_HOST}\n"
        f"x-tc-action:{TENCENT_TTS_ACTION.lower()}\n"
    )
    signed_headers = "content-type;host;x-tc-action"
    canonical_request = "\n".join(
        [
            "POST",
            "/",
            "",
            canonical_headers,
            signed_headers,
            hashlib.sha256(payload).hexdigest(),
        ]
    )
    credential_scope = f"{date}/{TENCENT_TTS_SERVICE}/tc3_request"
    string_to_sign = "\n".join(
        [
            "TC3-HMAC-SHA256",
            str(timestamp),
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    secret_date = _hmac_sha256(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = _hmac_sha256(secret_date, TENCENT_TTS_SERVICE)
    secret_signing = _hmac_sha256(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing,
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return (
        "TC3-HMAC-SHA256 "
        f"Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )


def _hmac_sha256(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _read_json_response(response: HttpResponse) -> dict[str, Any]:
    try:
        payload = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderRuntimeError("Tencent Cloud TTS returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ProviderRuntimeError("Tencent Cloud TTS returned a non-object response")
    return payload


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
