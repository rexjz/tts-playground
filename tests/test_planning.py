from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tts_playground.manifest import write_plan
from tts_playground.providers.base import SynthesisRequest, SynthesisResult
from tts_playground.providers.registry import get_provider
from tts_playground.scripts import iter_scripts, load_index


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "tts-benchmark-scripts"


class ScriptLoadingTests(unittest.TestCase):
    def test_load_index_filters_zh_cn_scripts(self) -> None:
        entries = load_index(SCRIPTS_DIR)
        zh_entries = [entry for entry in entries if entry.podcast_language == "zh-CN"]

        self.assertEqual(10, len(zh_entries))
        self.assertTrue(all(entry.file.startswith("zh-CN/") for entry in zh_entries))

    def test_load_script_discussion_sentences(self) -> None:
        scripts = iter_scripts(SCRIPTS_DIR, language="zh-CN", limit=1)

        self.assertEqual(1, len(scripts))
        self.assertEqual("zh-CN", scripts[0].podcast_language)
        self.assertGreater(len(scripts[0].discussion_sentences), 0)
        self.assertTrue(scripts[0].discussion_sentences[0].speaker_name)


class PlanningTests(unittest.TestCase):
    def test_write_plan_generates_script_and_utterance_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "outputs" / "dry-run"
            provider = get_provider("dry_run")

            manifest = write_plan(
                scripts_dir=SCRIPTS_DIR,
                out_dir=out_dir,
                language="zh-CN",
                provider=provider,
                limit=1,
            )

            self.assertEqual("dry_run", manifest["provider"])
            self.assertEqual("zh-CN", manifest["language"])
            self.assertEqual(1, manifest["script_count"])
            self.assertEqual(0, manifest["podcast_count"])

            script_entry = manifest["scripts"][0]
            self.assertIn(script_entry["id"], script_entry["script_task_path"])
            self.assertEqual(
                script_entry["utterance_count"],
                manifest["utterance_count"],
            )
            self.assertEqual("not_available", script_entry["podcast_audio"]["status"])

            manifest_path = out_dir / "zh-CN" / "manifest.json"
            script_path = Path(script_entry["script_task_path"])
            utterance_path = Path(script_entry["utterance_paths"][0])

            self.assertTrue(manifest_path.exists())
            self.assertTrue(script_path.exists())
            self.assertTrue(utterance_path.exists())
            self.assertIn(script_entry["id"], utterance_path.as_posix())
            self.assertTrue(utterance_path.name.endswith(".json"))

            with script_path.open("r", encoding="utf-8") as file:
                script_payload = json.load(file)
            with utterance_path.open("r", encoding="utf-8") as file:
                utterance_payload = json.load(file)

            self.assertEqual("script", script_payload["kind"])
            self.assertEqual("speaker1", script_payload["dialogue"][0]["speaker_slot"])
            self.assertIn("speaker_slots", script_payload)
            self.assertEqual("utterance", utterance_payload["kind"])
            self.assertEqual("planned", utterance_payload["status"])
            self.assertEqual("speaker1", utterance_payload["request"]["speaker_slot"])
            self.assertIsNone(utterance_payload.get("audio_path"))
            self.assertIn(
                "/audio/0001-dry_run.mp3",
                utterance_payload["request"]["suggested_audio_path"],
            )

    def test_write_plan_concatenates_provider_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "outputs" / "fake"
            provider = FakeAudioProvider()

            manifest = write_plan(
                scripts_dir=SCRIPTS_DIR,
                out_dir=out_dir,
                language="zh-CN",
                provider=provider,
                limit=1,
                concat_method="binary",
            )

            script_entry = manifest["scripts"][0]
            podcast_audio = script_entry["podcast_audio"]
            podcast_path = Path(podcast_audio["path"])

            self.assertEqual(1, manifest["podcast_count"])
            self.assertEqual("synthesized", podcast_audio["status"])
            self.assertEqual("binary-mp3", podcast_audio["method"])
            self.assertEqual(script_entry["utterance_count"], podcast_audio["input_count"])
            self.assertTrue(podcast_path.exists())

            podcast_bytes = podcast_path.read_bytes()
            self.assertIn(b"audio-0001", podcast_bytes)
            self.assertIn(
                f"audio-{script_entry['utterance_count']:04d}".encode("ascii"),
                podcast_bytes,
            )


class FakeAudioProvider:
    id = "fake_audio"
    audio_file_extension = "mp3"

    def synthesize(
        self,
        request: SynthesisRequest,
        *,
        output_path: Path,
    ) -> SynthesisResult:
        audio_path = Path(request.suggested_audio_path)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(_fake_mp3(f"audio-{request.turn_index:04d}"))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(
                {
                    "kind": "utterance",
                    "status": "synthesized",
                    "request": request.to_dict(),
                    "audio_path": audio_path.as_posix(),
                },
                file,
                ensure_ascii=False,
                indent=2,
            )
            file.write("\n")

        return SynthesisResult(
            provider_id=self.id,
            status="synthesized",
            output_path=output_path.as_posix(),
            audio_path=audio_path.as_posix(),
        )


def _fake_mp3(label: str) -> bytes:
    id3_header = b"ID3\x04\x00\x00\x00\x00\x00\x00"
    return id3_header + b"\xff\xfb" + label.encode("ascii")


if __name__ == "__main__":
    unittest.main()
