"""Central config constants for Prompt Optimization Playground."""

APP_TITLE = "Prompt Optimization Playground"
APP_DESCRIPTION = (
    "A Gradio-based tool that compares multiple prompt engineering strategies and evaluates "
    "their effect on Gemini model outputs using heuristic scoring and human preference."
)

MODEL_ID = "gemini-3.1-flash-lite-preview"
GENERATE_CONTENT_API = "streamGenerateContent"
TIMEOUT_SECONDS = 60

EXAMPLE_QUERIES = [
    "Explain transformers in simple words.",
    "Write a professional email asking for internship feedback.",
    "Summarize reinforcement learning for a beginner.",
]

# Weighted average for overall score.
SCORE_WEIGHTS = {
    "relevance": 0.4,
    "length": 0.2,
    "readability": 0.2,
    "structure": 0.2,
}
