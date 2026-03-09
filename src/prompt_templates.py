"""Prompt variant construction logic."""

from __future__ import annotations

from typing import Any

VARIANT_SPECS = [
    {
        "id": "simple",
        "name": "Simple Explanation",
        "tagline": "Basic zero-shot response",
        "instruction": (
            "Answer the task clearly and directly. Keep it practical and easy to follow."
        ),
    },
    {
        "id": "teacher",
        "name": "Teacher Mode",
        "tagline": "Beginner-friendly teaching style",
        "instruction": (
            "Explain as if teaching a beginner. Use simple language and include one easy example."
        ),
    },
    {
        "id": "structured",
        "name": "Structured Answer",
        "tagline": "Organized into sections",
        "instruction": (
            "Respond in exactly 3 sections titled:\n"
            "1) Definition or Main Answer\n"
            "2) Explanation\n"
            "3) Example or Application"
        ),
    },
    {
        "id": "concise",
        "name": "Concise Version",
        "tagline": "Short and focused",
        "instruction": (
            "Answer in under 120 words. Use clear language and focus on the core idea only."
        ),
    },
]


def build_prompt_variants(query: str) -> list[dict[str, Any]]:
    """Return 4 fixed prompt variants for the same user query."""
    user_query = query.strip()
    variants: list[dict[str, Any]] = []

    for spec in VARIANT_SPECS:
        prompt = (
            "You are a helpful assistant.\n\n"
            f"User task:\n{user_query}\n\n"
            "How to respond:\n"
            f"{spec['instruction']}\n\n"
            "Output format rules:\n"
            "- Use plain text only.\n"
            "- Do not use markdown symbols like #, **, or backticks.\n"
            "- Keep the response clean and readable."
        )
        variants.append(
            {
                "id": spec["id"],
                "name": spec["name"],
                "tagline": spec["tagline"],
                "prompt": prompt,
            }
        )

    return variants
