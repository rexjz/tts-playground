# tts_playground

Local tools for planning TTS provider benchmark runs against the scripts in
`tts-benchmark-scripts`.

The first version is intentionally offline-only. It reads benchmark scripts,
builds script-level and utterance-level tasks, and writes dry-run JSON artifacts
that can be reviewed before connecting real TTS providers.

## Usage

Plan Chinese benchmark tasks with the dry-run provider:

```bash
uv run tts_playground plan --language zh-CN --provider dry_run
```

Plan a small sample:

```bash
uv run tts_playground plan --language zh-CN --limit 1
```

By default, output is written to:

```text
outputs/dry-run/<language>/
```

The generated files include:

- `manifest.json`: run summary for the selected provider and language
- `<script-id>/script.json`: one task for the whole script
- `<script-id>/utterances/<turn-index>.json`: one task per dialogue sentence

## Providers

Only `dry_run` is implemented in this version. The provider registry reserves
IDs for future adapters:

- `volcengine_seed_tts`
- `dashscope_cosyvoice`
- `minimax_speech`
- `tencent_tts`

Use `configs/providers.example.toml` as the non-secret configuration reference.
Real credentials should be supplied with environment variables when those
providers are implemented.

## Tests

```bash
uv run python -m unittest
```
