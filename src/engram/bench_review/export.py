"""Redacted exports and status rendering for RFC 0029 bench review."""

from __future__ import annotations

from pathlib import Path

from engram.bench_review import storage


class BenchReviewExportError(RuntimeError):
    """Raised when a redacted export cannot be written safely."""


def render_status(db_path: Path) -> str:
    """Render a compact CLI status summary."""
    summary = storage.summary(db_path)
    lines = [
        f"bench-review status: {summary['decided']}/{summary['total']} decided "
        f"({summary['remaining']} remaining)",
        "data states:",
    ]
    lines.extend(_count_lines(summary["by_state"]))
    lines.append("tags:")
    lines.extend(_count_lines(summary["by_tag"]))
    lines.append("decisions:")
    lines.extend(_count_lines(summary["by_decision"]))
    if summary.get("run_decision"):
        lines.append(f"run decision: {summary['run_decision_label']}")
    return "\n".join(lines) + "\n"


def export_markdown(
    *, db_path: Path, output_path: Path, repo_root: Path, allow_outside_reviews: bool = False
) -> Path:
    """Write a redacted Markdown export from scratch review state."""
    target = _checked_output_path(output_path, repo_root=repo_root, allow=allow_outside_reviews)
    session = storage.get_session(db_path)
    summary = storage.summary(db_path)
    rows = storage.list_segments(db_path)
    lines = [
        "# Bench Review Export",
        "",
        "This export is redacted. It must not contain segment text, claim text, "
        "evidence excerpts, or LLM responses.",
        "",
        "## Session",
        "",
        f"- Run: `{session['run_id']}`",
        f"- Slice: `{session['slice_path']}`",
        f"- Run artifact: `{session['run_path']}`",
        f"- Segment records: `{session['segments_path'] or 'not provided'}`",
        f"- Candidate prompt: `{session['candidate_prompt_version'] or 'unknown'}`",
        f"- Candidate model: `{session['candidate_model_version'] or 'unknown'}`",
        f"- Candidate profile: `{session['candidate_request_profile_version'] or 'unknown'}`",
        f"- Prior prompt: `{session['prior_prompt_version']}`",
        f"- Prior model: `{session['prior_model_version']}`",
        f"- Prior profile: `{session['prior_request_profile_version']}`",
        "",
        "## Summary",
        "",
        f"- Progress: `{summary['decided']}/{summary['total']}` decided",
        f"- Remaining: `{summary['remaining']}`",
    ]
    if summary.get("run_decision"):
        lines.append(f"- Run decision: `{summary['run_decision_label']}`")
    if summary.get("run_rationale"):
        lines.append(f"- Run note: {summary['run_rationale']}")
    lines.extend(["", "## Counts", "", "### Data states", ""])
    lines.extend(_markdown_counts(summary["by_state"]))
    lines.extend(["", "### Tags", ""])
    lines.extend(_markdown_counts(summary["by_tag"]))
    lines.extend(["", "### Decisions", ""])
    lines.extend(_markdown_counts(summary["by_decision"]))
    lines.extend(
        [
            "",
            "## Segments",
            "",
            "| Segment | State | Tags | Prior | Candidate | Decision | Note |",
            "|---------|-------|------|-------|-----------|----------|------|",
        ]
    )
    for row in rows:
        tags = ", ".join(__import__("json").loads(row["tags_json"]))
        lines.append(
            "| "
            f"`{row['segment_id']}` | `{row['data_state']}` | `{tags}` | "
            f"`{_count(row['prior_claim_count'])}` | "
            f"`{_count(row['candidate_claim_count'])}` | "
            f"`{row['decision'] or 'undecided'}` | "
            f"{_escape_cell(row['rationale'] or '')} |"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _checked_output_path(output_path: Path, *, repo_root: Path, allow: bool) -> Path:
    target = output_path if output_path.is_absolute() else repo_root / output_path
    resolved = target.resolve()
    reviews = (repo_root / "docs" / "reviews").resolve()
    if not allow and not _is_relative_to(resolved, reviews):
        raise BenchReviewExportError(
            f"export output must stay under {reviews} unless --allow-outside-reviews is set"
        )
    return resolved


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _count_lines(counts: object) -> list[str]:
    if not isinstance(counts, dict) or not counts:
        return ["  none"]
    return [f"  {key}: {value}" for key, value in counts.items()]


def _markdown_counts(counts: object) -> list[str]:
    if not isinstance(counts, dict) or not counts:
        return ["- none"]
    return [f"- `{key}`: `{value}`" for key, value in counts.items()]


def _count(value: object) -> str:
    return "n/a" if value is None else str(value)


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|")

