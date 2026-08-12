Build log — AI usage

Honest record of where AI helped, where it was wrong, and what I changed.

Initial scaffold
AI generated the full initial project structure (FastAPI app, models, vision/embeddings/guard modules, tests, docs) using Python + FastAPI and Gemini for vision/embeddings. I switched the image corpus domain from the suggested animals (fox/wolf/dog) to flowers (rose/peony/sunflower/tulip/daisy) — updated corpus_urls.json, eval_set.json, and the matching test to use rose/peony as the confusable pair instead of fox/wolf.

If asked about app/guard.py: the guard combines three checks — confidence threshold, similarity threshold, and a subject/category word match against the post text. All three have to pass for an image to be accepted.

Environment setup — real debugging, not AI-generated
Hit a broken embeddable Python install shadowing the real one on PATH; found and used the correct install (Python312) directly by full path to fix venv creation.

Discovered Google rolled out a new Gemini API key format (AQ. "Auth keys" replacing AIza "Standard keys") mid-2026 — the original google-generativeai library didn't support it reliably. Switched to the newer google-genai SDK.

Discovered gemini-2.0-flash (the model AI originally suggested) had been retired by Google (quota showed limit: 0, not a normal rate-limit message). Switched to gemini-3.1-flash-lite with gemini-2.5-flash-lite as a fallback model, so a future model retirement doesn't silently break the pipeline again.

Mismatch guard — found and fixed 3 real bugs via testing
Bug 1: guard matched on any word overlap including image attributes. A wolf image tagged with attribute "forest" falsely passed a fox post that also mentioned "forest" — caught by pytest (test_wolf_rejected_on_fox_post failed). Fix: dropped attributes from the match check entirely; attributes are too generic to be a reliable signal.

Bug 2: exact-string word matching missed plural/singular pairs — a post about "peonies" didn't match an image tagged "peony". Caught by running the eval script (67% precision, 1 post with no accepted image at all). Fix: added lightweight singularization before comparing words.

Bug 3: after fixing #2, a "pink and white tulip" image got falsely accepted on a peony post because the post's color description ("soft pinks and whites") overlapped with the tulip's subject phrase. Caught by rerunning the eval script (still 67%, wrong image now). Fix: match on the subject's core noun (last word of the phrase) instead of every word in it, since color/descriptor words are unreliable signals.

Final result: pytest 10/10 passing, eval script 100% (3/3) top-1 precision.

What I can explain at demo time
Why the guard checks confidence, similarity, and subject/category separately rather than one combined score: each catches a different failure mode a single threshold would miss (self-reported uncertainty, vector-space closeness, and actual topical relevance are independent signals).

Why attributes are excluded from the subject match: they're too generic (shared across genuinely different subjects) and caused a real false-positive I found and fixed.

Why there's a fallback vision model: a model I was using got retired by Google mid-project with no warning beyond a limit: 0 quota error.

the corpus was expanded from 5 to 50 images via the Unsplash API, and the eval script was fixed to grade by category instead of exact filename (since ~10 images per category means multiple correct answers exist). Be honest that AI helped write these scripts — that's exactly what the brief asks for.