# FreeFoodUCD — Project Plan

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

The NLP pipeline determines whether an Instagram post is a free food event open to UCD students. This is the highest-leverage improvement area — the audit (707 posts) showed:

- Current precision: **88.6%** (101 true positives, 13 false positives)
- Current recall: **48.3%** (101 true positives, 108 false negatives)
- Target: **precision ≥ 95%, recall ≥ 70%**

The root causes of poor recall: keyword gaps, over-firing paid event filter, no context modifiers, no implied-free event types, missed past-tense recaps, and no LLM fallback for borderline posts.

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

**Phase A is complete. All 42 regression tests pass.**

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

### Phase B — LLM Fallback (next)

Posts that score in the "borderline" zone under the rule-based system are routed to GPT-4o-mini for a final accept/reject decision. Only borderline posts are sent to the LLM (~30% of posts). Results are Redis-cached for 7 days so the same post is never re-classified.

| # | Change | File | Status |
|---|--------|------|--------|
| B1 | LLM fallback classifier (GPT-4o-mini, Redis-cached 7 days) | `app/services/nlp/llm_classifier.py` *(new)* | **Not started** |
| B2 | Classification decision logging (food_score, paid_penalty, composite, stage_reached) | `extractor.py`, `scraping_tasks.py` | **Not started** |
| B3 | Regression test suite as proper pytest fixtures | `tests/nlp/test_classifier.py` *(new)* | **Not started** |
| B4 | Admin classification-stats endpoint (`borderline_rate`, `llm_call_count`) | `admin.py` | **Not started** |

#### Phase B design notes

- LLM is called only for borderline posts (composite score 30–65 under the scoring model).
- LLM prompt: caption + OCR text → `{is_event: bool, confidence: 0-100, reason: str}`.
- Flip to ACCEPT only if LLM confidence ≥ 80.
- Redis cache key: `llm_classify:{sha256(post_url)[:16]}`, TTL 7 days.
- Circuit breaker: >100 LLM calls/hour → disable LLM fallback + Sentry alert.
- Estimated cost: ~$0.45/month (OpenAI credit already available).
- `OPENAI_API_KEY` already added to config (optional; Phase A does not need it).

---

### Phase C — Long-Term

| # | Change | Status |
|---|--------|--------|
| C1 | Monthly automated LLM re-audit as Celery task (precision canary) | Not started |
| C2 | Non-English caption detection → auto-route to LLM | Not started |
| C3 | Fine-tuned embedding classifier (needs >5000 labeled examples) | Future |

---

## Next Concrete Steps

1. **Deploy Phase A** — push to `main`, Railway auto-deploys. Monitor the next scrape run (8am or 3pm Dublin) to confirm no regressions.

2. **Manually label 30–50 audit posts** — take posts from `backend/audit_report.txt` (mix of clear positives, borderlines, clear negatives) and label them by hand. These become the gold-standard fixtures for `tests/nlp/test_classifier.py`.

3. **Implement Phase B1** — create `backend/app/services/nlp/llm_classifier.py`:
   - Async function `classify_with_llm(caption: str, ocr_text: str) -> dict`
   - Redis cache with 7-day TTL
   - Prompt: structured JSON output `{is_event, confidence, reason}`
   - Wire into `_process_scraped_content_async` in `scraping_tasks.py` for borderline posts only

4. **Implement Phase B2** — add classification score logging:
   - Log `food_score`, `paid_penalty`, `composite`, `stage_reached`, `llm_called` for every post
   - Optional: store in `Event.extracted_data` JSONB for admin audit trail

5. **Run re-audit** — after Phase B is live for one week, re-run `audit_classifier.py` against the last batch of posts and compare precision/recall to baseline (88.6% / 48.3%).

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
| `backend/test_extractor.py` | 42-fixture regression test (run: `venv/bin/python test_extractor.py`) |
| `backend/audit_classifier.py` | LLM-based audit of full post history (silver-standard eval) |
| `backend/audit_report.txt` | Last audit results (707 posts, GPT-4o-mini as judge) |
