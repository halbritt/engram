#!/usr/bin/env bash
# Driver for a single lane/role of the source-ingestion RFC workflow.
# Usage:
#   drive_lane.sh <lane_id> <role_id> <model_cmd...>
# Where model_cmd is the CLI invocation to run with the prompt argument,
# e.g. "codex exec" or "claude --model opus -p" or "gemini --yolo".
#
# Reads run id from $RUN_ID env. Registers a session, claims its job, runs the
# model on the constructed prompt, publishes the artifact, completes the job.
set -euo pipefail

RUN_ID="${RUN_ID:?RUN_ID is required}"
LANE_ID="$1"; shift
ROLE_ID="$1"; shift
MODEL_CMD=("$@")

REPO=/home/halbritt/git/engram
WORKFLOW_DIR=striatum/source-ingestion-rfc-research-2026-05-15
LOG=/tmp/lane-${LANE_ID}-${ROLE_ID}.log

export STRIATUM_TEST_HARNESS=1
export STRIATUM_DAEMON_REQUIRED=0

log() { printf '[%(%H:%M:%S)T] %s\n' -1 "$*" >> "$LOG" 2>/dev/null || true; }

log "register session lane=$LANE_ID role=$ROLE_ID"
SESS=$(striatum --repo "$REPO" register-session --run-id "$RUN_ID" --role "$ROLE_ID" --lane "$LANE_ID" --fresh --json | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['session_id'])")
log "session=$SESS"

log "claim-next"
striatum --repo "$REPO" claim-next --session-id "$SESS" --lease-seconds 1800 --json > "/tmp/packet-${LANE_ID}-${ROLE_ID}.json"
PACKET="/tmp/packet-${LANE_ID}-${ROLE_ID}.json"

JOB_ID=$(python3 -c "import json;d=json.load(open('$PACKET'));print(d['data']['packet']['job']['job_id'])")
LEASE_ID=$(python3 -c "import json;d=json.load(open('$PACKET'));print(d['data']['packet']['lease']['lease_id'])")
MSG_ID=$(python3 -c "import json;d=json.load(open('$PACKET'));print(d['data']['packet']['lease']['message_id'])")
ART_PATH=$(python3 -c "import json;d=json.load(open('$PACKET'));print(d['data']['packet']['expected_artifacts'][0]['path'])")
ART_NAME=$(python3 -c "import json;d=json.load(open('$PACKET'));print(d['data']['packet']['expected_artifacts'][0]['logical_name'])")
ART_KIND=$(python3 -c "import json;d=json.load(open('$PACKET'));print(d['data']['packet']['expected_artifacts'][0]['kind'])")
log "job=$JOB_ID lease=$LEASE_ID art=$ART_PATH"

log "ack"
striatum --repo "$REPO" ack --session-id "$SESS" --message-id "$MSG_ID" --lease-id "$LEASE_ID" --json >/dev/null

PROMPT_PATH=$(python3 -c "import json;d=json.load(open('$PACKET'));print(d['data']['packet']['task_prompt'].get('path',''))" 2>/dev/null || true)
ROLE_PATH=$(python3 -c "import json;d=json.load(open('$PACKET'));print(d['data']['packet']['role'].get('definition_path',''))" 2>/dev/null || true)

# Build a single self-contained prompt for the CLI agent.
PROMPT=$(cat <<EOF
You are the $ROLE_ID for lane $LANE_ID in the source-ingestion RFC research workflow.

CWD: $REPO

REQUIRED READING (use your file-read tools):
- Role: $ROLE_PATH
- Task prompt: $PROMPT_PATH
- Source design: docs/design/source-ingestion-expansion-proposal-2026-05-15.md
- Project canon: AGENTS.md, README.md, HUMAN_REQUIREMENTS.md, SPEC.md, BUILD_PHASES.md, ROADMAP.md, docs/schema/README.md, STRIATUM_MEMORY_E2E_BACKLOG.md, docs/AGENT_CONTEXT_NOTES.md

DELIVERABLE:
Write a single Markdown file at exactly this path:
  $ART_PATH
The file must be your role's artifact, fully self-contained, following the task prompt instructions.

CONSTRAINTS:
- Allowed write paths: $ART_PATH (and only that path).
- Forbidden write paths: .striatum/, src/, tests/, migrations/, docs/rfcs/, DECISION_LOG.md, CHANGELOG.md, BUILD_PHASES.md, ROADMAP.md.
- No network access. No telemetry. No outbound calls.
- Local-only operation; preserve Engram's no-cloud constraint.
- Do not start the document with a markdown-byline-style "Author:" or "author:" line; striatum validates that field. Use "Lane: $LANE_ID" and "Role: $ROLE_ID" lines instead, and put any author/byline info inside a table or section body. Do not impersonate another lane in any byline.
- This is a PROPOSAL document only. Do not promote, do not edit DECISION_LOG, do not edit the RFC index.

ACTIONS:
1. Read the role definition and task prompt above.
2. Read the required inputs.
3. Write the deliverable to the artifact path.
4. Verify the file exists and is non-empty before exiting.
EOF
)

log "running model: ${MODEL_CMD[*]}"
"${MODEL_CMD[@]}" "$PROMPT" >> "$LOG" 2>&1 || { log "model exited non-zero"; }

if [[ ! -s "$REPO/$ART_PATH" ]]; then
  log "ERROR: artifact missing at $ART_PATH"
  exit 2
fi
log "artifact present: $(wc -l < "$REPO/$ART_PATH") lines"

log "publish artifact"
striatum --repo "$REPO" publish-artifact --session-id "$SESS" --job-id "$JOB_ID" --lease-id "$LEASE_ID" --logical-name "$ART_NAME" --path "$ART_PATH" --kind "$ART_KIND" --allow-no-process-execution --override-rationale "operator-driven-subprocess-no-striatum-supervise" --json >> "$LOG" 2>&1

log "complete"
striatum --repo "$REPO" complete --session-id "$SESS" --job-id "$JOB_ID" --lease-id "$LEASE_ID" --json >> "$LOG" 2>&1

log "done"
