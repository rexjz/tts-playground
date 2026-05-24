from __future__ import annotations

import json
from pathlib import Path

from tts_playground.providers.base import SynthesisRequest, SynthesisResult


class DryRunProvider:
    id = "dry_run"

    def synthesize(
        self,
        request: SynthesisRequest,
        *,
        output_path: Path,
    ) -> SynthesisResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "kind": "utterance",
            "status": "planned",
            "request": request.to_dict(),
        }
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")

        return SynthesisResult(
            provider_id=self.id,
            status="planned",
            output_path=output_path.as_posix(),
            audio_path=None,
        )
