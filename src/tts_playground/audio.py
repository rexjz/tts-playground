from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from tts_playground.providers.base import ProviderRuntimeError


@dataclass(frozen=True)
class AudioConcatResult:
    output_path: str
    input_count: int
    method: str


def concatenate_audio(
    audio_paths: list[Path],
    *,
    output_path: Path,
    audio_file_extension: str,
    method: str = "auto",
) -> AudioConcatResult:
    if not audio_paths:
        raise ProviderRuntimeError("Cannot concatenate audio: no input files")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_method = method.lower()
    if normalized_method == "none":
        raise ProviderRuntimeError("Cannot concatenate audio with method 'none'")

    if normalized_method == "auto":
        if shutil.which("ffmpeg"):
            return _concat_with_ffmpeg(audio_paths, output_path)
        normalized_method = "binary"

    if normalized_method == "ffmpeg":
        return _concat_with_ffmpeg(audio_paths, output_path)
    if normalized_method == "binary":
        return _concat_binary(
            audio_paths,
            output_path,
            audio_file_extension=audio_file_extension,
        )

    raise ProviderRuntimeError(f"Unknown audio concat method: {method}")


def _concat_with_ffmpeg(
    audio_paths: list[Path],
    output_path: Path,
) -> AudioConcatResult:
    if not shutil.which("ffmpeg"):
        raise ProviderRuntimeError("ffmpeg is required for concat method 'ffmpeg'")

    with tempfile.TemporaryDirectory() as tmp:
        list_path = Path(tmp) / "concat.txt"
        list_path.write_text(
            "".join(f"file '{_ffmpeg_escape(path)}'\n" for path in audio_paths),
            encoding="utf-8",
        )
        completed = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path.as_posix(),
                "-c",
                "copy",
                output_path.as_posix(),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    if completed.returncode != 0:
        raise ProviderRuntimeError(
            "ffmpeg audio concat failed: "
            + (completed.stderr.strip() or completed.stdout.strip())
        )

    return AudioConcatResult(
        output_path=output_path.as_posix(),
        input_count=len(audio_paths),
        method="ffmpeg",
    )


def _concat_binary(
    audio_paths: list[Path],
    output_path: Path,
    *,
    audio_file_extension: str,
) -> AudioConcatResult:
    extension = audio_file_extension.lower()
    if extension not in {"mp3", "pcm"}:
        raise ProviderRuntimeError(
            f"Binary audio concat only supports mp3 and pcm, got {extension!r}"
        )

    with output_path.open("wb") as output:
        for index, audio_path in enumerate(audio_paths):
            data = audio_path.read_bytes()
            if extension == "mp3" and index > 0:
                data = _strip_id3v2_header(data)
            output.write(data)

    return AudioConcatResult(
        output_path=output_path.as_posix(),
        input_count=len(audio_paths),
        method=f"binary-{extension}",
    )


def _strip_id3v2_header(data: bytes) -> bytes:
    if len(data) < 10 or data[:3] != b"ID3":
        return data
    tag_size = _read_synchsafe_int(data[6:10])
    header_size = 10 + tag_size
    if header_size > len(data):
        return data
    return data[header_size:]


def _read_synchsafe_int(raw: bytes) -> int:
    value = 0
    for byte in raw:
        value = (value << 7) | (byte & 0x7F)
    return value


def _ffmpeg_escape(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "'\\''")
