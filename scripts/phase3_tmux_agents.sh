#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="${PHASE3_SESSION:-engram-phase3}"
RUN_MODE="${PHASE3_RUN_MODE:-print}"
MARKERS_DIR="docs/reviews/phase3/markers"
POSTBUILD_MARKERS_DIR="docs/reviews/phase3/postbuild/markers"

usage() {
  cat <<'EOF'
Usage:
  scripts/phase3_tmux_agents.sh start
  scripts/phase3_tmux_agents.sh run-job <job>
  scripts/phase3_tmux_agents.sh status
  scripts/phase3_tmux_agents.sh next

Environment:
  PHASE3_SESSION   tmux session name (default: engram-phase3)
  PHASE3_RUN_MODE  print | pipe (default: print)

  CODEX_CMD        stdin-taking command for Codex GPT-5.5
                   (default: codex -a never exec --model gpt-5.5
                    --sandbox danger-full-access -)
  CLAUDE_CMD       stdin-taking command for Claude Opus 4.7
                   (default: claude --model opus --dangerously-skip-permissions)
  GEMINI_CMD       stdin-taking command for Gemini Pro 3.1
                   (default: gemini --model gemini-3.1-pro-preview --yolo)

Modes:
  print  Wait for markers, then print the prompt/model/marker handoff.
  pipe   Wait for markers, then pipe the prompt into the configured *_CMD.

If your model CLIs are interactive rather than stdin-taking, use print mode and
paste the shown prompt path into the appropriate tmux pane.
EOF
}

marker_path() {
  printf "%s/%s\n" "$MARKERS_DIR" "$1"
}

marker_aliases() {
  case "$1" in
    02_SPEC_REVIEW_codex_gpt5_5.ready.md)
      printf "%s\n" "02_SPEC_REVIEW_codex_gpt_5_5.ready.md"
      ;;
    04_SPEC_SYNTHESIS_REVIEW_codex_gpt5_5.ready.md)
      printf "%s\n" "04_SPEC_SYNTHESIS_REVIEW_codex_gpt_5_5.ready.md"
      ;;
    06_BUILD_PROMPT_REVIEW_codex_gpt5_5.ready.md)
      printf "%s\n" "06_BUILD_PROMPT_REVIEW_codex_gpt_5_5.ready.md"
      ;;
    09_BUILD_REVIEW_codex_gpt5_5.ready.md)
      printf "%s\n" "09_BUILD_REVIEW_codex_gpt_5_5.ready.md"
      ;;
  esac
}

marker_exists() {
  local marker="$1"
  local alias
  [[ -f "$ROOT/$(marker_path "$marker")" ]] && return 0
  while IFS= read -r alias; do
    [[ -z "$alias" ]] && continue
    [[ -f "$ROOT/$(marker_path "$alias")" ]] && return 0
  done < <(marker_aliases "$marker")
  return 1
}

marker_front_matter_value() {
  local path="$1"
  local key="$2"
  awk -v key="$key" '
    NR == 1 && $0 == "---" { in_front_matter = 1; next }
    in_front_matter && $0 == "---" { exit }
    in_front_matter && index($0, key ":") == 1 {
      sub("^[^:]+:[[:space:]]*", "")
      gsub(/^["'\''[:space:]]+|["'\''[:space:]]+$/, "")
      print
      exit
    }
  ' "$path"
}

