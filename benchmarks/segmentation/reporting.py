"""Human-readable reports for segmentation benchmark result files."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.segmentation.results import output_from_record, parent_from_record
from benchmarks.segmentation.scoring import predicted_boundaries_for_parent
from benchmarks.segmentation.strategies import BenchmarkParent, SegmentProposal, StrategyOutput


REPORT_SCHEMA_VERSION = "segmentation-benchmark-report.v1"


@dataclass(frozen=True)
class ParentStrategyRecord:
    parent: BenchmarkParent
    output: StrategyOutput
    duration_seconds: float | None


@dataclass(frozen=True)
class ReportInput:
    run: dict[str, Any]
    records_by_strategy: dict[str, list[ParentStrategyRecord]]
    parent_order: tuple[str, ...]
    parents_by_id: dict[str, BenchmarkParent]


def write_report_files(
    *,
    run_json_path: str | Path,
    output_dir: str | Path | None = None,
    report_format: str = "markdown",
    max_parents: int = 50,
) -> list[Path]:
    run_json_path = Path(run_json_path)
    output_root = Path(output_dir) if output_dir else run_json_path.parent
    output_root.mkdir(parents=True, exist_ok=True)
    report_input = load_report_input(run_json_path)

    paths: list[Path] = []
    if report_format in {"markdown", "both"}:
        path = output_root / "report.md"
        path.write_text(
            generate_markdown_report(report_input, max_parents=max_parents),
            encoding="utf-8",
        )
        paths.append(path)
    if report_format in {"html", "both"}:
        path = output_root / "report.html"
        path.write_text(
            generate_html_report(report_input, max_parents=max_parents),
            encoding="utf-8",
        )
        paths.append(path)
    if not paths:
        raise ValueError(f"unsupported report format: {report_format}")
    return paths


def load_report_input(run_json_path: str | Path) -> ReportInput:
    run_json_path = Path(run_json_path)
    run = json.loads(run_json_path.read_text(encoding="utf-8"))
    parents_path = run_json_path.parent / run.get("parents_path", "parents.jsonl")
    records_by_strategy: dict[str, list[ParentStrategyRecord]] = {}
    parent_order: list[str] = []
    parents_by_id: dict[str, BenchmarkParent] = {}

    with parents_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            strategy_name = record["strategy_name"]
            parent = parent_from_record(record["parent"])
            output = output_from_record(record)
            duration = record.get("duration_seconds")
            duration_seconds = float(duration) if isinstance(duration, (int, float)) else None
            records_by_strategy.setdefault(strategy_name, []).append(
                ParentStrategyRecord(
                    parent=parent,
                    output=output,
                    duration_seconds=duration_seconds,
                )
            )
            if parent.parent_id not in parents_by_id:
                parent_order.append(parent.parent_id)
                parents_by_id[parent.parent_id] = parent

    return ReportInput(
        run=run,
        records_by_strategy=records_by_strategy,
        parent_order=tuple(parent_order),
        parents_by_id=parents_by_id,
    )


def generate_markdown_report(report_input: ReportInput, *, max_parents: int) -> str:
    run = report_input.run
    lines = [
        f"# Segmentation Benchmark Report",
        "",
        f"Report schema: `{REPORT_SCHEMA_VERSION}`",
        "",
        "## Run",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Run ID | `{run.get('run_id')}` |",
        f"| Created | `{run.get('created_at')}` |",
        f"| Git commit | `{run.get('git_commit')}` |",
        f"| Dataset | `{dataset_label(run)}` |",
        f"| Benchmark tier | `{run.get('benchmark_tier', 'unknown')}` |",
        f"| Selection caveat | `{run.get('selection_caveat', 'unknown')}` |",
        f"| Operational model strategy | `{run.get('operational_model_strategy', 'unknown')}` |",
        f"| Sample plan | `{sample_plan_label(run)}` |",
        f"| Threshold set | `{threshold_set_label(run)}` |",
        f"| Scoring | `{run.get('scoring_implementation_version')}` |",
        f"| Token estimator | `{run.get('benchmark_token_estimator_version')}` |",
        "",
        "## Strategy Comparison",
        "",
        markdown_strategy_table(run),
        "",
        "## Segment Lengths",
        "",
        markdown_length_table(run),
        "",
        "## Fragmentation",
        "",
        markdown_fragmentation_table(run),
        "",
        "## Early-Signal Verdicts",
        "",
        markdown_verdict_table(run),
        "",
        "## Backend Errors",
        "",
        markdown_backend_errors(run),
        "",
        "## Parent Boundary Diffs",
        "",
    ]
    lines.extend(markdown_parent_diffs(report_input, max_parents=max_parents))
    return "\n".join(lines).rstrip() + "\n"


def generate_html_report(report_input: ReportInput, *, max_parents: int) -> str:
    markdown_lines = generate_markdown_report(
        report_input, max_parents=max_parents
    ).splitlines()
    body_parts: list[str] = []
    in_table = False
    table_rows: list[str] = []
    in_code = False
    code_lines: list[str] = []

    for line in markdown_lines:
        if line.startswith("```"):
            if in_code:
                body_parts.append(f"<pre>{html.escape(chr(10).join(code_lines))}</pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if line.startswith("|"):
            if "---" in line:
                continue
            in_table = True
            table_rows.append(line)
            continue
        if in_table:
            body_parts.append(markdown_table_to_html(table_rows))
            table_rows = []
            in_table = False
        if line.startswith("# "):
            body_parts.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body_parts.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            body_parts.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("- "):
            body_parts.append(f"<p>{html.escape(line)}</p>")
        elif line.strip():
            body_parts.append(f"<p>{html.escape(line)}</p>")
    if in_table:
        body_parts.append(markdown_table_to_html(table_rows))
    if in_code:
        body_parts.append(f"<pre>{html.escape(chr(10).join(code_lines))}</pre>")

    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<title>Segmentation Benchmark Report</title>\n"
        "<style>\n"
        "body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:2rem;"
        "line-height:1.45;color:#202124;background:#fafafa}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0;background:white}"
        "th,td{border:1px solid #d0d7de;padding:.45rem;text-align:left;vertical-align:top}"
        "th{background:#f3f4f6}pre{background:#111827;color:#f9fafb;padding:1rem;"
        "overflow:auto;border-radius:6px}code{font-family:ui-monospace,monospace}"
        "h1,h2,h3{line-height:1.2}.muted{color:#6b7280}"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        + "\n".join(body_parts)
        + "\n</body>\n</html>\n"
    )


def markdown_strategy_table(run: dict[str, Any]) -> str:
    rows = [
        "| Strategy | Kind | Parents | Segments | Schema valid | Provenance valid | Strict F1 | W-F1 +/-1 | W-F1 +/-2 | P_k | WindowDiff | Throughput/s | Claims |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    strategy_meta = {item["name"]: item for item in run.get("strategy_results", [])}
    for strategy_name in sorted(run.get("metrics", {})):
        metrics = run["metrics"][strategy_name]
        operational = metrics.get("operational", {})
        segmentation = metrics.get("segmentation", {})
        denominators = metrics.get("denominators", {})
        claims = metrics.get("claim_utility", {})
        rows.append(
            "| "
            + " | ".join(
                [
                    f"`{strategy_name}`",
                    str(strategy_meta.get(strategy_name, {}).get("kind", "")),
                    str(denominators.get("parents", "")),
                    str(denominators.get("segments", "")),
                    format_percent(operational.get("schema_valid_rate")),
                    format_percent(operational.get("provenance_valid_rate")),
                    format_metric(nested_metric(segmentation, "strict_boundary", "f1")),
                    format_metric(
                        nested_metric(
                            segmentation,
                            "window_tolerant_f1",
                            "plus_minus_1",
                            "f1",
                        )
                    ),
                    format_metric(
                        nested_metric(
                            segmentation,
                            "window_tolerant_f1",
                            "plus_minus_2",
                            "f1",
                        )
                    ),
                    format_metric(segmentation.get("pk")),
                    format_metric(segmentation.get("windowdiff")),
                    format_metric(operational.get("parent_throughput_per_second")),
                    str(claims.get("status", "")),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def markdown_length_table(run: dict[str, Any]) -> str:
    rows = [
        "| Strategy | Avg segments/parent | p10 tokens | p50 tokens | p90 tokens | <50 | <100 | <200 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for strategy_name in sorted(run.get("metrics", {})):
        metrics = run["metrics"][strategy_name]
        operational = metrics.get("operational", {})
        segmentation = metrics.get("segmentation", {})
        subfloors = operational.get("sub_floor_fragment_counts", {})
        rows.append(
            "| "
            + " | ".join(
                [
                    f"`{strategy_name}`",
                    format_metric(segmentation.get("segment_count_average")),
                    format_metric(segmentation.get("segment_token_length_p10")),
                    format_metric(segmentation.get("segment_token_length_p50")),
                    format_metric(segmentation.get("segment_token_length_p90")),
                    str(subfloors.get("50", "")),
                    str(subfloors.get("100", "")),
                    str(subfloors.get("200", "")),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def markdown_fragmentation_table(run: dict[str, Any]) -> str:
    rows = [
        "| Strategy | Ratio avg | Abs distance avg | No-boundary false split rate | <100 rate | Adjacent tiny rate | Duplicate adjacent rate | >2x expected parents |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for strategy_name in sorted(run.get("metrics", {})):
        fragmentation = run["metrics"][strategy_name].get("fragmentation", {})
        rows.append(
            "| "
            + " | ".join(
                [
                    f"`{strategy_name}`",
                    format_metric(
                        fragmentation.get(
                            "predicted_expected_segment_count_ratio_average"
                        )
                    ),
                    format_metric(
                        fragmentation.get("absolute_segment_count_distance_average")
                    ),
                    format_percent(fragmentation.get("no_boundary_false_split_rate")),
                    format_percent(fragmentation.get("sub_100_fragment_rate")),
                    format_percent(fragmentation.get("adjacent_tiny_fragment_rate")),
                    format_percent(fragmentation.get("duplicate_adjacent_rate")),
                    format_metric(
                        fragmentation.get("parents_more_than_twice_expected_count")
                    ),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def markdown_verdict_table(run: dict[str, Any]) -> str:
    verdicts = run.get("early_signal_verdicts") or {}
    rows = [
        "| Strategy | Verdict | Caveat | Hard warnings | Blocking failures | Summary |",
        "|---|---|---|---:|---:|---|",
    ]
    if not isinstance(verdicts, dict) or not verdicts:
        rows.append("| n/a | n/a | n/a | 0 | 0 | No early-signal verdicts in this result. |")
        return "\n".join(rows)
    for strategy_name in sorted(verdicts):
        verdict = verdicts[strategy_name]
        if not isinstance(verdict, dict):
            continue
        rows.append(
            "| "
            + " | ".join(
                [
                    f"`{strategy_name}`",
                    str(verdict.get("verdict", "")),
                    str(verdict.get("selection_caveat", "")),
                    str(len(verdict.get("hard_warnings") or [])),
                    str(len(verdict.get("blocking_failures") or [])),
                    escape_table_text(str(verdict.get("summary", ""))),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def markdown_backend_errors(run: dict[str, Any]) -> str:
    rows = [
        "| Strategy | connect_refused | read_timeout | http_5xx | grammar_stack_empty | cuda_oom | backend_wedge_post_smoke | unknown |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for strategy_name in sorted(run.get("metrics", {})):
        errors = run["metrics"][strategy_name].get("operational", {}).get(
            "backend_error_counts", {}
        )
        rows.append(
            "| "
            + " | ".join(
                [
                    f"`{strategy_name}`",
                    str(errors.get("connect_refused", 0)),
                    str(errors.get("read_timeout", 0)),
                    str(errors.get("http_5xx", 0)),
                    str(errors.get("grammar_stack_empty", 0)),
                    str(errors.get("cuda_oom", 0)),
                    str(errors.get("backend_wedge_post_smoke", 0)),
                    str(errors.get("unknown", 0)),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def markdown_parent_diffs(report_input: ReportInput, *, max_parents: int) -> list[str]:
    lines: list[str] = []
    shown_parent_ids = report_input.parent_order[:max_parents]
    records_by_parent_strategy: dict[tuple[str, str], ParentStrategyRecord] = {}
    for strategy_name, records in report_input.records_by_strategy.items():
        for record in records:
            records_by_parent_strategy[(record.parent.parent_id, strategy_name)] = record

    for parent_id in shown_parent_ids:
        parent = report_input.parents_by_id[parent_id]
        expected = tuple(parent.expected_boundaries or ())
        lines.extend(
            [
                f"### `{parent_id}`",
                "",
                f"- Messages: {len(parent.messages)}",
                f"- Expected boundaries: {format_boundaries(expected)}",
                "",
                "```text",
                f"positions: {boundary_position_line(len(parent.messages))}",
                f"expected:  {boundary_diagram(len(parent.messages), expected)}",
                "```",
                "",
                "| Strategy | Predicted | Missing | Extra | Segments |",
                "|---|---|---|---|---|",
            ]
        )
        strategy_diagrams: list[tuple[str, tuple[int, ...]]] = []
        for strategy_name in sorted(report_input.records_by_strategy):
            record = records_by_parent_strategy.get((parent_id, strategy_name))
            if record is None:
                continue
            predicted = predicted_boundaries_for_parent(parent, record.output.segments)
            strategy_diagrams.append((strategy_name, predicted))
            missing = sorted(set(expected) - set(predicted))
            extra = sorted(set(predicted) - set(expected))
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{strategy_name}`",
                        format_boundaries(predicted),
                        format_boundaries(tuple(missing)),
                        format_boundaries(tuple(extra)),
                        format_segment_spans(parent, record.output.segments),
                    ]
                )
                + " |"
            )
        lines.append("")
        for strategy_name, predicted in strategy_diagrams:
            lines.extend(
                [
                    "```text",
                    f"{strategy_name}: {boundary_diagram(len(parent.messages), predicted)}",
                    "```",
                    "",
                ]
            )
    if len(report_input.parent_order) > max_parents:
        lines.append(
            f"_Showing {max_parents} of {len(report_input.parent_order)} parents. "
            "Use `--max-parents` to raise the report limit._"
        )
    return lines


def markdown_table_to_html(rows: list[str]) -> str:
    parsed_rows = [
        [cell.strip().strip("`") for cell in row.strip("|").split("|")]
        for row in rows
    ]
    if not parsed_rows:
        return ""
    header = parsed_rows[0]
    body = parsed_rows[1:]
    html_rows = [
        "<thead><tr>"
        + "".join(f"<th>{html.escape(cell)}</th>" for cell in header)
        + "</tr></thead>"
    ]
    html_rows.append(
        "<tbody>"
        + "".join(
            "<tr>"
            + "".join(f"<td>{html.escape(cell)}</td>" for cell in row)
            + "</tr>"
            for row in body
        )
        + "</tbody>"
    )
    return "<table>" + "".join(html_rows) + "</table>"


def dataset_label(run: dict[str, Any]) -> str:
    dataset = run.get("dataset", {})
    return f"{dataset.get('name')} {dataset.get('version')} ({dataset.get('source')})"


def sample_plan_label(run: dict[str, Any]) -> str:
    sample_plan = run.get("sample_plan")
    if not isinstance(sample_plan, dict):
        return "none"
    return (
        f"{sample_plan.get('benchmark_tier')} seed={sample_plan.get('sample_seed')} "
        f"selected={sample_plan.get('selected_parent_count')}/"
        f"{sample_plan.get('target_sample_size')}"
    )


def threshold_set_label(run: dict[str, Any]) -> str:
    thresholds = run.get("early_signal_thresholds")
    if not isinstance(thresholds, dict):
        return "none"
    return f"{thresholds.get('threshold_set_id')} ({thresholds.get('source')})"


def nested_metric(value: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(value, dict):
            return value
        value = value.get(key)
    return value


def format_metric(value: Any) -> str:
    if value == "not_applicable":
        return "n/a"
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def format_percent(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value) * 100:.1f}%"
    return format_metric(value)


def escape_table_text(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def format_boundaries(boundaries: tuple[int, ...]) -> str:
    if not boundaries:
        return "none"
    return ", ".join(str(boundary) for boundary in boundaries)


def boundary_position_line(message_count: int) -> str:
    if message_count <= 1:
        return "none"
    return " ".join(str(position) for position in range(1, message_count))


def boundary_diagram(message_count: int, boundaries: tuple[int, ...]) -> str:
    if message_count <= 1:
        return "none"
    boundary_set = set(boundaries)
    return " ".join("|" if position in boundary_set else "." for position in range(1, message_count))


def format_segment_spans(
    parent: BenchmarkParent, segments: tuple[SegmentProposal, ...]
) -> str:
    sequence_by_id = {message.id: message.sequence_index for message in parent.messages}
    spans: list[str] = []
    for segment in segments:
        sequences = [
            sequence_by_id[message_id]
            for message_id in segment.message_ids
            if message_id in sequence_by_id
        ]
        if not sequences:
            spans.append("?")
        elif min(sequences) == max(sequences):
            spans.append(str(min(sequences)))
        else:
            spans.append(f"{min(sequences)}-{max(sequences)}")
    return ", ".join(spans) if spans else "none"
