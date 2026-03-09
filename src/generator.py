"""Gemini API request and response parsing."""

from __future__ import annotations

import json
from typing import Any

import requests

from src.config import GENERATE_CONTENT_API, TIMEOUT_SECONDS


class GeminiRequestError(RuntimeError):
    """Structured error surfaced to UI for troubleshooting."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _build_url(api_key: str, model_id: str) -> str:
    return (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_id}:{GENERATE_CONTENT_API}?key={api_key}"
    )


def _safe_preview(response: requests.Response, max_chars: int = 500) -> str:
    text = (response.text or "").strip()
    if not text:
        return ""
    text = " ".join(text.split())
    return text[:max_chars]


def _try_parse_json(response: requests.Response) -> Any:
    """Parse standard JSON first, then fall back to line-by-line JSON chunks."""
    try:
        return response.json()
    except ValueError:
        raw = response.text.strip()
        if not raw:
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            chunks = []
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data:"):
                    line = line.replace("data:", "", 1).strip()
                line = line.rstrip(",")
                if line in {"[", "]"}:
                    continue
                try:
                    chunks.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return chunks if chunks else None


def _extract_error_message(payload: Any) -> str:
    blocks = payload if isinstance(payload, list) else [payload]
    for block in blocks:
        if not isinstance(block, dict):
            continue
        err = block.get("error")
        if isinstance(err, dict):
            return err.get("message", "Unknown Gemini API error.")
    return "Unknown Gemini API error."


def _extract_text(payload: Any) -> str:
    """Extract generated text from dict or list Gemini responses."""
    blocks = payload if isinstance(payload, list) else [payload]
    collected: list[str] = []

    for block in blocks:
        if not isinstance(block, dict):
            continue
        if "error" in block:
            raise GeminiRequestError(_extract_error_message(block), {"error_type": "api_error_payload"})

        candidates = block.get("candidates", [])
        if not isinstance(candidates, list):
            continue

        for candidate in candidates:
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            if not isinstance(parts, list):
                continue
            for part in parts:
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    collected.append(text.strip())

    return "\n".join(collected).strip()


def generate_answer(api_key: str, prompt: str, model_id: str) -> str:
    """Send one prompt variant to Gemini and return plain text output."""
    if not api_key.strip():
        raise GeminiRequestError("Gemini API key is missing.", {"error_type": "validation"})
    if not prompt.strip():
        raise GeminiRequestError("Prompt text is empty.", {"error_type": "validation"})

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "thinkingConfig": {
                "thinkingLevel": "MINIMAL",
            }
        },
    }

    try:
        response = requests.post(
            _build_url(api_key=api_key, model_id=model_id),
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise GeminiRequestError(
            f"Gemini request timed out after {TIMEOUT_SECONDS} seconds.",
            {
                "error_type": "timeout",
                "timeout_seconds": TIMEOUT_SECONDS,
                "suggestions": [
                    "Retry the same request once.",
                    "Use a shorter query to reduce generation time.",
                    "Check network stability and try again.",
                ],
            },
        ) from exc
    except requests.RequestException as exc:
        raise GeminiRequestError(
            "Could not reach Gemini API.",
            {
                "error_type": "network_error",
                "raw_error": str(exc),
                "suggestions": [
                    "Check internet connection.",
                    "Verify firewall or proxy settings.",
                    "Retry in a few seconds.",
                ],
            },
        ) from exc

    parsed = _try_parse_json(response)

    if response.status_code >= 400:
        message = _extract_error_message(parsed)
        details: dict[str, Any] = {
            "error_type": "http_error",
            "status_code": response.status_code,
            "api_message": message,
        }
        preview = _safe_preview(response)
        if preview:
            details["response_preview"] = preview
        raise GeminiRequestError(f"Gemini API error ({response.status_code}): {message}", details)

    if parsed is None:
        raise GeminiRequestError(
            "Gemini returned an empty or non-JSON response.",
            {
                "error_type": "parse_error",
                "status_code": response.status_code,
                "response_preview": _safe_preview(response),
            },
        )

    text = _extract_text(parsed)
    if not text:
        raise GeminiRequestError(
            "Gemini returned no text content for this prompt.",
            {"error_type": "empty_text_response"},
        )

    return text
