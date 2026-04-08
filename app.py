"""Streamlit entrypoint for the TireLens MVP."""

from __future__ import annotations

from typing import Any

import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from services.analytics import DOMAINS, build_domain_comparison
from services.data_loader import (
    DataValidationError,
    filter_by_brands,
    load_financials,
    load_products,
    load_sustainability,
)
from services.llm_service import generate_brand_analysis


load_dotenv()
st.set_page_config(page_title="TireLens", layout="wide")


@st.cache_data
def load_all_datasets():
    return load_financials(), load_sustainability(), load_products()


def render_analysis_card(analysis: dict[str, Any]) -> None:
    st.subheader("AI Analysis")
    st.markdown(f"**Leader:** {analysis['leader']}")
    st.markdown(f"**Domain:** {analysis['domain']}")
    st.markdown(f"**Strength Assessment:** {analysis['strength_assessment']}")
    st.markdown(f"**Long-Term Outlook:** {analysis['long_term_outlook']}")
    st.markdown("**Risk Factors**")
    for risk in analysis["risk_factors"]:
        st.write(f"- {risk}")
    st.markdown("**Executive Summary**")
    st.write(analysis["summary"])


def main() -> None:
    st.title("TireLens")
    st.caption(
        "Compare leading tire brands across financial performance, sustainability, "
        "and product portfolio strength with explainable analytics and optional AI insight."
    )

    try:
        financials, sustainability, products = load_all_datasets()
    except DataValidationError as exc:
        st.error(f"Dataset error: {exc}")
        return

    available_brands = sorted(financials["brand"].unique().tolist())

    selected_brands = st.multiselect(
        "Select brands",
        options=available_brands,
        default=available_brands,
    )
    selected_domain = st.selectbox("Select comparison domain", options=DOMAINS)

    if len(selected_brands) < 2:
        st.warning("Select at least two brands to generate a meaningful comparison.")
        return

    try:
        filtered_financials = filter_by_brands(financials, selected_brands)
        filtered_sustainability = filter_by_brands(sustainability, selected_brands)
        filtered_products = filter_by_brands(products, selected_brands)
        comparison = build_domain_comparison(
            selected_domain,
            filtered_financials,
            filtered_sustainability,
            filtered_products,
        )
    except (DataValidationError, ValueError) as exc:
        st.error(f"Unable to build comparison: {exc}")
        return

    left_col, right_col = st.columns((1.15, 1))
    with left_col:
        st.subheader(f"{selected_domain} Comparison")
        st.dataframe(comparison["table"], use_container_width=True, hide_index=True)

    with right_col:
        st.subheader(f"{selected_domain} Chart")
        figure = px.bar(
            comparison["chart"],
            x="Brand",
            y="Value",
            color="Metric",
            barmode="group",
            title=f"{selected_domain} metrics by brand",
        )
        figure.update_layout(legend_title_text="")
        st.plotly_chart(figure, use_container_width=True)

    st.divider()

    cache_key = f"analysis::{selected_domain}::{','.join(sorted(selected_brands))}"
    if st.button("Generate AI Insight", type="primary"):
        with st.spinner("Generating structured analysis..."):
            analysis = generate_brand_analysis(
                selected_brands,
                selected_domain,
                comparison["llm_payload"],
            )
            st.session_state[cache_key] = analysis.model_dump()

    analysis_result = st.session_state.get(cache_key)
    if analysis_result:
        render_analysis_card(analysis_result)
    else:
        st.info(
            "Generate AI Insight to produce a structured summary for the selected domain. "
            "If no API key is configured, TireLens will show a graceful fallback message."
        )


if __name__ == "__main__":
    main()
