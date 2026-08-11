# AI Image Matching Engine

A service that matches blog posts to the most relevant images from a photo
library — using a vision model for structured tagging, embeddings for
semantic similarity, and a mismatch guard that refuses bad pairings
instead of forcing the "best available" wrong answer.

Corpus domain: flowers (rose, peony, sunflower, tulip, daisy). Rose and
peony are the deliberately confusable pair, used to prove the guard
catches a same-category-but-wrong-subject mismatch.

## Architecture
Images ─(batch job)─► Vision Model ─► {tags, caption, confidence} ─► image_metadata
└─► embed(caption) ────────► image_vectors

Posts ──────────────► embed(post text) ─────────────────────────────► post_vectors

GET /posts/:id/images
└─► Similarity Ranking (image_vectors × post_vector)
└─► Mismatch Guard (tags + threshold + confidence)
├─► Suggested image (ranked, explained)
└─► "No good match" + explanation
└─► Review API: approve / reject

## Setup

```bash
git clone <this-repo>
cd flyrank-capstone-image-relevance
cp .env.example .env
# edit .env and set GEMINI_API_KEY (free key: https://aistudio.google.com/apikey)

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_corpus.py
uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

## Tests

```bash
pytest
```

All 10 tests pass, offline and deterministic.

## Evaluation

```bash
python scripts/run_eval.py
```

**Top-1 precision: 100% (3/3)**

## Limitations

- Embeddings stored as plain JSON arrays in SQLite — fine at ~50 images.
- The guard's subject/category check is a word-match heuristic, not a learned classifier.
- No frontend; review workflow is API-only.
- Batch job runs synchronously in-request; production would use a task queue.