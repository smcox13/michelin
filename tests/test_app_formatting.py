from __future__ import annotations

from app import build_evidence_list_html, format_analysis_paragraphs


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
