from __future__ import annotations

import pandas as pd
import pytest

from services.analytics import (
    FINANCIALS,
    PRODUCTS,
    SUSTAINABILITY,
    build_domain_comparison,
    calculate_revenue_growth,
    compute_composite_scores,
    min_max_normalize,
    rank_brands,
)


def report_fields(summary: str, evidence_prefix: str, year: int = 2025) -> dict[str, object]:
    return {
        "report_year": year,
        "report_summary": summary,
        "evidence_1": f"{evidence_prefix} first insight",
        "evidence_1_page": 10,
        "evidence_2": f"{evidence_prefix} second insight",
        "evidence_2_page": 11,
        "evidence_3": f"{evidence_prefix} third insight",
        "evidence_3_page": 12,
    }


def sample_financials() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "brand": "Michelin",
                "fiscal_year": 2024,
                "revenue_usd_bn": 30.0,
                "prior_revenue_usd_bn": 27.0,
                "net_income_usd_bn": 2.5,
                "operating_margin_pct": 12.0,
                "market_cap_usd_bn": 28.0,
                **report_fields("Michelin financial summary", "Michelin financial"),
            },
            {
                "brand": "Goodyear",
                "fiscal_year": 2024,
                "revenue_usd_bn": 20.0,
                "prior_revenue_usd_bn": 20.0,
                "net_income_usd_bn": 0.4,
                "operating_margin_pct": 7.0,
                "market_cap_usd_bn": 6.0,
                **report_fields(
                    "Goodyear financial summary",
                    "Goodyear financial",
                    year=2024,
                ),
            },
        ]
    )


def sample_sustainability() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "brand": "Michelin",
                "co2_emissions_scope12_mt": 1.8,
                "sustainability_commitment": "Net-zero roadmap",
                "circular_economy_initiatives": "Recycled materials",
                "sustainability_score": 88,
                **report_fields("Michelin sustainability summary", "Michelin sustainability"),
            },
            {
                "brand": "Goodyear",
                "co2_emissions_scope12_mt": 2.1,
                "sustainability_commitment": "Efficiency initiatives",
                "circular_economy_initiatives": "Retread pilots",
                "sustainability_score": 76,
                **report_fields(
                    "Goodyear sustainability summary",
                    "Goodyear sustainability",
                    year=2024,
                ),
            },
        ]
    )


def sample_products() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "brand": "Michelin",
                "product_categories_count": 8,
                "market_position": "Premium",
                "ev_tire_presence": "Strong",
                "product_portfolio_score": 91,
                **report_fields("Michelin products summary", "Michelin products"),
            },
            {
                "brand": "Goodyear",
                "product_categories_count": 7,
                "market_position": "Mid-market",
                "ev_tire_presence": "Moderate",
                "product_portfolio_score": 78,
                **report_fields(
                    "Goodyear products summary",
                    "Goodyear products",
                    year=2024,
                ),
            },
        ]
    )


def test_calculate_revenue_growth():
    result = calculate_revenue_growth(sample_financials())
    assert round(result.loc[0, "revenue_growth_pct"], 2) == 11.11
    assert round(result.loc[1, "revenue_growth_pct"], 2) == 0.00


def test_min_max_normalize_bounds():
    normalized = min_max_normalize(pd.Series([10, 20, 30]))
    assert normalized.tolist() == [0.0, 50.0, 100.0]


def test_compute_composite_score_prefers_stronger_brand():
    result = compute_composite_scores(sample_financials(), sample_sustainability())
    michelin_score = result[result["brand"] == "Michelin"]["composite_score"].iloc[0]
    goodyear_score = result[result["brand"] == "Goodyear"]["composite_score"].iloc[0]
    assert michelin_score > goodyear_score


def test_rank_brands_orders_highest_first():
    dataframe = pd.DataFrame(
        [
            {"brand": "A", "score": 20},
            {"brand": "B", "score": 40},
        ]
    )
    ranked = rank_brands(dataframe, "score")
    assert ranked["brand"].tolist() == ["B", "A"]
    assert ranked["rank"].tolist() == [1, 2]


def test_build_domain_comparison_returns_table_chart_and_payload():
    comparison = build_domain_comparison(
        FINANCIALS,
        sample_financials(),
        sample_sustainability(),
        sample_products(),
    )
    assert list(comparison.keys()) == ["table", "chart", "llm_payload", "evidence"]
    assert not comparison["table"].empty
    assert not comparison["chart"].empty
    assert len(comparison["llm_payload"]) == 2
    assert len(comparison["evidence"]) == 2
    assert comparison["llm_payload"][0]["report_summary"] == "Michelin financial summary"
    assert comparison["llm_payload"][0]["evidence_1_page"] == 10
    assert comparison["evidence"][0]["evidence"][0]["page"] == 10


def test_build_domain_comparison_returns_evidence_for_each_domain():
    for domain in (FINANCIALS, SUSTAINABILITY, PRODUCTS):
        comparison = build_domain_comparison(
            domain,
            sample_financials(),
            sample_sustainability(),
            sample_products(),
        )
        assert [item["brand"] for item in comparison["evidence"]] == [
            "Michelin",
            "Goodyear",
        ]
        assert all(item["report_summary"] for item in comparison["evidence"])


def test_build_domain_comparison_raises_for_missing_report_fields():
    with pytest.raises(ValueError, match="missing report evidence columns"):
        build_domain_comparison(
            FINANCIALS,
            sample_financials().drop(columns=["report_year"]),
            sample_sustainability(),
            sample_products(),
        )
