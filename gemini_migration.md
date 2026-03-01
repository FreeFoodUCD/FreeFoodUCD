# Gemini Migration & Production Deployment Guide

> Last updated: March 2026 (Phase E + Phase F complete)  
> The last production push used the **multi-level rule-based + OpenAI GPT-4o-mini** architecture (Phase B).  
> This guide covers everything needed to deploy the current **Gemini-first Phase E+F** codebase to Railway.

---

## 1. What Changed Since Last Production Push

The entire NLP pipeline was rewritten. The old architecture (Phase B) is gone:

| Old (Phase B — last production push) | New (Phase E+F — current codebase) |
|---------------------------------------|--------------------------------------|
| Rule-based classifier (`classify_event()`) | Deleted |
| OpenAI GPT-4o-mini fallback (`_try_llm_fallback()`) | Deleted |
| `LLMClassifier` (OpenAI) in `llm_classifier.py` | Deleted |
| `USE_SCORING_PIPELINE`, `USE_VISION_FALLBACK` flags | Deleted |
| `OPENAI_API_KEY` required | No longer needed |
| Tesseract OCR → append to caption → Gemini sees text only | Gemini sees actual image pixels (inline_data) |
| `file_uri` with Instagram CDN URLs (broken) | `inline_data` base64 (working) |
| 7-day Redis cache, no versioning | 24h Redis cache, `v2:` prefix |
| `_passes_hard_filters()` returns `bool` | Returns `tuple[bool, str]` |
| No observability | Langfuse tracing (optional) |
| No `nlp_failed` flag | `nlp_failed` + `nlp_error` on `Post` model |
| Caption truncated at 600 chars | First 1000 + last 400 chars (≤1500 total) |

---

## 2. Railway Environment Variables

### 2.1 Variables to ADD

