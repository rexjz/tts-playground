from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tts_playground.providers.base import ProviderConfigError, SynthesisRequest
from tts_playground.providers.config import (
    TencentTtsConfig,
    TencentTtsVoiceConfig,
    VolcengineSeedTtsConfig,
    VolcengineSeedTtsVoiceConfig,
)
from tts_playground.providers.http import HttpResponse
from tts_playground.providers.registry import get_provider, list_provider_ids
from tts_playground.providers.tencent import TencentTtsProvider
from tts_playground.providers.volcengine import VolcengineSeedTtsProvider


class ProviderRegistryTests(unittest.TestCase):
    def test_provider_ids_include_real_initial_providers(self) -> None:
        provider_ids = list_provider_ids()

        self.assertIn("volcengine_seed_tts", provider_ids)
        self.assertIn("tencent_tts", provider_ids)

    def test_real_providers_require_credentials_from_env(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ProviderConfigError):
                get_provider("volcengine_seed_tts")
            with self.assertRaises(ProviderConfigError):
                get_provider("tencent_tts")


class ProviderConfigTests(unittest.TestCase):
    def test_volcengine_config_from_env_requires_two_speaker_voice_ids(self) -> None:
        env = {
            "VOLCENGINE_TTS_API_KEY": "api-key",
            "VOLCENGINE_TTS_RESOURCE_ID": "seed-tts-2.0",
            "VOLCENGINE_TTS_SPEAKER1_SPEAKER": "voice-1",
            "VOLCENGINE_TTS_SPEAKER2_SPEAKER": "voice-2",
            "VOLCENGINE_TTS_SPEAKER2_SPEECH_RATE": "12",
        }

        with patch.dict("os.environ", env, clear=True):
            config = VolcengineSeedTtsConfig.from_env()

        self.assertEqual("voice-1", config.voice_for("speaker1").speaker)
        self.assertEqual("voice-2", config.voice_for("speaker2").speaker)
        self.assertEqual(12, config.voice_for("speaker2").speech_rate)
        self.assertEqual("***", config.redacted_dict()["api_key"])

    def test_tencent_config_from_env_requires_two_speaker_voice_ids(self) -> None:
        env = {
            "TENCENTCLOUD_SECRET_ID": "secret-id",
            "TENCENTCLOUD_SECRET_KEY": "secret-key",
            "TENCENT_TTS_SPEAKER1_VOICE_TYPE": "101001",
            "TENCENT_TTS_SPEAKER2_VOICE_TYPE": "101007",
            "TENCENT_TTS_SPEAKER2_SPEED": "1.25",
        }

        with patch.dict("os.environ", env, clear=True):
            config = TencentTtsConfig.from_env()

        self.assertEqual(101001, config.voice_for("speaker1").voice_type)
        self.assertEqual(101007, config.voice_for("speaker2").voice_type)
        self.assertEqual(1.25, config.voice_for("speaker2").speed)
        self.assertEqual("***", config.redacted_dict()["secret_key"])


