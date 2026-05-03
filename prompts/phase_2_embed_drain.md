# Phase 2 Embed Drain

> Hand this to a coding agent on branch `phase-2-segments-embeddings`.
> Goal: drain the Phase 2 embedding backlog only. Do not run segmentation.
> Do not change code unless the embed-only pass exposes a clear bug and you
> confirm before editing.

## Context

- A post-CUDA `pipeline --limit 300` soak completed with 280 segmented parents,
  but the embed phase only processed 300 segments because the same `--limit`
  capped embedding work.
- There are `segment_generations.status='segmented'` rows waiting for
  embeddings and activation.
- The DB should reach a consistent activation state before the next
  segmentation experiment.
- OpenClaw shares GPU/runtime resources and should be stopped during this pass.

## Steps

1. Go to the repo and record baseline state.

   ```bash
   cd ~/git/engram
   git status --short --branch
   date -u
   nvidia-smi
   psql postgresql:///engram -X -c "
     SELECT status, count(*) FROM segment_generations GROUP BY status ORDER BY status;
     SELECT count(*) AS active_segments FROM segments WHERE is_active=true;
     SELECT count(*) AS active_embeddings FROM segment_embeddings WHERE is_active=true;
     SELECT count(*) AS pending_segment_generations
       FROM segment_generations WHERE status IN ('segmented','embedding');
   "
   ```

2. Stop OpenClaw for the duration of the embed pass, and restore it on exit.

   ```bash
   restore() {
     systemctl --user start openclaw-gateway.service 2>/dev/null || true
   }
   trap restore EXIT INT TERM
   systemctl --user stop openclaw-gateway.service 2>/dev/null || true
   ```

3. Run embed only. Do not run `pipeline` or `segment`.

   ```bash
   export ENGRAM_DATABASE_URL=postgresql:///engram

   mkdir -p logs
   ts=$(date -u +%Y%m%dT%H%M%SZ)

   .venv/bin/python -m engram.cli embed \
     --batch-size 1000 \
     2>&1 | tee "logs/phase2_embed_drain_${ts}.log"
   ```

   If one pass leaves more `segmented` / `embedding` generations, repeat the
   same `embed` command until it reports zero new embeddings/activations or the
   DB query below shows no pending generations.

4. Record post-run state.

   ```bash
   date -u
   nvidia-smi
   psql postgresql:///engram -X -c "
     SELECT status, count(*) FROM segment_generations GROUP BY status ORDER BY status;
     SELECT count(*) AS active_segments FROM segments WHERE is_active=true;
     SELECT count(*) AS active_embeddings FROM segment_embeddings WHERE is_active=true;
     SELECT count(*) AS pending_segment_generations
       FROM segment_generations WHERE status IN ('segmented','embedding');
     SELECT count(*) AS active_sequence_dupes
       FROM (
         SELECT conversation_id, sequence_index
         FROM segments
         WHERE is_active=true AND conversation_id IS NOT NULL
         GROUP BY 1,2 HAVING count(*) > 1
       ) q;
   "
   ```

5. Summarize:

   - log file path
   - number of embed passes run
   - active segment/embedding counts before and after
   - remaining pending generations, if any
   - active sequence duplicate count
   - any errors

## Acceptance

- No segmentation commands were run.
- OpenClaw was stopped during embedding and restored afterward.
- Pending `segmented` / `embedding` generations are drained as far as
  `engram embed` can drain them.
- Active sequence duplicates remain zero.
