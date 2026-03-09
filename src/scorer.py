"""Lightweight heuristic scoring for generated answers."""

from __future__ import annotations

import re
from typing import Any

from src.config import SCORE_WEIGHTS

STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "as",
    "is",
    "are",
    "be",
    "by",
    "that",
    "this",
    "it",
    "from",
    "at",
    "your",
    "you",
    "about",
    "into",
    "their",
}


def _clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    return max(low, min(high, value))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def _meaningful_terms(text: str) -> set[str]:
    return {tok for tok in _tokens(text) if len(tok) > 2 and tok not in STOPWORDS}


def _round1(value: float) -> float:
    return round(value, 1)


def _relevance_score(query: str, answer: str) -> float:
    query_terms = _meaningful_terms(query)
    if not query_terms:
        return 5.0

    answer_terms = _meaningful_terms(answer)
    overlap = len(query_terms & answer_terms)
    coverage = overlap / len(query_terms)
    return _clamp(2.0 + 8.0 * coverage)


def _length_score(answer: str) -> float:
    words = _tokens(answer)
    count = len(words)
    if count == 0:
        return 0.0

    # Favor medium-length responses and softly penalize extremes.
    if 60 <= count <= 220:
        return 10.0
    if count < 60:
        return _clamp((count / 60) * 10)
    if count <= 360:
        return _clamp(10 - ((count - 220) / 140) * 6)
    return 2.0


def _readability_score(answer: str) -> float:
    words = _tokens(answer)
    if not words:
        return 0.0

    sentences = [s.strip() for s in re.split(r"[.!?]+", answer) if s.strip()]
    sentence_count = len(sentences) or 1
    avg_sentence_len = len(words) / sentence_count
    long_word_ratio = sum(1 for w in words if len(w) >= 12) / len(words)

    score = 10.0
    score -= max(0.0, avg_sentence_len - 22) * 0.25
    score -= long_word_ratio * 20

    return _clamp(score)


def _structure_score(answer: str) -> float:
    if not answer.strip():
        return 0.0

    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    bullet_count = sum(1 for line in lines if re.match(r"^([-*]|\d+\.)\s+", line))
    short_heading_like = sum(1 for line in lines if ":" in line and len(line.split()) <= 7)
    paragraphs = [p.strip() for p in answer.split("\n\n") if p.strip()]

    score = 3.5
    if bullet_count > 0:
        score += 2.5
    if short_heading_like >= 2:
        score += 1.5
    if len(paragraphs) >= 2:
        score += 2.0
    if "\n" in answer:
        score += 1.0

    return _clamp(score)


def score_answer(query: str, answer: str) -> dict[str, float]:
    """Return per-metric and overall scores on a 0-10 scale."""
    relevance = _relevance_score(query, answer)
    length = _length_score(answer)
    readability = _readability_score(answer)
    structure = _structure_score(answer)

    overall = (
        relevance * SCORE_WEIGHTS["relevance"]
        + length * SCORE_WEIGHTS["length"]
        + readability * SCORE_WEIGHTS["readability"]
        + structure * SCORE_WEIGHTS["structure"]
    )

    return {
        "relevance": _round1(relevance),
        "length": _round1(length),
        "readability": _round1(readability),
        "structure": _round1(structure),
        "overall": _round1(overall),
    }


def select_top_result(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the highest-scoring successful result."""
    successful = [item for item in results if not item.get("error")]
    if not successful:
        return None
    return max(successful, key=lambda item: item.get("scores", {}).get("overall", 0.0))
