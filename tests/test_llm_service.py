from __future__ import annotations

import pytest

from chains.brand_analysis_chain import BrandAnalysis
from services.llm_service import generate_brand_analysis


class StubChain:
    def __init__(self, result):
        self._result = result

    def invoke(self, _payload):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def test_generate_brand_analysis_returns_structured_result(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def factory():
        return StubChain(
            BrandAnalysis(
                leader="Michelin",
                domain="Financials",
                strength_assessment="High",
                risk_factors=["Margin pressure"],
                long_term_outlook="Positive",
                summary="Michelin leads on the selected financial metrics.",
            )
        )

    result = generate_brand_analysis(
        ["Michelin", "Goodyear"],
        "Financials",
        [{"brand": "Michelin"}],
        chain_factory=factory,
    )
    assert result.leader == "Michelin"
    assert result.domain == "Financials"


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
