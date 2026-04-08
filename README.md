# TireLens

TireLens is a lightweight Streamlit application for comparing four major tire brands across financial, sustainability, and product portfolio dimensions. It pairs curated public-style datasets with explainable analytics and an LLM-powered insight panel that returns structured analysis on demand.

## What The Application Does

- Compares Michelin, Goodyear, Continental, and Bridgestone.
- Shows a domain-specific comparison table and chart for Financials, Sustainability, or Products.
- Calculates transparent ranking metrics, including revenue growth and a composite score.
- Generates structured AI analysis using OpenAI via LangChain.

## Architecture Overview

- **Frontend:** Streamlit single-page app in `app.py`
- **Analytics:** Pure Python helpers in `services/analytics.py`
- **Data Layer:** Curated CSV datasets loaded by `services/data_loader.py`
- **LLM Integration:** LangChain prompt and structured response model in `chains/brand_analysis_chain.py` and `services/llm_service.py`

## Data Sources

This MVP uses curated CSV datasets stored in `data/` for a deterministic demo. Values are demo-ready approximations based on public company reporting patterns and brand positioning rather than real-time feeds.

- `data/financials.csv`
- `data/sustainability.csv`
- `data/products.csv`

## Local Setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file and add your OpenAI API key if you want AI insights:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
```

4. Start the app:

```bash
streamlit run app.py
```

## Environment Variables

- `OPENAI_API_KEY`: Required to generate AI insights.
- `OPENAI_MODEL`: Optional. Defaults to `gpt-4.1-mini`.

If `OPENAI_API_KEY` is not set, the app still works and displays a graceful fallback message in the AI panel.

## Docker

Build the image:

```bash
docker build -t tirelens .
```

Run the container:

```bash
docker run --rm -p 8501:8501 --env-file .env tirelens
```

Run without an API key to validate graceful degradation:

```bash
docker run --rm -p 8501:8501 tirelens
```

The application will be available at `http://localhost:8501`.

## Docker Compose

This repo also includes `compose.yaml` for a one-command startup.

Start the app:

```bash
docker compose up --build
```

Run in the background:

```bash
docker compose up --build -d
```

Stop it:

```bash
docker compose down
```

To enable AI insights with Docker Compose, create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Then start the app with:

```bash
docker compose up --build
```

The app will be available at `http://localhost:8501` on that machine. Because Streamlit is configured to listen on `0.0.0.0`, you can also open it from another device on the same network at `http://<computer-ip>:8501` if that computer's firewall allows port `8501`.

## How LLM Is Used

- The user selects brands and a comparison domain.
- TireLens prepares a structured metrics payload from the visible data.
- The LLM receives only the selected-domain metrics plus limited qualitative context.
- LangChain validates the response into a structured schema before the UI renders it.

## Tests

Run the automated test suite with:

```bash
pytest
```

## Limitations

- Uses curated datasets instead of live financial or ESG APIs.
- Excludes real-time news sentiment in the MVP.
- AI insights are only as strong as the structured inputs provided.
- The comparison universe is limited to four brands in v1.

## Future Improvements

- Add optional live data connectors with CSV fallback.
- Expand product taxonomy and regional segmentation.
- Add news sentiment and timeline views.
- Support exportable reports and saved comparisons.
