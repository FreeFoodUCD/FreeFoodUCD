# NLP Architecture Analysis — FreeFoodUCD
## Current State After Phase E + Phase F (March 2026)

> All 93 tests passing. Phase F complete. This document reflects the current production-ready codebase.

---

## 1. How the Pipeline Works (Current State — Phase E + F)

```
Instagram Post
      │
      ▼
[Hard Filters]  ← tuple[bool, str] return; audit-logged at INFO
      │           paid/nightlife/off-campus/religious/other-college
      │           bake_sale/cake_sale → soft hint (not hard reject)
      │ pass
      ▼
[TBC/TBA skip]  ← regex: "tbc", "to be confirmed"
      │ pass
      ▼
[Soft Filter Hints]  ← inject clarifying notes into Gemini prompt
      │                 for borderline patterns (bake sale, cake sale)
      ▼
[Gemini 2.0 Flash]  ← PRIMARY classifier + extractor
      │               caption (≤1500 chars, first 1000 + last 400 if longer)
      │               + up to 3 images as inline_data (base64, actual pixels)
      │               returns: {food, title, start_datetime, end_datetime,
      │                          location, image_text, members_only}
      │ food=true
      ▼
[image_text injection]  ← BEFORE _reconcile_datetime (injection-order fix)
      │                    text = f"{text}\n\n[Image Text]\n{image_text}"
      ▼
[_reconcile_datetime()]  ← cross-check Gemini ISO datetime vs regex evidence
      │                     _DATE_EVIDENCE_RE and _TIME_EVIDENCE_RE now see image text
      │                     returns (start_dt, end_dt, confidence)
      │                     confidence=-1.0 sentinel → past event, reject whole post
      ▼
[_extract_location()]  ← canonicalize Gemini's location string via alias dict
      │
      ▼
[Duplicate check]  ← ±1h window + same-day society dedup
      │               None start_time → title-only dedup (no crash)
      ▼
[Event saved to DB]  ← notifications sent
      │
      ▼
[Langfuse trace]  ← every Gemini call traced with input/output/latency/score
```

**How Gemini is used:**
- Single API call per post (caption + up to 3 images as `inline_data` base64)
- System prompt injects today's date + post publication date for relative date resolution
- Returns structured JSON: `{food, title, start_datetime, end_datetime, location, image_text, members_only}`
- `response_mime_type="application/json"` forces structured output
- `temperature=0` for deterministic classification
- Redis-cached 24h (keyed by `v2:<sha256(caption + image_urls + today_date)[:16]>`)
- Cache version prefix `v2` — prompt changes auto-invalidate all cached results
- Free tier: 1,500 req/day — sufficient for current ~50 societies × 3 posts/scrape = 150 req/run

---

## 2. Issues — Status After Phase F

### 2.1 Image Pipeline: Tesseract Before Gemini ✅ RESOLVED

**Was:** Tesseract OCR ran first, appended to caption, Gemini never saw actual images.
`file_uri` approach used raw Instagram CDN URLs (invalid for Gemini Files API) — silently failed.

**Fix applied:** Images downloaded via `httpx` and passed as `inline_data` (base64). Gemini now sees actual image pixels. Tesseract still runs as a pre-pass but Gemini's native vision is the primary image reader.

---

### 2.2 No Observability ✅ RESOLVED (F1)

**Was:** No visibility into accept/reject rates, false positives, Gemini raw responses.

**Fix applied:** Langfuse integration in `llm_classifier.py`. Every Gemini call creates a trace with:
- Input (caption preview, image count, society handle, post timestamp)
- Output (full JSON response)
- Score (`food_detected`: 0 or 1)
- Latency

Graceful degradation: if `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` are absent, Langfuse is silently disabled — no errors.

