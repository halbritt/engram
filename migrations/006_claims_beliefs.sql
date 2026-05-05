-- Phase 3: claim extraction and deterministic bitemporal beliefs.
-- Forward-only migration. See docs/claims_beliefs.md.

CREATE OR REPLACE FUNCTION engram_normalize_subject(value TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    normalized TEXT;
BEGIN
    normalized := normalize(COALESCE(value, ''), NFKC);
    normalized := lower(normalized);
    normalized := btrim(normalized);
    normalized := regexp_replace(normalized, '\s+', ' ', 'g');
    normalized := regexp_replace(normalized, '[\.,;:!\?]+$', '', 'g');
    RETURN normalized;
END;
$$;

CREATE OR REPLACE FUNCTION engram_normalize_group_object_value(value TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    normalized TEXT;
BEGIN
    normalized := normalize(COALESCE(value, ''), NFKC);
    normalized := lower(normalized);
    normalized := btrim(normalized);
    normalized := regexp_replace(normalized, '\s+', ' ', 'g');
    RETURN normalized;
END;
$$;

CREATE TABLE predicate_vocabulary (
    predicate TEXT PRIMARY KEY,
    stability_class TEXT NOT NULL CHECK (
        stability_class IN (
            'identity',
            'preference',
            'project_status',
            'goal',
            'task',
            'mood',
            'relationship'
        )
    ),
    cardinality_class TEXT NOT NULL CHECK (
        cardinality_class IN (
            'single_current',
            'single_current_per_object',
            'multi_current',
            'event'
        )
    ),
    object_kind TEXT NOT NULL CHECK (object_kind IN ('text', 'json')),
    group_object_keys TEXT[] NOT NULL DEFAULT '{}'::text[],
    required_object_keys TEXT[] NOT NULL DEFAULT '{}'::text[],
    description TEXT NOT NULL
);

INSERT INTO predicate_vocabulary (
    predicate,
    stability_class,
    cardinality_class,
    object_kind,
    group_object_keys,
    required_object_keys,
    description
)
VALUES
    ('has_name', 'identity', 'single_current', 'text', '{}', '{}', 'legal or preferred name'),
    ('has_pronouns', 'identity', 'single_current', 'text', '{}', '{}', 'pronouns'),
    ('born_on', 'identity', 'single_current', 'text', '{}', '{}', 'birth date string'),
    ('lives_at', 'identity', 'single_current', 'json', '{}', '{address_line1}', 'current address as structured JSON'),
    ('holds_role_at', 'identity', 'single_current', 'json', '{}', '{role,employer}', 'current role and employer'),
    ('has_pet', 'identity', 'multi_current', 'json', '{name,species}', '{species}', 'pet with optional name and species'),
    ('is_related_to', 'relationship', 'multi_current', 'json', '{name}', '{name,kind}', 'family relation'),
    ('is_friends_with', 'relationship', 'multi_current', 'text', '{text}', '{}', 'friend name or alias'),
    ('works_with', 'relationship', 'multi_current', 'text', '{text}', '{}', 'coworker or collaborator name'),
    ('prefers', 'preference', 'multi_current', 'text', '{text}', '{}', 'preference'),
    ('dislikes', 'preference', 'multi_current', 'text', '{text}', '{}', 'dispreference'),
    ('believes', 'preference', 'multi_current', 'text', '{text}', '{}', 'open opinion'),
    ('uses_tool', 'preference', 'multi_current', 'text', '{text}', '{}', 'software or hardware tool'),
    ('drives', 'preference', 'single_current', 'text', '{}', '{}', 'current vehicle'),
    ('eats_diet', 'preference', 'single_current', 'text', '{}', '{}', 'current diet'),
    ('working_on', 'project_status', 'multi_current', 'text', '{text}', '{}', 'active project'),
    ('project_status_is', 'project_status', 'single_current_per_object', 'json', '{project}', '{project,status}', 'status for one project'),
    ('owns_repo', 'project_status', 'multi_current', 'text', '{text}', '{}', 'repository path or URL'),
    ('wants_to', 'goal', 'multi_current', 'text', '{text}', '{}', 'aspirational goal'),
    ('plans_to', 'goal', 'multi_current', 'json', '{action}', '{action}', 'planned action'),
    ('intends_to', 'goal', 'multi_current', 'text', '{text}', '{}', 'stated intention'),
    ('must_do', 'task', 'event', 'text', '{text}', '{}', 'action item'),
    ('committed_to', 'task', 'event', 'json', '{action,with_party}', '{action}', 'commitment event'),
    ('feels', 'mood', 'multi_current', 'text', '{text}', '{}', 'emotion or disposition'),
    ('relationship_with', 'relationship', 'single_current_per_object', 'json', '{name}', '{name,status}', 'relationship status for one person'),
    ('met_with', 'relationship', 'event', 'json', '{name,when}', '{name}', 'meeting event'),
    ('talked_about', 'preference', 'event', 'text', '{text}', '{}', 'topic discussed as an event'),
    ('studied', 'identity', 'multi_current', 'text', '{text}', '{}', 'school, program, or subject'),
    ('traveled_to', 'identity', 'event', 'json', '{place,when}', '{place}', 'travel event');

CREATE TABLE claim_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    segment_id UUID NOT NULL REFERENCES segments(id),
    generation_id UUID NOT NULL REFERENCES segment_generations(id),
    extraction_prompt_version TEXT NOT NULL,
    extraction_model_version TEXT NOT NULL,
    request_profile_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('extracting', 'extracted', 'failed', 'superseded')
    ),
    claim_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX claim_extractions_active_unique_idx
    ON claim_extractions (
        segment_id,
        extraction_prompt_version,
        extraction_model_version
    )
    WHERE status IN ('extracting', 'extracted');

CREATE INDEX claim_extractions_segment_status_idx
    ON claim_extractions (segment_id, status, created_at DESC);

CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    segment_id UUID NOT NULL REFERENCES segments(id),
    generation_id UUID NOT NULL REFERENCES segment_generations(id),
    conversation_id UUID NULL REFERENCES conversations(id),
    extraction_id UUID NOT NULL REFERENCES claim_extractions(id),
    subject_text TEXT NOT NULL CHECK (btrim(subject_text) <> ''),
    subject_normalized TEXT NOT NULL,
    predicate TEXT NOT NULL REFERENCES predicate_vocabulary(predicate),
    object_text TEXT NULL CHECK (object_text IS NULL OR btrim(object_text) <> ''),
    object_json JSONB NULL,
    stability_class TEXT NOT NULL CHECK (
        stability_class IN (
            'identity',
            'preference',
            'project_status',
            'goal',
            'task',
            'mood',
            'relationship'
        )
    ),
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    evidence_message_ids UUID[] NOT NULL CHECK (cardinality(evidence_message_ids) > 0),
    extraction_prompt_version TEXT NOT NULL,
    extraction_model_version TEXT NOT NULL,
    request_profile_version TEXT NOT NULL,
    privacy_tier INT NOT NULL,
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload JSONB NOT NULL,
    CHECK (
        (object_text IS NOT NULL AND object_json IS NULL)
        OR (object_text IS NULL AND object_json IS NOT NULL)
    )
);

