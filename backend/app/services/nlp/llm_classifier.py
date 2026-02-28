import hashlib
import json
import logging
from typing import Optional

import redis as redis_lib
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You classify Instagram captions from UCD (University College Dublin) student society accounts. "
    "Reply with JSON only — no extra text. "
    "If the caption announces an upcoming event where free food or drinks will be provided for students, "
    'reply: {"food": true, "location": "<canonical building name or null>", "time": "<HH:MM 24h or null>"}. '
    'If not: {"food": false}. '
    "Known UCD buildings (use these exact names for location, or null if unrecognisable): "
    "Newman Building, Student Centre, Engineering & Materials Science Centre, "
    "O'Brien Centre for Science, James Joyce Library, Sutherland School of Law, "
    "Lochlann Quinn School of Business, Agriculture & Food Science Centre, "
    "Health Sciences Centre, Veterinary Sciences Centre, Computer Science & Informatics Centre, "
    "Daedalus Building, Confucius Institute, Hanna Sheehy-Skeffington Building, "
    "Tierney Building, Roebuck Castle, UCD Village."
)

_CACHE_TTL = 7 * 24 * 3600  # 7 days


class LLMClassifier:
    def __init__(self, api_key: str, redis_url: str):
        self._client = OpenAI(api_key=api_key, timeout=10.0)
        self._redis = redis_lib.from_url(redis_url, decode_responses=False)

    def classify_and_extract(self, normalized_text: str) -> Optional[dict]:
        """
        Single LLM call: food classification + optional location/time hints.
        Returns dict {food: bool, location: str|None, time: str|None}
        or None if LLM is unavailable (circuit break).
        normalized_text: pre-processed (lowercased, emoji-mapped) caption.
        """
        cache_key = f"llm_extract:{hashlib.sha256(normalized_text.encode()).hexdigest()[:16]}"

        # Cache read
        try:
            cached = self._redis.get(cache_key)
            if cached is not None:
                logger.debug("LLM cache hit")
                return json.loads(cached)
        except Exception:
            pass

        # API call
        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": normalized_text[:600]},
                ],
                max_tokens=60,
                temperature=0,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            logger.info(
                f"LLM classified borderline post: food={result.get('food')}, "
                f"location={result.get('location')}, time={result.get('time')}"
            )
        except Exception as exc:
            logger.warning(f"LLM classifier unavailable: {exc}")
            return None  # circuit break — caller will apply rule-based reject

        # Cache write (non-fatal)
        try:
            self._redis.setex(cache_key, _CACHE_TTL, json.dumps(result))
        except Exception:
            pass

        return result


_instance: Optional[LLMClassifier] = None


def get_llm_classifier() -> Optional[LLMClassifier]:
    """Lazy singleton — returns None if OPENAI_API_KEY is not configured."""
    global _instance
    if _instance is None and settings.OPENAI_API_KEY:
        _instance = LLMClassifier(
            api_key=settings.OPENAI_API_KEY,
            redis_url=settings.REDIS_URL,
        )
    return _instance
