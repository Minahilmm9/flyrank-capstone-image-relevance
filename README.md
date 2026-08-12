# AI Image Matching Engine

A service that matches blog posts to the most relevant images from a photo
library — using a vision model for structured tagging, embeddings for
semantic similarity, and a mismatch guard that refuses bad pairings
instead of forcing the "best available" wrong answer.

Corpus domain: flowers (rose, peony, sunflower, tulip, daisy), ~50 images
across the 5 categories. Rose and peony are the deliberately confusable
pair, used to prove the guard catches a same-category-but-wrong-subject
mismatch.

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

# data/corpus_urls.json already has ~50 images committed. To regenerate it
# from scratch (or add more), get a free Unsplash Demo key (no card:
# https://unsplash.com/developers) and run:
#   export UNSPLASH_ACCESS_KEY=your_key
#   python scripts/expand_corpus.py
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

**Top-1 precision: 100% (7/7)** — measured against the full 50-image
corpus. The eval set covers one post per category, a "no confident match"
case (an unrelated post the guard correctly rejects), and one semantic-
matching case: a post describing a daisy ("low-growing rosettes,"
"Bellis perennis") without ever using the word "daisy" — the system still
correctly matched it to a daisy image, proving matching works on meaning,
not keyword overlap. Ground truth is checked at the category level: with
~10 images per category, any correctly-tagged image in the right category
is a valid top-1 pick, so `run_eval.py` compares the predicted category
rather than one arbitrary filename.

## Limitations

- Embeddings stored as plain JSON arrays in SQLite — fine at ~50 images.
- The guard's subject/category check is a word-match heuristic, not a learned classifier.
- No frontend; review workflow is API-only.
- Batch job runs synchronously in-request; production would use a task queue.
- 1 of 50 images failed vision classification during the batch run and was flagged rather than guessed (see EVIDENCE.md).