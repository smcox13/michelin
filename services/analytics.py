"""Explainable analytics helpers for TireLens."""

from __future__ import annotations

from typing import Any

import pandas as pd


FINANCIALS = "Financials"
SUSTAINABILITY = "Sustainability"
PRODUCTS = "Products"
DOMAINS = (FINANCIALS, SUSTAINABILITY, PRODUCTS)
REPORT_EVIDENCE_FIELDS = [
    "report_year",
    "report_summary",
    "evidence_1",
    "evidence_1_page",
    "evidence_2",
    "evidence_2_page",
    "evidence_3",
    "evidence_3_page",
]


def calculate_revenue_growth(dataframe: pd.DataFrame) -> pd.DataFrame:
    enriched = dataframe.copy()
    enriched["revenue_growth_pct"] = (
        (enriched["revenue_usd_bn"] - enriched["prior_revenue_usd_bn"])
        / enriched["prior_revenue_usd_bn"]
        * 100
    )
    return enriched


def min_max_normalize(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    minimum = numeric.min()
    maximum = numeric.max()
    if pd.isna(minimum) or pd.isna(maximum):
        return pd.Series([0.0] * len(series), index=series.index, dtype=float)
    if maximum == minimum:
        return pd.Series([50.0] * len(series), index=series.index, dtype=float)
    return ((numeric - minimum) / (maximum - minimum) * 100).round(2)


def compute_composite_scores(
    financials: pd.DataFrame, sustainability: pd.DataFrame
) -> pd.DataFrame:
    merged = calculate_revenue_growth(financials).merge(
        sustainability[["brand", "sustainability_score"]],
        on="brand",
        how="left",
    )

    merged["revenue_growth_score"] = min_max_normalize(merged["revenue_growth_pct"])
    merged["operating_margin_score"] = min_max_normalize(merged["operating_margin_pct"])
    merged["sustainability_score_normalized"] = min_max_normalize(
        merged["sustainability_score"]
    )
    merged["composite_score"] = (
        merged["revenue_growth_score"] * 0.4
        + merged["operating_margin_score"] * 0.3
        + merged["sustainability_score_normalized"] * 0.3
    ).round(2)
    return merged


def rank_brands(dataframe: pd.DataFrame, score_column: str) -> pd.DataFrame:
    ranked = dataframe.copy()
    ranked["rank"] = ranked[score_column].rank(method="dense", ascending=False).astype(int)
    return ranked.sort_values(by=[score_column, "brand"], ascending=[False, True]).reset_index(
        drop=True
    )


def build_financial_comparison(
    financials: pd.DataFrame, sustainability: pd.DataFrame
) -> pd.DataFrame:
    comparison = rank_brands(compute_composite_scores(financials, sustainability), "composite_score")
    return comparison[
        [
            "brand",
            "revenue_usd_bn",
            "prior_revenue_usd_bn",
            "revenue_growth_pct",
            "net_income_usd_bn",
            "operating_margin_pct",
            "market_cap_usd_bn",
            "sustainability_score",
            "composite_score",
            "rank",
        ]
    ].rename(
        columns={
            "brand": "Brand",
            "revenue_usd_bn": "Revenue (USD bn)",
            "prior_revenue_usd_bn": "Prior Revenue (USD bn)",
            "revenue_growth_pct": "Revenue Growth (%)",
            "net_income_usd_bn": "Net Income (USD bn)",
            "operating_margin_pct": "Operating Margin (%)",
            "market_cap_usd_bn": "Market Cap (USD bn)",
            "sustainability_score": "Sustainability Score",
            "composite_score": "Composite Score",
            "rank": "Rank",
        }
    )


def build_sustainability_comparison(sustainability: pd.DataFrame) -> pd.DataFrame:
    comparison = sustainability.copy()
    comparison["sustainability_score_normalized"] = min_max_normalize(
        comparison["sustainability_score"]
    )
    comparison = rank_brands(comparison, "sustainability_score")
    return comparison[
        [
            "brand",
            "co2_emissions_scope12_mt",
            "sustainability_score",
            "sustainability_commitment",
            "circular_economy_initiatives",
            "rank",
        ]
    ].rename(
        columns={
            "brand": "Brand",
            "co2_emissions_scope12_mt": "CO2 Scope 1+2 (Mt)",
            "sustainability_score": "Sustainability Score",
            "sustainability_commitment": "Commitment",
            "circular_economy_initiatives": "Circular Economy Initiatives",
            "rank": "Rank",
        }
    )


def build_product_comparison(products: pd.DataFrame) -> pd.DataFrame:
    comparison = rank_brands(products.copy(), "product_portfolio_score")
    return comparison[
        [
            "brand",
            "product_categories_count",
            "market_position",
            "ev_tire_presence",
            "product_portfolio_score",
            "rank",
        ]
    ].rename(
        columns={
            "brand": "Brand",
            "product_categories_count": "Product Categories",
            "market_position": "Market Position",
            "ev_tire_presence": "EV Tire Presence",
            "product_portfolio_score": "Portfolio Score",
            "rank": "Rank",
        }
    )


def build_chart_data(domain: str, comparison_table: pd.DataFrame) -> pd.DataFrame:
    if domain == FINANCIALS:
        metric_columns = [
            "Revenue (USD bn)",
            "Net Income (USD bn)",
            "Operating Margin (%)",
            "Revenue Growth (%)",
            "Composite Score",
        ]
    elif domain == SUSTAINABILITY:
        metric_columns = [
            "CO2 Scope 1+2 (Mt)",
            "Sustainability Score",
        ]
    else:
        metric_columns = [
            "Product Categories",
            "Portfolio Score",
        ]

    return comparison_table.melt(
        id_vars=["Brand"],
        value_vars=metric_columns,
        var_name="Metric",
        value_name="Value",
    )


def build_evidence_payload(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    required_columns = ["brand", *REPORT_EVIDENCE_FIELDS]
    missing_columns = [
        column for column in required_columns if column not in dataframe.columns
    ]
    if missing_columns:
        missing_list = ", ".join(missing_columns)
        raise ValueError(
            "Dataset is missing report evidence columns: "
            f"{missing_list}. If the app was already running, refresh it so the "
            "latest CSV data is reloaded."
        )

    payload: list[dict[str, Any]] = []
    for record in dataframe.to_dict(orient="records"):
        payload.append(
            {
                "brand": record["brand"],
                "report_year": int(record["report_year"]),
                "report_summary": str(record["report_summary"]),
                "evidence": [
                    {
                        "text": str(record["evidence_1"]),
                        "page": int(record["evidence_1_page"]),
                    },
                    {
                        "text": str(record["evidence_2"]),
                        "page": int(record["evidence_2_page"]),
                    },
                    {
                        "text": str(record["evidence_3"]),
                        "page": int(record["evidence_3_page"]),
                    },
                ],
            }
        )
    return payload


def build_llm_payload(
    domain: str,
    financials: pd.DataFrame,
    sustainability: pd.DataFrame,
    products: pd.DataFrame,
) -> list[dict[str, Any]]:
    if domain == FINANCIALS:
        payload = compute_composite_scores(financials, sustainability)[
            [
                "brand",
                "revenue_usd_bn",
                "prior_revenue_usd_bn",
                "revenue_growth_pct",
                "net_income_usd_bn",
                "operating_margin_pct",
                "market_cap_usd_bn",
                "sustainability_score",
                "composite_score",
                *REPORT_EVIDENCE_FIELDS,
            ]
        ]
    elif domain == SUSTAINABILITY:
        payload = sustainability[
            [
                "brand",
                "co2_emissions_scope12_mt",
                "sustainability_score",
                "sustainability_commitment",
                "circular_economy_initiatives",
                *REPORT_EVIDENCE_FIELDS,
            ]
        ].copy()
    else:
        payload = products[
            [
                "brand",
                "product_categories_count",
                "market_position",
                "ev_tire_presence",
                "product_portfolio_score",
                *REPORT_EVIDENCE_FIELDS,
            ]
        ].copy()

    return payload.round(2).to_dict(orient="records")


def build_domain_comparison(
    domain: str,
    financials: pd.DataFrame,
    sustainability: pd.DataFrame,
    products: pd.DataFrame,
) -> dict[str, Any]:
    if domain not in DOMAINS:
        raise ValueError(f"Unsupported domain: {domain}")

    if domain == FINANCIALS:
        table = build_financial_comparison(financials, sustainability).round(2)
        evidence = build_evidence_payload(financials)
    elif domain == SUSTAINABILITY:
        table = build_sustainability_comparison(sustainability).round(2)
        evidence = build_evidence_payload(sustainability)
    else:
        table = build_product_comparison(products).round(2)
        evidence = build_evidence_payload(products)

    return {
        "table": table,
        "chart": build_chart_data(domain, table),
        "llm_payload": build_llm_payload(domain, financials, sustainability, products),
        "evidence": evidence,
    }
