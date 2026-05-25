from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from tts_playground.manifest import write_plan
from tts_playground.providers.base import ProviderError
from tts_playground.providers.registry import get_provider, list_provider_ids


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "plan":
        return _plan(args)

    parser.print_help()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tts_playground",
        description="Plan TTS provider benchmark runs from local script fixtures.",
    )
    subparsers = parser.add_subparsers(dest="command")

    plan_parser = subparsers.add_parser(
        "plan",
        help="Generate benchmark manifest, task files, and provider outputs.",
    )
    plan_parser.add_argument("--language", default="zh-CN")
    plan_parser.add_argument(
        "--provider",
        default="dry_run",
        choices=list_provider_ids(),
    )
    plan_parser.add_argument("--limit", type=_positive_int)
    plan_parser.add_argument(
        "--scripts-dir",
        default="tts-benchmark-scripts",
        type=Path,
    )
    plan_parser.add_argument(
        "--out",
        default=None,
        type=Path,
    )
    plan_parser.add_argument(
        "--concat-method",
        default="auto",
        choices=("auto", "ffmpeg", "binary", "none"),
        help="How to concatenate utterance audio into a podcast file.",
    )

    return parser


def _plan(args: argparse.Namespace) -> int:
    try:
        provider = get_provider(args.provider)
    except (NotImplementedError, ValueError, ProviderError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out_dir = args.out or _default_out_dir(provider.id)
    manifest = write_plan(
        scripts_dir=args.scripts_dir,
        out_dir=out_dir,
        language=args.language,
        provider=provider,
        limit=args.limit,
        concat_method=args.concat_method,
    )
    print(
        "Planned "
        f"{manifest['script_count']} scripts and "
        f"{manifest['utterance_count']} utterances for "
        f"{manifest['provider']} -> {manifest['output_dir']}"
    )
    return 0


def _positive_int(raw: str) -> int:
    value = int(raw)
    if value < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return value


def _default_out_dir(provider_id: str) -> Path:
    if provider_id == "dry_run":
        return Path("outputs/dry-run")
    return Path("outputs") / provider_id
