# Evidence

One proof per Definition-of-Done checkbox (§ 6 of the brief).

## AI Processing

- [x] Vision model produces structured output validated against a schema
  - Proof: `pytest tests/test_schema_validation.py -v` → all 4 tests PASSED
- [x] Low-confidence classifications are flagged instead of accepted
  - Proof: `app/vision.py` sets `low_confidence_flag` based on the confidence threshold; verified by `pytest tests/test_guard.py::test_low_confidence_rejected_even_if_similar` → PASSED
- [x] Images processed through a batch background job with retries
  - Proof: `POST /images/batch-process` →
```json
    { "total": 5, "done": 5, "failed": 0, "low_confidence": 0 }
```
- [x] Vision and embedding costs tracked per call
  - Proof: `GET /images/costs/summary` →
```json
    { "total_calls": 20, "vision_calls": 15, "embedding_calls": 5, "failed_calls": 10, "total_estimated_cost_usd": 0 }
```
    (failed_calls reflects earlier debugging — invalid key, retired model — before fixes were applied; cost is $0 since Gemini's free tier was used throughout)

## Matching System

- [x] Image and post embeddings stored; posts return ranked image suggestions
  - Proof: `GET /posts/3/images` returned rose_01.jpg at rank 1 (similarity 0.824), tulip_01.jpg at rank 2, with peony/sunflower/daisy correctly rejected
- [x] Semantic matching works for equivalent concepts
  - Proof: `python scripts/run_eval.py` → `Top-1 precision: 100% (3/3)`

## Safety Layer

- [x] Mismatch guard rejects incorrect recommendations
  - Proof: `pytest tests/test_matching.py::test_rose_ranks_first_and_peony_is_rejected -v` → PASSED
- [x] Rejections include a human-readable explanation
  - Proof: live `guard_reason`: `"Category/subject mismatch: post does not mention 'purple peony' or category 'flower', despite similarity 0.77."`
- [x] "No confident match" answers with reasons when nothing clears the bar
  - Proof: `pytest tests/test_matching.py::test_no_confident_match_when_nothing_relevant -v` → PASSED

## Backend

- [x] DB models for images, tags, embeddings, posts, suggestions, approvals — with indexes
  - Proof: `app/models.py` — Image, Post, Suggestion, CostLog tables with `Index("ix_suggestions_post_rank", "post_id", "rank")`
- [x] API endpoints validated; review workflow exists
  - Proof: `POST /review/1` with `{"approve": true}` → `{ "suggestion_id": 1, "review_status": "approved" }`
- [x] Automated tests cover schema validation, mismatch rejection, matching accuracy
  - Proof: `pytest -v` → `10 passed, 10 warnings in 2.88s`

## Quality & Documentation

- [x] Labeled eval dataset measures top-1 precision; number is in README
  - Proof: `Top-1 precision: 100% (3/3)` — in README.md
- [x] README with architecture explanation + submission-pack files present
  - Proof: README.md, capstone.yaml, BUILDLOG.md, .env.example all in repo root