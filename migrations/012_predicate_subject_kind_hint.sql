-- RFC 0028 / D-082: surface predicate intent across extraction and interview.
-- The new hint is advisory metadata for prompts and review UX; it is not a
-- constraint on claims or beliefs.

ALTER TABLE predicate_vocabulary
    ADD COLUMN subject_kind_hint TEXT NULL;

ALTER TABLE predicate_vocabulary
    ADD CONSTRAINT chk_predicate_vocabulary_subject_kind_hint_nonblank
    CHECK (subject_kind_hint IS NULL OR btrim(subject_kind_hint) <> '');

UPDATE predicate_vocabulary AS pv
SET subject_kind_hint = hints.subject_kind_hint
FROM (
    VALUES
        ('has_name', 'persons only'),
        ('has_pronouns', 'persons only'),
        ('born_on', 'persons only'),
        ('lives_at', 'persons or households'),
        ('holds_role_at', 'persons only'),
        ('has_pet', 'persons only'),
        ('is_related_to', 'persons only'),
        ('is_friends_with', 'persons only'),
        ('works_with', 'persons or organizations'),
        ('prefers', 'persons only'),
        ('dislikes', 'persons only'),
        ('believes', 'persons only'),
        ('uses_tool', 'persons or projects'),
        ('drives', 'persons only'),
        ('eats_diet', 'persons only'),
        ('working_on', 'persons only'),
        ('project_status_is', 'projects only'),
        ('owns_repo', 'persons or organizations'),
        ('wants_to', 'persons only'),
        ('plans_to', 'persons only'),
        ('intends_to', 'persons only'),
        ('must_do', 'persons only'),
        ('committed_to', 'persons only'),
        ('feels', 'persons only'),
        ('relationship_with', 'persons only'),
        ('met_with', 'persons only'),
        ('talked_about', 'persons only'),
        ('studied', 'persons only'),
        ('traveled_to', 'persons only')
) AS hints(predicate, subject_kind_hint)
WHERE pv.predicate = hints.predicate;
