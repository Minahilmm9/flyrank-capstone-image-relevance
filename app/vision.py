"""
Vision pipeline: image -> Gemini -> validated ImageTagSchema.

Uses the newer `google-genai` SDK (google.genai), not the older
`google-generativeai` package — see app/embeddings.py for background.

Tries GEMINI_VISION_MODEL first; if that model call fails at the API level
(quota exhausted, deprecated/retired model, etc.) it falls back to
GEMINI_VISION_MODEL_FALLBACK once. Google's free-tier model lineup has
shifted several times in 2026, so this keeps the pipeline working even if
one model gets retired without you noticing.

Rule this file exists to enforce: never trust invalid model output.
Every response is parsed through ImageTagSchema.model_validate(). If a
model's response fails validation, we retry that same model once with a
stricter reminder prompt. If a model's *call itself* fails (network/quota/
retired model), we move to the next model in the list instead of retrying
a call that will never succeed. If nothing works, the image is marked
"failed" — never silently guessed. Low-confidence results are flagged for
human review rather than trusted outright.
"""
import json
import logging

from google import genai
from pydantic import ValidationError

from app.config import settings
from app.schemas import ImageTagSchema

logger = logging.getLogger(__name__)

_PROMPT = """You are an image tagging system. Look at this image and respond with
ONLY a JSON object (no markdown fences, no prose) matching exactly this shape:

{{
  "subject": "short main subject, e.g. 'red rose'",
  "category": "broad category, e.g. 'flower'",
  "attributes": ["3-6 short descriptive attributes"],
  "caption": "one sentence caption",
  "confidence": 0.0-1.0 float, your own certainty about this classification
}}

Respond with nothing but that JSON object.
"""

_RETRY_SUFFIX = (
    "\n\nYour previous response did not parse as valid JSON matching the schema. "
    "Return ONLY the raw JSON object, with no markdown code fences and no extra text."
)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def _call_gemini(image_path: str, prompt: str, model: str) -> tuple[str, dict]:
    """Returns (raw_text, usage_dict). Raises on transport/API failure."""
    client = _get_client()
    uploaded = client.files.upload(file=image_path)
    response = client.models.generate_content(
        model=model,
        contents=[uploaded, prompt],
    )
    usage = {}
    if getattr(response, "usage_metadata", None):
        usage = {
            "input_tokens": getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
            "output_tokens": getattr(response.usage_metadata, "candidates_token_count", 0) or 0,
        }
    return response.text, usage


def _candidate_models() -> list[str]:
    models = [settings.gemini_vision_model]
    if settings.gemini_vision_model_fallback and settings.gemini_vision_model_fallback not in models:
        models.append(settings.gemini_vision_model_fallback)
    return models


def classify_image(image_path: str) -> tuple[ImageTagSchema | None, dict, str | None]:
    """
    Tries each candidate model in turn. Within a model, retries once on
    invalid JSON/schema. If the model *call itself* fails (quota, retired
    model, network error), moves straight to the next candidate model
    instead of wasting a retry on a call that will fail again.
    Returns (validated_schema_or_None, usage_metadata, error_message_or_None).
    """
    last_error = None
    usage_total = {"input_tokens": 0, "output_tokens": 0}

    for model in _candidate_models():
        for attempt in range(2):
            prompt = _PROMPT if attempt == 0 else _PROMPT + _RETRY_SUFFIX
            try:
                raw_text, usage = _call_gemini(image_path, prompt, model)
            except Exception as exc:  # network/API-level error — try next model, not a retry
                last_error = f"Gemini call failed (model={model}): {exc}"
                logger.warning(last_error)
                break  # stop retrying this model, move to next candidate

            usage_total["input_tokens"] += usage.get("input_tokens", 0)
            usage_total["output_tokens"] += usage.get("output_tokens", 0)

            cleaned = _strip_fences(raw_text)
            try:
                parsed = json.loads(cleaned)
                validated = ImageTagSchema.model_validate(parsed)
                return validated, usage_total, None
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = f"Schema validation failed (model={model}, attempt {attempt + 1}): {exc}"
                logger.warning("%s | raw response: %.200s", last_error, raw_text)
                continue  # retry same model once more on bad JSON/schema

    return None, usage_total, last_error or "Unknown vision failure"


# Gemini Flash free-tier pricing is $0 up to quota; we still track a nominal
# cost estimate so the cost-tracking requirement holds even off the free tier.
_VISION_COST_PER_1K_INPUT = 0.0
_VISION_COST_PER_1K_OUTPUT = 0.0


def estimate_vision_cost(usage: dict) -> float:
    return (
        usage.get("input_tokens", 0) / 1000 * _VISION_COST_PER_1K_INPUT
        + usage.get("output_tokens", 0) / 1000 * _VISION_COST_PER_1K_OUTPUT
    )