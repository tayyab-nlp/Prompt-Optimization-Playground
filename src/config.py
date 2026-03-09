"""Central config constants for Prompt Variant Lab."""

APP_TITLE = "Prompt Variant Lab"
APP_DESCRIPTION = (
    "Compare how four fixed prompt strategies change Gemini outputs for the same task. "
    "Paste your API key, run generation, then compare answers side-by-side."
)

MODEL_ID = "gemini-3.1-flash-lite-preview"
GENERATE_CONTENT_API = "streamGenerateContent"
TIMEOUT_SECONDS = 60

EXAMPLE_QUERIES = [
    "Explain transformers in simple words.",
    "Write a professional email asking for internship feedback.",
    "Summarize reinforcement learning for a beginner.",
    "Create a 5-step plan to improve time management for students.",
]

# Weighted average for overall score.
SCORE_WEIGHTS = {
    "relevance": 0.4,
    "length": 0.2,
    "readability": 0.2,
    "structure": 0.2,
}
