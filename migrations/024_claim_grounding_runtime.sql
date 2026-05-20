-- RFC 0053: claim-grounding request/response/grant audit scaffold.
-- These tables are sidecars for future extraction grounding. They do not
-- mutate claims, beliefs, raw evidence, or local grounding evidence.

CREATE TABLE IF NOT EXISTS claim_grounding_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    schema_version TEXT NOT NULL DEFAULT 'claim_grounding.request.v1'
        CHECK (schema_version = 'claim_grounding.request.v1'),
    extraction_id UUID NULL REFERENCES claim_extractions(id),
    segment_id UUID NULL REFERENCES segments(id),
    extraction_run_id TEXT NULL,
    extraction_prompt_version TEXT NOT NULL,
    extraction_model_version TEXT NOT NULL,
    surface_form TEXT NOT NULL,
    mention_role TEXT NOT NULL CHECK (mention_role IN ('subject', 'object', 'context')),
    candidate_entity_kinds TEXT[] NOT NULL CHECK (cardinality(candidate_entity_kinds) > 0),
    source_refs JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(source_refs) = 'array'),
    local_context_capsule JSONB NOT NULL DEFAULT '{"mode":"none","text":null}'::jsonb
        CHECK (jsonb_typeof(local_context_capsule) = 'object'),
    allowed_modes TEXT[] NOT NULL DEFAULT ARRAY['local_lookup']::TEXT[]
        CHECK (
            cardinality(allowed_modes) > 0
            AND allowed_modes <@ ARRAY['local_lookup','network_fetch']::TEXT[]
        ),
    network_grant JSONB NULL CHECK (
        network_grant IS NULL OR jsonb_typeof(network_grant) = 'object'
    ),
    privacy_tier_ceiling INT NOT NULL DEFAULT 1 CHECK (privacy_tier_ceiling >= 0),
    sensitivity_ceiling TEXT[] NOT NULL DEFAULT ARRAY['routine_project']::TEXT[]
        CHECK (cardinality(sensitivity_ceiling) > 0),
    request_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(request_payload) = 'object'),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (extraction_run_id IS NULL OR btrim(extraction_run_id) <> ''),
    CHECK (btrim(extraction_prompt_version) <> ''),
    CHECK (btrim(extraction_model_version) <> ''),
    CHECK (btrim(surface_form) <> ''),
    CHECK (
        NOT ('network_fetch' = ANY(allowed_modes))
        OR network_grant IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS claim_grounding_requests_scope_requested_idx
    ON claim_grounding_requests (tenant_id, corpus_id, requested_at DESC);

CREATE INDEX IF NOT EXISTS claim_grounding_requests_extraction_idx
    ON claim_grounding_requests (extraction_id, requested_at DESC)
    WHERE extraction_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS claim_grounding_requests_segment_idx
    ON claim_grounding_requests (segment_id, requested_at DESC)
    WHERE segment_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS claim_grounding_requests_surface_idx
    ON claim_grounding_requests (tenant_id, corpus_id, lower(surface_form), requested_at DESC);

CREATE TABLE IF NOT EXISTS claim_grounding_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    request_id UUID NULL REFERENCES claim_grounding_requests(id),
    schema_version TEXT NOT NULL DEFAULT 'claim_grounding.grant.v1'
        CHECK (schema_version = 'claim_grounding.grant.v1'),
    grant_status TEXT NOT NULL CHECK (
        grant_status IN ('draft', 'approved', 'denied', 'revoked', 'expired')
    ),
    grant_purpose TEXT NOT NULL CHECK (grant_purpose IN ('entity_grounding')),
    target_mode TEXT NOT NULL CHECK (target_mode IN ('network_fetch')),
    surface_form TEXT NOT NULL,
    search_query TEXT NOT NULL,
    query_text_class TEXT NOT NULL CHECK (
        query_text_class IN ('entity_surface_form', 'operator_entered', 'broker_minimized')
    ),
    query_privacy_tier INT NOT NULL CHECK (query_privacy_tier >= 0),
    allowed_network_targets TEXT[] NOT NULL CHECK (
        cardinality(allowed_network_targets) > 0
        AND allowed_network_targets <@ ARRAY['internet_search','public_dataset_api']::TEXT[]
    ),
    granted_by TEXT NULL,
    granted_at TIMESTAMPTZ NULL,
    expires_at TIMESTAMPTZ NULL,
    revoked_at TIMESTAMPTZ NULL,
    grant_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(grant_payload) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(surface_form) <> ''),
    CHECK (btrim(search_query) <> ''),
    CHECK (granted_by IS NULL OR btrim(granted_by) <> ''),
    CHECK (grant_status <> 'approved' OR granted_at IS NOT NULL),
    CHECK (grant_status <> 'revoked' OR revoked_at IS NOT NULL),
    CHECK (expires_at IS NULL OR granted_at IS NULL OR expires_at > granted_at)
);

