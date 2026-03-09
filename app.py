"""Prompt Variant Lab - Gradio app entry point."""

from __future__ import annotations

import html
import re
from typing import Any

import gradio as gr

from src.config import APP_DESCRIPTION, APP_TITLE, EXAMPLE_QUERIES, MODEL_ID
from src.generator import GeminiRequestError, generate_answer
from src.prompt_templates import VARIANT_SPECS, build_prompt_variants
from src.scorer import select_top_result, score_answer

CARD_CSS = """
:root { color-scheme: light; }
body, .gradio-container {
  background: #f6f8fc !important;
  color: #0f172a !important;
}
.pvl-shell {max-width: 1240px; margin: 0 auto;}
.pvl-panel {
  border: 1px solid #d7e1ef;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 3px 14px rgba(2, 6, 23, 0.06);
  padding: 16px;
}
.pvl-card {
  border: 1px solid #d7e1ef;
  border-radius: 14px;
  padding: 14px;
  background: #ffffff;
}
.pvl-card h3 {margin: 0; font-size: 1.12rem;}
.pvl-tagline {margin-top: 4px; color: #475569; font-size: 0.92rem;}
.pvl-status {margin-top: 10px; font-size: 0.86rem; color: #0369a1; font-weight: 600;}
.pvl-answer {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
  line-height: 1.55;
  white-space: pre-wrap;
  min-height: 220px;
}
.pvl-scores {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.pvl-score {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 7px 10px;
  background: #f8fafc;
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}
.pvl-overall {
  margin-top: 10px;
  font-weight: 700;
  color: #0f766e;
}
.pvl-error {
  margin-top: 10px;
  color: #b91c1c;
  font-weight: 600;
  white-space: pre-wrap;
}
.pvl-debug-line {margin: 6px 0; color: #1f2937;}
details {margin-top: 10px;}
summary {cursor: pointer; font-weight: 600; color: #1f2937;}
.pvl-prompt {
  margin-top: 7px;
  padding: 10px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.82rem;
}
.pvl-progress {
  margin-top: 2px;
  margin-bottom: 8px;
  font-size: 0.95rem;
  color: #0f172a;
  font-weight: 600;
}
"""


def _escape_text(text: str) -> str:
    return html.escape(text)


