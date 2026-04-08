"""Streamlit entrypoint for the TireLens MVP."""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path
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
from services.mcp_models import LiveContextBundle, SourceAttribution
from services.mcp_service import get_live_context
from services.llm_service import generate_brand_analysis


load_dotenv()
st.set_page_config(page_title="TireLens", layout="wide")


LOGO_DIR = Path(__file__).parent / "assets" / "logos"
SELECTED_TILE_BORDER = "#FF4B4B"
UNSELECTED_TILE_BORDER = "#D7DCE5"

BRAND_TILE_STYLES = {
    "Bridgestone": {
        "background": "#FFFFFF",
        "foreground": "#1C1C1C",
        "accent": "#E31E24",
    },
    "Continental": {
        "background": "#F6B500",
        "foreground": "#111111",
        "accent": "#111111",
    },
    "Goodyear": {
        "background": "#123A8C",
        "foreground": "#FFFFFF",
        "accent": "#F5C242",
    },
    "Michelin": {
        "background": "#0B3A82",
        "foreground": "#FFFFFF",
        "accent": "#F5C400",
    },
}


@st.cache_data
def load_all_datasets():
    return load_financials(), load_sustainability(), load_products()


def format_analysis_paragraphs(text: str) -> str:
    normalized_text = text.replace("\r\n", "\n").strip()
    if not normalized_text:
        return "<p></p>"

    paragraphs = [
        paragraph.strip()
        for paragraph in normalized_text.split("\n\n")
        if paragraph.strip()
    ]
    if not paragraphs:
        paragraphs = [normalized_text]

    return "".join(
        f"<p>{escape(paragraph).replace(chr(10), '<br />')}</p>"
        for paragraph in paragraphs
    )


