from app.guard import evaluate_guard


def test_wolf_rejected_on_fox_post():
    """PROBE 3 core scenario: a gray wolf candidate on a red-fox post is refused."""
    result = evaluate_guard(
        post_text="The behavior of red foxes in their natural forest habitat",
        image_subject="gray wolf",
        image_category="animal",
        image_attributes=["gray fur", "forest", "pack"],
        similarity=0.70,  # embeddings alone might think this is close enough
        confidence=0.9,
    )
    assert result.passed is False
    assert "mismatch" in result.reason.lower() or "wolf" in result.reason.lower()


def test_fox_accepted_on_fox_post():
    result = evaluate_guard(
        post_text="The behavior of red foxes in their natural forest habitat",
        image_subject="red fox",
        image_category="animal",
        image_attributes=["orange fur", "wild", "forest"],
        similarity=0.85,
        confidence=0.94,
    )
    assert result.passed is True


def test_low_confidence_rejected_even_if_similar():
    result = evaluate_guard(
        post_text="The behavior of red foxes",
        image_subject="red fox",
        image_category="animal",
        image_attributes=["orange fur"],
        similarity=0.9,
        confidence=0.2,  # vision model itself was unsure
    )
    assert result.passed is False
    assert "confidence" in result.reason.lower()


def test_low_similarity_rejected():
    result = evaluate_guard(
        post_text="A guide to sourdough bread baking",
        image_subject="red fox",
        image_category="animal",
        image_attributes=["orange fur"],
        similarity=0.1,
        confidence=0.9,
    )
    assert result.passed is False
    assert "similarity" in result.reason.lower()