CREATE INDEX IF NOT EXISTS claim_grounding_grants_scope_status_idx
    ON claim_grounding_grants (tenant_id, corpus_id, grant_status, created_at DESC);

CREATE INDEX IF NOT EXISTS claim_grounding_grants_expiry_idx
    ON claim_grounding_grants (tenant_id, corpus_id, expires_at)
    WHERE grant_status = 'approved' AND expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS claim_grounding_grants_request_idx
    ON claim_grounding_grants (request_id, created_at DESC)
    WHERE request_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS claim_grounding_network_dispatches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES claim_grounding_requests(id),
    grant_id UUID NOT NULL REFERENCES claim_grounding_grants(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    schema_version TEXT NOT NULL DEFAULT 'claim_grounding.network_dispatch.v1'
        CHECK (schema_version = 'claim_grounding.network_dispatch.v1'),
    target_mode TEXT NOT NULL CHECK (target_mode IN ('network_fetch')),
    target_adapter TEXT NOT NULL CHECK (
        target_adapter IN ('internet_search', 'public_dataset_api')
    ),
    search_query TEXT NOT NULL,
    query_privacy_tier INT NOT NULL CHECK (query_privacy_tier >= 0),
    attempt_number INT NOT NULL DEFAULT 1 CHECK (attempt_number > 0),
    dispatch_status TEXT NOT NULL CHECK (
        dispatch_status IN ('prepared', 'dispatched', 'succeeded', 'failed', 'denied', 'skipped')
    ),
    denial_reason TEXT NULL,
    dispatch_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(dispatch_payload) = 'object'),
    result_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(result_metadata) = 'object'),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(search_query) <> ''),
    CHECK (denial_reason IS NULL OR btrim(denial_reason) <> '')
);

CREATE UNIQUE INDEX IF NOT EXISTS claim_grounding_network_dispatches_attempt_idx
    ON claim_grounding_network_dispatches (
        request_id,
        grant_id,
        target_adapter,
        attempt_number
    );

CREATE INDEX IF NOT EXISTS claim_grounding_network_dispatches_scope_status_idx
    ON claim_grounding_network_dispatches (tenant_id, corpus_id, dispatch_status, requested_at DESC);

CREATE TABLE IF NOT EXISTS claim_grounding_grant_uses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grant_id UUID NOT NULL REFERENCES claim_grounding_grants(id),
    request_id UUID NOT NULL REFERENCES claim_grounding_requests(id),
    dispatch_id UUID NULL REFERENCES claim_grounding_network_dispatches(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    schema_version TEXT NOT NULL DEFAULT 'claim_grounding.grant_use.v1'
        CHECK (schema_version = 'claim_grounding.grant_use.v1'),
    use_status TEXT NOT NULL CHECK (
        use_status IN (
            'verified',
            'denied',
            'expired',
            'revoked',
            'query_mismatch',
            'target_mismatch',
            'privacy_exceeded',
            'error'
        )
    ),
    target_adapter TEXT NULL CHECK (
        target_adapter IS NULL OR target_adapter IN ('internet_search', 'public_dataset_api')
    ),
    search_query TEXT NOT NULL,
    query_privacy_tier INT NOT NULL CHECK (query_privacy_tier >= 0),
    expires_at_snapshot TIMESTAMPTZ NULL,
    use_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(use_payload) = 'object'),
    verified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(search_query) <> '')
);

CREATE INDEX IF NOT EXISTS claim_grounding_grant_uses_grant_idx
    ON claim_grounding_grant_uses (grant_id, verified_at DESC);

CREATE INDEX IF NOT EXISTS claim_grounding_grant_uses_request_idx
    ON claim_grounding_grant_uses (request_id, verified_at DESC);

CREATE INDEX IF NOT EXISTS claim_grounding_grant_uses_status_idx
    ON claim_grounding_grant_uses (tenant_id, corpus_id, use_status, verified_at DESC);

CREATE TABLE IF NOT EXISTS claim_grounding_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES claim_grounding_requests(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    schema_version TEXT NOT NULL DEFAULT 'claim_grounding.response.v1'
        CHECK (schema_version = 'claim_grounding.response.v1'),
    status TEXT NOT NULL CHECK (
        status IN ('resolved', 'ambiguous', 'not_found', 'denied', 'deferred', 'error')
    ),
    mode TEXT NOT NULL CHECK (mode IN ('local_lookup', 'network_fetch')),
    network_fetch TEXT NOT NULL CHECK (
        network_fetch IN (
            'not_requested',
            'unsupported',
            'denied',
            'performed_by_grounding_broker'
        )
    ),
    candidates JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(candidates) = 'array'),
    omissions JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(omissions) = 'array'),
    broker_version TEXT NOT NULL,
    dataset_snapshots JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(dataset_snapshots) = 'array'),
    response_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(response_payload) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(broker_version) <> ''),
    CHECK (status <> 'resolved' OR jsonb_array_length(candidates) > 0),
    CHECK (network_fetch <> 'performed_by_grounding_broker' OR mode = 'network_fetch')
);

