from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Post, Suggestion
from app.schemas import PostCreate, PostOut, RankedResponse, SuggestionOut
from app.embeddings import embed_text
from app.matching import rank_images_for_post

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostOut)
def create_post(payload: PostCreate, db: Session = Depends(get_db)):
    vector = embed_text(f"{payload.title} {payload.body}")
    post = Post(title=payload.title, body=payload.body, embedding=vector)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("", response_model=list[PostOut])
def list_posts(db: Session = Depends(get_db)):
    return db.query(Post).order_by(Post.id).all()


def _to_suggestion_out(s: Suggestion) -> SuggestionOut:
    return SuggestionOut(
        image_id=s.image.id,
        filename=s.image.filename,
        subject=s.image.subject,
        caption=s.image.caption,
        similarity=s.similarity,
        rank=s.rank,
        guard_passed=s.guard_passed,
        guard_reason=s.guard_reason,
        review_status=s.review_status,
    )


@router.get("/{post_id}/images", response_model=RankedResponse)
def get_ranked_images(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).get(post_id)
    if post is None:
        raise HTTPException(404, "Post not found")
    if post.embedding is None:
        raise HTTPException(422, "Post has no embedding — was it created before Gemini was configured?")

    suggestions = rank_images_for_post(db, post)
    accepted = [_to_suggestion_out(s) for s in suggestions if s.guard_passed]
    rejected = [_to_suggestion_out(s) for s in suggestions if not s.guard_passed]

    no_confident_match = len(accepted) == 0
    explanation = None
    if no_confident_match:
        explanation = (
            "No confident match found. " + (rejected[0].guard_reason if rejected else
            "No processed images available to compare against.")
        )

    return RankedResponse(
        post_id=post_id,
        accepted=accepted,
        rejected=rejected,
        no_confident_match=no_confident_match,
        explanation=explanation,
    )
