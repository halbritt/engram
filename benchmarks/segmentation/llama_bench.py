"""Scratch-only llama-bench runner for raw local model throughput."""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchmarks.segmentation.results import git_commit
from benchmarks.segmentation.strategies import (
    DEFAULT_STRATEGIES,
    LocalModelStrategy,
    expanded_model_path,
    model_file_size,
)


LLAMA_BENCH_SCHEMA_VERSION = "segmentation-llama-bench-result.v1"


@dataclass(frozen=True)
class LlamaBenchConfig:
    llama_bench_bin: str
    model_path: str
    output_dir: Path
    strategy_name: str | None = None
    prompt_tokens: int = 512
    generation_tokens: int = 128
    repetitions: int = 3
    gpu_layers: int = 99
    threads: int = 8
    batch_size: int = 2048
    ubatch_size: int = 512
    ctx_size: int = 49152
    flash_attn: str = "on"
    cache_type_k: str = "q8_0"
    cache_type_v: str = "q8_0"
    min_generation_tps: float | None = None
    extra_args: tuple[str, ...] = ()


def model_path_for_strategy(strategy_name: str) -> str:
    strategy = DEFAULT_STRATEGIES.get(strategy_name)
    if strategy is None:
        raise ValueError(f"unknown strategy: {strategy_name}")
    if not isinstance(strategy, LocalModelStrategy):
        raise ValueError(f"{strategy_name} is not a local-model strategy")
    return expanded_model_path(strategy.profile.model_path)


def build_llama_bench_command(config: LlamaBenchConfig) -> list[str]:
    command = [
        config.llama_bench_bin,
        "-m",
        expanded_model_path(config.model_path),
        "-p",
        str(config.prompt_tokens),
        "-n",
        str(config.generation_tokens),
        "-r",
        str(config.repetitions),
        "-ngl",
        str(config.gpu_layers),
        "-t",
        str(config.threads),
        "-b",
        str(config.batch_size),
        "-ub",
        str(config.ubatch_size),
        "-c",
        str(config.ctx_size),
        "-fa",
        "1" if config.flash_attn == "on" else "0",
        "-ctk",
        config.cache_type_k,
        "-ctv",
        config.cache_type_v,
        "-o",
        "json",
    ]
    command.extend(config.extra_args)
    return command


def run_llama_bench(config: LlamaBenchConfig) -> Path:
    run_dir = config.output_dir / make_llama_bench_run_id()
    run_dir.mkdir(parents=True, exist_ok=False)
    command = build_llama_bench_command(config)
    started = time.perf_counter()
    stdout = ""
    stderr = ""
    returncode = -1
    process_error: str | None = None
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        returncode = completed.returncode
    except OSError as exc:
        process_error = str(exc)
        stderr = process_error
    duration_seconds = time.perf_counter() - started
    parsed_json, parse_error = parse_json_output(stdout)
    if process_error is not None:
        parse_error = f"process_start_failed: {process_error}"
    generation_tps = extract_generation_tokens_per_second(parsed_json)
    failure_reasons = llama_bench_failure_reasons(
        returncode=returncode,
        parse_error=parse_error,
        generation_tps=generation_tps,
        min_generation_tps=config.min_generation_tps,
    )
    status = "ok" if not failure_reasons else "failed"
    payload = {
        "schema_version": LLAMA_BENCH_SCHEMA_VERSION,
        "run_id": run_dir.name,
        "created_at": utc_now(),
        "git_commit": git_commit(),
        "status": status,
        "strategy_name": config.strategy_name,
        "model": {
            "model_path": expanded_model_path(config.model_path),
            "size_bytes": model_file_size(expanded_model_path(config.model_path)),
        },
        "llama_bench": {
            "binary": config.llama_bench_bin,
            "command": command,
            "returncode": returncode,
            "duration_seconds": duration_seconds,
            "prompt_tokens": config.prompt_tokens,
            "generation_tokens": config.generation_tokens,
            "repetitions": config.repetitions,
            "gpu_layers": config.gpu_layers,
            "threads": config.threads,
            "batch_size": config.batch_size,
            "ubatch_size": config.ubatch_size,
            "ctx_size": config.ctx_size,
            "flash_attn": config.flash_attn,
            "cache_type_k": config.cache_type_k,
            "cache_type_v": config.cache_type_v,
            "min_generation_tps": config.min_generation_tps,
            "extra_args": list(config.extra_args),
        },
        "metrics": {
            "generation_tokens_per_second": generation_tps,
        },
        "smoke": {
            "passed": status == "ok",
            "failure_reasons": failure_reasons,
            "min_generation_tokens_per_second": config.min_generation_tps,
        },
        "parsed_json": parsed_json,
        "parse_error": parse_error,
        "raw_stdout": stdout,
        "raw_stderr": stderr,
    }
    output_path = run_dir / "llama_bench.json"
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if status != "ok":
        raise LlamaBenchError(output_path, returncode, parse_error, failure_reasons)
    return output_path


class LlamaBenchError(RuntimeError):
    def __init__(
        self,
        output_path: Path,
        returncode: int,
        parse_error: str | None,
        failure_reasons: list[str],
    ) -> None:
        reason = f"returncode={returncode}"
        if parse_error:
            reason = f"{reason}; parse_error={parse_error}"
        if failure_reasons:
            reason = f"{reason}; failure_reasons={','.join(failure_reasons)}"
        super().__init__(f"llama-bench failed ({reason}); artifact: {output_path}")
        self.output_path = output_path
        self.returncode = returncode
        self.parse_error = parse_error
        self.failure_reasons = failure_reasons


def llama_bench_failure_reasons(
    *,
    returncode: int,
    parse_error: str | None,
    generation_tps: float | None,
    min_generation_tps: float | None,
) -> list[str]:
    reasons: list[str] = []
    if returncode != 0:
        reasons.append("nonzero_returncode")
    if parse_error is not None:
        reasons.append("invalid_json_output")
    if generation_tps is None:
        reasons.append("missing_generation_tps")
    elif min_generation_tps is not None and generation_tps < min_generation_tps:
        reasons.append("below_min_generation_tps")
    return reasons


def parse_json_output(stdout: str) -> tuple[Any | None, str | None]:
    try:
        return json.loads(stdout), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def extract_generation_tokens_per_second(parsed_json: Any) -> float | None:
    rows = result_rows(parsed_json)
    candidates: list[float] = []
    for row in rows:
        n_gen = numeric_value(row, ("n_gen", "generation_tokens", "n_tokens_gen"))
        tps = numeric_value(
            row,
            (
                "avg_ts",
                "avg_tps",
                "tokens_per_second",
                "generation_tokens_per_second",
                "tg_tps",
            ),
        )
        if n_gen is not None and n_gen <= 0:
            continue
        if tps is not None:
            candidates.append(tps)
    if not candidates:
        return None
    return candidates[0]


def result_rows(parsed_json: Any) -> list[dict[str, Any]]:
    if isinstance(parsed_json, list):
        return [row for row in parsed_json if isinstance(row, dict)]
    if isinstance(parsed_json, dict):
        for key in ("results", "data", "benchmarks"):
            value = parsed_json.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
        return [parsed_json]
    return []


def numeric_value(row: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return None


def make_llama_bench_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}.llama-bench.{uuid.uuid4().hex[:8]}"


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
