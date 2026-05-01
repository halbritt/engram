ALTER TABLE notes
    ADD COLUMN IF NOT EXISTS privacy_tier INT NOT NULL DEFAULT 1;

ALTER TABLE consolidation_progress
    ADD COLUMN IF NOT EXISTS error_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_error TEXT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS consolidation_progress_stage_scope_unique_idx
    ON consolidation_progress (stage, scope);

CREATE TABLE segment_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_kind TEXT NOT NULL CHECK (parent_kind IN ('conversation', 'note', 'capture')),
    parent_id UUID NOT NULL,
    segmenter_prompt_version TEXT NOT NULL,
    segmenter_model_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'segmenting',
            'segmented',
            'embedding',
            'active',
            'superseded',
            'failed'
        )
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at TIMESTAMPTZ NULL,
    superseded_at TIMESTAMPTZ NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX segment_generations_active_parent_idx
    ON segment_generations (parent_kind, parent_id)
    WHERE status = 'active';

CREATE INDEX segment_generations_parent_version_idx
    ON segment_generations (
        parent_kind,
        parent_id,
        segmenter_prompt_version,
        segmenter_model_version
    );

CREATE TABLE segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id UUID NOT NULL REFERENCES segment_generations(id),
    source_id UUID NOT NULL REFERENCES sources(id),
    source_kind source_kind NOT NULL,
    conversation_id UUID NULL REFERENCES conversations(id),
    note_id UUID NULL REFERENCES notes(id),
    capture_id UUID NULL REFERENCES captures(id),
    message_ids UUID[] NOT NULL,
    sequence_index INT NOT NULL,
    content_text TEXT NOT NULL,
    summary_text TEXT NULL,
    window_strategy TEXT NOT NULL DEFAULT 'whole'
        CHECK (window_strategy IN ('whole', 'windowed')),
    window_index INT NULL,
    segmenter_prompt_version TEXT NOT NULL,
    segmenter_model_version TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT false,
    invalidated_at TIMESTAMPTZ NULL,
    invalidation_reason TEXT NULL,
    privacy_tier INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload JSONB NOT NULL,
    CHECK (
        ((conversation_id IS NOT NULL)::int
        + (note_id IS NOT NULL)::int
        + (capture_id IS NOT NULL)::int) = 1
    )
);

CREATE UNIQUE INDEX segments_active_conversation_sequence_idx
    ON segments (conversation_id, sequence_index)
    WHERE is_active = true AND conversation_id IS NOT NULL;

CREATE UNIQUE INDEX segments_active_note_sequence_idx
    ON segments (note_id, sequence_index)
    WHERE is_active = true AND note_id IS NOT NULL;

CREATE UNIQUE INDEX segments_active_capture_sequence_idx
    ON segments (capture_id, sequence_index)
    WHERE is_active = true AND capture_id IS NOT NULL;

CREATE INDEX segments_generation_idx
    ON segments (generation_id, sequence_index);

CREATE INDEX segments_message_ids_gin_idx
    ON segments USING gin (message_ids);

CREATE TABLE embedding_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    input_sha256 TEXT NOT NULL,
    embedding_model_version TEXT NOT NULL,
    embedding_dimension INT NOT NULL,
    embedding vector NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (input_sha256, embedding_model_version),
    CHECK (vector_dims(embedding) = embedding_dimension)
);

CREATE TABLE segment_embeddings (
    segment_id UUID NOT NULL REFERENCES segments(id),
    generation_id UUID NOT NULL REFERENCES segment_generations(id),
    embedding_cache_id UUID NOT NULL REFERENCES embedding_cache(id),
    embedding vector NOT NULL,
    embedding_model_version TEXT NOT NULL,
    embedding_dimension INT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT false,
    privacy_tier INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (segment_id, embedding_model_version),
    CHECK (vector_dims(embedding) = embedding_dimension)
);

CREATE INDEX segment_embeddings_generation_idx
    ON segment_embeddings (generation_id);

CREATE INDEX segment_embeddings_active_model_tier_idx
    ON segment_embeddings (embedding_model_version, embedding_dimension, privacy_tier)
    WHERE is_active = true;

CREATE INDEX segment_embeddings_nomic_768_hnsw_idx
    ON segment_embeddings
    USING hnsw ((embedding::vector(768)) vector_cosine_ops)
    WHERE (
        is_active = true
        AND embedding_model_version = 'nomic-embed-text:latest'
        AND embedding_dimension = 768
    );