class VolcengineProviderTests(unittest.TestCase):
    def test_synthesize_writes_audio_and_result_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            request = _request(tmp_path / "audio" / "0001.mp3")
            captured: dict[str, object] = {}

            def fake_post_stream(
                url: str,
                *,
                body: bytes,
                headers: dict[str, str],
                timeout_seconds: float,
            ) -> list[dict[str, object]]:
                captured["url"] = url
                captured["body"] = json.loads(body.decode("utf-8"))
                captured["headers"] = headers
                return [
                    {
                        "code": 0,
                        "message": "",
                        "data": base64.b64encode(b"volc-").decode("ascii"),
                    },
                    {
                        "code": 0,
                        "message": "",
                        "data": base64.b64encode(b"audio").decode("ascii"),
                    },
                    {
                        "code": 20000000,
                        "message": "ok",
                        "data": None,
                        "usage": {"text_words": 4},
                    },
                ]

            provider = VolcengineSeedTtsProvider(
                VolcengineSeedTtsConfig(
                    api_key="api-key",
                    resource_id="seed-tts-2.0",
                    speaker1=VolcengineSeedTtsVoiceConfig(speaker="voice-1"),
                    speaker2=VolcengineSeedTtsVoiceConfig(
                        speaker="voice-2",
                        speech_rate=12,
                    ),
                ),
                post_stream=fake_post_stream,
            )
            output_path = tmp_path / "utterance.json"

            result = provider.synthesize(request, output_path=output_path)

            self.assertEqual("synthesized", result.status)
            self.assertEqual(b"volc-audio", Path(result.audio_path or "").read_bytes())
            self.assertEqual("api-key", captured["headers"]["X-Api-Key"])
            self.assertEqual("seed-tts-2.0", captured["headers"]["X-Api-Resource-Id"])
            self.assertEqual("BidirectionalTTS", captured["body"]["namespace"])
            self.assertEqual("voice-2", captured["body"]["req_params"]["speaker"])
            self.assertEqual(
                12,
                captured["body"]["req_params"]["audio_params"]["speech_rate"],
            )
            self.assertEqual("测试文本", captured["body"]["req_params"]["text"])

            with output_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
            self.assertEqual(2, payload["provider_response"]["audio_chunk_count"])
            self.assertEqual(
                {"text_words": 4},
                payload["provider_response"]["usage"],
            )
            self.assertEqual(request.suggested_audio_path, payload["audio_path"])


class TencentProviderTests(unittest.TestCase):
    def test_synthesize_writes_audio_and_result_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            request = _request(tmp_path / "audio" / "0001.mp3")
            captured: dict[str, object] = {}

            def fake_post(
                url: str,
                *,
                body: bytes,
                headers: dict[str, str],
                timeout_seconds: float,
            ) -> HttpResponse:
                captured["url"] = url
                captured["body"] = json.loads(body.decode("utf-8"))
                captured["headers"] = headers
                return HttpResponse(
                    status_code=200,
                    body=json.dumps(
                        {
                            "Response": {
                                "Audio": base64.b64encode(b"tencent-audio").decode(
                                    "ascii"
                                ),
                                "SessionId": captured["body"]["SessionId"],
                                "RequestId": "tencent-req",
                                "Subtitles": [],
                            }
                        }
                    ).encode("utf-8"),
                )

            provider = TencentTtsProvider(
                TencentTtsConfig(
                    secret_id="secret-id",
                    secret_key="secret-key",
                    speaker1=TencentTtsVoiceConfig(voice_type=101001),
                    speaker2=TencentTtsVoiceConfig(voice_type=101007, speed=1.25),
                    codec="mp3",
                ),
                post=fake_post,
                now=lambda: 1_700_000_000,
            )
            output_path = tmp_path / "utterance.json"

            result = provider.synthesize(request, output_path=output_path)

            self.assertEqual("synthesized", result.status)
            self.assertEqual(b"tencent-audio", Path(result.audio_path or "").read_bytes())
            self.assertEqual("TextToVoice", captured["headers"]["X-TC-Action"])
            self.assertIn("TC3-HMAC-SHA256", captured["headers"]["Authorization"])
            self.assertEqual("测试文本", captured["body"]["Text"])
            self.assertEqual(101007, captured["body"]["VoiceType"])
            self.assertEqual(1.25, captured["body"]["Speed"])
            self.assertEqual("mp3", captured["body"]["Codec"])

            with output_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
            self.assertEqual("tencent-req", payload["provider_response"]["request_id"])
            self.assertEqual(request.suggested_audio_path, payload["audio_path"])


def _request(audio_path: Path) -> SynthesisRequest:
    return SynthesisRequest(
        provider_id="provider",
        language="zh-CN",
        script_id="script-id",
        turn_index=1,
        speaker_slot="speaker2",
        speaker_name="李教授",
        text="测试文本",
        tts_instructions="自然",
        suggested_audio_path=audio_path.as_posix(),
    )


if __name__ == "__main__":
    unittest.main()
