"""Gold-set evaluation runner for context compiler output."""

from __future__ import annotations

import importlib
import json
import os
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

JsonObject = dict[str, Any]  # JSON reports preserve flexible compiler payloads.

CONTEXT_EVAL_SCHEMA_VERSION = "context_eval.item.v1"
CONTEXT_EVAL_RUNNER_VERSION = "context_eval.runner.v1"
CONTEXT_EVAL_DATASET_ENV_VAR = "ENGRAM_EVAL_DATASET_PATH"
CONTEXT_EVAL_DATASET_GOLD_FILENAME = "context_eval.gold.jsonl"
DEFAULT_PRIVACY_CEILING = 1
_WORD_PATTERN = re.compile(r"[A-Za-z0-9_]+")
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")


class ContextEvalError(RuntimeError):
    """Base error for context evaluation failures."""


class ContextEvalSchemaError(ContextEvalError):
    """Raised when a gold-set item does not match the eval schema."""


class ContextCompilerUnavailableError(ContextEvalError):
    """Raised when no context compiler callable is available."""


@dataclass(frozen=True)
class ContextCompileRequest:
    """Compiler request shape used by the eval runner seam."""

    query_text: str
    privacy_ceiling: int
    relevant_entities: tuple[str, ...] = ()
    allowed_evidence_references: tuple[str, ...] = ()
    eval_item_id: str | None = None


@dataclass(frozen=True)
class ContextCompilerOutput:
    """Normalized context compiler output used for scoring."""

    text: str
    citations: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    raw_output: JsonObject = field(default_factory=dict)


class ContextCompiler(Protocol):
    """Callable seam for context compiler implementations."""

    def __call__(
        self,
        request: ContextCompileRequest,
    ) -> ContextCompilerOutput | Mapping[str, Any] | str:
        """Compile context for one eval request."""


