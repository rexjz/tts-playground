from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ScriptIndexEntry:
    id: str
    dwd_id: str
    title: str
    podcast_language: str
    character_ids: tuple[str, ...]
    script_storage_key: str
    duration_seconds: int | None
    generated_at: str
    file: str


@dataclass(frozen=True)
class DialogueTurn:
    speaker_name: str
    content: str
    tts_instructions: str


@dataclass(frozen=True)
class BenchmarkScript:
    id: str
    dwd_id: str
    title: str
    abstract: str
    podcast_language: str
    character_ids: tuple[str, ...]
    script_storage_key: str
    generated_at: str
    source_file: str
    discussion_sentences: tuple[DialogueTurn, ...]


def load_index(scripts_dir: Path) -> list[ScriptIndexEntry]:
    index_path = scripts_dir / "index.json"
    raw_entries = _read_json(index_path)
    if not isinstance(raw_entries, list):
        raise ValueError(f"Expected {index_path} to contain a JSON array")

    return [_parse_index_entry(entry, index_path) for entry in raw_entries]


def load_script(scripts_dir: Path, entry: ScriptIndexEntry) -> BenchmarkScript:
    script_path = scripts_dir / entry.file
    raw_script = _read_json(script_path)
    if not isinstance(raw_script, dict):
        raise ValueError(f"Expected {script_path} to contain a JSON object")

    discussion = _require_list(raw_script, "discussionSentences", script_path)
    turns = tuple(_parse_turn(turn, script_path) for turn in discussion)

    return BenchmarkScript(
        id=entry.id,
        dwd_id=entry.dwd_id,
        title=_require_str(raw_script, "title", script_path),
        abstract=_require_str(raw_script, "abstract", script_path),
        podcast_language=entry.podcast_language,
        character_ids=entry.character_ids,
        script_storage_key=entry.script_storage_key,
        generated_at=entry.generated_at,
        source_file=entry.file,
        discussion_sentences=turns,
    )


def iter_scripts(
    scripts_dir: Path,
    *,
    language: str,
    limit: int | None = None,
) -> list[BenchmarkScript]:
    entries = [
        entry
        for entry in load_index(scripts_dir)
        if entry.podcast_language == language
    ]
    if limit is not None:
        entries = entries[:limit]
    return [load_script(scripts_dir, entry) for entry in entries]


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Missing benchmark script file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def _parse_index_entry(raw: Any, source: Path) -> ScriptIndexEntry:
    if not isinstance(raw, dict):
        raise ValueError(f"Expected entries in {source} to be JSON objects")

    return ScriptIndexEntry(
        id=_require_str(raw, "id", source),
        dwd_id=_require_str(raw, "dwdId", source),
        title=_require_str(raw, "title", source),
        podcast_language=_require_str(raw, "podcastLanguage", source),
        character_ids=tuple(_require_list(raw, "characterIds", source)),
        script_storage_key=_require_str(raw, "scriptStorageKey", source),
        duration_seconds=raw.get("durationSeconds"),
        generated_at=_require_str(raw, "generatedAt", source),
        file=_require_str(raw, "file", source),
    )


def _parse_turn(raw: Any, source: Path) -> DialogueTurn:
    if not isinstance(raw, dict):
        raise ValueError(f"Expected discussionSentences in {source} to be objects")

    return DialogueTurn(
        speaker_name=_require_str(raw, "speakerName", source),
        content=_require_str(raw, "content", source),
        tts_instructions=_require_str(raw, "ttsInstructions", source),
    )


def _require_str(raw: dict[str, Any], key: str, source: Path) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Expected {key!r} in {source} to be a string")
    return value


def _require_list(raw: dict[str, Any], key: str, source: Path) -> list[Any]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Expected {key!r} in {source} to be a list")
    return value
