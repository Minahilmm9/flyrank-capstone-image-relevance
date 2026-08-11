from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Image, CostLog
from app.schemas import ImageOut
from app.batch import run_batch

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/batch-process")
def batch_process(db: Session = Depends(get_db)):
    """Runs the vision batch job over data/corpus. See PROBE 1 in the brief."""
    summary = run_batch(db)
    return summary


@router.get("", response_model=list[ImageOut])
def list_images(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Image)
    if status:
        query = query.filter(Image.processing_status == status)
    return query.order_by(Image.id).all()


@router.get("/{image_id}", response_model=ImageOut)
def get_image(image_id: int, db: Session = Depends(get_db)):
    img = db.query(Image).get(image_id)
    if img is None:
        raise HTTPException(404, "Image not found")
    return img


@router.get("/costs/summary")
def cost_summary(db: Session = Depends(get_db)):
    """PROBE 6: every vision/embedding call attributed with a cost entry."""
    logs = db.query(CostLog).all()
    return {
        "total_calls": len(logs),
        "vision_calls": sum(1 for l in logs if l.call_type == "vision"),
        "embedding_calls": sum(1 for l in logs if l.call_type == "embedding"),
        "failed_calls": sum(1 for l in logs if not l.success),
        "total_estimated_cost_usd": sum(l.estimated_cost_usd for l in logs),
    }
