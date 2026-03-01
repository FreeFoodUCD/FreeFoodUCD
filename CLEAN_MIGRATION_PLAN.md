# Phase E: Clean Gemini Migration Plan

> Status: **PENDING REVIEW**  
> Approach: Dual-source cross-check (Gemini primary classifier + regex validators)  
> Goal: Replace the 1,500-line hybrid NLP pipeline with a clean ~400-line Gemini-first architecture

---

## Why This Migration

The current Phase D architecture is a hybrid where:
- Rule-based `classify_event()` runs first as the primary classifier
- Gemini is called as a *fallback* when rules fail
- Gemini's `time`/`date`/`location` outputs are only used when regex finds nothing
- Two separate code paths exist with duplicated logic

This is messy. Since Gemini is now called on every post anyway, the rule-based classifier is redundant overhead. The clean architecture makes Gemini the **primary** classifier and uses regex only as a **cross-check validator** for time/date accuracy.

---

## Architecture: Before vs After

### Before (Phase D — hybrid)
```
Post → _preprocess_text() → classify_event() (11-gate regex)
                                    │
                              True  │  False
                                    │
                              extract_event()   _try_llm_fallback()
                                    │                   │
                              TimeParser          Gemini/OpenAI
                              DateParser               │
                              _extract_location()  food=true?
                                    │                   │
                              LLM hints used       inject hints
                              as fallback only     into extract_event()
```

### After (Phase E — Gemini-first)
```
Post → Hard filters (5 fast checks) → Gemini(caption, images, today=now)
                                              │
                                        food=false → REJECT
                                        food=true  ↓
                                       TimeParser(text)   ← regex validator
                                       DateParser(text)   ← regex validator
                                              │
                                       _reconcile_datetime(regex, gemini)
                                              │
                                       _extract_location(gemini.location)
                                              │
                                       Past-date validation + TBC skip
                                              │
                                       Store event
```

---

## What Changes

### Files Modified

| File | Change | Lines before → after |
|------|--------|----------------------|
| [`backend/app/services/nlp/extractor.py`](backend/app/services/nlp/extractor.py) | Full rewrite | ~1,500 → ~400 |
| [`backend/app/services/nlp/llm_classifier.py`](backend/app/services/nlp/llm_classifier.py) | Remove `LLMClassifier` + OpenAI prompts | ~444 → ~250 |
| [`backend/app/core/config.py`](backend/app/core/config.py) | Remove deprecated flags | ~98 → ~85 |
| [`backend/tests/nlp/test_classifier.py`](backend/tests/nlp/test_classifier.py) | Full rewrite | ~1,080 → ~350 |

### Files Deleted

| File | Reason |
|------|--------|
| [`backend/app/services/nlp/date_parser.py`](backend/app/services/nlp/date_parser.py) | Gemini resolves dates; DateParser demoted to thin wrapper |
| [`backend/app/services/nlp/time_parser.py`](backend/app/services/nlp/time_parser.py) | Gemini returns HH:MM; TimeParser demoted to thin wrapper |

> **Note**: DateParser and TimeParser are not fully deleted — they are kept as thin validators (~50 lines each) that extract time/date from text for cross-checking. The full 400-line implementations are replaced with minimal versions.

---

## E1: Updated Gemini Prompt

The prompt gains two new elements:

1. **Today's date injection** (dynamic, per-call):
```
Today is {weekday} {day} {month} {year}. The post was published on {post_date}.
```

2. **Updated output format** — `start_datetime` replaces `time` + `date_hint`:
```json
{
  "food": true,
  "title": "<short event name max 60 chars>",
  "start_datetime": "<ISO 8601 datetime e.g. 2026-03-06T18:00:00, or null if no specific date/time>",
  "end_datetime": "<ISO 8601 datetime or null>",
  "location": "<canonical UCD location or null>",
  "image_text": "<key text read from image, or null>",
  "members_only": false
}
```

**Critical prompt instructions added**:
- `"If no specific date is mentioned, return start_datetime: null. Do NOT invent a date."`
- `"'Soon', 'this week', 'coming up' are NOT specific dates — return null."`
- `"If a time is mentioned but no date, return start_datetime: null (date unknown)."`
- `"Use the post publication date as context for resolving 'this Friday', 'next Tuesday', etc."`

