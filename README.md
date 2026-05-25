# tts_playground

Local tools for planning TTS provider benchmark runs against the scripts in
`tts-benchmark-scripts`.

It reads benchmark scripts, builds script-level and utterance-level tasks, and
writes provider outputs for repeatable TTS comparisons.

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
- `<script-id>/audio/<turn-index>-<provider>.mp3`: one audio file per sentence
- `<script-id>/podcast/<script-id>-<provider>.mp3`: concatenated podcast audio

By default, provider audio is concatenated after all utterances in a script
finish. If `ffmpeg` is available, it is used for stream-copy concatenation. If
not, MP3 output falls back to an internal binary concatenation path that removes
extra ID3 headers from later segments.

To skip podcast concatenation:

```bash
uv run tts_playground plan --provider volcengine_seed_tts --language zh-CN --limit 1 --concat-method none
```

## Providers

The implemented providers are:

- `dry_run`
- `volcengine_seed_tts`
- `tencent_tts`

The provider registry also reserves IDs for future adapters:

- `dashscope_cosyvoice`
- `minimax_speech`

Use `configs/providers.example.toml` as the non-secret configuration reference.
Real credentials are read from environment variables.

For two-person podcast scripts, voices are assigned by first appearance order
within each script:

- first distinct speaker name -> `speaker1`
- second distinct speaker name -> `speaker2`

The original `speakerName` text is preserved in manifests, but provider voice
selection only uses `speaker1` and `speaker2`.

### Volcengine Seed-TTS / Doubao Speech

This provider uses the Seed-TTS 2.0 V3 HTTP Chunked API:

```text
https://openspeech.bytedance.com/api/v3/tts/unidirectional
```

Required:

```bash
export VOLCENGINE_TTS_API_KEY="..."
export VOLCENGINE_TTS_RESOURCE_ID="seed-tts-2.0"
export VOLCENGINE_TTS_SPEAKER1_SPEAKER="speaker1 的火山音色 speaker id"
export VOLCENGINE_TTS_SPEAKER2_SPEAKER="speaker2 的火山音色 speaker id"
```

Optional:

```bash
export VOLCENGINE_TTS_ENDPOINT="https://openspeech.bytedance.com/api/v3/tts/unidirectional"
export VOLCENGINE_TTS_AUDIO_FORMAT="mp3"
export VOLCENGINE_TTS_SAMPLE_RATE="24000"
export VOLCENGINE_TTS_SPEECH_RATE="0"
export VOLCENGINE_TTS_LOUDNESS_RATE="0"
export VOLCENGINE_TTS_ENABLE_SUBTITLE="false"
export VOLCENGINE_TTS_USER_ID="tts_playground"
export VOLCENGINE_TTS_TIMEOUT_SECONDS="30"
export VOLCENGINE_TTS_SPEAKER1_SPEECH_RATE="0"
export VOLCENGINE_TTS_SPEAKER2_SPEECH_RATE="0"
```

Run a small sample:

```bash
uv run tts_playground plan --provider volcengine_seed_tts --language zh-CN --limit 1
```

### Tencent Cloud TTS

Required:

```bash
export TENCENTCLOUD_SECRET_ID="..."
export TENCENTCLOUD_SECRET_KEY="..."
export TENCENT_TTS_SPEAKER1_VOICE_TYPE="101001"
export TENCENT_TTS_SPEAKER2_VOICE_TYPE="101007"
```

Optional:

```bash
export TENCENTCLOUD_REGION="ap-beijing"
export TENCENT_TTS_CODEC="mp3"
export TENCENT_TTS_SAMPLE_RATE="16000"
export TENCENT_TTS_SPEED="0"
export TENCENT_TTS_VOLUME="0"
export TENCENT_TTS_PRIMARY_LANGUAGE="1"
export TENCENT_TTS_MODEL_TYPE="1"
export TENCENT_TTS_ENABLE_SUBTITLE="false"
export TENCENT_TTS_TIMEOUT_SECONDS="30"
export TENCENT_TTS_SPEAKER1_SPEED="0"
export TENCENT_TTS_SPEAKER2_SPEED="0"
```

Run a small sample:

```bash
uv run tts_playground plan --provider tencent_tts --language zh-CN --limit 1
```

## Tests

```bash
uv run python -m unittest
```
