from __future__ import annotations

import codecs
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterator

from tts_playground.providers.base import ProviderRuntimeError


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    body: bytes


def post_bytes(
    url: str,
    *,
    body: bytes,
    headers: dict[str, str],
    timeout_seconds: float,
) -> HttpResponse:
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return HttpResponse(
                status_code=response.status,
                body=response.read(),
            )
    except urllib.error.HTTPError as exc:
        raise ProviderRuntimeError(
            f"HTTP {exc.code} from {url}: {exc.read().decode('utf-8', 'replace')}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ProviderRuntimeError(f"Failed to call {url}: {exc}") from exc


def post_json_stream(
    url: str,
    *,
    body: bytes,
    headers: dict[str, str],
    timeout_seconds: float,
) -> Iterator[dict[str, Any]]:
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    decoder = codecs.getincrementaldecoder("utf-8")()
    json_decoder = json.JSONDecoder()
    buffer = ""
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                buffer += decoder.decode(chunk)
                buffer, items = _decode_json_items(buffer, json_decoder)
                yield from items

            buffer += decoder.decode(b"", final=True)
            buffer, items = _decode_json_items(buffer, json_decoder)
            yield from items
    except urllib.error.HTTPError as exc:
        raise ProviderRuntimeError(
            f"HTTP {exc.code} from {url}: {exc.read().decode('utf-8', 'replace')}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ProviderRuntimeError(f"Failed to call {url}: {exc}") from exc

    if buffer.strip():
        raise ProviderRuntimeError(f"Response from {url} ended with invalid JSON")


def _decode_json_items(
    buffer: str,
    json_decoder: json.JSONDecoder,
) -> tuple[str, list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    while True:
        buffer = buffer.lstrip()
        if not buffer:
            return "", items
        try:
            item, end = json_decoder.raw_decode(buffer)
        except json.JSONDecodeError:
            return buffer, items
        if not isinstance(item, dict):
            raise ProviderRuntimeError("Streaming response item was not a JSON object")
        items.append(item)
        buffer = buffer[end:]
