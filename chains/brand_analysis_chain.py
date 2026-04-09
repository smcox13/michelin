"""LangChain prompt and schema for TireLens brand analysis."""

from __future__ import annotations

import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from services.analytics import FINANCIALS, PRODUCTS, SUSTAINABILITY


SYSTEM_PROMPT_TEMPLATE = (
    "You are a financial and sustainability analyst helping users compare global "
    "tire brands. Use only the structured data provided. Treat the report-backed "
    "fields as first-class evidence, not as optional background context. Each "
    "brand may include a report summary, three evidence snippets, and page "
    "references. Use these fields to explain reported business drivers, strategic "
    "priorities, execution constraints, and risks. Combine the report-backed "
    "evidence with the quantitative metrics to pick one clear leader for the "
    "selected domain. If the qualitative evidence and the headline metrics pull in "
    "different directions, explain the tradeoff rather than ignoring it. Do not "
    "invent claims, quotes, page references, or outside facts. Keep the response "
    "concise, comparative, and grounded in the provided evidence."
)

HUMAN_PROMPT_TEMPLATE = (
    "Analyze the selected tire brands.\n"
    "Domain: {domain}\n"
    "Brands: {brands}\n"
    "Domain guidance for report-backed fields:\n"
    "{report_guidance}\n\n"
    "Metrics JSON (including report-backed evidence fields):\n"
    "{metrics_json}\n\n"
    "When the payload includes report fields, use `report_summary`, `evidence_1`, "
    "`evidence_2`, `evidence_3`, and their page references as the main qualitative "
    "grounding for strengths, risks, and outlook. Return structured output only."
)

REPORT_GUIDANCE_BY_DOMAIN = {
    FINANCIALS: (
        "For Financials, treat evidence_1 as the reported performance driver, "
        "evidence_2 as the capital allocation or strategic priority, and "
        "evidence_3 as the explicit headwind, risk, or execution constraint."
    ),
    SUSTAINABILITY: (
        "For Sustainability, treat evidence_1 as decarbonization target or "
        "progress, evidence_2 as circularity, recycled-material, or renewable-"
        "material action, and evidence_3 as the stated execution risk, dependency, "
        "or regulatory exposure."
    ),
    PRODUCTS: (
        "For Products, treat evidence_1 as portfolio breadth or segment focus, "
        "evidence_2 as EV, OEM, or technology positioning, and evidence_3 as the "
        "portfolio weakness, dependency, or competitive pressure."
    ),
}


class BrandAnalysis(BaseModel):
    leader: str = Field(description="The brand that currently leads in the selected domain.")
    domain: str = Field(description="The comparison domain used for this analysis.")
    strength_assessment: str = Field(
        description="A concise assessment of the leader's strength in the selected domain."
    )
    risk_factors: list[str] = Field(
        description="Key risks, weaknesses, or watch-outs for the selected brands."
    )
    long_term_outlook: str = Field(
        description="A concise forward-looking outlook for the domain comparison."
    )
    summary: str = Field(description="An executive summary of the domain comparison.")


def build_report_guidance(domain: str) -> str:
    return REPORT_GUIDANCE_BY_DOMAIN.get(
        domain,
        (
            "Use any report-backed summary and evidence fields to explain the most "
            "important strategic drivers, risks, and tradeoffs in the selected "
            "domain."
        ),
    )


def create_brand_analysis_chain(llm: ChatOpenAI | None = None):
    if llm is None:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            temperature=0,
        )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                SYSTEM_PROMPT_TEMPLATE,
            ),
            (
                "human",
                HUMAN_PROMPT_TEMPLATE,
            ),
        ]
    )

    return prompt | llm.with_structured_output(BrandAnalysis)
