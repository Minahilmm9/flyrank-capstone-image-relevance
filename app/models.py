"""
Database schema.

Images and Posts each get an embedding (stored as JSON float arrays — fine
at ~50 images; swap to pgvector's native vector type later without touching
anything above this layer). Suggestions record every ranking decision the
guard made, including rejections, so the review API can show *why*.
"""
import datetime as dt

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text, Index
)
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return dt.datetime.utcnow()


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False, unique=True, index=True)
    path = Column(String, nullable=False)

    # Vision output — validated against ImageTagSchema before being stored.
    subject = Column(String, nullable=True)
    category = Column(String, nullable=True, index=True)
    attributes = Column(JSON, nullable=True)  # list[str]
    caption = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    low_confidence_flag = Column(Boolean, default=False)

    embedding = Column(JSON, nullable=True)  # list[float], embedding of `caption`

    processing_status = Column(String, default="pending", index=True)  # pending|done|failed
    processing_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow)

    suggestions = relationship("Suggestion", back_populates="image")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)  # list[float], embedding of title+body
    created_at = Column(DateTime, default=utcnow)

    suggestions = relationship("Suggestion", back_populates="post")


class Suggestion(Base):
    """
    One ranking decision for a (post, image) pair — accepted or rejected.
    This is what the review API and EVIDENCE.md proofs read from: every
    "why was this picked / refused" question is answered by a row here.
    """
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False, index=True)

    similarity = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)  # 1 = best candidate that turn

    guard_passed = Column(Boolean, nullable=False)
    guard_reason = Column(String, nullable=False)  # human-readable explanation either way

    review_status = Column(String, default="pending", index=True)  # pending|approved|rejected
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow)

    post = relationship("Post", back_populates="suggestions")
    image = relationship("Image", back_populates="suggestions")

    __table_args__ = (
        Index("ix_suggestions_post_rank", "post_id", "rank"),
    )


class CostLog(Base):
    """Per-call cost/usage tracking for every vision and embedding call."""
    __tablename__ = "cost_log"

    id = Column(Integer, primary_key=True)
    call_type = Column(String, nullable=False)  # "vision" | "embedding"
    model = Column(String, nullable=False)
    related_image_id = Column(Integer, nullable=True)
    related_post_id = Column(Integer, nullable=True)

    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)

    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow)
