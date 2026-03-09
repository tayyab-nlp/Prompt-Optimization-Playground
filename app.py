"""Prompt Optimization Playground - Gradio app entry point."""

from __future__ import annotations

import html
import os
import re
from typing import Any

import gradio as gr
import markdown

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
#main-layout { align-items: flex-start; }
.pvl-panel {
  border: 1px solid #d7e1ef;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 3px 14px rgba(2, 6, 23, 0.06);
  padding: 16px;
}
#left-panel {
  position: sticky;
  top: 14px;
  align-self: flex-start;
}
.pvl-card {
  border: 1px solid #d7e1ef;
  border-radius: 14px;
  padding: 14px;
  background: #ffffff;
}
.pvl-card h3 {margin: 0; font-size: 1.12rem;}
.pvl-tagline {margin-top: 4px; color: #475569; font-size: 0.92rem;}
.pvl-head {display: flex; align-items: flex-start; justify-content: space-between; gap: 10px;}
.pvl-status-chip {
  font-size: 0.8rem;
  font-weight: 700;
  padding: 5px 9px;
  border-radius: 999px;
  border: 1px solid #d7e1ef;
  white-space: nowrap;
  color: #334155;
  background: #f8fafc;
}
.pvl-status-chip.is-running {color: #1d4ed8; background: #eff6ff; border-color: #bfdbfe;}
.pvl-status-chip.is-done {color: #0f766e; background: #ecfeff; border-color: #99f6e4;}
.pvl-status-chip.is-failed {color: #b91c1c; background: #fef2f2; border-color: #fecaca;}
.pvl-answer {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
  line-height: 1.55;
  min-height: 220px;
}
.pvl-answer h1, .pvl-answer h2, .pvl-answer h3, .pvl-answer h4 {
  margin-top: 0.5rem;
  margin-bottom: 0.45rem;
}
.pvl-answer p { margin: 0.45rem 0; }
.pvl-answer ul, .pvl-answer ol { margin: 0.45rem 0 0.45rem 1.1rem; }
.pvl-answer strong { font-weight: 700; }
.pvl-answer li { margin-bottom: 0.3rem; }
.pvl-answer hr { display: none; }
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
#left-panel .examples .example,
#left-panel [data-testid="examples"] button,
#left-panel .examples button {
  justify-content: flex-start !important;
  text-align: left !important;
}
"""


def _escape_text(text: str) -> str:
    return html.escape(text)


def _normalize_optimized_prompt(text: str) -> str:
    """Trim wrappers so optimized prompt is directly reusable."""
    cleaned = text.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


def _clean_answer_markdown(answer: str) -> str:
    """Normalize common malformed markdown from model outputs."""
    text = answer.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"(?m)^\s*([-*_])\1{2,}\s*$", "", text)  # remove horizontal rules
    text = re.sub(r"(?m)^\s*[•◦]\s+", "- ", text)
    text = re.sub(r"(?m)^\s*\*\s+\*\s+", "- ", text)
    text = re.sub(r"(?m)^\s*\*\s+(?=[A-Za-z][^:\n]{1,40}:)", "- ", text)
    text = re.sub(r"\s+\*\s+\*\s+(?=[A-Z][^:\n]{1,40}:)", "\n- ", text)
    text = re.sub(r"\s+\*\s+(?=[A-Z][^:\n]{1,40}:)", "\n- ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _render_answer_html(answer: str) -> str:
    """Render markdown output as HTML so headings/bold/lists display correctly."""
    if not answer.strip():
        return "Waiting for generation..."
    safe_markdown = html.escape(_clean_answer_markdown(answer))
    return markdown.markdown(safe_markdown, extensions=["extra", "sane_lists"])


def _status_class(status_text: str) -> str:
    low = status_text.lower()
    if "failed" in low:
        return "is-failed"
    if "completed" in low or "done" in low:
        return "is-done"
    if "optimizing" in low or "generating" in low or "running" in low:
        return "is-running"
    return ""


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
    optimized_prompt: str,
    answer: str,
    status_text: str,
    scores: dict[str, float] | None = None,
    error_message: str | None = None,
    error_details: dict[str, Any] | None = None,
) -> str:
    prompt_text = optimized_prompt.strip() if optimized_prompt.strip() else "Optimized prompt not generated yet."
    prompt_html = _escape_text(prompt_text)
    answer_html = _render_answer_html(answer)

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
      <div class="pvl-head">
        <h3>{_escape_text(variant["name"])}</h3>
        <span class="pvl-status-chip {_status_class(status_text)}">{_escape_text(status_text)}</span>
      </div>
      <div class="pvl-tagline">{_escape_text(variant["tagline"])}</div>
      <details>
        <summary>Show optimized prompt</summary>
        <div class="pvl-prompt">{prompt_html}</div>
      </details>
      <div class="pvl-answer">{answer_html}</div>
      {score_block}
      {error_html}
      {_render_error_details(error_details)}
    </div>
    """


def _build_outputs(
    cards: list[str],
    progress_text: str,
    top_text: str,
    favorite_state: Any,
    favorite_text: str,
) -> tuple[Any, ...]:
    progress_html = f'<div class="pvl-progress">{_escape_text(progress_text)}</div>'
    return (*cards, progress_html, top_text, favorite_state, favorite_text)


def _compute_top_text(scored_results: list[dict[str, Any]]) -> str:
    top = select_top_result(scored_results)
    if top:
        return (
            "### Top automatic result\n"
            f"**{top['name']}** ({top['scores']['overall']}/10)  \n"
            f"{top['tagline']}"
        )
    return "### Top automatic result\nNo successful responses yet."


def _input_error_outputs(message: str) -> tuple[Any, ...]:
    cards: list[str] = []
    for spec in VARIANT_SPECS:
        cards.append(
            _render_result_card(
                variant=spec,
                optimized_prompt="",
                answer="",
                status_text=message,
                scores=None,
                error_message=message,
            )
        )
    top = f"### Top automatic result\n{message}"
    favorite_state = gr.update(choices=[], value=None, interactive=False)
    favorite_text = "Your selection: unavailable until results are generated."
    return _build_outputs(cards, "Validation failed.", top, favorite_state, favorite_text)


def run_variant_lab(api_key: str, query: str, model_id: str):
    """Run 2-stage flow per variant: optimize prompt, then generate final answer."""
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
    cards = [_render_result_card(variant, "", "", "Queued", scores=None) for variant in variants]
    top_text = "### Top automatic result\nRunning..."
    favorite_state = gr.update(choices=[], value=None, interactive=False)
    favorite_text = "Your selection: waiting for results."

    yield _build_outputs(
        cards,
        f"Initialized {total} variants. Starting optimization...",
        top_text,
        favorite_state,
        favorite_text,
    )

    scored_results: list[dict[str, Any]] = []

    for idx, variant in enumerate(variants, start=1):
        cards[idx - 1] = _render_result_card(variant, "", "", f"Optimizing prompt ({idx}/{total})...", scores=None)
        yield _build_outputs(
            cards,
            f"Optimizing prompt for {variant['name']} ({idx}/{total})...",
            top_text,
            favorite_state,
            favorite_text,
        )

        error_message: str | None = None
        error_details: dict[str, Any] | None = None
        optimized_prompt = ""

        try:
            optimized_prompt_raw = generate_answer(
                api_key=api_key,
                prompt=variant["optimizer_prompt"],
                model_id=model_id,
            )
            optimized_prompt = _normalize_optimized_prompt(optimized_prompt_raw)
        except GeminiRequestError as exc:
            answer = "This variant failed during prompt optimization."
            error_message = str(exc)
            error_details = exc.details
            scores = _empty_scores()
            status = f"Failed during optimization ({idx}/{total})"
            cards[idx - 1] = _render_result_card(
                variant=variant,
                optimized_prompt=optimized_prompt,
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
            top_text = _compute_top_text(scored_results)
            top = select_top_result(scored_results)
            favorite_state = gr.update(
                choices=[item["name"] for item in scored_results],
                value=top["name"] if top else None,
                interactive=bool(scored_results),
            )
            favorite_text = (
                f"Your selection: **{top['name']}**"
                if top
                else "Your selection: choose your preferred variant."
            )
            yield _build_outputs(cards, f"Processed {idx}/{total} variants.", top_text, favorite_state, favorite_text)
            continue
        except Exception as exc:  # pylint: disable=broad-except
            answer = "This variant failed during prompt optimization."
            error_message = f"Unexpected local error: {exc}"
            error_details = {"error_type": "unexpected_error", "raw_error": str(exc)}
            scores = _empty_scores()
            status = f"Failed during optimization ({idx}/{total})"
            cards[idx - 1] = _render_result_card(
                variant=variant,
                optimized_prompt=optimized_prompt,
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
            top_text = _compute_top_text(scored_results)
            top = select_top_result(scored_results)
            favorite_state = gr.update(
                choices=[item["name"] for item in scored_results],
                value=top["name"] if top else None,
                interactive=bool(scored_results),
            )
            favorite_text = (
                f"Your selection: **{top['name']}**"
                if top
                else "Your selection: choose your preferred variant."
            )
            yield _build_outputs(cards, f"Processed {idx}/{total} variants.", top_text, favorite_state, favorite_text)
            continue

        cards[idx - 1] = _render_result_card(
            variant=variant,
            optimized_prompt=optimized_prompt,
            answer="",
            status_text=f"Prompt optimized. Generating answer ({idx}/{total})...",
            scores=None,
        )
        yield _build_outputs(
            cards,
            f"Generating final answer for {variant['name']} ({idx}/{total})...",
            top_text,
            favorite_state,
            favorite_text,
        )

        error_message = None
        error_details = None
        try:
            answer = generate_answer(api_key=api_key, prompt=optimized_prompt, model_id=model_id)
            scores = score_answer(query=query, answer=answer)
            status = f"Completed ({idx}/{total})"
        except GeminiRequestError as exc:
            answer = "This variant failed during final answer generation."
            error_message = str(exc)
            error_details = exc.details
            scores = _empty_scores()
            status = f"Failed during generation ({idx}/{total})"
        except Exception as exc:  # pylint: disable=broad-except
            answer = "This variant failed during final answer generation."
            error_message = f"Unexpected local error: {exc}"
            error_details = {"error_type": "unexpected_error", "raw_error": str(exc)}
            scores = _empty_scores()
            status = f"Failed during generation ({idx}/{total})"

        cards[idx - 1] = _render_result_card(
            variant=variant,
            optimized_prompt=optimized_prompt,
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

        top_text = _compute_top_text(scored_results)
        top = select_top_result(scored_results)
        favorite_state = gr.update(
            choices=[item["name"] for item in scored_results],
            value=top["name"] if top else None,
            interactive=bool(scored_results),
        )
        favorite_text = (
            f"Your selection: **{top['name']}**"
            if top
            else "Your selection: choose your preferred variant."
        )

        yield _build_outputs(cards, f"Processed {idx}/{total} variants.", top_text, favorite_state, favorite_text)

    yield _build_outputs(cards, f"Done. Processed all {total} variants.", top_text, favorite_state, favorite_text)


def update_favorite(selection: str | None) -> str:
    if not selection:
        return "Your selection: choose your preferred variant."
    return f"Your selection: **{selection}**"


def build_demo() -> gr.Blocks:
    with gr.Blocks(title=APP_TITLE) as demo:
        with gr.Column(elem_classes="pvl-shell"):
            gr.Markdown(f"# {APP_TITLE}\n{APP_DESCRIPTION}")

            with gr.Row(elem_id="main-layout"):
                with gr.Column(scale=1, elem_classes=["pvl-panel"], elem_id="left-panel"):
                    api_key = gr.Textbox(
                        label="Gemini API Key",
                        type="password",
                        placeholder="Paste key here (not stored)",
                    )
                    model = gr.Dropdown(
                        choices=[MODEL_ID],
                        value=MODEL_ID,
                        interactive=False,
                        label="Model",
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
                    generate = gr.Button("Generate Variants", variant="primary")

                with gr.Column(scale=2, elem_classes="pvl-panel"):
                    gr.Markdown("## Output")
                    progress_text = gr.HTML('<div class="pvl-progress">Ready.</div>')

                    with gr.Tabs():
                        with gr.Tab("Simple Explanation"):
                            card_1 = gr.HTML(_render_result_card(VARIANT_SPECS[0], "", "", "Waiting", None))
                        with gr.Tab("Teacher Mode"):
                            card_2 = gr.HTML(_render_result_card(VARIANT_SPECS[1], "", "", "Waiting", None))
                        with gr.Tab("Structured Answer"):
                            card_3 = gr.HTML(_render_result_card(VARIANT_SPECS[2], "", "", "Waiting", None))
                        with gr.Tab("Concise Version"):
                            card_4 = gr.HTML(_render_result_card(VARIANT_SPECS[3], "", "", "Waiting", None))

                    top_result = gr.Markdown("### Top automatic result\nGenerate outputs to see ranking.")
                    favorite_pick = gr.Radio(
                        label="Your preferred result",
                        choices=[],
                        interactive=False,
                    )
                    favorite_text = gr.Markdown("Your selection: not selected.")

            generate.click(
                fn=run_variant_lab,
                inputs=[api_key, query, model],
                outputs=[card_1, card_2, card_3, card_4, progress_text, top_result, favorite_pick, favorite_text],
            )
            favorite_pick.change(fn=update_favorite, inputs=[favorite_pick], outputs=[favorite_text])

    return demo


if __name__ == "__main__":
    share_enabled = os.getenv("GRADIO_SHARE", "false").lower() in {"1", "true", "yes"}
    build_demo().queue().launch(css=CARD_CSS, theme=gr.themes.Default(), share=share_enabled)
