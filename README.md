# TireLens

TireLens is a Streamlit application for comparing Michelin, Goodyear, Continental, and Bridgestone across curated financial, sustainability, and product portfolio datasets. It combines transparent ranking logic, report-backed evidence, and optional AI-generated analysis.

## Current Application Capabilities

- Compare any 2 to 4 supported tire brands in the same session.
- Switch between `Financials`, `Sustainability`, and `Products` comparison views.
- View a ranked comparison table and grouped bar chart for the selected domain.
- Review report-backed evidence cards with annual report summaries, page-level evidence snippets, and links to bundled PDF reports when available.
- Generate structured AI insight that identifies a leader, explains strengths, highlights risks, and summarizes long-term outlook.
- Continue using the dashboard without an API key; the AI panel falls back gracefully instead of breaking the app.

## Architecture Overview

- **Frontend:** Streamlit app in `app.py`
- **Analytics:** ranking, normalization, and comparison builders in `services/analytics.py`
- **Data Layer:** validated CSV loaders in `services/data_loader.py`
- **LLM Integration:** LangChain + OpenAI structured output in `chains/brand_analysis_chain.py` and `services/llm_service.py`

## Data Sources

The current application uses curated local assets for a deterministic demo experience. It does not use live financial, ESG, or news APIs.

- `data/financials.csv`
- `data/sustainability.csv`
- `data/products.csv`
- `static/reports/*.pdf`

## Installation

### Local Install

1. Create and activate a Python `3.11+` virtual environment.
2. Install the runtime dependencies:

```bash
pip install -r requirements.txt
```

If you also want to run the automated tests locally, install the dev dependencies:

```bash
pip install -r requirements-dev.txt
```

3. Copy or rename `.env.example` to `.env`, then insert your `OPENAI_API_KEY`.

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Only `OPENAI_API_KEY` is needed for the current AI insight feature. `OPENAI_MODEL` is optional.

4. Start the app:

```bash
streamlit run app.py
```

### Alternative Docker and Docker Compose Install

Use the same `.env` file if you want AI insights in a container.

Docker:

```bash
docker build -t tirelens .
docker run --rm -p 8501:8501 --env-file .env tirelens
```

Docker Compose:

```bash
docker compose up --build
```

The app will be available at `http://localhost:8501`.

### Deployment Notes

- The production image installs runtime dependencies only.
- The container runs as a non-root user and exposes a built-in health check.
- If `OPENAI_API_KEY` is omitted, the dashboard still loads and the AI panel falls back gracefully.

## Tests

Run the automated test suite with:

```bash
pip install -r requirements-dev.txt
pytest
```

## Limitations

- Uses curated demo datasets instead of live data feeds.
- AI analysis is limited to the structured metrics and evidence provided to the model.
- The comparison universe is currently limited to four tire brands.
