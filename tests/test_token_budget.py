"""Unit tests for the segmenter's pure token-budget helpers.

Closes RFC 0015 gap 9: ``assert_context_budget``,
``estimate_segmenter_prompt_tokens``, ``should_adaptively_split_window``, and
``split_message_window`` were previously exercised only via integration
tests. These tests pin the math directly without a database, LLM, or HTTP.
"""

from __future__ import annotations

import pytest

from engram.segmenter import (
    ADAPTIVE_SPLIT_MAX_DEPTH,
    CONTEXT_GUARD_MARGIN_TOKENS,
    ConversationMessage,
    MessageWindow,
    SegmentationError,
    SegmenterContextBudgetError,
    assert_context_budget,
    estimate_segmenter_prompt_tokens,
    should_adaptively_split_window,
    split_message_window,
)


def make_message(
    message_id: str,
    *,
    sequence_index: int = 0,
    role: str = "user",
    content_text: str = "hello",
    privacy_tier: int = 1,
) -> ConversationMessage:
    return ConversationMessage(
        id=message_id,
        sequence_index=sequence_index,
        role=role,
        content_text=content_text,
        privacy_tier=privacy_tier,
    )


# ---------------------------------------------------------------------------
# estimate_segmenter_prompt_tokens
# ---------------------------------------------------------------------------


def test_estimate_tokens_empty_prompt_returns_scaffold_overhead() -> None:
    """Even an empty user prompt costs the system prompt + template scaffold."""
    estimate = estimate_segmenter_prompt_tokens("")
    # The scaffold (system prompt + 512-char template overhead) is always
    # billed. A positive integer that is not zero confirms this.
    assert isinstance(estimate, int)
    assert estimate > 0


def test_estimate_tokens_short_prompt_exceeds_empty() -> None:
    """Adding any content must raise the estimate above the empty baseline."""
    baseline = estimate_segmenter_prompt_tokens("")
    short = estimate_segmenter_prompt_tokens("hello world")
    assert short > baseline


def test_estimate_tokens_scales_roughly_linearly_with_repeated_content() -> None:
    """Doubling the prompt content increases the estimate, bounded by 2x."""
    base_prompt = "hello world! "
    one = estimate_segmenter_prompt_tokens(base_prompt)
    two = estimate_segmenter_prompt_tokens(base_prompt * 2)
    one_excess = one - estimate_segmenter_prompt_tokens("")
    two_excess = two - estimate_segmenter_prompt_tokens("")
    # The per-content delta should approximately double when content doubles.
    # Scaffold overhead is shared, so we compare excess-over-baseline.
    assert two_excess >= 2 * one_excess - 1
    assert two_excess <= 2 * one_excess + 1


def test_estimate_tokens_long_prompt_substantially_larger_than_short() -> None:
    """A 1000-char message should cost meaningfully more than a 10-char message."""
    short = estimate_segmenter_prompt_tokens("a" * 10)
    long = estimate_segmenter_prompt_tokens("a" * 1000)
    assert long > short
    # Difference should be on the order of (1000 - 10) / chars_per_token (~2.5)
    # which is a few hundred tokens.
    assert (long - short) >= 300


def test_estimate_tokens_locks_realistic_value() -> None:
    """Regression-pin the integer output for one realistic windowed prompt.

    This catches silent shifts in scaffold size or chars-per-token.
    """
    realistic = (
        '<conversation><message id="m1">hello</message></conversation>'
    )
    assert estimate_segmenter_prompt_tokens(realistic) == 275


# ---------------------------------------------------------------------------
# assert_context_budget
# ---------------------------------------------------------------------------


def test_assert_context_budget_within_window_does_not_raise() -> None:
    """A small prompt with a generous window must pass without raising."""
    assert_context_budget("hello", max_tokens=128, context_window=8192) is None


def test_assert_context_budget_none_window_skips_check() -> None:
    """When context_window is None, even an oversize prompt must pass."""
    # No raise expected — None means "unknown context, fail-open".
    assert_context_budget(
        "x" * 1_000_000,
        max_tokens=999_999,
        context_window=None,
    ) is None


def test_assert_context_budget_over_budget_raises() -> None:
    """A prompt that exceeds context_window raises SegmenterContextBudgetError."""
    # Empty prompt scaffold ~= 251 tokens. With max_tokens=100 and margin=1024,
    # requested ~= 1375. A context_window of 256 is far below that.
    with pytest.raises(SegmenterContextBudgetError, match="context shift"):
        assert_context_budget("", max_tokens=100, context_window=256)


def test_assert_context_budget_boundary_at_window_raises() -> None:
    """Locks current ``>=`` semantics: equality is treated as over-budget."""
    estimate = estimate_segmenter_prompt_tokens("")
    boundary_window = estimate + 1 + CONTEXT_GUARD_MARGIN_TOKENS
    # requested_tokens == boundary_window triggers the >= branch.
    with pytest.raises(SegmenterContextBudgetError):
        assert_context_budget("", max_tokens=1, context_window=boundary_window)
    # One token of headroom passes silently.
    assert_context_budget("", max_tokens=1, context_window=boundary_window + 1) is None


