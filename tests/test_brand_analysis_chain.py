from __future__ import annotations

from chains.brand_analysis_chain import (
    HUMAN_PROMPT_TEMPLATE,
    SYSTEM_PROMPT_TEMPLATE,
    build_report_guidance,
)


def test_prompt_templates_explicitly_reference_report_backed_fields():
    assert "report-backed" in SYSTEM_PROMPT_TEMPLATE
    assert "page references" in SYSTEM_PROMPT_TEMPLATE
    assert "report_summary" in HUMAN_PROMPT_TEMPLATE
    assert "evidence_1" in HUMAN_PROMPT_TEMPLATE
    assert "{report_guidance}" in HUMAN_PROMPT_TEMPLATE


def test_build_report_guidance_varies_by_domain():
    assert "performance driver" in build_report_guidance("Financials").lower()
    assert "decarbonization" in build_report_guidance("Sustainability").lower()
    assert "portfolio breadth" in build_report_guidance("Products").lower()