CREATE INDEX IF NOT EXISTS claim_grounding_responses_request_idx
    ON claim_grounding_responses (request_id, created_at DESC);

CREATE INDEX IF NOT EXISTS claim_grounding_responses_scope_status_idx
    ON claim_grounding_responses (tenant_id, corpus_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS claim_grounding_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES claim_grounding_requests(id),
    response_id UUID NULL REFERENCES claim_grounding_responses(id),
    claim_id UUID NULL REFERENCES claims(id),
    extraction_id UUID NULL REFERENCES claim_extractions(id),
    grounding_evidence_id UUID NULL REFERENCES entity_grounding_evidence(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    schema_version TEXT NOT NULL DEFAULT 'claim_grounding.link.v1'
        CHECK (schema_version = 'claim_grounding.link.v1'),
    link_kind TEXT NOT NULL CHECK (
        link_kind IN (
            'request_to_claim',
            'request_to_extraction',
            'response_candidate_to_claim',
            'response_candidate_to_evidence',
            'extraction_grounding_sidecar'
        )
    ),
    response_candidate_id TEXT NULL,
    link_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(link_payload) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (response_candidate_id IS NULL OR btrim(response_candidate_id) <> ''),
    CHECK (
        claim_id IS NOT NULL
        OR extraction_id IS NOT NULL
        OR grounding_evidence_id IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS claim_grounding_links_request_idx
    ON claim_grounding_links (request_id, created_at DESC);

CREATE INDEX IF NOT EXISTS claim_grounding_links_response_idx
    ON claim_grounding_links (response_id, created_at DESC)
    WHERE response_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS claim_grounding_links_claim_idx
    ON claim_grounding_links (claim_id, created_at DESC)
    WHERE claim_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS claim_grounding_links_extraction_idx
    ON claim_grounding_links (extraction_id, created_at DESC)
    WHERE extraction_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS claim_grounding_links_evidence_idx
    ON claim_grounding_links (grounding_evidence_id, created_at DESC)
    WHERE grounding_evidence_id IS NOT NULL;

CREATE OR REPLACE FUNCTION fn_claim_grounding_append_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'claim grounding table "%" is append-only; % is not allowed',
        TG_TABLE_NAME,
        TG_OP
        USING ERRCODE = 'P0001';
END;
$$;

DROP TRIGGER IF EXISTS claim_grounding_requests_append_only ON claim_grounding_requests;
CREATE TRIGGER claim_grounding_requests_append_only
    BEFORE UPDATE OR DELETE ON claim_grounding_requests
    FOR EACH ROW EXECUTE FUNCTION fn_claim_grounding_append_only();

DROP TRIGGER IF EXISTS claim_grounding_grants_append_only ON claim_grounding_grants;
CREATE TRIGGER claim_grounding_grants_append_only
    BEFORE UPDATE OR DELETE ON claim_grounding_grants
    FOR EACH ROW EXECUTE FUNCTION fn_claim_grounding_append_only();

DROP TRIGGER IF EXISTS claim_grounding_network_dispatches_append_only
    ON claim_grounding_network_dispatches;
CREATE TRIGGER claim_grounding_network_dispatches_append_only
    BEFORE UPDATE OR DELETE ON claim_grounding_network_dispatches
    FOR EACH ROW EXECUTE FUNCTION fn_claim_grounding_append_only();

DROP TRIGGER IF EXISTS claim_grounding_grant_uses_append_only ON claim_grounding_grant_uses;
CREATE TRIGGER claim_grounding_grant_uses_append_only
    BEFORE UPDATE OR DELETE ON claim_grounding_grant_uses
    FOR EACH ROW EXECUTE FUNCTION fn_claim_grounding_append_only();

DROP TRIGGER IF EXISTS claim_grounding_responses_append_only ON claim_grounding_responses;
CREATE TRIGGER claim_grounding_responses_append_only
    BEFORE UPDATE OR DELETE ON claim_grounding_responses
    FOR EACH ROW EXECUTE FUNCTION fn_claim_grounding_append_only();

DROP TRIGGER IF EXISTS claim_grounding_links_append_only ON claim_grounding_links;
CREATE TRIGGER claim_grounding_links_append_only
    BEFORE UPDATE OR DELETE ON claim_grounding_links
    FOR EACH ROW EXECUTE FUNCTION fn_claim_grounding_append_only();