CREATE INDEX claims_segment_id_idx ON claims (segment_id);
CREATE INDEX claims_conversation_id_idx ON claims (conversation_id);
CREATE INDEX claims_version_idx ON claims (
    extraction_prompt_version,
    extraction_model_version
);
CREATE INDEX claims_predicate_idx ON claims (predicate);
CREATE INDEX claims_stability_class_idx ON claims (stability_class);
CREATE INDEX claims_subject_predicate_idx ON claims (subject_normalized, predicate);
CREATE INDEX claims_evidence_message_ids_gin_idx ON claims USING gin (evidence_message_ids);

CREATE TABLE beliefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_text TEXT NOT NULL CHECK (btrim(subject_text) <> ''),
    subject_normalized TEXT NOT NULL,
    predicate TEXT NOT NULL REFERENCES predicate_vocabulary(predicate),
    cardinality_class TEXT NOT NULL CHECK (
        cardinality_class IN (
            'single_current',
            'single_current_per_object',
            'multi_current',
            'event'
        )
    ),
    object_text TEXT NULL CHECK (object_text IS NULL OR btrim(object_text) <> ''),
    object_json JSONB NULL,
    group_object_key TEXT NOT NULL DEFAULT '',
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ NULL,
    closed_at TIMESTAMPTZ NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    extracted_at TIMESTAMPTZ NOT NULL,
    superseded_by UUID NULL REFERENCES beliefs(id),
    status TEXT NOT NULL CHECK (
        status IN ('candidate', 'provisional', 'accepted', 'superseded', 'rejected')
    ),
    stability_class TEXT NOT NULL CHECK (
        stability_class IN (
            'identity',
            'preference',
            'project_status',
            'goal',
            'task',
            'mood',
            'relationship'
        )
    ),
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    evidence_ids UUID[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    claim_ids UUID[] NOT NULL CHECK (cardinality(claim_ids) > 0),
    prompt_version TEXT NOT NULL,
    model_version TEXT NOT NULL,
    privacy_tier INT NOT NULL,
    raw_payload JSONB NOT NULL,
    CHECK (
        (object_text IS NOT NULL AND object_json IS NULL)
        OR (object_text IS NULL AND object_json IS NOT NULL)
    )
);

