# FreeFoodUCD — NLP Plan

## What Has Been Built

FreeFoodUCD is a production service that scrapes UCD society Instagram accounts, detects free food events, and emails subscribers in real time.

### Core Infrastructure (complete)
- **Scraper**: Apify-based Instagram scraper, runs 2x/day (8am + 3pm Dublin time). Batch scrapes all active societies in one Apify call. Results cached in Redis for 90 minutes so Celery retries never pay twice.
- **Pipeline**: Scrape → OCR → NLP classify → extract event details → dedup → store → email
- **Database**: PostgreSQL on Railway. Models: Society, Post, Event, User, NotificationLog, ScrapingLog.
- **Email**: Brevo (Sendinblue). Batch email per user per scrape run (one email listing all new events). Sender: hello@freefooducd.com.
- **Queue**: Redis + Celery on Railway.
- **Frontend**: Next.js on Vercel. Signup, email verification, society preferences.
- **Admin**: Protected admin API (ADMIN_API_KEY) for manual scrape triggers, force-reprocess, society management.

### Security Hardening (complete)
- HMAC-signed user tokens (1-hour TTL) on all user-facing endpoints.
- Rate limiting: `/signup` 3/10min, `/verify` 5/10min per IP (slowapi).
- Sentry error tracking (activate by setting `SENTRY_DSN` in Railway).
- Notification idempotency: `event.notified` committed before email loop; retries skip already-notified users via `NotificationLog`.
- Parallel email sends via `asyncio.gather` + `Semaphore(10)`.
- CSPRNG for 6-digit verification codes.

### Scraping Hardening (complete)
- Distributed lock (`scrape_all_posts_lock`, 30-min TTL) prevents overlapping runs.
- Zero-result guard: >10 societies returning 0 results → error log + RuntimeError (triggers retry, hits cache).
- Per-post error isolation: one bad post does not abort the whole batch.
- 10-min admin cooldown on manual scrape triggers; bypass with `force_reprocess=true`.
- All carousel images passed to OCR (not just image[0]).

---

## Current Focus: NLP Classification

The NLP pipeline determines whether an Instagram post is a free food event open to UCD students.

### Audit History (GPT-4o-mini as silver-standard judge, 707 posts)

| Audit | Date | TP | FP | FN | Precision | Recall | Notes |
|-------|------|----|----|----|-----------|--------|-------|
| Baseline | pre-2026-02-28 | 101 | 13 | 108 | **88.6%** | **48.3%** | Rule-based only, original extractor |
| Phase A | 2026-03-01 | 102 | 13 | 123 | **88.7%** | **45.3%** | See notes below |

**Target: precision ≥ 95%, recall ≥ 70%**

**Phase A audit notes:** Precision held flat (+0.1%). Recall dipped slightly despite Phase A improvements because (a) the LLM judge is more permissive than our rule-based system, labelling many speculative posts as food events, and (b) many of the 123 FNs are legitimately rejected (empty captions, bake-sale-for-charity, past-tense recaps). The biggest genuine miss categories in the FNs:
- **"food" keyword with no context modifier** (24 posts) — exactly the grey zone B1 targets
- **"snacks", "breakfast", "dinner", "baked goods", "goodies"** — not in any keyword list yet
- **Eid/Ramadan posts** — religious event filter over-firing
- **Posts with empty captions** — OCR missed; scraping issue not NLP

Next audit after 1 week of B1 in production will isolate B1's real contribution.

The root causes of poor recall: keyword gaps, no context modifiers for weak keywords, missed past-tense recaps, and no LLM fallback for borderline posts.

---

## NLP Improvement Plan

### Phase A — Rule-Based (no external dependencies)

| # | Change | File | Status |
|---|--------|------|--------|
| A1 | OCR all carousel images (not just image[0]) | `scraping_tasks.py`, `image_text_extractor.py` | **Done** (was already implemented) |
| A2 | Richer context modifiers for weak food keywords | `extractor.py` | **Done** |
| A3 | Past-tense recap filter | `extractor.py` | **Done** |
| A4 | Implied-free event types ("welcome reception", "freshers fair") | `extractor.py` | **Done** |
| A5 | Staff/committee-only filter → reject | `extractor.py` | **Done** |
| A6 | Score-based paid penalty (replace binary reject) | `extractor.py` | **Done** |

**Phase A is complete. All 59 regression tests pass (42 original + 17 Phase A edge cases).**

#### What Phase A changed in `extractor.py`

- **A2**: `_has_explicit_food` now accepts "included", "on us", "kindly sponsored", "brought to you by", "at no cost/charge", "for free" as context modifiers (not just "provided"/"complimentary"). Stored in `self.context_modifiers`.
- **A4**: "welcome reception", "freshers fair", "fresher's fair", "open evening" added to `strong_food_keywords`.
- **A3**: New `_is_past_tense_post()` — fires on "thanks for coming", "[food] was amazing", "hope everyone had", etc. Runs before food detection.
- **A5**: New `_is_staff_only()` — fires on "committee only", "exec meeting/training/session", "volunteers only", "board meeting". Does NOT fire on "committee" alone (too broad).
- **A6**: `_is_paid_event()` rewritten. Now: membership context ≤€5 → allowed; ticket/admission language → hard reject; €X ≥10 without explicit "free [food]" → reject; small fees (€2-5) without ticket language → pass. "€5 registration + refreshments" is now accepted.
- **members_only**: `_is_members_only` extended to catch "members welcome", "join…member…attend". Already stored in `extracted_data` JSONB and read by `notification_tasks.py` — no schema change needed.

