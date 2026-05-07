"""Pure-function tests for the Gemini HTML-to-text path.

Addresses RFC 0015 gap 5: ``TextHTMLParser`` (and the ``html_to_text``
wrapper) had no direct tests, and Gemini ingest was thinner than the other
loaders. These tests lock current behavior of the parser so future drift
in the HTML-to-text pipeline is caught loudly.

No DB / no fixtures: every case feeds a small inline HTML string and
asserts the parser's text output. The expected values were captured from
the parser's actual behavior at the time of writing; see RFC 0015 § 5.
"""

from __future__ import annotations

import pytest

from engram.gemini_export import (
    TextHTMLParser,
    activity_external_id,
    activity_title,
    html_to_text,
    prompt_text_from_title,
)


# ---------------------------------------------------------------------------
# TextHTMLParser.text() — locks current output for representative HTML shapes.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "html_input", "expected"),
    [
        # Plain text passes through; <p> wrappers add whitespace that is
        # collapsed back to a single non-empty line.
        ("plain_paragraph", "<p>hello world</p>", "hello world"),
        # Nested inline formatting: <b>/<i> are not in the block-tag set,
        # so their boundaries become ordinary spaces between data chunks.
        ("nested_formatting", "<p>hello <b>bold</b> <i>italic</i></p>", "hello bold italic"),
        # <pre><code> are not in the block-tag set; the text comes through
        # but internal newlines/indentation are not preserved (whitespace
        # is collapsed by ``" ".join(line.split())`` per non-empty line).
        ("code_block", '<pre><code>print("hi")</code></pre>', 'print("hi")'),
        # Multiple <p> elements yield paragraphs separated by a single
        # newline (consecutive blank lines are dropped).
        (
            "multiple_paragraphs",
            "<p>first paragraph</p><p>second paragraph</p>",
            "first paragraph\nsecond paragraph",
        ),
        # Unordered list: <li> is a block tag, so each item lands on its
        # own line.
        ("unordered_list", "<ul><li>a</li><li>b</li></ul>", "a\nb"),
        # Empty input yields an empty string from the parser (the
        # ``html_to_text`` wrapper turns this into ``None``; tested below).
        ("empty_input", "", ""),
        # HTML entities are decoded once by ``convert_charrefs=True``.
        ("html_entities_top_level", "&amp; &lt; &gt;", "& < >"),
        # Malformed HTML must not crash; the parser emits the data it saw.
        ("malformed_unclosed", "<p>unclosed", "unclosed"),
        # Script/style tags are not stripped — their text content leaks
        # through. This is a regression-locking assertion, not an
        # endorsement of the behavior.
        ("script_tag_leaks", "<script>alert('xss')</script>hi", "alert('xss')hi"),
        ("style_tag_leaks", "<style>body{color:red}</style>visible", "body{color:red}visible"),
        # <br> is a block tag and emits a newline on the start tag.
        ("br_breaks_lines", "line1<br>line2<br>line3", "line1\nline2\nline3"),
        # Headers (h1/h2) are block tags.
        ("headers", "<h1>Title</h1><h2>Subtitle</h2>", "Title\nSubtitle"),
        # <div> is a block tag.
        ("divs", "<div>line1</div><div>line2</div>", "line1\nline2"),
        # Whitespace inside a paragraph is collapsed and the paragraph is
        # trimmed.
        ("whitespace_collapsed", "<p>  multiple   spaces  </p>", "multiple spaces"),
        # Tables: <tr> is a block tag but <td> is not, so cells in a row
        # are concatenated without a separator.
        (
            "table_rows",
            "<table><tr><td>a</td><td>b</td></tr><tr><td>c</td></tr></table>",
            "ab\nc",
        ),
        # Entity inside a paragraph is decoded by the parser.
        ("entities_inside_paragraph", "<p>foo &amp; bar</p>", "foo & bar"),
    ],
)
def test_text_html_parser_locks_output(label: str, html_input: str, expected: str) -> None:
    parser = TextHTMLParser()
    parser.feed(html_input)
    assert parser.text() == expected, label


# ---------------------------------------------------------------------------
# html_to_text wrapper — empty/whitespace inputs collapse to None.
# ---------------------------------------------------------------------------


def test_html_to_text_returns_none_for_empty_input() -> None:
    assert html_to_text("") is None


def test_html_to_text_returns_none_for_whitespace_only_html() -> None:
    assert html_to_text("<p>   </p>") is None


def test_html_to_text_strips_outer_whitespace() -> None:
    assert html_to_text("  <p>hello</p>  ") == "hello"


# ---------------------------------------------------------------------------
# Gemini-specific activity-id edge cases.
#
# RFC 0015 § 5 calls out "Gemini-specific activity-id edge cases". The
# parser itself has no ``activity-id`` attribute handling, but Gemini's
# conversation-level external id is derived from the activity payload's
# ``time`` field with a content-hash fallback. These tests lock that
# derivation so any future drift surfaces immediately.
# ---------------------------------------------------------------------------


def test_activity_external_id_uses_time_string_when_present() -> None:
    payload = {"time": "2026-04-28T08:53:43.029Z", "title": "Prompted hi"}
    assert activity_external_id(payload) == "2026-04-28T08:53:43.029Z"


def test_activity_external_id_falls_back_to_payload_hash_when_time_missing() -> None:
    external_id = activity_external_id({"title": "Prompted hi"})
    # Falls back to a sha256 hex digest of the canonical JSON payload.
    assert len(external_id) == 64
    assert all(ch in "0123456789abcdef" for ch in external_id)


def test_activity_external_id_falls_back_when_time_is_empty_string() -> None:
    # An empty ``time`` string is falsy, so the hash fallback fires —
    # the same payload always produces the same id, which protects
    # idempotency in ``validate_unique_payloads``.
    payload = {"time": "", "title": "Prompted hi"}
    first = activity_external_id(payload)
    second = activity_external_id(dict(payload))
    assert first == second
    assert len(first) == 64


def test_activity_title_strips_prompted_prefix() -> None:
    assert activity_title({"title": "Prompted Can one vinyl wrap motorcycle plastics?"}) == (
        "Can one vinyl wrap motorcycle plastics?"
    )


def test_activity_title_returns_none_when_title_missing_or_non_string() -> None:
    assert activity_title({}) is None
    assert activity_title({"title": 123}) is None


def test_prompt_text_from_title_returns_none_for_whitespace_only_prompt() -> None:
    # ``"Prompted "`` strips to an empty string — the helper returns None
    # rather than an empty prompt.
    assert prompt_text_from_title("Prompted ") is None
    assert prompt_text_from_title("Prompted    ") is None


def test_prompt_text_from_title_returns_none_for_non_prompted_titles() -> None:
    assert prompt_text_from_title("Searched for X") is None
