import pytest
from pydantic import ValidationError

from app.schemas import ImageTagSchema


def test_valid_tag_parses():
    tag = ImageTagSchema.model_validate({
        "subject": "red fox",
        "category": "animal",
        "attributes": ["orange fur", "wild", "forest"],
        "caption": "A red fox standing in a forest",
        "confidence": 0.94,
    })
    assert tag.subject == "red fox"
    assert tag.confidence == 0.94


def test_missing_required_field_rejected():
    with pytest.raises(ValidationError):
        ImageTagSchema.model_validate({
            "subject": "red fox",
            "category": "animal",
            # caption missing
            "confidence": 0.9,
        })


def test_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        ImageTagSchema.model_validate({
            "subject": "red fox",
            "category": "animal",
            "caption": "A fox",
            "confidence": 1.5,  # invalid: > 1.0
        })


def test_attributes_are_capped():
    tag = ImageTagSchema.model_validate({
        "subject": "red fox",
        "category": "animal",
        "caption": "A fox",
        "confidence": 0.8,
        "attributes": [f"attr{i}" for i in range(20)],
    })
    assert len(tag.attributes) == 10
