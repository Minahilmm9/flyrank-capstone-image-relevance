"""
Downloads the ~50-image corpus from data/corpus_urls.json into data/corpus/.
Keeps the repo small (images aren't committed) while still letting an
evaluator reproduce your exact corpus with one command.

Usage:
    python scripts/download_corpus.py
"""
import json
import os
import sys
import urllib.request

CORPUS_URLS_FILE = os.path.join("data", "corpus_urls.json")
CORPUS_DIR = os.path.join("data", "corpus")


def main():
    if not os.path.exists(CORPUS_URLS_FILE):
        print(f"Missing {CORPUS_URLS_FILE} — add {{filename: url}} entries first.")
        sys.exit(1)

    with open(CORPUS_URLS_FILE) as f:
        entries = json.load(f)

    os.makedirs(CORPUS_DIR, exist_ok=True)
    for filename, url in entries.items():
        dest = os.path.join(CORPUS_DIR, filename)
        if os.path.exists(dest):
            print(f"skip (exists): {filename}")
            continue
        print(f"downloading: {filename} <- {url}")
        try:
            urllib.request.urlretrieve(url, dest)
        except Exception as exc:
            print(f"  FAILED: {exc}")

    print("Done.")


if __name__ == "__main__":
    main()