CREATE INDEX beliefs_group_idx
    ON beliefs (subject_normalized, predicate, group_object_key);
CREATE UNIQUE INDEX beliefs_active_group_unique_idx
    ON beliefs (subject_normalized, predicate, group_object_key)
    WHERE valid_to IS NULL
      AND status IN ('candidate', 'provisional', 'accepted');
CREATE INDEX beliefs_status_stability_idx ON beliefs (status, stability_class);
CREATE INDEX beliefs_evidence_ids_gin_idx ON beliefs USING gin (evidence_ids);
CREATE INDEX beliefs_claim_ids_gin_idx ON beliefs USING gin (claim_ids);
CREATE INDEX beliefs_superseded_by_idx ON beliefs (superseded_by);

CREATE TABLE belief_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    belief_id UUID NOT NULL REFERENCES beliefs(id),
    transition_kind TEXT NOT NULL CHECK (
        transition_kind IN (
            'insert',
            'close',
            'supersede',
            'promote',
            'demote',
            'reject',
            'reactivate'
        )
    ),
    previous_status TEXT NULL,
    new_status TEXT NOT NULL,
    previous_valid_to TIMESTAMPTZ NULL,
    new_valid_to TIMESTAMPTZ NULL,
    prompt_version TEXT NOT NULL,
    model_version TEXT NOT NULL,
    input_claim_ids UUID[] NULL,
    evidence_message_ids UUID[] NOT NULL DEFAULT '{}'::uuid[],
    score_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_uuid UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX belief_audit_belief_id_idx ON belief_audit (belief_id);
CREATE INDEX belief_audit_request_uuid_idx ON belief_audit (request_uuid);

CREATE TABLE contradictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    belief_a_id UUID NOT NULL REFERENCES beliefs(id),
    belief_b_id UUID NOT NULL REFERENCES beliefs(id),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    detection_kind TEXT NOT NULL CHECK (
        detection_kind IN ('same_subject_predicate', 'reclassification_recompute')
    ),
    resolution_status TEXT NOT NULL DEFAULT 'open' CHECK (
        resolution_status IN (
            'open',
            'auto_resolved',
            'human_resolved',
            'irreconcilable'
        )
    ),
    resolution_kind TEXT NULL,
    resolved_at TIMESTAMPTZ NULL,
    privacy_tier INT NOT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (belief_a_id <> belief_b_id)
);