**Example added to prompt**:
```
Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "Free pizza this Friday at 6pm in Newman!"
→ {"food": true, "title": "Free Pizza", "start_datetime": "2026-03-06T18:00:00", 
   "end_datetime": null, "location": "Newman Building", "image_text": null, "members_only": false}

Caption: "Join us for free coffee sometime next week!"
→ {"food": true, "title": "Free Coffee", "start_datetime": null, 
   "end_datetime": null, "location": null, "image_text": null, "members_only": false}
```

---

## E2: New `extractor.py` Structure

The new `EventExtractor` class has these methods only:

```python
class EventExtractor:
    def __init__(self):
        self.timezone = pytz.timezone('Europe/Dublin')
        self.building_aliases = self._load_building_aliases()  # kept — ~80 entries
        self.student_centre_rooms = {...}                       # kept
        # Hard-filter keyword lists (kept — fast, high-precision)
        self.other_colleges = [...]
        self.off_campus_venues = [...]
        self.nightlife_keywords = [...]

    # ── Hard filters (kept from Phase D, ~200 lines total) ──────────────────
    def _is_paid_event(self, text) -> bool          # kept as-is
    def _is_nightlife_event(self, text) -> bool     # kept as-is
    def _is_off_campus(self, text) -> bool          # kept as-is
    def _is_other_college(self, text) -> bool       # kept as-is
    def _is_religious_event(self, text) -> bool     # kept as-is
    def _passes_hard_filters(self, text) -> bool    # NEW: combines all 5 above

    # ── Location (kept from Phase D, ~100 lines) ────────────────────────────
    def _extract_location(self, text) -> Optional[dict]   # kept as-is
    def _load_building_aliases(self) -> dict              # kept as-is

    # ── Datetime reconciliation (NEW, ~60 lines) ─────────────────────────────
    def _parse_time_from_text(self, text) -> Optional[dict]   # thin wrapper around TimeParser
    def _parse_date_from_text(self, text, post_ts) -> Optional[datetime]  # thin wrapper around DateParser
    def _reconcile_datetime(self, gemini_dt_str, text, post_ts) -> tuple[Optional[datetime], float]
    # Returns (resolved_datetime, confidence_modifier)

    # ── Main entry point ─────────────────────────────────────────────────────
    def extract_event(self, text, source_type, post_timestamp, image_urls, ocr_low_yield) -> Optional[dict]
```

**Deleted from extractor.py**:
- `classify_event()` — 90 lines
- `_try_llm_fallback()` — 85 lines
- `_has_explicit_food()` — 35 lines
- `_has_weak_food_only()` — 20 lines
- `_food_is_negated()` — 20 lines
- `_is_past_tense_post()` — 40 lines (Gemini handles this)
- `_is_food_activity()` — 25 lines (Gemini handles this)
- `_is_giveaway_contest()` — 20 lines (Gemini handles this)
- `_is_staff_only()` — 15 lines (Gemini handles this)
- `_is_online_event()` — 15 lines (Gemini handles this)
- `_generate_title()` — 40 lines (Gemini returns title directly)
- `_is_members_only()` — 15 lines (Gemini returns members_only directly)
- `_preprocess_text()` — 35 lines (Gemini handles raw text natively)
- `_combine_datetime()` — 20 lines (replaced by ISO parse)
- All strong/weak food keyword lists — 60 lines
- All context modifier lists — 15 lines
- `_FOOD_EMOJI_MAP` — 85 lines (Gemini understands emojis natively)

**Net**: ~700 lines deleted, ~60 new lines added.

---

## E3: `_reconcile_datetime()` Logic

