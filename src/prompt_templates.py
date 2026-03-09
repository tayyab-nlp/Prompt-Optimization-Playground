"""Prompt variant construction logic."""

from __future__ import annotations

from typing import Any

VARIANT_SPECS = [
    {
        "id": "simple",
        "name": "Simple Explanation",
        "tagline": "Basic zero-shot response",
        "strategy": (
            "Create a direct and clear prompt for a straightforward response. "
            "Focus on clarity and practical explanation."
        ),
    },
    {
        "id": "teacher",
        "name": "Teacher Mode",
        "tagline": "Beginner-friendly teaching style",
        "strategy": (
            "Create a teaching-style prompt for beginners. "
            "Use simple language and request one easy example."
        ),
    },
    {
        "id": "structured",
        "name": "Structured Answer",
        "tagline": "Organized into sections",
        "strategy": (
            "Create a prompt that asks for exactly 3 sections:\n"
            "1) Definition or Main Answer\n"
            "2) Explanation\n"
            "3) Example or Application\n"
            "Use clear markdown headings."
        ),
    },
    {
        "id": "concise",
        "name": "Concise Version",
        "tagline": "Short and focused",
        "strategy": (
            "Create a prompt that requests an answer under 120 words with only core ideas."
        ),
    },
]


def build_prompt_variants(query: str) -> list[dict[str, Any]]:
    """Return 4 prompt-optimization jobs for the same user query."""
    user_query = query.strip()
    variants: list[dict[str, Any]] = []

    for spec in VARIANT_SPECS:
        optimizer_prompt = (
            "You are an expert prompt engineer.\n"
            "Convert the user task into one optimized prompt for another assistant.\n\n"
            f"User task:\n{user_query}\n\n"
            "Strategy requirements:\n"
            f"{spec['strategy']}\n\n"
            "Output rules:\n"
            "- Return only the optimized prompt text.\n"
            "- Do not include analysis, labels, or explanations.\n"
            "- Keep the optimized prompt concise but complete.\n"
            "- Encourage readable markdown output when useful (headings, bullets, bold)."
        )
        variants.append(
            {
                "id": spec["id"],
                "name": spec["name"],
                "tagline": spec["tagline"],
                "optimizer_prompt": optimizer_prompt,
            }
        )

    return variants
