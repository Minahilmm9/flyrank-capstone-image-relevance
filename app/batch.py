"""
Batch job: process every image in data/corpus through the vision pipeline,
off the request path. Modeled on FlyRank's batch-classification pattern —
per-item try/except so one bad image never kills the run, progress is
logged as it goes, and every call's cost is attributed in CostLog.
"""
import logging
import os

from sqlalchemy.orm import Session

from app.models import Image, CostLog
from app.vision import classify_image, estimate_vision_cost
from app.embeddings import embed_text
from app.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def discover_corpus(corpus_dir: str) -> list[str]:
    if not os.path.isdir(corpus_dir):
        return []
    return sorted(
        f for f in os.listdir(corpus_dir)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXT
    )


def _get_or_create_image(db: Session, filename: str, path: str) -> Image:
    img = db.query(Image).filter(Image.filename == filename).first()
    if img is None:
        img = Image(filename=filename, path=path, processing_status="pending")
        db.add(img)
        db.commit()
        db.refresh(img)
    return img


def process_one_image(db: Session, image: Image) -> Image:
    """Runs vision classification + embedding for a single image row."""
    validated, usage, error = classify_image(image.path)

    db.add(CostLog(
        call_type="vision",
        model=settings.gemini_vision_model,
        related_image_id=image.id,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        estimated_cost_usd=estimate_vision_cost(usage),
        success=validated is not None,
        error=error,
    ))

    if validated is None:
        image.processing_status = "failed"
        image.processing_error = error
        db.commit()
        logger.warning("Image %s failed vision classification: %s", image.filename, error)
        return image

    image.subject = validated.subject
    image.category = validated.category
    image.attributes = validated.attributes
    image.caption = validated.caption
    image.confidence = validated.confidence
    image.low_confidence_flag = validated.confidence < settings.mismatch_confidence_threshold
    image.processing_status = "done"
    image.processing_error = None

    vector = embed_text(validated.caption)
    db.add(CostLog(
        call_type="embedding",
        model=settings.gemini_embedding_model,
        related_image_id=image.id,
        success=vector is not None,
        error=None if vector else "embedding call failed",
    ))
    if vector is not None:
        image.embedding = vector

    db.commit()
    logger.info(
        "Processed %s -> subject=%s category=%s confidence=%.2f%s",
        image.filename, image.subject, image.category, image.confidence,
        " [LOW CONFIDENCE]" if image.low_confidence_flag else "",
    )
    return image


def run_batch(db: Session, corpus_dir: str = "data/corpus") -> dict:
    """
    Processes every not-yet-done image in the corpus directory.
    Returns a summary dict — this is what the batch endpoint returns and
    what EVIDENCE.md proofs can paste.
    """
    filenames = discover_corpus(corpus_dir)
    results = {"total": len(filenames), "done": 0, "failed": 0, "low_confidence": 0}

    for filename in filenames:
        path = os.path.join(corpus_dir, filename)
        image = _get_or_create_image(db, filename, path)
        if image.processing_status == "done":
            results["done"] += 1
            if image.low_confidence_flag:
                results["low_confidence"] += 1
            continue

        process_one_image(db, image)
        if image.processing_status == "done":
            results["done"] += 1
            if image.low_confidence_flag:
                results["low_confidence"] += 1
        else:
            results["failed"] += 1

    return results
