# Bench Review Export

This export is redacted. It must not contain segment text, claim text, evidence excerpts, or LLM responses.

## Session

- Run: `20260509T045641Z.rfc0028-predicate-intent-100.d01f44fd`
- Slice: `.scratch/benchmarks/extraction-backend/slices/rfc0028-predicate-intent-seed19-100.json`
- Run artifact: `.scratch/benchmarks/extraction-backend/20260509T045641Z.rfc0028-predicate-intent-100.d01f44fd/run.json`
- Segment records: `.scratch/benchmarks/extraction-backend/20260509T045641Z.rfc0028-predicate-intent-100.d01f44fd/segments.jsonl`
- Candidate prompt: `extractor.v9.d082.predicate-intent`
- Candidate model: `/home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf`
- Candidate profile: `openai-json-schema.d034.extraction-benchmark.v1`
- Prior prompt: `extractor.v8.d064.accounted-zero`
- Prior model: `/home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf`
- Prior profile: `ik-llama-json-schema.d034.v10.extractor-8192-accounted-zero`

## Summary

- Progress: `11/100` decided
- Remaining: `89`
- Run decision: `Bench review: needs more review`
- Run note: Zeroed-segment review found 1 candidate regression: 431fd7be-5cd8-4686-b4bf-d976cc31219e emitted zero claims where prior had working_on and feels claims.

## Counts

### Data states

- `candidate_zero`: `11`
- `complete`: `51`
- `prior_missing`: `38`

### Tags

- `count_changed`: `50`
- `high_drop_count`: `2`
- `predicate_mix_changed`: `54`
- `provenance_anomaly`: `30`
- `unchanged`: `41`
- `zeroed`: `11`

### Decisions

- `accept_candidate_change`: `10`
- `flag_candidate_regression`: `1`
- `undecided`: `89`

## Segments