CREATE INDEX contradictions_beliefs_idx
    ON contradictions (belief_a_id, belief_b_id);
CREATE INDEX contradictions_status_idx
    ON contradictions (resolution_status, detection_kind);

CREATE OR REPLACE FUNCTION fn_claim_extractions_mutation_guard()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'claim_extractions rows cannot be deleted'
            USING ERRCODE = 'P0001';
    END IF;

    IF (
        NEW.id IS NOT DISTINCT FROM OLD.id
        AND NEW.segment_id IS NOT DISTINCT FROM OLD.segment_id
        AND NEW.generation_id IS NOT DISTINCT FROM OLD.generation_id
        AND NEW.extraction_prompt_version IS NOT DISTINCT FROM OLD.extraction_prompt_version
        AND NEW.extraction_model_version IS NOT DISTINCT FROM OLD.extraction_model_version
        AND NEW.request_profile_version IS NOT DISTINCT FROM OLD.request_profile_version
        AND NEW.created_at IS NOT DISTINCT FROM OLD.created_at
    ) THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION
        'claim_extractions updates are limited to status, claim_count, completed_at, and raw_payload'
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER claim_extractions_mutation_guard
    BEFORE UPDATE OR DELETE ON claim_extractions
    FOR EACH ROW EXECUTE FUNCTION fn_claim_extractions_mutation_guard();

CREATE OR REPLACE FUNCTION fn_claims_insert_prepare_validate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    segment_message_ids UUID[];
    segment_generation_id UUID;
    segment_conversation_id UUID;
    extraction_segment_id UUID;
    extraction_generation_id UUID;
    parent_extraction_prompt_version TEXT;
    parent_extraction_model_version TEXT;
    parent_request_profile_version TEXT;
    vocab predicate_vocabulary%ROWTYPE;
    required_key TEXT;
BEGIN
    NEW.subject_normalized := engram_normalize_subject(NEW.subject_text);

    SELECT s.message_ids, s.generation_id, s.conversation_id
    INTO segment_message_ids, segment_generation_id, segment_conversation_id
    FROM segments s
    WHERE s.id = NEW.segment_id;

    IF segment_message_ids IS NULL THEN
        RAISE EXCEPTION
            'claim segment not found: %',
            NEW.segment_id
            USING ERRCODE = '23503';
    END IF;

    IF NOT (NEW.evidence_message_ids <@ segment_message_ids) THEN
        RAISE EXCEPTION
            'claim evidence_message_ids must be a subset of segment message_ids'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.generation_id IS DISTINCT FROM segment_generation_id THEN
        RAISE EXCEPTION
            'claim generation_id must match segment generation_id'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.conversation_id IS DISTINCT FROM segment_conversation_id THEN
        RAISE EXCEPTION
            'claim conversation_id must match segment conversation_id'
            USING ERRCODE = '23514';
    END IF;

    SELECT
        ce.segment_id,
        ce.generation_id,
        ce.extraction_prompt_version,
        ce.extraction_model_version,
        ce.request_profile_version
    INTO
        extraction_segment_id,
        extraction_generation_id,
        parent_extraction_prompt_version,
        parent_extraction_model_version,
        parent_request_profile_version
    FROM claim_extractions ce
    WHERE ce.id = NEW.extraction_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'claim extraction_id not found: %',
            NEW.extraction_id
            USING ERRCODE = '23503';
    END IF;

    IF NEW.segment_id IS DISTINCT FROM extraction_segment_id THEN
        RAISE EXCEPTION
            'claim extraction_id must match claim segment_id'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.generation_id IS DISTINCT FROM extraction_generation_id THEN
        RAISE EXCEPTION
            'claim extraction_id must match claim generation_id'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.extraction_prompt_version IS DISTINCT FROM parent_extraction_prompt_version
        OR NEW.extraction_model_version IS DISTINCT FROM parent_extraction_model_version
        OR NEW.request_profile_version IS DISTINCT FROM parent_request_profile_version
    THEN
        RAISE EXCEPTION
            'claim derivation columns must match parent claim_extractions row'
            USING ERRCODE = '23514';
    END IF;

    SELECT * INTO vocab
    FROM predicate_vocabulary
    WHERE predicate = NEW.predicate;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'unknown claim predicate: %',
            NEW.predicate
            USING ERRCODE = '23503';
    END IF;

    IF NEW.stability_class <> vocab.stability_class THEN
        RAISE EXCEPTION
            'claim stability_class does not match predicate vocabulary'
            USING ERRCODE = '23514';
    END IF;

    IF vocab.object_kind = 'text' AND NEW.object_text IS NULL THEN
        RAISE EXCEPTION
            'claim predicate % requires object_text',
            NEW.predicate
            USING ERRCODE = '23514';
    END IF;

    IF vocab.object_kind = 'json' AND NEW.object_json IS NULL THEN
        RAISE EXCEPTION
            'claim predicate % requires object_json',
            NEW.predicate
            USING ERRCODE = '23514';
    END IF;

    IF NEW.object_json IS NOT NULL THEN
        FOREACH required_key IN ARRAY vocab.required_object_keys LOOP
            IF NOT (NEW.object_json ? required_key) THEN
                RAISE EXCEPTION
                    'claim predicate % object_json missing required key %',
                    NEW.predicate,
                    required_key
                    USING ERRCODE = '23514';
            END IF;
        END LOOP;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER claims_insert_prepare_validate
    BEFORE INSERT ON claims
    FOR EACH ROW EXECUTE FUNCTION fn_claims_insert_prepare_validate();

