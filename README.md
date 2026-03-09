---
title: Prompt Optimization Playground
emoji: 🧪
colorFrom: blue
colorTo: indigo
sdk: gradio
python_version: "3.10"
app_file: app.py
pinned: false
---

# Prompt Optimization Playground

Prompt Optimization Playground is a Gradio-based tool that compares multiple prompt engineering strategies and evaluates their effect on Gemini model outputs using heuristic scoring and human preference.

The app is designed for quick visual comparison:
- one query
- four fixed prompt variants
- one Gemini response per variant
- automatic heuristic scoring
- hidden-by-default prompt reveal

## Features

- Two-column Gradio UI (inputs on left, outputs on right)
- Sticky input column for easier long-form output review
- API key entry in the GUI (`password` field)
- No API key storage, persistence, or logging
- Four fixed prompt strategies:
  - Simple Explanation
  - Teacher Mode
  - Structured Answer
  - Concise Version
- Two-stage generation per variant:
  - Stage 1: generate an optimized prompt for the strategy
  - Stage 2: generate the final answer from that optimized prompt
- Automatic scoring (0-10 scale):
  - Relevance
  - Length
  - Readability
  - Structure
  - Weighted overall score
- Tabbed output view (one variant visible at a time)
- Progressive updates as each variant finishes
- “Top automatic result” summary
- Manual “preferred result” selection
- Graceful handling of missing input, API errors, and malformed responses
- Expandable troubleshooting details for failed variants (timeout/network/HTTP clues)

## Project Structure

```text
prompt-variant-lab/
├── app.py
├── requirements.txt
├── README.md
└── src/
    ├── __init__.py
    ├── config.py
    ├── prompt_templates.py
    ├── generator.py
    └── scorer.py
```

## How It Works

1. User enters a Gemini API key in the app.
2. User enters a query/task.
3. The app builds 4 fixed prompt variants from the same query.
4. For each variant, Gemini first creates an optimized prompt using that strategy.
5. The optimized prompt is then sent to Gemini to generate the final answer.
6. Each final answer is scored with lightweight local heuristics.
7. Results are shown in tabs with:
   - variant name + tagline
   - optimized prompt (expandable)
   - generated answer
   - metric scores + overall score
8. The app highlights the top-scoring result and supports manual preference selection.

## Setup

### 1) Create and activate a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

## Run Locally

```bash
python app.py
```

Then open the local Gradio URL shown in your terminal.

## Public Demo Link (for GitHub)

Live demo: [https://vtayyab6-prompt-optimization-playground.hf.space](https://vtayyab6-prompt-optimization-playground.hf.space)

Use one of these options:

### Option 1: Temporary public link (quick test)

Run locally with Gradio sharing enabled and copy the generated public URL:

```bash
GRADIO_SHARE=true python app.py
```

This shared link is temporary (Gradio docs state it expires after one week).

### Option 2: Persistent public link (recommended)

Deploy to Hugging Face Spaces (Gradio SDK) for a stable URL you can place in your GitHub README:

1. Create a new Space on Hugging Face and select **Gradio** as the SDK.
2. Push this repository content to the Space.
3. Hugging Face builds and serves your app automatically.
4. Use your Space URL in README, for example:
   `https://vtayyab6-prompt-optimization-playground.hf.space`

Suggested README badge/link format:

```md
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Open-blue)](https://vtayyab6-prompt-optimization-playground.hf.space)
```

## API Key Handling

- The Gemini API key is entered directly in the UI.
- The app uses the key only for the current request.
- The key is not saved to disk, database, or environment variables by this implementation.

## Future Improvements

- Add export buttons (Markdown/JSON) for comparison sessions
- Add optional user-tunable scoring weights
- Add additional prompt strategy presets
- Add support for comparing multiple Gemini models in a controlled way
