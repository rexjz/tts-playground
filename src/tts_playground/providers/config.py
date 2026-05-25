from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Literal

from tts_playground.providers.base import ProviderConfigError


SpeakerSlot = Literal["speaker1", "speaker2"]

VOLCENGINE_TTS_ENDPOINT = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
TENCENT_TTS_ENDPOINT = "https://tts.tencentcloudapi.com"


@dataclass(frozen=True)
class DryRunConfig:
    provider_id: str = "dry_run"
    audio_file_extension: str = "mp3"

    def redacted_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VolcengineSeedTtsVoiceConfig:
    speaker: str
    speech_rate: int | None = None
    loudness_rate: int | None = None
    emotion: str | None = None
    emotion_scale: int | None = None

    @classmethod
    def from_env(cls, prefix: str) -> "VolcengineSeedTtsVoiceConfig":
        return cls(
            speaker=_required_env(f"{prefix}_SPEAKER"),
            speech_rate=_env_optional_int(f"{prefix}_SPEECH_RATE"),
            loudness_rate=_env_optional_int(f"{prefix}_LOUDNESS_RATE"),
            emotion=os.getenv(f"{prefix}_EMOTION") or None,
            emotion_scale=_env_optional_int(f"{prefix}_EMOTION_SCALE"),
        )


@dataclass(frozen=True)
class VolcengineSeedTtsConfig:
    api_key: str
    resource_id: str
    speaker1: VolcengineSeedTtsVoiceConfig
    speaker2: VolcengineSeedTtsVoiceConfig
    endpoint: str = VOLCENGINE_TTS_ENDPOINT
    audio_format: str = "mp3"
    sample_rate: int = 24000
    bit_rate: int | None = None
    speech_rate: int = 0
    loudness_rate: int = 0
    emotion: str | None = None
    emotion_scale: int | None = None
    enable_subtitle: bool = False
    user_id: str = "tts_playground"
    timeout_seconds: float = 30.0
    provider_id: str = "volcengine_seed_tts"

    @classmethod
    def from_env(cls) -> "VolcengineSeedTtsConfig":
        return cls(
            api_key=_required_env("VOLCENGINE_TTS_API_KEY"),
            resource_id=os.getenv("VOLCENGINE_TTS_RESOURCE_ID", "seed-tts-2.0"),
            speaker1=VolcengineSeedTtsVoiceConfig.from_env(
                "VOLCENGINE_TTS_SPEAKER1"
            ),
            speaker2=VolcengineSeedTtsVoiceConfig.from_env(
                "VOLCENGINE_TTS_SPEAKER2"
            ),
            endpoint=os.getenv("VOLCENGINE_TTS_ENDPOINT", VOLCENGINE_TTS_ENDPOINT),
            audio_format=os.getenv("VOLCENGINE_TTS_AUDIO_FORMAT", "mp3"),
            sample_rate=_env_int("VOLCENGINE_TTS_SAMPLE_RATE", 24000),
            bit_rate=_env_optional_int("VOLCENGINE_TTS_BIT_RATE"),
            speech_rate=_env_int("VOLCENGINE_TTS_SPEECH_RATE", 0),
            loudness_rate=_env_int("VOLCENGINE_TTS_LOUDNESS_RATE", 0),
            emotion=os.getenv("VOLCENGINE_TTS_EMOTION") or None,
            emotion_scale=_env_optional_int("VOLCENGINE_TTS_EMOTION_SCALE"),
            enable_subtitle=_env_bool("VOLCENGINE_TTS_ENABLE_SUBTITLE", False),
            user_id=os.getenv("VOLCENGINE_TTS_USER_ID", "tts_playground"),
            timeout_seconds=_env_float("VOLCENGINE_TTS_TIMEOUT_SECONDS", 30.0),
        )

    @property
    def audio_file_extension(self) -> str:
        if self.audio_format == "ogg_opus":
            return "ogg"
        return self.audio_format

    def voice_for(self, speaker_slot: str) -> VolcengineSeedTtsVoiceConfig:
        if speaker_slot == "speaker1":
            return self.speaker1
        if speaker_slot == "speaker2":
            return self.speaker2
        raise ProviderConfigError(f"Unknown speaker slot: {speaker_slot}")

    def redacted_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["api_key"] = "***"
        return payload