CREATE OR REPLACE FUNCTION prevent_segment_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'segments are immutable; DELETE is not allowed'
            USING ERRCODE = 'P0001';
    END IF;

    IF (
        NEW.id IS NOT DISTINCT FROM OLD.id
        AND NEW.generation_id IS NOT DISTINCT FROM OLD.generation_id
        AND NEW.source_id IS NOT DISTINCT FROM OLD.source_id
        AND NEW.source_kind IS NOT DISTINCT FROM OLD.source_kind
        AND NEW.conversation_id IS NOT DISTINCT FROM OLD.conversation_id
        AND NEW.note_id IS NOT DISTINCT FROM OLD.note_id
        AND NEW.capture_id IS NOT DISTINCT FROM OLD.capture_id
        AND NEW.message_ids IS NOT DISTINCT FROM OLD.message_ids
        AND NEW.sequence_index IS NOT DISTINCT FROM OLD.sequence_index
        AND NEW.content_text IS NOT DISTINCT FROM OLD.content_text
        AND NEW.summary_text IS NOT DISTINCT FROM OLD.summary_text
        AND NEW.window_strategy IS NOT DISTINCT FROM OLD.window_strategy
        AND NEW.window_index IS NOT DISTINCT FROM OLD.window_index
        AND NEW.segmenter_prompt_version IS NOT DISTINCT FROM OLD.segmenter_prompt_version
        AND NEW.segmenter_model_version IS NOT DISTINCT FROM OLD.segmenter_model_version
        AND NEW.privacy_tier IS NOT DISTINCT FROM OLD.privacy_tier
        AND NEW.created_at IS NOT DISTINCT FROM OLD.created_at
        AND NEW.raw_payload IS NOT DISTINCT FROM OLD.raw_payload
    ) THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION
        'segments are immutable except activation and invalidation metadata'
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER segments_immutable
    BEFORE UPDATE OR DELETE ON segments
    FOR EACH ROW EXECUTE FUNCTION prevent_segment_mutation();

CREATE OR REPLACE FUNCTION prevent_embedding_cache_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'embedding_cache is immutable; % is not allowed',
        TG_OP
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER embedding_cache_immutable
    BEFORE UPDATE OR DELETE ON embedding_cache
    FOR EACH ROW EXECUTE FUNCTION prevent_embedding_cache_mutation();

CREATE OR REPLACE FUNCTION prevent_segment_embedding_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'segment_embeddings are immutable; DELETE is not allowed'
            USING ERRCODE = 'P0001';
    END IF;

    IF (
        NEW.segment_id IS NOT DISTINCT FROM OLD.segment_id
        AND NEW.generation_id IS NOT DISTINCT FROM OLD.generation_id
        AND NEW.embedding_cache_id IS NOT DISTINCT FROM OLD.embedding_cache_id
        AND NEW.embedding IS NOT DISTINCT FROM OLD.embedding
        AND NEW.embedding_model_version IS NOT DISTINCT FROM OLD.embedding_model_version
        AND NEW.embedding_dimension IS NOT DISTINCT FROM OLD.embedding_dimension
        AND NEW.privacy_tier IS NOT DISTINCT FROM OLD.privacy_tier
        AND NEW.created_at IS NOT DISTINCT FROM OLD.created_at
    ) THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION
        'segment_embeddings are immutable except activation metadata'
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER segment_embeddings_immutable
    BEFORE UPDATE OR DELETE ON segment_embeddings
    FOR EACH ROW EXECUTE FUNCTION prevent_segment_embedding_mutation();

CREATE OR REPLACE FUNCTION validate_conversation_segment_message_ids()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    expected_message_ids UUID[];
    expected_count INT;
    provided_count INT;
BEGIN
    provided_count := cardinality(NEW.message_ids);

    IF NEW.conversation_id IS NOT NULL THEN
        IF provided_count = 0 THEN
            RAISE EXCEPTION
                'conversation segments must cite at least one message id'
                USING ERRCODE = '23514';
        END IF;

        SELECT array_agg(m.id ORDER BY m.sequence_index), count(*)
        INTO expected_message_ids, expected_count
        FROM messages m
        WHERE m.conversation_id = NEW.conversation_id
          AND m.id = ANY(NEW.message_ids);

        IF expected_count <> provided_count THEN
            RAISE EXCEPTION
                'conversation segment message_ids must all exist in the same conversation'
                USING ERRCODE = '23514';
        END IF;

        IF expected_message_ids IS DISTINCT FROM NEW.message_ids THEN
            RAISE EXCEPTION
                'conversation segment message_ids must follow message sequence order'
                USING ERRCODE = '23514';
        END IF;
    ELSE
        IF provided_count <> 0 THEN
            RAISE EXCEPTION
                'non-conversation segments must not cite message ids'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER segments_message_ids_valid
    BEFORE INSERT ON segments
    FOR EACH ROW EXECUTE FUNCTION validate_conversation_segment_message_ids();
