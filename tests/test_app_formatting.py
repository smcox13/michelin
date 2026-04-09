from __future__ import annotations

from app import (
    build_evidence_list_html,
    build_evidence_meta_html,
    build_report_pdf_url,
    format_analysis_paragraphs,
    sort_evidence_payload,
)


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


def test_build_evidence_list_html_renders_labels_pages_and_escaped_text():
    result = build_evidence_list_html(
        (
            "Performance Driver",
            "Capital Allocation / Priority",
            "Headwind / Risk",
        ),
        [
            {"text": "Premium mix improved <clearly>.", "page": 13},
            {"text": "Cash stayed strong.", "page": 31},
            {"text": "Tariffs remained a watch-out.", "page": 21},
        ],
    )

    assert "Performance Driver" in result
    assert "p. 13" in result
    assert "&lt;clearly&gt;" in result
    assert "Tariffs remained a watch-out." in result


def test_sort_evidence_payload_orders_brands_alphabetically():
    result = sort_evidence_payload(
        [
            {"brand": "Michelin", "report_year": 2025, "report_summary": "", "evidence": []},
            {"brand": "Bridgestone", "report_year": 2025, "report_summary": "", "evidence": []},
            {"brand": "continental", "report_year": 2025, "report_summary": "", "evidence": []},
        ]
    )

    assert [item["brand"] for item in result] == [
        "Bridgestone",
        "continental",
        "Michelin",
    ]


def test_build_report_pdf_url_returns_static_path_for_existing_report():
    assert build_report_pdf_url("Michelin", 2025) == "/app/static/reports/michelin-2025.pdf"


def test_build_evidence_meta_html_renders_new_tab_link_for_existing_report():
    result = build_evidence_meta_html("Michelin", 2025)

    assert 'class="evidence-meta evidence-meta-link"' in result
    assert 'href="/app/static/reports/michelin-2025.pdf"' in result
    assert 'target="_blank"' in result
    assert "Annual report 2025" in result


def test_build_evidence_meta_html_falls_back_to_plain_badge_for_missing_report():
    result = build_evidence_meta_html("Michelin", 2024)

    assert result == '<div class="evidence-meta">Annual report 2024</div>'
