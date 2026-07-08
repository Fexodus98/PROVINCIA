"""Shared Mistral client helpers: vision chat with JSON mode, OCR API, retries.

The free Experiment plan is rate-limited (~1 request/second), so every call
retries on 429/5xx with exponential backoff.
"""
from __future__ import annotations

import base64
import time
from pathlib import Path

from mistralai.client import Mistral

from config import MISTRAL_API_KEY

RETRY_DELAYS = [5, 15, 35, 60]


def get_client() -> Mistral:
    if not MISTRAL_API_KEY:
        raise SystemExit(
            "MISTRAL_API_KEY is not set. In PowerShell run:\n"
            '  setx MISTRAL_API_KEY "your_key_here"\n'
            "then open a new terminal."
        )
    return Mistral(api_key=MISTRAL_API_KEY)


def image_data_url(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _retryable(exc: Exception) -> bool:
    text = str(exc)
    return "429" in text or "rate" in text.lower() or "500" in text or "502" in text or "503" in text


def _with_retries(fn):
    last_exc: Exception | None = None
    for attempt, delay in enumerate([0] + RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if not _retryable(exc):
                raise
            print(f"  [RETRY {attempt + 1}/{len(RETRY_DELAYS)}] {type(exc).__name__}: {str(exc)[:120]}")
    raise last_exc  # type: ignore[misc]


def chat_with_image(
    client: Mistral,
    model: str,
    user_text: str,
    image_path: Path | None = None,
    system: str | None = None,
    max_tokens: int = 32768,
    json_mode: bool = True,
) -> str:
    content: list[dict] = [{"type": "text", "text": user_text}]
    if image_path is not None:
        content.append({"type": "image_url", "image_url": image_data_url(image_path)})
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": content})

    def call():
        return client.chat.complete(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.0,
            response_format={"type": "json_object"} if json_mode else None,
        )

    response = _with_retries(call)
    text = response.choices[0].message.content
    if not text:
        raise RuntimeError("empty model response")
    return text


def ocr_image(client: Mistral, model: str, image_path: Path) -> str:
    def call():
        return client.ocr.process(
            model=model,
            document={"type": "image_url", "image_url": image_data_url(image_path)},
        )

    result = _with_retries(call)
    return "\n\n".join(page.markdown for page in result.pages)