Also added to `config.py`:
- `USE_SCORING_PIPELINE: bool = True` — set to `false` in Railway env for emergency rollback without redeploy.
- `OPENAI_API_KEY: Optional[str] = None` — placeholder for Phase B.

---

### Phase B — LLM Fallback (complete)

Borderline posts (weak food keyword, no context modifier, no strong keyword) are routed to GPT-4o-mini. The same call also returns location + time hints to fill gaps the rule-based extractors miss. Results are Redis-cached 7 days so the same post is never re-classified.

| # | Change | File | Status |
|---|--------|------|--------|
| B1 | LLM fallback classifier + extraction hints (GPT-4o-mini, Redis-cached 7 days) | `app/services/nlp/llm_classifier.py` *(new)* | **Done** |
| B2 | Classification decision logging (food_score, paid_penalty, composite, stage_reached) | `extractor.py`, `scraping_tasks.py` | **Not started** |
| B3 | Regression test suite as proper pytest fixtures | `tests/nlp/test_classifier.py` *(new)* | **Not started** |
| B4 | Admin classification-stats endpoint (`borderline_rate`, `llm_call_count`) | `admin.py` | **Not started** |

**Phase B1 is complete. All 59 regression tests pass. `OPENAI_API_KEY` set in Railway.**

#### What Phase B1 implemented

**Grey zone gate** — `_has_weak_food_only()` in `extractor.py`:
- Fires only when: weak food keyword present + no strong keyword + no free context modifier
- Strong keywords and well-provisioned posts never touch the LLM

**LLM call** — single GPT-4o-mini call per borderline post, returning `{food, location, time}`:
- Prompt includes canonical UCD building list to constrain location output to known names
- `max_tokens=60`, caption capped at 600 chars, `temperature=0`, JSON mode
- ~320 tokens/call → **~$0.10/year**

**Fallback flow** in `extract_event()`:
1. `classify_event()` returns False → `_try_llm_fallback()` runs all hard filters first (staff-only, off-campus, paid, nightlife) — LLM cannot bypass safety checks
2. If LLM returns `food: true` → event is accepted with reduced confidence (0.7 if time+location found, 0.5 otherwise; vs 1.0/0.8 for rule-based)
3. `hints['location']` fills rule-based location gap if present
4. `hints['time']` fills rule-based time gap if present
5. `extracted_data['llm_assisted'] = True` stored in JSONB for audit trail

**Caching + reliability:**
- Redis cache: `llm_extract:{sha256[:16]}`, TTL 7 days
- Circuit breaker: any exception → `None` → rule-based reject (never crashes pipeline)
- `USE_SCORING_PIPELINE=False` in Railway → LLM entirely skipped
- No `OPENAI_API_KEY` → singleton never created, zero API calls

---

### Phase C — Long-Term

| # | Change | Status |
|---|--------|--------|
| C1 | Monthly automated LLM re-audit as Celery task (precision canary) | Not started |
| C2 | Non-English caption detection → auto-route to LLM | Not started |
| C3 | Fine-tuned embedding classifier (needs >5000 labeled examples) | Future |

---

## Next Concrete Steps

1. **Run re-audit in ~1 week** — B1 is now live in production. After a week of scrape runs (~14 cycles), re-run `audit_classifier.py` to measure B1's real contribution. Expect the grey-zone FNs ("food"/"snacks"/"dinner" with no context) to drop.

2. **Implement Phase B2** — add per-post classification decision logging:
   - Log `stage_reached` (which filter fired), `llm_called`, `llm_food` result to `Event.extracted_data` JSONB
   - Enables admin audit trail without a schema change

3. **Implement Phase B4** — admin stats endpoint:
   - `GET /admin/nlp-stats` → `{borderline_rate, llm_call_count, llm_accept_rate}` over last N scrape runs
   - Pulls from `ScrapingLog` + `Event.extracted_data`

4. **Manually label 30–50 audit posts** — take posts from `backend/audit_report.txt`, label by hand, convert to gold-standard pytest fixtures in `tests/nlp/test_classifier.py` (B3).

---

## Key Files

| File | Role |
|------|------|
| `backend/app/services/nlp/extractor.py` | Main classifier + structured extractor (1060 lines) |
| `backend/app/services/ocr/image_text_extractor.py` | Tesseract OCR — accepts list of URLs, merges output |
| `backend/app/services/nlp/date_parser.py` | Regex date extraction |
| `backend/app/services/nlp/time_parser.py` | Regex time extraction |
| `backend/app/workers/scraping_tasks.py` | Celery task: scrape → OCR → NLP → save → notify |
| `backend/app/workers/notification_tasks.py` | Celery task: email eligible users, batch per scrape run |
| `backend/app/services/notifications/brevo.py` | Brevo email service (sole email provider) |
| `backend/app/core/config.py` | All env-var settings (feature flags, keys) |
| `backend/app/db/models.py` | SQLAlchemy models |
| `backend/app/services/nlp/llm_classifier.py` | GPT-4o-mini classifier + extraction hints, Redis-cached |
| `backend/test_extractor.py` | 59-fixture regression test (run: `venv/bin/python test_extractor.py`) |
| `backend/audit_classifier.py` | LLM-based audit of full post history (silver-standard eval) |
| `backend/audit_report.txt` | Last audit results (707 posts, GPT-4o-mini as judge) |
