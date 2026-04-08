"""LangChain prompt and schema for TireLens brand analysis."""

from __future__ import annotations

import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


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
                (
                    "You are a financial and sustainability analyst helping users compare "
                    "global tire brands. Use only the structured data provided. The "
                    "curated metrics payload is the stable baseline. If live MCP context "
                    "is present, use it to augment the analysis, prefer fresher evidence "
                    "when it is clearly relevant, and be explicit when the conclusion is "
                    "based on mixed curated and live inputs. Pick one clear leader for "
                    "the selected domain, explain tradeoffs, call out real risks, and "
                    "keep the summary concise and evidence-based."
                ),
            ),
            (
                "human",
                (
                    "Analyze the selected tire brands.\n"
                    "Domain: {domain}\n"
                    "Brands: {brands}\n"
                    "Curated Metrics JSON:\n{metrics_json}\n\n"
                    "Live MCP Context JSON:\n{live_context_json}\n\n"
                    "Return structured output only."
                ),
            ),
        ]
    )

    return prompt | llm.with_structured_output(BrandAnalysis)
