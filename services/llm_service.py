"""LLM service wrapper with graceful fallback behavior."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from chains.brand_analysis_chain import BrandAnalysis, create_brand_analysis_chain
from services.mcp_models import LiveContextBundle
from services.mcp_service import augment_llm_payload


load_dotenv()


def _fallback_analysis(brands: list[str], domain: str, summary: str) -> BrandAnalysis:
    leader = brands[0] if brands else "Unavailable"
    return BrandAnalysis(
        leader=leader,
        domain=domain,
        strength_assessment="LLM insight unavailable",
        risk_factors=["AI analysis could not be generated from the current environment."],
        long_term_outlook="Needs API-backed analysis",
        summary=summary,
    )


def generate_brand_analysis(
    brands: list[str],
    domain: str,
    metrics_payload: list[dict[str, Any]],
    live_context: LiveContextBundle | None = None,
    chain_factory=create_brand_analysis_chain,
) -> BrandAnalysis:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_analysis(
            brands,
            domain,
            "Set OPENAI_API_KEY to generate structured AI analysis. The comparison "
            "dashboard remains fully usable without it.",
        )

    try:
        insight_input = augment_llm_payload(
            metrics_payload,
            live_context
            or LiveContextBundle(
                domain=domain,
            ),
        )
        chain = chain_factory()
        result = chain.invoke(
            {
                "domain": domain,
                "brands": ", ".join(brands),
                "metrics_json": json.dumps(insight_input["metrics_payload"], indent=2),
                "live_context_json": json.dumps(insight_input["live_context"], indent=2),
            }
        )
        if isinstance(result, BrandAnalysis):
            return result
        return BrandAnalysis.model_validate(result)
    except Exception as exc:  # pragma: no cover - exercised through tests with mocks
        return _fallback_analysis(
            brands,
            domain,
            f"AI analysis failed gracefully: {exc}",
        )
