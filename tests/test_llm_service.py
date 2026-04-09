from __future__ import annotations

import pytest

from chains.brand_analysis_chain import BrandAnalysis, build_report_guidance
from services.llm_service import generate_brand_analysis


class StubChain:
    def __init__(self, result):
        self._result = result

    def invoke(self, _payload):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class RecordingChain:
    def __init__(self, result):
        self._result = result
        self.last_payload = None

    def invoke(self, payload):
        self.last_payload = payload
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


def test_generate_brand_analysis_passes_domain_report_guidance(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    chain = RecordingChain(
        BrandAnalysis(
            leader="Michelin",
            domain="Sustainability",
            strength_assessment="High",
            risk_factors=["Execution risk"],
            long_term_outlook="Positive",
            summary="Michelin leads on sustainability metrics and evidence.",
        )
    )

    def factory():
        return chain

    generate_brand_analysis(
        ["Michelin", "Goodyear"],
        "Sustainability",
        [{"brand": "Michelin", "report_summary": "Example"}],
        chain_factory=factory,
    )

    assert chain.last_payload is not None
    assert chain.last_payload["report_guidance"] == build_report_guidance(
        "Sustainability"
    )
    assert "decarbonization" in chain.last_payload["report_guidance"].lower()
