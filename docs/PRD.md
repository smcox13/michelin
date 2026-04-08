# TireLens PRD

## Product Name

TireLens – Brand Comparison & Analysis Platform

## 1. Product Overview

### 1.1 Objective

Build a lightweight web application that compares and analyzes major tire brands:

- Michelin
- Goodyear
- Continental
- Bridgestone

The application will:

- Aggregate public data
- Normalize and compare metrics
- Provide structured analytics
- Use an LLM to generate insights and summaries
- Offer a simple interactive UI

The system must be:

- Deployable within 2 days
- Simple to explain architecturally
- Maintainable and extensible
- Demonstrably using LLM value-add

## 2. Product Scope

### 2.1 Domain of Comparison

To ensure feasibility in 2 days, the app will compare brands across:

#### A. Financial Performance (Public Data)

- Revenue
- Net Income
- Operating Margin
- Market Cap
- Revenue Growth (YoY)

Source:

- Public financial APIs (for future enhancement)
- Manually curated static dataset (MVP)

#### B. Sustainability Metrics

- CO2 emissions (if available)
- Sustainability commitments
- Circular economy initiatives

Source:

- Public sustainability reports
- Curated dataset

#### C. Product Portfolio Overview

- Total product categories
- Premium vs budget positioning
- Presence in EV tire market

Source:

- Structured manual dataset

#### D. Sentiment Snapshot

Optional future enhancement via news API and LLM sentiment classification.

## 3. Core Features

### 3.1 Brand Comparison Dashboard

Users can:

- Select brands to compare
- Select comparison domain
- View a comparison table
- View charts
- Generate an LLM-backed insight summary

### 3.2 LLM-Powered Insight Engine

The LLM must:

- Generate an executive summary
- Compare brand positioning
- Return structured JSON output

Example:

```json
{
  "leader": "Michelin",
  "financial_strength": "High",
  "risk_factors": ["High debt", "Declining growth"],
  "long_term_outlook": "Moderate positive",
  "summary": "..."
}
```

## 4. Technical Architecture

- Frontend: Streamlit
- Backend: Python
- Data Layer: CSV first
- LLM Service: OpenAI via LangChain

## 5. User Flow

1. User opens the app.
2. User selects at least two brands and a domain.
3. The app renders comparison data and charts.
4. The user clicks **Generate AI Insight**.
5. The app shows a structured LLM analysis.

## 6. Non-Functional Requirements

- Runs locally with `streamlit run app.py`
- Setup under 5 minutes
- `.env` file for API key
- Deterministic demo data
- Clear error handling
- No heavy scraping dependencies

## 7. Repository Structure

```text
Michelin/
├── app.py
├── requirements.txt
├── Dockerfile
├── README.md
├── data/
├── services/
├── chains/
└── docs/
```

## 8. Detailed Functional Requirements

### 8.1 Data Loader

- Load CSV files
- Validate schema
- Return pandas DataFrame
- Filter by selected brands

### 8.2 Analytics Engine

Must provide:

- YoY growth calculations
- Margin comparisons
- Normalized score index (0–100)
- Ranking algorithm

Composite score formula:

```text
Score = (Revenue Growth * 0.4) + (Operating Margin * 0.3) + (Sustainability Score * 0.3)
```

### 8.3 LLM Chain

System prompt:

> You are a financial and sustainability analyst...

User input:

Structured JSON of metrics.

Output:

Validated structured JSON via Pydantic parser.

## 9. UI Requirements

Sections:

1. Title and description
2. Brand selector
3. Domain selector
4. Comparison table
5. Chart
6. Generate AI Insight button
7. AI analysis card

## 10. Limitations

- Limited public data
- Sustainability metrics may be manually curated
- LLM insights depend on the provided numeric inputs
- Not real-time financial streaming
