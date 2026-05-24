"""Tools for planning TTS provider benchmark runs."""

__all__ = ["main"]


def main() -> None:
    from tts_playground.cli import main as cli_main

    raise SystemExit(cli_main())
