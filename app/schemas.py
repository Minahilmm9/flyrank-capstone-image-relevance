"""
Pydantic schemas. ImageTagSchema is the contract every Gemini vision
response must satisfy — model_validate_json() either produces one of these
or raises, and vision.py never lets a raise become a silently-accepted guess.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ImageTagSchema(BaseModel):
    subject: str = Field(..., min_length=1, description="Main subject, e.g. 'red fox'")
    category: str = Field(..., min_length=1, description="Broad category, e.g. 'animal'")
    attributes: list[str] = Field(default_factory=list)
    caption: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("attributes")
    @classmethod
    def cap_attributes(cls, v: list[str]) -> list[str]:
        return v[:10]


class ImageOut(BaseModel):
    id: int
    filename: str
    subject: Optional[str]
    category: Optional[str]
    attributes: Optional[list[str]]
    caption: Optional[str]
    confidence: Optional[float]
    low_confidence_flag: bool
    processing_status: str

    model_config = {"from_attributes": True}


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)


class PostOut(BaseModel):
    id: int
    title: str
    body: str

    model_config = {"from_attributes": True}


class SuggestionOut(BaseModel):
    image_id: int
    filename: str
    subject: Optional[str]
    caption: Optional[str]
    similarity: float
    rank: int
    guard_passed: bool
    guard_reason: str
    review_status: str

    model_config = {"from_attributes": True}


class RankedResponse(BaseModel):
    post_id: int
    accepted: list[SuggestionOut]
    rejected: list[SuggestionOut]
    no_confident_match: bool
    explanation: Optional[str] = None


class ReviewDecision(BaseModel):
    approve: bool
