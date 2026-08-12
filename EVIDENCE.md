# Evidence

One proof per Definition-of-Done checkbox (§ 6 of the brief).

## AI Processing

- [x] Vision model produces structured output validated against a schema
  - Proof: `pytest tests/test_schema_validation.py -v` → all 4 tests PASSED
- [x] Low-confidence classifications are flagged instead of accepted
  - Proof: `app/vision.py` sets `low_confidence_flag` based on the confidence threshold; verified by `pytest tests/test_guard.py::test_low_confidence_rejected_even_if_similar` → PASSED
- [x] Images processed through a batch background job with retries
  - Proof: `POST /images/batch-process` (run against the full 50-image corpus) →
```json
    { "total": 50, "done": 49, "failed": 1, "low_confidence": 0 }
```
    One image failed vision classification rather than being silently guessed — its `processing_status` is `"failed"` with `processing_error` populated (see `app/batch.py::process_one_image`), satisfying "never trust invalid model output" at scale, not just in the earlier 5-image demo.
- [x] Vision and embedding costs tracked per call
  - Proof: `GET /images/costs/summary` →
```json
    { "total_calls": 109, "vision_calls": 60, "embedding_calls": 49, "failed_calls": 11, "total_estimated_cost_usd": 0 }
```
    (call counts include retries/fallback-model attempts and calls made while re-running the batch job during development — every one of the 109 is still individually attributed in `CostLog`, not just the successful ones; cost is $0 since Gemini's free tier was used throughout)

## Matching System

- [x] Image and post embeddings stored; posts return ranked image suggestions
  - Proof: `python scripts/run_eval.py` against the live server returned ranked, guard-evaluated results for every eval post — e.g. the rose post's top accepted suggestion was `rose_05.jpg`, the peony post's was `peony_05.jpg`, each drawn from embeddings stored on 49 processed images (see full run below).
- [x] Semantic matching works for equivalent concepts
  - Proof: `python scripts/run_eval.py` →

  [OK] 'The romance of the classic red rose' -> top1=rose_05.jpg expected_category=rose
[OK] 'Why peonies are a spring garden favorite' -> top1=peony_05.jpg expected_category=peony
[OK] 'Sunflowers and how they track the sun' -> top1=sunflower_03.jpg expected_category=sunflower
[OK] 'Growing tulips from bulbs this fall' -> top1=tulip_07.jpg expected_category=tulip
[OK] 'The humble daisy in cottage gardens' -> top1=daisy_04.jpg expected_category=daisy
[OK] 'Five budgeting tips for freelancers' -> top1=None expected_category=None

Top-1 precision: 100% (6/6)

Ground truth is checked at category level (e.g. any of the 10 rose images is a valid top-1 pick, not one fixed filename) — see `scripts/run_eval.py`.

## Safety Layer

- [x] Mismatch guard rejects incorrect recommendations
  - Proof: `pytest tests/test_matching.py::test_rose_ranks_first_and_peony_is_rejected -v` → PASSED
- [x] Rejections include a human-readable explanation
  - Proof: live `guard_reason`: `"Category/subject mismatch: post does not mention 'purple peony' or category 'flower', despite similarity 0.77."`
- [x] "No confident match" answers with reasons when nothing clears the bar
  - Proof: `pytest tests/test_matching.py::test_no_confident_match_when_nothing_relevant -v` → PASSED. Also confirmed live above: the "Five budgeting tips for freelancers" eval post (no matching image in the corpus) returned `top1=None`, correctly matching `expected_category=None`.

## Backend

- [x] DB models for images, tags, embeddings, posts, suggestions, approvals — with indexes
  - Proof: `app/models.py` — Image, Post, Suggestion, CostLog tables with `Index("ix_suggestions_post_rank", "post_id", "rank")`
- [x] API endpoints validated; review workflow exists
  - Proof: `POST /review/1` with `{"approve": true}` → `{ "suggestion_id": 1, "review_status": "approved" }`
- [x] Automated tests cover schema validation, mismatch rejection, matching accuracy
  - Proof: `pytest -v` → `10 passed, 10 warnings in 2.88s`

## Quality & Documentation

- [x] Labeled eval dataset measures top-1 precision; number is in README
  - Proof: `Top-1 precision: 100% (6/6)` — in README.md, measured against the full 50-image corpus
- [x] README with architecture explanation + submission-pack files present
  - Proof: README.md, capstone.yaml, BUILDLOG.md, EVIDENCE.md, .env.example all in repo root