CREATE OR REPLACE FUNCTION fn_claims_insert_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'claims are insert-only; % is not allowed',
        TG_OP
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER claims_insert_only
    BEFORE UPDATE OR DELETE ON claims
    FOR EACH ROW EXECUTE FUNCTION fn_claims_insert_only();

CREATE OR REPLACE FUNCTION fn_beliefs_prepare_validate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    transition_request TEXT;
    vocab predicate_vocabulary%ROWTYPE;
    key_name TEXT;
    key_parts TEXT[] := '{}'::text[];
    key_value TEXT;
BEGIN
    transition_request := current_setting('engram.transition_in_progress', true);
    IF transition_request IS NULL OR transition_request = '' THEN
        RAISE EXCEPTION
            'belief mutations require engram.transition_in_progress'
            USING ERRCODE = 'P0001';
    END IF;

    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'beliefs cannot be deleted'
            USING ERRCODE = 'P0001';
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF (
            NEW.id IS NOT DISTINCT FROM OLD.id
            AND NEW.subject_text IS NOT DISTINCT FROM OLD.subject_text
            AND NEW.subject_normalized IS NOT DISTINCT FROM OLD.subject_normalized
            AND NEW.predicate IS NOT DISTINCT FROM OLD.predicate
            AND NEW.cardinality_class IS NOT DISTINCT FROM OLD.cardinality_class
            AND NEW.object_text IS NOT DISTINCT FROM OLD.object_text
            AND NEW.object_json IS NOT DISTINCT FROM OLD.object_json
            AND NEW.group_object_key IS NOT DISTINCT FROM OLD.group_object_key
            AND NEW.valid_from IS NOT DISTINCT FROM OLD.valid_from
            AND NEW.observed_at IS NOT DISTINCT FROM OLD.observed_at
            AND NEW.recorded_at IS NOT DISTINCT FROM OLD.recorded_at
            AND NEW.extracted_at IS NOT DISTINCT FROM OLD.extracted_at
            AND NEW.stability_class IS NOT DISTINCT FROM OLD.stability_class
            AND NEW.confidence IS NOT DISTINCT FROM OLD.confidence
            AND NEW.evidence_ids IS NOT DISTINCT FROM OLD.evidence_ids
            AND NEW.claim_ids IS NOT DISTINCT FROM OLD.claim_ids
            AND NEW.prompt_version IS NOT DISTINCT FROM OLD.prompt_version
            AND NEW.model_version IS NOT DISTINCT FROM OLD.model_version
            AND NEW.privacy_tier IS NOT DISTINCT FROM OLD.privacy_tier
            AND NEW.raw_payload IS NOT DISTINCT FROM OLD.raw_payload
        ) THEN
            RETURN NEW;
        END IF;

        RAISE EXCEPTION
            'belief updates are limited to valid_to, closed_at, superseded_by, and status'
            USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO vocab
    FROM predicate_vocabulary
    WHERE predicate = NEW.predicate;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'unknown belief predicate: %',
            NEW.predicate
            USING ERRCODE = '23503';
    END IF;

    NEW.subject_normalized := engram_normalize_subject(NEW.subject_text);
    NEW.cardinality_class := vocab.cardinality_class;
    NEW.stability_class := vocab.stability_class;

    IF vocab.object_kind = 'text' AND NEW.object_text IS NULL THEN
        RAISE EXCEPTION
            'belief predicate % requires object_text',
            NEW.predicate
            USING ERRCODE = '23514';
    END IF;

    IF vocab.object_kind = 'json' AND NEW.object_json IS NULL THEN
        RAISE EXCEPTION
            'belief predicate % requires object_json',
            NEW.predicate
            USING ERRCODE = '23514';
    END IF;

    IF vocab.cardinality_class = 'single_current' THEN
        NEW.group_object_key := '';
    ELSIF vocab.object_kind = 'text' THEN
        NEW.group_object_key := engram_normalize_subject(NEW.object_text);
    ELSE
        FOREACH key_name IN ARRAY vocab.group_object_keys LOOP
            key_value := COALESCE(NEW.object_json ->> key_name, '');
            key_parts := array_append(
                key_parts,
                engram_normalize_group_object_value(key_value)
            );
        END LOOP;
        NEW.group_object_key := array_to_string(key_parts, U&'\001F');
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER beliefs_prepare_validate
    BEFORE INSERT OR UPDATE OR DELETE ON beliefs
    FOR EACH ROW EXECUTE FUNCTION fn_beliefs_prepare_validate();

