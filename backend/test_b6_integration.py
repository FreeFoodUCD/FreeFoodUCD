"""
B6 Vision LLM Fallback — Integration Test
==========================================
Tests the full pipeline with the real OpenAI API and real image URLs.

Run with:
    cd backend && venv/bin/python test_b6_integration.py

What this tests:
1. That classify_with_vision() makes a real API call and returns the right shape.
2. That extract_event() with ocr_low_yield=True + image_urls routes to vision.
3. That _vision_text from the LLM is injected back, enabling time/location extraction.
4. That hard filters still block even when vision says food=True.
"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(__file__))
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from app.core.config import settings
from app.services.nlp.extractor import EventExtractor
from app.services.nlp.llm_classifier import LLMClassifier, get_llm_classifier

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
passed = failed = 0

def check(description, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"[{PASS}] {description}")
    else:
        failed += 1
        print(f"[{FAIL}] {description}")
        if detail:
            print(f"       {detail}")

# ── Preflight ─────────────────────────────────────────────────────────────────
if not settings.OPENAI_API_KEY:
    print("SKIP: OPENAI_API_KEY not set — cannot run integration test")
    sys.exit(0)

print("=" * 60)
print("B6 Integration Test — using real OpenAI API")
print(f"USE_VISION_FALLBACK = {settings.USE_VISION_FALLBACK}")
print("=" * 60)

llm = LLMClassifier(api_key=settings.OPENAI_API_KEY, redis_url=settings.REDIS_URL)
extractor = EventExtractor()

# ── Test 1: classify_with_vision() return shape ───────────────────────────────
# Use a real, publicly accessible image that contains food announcement text.
# This is a plain text-on-colour test image hosted on httpbin (always up).
# We can't guarantee it says "free food" — so we just check the schema.
print("\n── Test 1: classify_with_vision() returns correct schema ──")

# Use the UCD Arts Society coffee morning image from the Important Posts folder.
# Since we can't serve local files to the API, use a known stable public image
# that looks like a graphic with text. We'll use the OpenAI logo page as a safe
# known-accessible URL and just verify the schema (food will be False — that's fine).
result1 = llm.classify_with_vision(
    image_urls=["https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/512px-ChatGPT_logo.svg.png"],
    caption_text="Join us for an event this week!",
)
check("classify_with_vision returns a dict", isinstance(result1, dict), str(result1))
if isinstance(result1, dict):
    check("  → has 'food' key (bool)", 'food' in result1 and isinstance(result1['food'], bool), str(result1))
    check("  → has 'text' key (str)", 'text' in result1 and isinstance(result1['text'], str), str(result1))
    print(f"       food={result1.get('food')}, text={repr(result1.get('text','')[:80])}")

# ── Test 2: extract_event — vision path fires and accepts ──────────────────────
# Simulate a post where:
#   - Caption has zero food keywords (rule-based rejects)
#   - OCR returned <20 chars (ocr_low_yield=True)
#   - Vision LLM sees "FREE PIZZA Student Centre 1pm Tuesday"
# We provide a real image URL but the important part is the mocked vision response.
print("\n── Test 2: extract_event() routes to vision when ocr_low_yield=True ──")

from unittest.mock import MagicMock
import app.services.nlp.llm_classifier as _llm_mod

VISION_ACCEPT = {
    "food": True,
    "text": "FREE PIZZA Newman Building 1pm Tuesday 10th March",
    "location": "Newman Building",
    "time": "13:00",
}

# Caption has NO food keyword → rule-based classify_event returns False
thin_caption = "Come join us for our weekly meeting this Tuesday."
assert not extractor.classify_event(thin_caption), "Precondition: caption alone should reject"

mock_llm = MagicMock()
mock_llm.classify_with_vision.return_value = VISION_ACCEPT
orig = _llm_mod.get_llm_classifier
_llm_mod.get_llm_classifier = lambda: mock_llm

result2 = extractor.extract_event(
    thin_caption,
    source_type="post",
    image_urls=["https://example.com/fake.jpg"],
    ocr_low_yield=True,
)
_llm_mod.get_llm_classifier = orig

check("extract_event returns dict when vision accepts", result2 is not None, str(result2))
if result2:
    check("  → llm_assisted flag is set (confidence_score < 1.0)", result2.get('confidence_score', 1.0) < 1.0, str(result2.get('confidence_score')))
    check("  → title extracted", bool(result2.get('title')), str(result2.get('title')))
    check("  → location from vision text", result2.get('location') is not None, str(result2.get('location')))
    print(f"       title={result2.get('title')!r}")
    print(f"       location={result2.get('location')!r}")
    print(f"       start_time={result2.get('start_time')!r}")
    print(f"       confidence_score={result2.get('confidence_score')!r}")

# ── Test 3: Vision path skipped when ocr_low_yield=False ──────────────────────
print("\n── Test 3: Vision NOT called when ocr_low_yield=False ──")

mock_llm2 = MagicMock()
mock_llm2.classify_with_vision.return_value = VISION_ACCEPT
_llm_mod.get_llm_classifier = lambda: mock_llm2

result3 = extractor.extract_event(
    thin_caption,
    source_type="post",
    image_urls=["https://example.com/fake.jpg"],
    ocr_low_yield=False,  # <-- normal OCR yield
)
_llm_mod.get_llm_classifier = orig

check("extract_event returns None (no food keyword, no vision path)", result3 is None, str(result3))
check("classify_with_vision was NOT called", not mock_llm2.classify_with_vision.called)

# ── Test 4: Hard filter blocks even when vision says food=True ─────────────────
print("\n── Test 4: Hard filter (paid event) blocks before vision call ──")

mock_llm3 = MagicMock()
mock_llm3.classify_with_vision.return_value = VISION_ACCEPT
_llm_mod.get_llm_classifier = lambda: mock_llm3

paid_caption = "Get your tickets now — €25 per person. Student Centre Friday 7pm."
result4 = extractor.extract_event(
    paid_caption,
    source_type="post",
    image_urls=["https://example.com/fake.jpg"],
    ocr_low_yield=True,
)
_llm_mod.get_llm_classifier = orig

check("Hard filter (paid) rejects before vision LLM", result4 is None, str(result4))
check("classify_with_vision was NOT called for paid event", not mock_llm3.classify_with_vision.called)

# ── Test 5: USE_VISION_FALLBACK=False disables vision path ────────────────────
print("\n── Test 5: USE_VISION_FALLBACK=False disables the path ──")
from unittest.mock import patch

mock_llm4 = MagicMock()
mock_llm4.classify_with_vision.return_value = VISION_ACCEPT
_llm_mod.get_llm_classifier = lambda: mock_llm4

with patch.object(settings, 'USE_VISION_FALLBACK', False):
    result5 = extractor.extract_event(
        thin_caption,
        source_type="post",
        image_urls=["https://example.com/fake.jpg"],
        ocr_low_yield=True,
    )
_llm_mod.get_llm_classifier = orig

check("Vision disabled → returns None", result5 is None, str(result5))
check("classify_with_vision NOT called when flag is False", not mock_llm4.classify_with_vision.called)

# ── Results ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"B6 Integration: {passed}/{passed+failed} passed, {failed} failed")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
