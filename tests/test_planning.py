from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tts_playground.manifest import write_plan
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

            script_entry = manifest["scripts"][0]
            self.assertIn(script_entry["id"], script_entry["script_task_path"])
            self.assertEqual(
                script_entry["utterance_count"],
                manifest["utterance_count"],
            )

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
            self.assertEqual("utterance", utterance_payload["kind"])
            self.assertEqual("planned", utterance_payload["status"])
            self.assertIsNone(utterance_payload.get("audio_path"))
            self.assertIn(
                "/audio/0001-dry_run.mp3",
                utterance_payload["request"]["suggested_audio_path"],
            )


if __name__ == "__main__":
    unittest.main()