| Segment | State | Tags | Prior | Candidate | Decision | Note |
|---------|-------|------|-------|-----------|----------|------|
| `0726c93f-2376-4e47-a273-eb7582e253c9` | `candidate_zero` | `zeroed, count_changed, predicate_mix_changed` | `8` | `0` | `accept_candidate_change` | these are products, not people |
| `1d13d0d1-35c5-4e92-81fd-2b341b8d6e31` | `candidate_zero` | `zeroed, count_changed, predicate_mix_changed` | `1` | `0` | `accept_candidate_change` | a setup fact, not a preference. |
| `2a419384-8a05-4a87-ab26-fa21ec5e9fbe` | `candidate_zero` | `zeroed, count_changed, predicate_mix_changed` | `1` | `0` | `accept_candidate_change` |  |
| `431fd7be-5cd8-4686-b4bf-d976cc31219e` | `candidate_zero` | `zeroed, count_changed, predicate_mix_changed` | `2` | `0` | `flag_candidate_regression` |  |
| `86d97778-c666-4c75-a569-4ed7894a6738` | `candidate_zero` | `zeroed, count_changed, predicate_mix_changed` | `3` | `0` | `accept_candidate_change` |  |
| `8d98e0a4-2ad3-4464-888c-4f0d5fa0c8b2` | `candidate_zero` | `zeroed, count_changed, predicate_mix_changed` | `7` | `0` | `accept_candidate_change` |  |
| `963bc3fb-716e-4f3d-9be1-a9b84bce532c` | `candidate_zero` | `zeroed, count_changed, predicate_mix_changed` | `2` | `0` | `accept_candidate_change` |  |
| `a7de1e53-ef68-4e78-a3f2-ca5238486481` | `candidate_zero` | `zeroed, count_changed, predicate_mix_changed` | `2` | `0` | `accept_candidate_change` |  |
| `ae053e3c-b55f-4302-a98f-c21033f50e57` | `candidate_zero` | `zeroed, count_changed, predicate_mix_changed` | `21` | `0` | `accept_candidate_change` |  |
| `dc3246f2-09b6-4275-be61-11f9d5e2f7ef` | `candidate_zero` | `zeroed, count_changed, predicate_mix_changed` | `2` | `0` | `accept_candidate_change` |  |
| `ebea134c-146c-45a5-bfea-650eebb81569` | `candidate_zero` | `zeroed, count_changed, predicate_mix_changed` | `5` | `0` | `accept_candidate_change` |  |
| `1afa726e-e038-4b53-bdc8-5e3f18123be9` | `complete` | `high_drop_count, provenance_anomaly, count_changed, predicate_mix_changed` | `13` | `6` | `undecided` |  |
| `d14298cf-6290-4c01-8839-31b79f2dd6a2` | `complete` | `high_drop_count, count_changed, predicate_mix_changed` | `6` | `11` | `undecided` |  |
| `0881dd0d-7714-4186-8f36-e70098b7f349` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `10` | `9` | `undecided` |  |
| `0c9b0f99-5444-4c2c-bd67-1083dab18454` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `13` | `11` | `undecided` |  |
| `21751873-aeaa-4049-bf19-ba6da7d7b95f` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `11` | `8` | `undecided` |  |
| `26d1c764-aa10-4c85-96e5-d6376aa27be1` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `4` | `2` | `undecided` |  |
| `2b05cabd-2b8e-4cc6-926d-ae36fa882574` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `7` | `6` | `undecided` |  |
| `339869c7-8007-412f-84a8-77f6cc2fed17` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `5` | `4` | `undecided` |  |
| `3d890c1f-cfed-4517-9f8c-06f3f5aa2598` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `13` | `12` | `undecided` |  |
| `440a4a7f-25c0-4d74-9a13-7c6f3e0749a6` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `33` | `11` | `undecided` |  |
| `449de250-f97a-4690-bfde-839586e3d3ea` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `4` | `3` | `undecided` |  |
| `4532e65d-36f9-408e-9993-9ee7afbe0ea6` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `28` | `11` | `undecided` |  |
| `4c8a22e7-8622-44b0-a9b3-3958ad7c9b88` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `84` | `77` | `undecided` |  |
| `690b867b-8fb3-4a59-8594-4cdf88bb1462` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `2` | `1` | `undecided` |  |
| `6e225652-46f6-459c-92b5-86e29db1de9c` | `complete` | `provenance_anomaly, count_changed` | `11` | `6` | `undecided` |  |
| `73665ef8-12ea-4b9b-8b8f-f260e3db27aa` | `complete` | `provenance_anomaly, count_changed` | `11` | `10` | `undecided` |  |
| `74ad993b-24cc-4084-829f-fe79e85f0f55` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `8` | `7` | `undecided` |  |
| `820ec814-c63c-4448-9f6b-849e26ebc65e` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `4` | `2` | `undecided` |  |
| `8fc70328-6c11-4b79-b0f2-9eecf6f3d0cd` | `complete` | `provenance_anomaly, predicate_mix_changed` | `3` | `3` | `undecided` |  |
| `94236124-b649-4fd7-b09c-7a9e2faa506f` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `37` | `23` | `undecided` |  |
| `9443bf1c-6884-4563-a515-5c8d68df74dd` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `4` | `3` | `undecided` |  |
| `9e1f6f79-3aff-4585-bc6d-0b5355c542d7` | `complete` | `provenance_anomaly, count_changed` | `2` | `1` | `undecided` |  |
| `a9072f3b-ed9c-45fc-80d2-d3ef6690d4ef` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `3` | `2` | `undecided` |  |
| `b8a37a7b-22a2-4c91-ab90-969ccd14d6b3` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `4` | `3` | `undecided` |  |
| `b9cc043f-3e86-4019-9f4b-d2d6a8c15c7b` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `6` | `4` | `undecided` |  |
| `c6e4b367-d020-4f12-829f-a0cc1ae180c2` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `18` | `12` | `undecided` |  |
| `d7e6cc3c-90af-4934-bbcb-1fef69eaf727` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `5` | `4` | `undecided` |  |
| `e1c10f32-9eb1-4885-9a8f-09428c5bc64b` | `complete` | `provenance_anomaly, count_changed` | `7` | `4` | `undecided` |  |
| `f0fc04c9-bfb8-4a9c-8fb4-e1d9cef2c27c` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `11` | `9` | `undecided` |  |
| `f157d832-2f23-425a-ba14-34e5a77a9211` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `9` | `8` | `undecided` |  |
| `f6739257-262a-4bb5-a40d-b4ea197c86f1` | `complete` | `provenance_anomaly, count_changed, predicate_mix_changed` | `29` | `4` | `undecided` |  |
| `133ef191-cb94-40fc-98dd-c8ea1e433854` | `complete` | `count_changed, predicate_mix_changed` | `2` | `3` | `undecided` |  |
| `1ab3008d-ef96-484a-b966-41c3c8be7cdd` | `complete` | `count_changed, predicate_mix_changed` | `14` | `15` | `undecided` |  |
| `5e3f11fc-d5f7-456e-9ee4-1c265af6001d` | `complete` | `count_changed, predicate_mix_changed` | `26` | `36` | `undecided` |  |
| `77779ec7-e70e-4aea-bc12-7044b0dfe330` | `complete` | `count_changed` | `1` | `2` | `undecided` |  |
| `96d8da45-c85f-472d-98cf-a9a0b37a2600` | `complete` | `count_changed, predicate_mix_changed` | `7` | `30` | `undecided` |  |
| `9b9abde6-8523-4255-85a2-b94d926eca38` | `complete` | `count_changed, predicate_mix_changed` | `4` | `9` | `undecided` |  |
| `bf36e556-bdf1-405b-9184-65f1e6036d10` | `complete` | `count_changed, predicate_mix_changed` | `3` | `6` | `undecided` |  |
| `e0d0ad8e-12ed-419d-b74a-9d94d608f463` | `complete` | `count_changed, predicate_mix_changed` | `4` | `11` | `undecided` |  |
| `ecbff65d-e721-4dca-94bc-c1e5199efd5f` | `complete` | `count_changed, predicate_mix_changed` | `7` | `13` | `undecided` |  |
| `057ef063-e09b-4f54-930e-6a07de4e6adc` | `complete` | `predicate_mix_changed` | `4` | `4` | `undecided` |  |
| `2e236376-81aa-475e-b33f-47b193d045b7` | `complete` | `predicate_mix_changed` | `2` | `2` | `undecided` |  |
| `63339f69-e80a-4d65-8a8b-a54a476b468a` | `complete` | `predicate_mix_changed` | `25` | `25` | `undecided` |  |
| `66c94e19-2ca2-4545-b322-dcd405ac2fc5` | `complete` | `predicate_mix_changed` | `2` | `2` | `undecided` |  |
| `7b2a984e-23fd-40d5-8ace-1ee59299cdd8` | `complete` | `predicate_mix_changed` | `2` | `2` | `undecided` |  |
| `cc27dc7d-74ba-4250-84f4-8bb943cc8445` | `complete` | `predicate_mix_changed` | `23` | `23` | `undecided` |  |
| `ea2a1edf-dcf5-415e-8988-17abd004d69e` | `complete` | `predicate_mix_changed` | `3` | `3` | `undecided` |  |
| `f4551bbb-0c53-4b59-a4de-0496eb26c5c4` | `complete` | `predicate_mix_changed` | `5` | `5` | `undecided` |  |
| `71772020-d592-448b-9646-ee02c9887b72` | `complete` | `unchanged` | `2` | `2` | `undecided` |  |
| `7435b691-7f41-4f35-aed6-ab24db561cd1` | `complete` | `unchanged` | `2` | `2` | `undecided` |  |
| `790ca7eb-d2a1-4734-9c6d-121598f591e5` | `complete` | `unchanged` | `3` | `3` | `undecided` |  |
| `041695d4-a375-4b36-9a0c-59afa2658ce1` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `0a6c67d1-0a0c-4b0f-8d3f-a3504cd94591` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `0bf45673-40f3-48d6-ae95-088461fe4aa9` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `1234c5ff-7c8e-4dbf-80a9-8e004e362869` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `13d62358-acfe-408a-95a2-1199efedf8ec` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `190fe053-64b4-44dc-8a6c-717a92d9e529` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `1fc28f3f-3a61-47bd-ab9c-99f7b6d9c5ea` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `2213a069-6c85-4a53-a318-dd97b9e369a2` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `22976209-0662-45db-bb6c-ed76f70a1dad` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `3519af54-46a9-443e-8449-03b7e20fd702` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `38e18a16-fa20-48dd-87b5-45617beff95c` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `3be89306-88ab-48f6-b949-e61eb40ab0e5` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `45128879-cda3-4c5a-bbc7-b682122dfe6a` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `4c8715bc-3c13-4ae2-9781-5205b9de60c4` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `52eaef94-8c78-4d7d-a293-a41d5b035b00` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `538f6661-3d82-42da-bf64-aef3b7e199dd` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `56a7a32c-62d1-4b9d-bcf6-c9e804cd0e4b` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `70eb8232-4c03-42a4-a77c-331e88e3f6c0` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `789aaee7-58c2-47db-ad20-b972622996f4` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `824fc823-d74c-4363-a492-19b4075a3485` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `85765c18-8c86-48e9-88c5-15fcec6bfeab` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `85ac60b2-bdb1-4e7b-8d39-53c6fc10b7dc` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `86ca9d72-fb5f-4916-857b-18c30991f3d9` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `8f950f2d-4f90-4f92-af38-f6d27056affc` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `96181f27-0509-4ca1-bf9f-cb64c226da72` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `9674d52c-9f6f-490c-bb1d-443368327380` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `a0b040b2-1eb5-47f9-801c-5a9e2bf597a2` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `aa0f7f5c-2596-46e7-a218-8848ad1ace83` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `b0cbd03c-6395-4d0f-bf98-88f8a344dd30` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `be801163-cd15-416d-ba0b-47c9f01615e4` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `c78116d6-345d-41dd-9f43-7a8d39819bdb` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `d1bb02aa-e527-481c-bfbc-d4492169a393` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `d35daab1-9097-4c87-95b1-1b7f9772624b` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `e80c2f66-634a-4e61-bab8-4a2a5ed709d6` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `ecdaf75e-90c6-41d5-ab33-dbcf7979cc67` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `edac56d4-b443-4340-82d1-3cbfc15c53b9` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `f67f8b98-179b-48d8-817f-9b60cfa33703` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
| `ff38a8e1-3b90-4523-89af-406a8106dba3` | `prior_missing` | `unchanged` | `n/a` | `0` | `undecided` |  |
