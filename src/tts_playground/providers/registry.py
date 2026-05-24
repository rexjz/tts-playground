from __future__ import annotations

from tts_playground.providers.base import Provider
from tts_playground.providers.dry_run import DryRunProvider

RESERVED_PROVIDER_IDS = (
    "dry_run",
    "volcengine_seed_tts",
    "dashscope_cosyvoice",
    "minimax_speech",
    "tencent_tts",
)


def list_provider_ids() -> tuple[str, ...]:
    return RESERVED_PROVIDER_IDS


def get_provider(provider_id: str) -> Provider:
    if provider_id == DryRunProvider.id:
        return DryRunProvider()
    if provider_id in RESERVED_PROVIDER_IDS:
        raise NotImplementedError(
            f"Provider {provider_id!r} is reserved but not implemented yet. "
            "Use 'dry_run' for this version."
        )
    raise ValueError(
        f"Unknown provider {provider_id!r}. "
        f"Known provider ids: {', '.join(RESERVED_PROVIDER_IDS)}"
    )