**To activate:** Set `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in Railway env vars (free at cloud.langfuse.com).

---

### 2.3 Redis Cache Hides Stale Classifications ✅ RESOLVED (F2)

**Was:** 7-day TTL meant improved prompts didn't take effect for a week. No cache versioning.

**Fix applied:**
- TTL reduced to 24h (posts older than 24h are filtered out anyway)
- Cache key prefix changed to `v2:` — any future prompt change just requires bumping `_CACHE_VERSION`

---

### 2.4 `_reconcile_datetime` Rejects Valid Gemini Datetimes When Image Has Date ✅ RESOLVED

**Was:** `image_text` was injected into `text` AFTER `_reconcile_datetime` was called, so `_DATE_EVIDENCE_RE` never saw dates from images.

**Fix applied:** Image text injection (Step 4) moved to BEFORE `_reconcile_datetime` (Step 5) in `extract_event()`. Dates and times in image text are now available to the evidence regexes.

---

### 2.5 Hard Filters Are Brittle and Have No Feedback Loop ✅ RESOLVED (F3)

**Was:** Hard filters silently dropped posts with no audit trail. `\bmass\b` blocked "mass catering". `'bar'` in `_BOUNDARY_VENUES` blocked "chocolate bar". `'bake sale'` hard-rejected even when free pizza was also offered.

**Fix applied:**
- `_passes_hard_filters()` now returns `tuple[bool, str]` — named rejection reason logged at INFO
- `\bmass\b` replaced with context-aware patterns: `\bsunday\s+mass\b`, `\b(?:going\s+to|attending|after|before|at)\s+mass\b`
- `'bar'` removed from `_BOUNDARY_VENUES` (too many false positives)
- `'bake sale'` and `'cake sale'` moved to `_SOFT_FILTER_HINTS` — passes hard filter, Gemini decides with a hint injected into the prompt

---

### 2.6 Duplicate Detection Crashes When `start_time` Is None ✅ RESOLVED

**Was:** `ev_start - timedelta(hours=1)` raised `TypeError` when `start_time=None`, silently dropping the event.

**Fix applied:** Guard in `scraping_tasks.py` — if `start_time is None`, skip time-based dedup and only do title-based dedup. Event is still saved (users see "time TBC").

---

### 2.7 Gemini Prompt Has No Few-Shot Examples for Edge Cases ✅ RESOLVED (F7)

**Was:** Only 6 straightforward examples. Missing: image-only posts, Irish slang, past-tense recap mixed with future, "free entry but food costs money", Kaffeeklatsch.

**Fix applied:** 5 new few-shot examples added covering:
- Image-only food announcement (vague caption, all info in image)
- Irish slang ("deadly grub", "gas craic")
- Past-tense recap mixed with upcoming event
- Free entry but food costs money → reject
- Kaffeeklatsch (German Society coffee morning) → accept

---

### 2.8 No Feedback Mechanism ✅ RESOLVED (F4)

**Was:** `PostFeedback` table existed but was never used.

**Fix applied:**
- `POST /api/v1/admin/events/{id}/feedback` endpoint in `admin.py`
- Admin UI has three feedback buttons on every event card: ✓ Correct, ✗ False Positive, ⚠ False Negative
- False positive feedback deactivates the event (`is_active=False`)
- Langfuse score synced so feedback appears in observability dashboard

---

### 2.9 DateParser/`_reconcile_datetime` Window Mismatch ✅ RESOLVED (F5)

**Was:** `DateParser._validate_date` used 90-day window; `_reconcile_datetime` used 30-day window.

**Fix applied:**
- `DateParser.__init__` accepts `max_future_days: int = 90` parameter
- `_regex_parse_date()` in `extractor.py` passes `max_future_days=30` to `DateParser`
- Both now use the same 30-day window

---

### 2.10 Gemini `file_uri` Approach Wrong for Instagram URLs ✅ RESOLVED

**Was:** `FileData.file_uri` used raw Instagram CDN URLs — invalid, silently failed.

**Fix applied:** Images downloaded via `httpx.get()` and passed as `inline_data` with base64-encoded bytes. Gemini now receives actual image pixels.

---

### 2.11 Single-Point-of-Failure: No Fallback When Gemini Is Down ✅ RESOLVED (F6)

**Was:** If Gemini API failed, post was marked `processed=True` and silently dropped forever.

**Fix applied:**
- `nlp_failed: bool` and `nlp_error: str` columns added to `Post` model
- Alembic migration `add_nlp_failed_to_posts.py` created
- `scraping_tasks.py`: on Gemini API error → `post.nlp_failed=True`, `post.processed=False` (will be retried)
- `reprocess_nlp_failed_posts()` Celery task in `maintenance_tasks.py` re-queues failed posts

---

### 2.12 Caption Truncated to 600 Characters ✅ RESOLVED

**Was:** `text[:600]` — lost key details at end of long captions.

**Fix applied:** If `len(text) <= 1500` → full text. Otherwise: first 1000 chars + `"\n...\n"` + last 400 chars. Captures both the opening and the hashtag/detail section at the end.

---

## 3. Current Known Limitations (Post Phase F)

### 3.1 Langfuse Keys Not Yet Set in Railway
Langfuse is wired up but inactive until `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are added to Railway env vars. See `gemini_migration.md` for setup steps.

### 3.2 Tesseract Still Runs Before Gemini
Tesseract OCR still runs as a pre-pass in `scraping_tasks.py`. Its output is appended to the caption before Gemini is called. This is now redundant (Gemini reads images directly) but harmless — Gemini ignores garbled OCR text and reads the image itself. Removing Tesseract is a future cleanup task.

### 3.3 No Monthly Re-Audit Automation
`audit_classifier.py` exists but must be run manually. A Celery beat task to run it monthly and alert on precision drops below 90% has not been implemented.

### 3.4 Non-English Captions Still Missed
Posts entirely in Irish, Chinese, or Arabic pass hard filters (no food keyword match) but Gemini handles them natively. This is actually fine — Gemini's multilingual capability means non-English posts are classified correctly once they reach the LLM.

---

## 4. Test Coverage

| Class | Tests | What it covers |
|-------|-------|----------------|
| `TestHardFilters` | 12 | Core hard filter pass/fail + tuple return + rejection reason |
| `TestGeminiIntegration` | 13 | Full pipeline with mocked Gemini — accept, reject, datetime, location, members-only |
| `TestReconcileDateTime` | 7 | Core reconcile logic — agreement, past, far-future, no evidence |
| `TestLocationExtraction` | 6 | Building alias canonicalization |
| `TestHardFilterEdgeCases` | 12 | mass/bar false positives, bake sale soft filter, price thresholds |
| `TestGeminiEdgeCases` | 14 | Image text injection order, Irish slang, end time, room codes, confidence |
| `TestReconcileDateTimeEdgeCases` | 10 | Image text date evidence, end_dt handling, time evidence, grace period |
| `TestLocationEdgeCases` | 8 | Room codes, Student Centre rooms, village rooms, generic aliases |
| `TestDateParserWindowAlignment` | 6 | F5 window consistency, DateParser max_future_days param |
| `TestRealWorldPostPatterns` | 6 | Full pipeline with realistic UCD captions |
| **Total** | **93** | **All passing** |

Run: `cd backend && venv/bin/pytest tests/nlp/test_classifier.py -v`