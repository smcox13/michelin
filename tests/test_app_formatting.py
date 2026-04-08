from __future__ import annotations

from app import (
    build_live_highlight_items,
    build_source_status_markup,
    format_analysis_paragraphs,
    summarize_source_status,
)
from services.mcp_models import LiveContextBundle, LiveFinanceContext, SourceAttribution


def test_format_analysis_paragraphs_preserves_inline_math_as_literal_text():
    result = format_analysis_paragraphs(
        "Revenue stayed near $x + y$.\n"
        "Margin improved <slightly>.\n\n"
        "Second paragraph with **markdown**."
    )

    assert result == (
        "<p>Revenue stayed near $x + y$.<br />"
        "Margin improved &lt;slightly&gt;.</p>"
        "<p>Second paragraph with **markdown**.</p>"
    )


def test_summarize_source_status_formats_hybrid_mode():
    summary = summarize_source_status(
        SourceAttribution(
            mode="hybrid",
            providers=("Finance MCP", "News MCP"),
            freshness_timestamp="2026-04-08T12:00:00Z",
            warnings=("News timed out",),
        )
    )

    assert summary["mode_label"] == "Hybrid"
    assert summary["provider_text"] == "Finance MCP, News MCP"
    assert summary["warnings"] == ["News timed out"]


def test_build_source_status_markup_includes_mode_and_provider_text():
    markup = build_source_status_markup(
        SourceAttribution(
            mode="curated",
            providers=(),
            freshness_timestamp=None,
        )
    )

    assert "Source Mode: Curated" in markup
    assert "Curated CSV datasets" in markup


def test_build_live_highlight_items_returns_live_summaries():
    live_context = LiveContextBundle(
        domain="Financials",
        finance_updates={
            "Michelin": LiveFinanceContext(
                brand="Michelin",
                summary="Premium tire demand remained stable.",
                source="Finance MCP",
                revenue_usd_bn=31.0,
            )
        },
        attribution=SourceAttribution(mode="hybrid"),
        highlights=("Michelin: Revenue 31.00B USD | Premium tire demand remained stable.",),
    )

    assert build_live_highlight_items(live_context) == [
        "Michelin: Revenue 31.00B USD | Premium tire demand remained stable."
    ]
