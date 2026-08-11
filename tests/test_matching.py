"""
Exercises rank_images_for_post end-to-end against an in-memory DB, using
hand-crafted embedding vectors instead of live Gemini calls — this is the
"rose ranks first, peony gets rejected" gate (the flower-domain equivalent
of the brief's fox/wolf scenario), runnable offline and deterministically.
"""
from app.models import Image, Post
from app.matching import rank_images_for_post


def _seed_images(db):
    rose = Image(
        filename="rose.jpg", path="data/corpus/rose.jpg",
        subject="red rose", category="flower", attributes=["red petals", "romantic"],
        caption="A red rose in bloom", confidence=0.95,
        processing_status="done",
        embedding=[1.0, 0.0, 0.0],
    )
    peony = Image(
        filename="peony.jpg", path="data/corpus/peony.jpg",
        subject="pink peony", category="flower", attributes=["pink petals", "ruffled"],
        caption="A pink peony in bloom", confidence=0.9,
        processing_status="done",
        embedding=[0.9, 0.1, 0.0],  # deliberately close in vector space to the rose
    )
    sunflower = Image(
        filename="sunflower.jpg", path="data/corpus/sunflower.jpg",
        subject="sunflower", category="flower", attributes=["yellow petals", "tall"],
        caption="A sunflower in a field", confidence=0.9,
        processing_status="done",
        embedding=[0.0, 0.0, 1.0],
    )
    db.add_all([rose, peony, sunflower])
    db.commit()


def test_rose_ranks_first_and_peony_is_rejected(db_session):
    _seed_images(db_session)

    post = Post(
        title="The romance of the classic red rose",
        body="Roses have long symbolized love and passion in gardens worldwide.",
        embedding=[1.0, 0.0, 0.0],  # matches rose exactly
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)

    suggestions = rank_images_for_post(db_session, post, top_k=3)
    suggestions_by_rank = sorted(suggestions, key=lambda s: s.rank)

    # Rose should be rank 1 and pass the guard.
    top = suggestions_by_rank[0]
    assert top.image.subject == "red rose"
    assert top.guard_passed is True

    # The peony candidate — despite being vector-close — must be refused by
    # the guard because its subject/category never appears in the rose post.
    peony_suggestion = next(s for s in suggestions if s.image.subject == "pink peony")
    assert peony_suggestion.guard_passed is False
    assert "mismatch" in peony_suggestion.guard_reason.lower() or "peony" in peony_suggestion.guard_reason.lower()


def test_no_confident_match_when_nothing_relevant(db_session):
    rose = Image(
        filename="rose.jpg", path="x", subject="red rose", category="flower",
        attributes=[], caption="rose", confidence=0.9,
        processing_status="done", embedding=[0.0, 1.0, 0.0],
    )
    db_session.add(rose)
    db_session.commit()

    post = Post(
        title="A guide to sourdough bread baking",
        body="Baking bread requires patience and the right hydration ratio.",
        embedding=[1.0, 0.0, 0.0],  # orthogonal to the rose image
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)

    suggestions = rank_images_for_post(db_session, post, top_k=3)
    assert all(s.guard_passed is False for s in suggestions)