```
# Primary LLM — Gemini 2.0 Flash (required)
GEMINI_API_KEY=<your Google AI Studio key>
USE_GEMINI=true

# Langfuse observability (optional but recommended)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 2.2 Variables to REMOVE (no longer used)

```
OPENAI_API_KEY          ← delete (OpenAI LLMClassifier removed)
USE_SCORING_PIPELINE    ← delete (flag removed from config.py)
USE_VISION_FALLBACK     ← delete (flag removed from config.py)
```

### 2.3 Variables to KEEP (unchanged)

```
DATABASE_URL
DATABASE_URL_SYNC
REDIS_URL
APIFY_API_TOKEN
BREVO_API_KEY
BREVO_FROM_EMAIL
BREVO_FROM_NAME
SECRET_KEY
ADMIN_API_KEY
ENVIRONMENT=production
SENTRY_DSN
ALLOWED_ORIGINS
SCRAPE_MAX_POSTS_PER_SOCIETY
NOTIFICATION_TEST_EMAILS
```

### 2.4 New Optional Variables (Phase F)

```
# Plausibility window for Gemini datetime validation (default: 30)
GEMINI_MAX_FUTURE_DAYS=30
```

---

## 3. Database Migration

Two new columns were added to the `posts` table in Phase F (F6):

```sql
ALTER TABLE posts ADD COLUMN nlp_failed BOOLEAN DEFAULT FALSE;
ALTER TABLE posts ADD COLUMN nlp_error TEXT;
```

**Run the Alembic migration after deploying:**

```bash
# On Railway — run in the backend service shell, or via a one-off task
cd backend && alembic upgrade head
```

The migration file is: `backend/alembic/versions/add_nlp_failed_to_posts.py`

If you have other pending migrations, `alembic upgrade head` will run them all in order.

---

## 4. Getting a Gemini API Key

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **Create API key**
4. Copy the key (starts with `AIza...`)
5. Add to Railway: `GEMINI_API_KEY=AIza...`

**Free tier:** 1,500 requests/day, 1,000,000 tokens/day — sufficient for current volume (~250 eligible posts/day with 6× headroom).

---

## 5. Setting Up Langfuse (Optional but Recommended)

Langfuse gives you a dashboard showing every Gemini classification decision — accept/reject rates per society, latency, full prompt+response for every call.

1. Go to https://cloud.langfuse.com and sign up (free)
2. Create a new project (e.g. "FreeFoodUCD")
3. Go to **Settings → API Keys → Create new key pair**
4. Copy the public key (`pk-lf-...`) and secret key (`sk-lf-...`)
5. Add to Railway:
   ```
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```

If these keys are absent, Langfuse is silently disabled — no errors, no impact on the pipeline.

**Free tier:** 50,000 events/month. At 600 Gemini calls/day × 30 days = 18,000 events/month — well within the free tier.

---

## 6. Deployment Checklist

```
[ ] 1. Add GEMINI_API_KEY to Railway env vars
[ ] 2. Set USE_GEMINI=true in Railway env vars
[ ] 3. Remove OPENAI_API_KEY from Railway env vars (or leave — it's ignored)
[ ] 4. Remove USE_SCORING_PIPELINE from Railway env vars (or leave — it's ignored)
[ ] 5. Remove USE_VISION_FALLBACK from Railway env vars (or leave — it's ignored)
[ ] 6. Run: alembic upgrade head  (adds nlp_failed + nlp_error columns)
[ ] 7. Deploy backend to Railway (git push)
[ ] 8. Deploy frontend to Vercel (git push or auto-deploy)
[ ] 9. Trigger a manual scrape from admin panel to verify pipeline works
[ ] 10. (Optional) Add Langfuse keys and verify traces appear at cloud.langfuse.com
```

---

## 7. Rollback Plan

If something goes wrong after deploying:

**Option A — Kill switch (no redeploy needed):**
```
USE_GEMINI=false
```
This causes all posts to be rejected (no LLM). Events stop being created but the app stays up. Use this to stop the pipeline while you investigate.

**Option B — Full rollback to Phase B (requires redeploy):**
```
USE_GEMINI=false
OPENAI_API_KEY=<your OpenAI key>
USE_SCORING_PIPELINE=true
USE_VISION_FALLBACK=true
```
Then revert the git commit and redeploy. Note: the Phase B code (`LLMClassifier`, `classify_event()`, etc.) has been deleted from the codebase — you would need to restore from git history.

---

## 8. What to Verify After Deploying

### 8.1 Immediate checks (within 5 minutes)

1. **Admin panel loads** — go to `/admin`, check the dashboard stats
2. **Trigger manual scrape** — click "Scrape Now" in admin panel
3. **Check Railway logs** — look for:
   - `ACCEPT: Gemini approved post` — pipeline is working
   - `HARD_FILTER_REJECT:paid_event | ...` — hard filters firing (expected)
   - No `AttributeError` or `TypeError` exceptions
4. **Check events tab** — new events should appear with confidence scores

### 8.2 After first automated scrape run (8am or 3pm Dublin time)

1. **Check event count** — should be similar to before (5-15 new events per run is normal)
2. **Check Langfuse dashboard** (if configured) — traces should appear within seconds of scrape
3. **Check for `nlp_failed` posts** — run in Railway shell:
   ```sql
   SELECT COUNT(*) FROM posts WHERE nlp_failed = true;
   ```
   Should be 0 or very low. If high, check Railway logs for Gemini API errors.

### 8.3 After 1 week

Re-run the audit to compare precision/recall vs Phase B baseline:
```bash
cd backend && venv/bin/python audit_classifier.py
```

Expected improvements:
- **Recall ↑** — Gemini reads image flyers directly (was broken before)
- **Precision ↑** — Gemini understands context better than keyword tiers
- **False positives ↓** — Gemini handles giveaways, past recaps, cooking activities

---

## 9. Current Architecture (Phase E+F)

```
Instagram Post (caption + image URLs)
        │
        ▼
[Tesseract OCR]  ← still runs as pre-pass, output appended to caption
        │          (Gemini also reads images directly — OCR is now redundant but harmless)
        ▼
[Hard Filters]  ← _passes_hard_filters() → tuple[bool, str]
        │           paid / nightlife / off-campus / religious / other-college
        │           bake_sale/cake_sale → soft hint (not hard reject)
        │           Every rejection logged: HARD_FILTER_REJECT:reason | text[:80]
        │ pass
        ▼
[TBC/TBA Skip]  ← "tbc", "tba", "to be confirmed" → skip
        │
        ▼
[Soft Filter Hints]  ← inject clarifying notes into Gemini prompt
        │
        ▼
[Gemini 2.0 Flash]  ← caption (≤1500 chars) + up to 3 images (inline_data base64)
        │               Returns: {food, title, start_datetime, end_datetime,
        │                          location, image_text, members_only}
        │               Redis-cached 24h (key: v2:llm_gemini:<sha256>)
        │ food=false → REJECT
        │ food=true  → continue
        ▼
[image_text injection]  ← BEFORE _reconcile_datetime
        │
        ▼
[_reconcile_datetime()]  ← cross-check Gemini ISO datetime vs regex evidence
        │                    confidence=-1.0 → past event, reject whole post
        ▼
[_extract_location()]  ← canonicalize via alias dict (100+ aliases)
        │
        ▼
[Duplicate check]  ← ±1h window; None start_time → title-only dedup
        │
        ▼
[Event saved to DB]  ← notifications sent
        │
        ▼
[Langfuse trace]  ← input/output/latency/score logged (if keys configured)
```

---

## 10. Key Files

| File | Role |
|------|------|
| `backend/app/services/nlp/extractor.py` | `EventExtractor` — hard filters, `extract_event()`, `_reconcile_datetime()`, `_extract_location()` |
| `backend/app/services/nlp/llm_classifier.py` | `GeminiClassifier` — single call: classify + extract. Redis-cached. Langfuse tracing. |
| `backend/app/services/nlp/date_parser.py` | Regex date extraction — cross-check validator |
| `backend/app/services/nlp/time_parser.py` | Regex time extraction — cross-check validator |
| `backend/app/services/ocr/image_text_extractor.py` | Tesseract OCR (pre-pass, now redundant) |
| `backend/app/workers/scraping_tasks.py` | Celery task: scrape → OCR → NLP → save → notify |
| `backend/app/workers/maintenance_tasks.py` | `reprocess_nlp_failed_posts()` — retries posts where Gemini API failed |
| `backend/app/core/config.py` | All env-var settings and feature flags |
| `backend/app/api/v1/endpoints/admin.py` | Admin API including `/events/{id}/feedback` endpoint |
| `backend/alembic/versions/add_nlp_failed_to_posts.py` | Migration: adds `nlp_failed` + `nlp_error` to `posts` table |
| `backend/tests/nlp/test_classifier.py` | 93 tests — run: `cd backend && venv/bin/pytest tests/nlp/test_classifier.py -v` |

---

## 11. Cost Summary

| Service | Cost | Notes |
|---------|------|-------|
| Gemini 2.0 Flash | **$0/month** | Free tier: 1,500 req/day. Current usage: ~250/day (6× headroom) |
| Langfuse | **$0/month** | Free tier: 50k events/month. Current usage: ~18k/month |
| OpenAI | **$0/month** | No longer used |
| Railway (backend + worker) | ~$5/month | Unchanged |
| Vercel (frontend) | $0/month | Free tier |
| Brevo (email) | $0/month | Free tier (300 emails/day) |