def _clean_answer_text(text: str) -> str:
    """Light cleanup to avoid raw markdown artifacts in HTML cards."""
    cleaned = text.replace("\r", "").strip()
    cleaned = re.sub(r"(?m)^\s*#{1,6}\s*", "", cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("`", "")
    cleaned = re.sub(r"(?m)^\s*[-*]\s+", "• ", cleaned)
    return cleaned


def _render_error_details(error_details: dict[str, Any] | None) -> str:
    if not error_details:
        return ""

    rows: list[str] = []
    for key, value in error_details.items():
        label = _escape_text(key.replace("_", " ").title())
        if isinstance(value, list):
            value_html = "<br>".join(f"• {_escape_text(str(item))}" for item in value)
        else:
            value_html = _escape_text(str(value))
        rows.append(f'<div class="pvl-debug-line"><strong>{label}:</strong> {value_html}</div>')

    return (
        "<details>"
        "<summary>Troubleshooting details</summary>"
        f'<div class="pvl-prompt">{"".join(rows)}</div>'
        "</details>"
    )


def _empty_scores() -> dict[str, float]:
    return {
        "relevance": 0.0,
        "length": 0.0,
        "readability": 0.0,
        "structure": 0.0,
        "overall": 0.0,
    }


def _render_result_card(
    variant: dict[str, str],
    answer: str,
    status_text: str,
    scores: dict[str, float] | None = None,
    error_message: str | None = None,
    error_details: dict[str, Any] | None = None,
) -> str:
    prompt_html = _escape_text(variant.get("prompt", ""))
    answer_html = _escape_text(_clean_answer_text(answer)) if answer else "Waiting for generation..."

    if scores is None:
        score_block = '<div class="pvl-overall">Scores will appear after generation.</div>'
    else:
        score_block = f"""
        <div class="pvl-scores">
          <div class="pvl-score"><span>Relevance</span><strong>{scores["relevance"]}/10</strong></div>
          <div class="pvl-score"><span>Length</span><strong>{scores["length"]}/10</strong></div>
          <div class="pvl-score"><span>Readability</span><strong>{scores["readability"]}/10</strong></div>
          <div class="pvl-score"><span>Structure</span><strong>{scores["structure"]}/10</strong></div>
        </div>
        <div class="pvl-overall">Overall Score: {scores["overall"]}/10</div>
        """

    error_html = ""
    if error_message:
        error_html = f'<div class="pvl-error">Error: {_escape_text(error_message)}</div>'

    return f"""
    <div class="pvl-card">
      <h3>{_escape_text(variant["name"])}</h3>
      <div class="pvl-tagline">{_escape_text(variant["tagline"])}</div>
      <details>
        <summary>Show prompt</summary>
        <div class="pvl-prompt">{prompt_html}</div>
      </details>
      <div class="pvl-status">{_escape_text(status_text)}</div>
      <div class="pvl-answer">{answer_html}</div>
      {score_block}
      {error_html}
      {_render_error_details(error_details)}
    </div>
    """


def _build_outputs(cards: list[str], progress_text: str, top_text: str) -> tuple[Any, ...]:
    progress_html = f'<div class="pvl-progress">{_escape_text(progress_text)}</div>'
    return (*cards, progress_html, top_text)


def _input_error_outputs(message: str) -> tuple[Any, ...]:
    cards: list[str] = []
    for spec in VARIANT_SPECS:
        cards.append(
            _render_result_card(
                variant={**spec, "prompt": ""},
                answer="",
                status_text=message,
                scores=None,
                error_message=message,
            )
        )
    top = f"### Top automatic result\n{message}"
    return _build_outputs(cards, "Validation failed.", top)


def run_variant_lab(api_key: str, query: str, model_id: str):
    """Generate one answer per prompt variant and stream UI updates."""
    api_key = (api_key or "").strip()
    query = (query or "").strip()

    if not api_key:
        yield _input_error_outputs("Please enter your Gemini API key.")
        return
    if not query:
        yield _input_error_outputs("Please enter a query or task before generating.")
        return

    variants = build_prompt_variants(query)
    total = len(variants)
    cards = [_render_result_card(variant, "", "Queued", scores=None) for variant in variants]
    top_text = "### Top automatic result\nRunning..."

    yield _build_outputs(cards, f"Initialized {total} variants. Starting generation...", top_text)

    scored_results: list[dict[str, Any]] = []

    for idx, variant in enumerate(variants, start=1):
        cards[idx - 1] = _render_result_card(variant, "", f"Generating ({idx}/{total})...", scores=None)
        yield _build_outputs(cards, f"Calling Gemini for {variant['name']} ({idx}/{total})...", top_text)

        error_message: str | None = None
        error_details: dict[str, Any] | None = None
        try:
            answer = generate_answer(api_key=api_key, prompt=variant["prompt"], model_id=model_id)
            scores = score_answer(query=query, answer=answer)
            status = f"Completed ({idx}/{total})"
        except GeminiRequestError as exc:
            answer = "This variant failed to generate a response."
            error_message = str(exc)
            error_details = exc.details
            scores = _empty_scores()
            status = f"Failed ({idx}/{total})"
        except Exception as exc:  # pylint: disable=broad-except
            answer = "This variant failed to generate a response."
            error_message = f"Unexpected local error: {exc}"
            error_details = {"error_type": "unexpected_error", "raw_error": str(exc)}
            scores = _empty_scores()
            status = f"Failed ({idx}/{total})"

        cards[idx - 1] = _render_result_card(
            variant=variant,
            answer=answer,
            status_text=status,
            scores=scores,
            error_message=error_message,
            error_details=error_details,
        )

        scored_results.append(
            {
                "id": variant["id"],
                "name": variant["name"],
                "tagline": variant["tagline"],
                "scores": scores,
                "error": error_message,
            }
        )

        top = select_top_result(scored_results)
        if top:
            top_text = (
                "### Top automatic result\n"
                f"**{top['name']}** ({top['scores']['overall']}/10)  \n"
                f"{top['tagline']}"
            )
        else:
            top_text = "### Top automatic result\nNo successful responses yet."

        yield _build_outputs(cards, f"Processed {idx}/{total} variants.", top_text)

    yield _build_outputs(cards, f"Done. Processed all {total} variants.", top_text)


def build_demo() -> gr.Blocks:
    with gr.Blocks(title=APP_TITLE) as demo:
        with gr.Column(elem_classes="pvl-shell"):
            gr.Markdown(f"# {APP_TITLE}\n{APP_DESCRIPTION}")

            with gr.Row():
                with gr.Column(scale=1, elem_classes="pvl-panel"):
                    api_key = gr.Textbox(
                        label="Gemini API Key",
                        type="password",
                        placeholder="Paste key here (not stored)",
                    )
                    query = gr.Textbox(
                        label="Query or Task",
                        lines=8,
                        placeholder="Example: Explain transformers in simple words",
                    )
                    gr.Examples(
                        examples=[[sample] for sample in EXAMPLE_QUERIES],
                        inputs=[query],
                        label="Example queries",
                    )
                    model = gr.Dropdown(
                        choices=[MODEL_ID],
                        value=MODEL_ID,
                        interactive=False,
                        label="Model",
                    )
                    generate = gr.Button("Generate Variants", variant="primary")

                with gr.Column(scale=2, elem_classes="pvl-panel"):
                    gr.Markdown("## Output")
                    progress_text = gr.HTML('<div class="pvl-progress">Ready.</div>')

                    with gr.Tabs():
                        with gr.Tab("Simple Explanation"):
                            card_1 = gr.HTML(_render_result_card({**VARIANT_SPECS[0], "prompt": ""}, "", "Waiting", None))
                        with gr.Tab("Teacher Mode"):
                            card_2 = gr.HTML(_render_result_card({**VARIANT_SPECS[1], "prompt": ""}, "", "Waiting", None))
                        with gr.Tab("Structured Answer"):
                            card_3 = gr.HTML(_render_result_card({**VARIANT_SPECS[2], "prompt": ""}, "", "Waiting", None))
                        with gr.Tab("Concise Version"):
                            card_4 = gr.HTML(_render_result_card({**VARIANT_SPECS[3], "prompt": ""}, "", "Waiting", None))

                    top_result = gr.Markdown("### Top automatic result\nGenerate outputs to see ranking.")

            generate.click(
                fn=run_variant_lab,
                inputs=[api_key, query, model],
                outputs=[card_1, card_2, card_3, card_4, progress_text, top_result],
            )

    return demo


if __name__ == "__main__":
    build_demo().queue().launch(css=CARD_CSS, theme=gr.themes.Default())
