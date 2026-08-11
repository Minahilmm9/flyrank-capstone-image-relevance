import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Suggestion
from app.schemas import ReviewDecision

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/pending")
def list_pending(db: Session = Depends(get_db)):
    rows = (
        db.query(Suggestion)
        .filter(Suggestion.guard_passed == True, Suggestion.review_status == "pending")  # noqa: E712
        .all()
    )
    return [
        {
            "suggestion_id": s.id,
            "post_id": s.post_id,
            "image_id": s.image_id,
            "filename": s.image.filename,
            "similarity": s.similarity,
            "guard_reason": s.guard_reason,
        }
        for s in rows
    ]


@router.post("/{suggestion_id}")
def review_suggestion(suggestion_id: int, decision: ReviewDecision, db: Session = Depends(get_db)):
    """Approve or reject a suggested pairing. See § 6 Review API."""
    s = db.query(Suggestion).get(suggestion_id)
    if s is None:
        raise HTTPException(404, "Suggestion not found")

    s.review_status = "approved" if decision.approve else "rejected"
    s.reviewed_at = dt.datetime.utcnow()
    db.commit()
    return {"suggestion_id": s.id, "review_status": s.review_status}


@router.get("/{suggestion_id}/why")
def why_suggestion(suggestion_id: int, db: Session = Depends(get_db)):
    """Inspect why an image was selected or refused for a post."""
    s = db.query(Suggestion).get(suggestion_id)
    if s is None:
        raise HTTPException(404, "Suggestion not found")
    return {
        "post_id": s.post_id,
        "image_id": s.image_id,
        "filename": s.image.filename,
        "rank": s.rank,
        "similarity": s.similarity,
        "guard_passed": s.guard_passed,
        "guard_reason": s.guard_reason,
        "review_status": s.review_status,
    }