CREATE OR REPLACE FUNCTION fn_belief_audit_append_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'belief_audit is append-only; % is not allowed',
        TG_OP
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER belief_audit_append_only
    BEFORE UPDATE OR DELETE ON belief_audit
    FOR EACH ROW EXECUTE FUNCTION fn_belief_audit_append_only();

CREATE OR REPLACE FUNCTION fn_contradictions_mutation_guard()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'contradictions cannot be deleted'
            USING ERRCODE = 'P0001';
    END IF;

    IF (
        NEW.id IS NOT DISTINCT FROM OLD.id
        AND NEW.belief_a_id IS NOT DISTINCT FROM OLD.belief_a_id
        AND NEW.belief_b_id IS NOT DISTINCT FROM OLD.belief_b_id
        AND NEW.detected_at IS NOT DISTINCT FROM OLD.detected_at
        AND NEW.detection_kind IS NOT DISTINCT FROM OLD.detection_kind
        AND NEW.privacy_tier IS NOT DISTINCT FROM OLD.privacy_tier
        AND NEW.raw_payload IS NOT DISTINCT FROM OLD.raw_payload
    ) THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION
        'contradictions updates are limited to resolution fields'
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER contradictions_mutation_guard
    BEFORE UPDATE OR DELETE ON contradictions
    FOR EACH ROW EXECUTE FUNCTION fn_contradictions_mutation_guard();
