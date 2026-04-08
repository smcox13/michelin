from __future__ import annotations

import pytest

from chains.brand_analysis_chain import BrandAnalysis
from services.mcp_models import LiveContextBundle, LiveFinanceContext, SourceAttribution
from services.llm_service import generate_brand_analysis


class StubChain:
    def __init__(self, result):
        self._result = result
        self.last_payload = None

    def invoke(self, _payload):
        self.last_payload = _payload
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def test_generate_brand_analysis_returns_structured_result(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    stub_chain = StubChain(
        BrandAnalysis(
            leader="Michelin",
            domain="Financials",
            strength_assessment="High",
            risk_factors=["Margin pressure"],
            long_term_outlook="Positive",
            summary="Michelin leads on the selected financial metrics.",
        )
    )

    def factory():
        return stub_chain

    result = generate_brand_analysis(
        ["Michelin", "Goodyear"],
        "Financials",
        [{"brand": "Michelin"}],
        chain_factory=factory,
    )
    assert result.leader == "Michelin"
    assert result.domain == "Financials"
    assert '"source_mode": "curated"' in stub_chain.last_payload["live_context_json"]


def test_generate_brand_analysis_handles_malformed_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def factory():
        return StubChain({"leader": "Michelin"})

    result = generate_brand_analysis(
        ["Michelin", "Goodyear"],
        "Financials",
        [{"brand": "Michelin"}],
        chain_factory=factory,
    )
    assert result.strength_assessment == "LLM insight unavailable"
    assert "failed gracefully" in result.summary


def test_generate_brand_analysis_handles_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = generate_brand_analysis(
        ["Michelin", "Goodyear"],
        "Financials",
        [{"brand": "Michelin"}],
    )
    assert result.strength_assessment == "LLM insight unavailable"
    assert "Set OPENAI_API_KEY" in result.summary


def test_generate_brand_analysis_handles_provider_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def factory():
        return StubChain(RuntimeError("provider unavailable"))

    result = generate_brand_analysis(
        ["Michelin", "Goodyear"],
        "Financials",
        [{"brand": "Michelin"}],
        chain_factory=factory,
    )
    assert result.leader == "Michelin"
    assert "provider unavailable" in result.summary


def test_generate_brand_analysis_augments_payload_with_live_context(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    stub_chain = StubChain(
        BrandAnalysis(
            leader="Michelin",
            domain="Financials",
            strength_assessment="High",
            risk_factors=["Volatile commodity costs"],
            long_term_outlook="Positive",
            summary="Live updates strengthen Michelin's lead.",
        )
    )

    def factory():
        return stub_chain

    live_context = LiveContextBundle(
        domain="Financials",
        finance_updates={
            "Michelin": LiveFinanceContext(
                brand="Michelin",
                summary="Live margin update improved.",
                source="Finance MCP",
                operating_margin_pct=12.4,
            )
        },
        attribution=SourceAttribution(
            mode="hybrid",
            providers=("Finance MCP",),
            freshness_timestamp="2026-04-08T11:00:00Z",
        ),
        highlights=("Michelin: Live margin update improved.",),
    )

    result = generate_brand_analysis(
        ["Michelin", "Goodyear"],
        "Financials",
        [{"brand": "Michelin"}],
        live_context=live_context,
        chain_factory=factory,
    )

    assert result.summary == "Live updates strengthen Michelin's lead."
    assert '"source_mode": "hybrid"' in stub_chain.last_payload["live_context_json"]
    assert "Live margin update improved." in stub_chain.last_payload["live_context_json"]
