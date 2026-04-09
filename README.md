# TireLens

TireLens is a lightweight Streamlit application for comparing four major tire brands across financial, sustainability, and product portfolio dimensions. It pairs curated public-style datasets with explainable analytics and an LLM-powered insight panel that returns structured analysis on demand.

TireLens now also supports optional MCP-backed public data enrichment. The app keeps the curated CSV datasets as the stable baseline, and when compatible MCP servers are configured it augments the experience with live finance and news context.

## What The Application Does

- Compares Michelin, Goodyear, Continental, and Bridgestone.
- Shows a domain-specific comparison table and chart for Financials, Sustainability, or Products.
- Calculates transparent ranking metrics, including revenue growth and a composite score.
- Generates structured AI analysis using OpenAI via LangChain.
- Optionally enriches AI insight and UI context with public MCP finance/news tooling.

## Architecture Overview

- **Frontend:** Streamlit single-page app in `app.py`
- **Analytics:** Pure Python helpers in `services/analytics.py`
- **Data Layer:** Curated CSV datasets loaded by `services/data_loader.py`
- **LLM Integration:** LangChain prompt and structured response model in `chains/brand_analysis_chain.py` and `services/llm_service.py`
- **MCP Enrichment:** Optional connector layer and orchestration in `services/mcp_service.py`

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

4. Optional: configure MCP connectors if you want live finance and news enrichment:

```env
MCP_ENABLED=true
MCP_REQUEST_TIMEOUT_SECONDS=8
MCP_CACHE_TTL_SECONDS=300

FINANCE_MCP_TRANSPORT=streamable-http
FINANCE_MCP_URL=https://secedgar.caseyjhand.com/mcp
FINANCE_MCP_TOOL=secedgar_get_financials

NEWS_MCP_TRANSPORT=streamable-http
NEWS_MCP_URL=https://mrbridge--latest-news-mcp-server.apify.actor/mcp?token=YOUR_APIFY_TOKEN
NEWS_MCP_TOOL=get_top_news
```

You can also use `stdio` transport instead of HTTP by setting `..._TRANSPORT=stdio`, `..._COMMAND`, and `..._ARGS`.

5. Start the app:

```bash
streamlit run app.py
```

## Environment Variables

- `OPENAI_API_KEY`: Required to generate AI insights.
- `OPENAI_MODEL`: Optional. Defaults to `gpt-4.1-mini`.
- `MCP_ENABLED`: Enables optional live MCP enrichment.
- `MCP_REQUEST_TIMEOUT_SECONDS`: Timeout applied to each configured connector request.
- `MCP_CACHE_TTL_SECONDS`: In-memory cache TTL for live MCP context.
- `FINANCE_MCP_*`: Transport, target, headers, and tool configuration for the finance connector.
- `NEWS_MCP_*`: Transport, target, headers, and tool configuration for the news connector.

If `OPENAI_API_KEY` is not set, the app still works and displays a graceful fallback message in the AI panel.
If MCP is disabled, unconfigured, or unavailable, the comparison experience stays fully usable and falls back to curated mode.

## MCP Enrichment Behavior

- Core comparison tables and charts remain driven by the curated CSV datasets in v1.
- When live MCP context is available, TireLens switches the source badge to `Hybrid`.
- The app shows a source-status strip plus a `Live MCP Highlights` section with provider-backed finance or news context.
- MCP failures are non-blocking. Warnings appear in the UI, but the comparison still renders.
- AI insight generation keeps using the curated metrics payload and appends live MCP context when present.

## MCP Connector Notes

TireLens ships with two example connector adapters:

- Finance MCP connector: expects a configured tool that can return structured finance context for a brand.
- News MCP connector: expects a configured tool that can return recent text summaries or headlines for the selected brands.

These adapters are intentionally pluggable. TireLens does not hardcode any single public MCP server. Instead, you configure the provider URL or command and the tool name through environment variables.

Example structured payloads the adapters can consume:

```json
{
  "brand": "Michelin",
  "summary": "Premium demand remains steady.",
  "source": "Finance MCP",
  "as_of": "2026-04-08T12:00:00Z",
  "metrics": {
    "revenue_usd_bn": 31.2,
    "operating_margin_pct": 12.4,
    "market_cap_usd_bn": 29.1
  }
}
```

```json
{
  "text": "Top stories mention tire industry demand, transport regulation, and EV adoption."
}
```

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
MCP_ENABLED=true
FINANCE_MCP_URL=https://secedgar.caseyjhand.com/mcp
FINANCE_MCP_TOOL=secedgar_get_financials
NEWS_MCP_URL=https://mrbridge--latest-news-mcp-server.apify.actor/mcp?token=YOUR_APIFY_TOKEN
NEWS_MCP_TOOL=get_top_news
```

Then start the app with:

```bash
docker compose up --build
```

The app will be available at `http://localhost:8501` on that machine. Because Streamlit is configured to listen on `0.0.0.0`, you can also open it from another device on the same network at `http://<computer-ip>:8501` if that computer's firewall allows port `8501`.

When using Docker, keep MCP endpoints reachable from inside the container. For local HTTP MCP servers on macOS, `host.docker.internal` is often the simplest option.

## How LLM Is Used

- The user selects brands and a comparison domain.
- TireLens prepares a structured metrics payload from the visible data.
- The LLM receives the selected-domain curated metrics plus optional live MCP context.
- LangChain validates the response into a structured schema before the UI renders it.

## Tests

Run the automated test suite with:

```bash
pytest
```

## Limitations

- Uses curated datasets instead of live financial or ESG APIs.
- Live MCP enrichment depends on compatible external MCP tooling and environment configuration.
- Excludes real-time news sentiment in the MVP.
- AI insights are only as strong as the structured inputs provided.
- The comparison universe is limited to four brands in v1.

## Future Improvements

- Add optional live data connectors with CSV fallback.
- Expand product taxonomy and regional segmentation.
- Add news sentiment and timeline views.
- Support exportable reports and saved comparisons.
