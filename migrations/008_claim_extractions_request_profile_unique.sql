DROP INDEX IF EXISTS claim_extractions_active_unique_idx;

CREATE UNIQUE INDEX claim_extractions_active_unique_idx
    ON claim_extractions (
        segment_id,
        extraction_prompt_version,
        extraction_model_version,
        request_profile_version
    )
    WHERE status IN ('extracting', 'extracted');