postbuild_markers_root() {
  case "$POSTBUILD_MARKERS_DIR" in
    /*) printf "%s\n" "$POSTBUILD_MARKERS_DIR" ;;
    *) printf "%s/%s\n" "$ROOT" "$POSTBUILD_MARKERS_DIR" ;;
  esac
}

marker_epoch() {
  local path="$1"
  local created_at
  created_at="$(marker_front_matter_value "$path" "created_at")"
  if [[ -n "$created_at" ]]; then
    date -u -d "$created_at" +%s 2>/dev/null && return 0
  fi
  stat -c '%Y' "$path"
}

marker_blocks_expansion() {
  local path="$1"
  local state
  local gate
  state="$(marker_front_matter_value "$path" "state")"
  gate="$(marker_front_matter_value "$path" "gate")"
  case "$state" in
    blocked|human_checkpoint) return 0 ;;
  esac
  case "$gate" in
    blocked|human_checkpoint) return 0 ;;
  esac
  case "$path" in
    *.blocked.md|*.human_checkpoint.md) return 0 ;;
  esac
  return 1
}

marker_is_ready_superseder() {
  local path
  path="$1"
  [[ "$(marker_front_matter_value "$path" "state")" == "ready" ]] || return 1
  marker_blocks_expansion "$path" && return 1
  [[ -n "$(marker_front_matter_value "$path" "supersedes")" ]]
}

is_operational_marker_superseded() {
  local marker_rel="$1"
  local marker_path="$2"
  local marker_issue
  local marker_family
  local marker_created_at
  local marker_created
  local root
  local path
  local supersedes
  local superseder_issue
  local superseder_family
  local superseder_created
  marker_issue="$(marker_front_matter_value "$marker_path" "issue_id")"
  marker_family="$(marker_front_matter_value "$marker_path" "family")"
  marker_created_at="$(marker_front_matter_value "$marker_path" "created_at")"
  marker_created="$(marker_epoch "$marker_path")"
  root="$(postbuild_markers_root)"
  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    marker_is_ready_superseder "$path" || continue
    supersedes="$(marker_front_matter_value "$path" "supersedes")"
    [[ "$supersedes" == "$marker_rel" ]] || continue
    superseder_created="$(marker_epoch "$path")"
    if [[ -n "$marker_created_at" ]]; then
      (( superseder_created >= marker_created )) || continue
    fi
    if [[ -n "$marker_issue" || -n "$marker_family" ]]; then
      superseder_issue="$(marker_front_matter_value "$path" "issue_id")"
      superseder_family="$(marker_front_matter_value "$path" "family")"
      [[ "$superseder_issue" == "$marker_issue" ]] || continue
      [[ "$superseder_family" == "$marker_family" ]] || continue
    fi
    return 0
  done < <(
    find "$root" -type f -name '*.ready.md' -print 2>/dev/null
  )
  return 1
}

blocked_operational_markers() {
  local path
  local rel
  local root
  root="$(postbuild_markers_root)"
  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    marker_blocks_expansion "$path" || continue
    rel="${path#"$root/"}"
    if is_operational_marker_superseded "$POSTBUILD_MARKERS_DIR/$rel" "$path"; then
      continue
    fi
    printf "%s %s\n" "$(marker_epoch "$path")" "$rel"
  done < <(
    find "$root" -type f -name '*.md' -print 2>/dev/null
  ) | sort -nr
}

has_blocked_operational_markers() {
  [[ -n "$(blocked_operational_markers)" ]]
}

print_blocked_operational_markers() {
  local line
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    printf "[blocked] %s/%s\n" "$POSTBUILD_MARKERS_DIR" "${line#* }"
  done < <(blocked_operational_markers)
}

all_markers() {
  cat <<'EOF'
01_SPEC_DRAFT.ready.md
02_SPEC_REVIEW_gemini_pro_3_1.ready.md
02_SPEC_REVIEW_codex_gpt5_5.ready.md
02_SPEC_REVIEW_claude_opus_4_7.ready.md
03_SPEC_FINDINGS_LEDGER.ready.md
04_SPEC_SYNTHESIS.ready.md
04_SPEC_SYNTHESIS_REVIEW_codex_gpt5_5.ready.md
05_BUILD_PROMPT_DRAFT.ready.md
06_BUILD_PROMPT_REVIEW_gemini_pro_3_1.ready.md
06_BUILD_PROMPT_REVIEW_codex_gpt5_5.ready.md
06_BUILD_PROMPT_REVIEW_claude_opus_4_7.ready.md
07_BUILD_PROMPT_SYNTHESIS.ready.md
08_BUILD_COMPLETE.ready.md
09_BUILD_REVIEW_gemini_pro_3_1.ready.md
09_BUILD_REVIEW_codex_gpt5_5.ready.md
09_BUILD_REVIEW_claude_opus_4_7.ready.md
10_BUILD_REVIEW_SYNTHESIS.ready.md
11_PIPELINE_STARTED.ready.md
EOF
}

wait_for_markers() {
  local marker
  for marker in "$@"; do
    local path
    path="$(marker_path "$marker")"
    until marker_exists "$marker"; do
      printf "[%s] waiting for %s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$path"
      sleep 20
    done
  done
}

command_for_model() {
  case "$1" in
    codex_gpt5_5)
      local cmd="${CODEX_CMD:-}"
      if [[ -z "$cmd" || "$cmd" == "codex --model gpt-5.5 --yolo" ]]; then
        cmd="codex -a never exec --model gpt-5.5 --sandbox danger-full-access -"
      fi
      printf "%s" "$cmd"
      ;;
    claude_opus_4_7) printf "%s" "${CLAUDE_CMD:-claude --model opus --dangerously-skip-permissions}" ;;
    gemini_pro_3_1) printf "%s" "${GEMINI_CMD:-gemini --model gemini-3.1-pro-preview --yolo}" ;;
    *) return 1 ;;
  esac
}

job_config() {
  case "$1" in
    spec_draft)
      MODEL=claude_opus_4_7
      PROMPT=prompts/P021_generate_phase_3_claims_beliefs_spec.md
      WAITS=()
      EXPECTS=01_SPEC_DRAFT.ready.md
      ;;
    spec_review_gemini)
      MODEL=gemini_pro_3_1
      PROMPT=prompts/P022_review_phase_3_claims_beliefs_spec.md
      WAITS=(01_SPEC_DRAFT.ready.md)
      EXPECTS=02_SPEC_REVIEW_gemini_pro_3_1.ready.md
      ;;
    spec_review_codex)
      MODEL=codex_gpt5_5
      PROMPT=prompts/P022_review_phase_3_claims_beliefs_spec.md
      WAITS=(01_SPEC_DRAFT.ready.md)
      EXPECTS=02_SPEC_REVIEW_codex_gpt5_5.ready.md
      ;;
    spec_review_claude)
      MODEL=claude_opus_4_7
      PROMPT=prompts/P022_review_phase_3_claims_beliefs_spec.md
      WAITS=(01_SPEC_DRAFT.ready.md)
      EXPECTS=02_SPEC_REVIEW_claude_opus_4_7.ready.md
      ;;
    spec_ledger)
      MODEL=codex_gpt5_5
      PROMPT=prompts/P023_record_phase_3_spec_findings.md
      WAITS=(
        02_SPEC_REVIEW_gemini_pro_3_1.ready.md
        02_SPEC_REVIEW_codex_gpt5_5.ready.md
        02_SPEC_REVIEW_claude_opus_4_7.ready.md
      )
      EXPECTS=03_SPEC_FINDINGS_LEDGER.ready.md
      ;;
    spec_synthesis)
      MODEL=claude_opus_4_7
      PROMPT=prompts/P024_synthesize_phase_3_spec_findings.md
      WAITS=(03_SPEC_FINDINGS_LEDGER.ready.md)
      EXPECTS=04_SPEC_SYNTHESIS.ready.md
      ;;
    spec_synthesis_review_codex)
      MODEL=codex_gpt5_5
      PROMPT=prompts/P024_review_phase_3_spec_synthesis_codex.md
      WAITS=(04_SPEC_SYNTHESIS.ready.md)
      EXPECTS=04_SPEC_SYNTHESIS_REVIEW_codex_gpt5_5.ready.md
      ;;
    build_prompt_draft)
      MODEL=codex_gpt5_5
      PROMPT=prompts/P025_write_phase_3_build_prompt.md
      WAITS=(04_SPEC_SYNTHESIS_REVIEW_codex_gpt5_5.ready.md)
      EXPECTS=05_BUILD_PROMPT_DRAFT.ready.md
      ;;
    build_prompt_review_gemini)
      MODEL=gemini_pro_3_1
      PROMPT=prompts/P026_review_phase_3_build_prompt.md
      WAITS=(05_BUILD_PROMPT_DRAFT.ready.md)
      EXPECTS=06_BUILD_PROMPT_REVIEW_gemini_pro_3_1.ready.md
      ;;
    build_prompt_review_codex)
      MODEL=codex_gpt5_5
      PROMPT=prompts/P026_review_phase_3_build_prompt.md
      WAITS=(05_BUILD_PROMPT_DRAFT.ready.md)
      EXPECTS=06_BUILD_PROMPT_REVIEW_codex_gpt5_5.ready.md
      ;;
    build_prompt_review_claude)
      MODEL=claude_opus_4_7
      PROMPT=prompts/P026_review_phase_3_build_prompt.md
      WAITS=(05_BUILD_PROMPT_DRAFT.ready.md)
      EXPECTS=06_BUILD_PROMPT_REVIEW_claude_opus_4_7.ready.md
      ;;
    build_prompt_synthesis)
      MODEL=codex_gpt5_5
      PROMPT=prompts/P027_synthesize_phase_3_build_prompt_findings.md
      WAITS=(
        06_BUILD_PROMPT_REVIEW_gemini_pro_3_1.ready.md
        06_BUILD_PROMPT_REVIEW_codex_gpt5_5.ready.md
        06_BUILD_PROMPT_REVIEW_claude_opus_4_7.ready.md
      )
      EXPECTS=07_BUILD_PROMPT_SYNTHESIS.ready.md
      ;;
    build)
      MODEL=codex_gpt5_5
      PROMPT=prompts/P028_build_phase_3_claims_beliefs.md
      WAITS=(07_BUILD_PROMPT_SYNTHESIS.ready.md)
      EXPECTS=08_BUILD_COMPLETE.ready.md
      ;;
    build_review_gemini)
      MODEL=gemini_pro_3_1
      PROMPT=prompts/P029_review_phase_3_build.md
      WAITS=(08_BUILD_COMPLETE.ready.md)
      EXPECTS=09_BUILD_REVIEW_gemini_pro_3_1.ready.md
      ;;
    build_review_codex)
      MODEL=codex_gpt5_5
      PROMPT=prompts/P029_review_phase_3_build.md
      WAITS=(08_BUILD_COMPLETE.ready.md)
      EXPECTS=09_BUILD_REVIEW_codex_gpt5_5.ready.md
      ;;
    build_review_claude)
      MODEL=claude_opus_4_7
      PROMPT=prompts/P029_review_phase_3_build.md
      WAITS=(08_BUILD_COMPLETE.ready.md)
      EXPECTS=09_BUILD_REVIEW_claude_opus_4_7.ready.md
      ;;
    build_review_synthesis)
      MODEL=codex_gpt5_5
      PROMPT=prompts/P030_synthesize_phase_3_build_review_findings.md
      WAITS=(
        09_BUILD_REVIEW_gemini_pro_3_1.ready.md
        09_BUILD_REVIEW_codex_gpt5_5.ready.md
        09_BUILD_REVIEW_claude_opus_4_7.ready.md
      )
      EXPECTS=10_BUILD_REVIEW_SYNTHESIS.ready.md
      ;;
    pipeline_start)
      MODEL=codex_gpt5_5
      PROMPT=prompts/P031_begin_phase_3_pipeline.md
      WAITS=(10_BUILD_REVIEW_SYNTHESIS.ready.md)
      EXPECTS=11_PIPELINE_STARTED.ready.md
      ;;
    *)
      printf "Unknown job: %s\n" "$1" >&2
      return 1
      ;;
  esac
}

agent_bundle() {
  local model="$1"
  local prompt="$2"
  local expects="$3"
  cat "$ROOT/$prompt"
  cat <<EOF

---

Coordinator injection:
- Your model slug is: $model
- Expected completion marker: $MARKERS_DIR/$expects
- Worktree: current repository root
- Before writing, run git status --short and avoid overwriting unrelated changes.
EOF
}

run_job() {
  local job="$1"
  MODEL=""
  PROMPT=""
  EXPECTS=""
  WAITS=()
  job_config "$job"

  cd "$ROOT"
  mkdir -p "$MARKERS_DIR"
  if [[ "${#WAITS[@]}" -gt 0 ]]; then
    wait_for_markers "${WAITS[@]}"
  fi

  printf "\n=== Phase 3 job ready ===\n"
  printf "Job:    %s\n" "$job"
  printf "Model:  %s\n" "$MODEL"
  printf "Prompt: %s\n" "$PROMPT"
  printf "Marker: %s/%s\n\n" "$MARKERS_DIR" "$EXPECTS"

  if [[ "$RUN_MODE" == "pipe" ]]; then
    local cmd
    cmd="$(command_for_model "$MODEL")"
    if [[ -z "$cmd" ]]; then
      printf "No command configured for %s. Set CODEX_CMD, CLAUDE_CMD, or GEMINI_CMD.\n" "$MODEL" >&2
      return 2
    fi
    agent_bundle "$MODEL" "$PROMPT" "$EXPECTS" | bash -lc "$cmd"
  else
    printf "Print mode. Run this prompt with %s:\n\n" "$MODEL"
    printf "  %s\n\n" "$PROMPT"
    printf "Or inspect the full prompt with:\n\n"
    printf "  sed -n '1,260p' %s\n\n" "$PROMPT"
  fi
}

jobs() {
  cat <<'EOF'
spec_draft
spec_review_gemini
spec_review_codex
spec_review_claude
spec_ledger
spec_synthesis
spec_synthesis_review_codex
build_prompt_draft
build_prompt_review_gemini
build_prompt_review_codex
build_prompt_review_claude
build_prompt_synthesis
build
build_review_gemini
build_review_codex
build_review_claude
build_review_synthesis
pipeline_start
EOF
}

start_session() {
  cd "$ROOT"
  mkdir -p "$MARKERS_DIR"
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    printf "tmux session already exists: %s\n" "$SESSION" >&2
    printf "Attach with: tmux attach -t %s\n" "$SESSION" >&2
    return 1
  fi

  tmux new-session -d -s "$SESSION" -c "$ROOT" -n coordinator \
    "printf 'Phase 3 coordinator session: %s\n\n' '$SESSION'; scripts/phase3_tmux_agents.sh status; exec ${SHELL:-/bin/bash} -l"

  local job
  while IFS= read -r job; do
    tmux new-window -t "$SESSION" -c "$ROOT" -n "$job" \
      "scripts/phase3_tmux_agents.sh run-job '$job'; exec ${SHELL:-/bin/bash} -l"
  done < <(jobs)

  printf "Started tmux session: %s\n" "$SESSION"
  printf "Attach with: tmux attach -t %s\n" "$SESSION"
}

status_markers() {
  cd "$ROOT"
  mkdir -p "$MARKERS_DIR"
  if has_blocked_operational_markers; then
    printf "Post-build operational blockers:\n"
    print_blocked_operational_markers
    printf "\n"
  fi
  local marker
  while IFS= read -r marker; do
    if marker_exists "$marker"; then
      printf "[x] %s\n" "$marker"
    else
      printf "[ ] %s\n" "$marker"
    fi
  done < <(all_markers)
}

next_marker() {
  cd "$ROOT"
  if has_blocked_operational_markers; then
    printf "blocked by post-build operational marker:\n"
    print_blocked_operational_markers
    return 1
  fi
  local marker
  while IFS= read -r marker; do
    if ! marker_exists "$marker"; then
      printf "%s\n" "$marker"
      return 0
    fi
  done < <(all_markers)
  printf "complete\n"
}

main() {
  case "${1:-}" in
    start) start_session ;;
    run-job)
      [[ $# -eq 2 ]] || { usage >&2; exit 2; }
      run_job "$2"
      ;;
    status) status_markers ;;
    next) next_marker ;;
    ""|-h|--help|help) usage ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
