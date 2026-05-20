# Product Surface Slice

Scaffold the smallest operator product surface for claim-grounding grant
approval and revocation.

Required:

1. Prefer CLI-first if that matches the current codebase better than a web UI.
2. Show exact `surface_form`, `search_query`, `query_text_class`,
   `query_privacy_tier`, allowed targets, request id, tenant/corpus, and source
   refs before approval.
3. Add commands/tests for listing pending/draft grants and recording approve,
   deny, and revoke rows.
4. Do not send network requests from the product surface.

Write `docs/reviews/rfc0053-runtime-completion/PRODUCT_SURFACE_HANDOFF.md`.