```python
def _reconcile_datetime(
    self,
    gemini_dt_str: Optional[str],   # e.g. "2026-03-06T18:00:00" or null
    text: str,                       # original post text
    post_ts: Optional[datetime],     # when the post was published
) -> tuple[Optional[datetime], float]:
    """
    Cross-check Gemini's datetime against text evidence.
    Returns (resolved_datetime, confidence_modifier).
    """
    now = post_ts or datetime.now(UTC)

    # --- Parse Gemini's datetime ---
    gemini_dt = None
    if gemini_dt_str:
        try:
            gemini_dt = datetime.fromisoformat(gemini_dt_str).replace(tzinfo=UTC)
        except (ValueError, TypeError):
            gemini_dt = None

    # --- Check for date/time evidence in text ---
    has_date_evidence = bool(DATE_EVIDENCE_RE.search(text))
    has_time_evidence = bool(TIME_EVIDENCE_RE.search(text))

    # --- Validate Gemini's datetime ---
    if gemini_dt:
        # Reject if in the past (>1h grace for "happening now")
        if gemini_dt < now - timedelta(hours=1):
            gemini_dt = None
        # Reject if suspiciously far future (>30 days)
        elif gemini_dt > now + timedelta(days=30):
            gemini_dt = None
        # Reject date component if no date evidence in text
        elif not has_date_evidence:
            gemini_dt = None
        # Strip time component if no time evidence in text
        elif not has_time_evidence:
            gemini_dt = gemini_dt.replace(hour=12, minute=0, second=0)  # noon default

    # --- Also run regex parsers as cross-check ---
    regex_time = self._parse_time_from_text(text)
    regex_date = self._parse_date_from_text(text, post_ts)

    # --- Reconcile ---
    if gemini_dt and regex_date:
        # Both found a date — check they agree (within 1 day)
        if abs((gemini_dt.date() - regex_date.date()).days) <= 1:
            # Agreement → high confidence, use Gemini's full datetime
            return gemini_dt, 1.0
        else:
            # Disagreement → trust regex date, use Gemini's time if available
            if regex_time and gemini_dt:
                resolved = regex_date.replace(
                    hour=gemini_dt.hour, minute=gemini_dt.minute
                )
            elif regex_time:
                resolved = regex_date.replace(
                    hour=regex_time['hour'], minute=regex_time['minute']
                )
            else:
                resolved = regex_date
            return resolved, 0.85  # slight penalty for disagreement

    elif gemini_dt:
        # Gemini found date, regex didn't — use Gemini (already validated above)
        return gemini_dt, 0.75

    elif regex_date:
        # Regex found date, Gemini didn't — use regex
        if regex_time:
            resolved = regex_date.replace(
                hour=regex_time['hour'], minute=regex_time['minute']
            )
        else:
            resolved = regex_date
        return resolved, 0.85

    else:
        # Neither found a date
        return None, 0.0
```

**Confidence scoring**:

| Scenario | Modifier |
|----------|----------|
| Gemini + regex agree on date | `1.0` |
| Regex date only (Gemini null/invalid) | `0.85` |
| Gemini date only (regex null) | `0.75` |
| Gemini + regex disagree → use regex | `0.85` |
| Neither found date | `0.0` (event stored without time) |

Final `confidence_score` = base (1.0 if location found, 0.8 if not) × datetime modifier.

---

## E4: `llm_classifier.py` Changes

**Deleted**:
- `LLMClassifier` class (~120 lines)
- `_SYSTEM_PROMPT` (~15 lines)
- `_VISION_SYSTEM_PROMPT` (~25 lines)
- `from openai import OpenAI` import

**Updated**:
- `_GEMINI_SYSTEM_PROMPT` — add today's date injection slot, update output format
- `GeminiClassifier.classify_and_extract()` — accept `today_str` and `post_date_str` parameters, inject into prompt
- `get_llm_classifier()` — simplified, returns `GeminiClassifier` only (no OpenAI fallback)

**Kept**:
- `GeminiClassifier` class (~90 lines)
- Redis caching logic
- `get_llm_classifier()` singleton factory

---

## E5: `config.py` Changes

**Removed flags** (no longer needed):
- `USE_SCORING_PIPELINE: bool = True` — no longer a toggle; Gemini always runs
- `USE_VISION_FALLBACK: bool = True` — Gemini handles vision natively
- `OPENAI_API_KEY: Optional[str] = None` — OpenAI no longer used

**Kept**:
- `GEMINI_API_KEY: Optional[str] = None`
- `USE_GEMINI: bool = False` — kept as a master kill switch (if `False`, no LLM runs at all and events are rejected; emergency rollback)

**New flag**:
- `GEMINI_MAX_FUTURE_DAYS: int = 30` — configurable plausibility window for date validation

---

## E6: New Test Suite

The 134-test suite is replaced with ~30 focused tests in three categories:

### Category 1: Hard filter tests (~10 tests)
Test that paid events, nightlife, off-campus, religious, and other-college posts are rejected before Gemini is called. These are pure unit tests with no mocking needed.

```python
def test_paid_event_rejected_before_gemini():
    extractor = EventExtractor()
    # Gemini should never be called — hard filter fires first
    assert not extractor._passes_hard_filters("Tickets: €20 per person")

def test_nightlife_rejected():
    assert not extractor._passes_hard_filters("Annual charity ball this Friday!")
```

### Category 2: Gemini integration tests (~15 tests, mocked)
Test the full `extract_event()` pipeline with mocked Gemini responses.

