from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tts_playground.providers.base import Provider, SynthesisRequest
from tts_playground.scripts import BenchmarkScript, iter_scripts


def write_plan(
    *,
    scripts_dir: Path,
    out_dir: Path,
    language: str,
    provider: Provider,
    limit: int | None = None,
) -> dict[str, Any]:
    scripts = iter_scripts(scripts_dir, language=language, limit=limit)
    language_out_dir = out_dir / language
    language_out_dir.mkdir(parents=True, exist_ok=True)

    manifest_scripts: list[dict[str, Any]] = []
    utterance_count = 0
    audio_file_extension = provider.audio_file_extension

    for script in scripts:
        speaker_slots = _assign_speaker_slots(script)
        script_dir = language_out_dir / script.id
        script_dir.mkdir(parents=True, exist_ok=True)

        script_task_path = script_dir / "script.json"
        _write_json(
            script_task_path,
            _build_script_task(script, provider.id, speaker_slots),
        )

        utterance_paths: list[str] = []
        for turn_index, turn in enumerate(script.discussion_sentences, start=1):
            utterance_path = script_dir / "utterances" / f"{turn_index:04d}.json"
            suggested_audio_path = (
                script_dir
                / "audio"
                / f"{turn_index:04d}-{provider.id}.{audio_file_extension}"
            )
            request = SynthesisRequest(
                provider_id=provider.id,
                language=script.podcast_language,
                script_id=script.id,
                turn_index=turn_index,
                speaker_slot=speaker_slots[turn.speaker_name],
                speaker_name=turn.speaker_name,
                text=turn.content,
                tts_instructions=turn.tts_instructions,
                suggested_audio_path=suggested_audio_path.as_posix(),
                metadata={
                    "title": script.title,
                    "source_file": script.source_file,
                    "speaker_slot": speaker_slots[turn.speaker_name],
                },
            )
            provider.synthesize(request, output_path=utterance_path)
            utterance_paths.append(utterance_path.as_posix())
            utterance_count += 1

        manifest_scripts.append(
            {
                "id": script.id,
                "title": script.title,
                "language": script.podcast_language,
                "source_file": script.source_file,
                "script_task_path": script_task_path.as_posix(),
                "utterance_count": len(script.discussion_sentences),
                "utterance_paths": utterance_paths,
                "speaker_slots": speaker_slots,
            }
        )

    manifest = {
        "provider": provider.id,
        "language": language,
        "scripts_dir": scripts_dir.as_posix(),
        "output_dir": language_out_dir.as_posix(),
        "script_count": len(scripts),
        "utterance_count": utterance_count,
        "scripts": manifest_scripts,
    }
    _write_json(language_out_dir / "manifest.json", manifest)
    return manifest


def _build_script_task(
    script: BenchmarkScript,
    provider_id: str,
    speaker_slots: dict[str, str],
) -> dict[str, Any]:
    return {
        "kind": "script",
        "status": "planned",
        "provider": provider_id,
        "script_id": script.id,
        "dwd_id": script.dwd_id,
        "language": script.podcast_language,
        "title": script.title,
        "abstract": script.abstract,
        "character_ids": list(script.character_ids),
        "script_storage_key": script.script_storage_key,
        "generated_at": script.generated_at,
        "source_file": script.source_file,
        "speaker_slots": speaker_slots,
        "dialogue": [
            {
                "turn_index": index,
                "speaker_slot": speaker_slots[turn.speaker_name],
                "speaker_name": turn.speaker_name,
                "content": turn.content,
                "tts_instructions": turn.tts_instructions,
            }
            for index, turn in enumerate(script.discussion_sentences, start=1)
        ],
    }


def _assign_speaker_slots(script: BenchmarkScript) -> dict[str, str]:
    slots = ("speaker1", "speaker2")
    speaker_slots: dict[str, str] = {}
    for turn in script.discussion_sentences:
        if turn.speaker_name in speaker_slots:
            continue
        if len(speaker_slots) >= len(slots):
            raise ValueError(
                f"Script {script.id} has more than two speakers; "
                "speaker-slot assignment only supports speaker1 and speaker2"
            )
        speaker_slots[turn.speaker_name] = slots[len(speaker_slots)]
    return speaker_slots


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