@dataclass(frozen=True)
class TencentTtsVoiceConfig:
    voice_type: int
    speed: float | None = None
    volume: float | None = None
    fast_voice_type: str | None = None
    emotion_category: str | None = None
    emotion_intensity: int | None = None

    @classmethod
    def from_env(cls, prefix: str) -> "TencentTtsVoiceConfig":
        return cls(
            voice_type=_required_env_int(f"{prefix}_VOICE_TYPE"),
            speed=_env_optional_float(f"{prefix}_SPEED"),
            volume=_env_optional_float(f"{prefix}_VOLUME"),
            fast_voice_type=os.getenv(f"{prefix}_FAST_VOICE_TYPE") or None,
            emotion_category=os.getenv(f"{prefix}_EMOTION_CATEGORY") or None,
            emotion_intensity=_env_optional_int(f"{prefix}_EMOTION_INTENSITY"),
        )


@dataclass(frozen=True)
class TencentTtsConfig:
    secret_id: str
    secret_key: str
    speaker1: TencentTtsVoiceConfig
    speaker2: TencentTtsVoiceConfig
    region: str = "ap-beijing"
    endpoint: str = TENCENT_TTS_ENDPOINT
    codec: str = "mp3"
    sample_rate: int = 16000
    speed: float = 0.0
    volume: float = 0.0
    primary_language: int = 1
    model_type: int = 1
    enable_subtitle: bool = False
    timeout_seconds: float = 30.0
    fast_voice_type: str | None = None
    emotion_category: str | None = None
    emotion_intensity: int | None = None
    provider_id: str = "tencent_tts"

    @classmethod
    def from_env(cls) -> "TencentTtsConfig":
        return cls(
            secret_id=_required_env("TENCENTCLOUD_SECRET_ID"),
            secret_key=_required_env("TENCENTCLOUD_SECRET_KEY"),
            speaker1=TencentTtsVoiceConfig.from_env("TENCENT_TTS_SPEAKER1"),
            speaker2=TencentTtsVoiceConfig.from_env("TENCENT_TTS_SPEAKER2"),
            region=os.getenv("TENCENTCLOUD_REGION", "ap-beijing"),
            endpoint=os.getenv("TENCENT_TTS_ENDPOINT", TENCENT_TTS_ENDPOINT),
            codec=os.getenv("TENCENT_TTS_CODEC", "mp3"),
            sample_rate=_env_int("TENCENT_TTS_SAMPLE_RATE", 16000),
            speed=_env_float("TENCENT_TTS_SPEED", 0.0),
            volume=_env_float("TENCENT_TTS_VOLUME", 0.0),
            primary_language=_env_int("TENCENT_TTS_PRIMARY_LANGUAGE", 1),
            model_type=_env_int("TENCENT_TTS_MODEL_TYPE", 1),
            enable_subtitle=_env_bool("TENCENT_TTS_ENABLE_SUBTITLE", False),
            timeout_seconds=_env_float("TENCENT_TTS_TIMEOUT_SECONDS", 30.0),
            fast_voice_type=os.getenv("TENCENT_TTS_FAST_VOICE_TYPE") or None,
            emotion_category=os.getenv("TENCENT_TTS_EMOTION_CATEGORY") or None,
            emotion_intensity=_env_optional_int("TENCENT_TTS_EMOTION_INTENSITY"),
        )

    @property
    def audio_file_extension(self) -> str:
        return self.codec

    def voice_for(self, speaker_slot: str) -> TencentTtsVoiceConfig:
        if speaker_slot == "speaker1":
            return self.speaker1
        if speaker_slot == "speaker2":
            return self.speaker2
        raise ProviderConfigError(f"Unknown speaker slot: {speaker_slot}")

    def redacted_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["secret_id"] = "***"
        payload["secret_key"] = "***"
        return payload


@dataclass(frozen=True)
class DashScopeCosyVoiceConfig:
    api_key: str
    speaker1_voice: str
    speaker2_voice: str
    provider_id: str = "dashscope_cosyvoice"


@dataclass(frozen=True)
class MiniMaxSpeechConfig:
    api_key: str
    group_id: str
    speaker1_voice: str
    speaker2_voice: str
    provider_id: str = "minimax_speech"


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ProviderConfigError(f"Missing required environment variable: {name}")
    return value


def _required_env_int(name: str) -> int:
    value = _required_env(name)
    try:
        return int(value)
    except ValueError as exc:
        raise ProviderConfigError(f"{name} must be an integer") from exc


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ProviderConfigError(f"{name} must be an integer") from exc


def _env_optional_int(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ProviderConfigError(f"{name} must be an integer") from exc


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ProviderConfigError(f"{name} must be a number") from exc


def _env_optional_float(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ProviderConfigError(f"{name} must be a number") from exc


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}