```python
def test_gemini_accept_with_full_datetime(extractor):
    """Gemini returns full datetime → stored correctly."""
    result = _run_gemini(extractor,
        caption="Free pizza in Newman this Friday at 6pm!",
        gemini_response={
            'food': True, 'title': 'Free Pizza',
            'start_datetime': '2026-03-06T18:00:00',
            'location': 'Newman Building', 'members_only': False
        },
        today='2026-03-01'
    )
    assert result is not None
    assert result['start_time'].hour == 18

def test_gemini_null_date_no_evidence(extractor):
    """Gemini returns null date, no date in text → no start_time."""
    result = _run_gemini(extractor,
        caption="Free pizza in Newman sometime soon!",
        gemini_response={
            'food': True, 'title': 'Free Pizza',
            'start_datetime': None, 'location': 'Newman Building'
        }
    )
    assert result is not None
    assert result['start_time'] is None

def test_gemini_hallucinated_date_rejected(extractor):
    """Gemini invents a date but text has no date evidence → date nulled."""
    result = _run_gemini(extractor,
        caption="Free pizza in Newman!",  # no date mentioned
        gemini_response={
            'food': True, 'start_datetime': '2026-03-06T18:00:00'
        }
    )
    assert result['start_time'] is None  # hallucinated date stripped

def test_gemini_past_datetime_rejected(extractor):
    """Gemini returns a past datetime → whole event rejected."""
    result = _run_gemini(extractor,
        caption="Free pizza last Friday at 6pm",
        gemini_response={
            'food': True, 'start_datetime': '2026-02-20T18:00:00'
        },
        today='2026-03-01'
    )
    assert result is None
```

### Category 3: Reconciliation tests (~5 tests)
Test the `_reconcile_datetime()` logic directly.

```python
def test_reconcile_agreement():
    """Regex and Gemini agree → confidence 1.0."""
    dt, conf = extractor._reconcile_datetime(
        '2026-03-06T18:00:00',
        'Free pizza this Friday at 6pm',
        post_ts=datetime(2026, 3, 1, tzinfo=UTC)
    )
    assert dt.hour == 18
    assert conf == 1.0

def test_reconcile_disagreement_trusts_regex():
    """Regex and Gemini disagree on date → regex wins."""
    # regex finds Friday 6th, Gemini returns Saturday 7th
    ...
```

---

## E7: Migration Checklist

```
[ ] E1: Update _GEMINI_SYSTEM_PROMPT — add today injection, update output format
[ ] E1: Update GeminiClassifier.classify_and_extract() — accept today_str, post_date_str
[ ] E2: Rewrite extractor.py — delete 700 lines, add _reconcile_datetime (~60 lines)
[ ] E3: Simplify date_parser.py → thin _parse_date_from_text() wrapper (~50 lines)
[ ] E3: Simplify time_parser.py → thin _parse_time_from_text() wrapper (~50 lines)
[ ] E4: Delete LLMClassifier + OpenAI prompts from llm_classifier.py
[ ] E5: Remove USE_SCORING_PIPELINE, USE_VISION_FALLBACK, OPENAI_API_KEY from config.py
[ ] E6: Rewrite test_classifier.py (~30 tests replacing 134)
[ ] E7: Update gemini_migration.md with final architecture
```

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Gemini quota exhausted (1,500/day free tier) | Low at current volume | Redis 7-day cache; `USE_GEMINI=false` kill switch rejects all events gracefully |
| Gemini hallucinated date passes validation | Low | `_reconcile_datetime()` requires date evidence in text |
| Gemini API outage | Low | `USE_GEMINI=false` kill switch; events simply not created during outage |
| Location canonicalization regression | Low | `_extract_location()` alias dict unchanged |
| Test coverage gap | Medium | 30 focused tests cover all critical paths |

---

## What This Does NOT Change

- Frontend (no changes needed — API response shape unchanged)
- Database schema (no changes)
- Scraping pipeline (`apify_scraper.py`, `scraping_tasks.py`)
- Email notifications (`brevo.py`)
- OCR pipeline (`image_text_extractor.py`) — still runs, output injected into Gemini prompt
- `members_only` badge (already implemented in Phase D)

---

## Estimated Effort

| Task | Estimated time |
|------|---------------|
| E1: Prompt update | 30 min |
| E2: extractor.py rewrite | 2 hours |
| E3: Thin parser wrappers | 30 min |
| E4: Delete OpenAI code | 15 min |
| E5: config.py cleanup | 15 min |
| E6: Test rewrite | 1.5 hours |
| E7: Docs update | 30 min |
| **Total** | **~5.5 hours** |