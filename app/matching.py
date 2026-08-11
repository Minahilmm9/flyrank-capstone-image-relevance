"""
Ties embeddings + guard together: given a post, rank all processed images
by similarity, run each candidate through the mismatch guard, and persist
every decision (accepted or rejected) as a Suggestion row.
"""
from sqlalchemy.orm import Session

from app.models import Image, Post, Suggestion
from app.embeddings import cosine_similarity
from app.guard import evaluate_guard


def rank_images_for_post(db: Session, post: Post, top_k: int = 5) -> list[Suggestion]:
    if post.embedding is None:
        raise ValueError("Post has no embedding yet")

    candidates = (
        db.query(Image)
        .filter(Image.processing_status == "done", Image.embedding.isnot(None))
        .all()
    )

    scored = []
    for img in candidates:
        sim = cosine_similarity(post.embedding, img.embedding)
        scored.append((sim, img))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    # Clear old suggestions for this post so re-ranking doesn't accumulate stale rows.
    db.query(Suggestion).filter(Suggestion.post_id == post.id).delete()

    suggestions = []
    for rank, (sim, img) in enumerate(scored[:top_k], start=1):
        guard_result = evaluate_guard(
            post_text=f"{post.title} {post.body}",
            image_subject=img.subject or "",
            image_category=img.category or "",
            image_attributes=img.attributes or [],
            similarity=sim,
            confidence=img.confidence or 0.0,
        )
        suggestion = Suggestion(
            post_id=post.id,
            image_id=img.id,
            similarity=sim,
            rank=rank,
            guard_passed=guard_result.passed,
            guard_reason=guard_result.reason,
        )
        db.add(suggestion)
        suggestions.append(suggestion)

    db.commit()
    for s in suggestions:
        db.refresh(s)
    return suggestions