def test_assert_context_budget_raises_subclass_of_segmentation_error() -> None:
    """The raised exception is a SegmentationError, so callers can catch broadly."""
    with pytest.raises(SegmentationError):
        assert_context_budget("", max_tokens=100, context_window=256)


# ---------------------------------------------------------------------------
# should_adaptively_split_window
# ---------------------------------------------------------------------------


def test_should_adaptively_split_window_single_message_returns_false() -> None:
    """A window of one message cannot be split further regardless of cause."""
    window = MessageWindow(index=0, messages=[make_message("m1")])
    exc = SegmenterContextBudgetError("context shift")
    assert should_adaptively_split_window(exc, window, 0) is False


def test_should_adaptively_split_window_budget_error_returns_true() -> None:
    """A multi-message window hitting a budget error should split."""
    window = MessageWindow(
        index=0,
        messages=[make_message("m1"), make_message("m2", sequence_index=1)],
    )
    exc = SegmenterContextBudgetError("context shift")
    assert should_adaptively_split_window(exc, window, 0) is True


def test_should_adaptively_split_window_at_max_depth_returns_false() -> None:
    """At ADAPTIVE_SPLIT_MAX_DEPTH the loop must stop, even on a budget error."""
    window = MessageWindow(
        index=0,
        messages=[make_message("m1"), make_message("m2", sequence_index=1)],
    )
    exc = SegmenterContextBudgetError("context shift")
    assert (
        should_adaptively_split_window(exc, window, ADAPTIVE_SPLIT_MAX_DEPTH)
        is False
    )
    # Just below the cap: still splittable.
    assert (
        should_adaptively_split_window(
            exc, window, ADAPTIVE_SPLIT_MAX_DEPTH - 1
        )
        is True
    )


def test_should_adaptively_split_window_unrelated_error_returns_false() -> None:
    """A generic non-truncation SegmentationError should not trigger a split."""
    window = MessageWindow(
        index=0,
        messages=[make_message("m1"), make_message("m2", sequence_index=1)],
    )
    exc = SegmentationError("schema mismatch on segment 0")
    assert should_adaptively_split_window(exc, window, 0) is False


def test_should_adaptively_split_window_truncation_text_returns_true() -> None:
    """Truncation-shaped text (e.g. unterminated JSON) qualifies as splittable."""
    window = MessageWindow(
        index=0,
        messages=[make_message("m1"), make_message("m2", sequence_index=1)],
    )
    exc = SegmentationError("unterminated string while decoding JSON")
    assert should_adaptively_split_window(exc, window, 0) is True


# ---------------------------------------------------------------------------
# split_message_window
# ---------------------------------------------------------------------------


def test_split_message_window_partitions_into_singletons() -> None:
    """A window with N messages produces N single-message sub-windows.

    Sub-window message ids in concatenation must equal the original; nothing
    is lost or duplicated.
    """
    messages = [
        make_message("m1", sequence_index=0),
        make_message("m2", sequence_index=1),
        make_message("m3", sequence_index=2),
    ]
    window = MessageWindow(index=4, messages=messages)
    parts = split_message_window(window)
    assert len(parts) == len(messages)
    flattened_ids = [m.id for part in parts for m in part.messages]
    assert flattened_ids == [m.id for m in messages]
    for part in parts:
        assert len(part.messages) == 1
        # The sub-window keeps the parent index so retry diagnostics map back.
        assert part.index == window.index


def test_split_message_window_singletons_are_smaller_inputs() -> None:
    """Each produced sub-window has fewer messages than the original (the
    post-split predicate the splitter must guarantee).
    """
    messages = [
        make_message("m1", sequence_index=0),
        make_message("m2", sequence_index=1, content_text="x" * 5_000),
        make_message("m3", sequence_index=2),
    ]
    window = MessageWindow(index=0, messages=messages)
    parts = split_message_window(window)
    assert len(parts) > 1
    for part in parts:
        assert len(part.messages) < len(window.messages)


def test_split_message_window_single_message_is_noop() -> None:
    """A window of one message is returned unchanged (identity, not a copy)."""
    window = MessageWindow(index=0, messages=[make_message("only")])
    result = split_message_window(window)
    assert len(result) == 1
    assert result[0] is window


def test_split_message_window_filters_truncated_ids_per_child() -> None:
    """Each sub-window only carries truncated ids that match its own message."""
    messages = [
        make_message("m1", sequence_index=0),
        make_message("m2", sequence_index=1),
        make_message("m3", sequence_index=2),
    ]
    window = MessageWindow(
        index=2,
        messages=messages,
        truncated_message_ids=["m2"],
    )
    parts = split_message_window(window)
    # Child carrying m2 should keep the truncation marker; siblings drop it.
    by_id = {part.messages[0].id: part for part in parts}
    assert by_id["m1"].truncated_message_ids == []
    assert by_id["m2"].truncated_message_ids == ["m2"]
    assert by_id["m3"].truncated_message_ids == []
