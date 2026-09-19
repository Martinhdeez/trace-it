"""Literal Gemini image transcription shared by experiments and the configured committee."""

import base64
import re
from pathlib import Path

import httpx

from app.common import prompts

from .errors import ProviderUnavailable
from .journal import record_response, retry_after

PROMPTS = Path(__file__).parents[1] / "prompts"
PROMPT = prompts.read(PROMPTS, "transcribe-invoice")
GENERATION = {"temperature": 0, "maxOutputTokens": 4096}


def request_body(images: list[bytes], prompt: str = PROMPT) -> dict:
    return {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
                + [
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": base64.b64encode(image).decode(),
                        }
                    }
                    for image in images
                ],
            }
        ],
        "generationConfig": dict(GENERATION),
    }


def generate(
    client: httpx.Client,
    model: str,
    key: str,
    images: list[bytes],
    *,
    before_request=None,
    prompt: str = PROMPT,
    max_tokens: int | None = None,
) -> dict:
    if not re.fullmatch(r"gemini-[a-zA-Z0-9._-]+", model):
        raise ValueError("Expected a Gemini model identifier, without a URL or models/ prefix")
    if before_request is not None:
        before_request()
    body = request_body(images, prompt)
    if max_tokens is not None:
        body["generationConfig"]["maxOutputTokens"] = max_tokens
    response = client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key},
        json=body,
    )
    record_response("gemini", response.status_code, retry_after_s=retry_after(response))
    if not response.is_success:
        raise ProviderUnavailable(f"Gemini returned HTTP {response.status_code}")
    result = response.json()
    record_response("gemini", response.status_code, result)
    if not isinstance(result, dict):
        raise ProviderUnavailable("Invalid Gemini response")
    return result


def output_text(response: dict) -> str:
    candidates = response.get("candidates", [])
    if not candidates or candidates[0].get("finishReason") != "STOP":
        raise ProviderUnavailable("Gemini output missing, blocked or truncated; keep for review")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "\n".join(p["text"] for p in parts if "text" in p and not p.get("thought"))
    if not text.strip() or len(text) > 50_000:
        raise ProviderUnavailable("Empty or oversized Gemini transcript")
    return text
