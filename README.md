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
- Automatic scoring (0-10 scale):
  - Relevance
  - Length
  - Readability
  - Structure
  - Weighted overall score
- Tabbed output view (one variant visible at a time)
- Progressive updates as each variant finishes
- “Top automatic result” summary
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
4. Each prompt variant is sent to Gemini (`streamGenerateContent`) using the same model and generation settings.
5. Each answer is scored with lightweight local heuristics.
6. Results are shown in tabs with:
   - variant name + tagline
   - generated answer
   - metric scores + overall score
   - hidden expandable prompt text
7. The app highlights the top-scoring result.

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

## Live Demo

Add your Gradio live link in this section so GitHub visitors can test the app quickly.

## API Key Handling

- The Gemini API key is entered directly in the UI.
- The app uses the key only for the current request.
- The key is not saved to disk, database, or environment variables by this implementation.

## Future Improvements

- Add export buttons (Markdown/JSON) for comparison sessions
- Add optional user-tunable scoring weights
- Add additional prompt strategy presets
- Add support for comparing multiple Gemini models in a controlled way