@dataclass(frozen=True)
class ContextEvalItem:
    """One human-authored context gold-set item."""

    item_id: str
    query: str
    required_facts: tuple[str, ...] = ()
    forbidden_stale_facts: tuple[str, ...] = ()
    required_gaps: tuple[str, ...] = ()
    relevant_entities: tuple[str, ...] = ()
    allowed_evidence_references: tuple[str, ...] = ()
    privacy_ceiling: int = DEFAULT_PRIVACY_CEILING
    notes: str | None = None
    schema_version: str = CONTEXT_EVAL_SCHEMA_VERSION

    @classmethod
    def from_json(
        cls,
        payload: Mapping[str, Any],
        *,
        line_number: int | None = None,
    ) -> ContextEvalItem:
        """Load and validate one JSON object from a gold-set JSONL file."""
        prefix = f"line {line_number}: " if line_number is not None else ""
        schema_version = _string_field(
            payload,
            "schema_version",
            default=CONTEXT_EVAL_SCHEMA_VERSION,
            prefix=prefix,
        )
        if schema_version != CONTEXT_EVAL_SCHEMA_VERSION:
            raise ContextEvalSchemaError(
                f'{prefix}unsupported schema_version "{schema_version}"'
            )
        item_id = _string_field(payload, "id", prefix=prefix)
        query = _string_field(payload, "query", default=None, prefix=prefix)
        if "prompt" in payload:
            prompt = _string_field(payload, "prompt", default=None, prefix=prefix)
            if query and prompt and query != prompt:
                raise ContextEvalSchemaError(
                    f'{prefix}"query" and "prompt" must match when both are present'
                )
            query = query or prompt
        if not query:
            raise ContextEvalSchemaError(f'{prefix}missing required string field "query"')
        privacy_ceiling = _int_field(
            payload,
            "privacy_ceiling",
            default=DEFAULT_PRIVACY_CEILING,
            prefix=prefix,
        )
        if privacy_ceiling < 0:
            raise ContextEvalSchemaError(f'{prefix}"privacy_ceiling" must be >= 0')
        notes = _optional_string_field(payload, "notes", prefix=prefix)
        return cls(
            item_id=item_id,
            query=query,
            required_facts=_string_tuple(payload, "required_facts", prefix=prefix),
            forbidden_stale_facts=_string_tuple(
                payload,
                "forbidden_stale_facts",
                prefix=prefix,
            ),
            required_gaps=_string_tuple(payload, "required_gaps", prefix=prefix),
            relevant_entities=_string_tuple(payload, "relevant_entities", prefix=prefix),
            allowed_evidence_references=_string_tuple(
                payload,
                "allowed_evidence_references",
                prefix=prefix,
            ),
            privacy_ceiling=privacy_ceiling,
            notes=notes,
            schema_version=schema_version,
        )

    def to_json(self) -> JsonObject:
        """Return the stable JSON shape for this item."""
        return {
            "schema_version": self.schema_version,
            "id": self.item_id,
            "query": self.query,
            "required_facts": list(self.required_facts),
            "forbidden_stale_facts": list(self.forbidden_stale_facts),
            "required_gaps": list(self.required_gaps),
            "relevant_entities": list(self.relevant_entities),
            "allowed_evidence_references": list(self.allowed_evidence_references),
            "privacy_ceiling": self.privacy_ceiling,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ContextEvalItemScore:
    """Scoring result for one context eval item."""

    item_id: str
    query: str
    required_fact_recall: float
    required_facts_found: tuple[str, ...]
    required_facts_missing: tuple[str, ...]
    forbidden_stale_fact_hits: tuple[str, ...]
    required_gap_recall: float
    required_gaps_found: tuple[str, ...]
    required_gaps_missing: tuple[str, ...]
    citation_coverage: float
    citation_hits: tuple[str, ...]
    citation_misses: tuple[str, ...]
    unsupported_fact_approximation: int
    unsupported_fact_candidates: tuple[str, ...]
    output_word_count: int
    waste_word_count: int
    waste_ratio: float
    compiler_output: ContextCompilerOutput

    def to_json(self) -> JsonObject:
        """Return the stable JSON report shape for one item score."""
        payload = asdict(self)
        payload["compiler_output"] = {
            "text": self.compiler_output.text,
            "citations": list(self.compiler_output.citations),
            "gaps": list(self.compiler_output.gaps),
            "raw_output": self.compiler_output.raw_output,
        }
        return payload


@dataclass(frozen=True)
class ContextEvalReport:
    """Machine-readable report for one context eval run."""

    schema_version: str
    runner_version: str
    item_count: int
    summary: JsonObject
    items: tuple[ContextEvalItemScore, ...]

    def to_json(self) -> JsonObject:
        """Return the JSON-serializable report shape."""
        return {
            "schema_version": self.schema_version,
            "runner_version": self.runner_version,
            "item_count": self.item_count,
            "summary": self.summary,
            "items": [item.to_json() for item in self.items],
        }

    def to_markdown(self) -> str:
        """Render a compact Markdown summary for review."""
        lines = [
            "# Context Eval Summary",
            "",
            f"- Runner: `{self.runner_version}`",
            f"- Items: {self.item_count}",
            f"- Required fact recall: {self.summary['required_fact_recall']:.3f}",
            f"- Forbidden stale fact hits: {self.summary['forbidden_stale_fact_hits']}",
            f"- Required gap recall: {self.summary['required_gap_recall']:.3f}",
            f"- Citation coverage: {self.summary['citation_coverage']:.3f}",
            f"- Unsupported fact approximation: {self.summary['unsupported_fact_approximation']}",
            f"- Waste ratio: {self.summary['waste_ratio']:.3f}",
            "",
            "## Items",
            "",
        ]
        for item in self.items:
            lines.extend(
                [
                    f"### {item.item_id}",
                    "",
                    f"- Query: {item.query}",
                    f"- Required fact recall: {item.required_fact_recall:.3f}",
                    f"- Required gaps: {item.required_gap_recall:.3f}",
                    f"- Citation coverage: {item.citation_coverage:.3f}",
                    f"- Stale hits: {len(item.forbidden_stale_fact_hits)}",
                    f"- Unsupported approx: {item.unsupported_fact_approximation}",
                    f"- Waste ratio: {item.waste_ratio:.3f}",
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"


def load_eval_items(path: Path) -> tuple[ContextEvalItem, ...]:
    """Load context eval items from a JSONL file."""
    items: list[ContextEvalItem] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ContextEvalSchemaError(
                    f"line {line_number}: invalid JSON: {exc.msg}"
                ) from exc
            if not isinstance(payload, Mapping):
                raise ContextEvalSchemaError(f"line {line_number}: item must be an object")
            items.append(ContextEvalItem.from_json(payload, line_number=line_number))
    return tuple(items)


def validate_eval_dataset(path: Path) -> tuple[ContextEvalItem, ...]:
    """Validate one context eval gold-set file and return parsed items."""
    return load_eval_items(path)


def context_eval_gold_set_path(dataset_path: Path) -> Path:
    """Return the JSONL gold-set file for a private context eval dataset path.

    The external dataset path may point directly at a JSONL file or at a
    dataset directory containing ``context_eval.gold.jsonl``.
    """
    path = Path(dataset_path)
    if path.suffix.lower() == ".jsonl" or path.is_file():
        return path
    return path / CONTEXT_EVAL_DATASET_GOLD_FILENAME


def resolve_context_eval_gold_set_path(
    *,
    dataset_path: Path | None = None,
    gold_set_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the context eval JSONL file from CLI or environment inputs."""
    if gold_set_path is not None:
        return Path(gold_set_path)
    if dataset_path is not None:
        return context_eval_gold_set_path(Path(dataset_path))
    active_environ = environ if environ is not None else os.environ
    env_value = active_environ.get(CONTEXT_EVAL_DATASET_ENV_VAR)
    if env_value is None or env_value.strip() == "":
        raise ContextEvalSchemaError(
            "context eval requires --dataset-path, --gold-set, or "
            f"{CONTEXT_EVAL_DATASET_ENV_VAR}"
        )
    return context_eval_gold_set_path(Path(env_value))


def run_context_eval(
    items: Sequence[ContextEvalItem],
    *,
    compiler: ContextCompiler | None = None,
    conn: object | None = None,
) -> ContextEvalReport:
    """Compile and score context for every eval item."""
    active_compiler = compiler or default_context_compiler(conn=conn)
    scores = tuple(_score_item(item, active_compiler) for item in items)
    return ContextEvalReport(
        schema_version="context_eval.report.v1",
        runner_version=CONTEXT_EVAL_RUNNER_VERSION,
        item_count=len(scores),
        summary=_summarize_scores(scores),
        items=scores,
    )


def run_context_eval_file(
    gold_set_path: Path,
    *,
    compiler: ContextCompiler | None = None,
    conn: object | None = None,
) -> ContextEvalReport:
    """Load a JSONL gold set and run the context eval."""
    return run_context_eval(load_eval_items(gold_set_path), compiler=compiler, conn=conn)


def write_json_report(report: ContextEvalReport, path: Path) -> None:
    """Write an eval report as pretty JSON."""
    Path(path).write_text(
        json.dumps(report.to_json(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_markdown_summary(report: ContextEvalReport, path: Path) -> None:
    """Write an eval report summary as Markdown."""
    Path(path).write_text(report.to_markdown(), encoding="utf-8")


def default_context_compiler(*, conn: object | None = None) -> ContextCompiler:
    """Return the installed context compiler when Worker D's service exists."""
    for module_name, function_name in (
        ("engram.context", "context_for"),
        ("engram.context", "compile_context"),
        ("engram.context_for", "context_for"),
    ):
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        service_compiler = _context_service_compiler(module, conn=conn)
        if service_compiler is not None:
            return service_compiler
        function = getattr(module, function_name, None)
        if callable(function) and not _requires_service_request(function):
            return _wrap_context_function(function)
    raise ContextCompilerUnavailableError(
        "no context compiler callable was supplied and no default context service is installed"
    )


def _requires_service_request(function: Callable[..., Any]) -> bool:
    """Return true for the service-layer context_for(conn, request) shape."""
    code = getattr(function, "__code__", None)
    if code is None:
        return False
    arg_names = code.co_varnames[: code.co_argcount]
    return len(arg_names) >= 2 and arg_names[0] == "conn" and arg_names[1] == "request"


def _wrap_context_function(function: Callable[..., Any]) -> ContextCompiler:
    def compile_request(
        request: ContextCompileRequest,
    ) -> ContextCompilerOutput | Mapping[str, Any] | str:
        return function(
            query_text=request.query_text,
            privacy_ceiling=request.privacy_ceiling,
            relevant_entities=list(request.relevant_entities),
            allowed_evidence_references=list(request.allowed_evidence_references),
        )

    return compile_request


def _context_service_compiler(
    module: ModuleType,
    *,
    conn: object | None,
) -> ContextCompiler | None:
    service_class = getattr(module, "PersonalContextService", None)
    request_class = getattr(module, "ContextForRequest", None)
    if service_class is None or request_class is None:
        return None
    if conn is None:
        return None
    service = service_class(conn)

    def compile_request(
        request: ContextCompileRequest,
    ) -> ContextCompilerOutput | Mapping[str, Any] | str:
        context_request = request_class(
            query_text=request.query_text,
            privacy_tier_ceiling=request.privacy_ceiling,
        )
        result = service.context_for(context_request)
        to_json = getattr(result, "to_json", None)
        if callable(to_json):
            converted = to_json()
            if isinstance(converted, Mapping):
                return converted
        return str(result)

    return compile_request


def _score_item(item: ContextEvalItem, compiler: ContextCompiler) -> ContextEvalItemScore:
    request = ContextCompileRequest(
        query_text=item.query,
        privacy_ceiling=item.privacy_ceiling,
        relevant_entities=item.relevant_entities,
        allowed_evidence_references=item.allowed_evidence_references,
        eval_item_id=item.item_id,
    )
    output = _normalize_compiler_output(compiler(request))
    score_text = "\n".join((output.text, "\n".join(output.gaps), "\n".join(output.citations)))

    found_facts, missing_facts = _partition_present(item.required_facts, score_text)
    stale_hits, _ = _partition_present(item.forbidden_stale_facts, score_text)
    found_gaps, missing_gaps = _partition_present(item.required_gaps, score_text)
    citation_hits, citation_misses = _partition_present(
        item.allowed_evidence_references,
        "\n".join(output.citations) or output.text,
    )
    unsupported_candidates = _unsupported_candidates(
        output.text,
        supported_phrases=(
            *item.required_facts,
            *item.forbidden_stale_facts,
            *item.required_gaps,
            *item.relevant_entities,
            *item.allowed_evidence_references,
        ),
    )
    output_word_count = _word_count(output.text)
    useful_word_count = _useful_word_count(
        output.text,
        phrases=(
            *found_facts,
            *found_gaps,
            *item.relevant_entities,
            *citation_hits,
        ),
    )
    waste_word_count = max(0, output_word_count - useful_word_count)
    return ContextEvalItemScore(
        item_id=item.item_id,
        query=item.query,
        required_fact_recall=_ratio(len(found_facts), len(item.required_facts)),
        required_facts_found=found_facts,
        required_facts_missing=missing_facts,
        forbidden_stale_fact_hits=stale_hits,
        required_gap_recall=_ratio(len(found_gaps), len(item.required_gaps)),
        required_gaps_found=found_gaps,
        required_gaps_missing=missing_gaps,
        citation_coverage=_ratio(len(citation_hits), len(item.allowed_evidence_references)),
        citation_hits=citation_hits,
        citation_misses=citation_misses,
        unsupported_fact_approximation=len(unsupported_candidates),
        unsupported_fact_candidates=unsupported_candidates,
        output_word_count=output_word_count,
        waste_word_count=waste_word_count,
        waste_ratio=_ratio(waste_word_count, output_word_count),
        compiler_output=output,
    )


def _normalize_compiler_output(
    output: ContextCompilerOutput | Mapping[str, Any] | str,
) -> ContextCompilerOutput:
    if isinstance(output, ContextCompilerOutput):
        return output
    if isinstance(output, str):
        return ContextCompilerOutput(text=output)
    to_json = getattr(output, "to_json", None)
    if callable(to_json):
        converted = to_json()
        if isinstance(converted, Mapping):
            return _normalize_compiler_output(converted)
    raw_output = dict(output)
    text_parts = _collect_text(raw_output)
    citations = tuple(_dedupe(_string_values(raw_output.get("citations"))))
    if not citations:
        citations = tuple(
            _dedupe(
                value
                for key in ("reference_id", "source_reference_ids", "source_belief_ids")
                for value in _string_values(raw_output.get(key))
            )
        )
    gaps = tuple(
        _dedupe(
            value
            for key in ("gaps", "required_gaps", "missing_data", "omissions")
            for value in _string_values(raw_output.get(key))
        )
    )
    return ContextCompilerOutput(
        text="\n".join(part for part in text_parts if part).strip(),
        citations=citations,
        gaps=gaps,
        raw_output=raw_output,
    )


def _collect_text(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        parts: list[str] = []
        for key, nested_value in value.items():
            if key in {"citations", "source_reference_ids", "source_belief_ids"}:
                continue
            parts.extend(_collect_text(nested_value))
        return parts
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        parts = []
        for item in value:
            parts.extend(_collect_text(item))
        return parts
    return []


def _string_values(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        values: list[str] = []
        for nested_value in value.values():
            values.extend(_string_values(nested_value))
        return tuple(values)
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        values = []
        for item in value:
            values.extend(_string_values(item))
        return tuple(values)
    return (str(value),)


def _unsupported_candidates(text: str, *, supported_phrases: Sequence[str]) -> tuple[str, ...]:
    candidates: list[str] = []
    for sentence in _SENTENCE_SPLIT_PATTERN.split(text):
        candidate = sentence.strip()
        if len(_words(candidate)) < 4:
            continue
        normalized = _normalize(candidate)
        if normalized.startswith(("standing context", "relevant beliefs", "missing data")):
            continue
        if any(_contains_phrase(candidate, phrase) for phrase in supported_phrases):
            continue
        candidates.append(candidate)
    return tuple(candidates)


def _summarize_scores(scores: Sequence[ContextEvalItemScore]) -> JsonObject:
    return {
        "required_fact_recall": _average(score.required_fact_recall for score in scores),
        "forbidden_stale_fact_hits": sum(
            len(score.forbidden_stale_fact_hits) for score in scores
        ),
        "required_gap_recall": _average(score.required_gap_recall for score in scores),
        "citation_coverage": _average(score.citation_coverage for score in scores),
        "unsupported_fact_approximation": sum(
            score.unsupported_fact_approximation for score in scores
        ),
        "output_word_count": sum(score.output_word_count for score in scores),
        "waste_word_count": sum(score.waste_word_count for score in scores),
        "waste_ratio": _ratio(
            sum(score.waste_word_count for score in scores),
            sum(score.output_word_count for score in scores),
        ),
    }


def _partition_present(
    phrases: Sequence[str],
    text: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    found = tuple(phrase for phrase in phrases if _contains_phrase(text, phrase))
    missing = tuple(phrase for phrase in phrases if phrase not in found)
    return found, missing


def _contains_phrase(text: str, phrase: str) -> bool:
    return _normalize(phrase) in _normalize(text)


def _normalize(text: str) -> str:
    return " ".join(_words(text)).lower()


def _words(text: str) -> list[str]:
    return _WORD_PATTERN.findall(text)


def _word_count(text: str) -> int:
    return len(_words(text))


def _useful_word_count(text: str, *, phrases: Sequence[str]) -> int:
    useful = 0
    normalized_text = _normalize(text)
    for phrase in phrases:
        normalized_phrase = _normalize(phrase)
        if normalized_phrase and normalized_phrase in normalized_text:
            useful += _word_count(phrase)
    return min(useful, _word_count(text))


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return numerator / denominator


def _average(values: Sequence[float] | Any) -> float:
    value_tuple = tuple(values)
    if not value_tuple:
        return 1.0
    return sum(value_tuple) / len(value_tuple)


def _dedupe(values: Sequence[str] | Any) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)


def _string_tuple(payload: Mapping[str, Any], key: str, *, prefix: str) -> tuple[str, ...]:
    value = payload.get(key, ())
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ContextEvalSchemaError(f'{prefix}"{key}" must be an array of strings')
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ContextEvalSchemaError(
                f'{prefix}"{key}[{index}]" must be a non-empty string'
            )
        result.append(item)
    return tuple(result)


def _string_field(
    payload: Mapping[str, Any],
    key: str,
    *,
    prefix: str,
    default: str | None = "",
) -> str:
    value = payload.get(key, default)
    if value is None:
        return ""
    if not isinstance(value, str) or not value.strip():
        raise ContextEvalSchemaError(f'{prefix}"{key}" must be a non-empty string')
    return value


def _optional_string_field(payload: Mapping[str, Any], key: str, *, prefix: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContextEvalSchemaError(f'{prefix}"{key}" must be a string when present')
    return value


def _int_field(payload: Mapping[str, Any], key: str, *, default: int, prefix: str) -> int:
    value = payload.get(key, default)
    if not isinstance(value, int):
        raise ContextEvalSchemaError(f'{prefix}"{key}" must be an integer')
    return value
