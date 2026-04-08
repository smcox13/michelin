from __future__ import annotations

from app import format_analysis_paragraphs


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