def render_analysis_styles() -> None:
    st.markdown(
        """
        <style>
        .analysis-field {
            display: grid;
            gap: 0.35rem;
            margin-bottom: 1rem;
        }

        .analysis-label {
            font-weight: 700;
        }

        .analysis-field p {
            margin: 0;
            line-height: 1.6;
            white-space: normal;
        }

        .analysis-field ul {
            margin: 0;
            padding-left: 1.25rem;
        }

        .analysis-field li + li {
            margin-top: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_analysis_text_field(label: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="analysis-field">
          <div class="analysis-label">{escape(label)}</div>
          {format_analysis_paragraphs(text)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_analysis_list_field(label: str, items: list[str]) -> None:
    list_items = "".join(
        f"<li>{format_analysis_paragraphs(item)}</li>"
        for item in items
    ) or "<li><p></p></li>"
    st.markdown(
        f"""
        <div class="analysis-field">
          <div class="analysis-label">{escape(label)}</div>
          <ul>{list_items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_analysis_card(analysis: dict[str, Any]) -> None:
    st.subheader("AI Analysis")
    render_analysis_styles()
    render_analysis_text_field("Leader", analysis["leader"])
    render_analysis_text_field("Domain", analysis["domain"])
    render_analysis_text_field(
        "Strength Assessment",
        analysis["strength_assessment"],
    )
    render_analysis_text_field(
        "Long-Term Outlook",
        analysis["long_term_outlook"],
    )
    render_analysis_list_field("Risk Factors", analysis["risk_factors"])
    render_analysis_text_field("Executive Summary", analysis["summary"])


def summarize_source_status(attribution: SourceAttribution) -> dict[str, str | list[str]]:
    mode_label = attribution.mode.title()
    provider_text = ", ".join(attribution.providers) if attribution.providers else "Curated CSV datasets"
    freshness_text = attribution.freshness_timestamp or "Not available"
    return {
        "mode_label": mode_label,
        "provider_text": provider_text,
        "freshness_text": freshness_text,
        "warnings": list(attribution.warnings),
    }


def build_source_status_markup(attribution: SourceAttribution) -> str:
    summary = summarize_source_status(attribution)
    badge_background = {
        "Curated": "#EEF2FF",
        "Hybrid": "#ECFDF3",
        "Live": "#FEF3C7",
    }.get(str(summary["mode_label"]), "#EEF2FF")
    badge_color = {
        "Curated": "#3730A3",
        "Hybrid": "#166534",
        "Live": "#92400E",
    }.get(str(summary["mode_label"]), "#3730A3")

    return f"""
    <div style="
        border: 1px solid #E5E7EB;
        border-radius: 18px;
        padding: 14px 18px;
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
        display: flex;
        flex-wrap: wrap;
        gap: 14px;
        align-items: center;
        margin-bottom: 1rem;
    ">
      <div style="
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 6px 12px;
          border-radius: 999px;
          background: {badge_background};
          color: {badge_color};
          font-weight: 700;
          font-size: 13px;
      ">
        Source Mode: {escape(str(summary["mode_label"]))}
      </div>
      <div style="min-width: 180px;">
        <div style="font-size: 12px; color: #6B7280; font-weight: 600;">Providers</div>
        <div style="font-size: 14px; color: #111827;">{escape(str(summary["provider_text"]))}</div>
      </div>
      <div style="min-width: 180px;">
        <div style="font-size: 12px; color: #6B7280; font-weight: 600;">Freshness</div>
        <div style="font-size: 14px; color: #111827;">{escape(str(summary["freshness_text"]))}</div>
      </div>
    </div>
    """


def build_live_highlight_items(live_context: LiveContextBundle) -> list[str]:
    return list(live_context.highlights)


def render_source_status_strip(attribution: SourceAttribution) -> None:
    st.markdown(build_source_status_markup(attribution), unsafe_allow_html=True)


def render_live_context_section(live_context: LiveContextBundle) -> None:
    highlight_items = build_live_highlight_items(live_context)
    if not highlight_items and not live_context.attribution.warnings:
        return

    st.subheader("Live MCP Highlights")
    st.caption(
        "Public MCP tooling augments the demo datasets when available. "
        "Core comparison tables remain deterministic in this version."
    )

    if highlight_items:
        for item in highlight_items:
            st.markdown(f"- {escape(item)}")

    for warning in live_context.attribution.warnings:
        st.info(warning)



@st.cache_data
def load_brand_logo_data_uri(brand: str) -> str | None:
    asset_path = LOGO_DIR / f"{brand.lower()}.png"
    if not asset_path.exists():
        return None

    encoded_logo = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded_logo}"


def build_brand_logo_data_uri(brand: str) -> str:
    logo_data_uri = load_brand_logo_data_uri(brand)
    if logo_data_uri:
        return logo_data_uri

    style = BRAND_TILE_STYLES.get(
        brand,
        {"background": "#F4F4F4", "foreground": "#111111", "accent": "#666666"},
    )
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="360" height="160" viewBox="0 0 360 160">
      <rect width="360" height="160" rx="28" fill="{style["background"]}"/>
      <rect x="18" y="18" width="324" height="124" rx="22" fill="none" stroke="{style["accent"]}" stroke-width="6"/>
      <text x="180" y="92" text-anchor="middle" font-size="34" font-family="Arial, Helvetica, sans-serif"
        font-weight="700" letter-spacing="1.2" fill="{style["foreground"]}">{brand.upper()}</text>
    </svg>
    """.strip()
    encoded_svg = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded_svg}"


def render_brand_tile_styles() -> None:
    st.markdown(
        """
        <style>
        [class*="st-key-brand-tile-"] {
            position: relative;
            min-height: 208px;
        }

        [class*="st-key-brand-tile-"] [data-testid="stCheckbox"] {
            position: absolute;
            inset: 0;
            z-index: 3;
            margin: 0;
            opacity: 0;
            height: 208px;
        }

        [class*="st-key-brand-tile-"] [data-testid="stCheckbox"] label,
        [class*="st-key-brand-tile-"] [data-testid="stCheckbox"] > div {
            width: 100%;
            height: 100%;
            display: block;
            cursor: pointer;
        }

        [class*="st-key-brand-tile-"] [data-testid="stCheckbox"] input {
            width: 100%;
            height: 100%;
            cursor: pointer;
        }

        [class*="st-key-brand-tile-"] .brand-tile-card {
            pointer-events: none;
            min-height: 208px;
            height: 208px;
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        }

        [class*="st-key-brand-tile-"]:hover .brand-tile-card {
            transform: translateY(-2px);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brand_tile(brand: str, is_selected: bool) -> str:
    status_text = "Selected" if is_selected else "Not selected"
    status_background = "#E8F5E9" if is_selected else "#F5F5F5"
    status_color = "#1B5E20" if is_selected else "#555555"
    ring_color = SELECTED_TILE_BORDER if is_selected else UNSELECTED_TILE_BORDER
    logo_data_uri = build_brand_logo_data_uri(brand)

    return f"""
    <div class="brand-tile-card" style="
        border: 5px solid {ring_color};
        border-radius: 18px;
        padding: 14px 14px 10px;
        background: #FFFFFF;
        min-height: 208px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
    ">
      <div style="
          height: 132px;
          border-radius: 14px;
          background: #F8FAFC;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 14px;
      ">
        <img
          src="{logo_data_uri}"
          alt="{brand} logo"
          style="
              width: 100%;
              height: 100%;
              object-fit: contain;
              object-position: center;
          "
        />
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
        <div style="font-weight: 600; color: #111827;">{brand}</div>
        <div style="
            font-size: 12px;
            font-weight: 700;
            color: {status_color};
            background: {status_background};
            border-radius: 999px;
            padding: 4px 10px;
        ">{status_text}</div>
      </div>
    </div>
    """


def render_brand_tiles(available_brands: list[str]) -> list[str]:
    st.markdown("**Step 1: Select Brands for Comparison**")
    render_brand_tile_styles()
    tile_columns = st.columns(min(len(available_brands), 4))
    selected_brands: list[str] = []

    for index, brand in enumerate(available_brands):
        state_key = f"brand_filter::{brand}"
        if state_key not in st.session_state:
            st.session_state[state_key] = True

        with tile_columns[index % len(tile_columns)]:
            with st.container(key=f"brand-tile-{brand.lower()}"):
                is_selected = st.checkbox(
                    f"Toggle {brand}",
                    key=state_key,
                    label_visibility="collapsed",
                )
                st.markdown(
                    render_brand_tile(brand, is_selected),
                    unsafe_allow_html=True,
                )
                if is_selected:
                    selected_brands.append(brand)

    return selected_brands


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

    selected_brands = render_brand_tiles(available_brands)

    st.divider()


    st.markdown("**Step 2: Choose What to Compare**")

    selected_domain = st.selectbox("Select the comparison domain:", options=DOMAINS)

    if len(selected_brands) < 2:
        st.warning("Select at least two brands to generate a meaningful comparison.")
        return

    try:
        live_context = get_live_context(selected_brands, selected_domain)
    except ValueError as exc:
        live_context = LiveContextBundle(
            domain=selected_domain,
            attribution=SourceAttribution(
                mode="curated",
                warnings=(f"MCP configuration error: {exc}",),
            ),
        )

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

    render_source_status_strip(live_context.attribution)

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
            #title=f"{selected_domain} metrics by brand",
        )
        figure.update_layout(legend_title_text="")
        st.plotly_chart(figure, use_container_width=True)

    render_live_context_section(live_context)

    st.divider()

    st.markdown("**Step 3: Generate AI Insight for Your Selections**")


    cache_key = f"analysis::{selected_domain}::{','.join(sorted(selected_brands))}"
    if st.button("Generate AI Insight", type="primary"):
        with st.spinner("Generating structured analysis..."):
            analysis = generate_brand_analysis(
                selected_brands,
                selected_domain,
                comparison["llm_payload"],
                live_context=live_context,
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
