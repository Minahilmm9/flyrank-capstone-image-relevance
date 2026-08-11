"""
Runs the labeled eval set against the live API and reports top-1 precision:
of all posts, the share whose first *accepted* suggestion was the labeled
correct image. This is PROBE 5 — the number this prints belongs in the README.

Usage (with the server already running on localhost:8000):
    python scripts/run_eval.py
"""
import json
import sys

import httpx

BASE_URL = "http://localhost:8000"
EVAL_FILE = "data/eval_set.json"


def main():
    with open(EVAL_FILE) as f:
        eval_set = json.load(f)

    client = httpx.Client(base_url=BASE_URL, timeout=60)
    correct = 0
    total = len(eval_set)

    for case in eval_set:
        resp = client.post("/posts", json={"title": case["title"], "body": case["body"]})
        resp.raise_for_status()
        post_id = resp.json()["id"]

        ranked = client.get(f"/posts/{post_id}/images")
        ranked.raise_for_status()
        data = ranked.json()

        top1 = data["accepted"][0]["filename"] if data["accepted"] else None
        is_correct = top1 == case["correct_image_filename"]
        correct += int(is_correct)

        print(
            f"[{'OK' if is_correct else 'MISS'}] '{case['title']}' "
            f"-> top1={top1} expected={case['correct_image_filename']}"
        )

    precision = correct / total if total else 0.0
    print(f"\nTop-1 precision: {precision:.0%} ({correct}/{total})")

    if precision < 0.5:
        sys.exit(1)


if __name__ == "__main__":
    main()
