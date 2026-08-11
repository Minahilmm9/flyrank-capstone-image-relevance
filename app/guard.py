"""
The mismatch guard — the production-critical part of the whole system.

Combines three independent signals so a single weak one can't push a bad
pairing through:
  1. Semantic similarity  — is the vector distance close enough?
  2. Confidence            — did the vision model itself trust its own tags?
  3. Subject / category overlap — a crude but effective sanity check that
     catches the classic "similar vibe, wrong subject" failure (fox post,
     wolf image; rose post, peony image) that pure cosine similarity alone
     will happily pass.

Deliberately checks only subject + category words against the post text —
NOT attribute words. Attributes ("forest", "close-up", "blooming") are
often shared across genuinely different subjects and produce false
matches if included (a wolf tagged "forest" will falsely pass a fox post
about forests). Subject/category words are far more specific. Common
stopwords are also filtered out so incidental shared words like "and" or
"the" can't trigger a false match.

Every decision returns a human-readable reason — accepted or rejected —
because "knowing when the best candidate is still wrong, and explaining
why, is what separates production AI from demos."
"""
from dataclasses import dataclass

from app.config import settings

_STOPWORDS = {
    "and", "the", "with", "from", "into", "this", "that", "have", "has",
    "for", "are", "was", "were", "been", "its", "their", "your", "our",
    "you", "but", "not", "all", "can", "her", "him", "his", "she", "who",
    "how", "why", "when", "what", "which", "these", "those", "than",
}


def _singularize(word: str) -> str:
    """Light plural stripping so 'peonies'/'peony' and 'sunflowers'/'sunflower'
    count as the same word — without this, exact-string matching misses
    almost every real post/caption pairing, since posts are written in
    plural ("Roses have...") while vision tags are usually singular."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("es") and len(word) > 3:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


@dataclass
class GuardResult:
    passed: bool
    reason: str


def _words(text: str) -> set[str]:
    raw = {_singularize(w.strip(".,;:!?").lower()) for w in text.split() if len(w) > 2}
    return raw - _STOPWORDS


def _core_noun(phrase: str) -> str:
    """The last non-stopword token of a subject phrase — English noun
    phrases like 'gray wolf' or 'pink and white tulip' put the actual
    subject last. Matching on this instead of every word in the phrase
    avoids false positives from color/descriptor words that happen to
    also appear in an unrelated post (e.g. a post about peonies mentioning
    'soft pinks and whites' falsely matching a 'pink and white tulip')."""
    tokens = [_singularize(w.strip(".,;:!?").lower()) for w in phrase.split() if len(w) > 2]
    tokens = [w for w in tokens if w not in _STOPWORDS]
    return tokens[-1] if tokens else ""


def evaluate_guard(
    *,
    post_text: str,
    image_subject: str,
    image_category: str,
    image_attributes: list[str],
    similarity: float,
    confidence: float,
) -> GuardResult:
    sim_threshold = settings.mismatch_similarity_threshold
    conf_threshold = settings.mismatch_confidence_threshold

    # 1. Confidence gate — never trust a low-confidence vision result outright.
    if confidence < conf_threshold:
        return GuardResult(
            passed=False,
            reason=(
                f"Low vision confidence ({confidence:.2f} < {conf_threshold:.2f}) "
                f"for subject '{image_subject}' — flagged instead of guessed."
            ),
        )

    # 2. Similarity gate — the embeddings say this isn't close enough.
    if similarity < sim_threshold:
        return GuardResult(
            passed=False,
            reason=(
                f"Similarity below threshold ({similarity:.2f} < {sim_threshold:.2f}); "
                f"detected subject '{image_subject}' does not match article topic."
            ),
        )

    # 3. Subject/category sanity check — catches "close vector, wrong entity"
    # (e.g. wolf image scoring reasonably on a fox post because both are
    # forest animals). Matches on the subject's core noun, not every word
    # in the subject phrase — descriptor words like colors are too generic
    # and cause false positives (see _core_noun docstring). Attributes are
    # excluded entirely for the same reason.
    post_words = _words(post_text)
    subject_core = _core_noun(image_subject)
    category_words = _words(image_category)

    subject_mentioned = subject_core in post_words
    category_mentioned = bool(category_words & post_words)

    if not (subject_mentioned or category_mentioned):
        return GuardResult(
            passed=False,
            reason=(
                f"Category/subject mismatch: post does not mention '{image_subject}' "
                f"or category '{image_category}', despite similarity {similarity:.2f}."
            ),
        )

    return GuardResult(
        passed=True,
        reason=(
            f"Accepted: subject '{image_subject}' matches post context "
            f"(similarity {similarity:.2f}, confidence {confidence:.2f})."
        ),
    )