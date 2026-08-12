"""
Grows data/corpus_urls.json from the original 5 "hero" images (one per
category — these are what data/eval_set.json points at, and what the
rose/peony guard demo is built around) up to the ~50-image corpus size
described in the capstone brief (§7 "Realistic scope").

Uses the free Unsplash API (https://unsplash.com/developers — register an
app, get a "Demo" Access Key, no credit card, 50 requests/hour which is
plenty for a one-time corpus build). This is a separate, one-time script
rather than something download_corpus.py does on every run, so the corpus
stays reproducible for an evaluator: run this once yourself, commit the
resulting corpus_urls.json, and evaluators only ever need to run
download_corpus.py (no Unsplash key required on their end).

Usage:
    export UNSPLASH_ACCESS_KEY=your_free_demo_key
    python scripts/expand_corpus.py
    python scripts/download_corpus.py   # downloads the newly added URLs too
"""
import json
import os
import sys
import urllib.parse
import urllib.request

CORPUS_URLS_FILE = os.path.join("data", "corpus_urls.json")
PER_CATEGORY = 10  # 5 categories x 10 = 50 images total

# Search query per category. Filenames stay <category>_NN.jpg so the
# existing hero files (rose_01.jpg etc, used by eval_set.json) are untouched.
CATEGORIES = {
    "rose": "red rose flower",
    "peony": "peony flower",
    "sunflower": "sunflower",
    "tulip": "tulip flower",
    "daisy": "daisy flower",
}


def search_unsplash(query: str, count: int, access_key: str) -> list[str]:
    params = urllib.parse.urlencode({
        "query": query,
        "per_page": count,
        "orientation": "landscape",
        "content_filter": "high",
    })
    url = f"https://api.unsplash.com/search/photos?{params}"
    req = urllib.request.Request(url, headers={"Authorization": f"Client-ID {access_key}"})
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    return [item["urls"]["regular"] for item in data.get("results", [])]


def main():
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not access_key:
        print("Set UNSPLASH_ACCESS_KEY first (free key, no card: https://unsplash.com/developers).")
        sys.exit(1)

    if not os.path.exists(CORPUS_URLS_FILE):
        print(f"Missing {CORPUS_URLS_FILE}.")
        sys.exit(1)

    with open(CORPUS_URLS_FILE) as f:
        entries = json.load(f)

    existing_urls = set(entries.values())

    for category, query in CATEGORIES.items():
        existing_files = [k for k in entries if k.startswith(category + "_")]
        needed = PER_CATEGORY - len(existing_files)
        if needed <= 0:
            print(f"skip {category}: already have {len(existing_files)}")
            continue

        print(f"fetching {needed} more '{category}' images ({query!r})...")
        try:
            candidates = search_unsplash(query, needed + 3, access_key)  # buffer for dedupe
        except Exception as exc:
            print(f"  FAILED to query Unsplash for {category}: {exc}")
            continue

        next_n = len(existing_files) + 1
        added = 0
        for url in candidates:
            if added >= needed:
                break
            if url in existing_urls:
                continue
            filename = f"{category}_{next_n:02d}.jpg"
            while filename in entries:
                next_n += 1
                filename = f"{category}_{next_n:02d}.jpg"
            entries[filename] = url
            existing_urls.add(url)
            next_n += 1
            added += 1
        print(f"  added {added}")

    with open(CORPUS_URLS_FILE, "w") as f:
        json.dump(entries, f, indent=2)
        f.write("\n")

    print(f"Done. corpus_urls.json now has {len(entries)} images.")


if __name__ == "__main__":
    main()