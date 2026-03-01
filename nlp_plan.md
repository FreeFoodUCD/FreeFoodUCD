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

### Decision Pipeline (in order)

```
Caption + OCR text
       │
       ▼
[1]  Past-tense filter       → "thanks for coming", "was amazing" → REJECT
[2]  _has_explicit_food()    → needs strong keyword OR (weak + context modifier) → REJECT if missing
[3]  Food-activity filter    → baking class, cooking competition → REJECT
[4]  Giveaway filter (A7)    → "giveaway", "enter to win", "prize draw" → REJECT
[5]  Staff-only filter (A5)  → "committee only", "exec meeting" → REJECT
[6]  Other college filter    → Trinity, DCU, etc. → REJECT
[7]  Off-campus filter       → Dundrum, pub, bar, named Dublin venues → REJECT
[8]  Online-only filter      → Zoom + no UCD location → REJECT
[9]  Paid event filter (A6)  → ticket language, €10+ amounts → REJECT
[10] Nightlife filter        → "ball", "pub crawl", "nightclub", "club night", etc. → REJECT
       │
       ▼
    ACCEPT  →  extract_event()
                  │
                  ├── B5: TBC detected? → return None (skip post)
                  ├── time_parser, date_parser, location extractor
                  └── LLM fallback (if OPENAI_API_KEY set): fills gaps
```

### Keyword Tiers

| Tier | Examples | Rule |
|------|----------|------|
| **Strong** | pizza, refreshments, cookies, snacks, coffee morning, pancakes, biscuits, chocolate, cake, kaffeeklatsch, free samples, handing out samples, welcome reception, freshers fair… (≈55 terms) | Sufficient alone |
| **Weak** | food, lunch, dinner, breakfast, drinks, drink, snack, tea, coffee, refreshers | Must be paired with a context modifier |
| **Context modifiers** | provided, complimentary, included, on us, kindly sponsored, brought to you by, at no cost/charge, for free, on the house | Upgrades a weak keyword to sufficient evidence |

---

## Audit History

| Audit | Date | TP | FP | FN | Precision | Recall | Notes |
|-------|------|----|----|----|-----------|--------|-------|
| Baseline | pre-2026-02-28 | 101 | 13 | 108 | **88.6%** | **48.3%** | Rule-based only |
| Phase A | 2026-03-01 | 102 | 13 | 123 | **88.7%** | **45.3%** | See notes below |
| Phase A8-A11+B5 | pending | — | — | — | — | — | **Re-audit due ~2026-03-08 after 1 week of new rules in production** |

**Target: precision ≥ 95%, recall ≥ 70%**

**Phase A audit notes:** Precision held flat (+0.1%). Recall dipped slightly because the LLM judge (GPT-4o-mini) is more permissive than the rule-based system, labelling many speculative posts as food events. The biggest genuine miss categories in the 123 FNs:
- **"food" keyword with no context modifier** (24 posts) — grey zone B1 handles
- **"breakfast", "dinner", "baked goods", "goodies"** — not in keyword lists or need modifier
- **Posts with empty captions** — OCR miss; scraping issue not NLP
- **Eid/Ramadan posts** — religious event filter over-firing

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
| A7 | Giveaway/contest filter → reject | `extractor.py` | **Done** |
| A8 | Add `kaffeeklatsch` to `strong_food_keywords` | `extractor.py` | **Done** (2026-03-01) |
| A9 | Add `free samples`, `handing out samples` to `strong_food_keywords` | `extractor.py` | **Done** (2026-03-01) |
| A10 | Remove `night out` from `nightlife_keywords` and `off_campus_venues` | `extractor.py` | **Done** (2026-03-01) |
| A11 | Multi-event segmentation → multiple Events per Post | `extractor.py`, `scraping_tasks.py` | **Done** (2026-03-01) |
| A12 | OCR improvement: adaptive thresholding fallback | `image_text_extractor.py` | **Not started** |

**Phase A (A1–A11) is complete. 90 tests pass: 67 classify_event + 4 B5 + 4 A11 + 15 screenshot-based.**

---

### What A8–A11 + B5 Changed (session: 2026-03-01)

#### Context: 17 real "Important Posts" screenshots reviewed

Screenshots were read directly (`backend/Important posts/IMG_3965–3991`) and used to build 15 real-world regression tests, all passing.

---

#### A8 — `kaffeeklatsch` → `strong_food_keywords`

**Root cause:** UCD German Society posts use "Kaffeeklatsch" (German for coffee chat/social). It was not in any keyword list. If the caption also contained "tea, coffee, snacks" (as in IMG_3989/3990), it would accept via `snacks` = strong — but if the caption was thin and only the image had "KAFFEEKLATSCH", OCR was the only path and the word was unrecognised.

**Fix:** `'kaffeeklatsch'` added to `strong_food_keywords`. One-line change. Now ACCEPTS on the word alone.

---

#### A9 — `free samples`, `handing out samples` → `strong_food_keywords`

**Root cause:** The Food Hall UCD posted "We'll be handing out samples of our new Indian and Thai dishes in the Foodhall!" (IMG_3991). No keyword matched: "samples", "dishes", "handing out" were all absent from keyword lists.

**Fix:** `'free samples'` and `'handing out samples'` added to `strong_food_keywords`. Both are unambiguous compound phrases — "samples" alone is too broad (product survey), but the compound is specific to food provision.

---

#### A10 — Remove `night out` from `nightlife_keywords` and `off_campus_venues`

**Root cause (Bug 1):** NAMSOC's "Week 24" schedule post (IMG_3986) listed four events: Pancake Tuesday, Healthcare Debate, Coffee Morning, Coppers Night Out. The combined OCR text contained "COPPERS NIGHT OUT", which matched `night out` in `nightlife_keywords`. Hard reject — the whole post was classified False, losing two legitimate food events (pancakes + coffee morning).

**Fix:** `'night out'` removed from both `load_nightlife_keywords()` and the `off_campus_venues` list. Rationale: "night out" as a phrase is too generic — a post can say "come for free pancakes before your night out" and be perfectly legitimate. The remaining nightlife terms (`nightclub`, `club night`, `bar crawl`, `pub crawl`, `pre drinks`, `afters`, `sesh`, `going out`, `ball`, `gala`, `formal`) are all specific enough to safely reject alone.

**After A10:** The NAMSOC Week 24 full-post test now correctly returns True (accepted). Coppers Night Out in isolation still correctly returns False because (a) it contains "nightclub" in the test text, and (b) there is no food keyword — "free entry" ≠ free food.

---

#### B5 — TBC/TBA time detection → `extract_event()` returns `None`

**Root cause:** `time_parser.py` has no knowledge of "TBC", "TBA", "to be confirmed". When a society posts "Açaí Breakfast TBC — details to follow", no time can be extracted, a null event is created, and the email shows no time. Worse, the society will post a follow-up with the real details — creating a duplicate dedup problem.

**Fix:** After classification passes (and LLM fallback if applicable), `extract_event()` checks for:
```python
r'\btbc\b', r'\btba\b', r'\bto\s+be\s+confirmed\b', r'\bto\s+be\s+announced\b'
```
If matched → return `None`. The post is not persisted as an event. When the society posts a follow-up with the real time, it's treated as a fresh post (no dedup conflict since no event was created).

**Risk:** If the follow-up post wording is very different from the original, it may not be caught by the keyword classifier. This is acceptable — it's better to potentially miss the follow-up than to email users with "Time: TBC".

**Scope:** The Finlay Week post (IMG_3988) — "Açaí Breakfast TBC" — would hit B5 if the LLM approved it. In practice it never reaches B5 because `breakfast` (weak keyword, no modifier) fails at `_has_explicit_food()` first. B5 is primarily relevant for posts with STRONG food keywords + TBC time, e.g. "Free pizza this week! Time TBC."

---

#### A11 — Multi-event segmentation → multiple Events per Post

**Root cause (Bug 1 continued):** Even with A10 fixing the nightlife filter, the NAMSOC Week 24 post creates only ONE event from the combined caption+OCR text — whichever time is extracted first. Coffee Morning (08:30) and Pancake Tuesday (11:00) are distinct events that deserve separate rows, separate dedup checks, and separate notification emails on different days.

**Structural change in `extractor.py`:** New method `segment_post_text(text) → list[str]`:
```python
_SEG_PATTERN = re.compile(
    r'\n\n+(?=[A-Z][A-Z\s]{4,}\n|'
    r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))',
    re.IGNORECASE,
)
```
- Splits on blank line(s) + ALL-CAPS heading (≥5 chars) or day-of-week name
- Minimum 50 chars per segment (noise guard — filters single-word OCR fragments; 80 was too aggressive for real schedule entries which average ~70 chars)
- Maximum 6 segments (prevents runaway on irregular text)
- If ≤1 segment produced → returns `[text]` (falls back to current full-post behavior — zero regression risk)

**Structural change in `scraping_tasks.py` (`_process_scraped_content_async`):** Instead of one `extract_event(text)` call, the function now:
1. Calls `segment_post_text(text)` → list of segments
2. Loops over segments; calls `classify_event(segment)` + `extract_event(segment)` for each
3. For each accepted segment: runs existing ±1-hour + same-day dedup checks
4. Creates one `Event` row per accepted segment (all with same `source_id = Post.id`)
5. **Key dedup fix:** tracks `created_this_run_uuids` — events flushed from earlier segments in the same run are excluded from the same-day society dedup check. Without this, the second food event in a NAMSOC post would always be blocked by the same-day dedup (which finds the first event just flushed).
6. Returns `{"event_created": True, "event_ids": ["...", "..."]}` — both callers (`_scrape_all_posts_async` and `_scrape_society_posts_async`) updated to `.extend(nlp_result.get("event_ids", []))`.

**Example outcomes (from A11 tests):**
```
NAMSOC Week 24 (4 segments, 50-char min):
  Seg 0: "PANCAKE TUESDAY..."   → pancakes = STRONG → Event 1 (11:00)
  Seg 1: "COFFEE MORNING..."    → coffee morning = STRONG → Event 2 (08:30)
  Seg 2: "HEALTHCARE DEBATE..."  → no food → rejected
  Seg 3: "COPPERS NIGHT OUT..."  → no food keyword + nightclub → rejected

German Soc Week 7 (2 segments):
  Seg 0: "KAFFEEKLATSCH..."     → kaffeeklatsch = STRONG (A8) → Event 1
  Seg 1: "GERMAN FOR BEGINNERS..." → no food → rejected
```

**Known limitation:** `segment_post_text()` only fires when the combined text has `\n\n` (double newlines) before ALL-CAPS headings. This works when:
- OCR text preserves newlines from schedule graphics (Tesseract PSM 11 does this for clear grids)
- Instagram captions use line breaks between schedule items

It does NOT fire when OCR collapses the schedule into a single dense line (depends on image quality/font). In that case it falls back to full-text behavior, which still accepts the post if any segment has a food keyword — just creates one event instead of many.

---

### Phase B — LLM Fallback (complete)

Borderline posts (weak food keyword, no context modifier, no strong keyword) are routed to GPT-4o-mini. Same call returns location + time hints to fill gaps the rule-based extractors miss. Results Redis-cached 7 days.

| # | Change | File | Status |
|---|--------|------|--------|
| B1 | LLM fallback classifier + extraction hints (GPT-4o-mini, Redis-cached 7 days) | `app/services/nlp/llm_classifier.py` *(new)* | **Done** |
| B2 | Classification decision logging (stage_reached, llm_called, llm_food) | `extractor.py`, `scraping_tasks.py` | **Not started** |
| B3 | Regression test suite as proper pytest fixtures | `tests/nlp/test_classifier.py` *(new)* | **Not started** |
| B4 | Admin classification-stats endpoint (`borderline_rate`, `llm_call_count`) | `admin.py` | **Not started** |
| B5 | TBC/TBA time detection → skip post entirely | `extractor.py` | **Done** (2026-03-01) |

#### What Phase B1 implemented

**Grey zone gate** — `_has_weak_food_only()` in `extractor.py`:
- Fires only when: weak food keyword present + no strong keyword + no free context modifier
- Strong keywords and well-provisioned posts never touch the LLM

**LLM call** — single GPT-4o-mini call per borderline post, returning `{food, location, time}`:
- Prompt includes canonical UCD building list to constrain location output
- `max_tokens=60`, caption capped at 600 chars, `temperature=0`, JSON mode
- ~320 tokens/call → **~$0.10/year**

**Fallback flow** in `extract_event()`:
1. `classify_event()` returns False → `_try_llm_fallback()` runs all hard filters first (staff-only, off-campus, paid, nightlife) — LLM cannot bypass safety checks
2. If LLM returns `food: true` → event accepted with confidence 0.7 (time+location) or 0.5 (neither)
3. `hints['location']` + `hints['time']` fill rule-based gaps if present
4. `extracted_data['llm_assisted'] = True` stored in JSONB for audit trail

**B5 interaction with B1:** If the LLM approves a borderline post → `extract_event()` still runs the TBC check immediately after. A "coffee morning TBA" post that slips past rule-based and is LLM-approved will still be skipped by B5.

---

### Phase C — Long-Term

| # | Change | Status |
|---|--------|--------|
| C1 | Monthly automated LLM re-audit as Celery task (precision canary) | Not started |
| C2 | Non-English caption detection → auto-route to LLM | Not started |
| C3 | Fine-tuned embedding classifier (needs >5000 labeled examples) | Future |

---

## Known Failures & Limitations

### Production False Positives Found

| ID | Date | Society | Root cause | Fix |
|----|------|---------|-----------|-----|
| `5231f44d` | 2026-03-01 | @ucdisoc | `"chocolate"` in strong keywords matched a giveaway prize; no giveaway filter existed | A7: `_is_giveaway_contest()` |

### Structural Limitations

**1. Admin `scrape-now` endpoint does not use segmentation (A11)**

`admin.py` lines 734–773 have their own NLP code path: it calls `extractor.extract_event(combined_text)` directly (not via `_process_scraped_content_async`). This means admin-triggered scrapes will only create one event per post, even for multi-event schedule posts.

Impact: low. Admin scrapes are mainly used for debugging single posts. The automated Celery worker path (which runs at 8am/3pm) correctly uses segmentation.

Fix: eventually refactor admin's NLP block to call `_process_scraped_content_async` internally rather than duplicating the logic.

**2. Segmentation requires OCR to preserve newlines**

`segment_post_text()` splits on `\n\n+` (double newlines). This works when Tesseract PSM 11 correctly identifies paragraph breaks in a schedule graphic. For heavily styled images (gradient backgrounds, decorative fonts) where Tesseract collapses text into one block, segmentation silently falls back to full-text processing — still creates one event (if food keyword present), just misses the multi-event structure.

OCR improvement (A12: adaptive thresholding fallback) would help here.

**3. `night out` removal: residual risk**

After A10, a post that says "free refreshments for our night out crew" with no other nightlife term would now pass the nightlife filter. However it would still need a proper food keyword to pass `_has_explicit_food()` (which "refreshments" alone without a context modifier would fail). In practice this seems safe, but warrants watching in the re-audit.

**4. Keyword-based food detection**

Posts that imply food visually (a photo of pizza with no caption text or OCR output) are never accepted. This is intentional — false positives are worse than false negatives for user trust.

**5. Giveaway filter coverage gaps**

`_is_giveaway_contest()` covers the most common patterns. It does not cover:
- "competition" alone — too broad (would reject legitimate bake-off competitions)
- "win a [prize]" without giveaway language — rare; LLM fallback handles
- "raffle" alone — `_is_paid_event()` already correctly rejects "raffle ticket" (paid)

**6. Non-English captions**

No language detection. Non-English posts with no English food keyword are always rejected by rule-based and only reach LLM if a weak keyword is present. Fully non-English posts are permanently missed unless the LLM is extended to handle them (Phase C2).

**7. `"chocolate"` and dessert words in strong keywords**

`chocolate`, `cookies`, `cake` etc. are legitimately served at campus events. The giveaway filter (A7) is the correct layer for "win a box of chocolates" cases — not removing the keyword itself.

**8. Recall gap: missing keyword families**

Known terms not yet modelled as keywords:
- `"baked goods"`, `"goodies"` — recurring FNs in audit; safe to add as weak keywords
- `"açaí bowl"`, `"acai bowl"` — niche but appeared in Finlay Week (IMG_3988)
- Food-by-emoji only (🌮 without any text label) — emoji-to-keyword map handles the most common ones; gaps remain for obscure emoji usage

---

## Screenshot Test Coverage (2026-03-01)

17 posts from `backend/Important posts/` reviewed. 15 classify_event regression tests added. All pass.

| Screenshot | Post | Expected | Classifier result | Key signal |
|-----------|------|----------|------------------|-----------|
| IMG_3965 | Arts Soc Coffee Morning | ACCEPT | ✅ | `coffee morning` = strong |
| IMG_3966 | Arts Soc Week 6 schedule | ACCEPT | ✅ | `coffee morning` in OCR only (caption empty of food) |
| IMG_3967 | Hispanic Soc Día de la Bandera | ACCEPT | ✅ | `tacos`+`nachos`+`snacks`; `WINNER GETS A VERY SPECIAL PRIZE` ≠ A7 pattern |
| IMG_3969 | Econ Soc Refreshers Week | REJECT | ✅ | `refreshers` = weak, no modifier |
| IMG_3970 | Econ Soc Coffee Morning | ACCEPT | ✅ | `coffee morning` = strong |
| IMG_3971 | MicroSoc Seminar Series | ACCEPT | ✅ | `snacks will be provided`; €2/€15 = membership, not ticket |
| IMG_3972 | NorthSoc Coffee Afternoon | ACCEPT | ✅ | `coffee afternoon` = strong + `biscuits` = strong |
| IMG_3975 | Plan'Eat Free Lunch | ACCEPT | ✅ | `free lunch included` in OCR (caption = meal prep, no food word) |
| IMG_3976+3977 | RADSOC Run 5 Donate 5 | REJECT | ✅ | `Tickets: €5` = ticket language → paid hard reject |
| IMG_3978 | RADSOC Free Breakfast | ACCEPT | ✅ | `free breakfast` = strong |
| IMG_3986 | NAMSOC Week 24 schedule | **ACCEPT** | ✅ | **A10 fix**: `pancakes`+`coffee morning` accepted; `night out` no longer blocks |
| IMG_3987 | NAMSOC Free Cookies | ACCEPT | ✅ | `cookies` = strong |
| IMG_3988 | Finlay Week Açaí Breakfast TBC | REJECT | ✅ | `breakfast` = weak + no modifier (B5 would block `extract_event` too) |
| IMG_3989+3990 | German Soc Kaffeeklatsch | **ACCEPT** | ✅ | **A8 fix**: `kaffeeklatsch` = strong (previously unrecognised) |
| IMG_3991 | Food Hall BLASTA samples | **ACCEPT** | ✅ | **A9 fix**: `handing out samples` = strong (previously unrecognised) |

Note: IMG_3967 (Hispanic Soc) and IMG_3988 (Finlay Week) were not tested for `extract_event` output (time/location extraction). Only `classify_event` is tested in the regression suite. Full extract_event correctness is verified via admin force_reprocess.

---

## Next Concrete Steps

### 1. Re-audit (~2026-03-08, 1 week after deploy)

After ~14 scrape cycles with A8/A9/A10/A11/B5 in production, re-run `audit_classifier.py` against the full post history.

**Expected improvements vs Phase A audit (45.3% recall, 88.7% precision):**
- **Recall ↑**: A11 creates multiple events from schedule posts → FN count drops for societies that post weekly schedules (NAMSOC, Arts Soc, German Soc). A8 catches Kaffeeklatsch posts. A9 catches Food Hall sampling events.
- **Recall neutral**: B5 slightly reduces recall by skipping TBC posts — but these were FNs already (null time → poor email UX).
- **Precision neutral/↑**: A10 adds a small FP risk (some pure nightlife "night out" posts might slip through if they mention food words). However the ±1-hour dedup + location checks further filter bad events downstream.

**Command:** `cd backend && venv/bin/python audit_classifier.py`

Re-audit output should be saved as a new entry in the audit table above with date, metrics, and notes.

### 2. A12 — OCR Improvement

Add adaptive thresholding fallback in `image_text_extractor.py`:
- When first Tesseract pass returns < 20 chars → re-run with `PIL.ImageOps.autocontrast` + binary threshold
- Targets: styled schedule graphics on gradient/photo backgrounds (Arts Soc Week 6 IMG_3966 style)
- Zero regression risk: only activates on low-yield images

### 3. Phase B2 — Decision Logging

Add per-post classification decision logging to `Event.extracted_data` JSONB:
- `stage_reached`: which filter fired (or "accepted")
- `llm_called`: bool
- `llm_food`: bool | null
- Enables admin audit trail without schema change

### 4. Phase B4 — Admin Stats Endpoint

`GET /admin/nlp-stats` → `{borderline_rate, llm_call_count, llm_accept_rate}` over last N scrape runs. Pulls from `Event.extracted_data` JSONB.

### 5. Phase B3 — Convert to pytest

Migrate `backend/test_extractor.py` from ad-hoc runner to `pytest` with proper fixtures in `tests/nlp/test_classifier.py`. Enables `pytest -v` with pass/fail per test, CI integration, and easy parameterised test cases.

### 6. Keyword Gaps

Low-risk additions worth making before next audit:
- `"baked goods"`, `"goodies"` → add to `weak_food_keywords` (require context modifier)
- `"acai bowl"`, `"açaí bowl"` → add to `weak_food_keywords`

---

## Key Files

| File | Role |
|------|------|
| `backend/app/services/nlp/extractor.py` | Main classifier + structured extractor. `classify_event()`, `extract_event()`, `segment_post_text()`, `get_classification_details()` |
| `backend/app/services/ocr/image_text_extractor.py` | Tesseract OCR — accepts list of URLs, merges output, PSM 11 |
| `backend/app/services/nlp/date_parser.py` | Regex date extraction |
| `backend/app/services/nlp/time_parser.py` | Regex time extraction (no TBC handling — B5 in extractor.py handles skip) |
| `backend/app/services/nlp/llm_classifier.py` | GPT-4o-mini fallback, Redis-cached 7 days |
| `backend/app/workers/scraping_tasks.py` | Celery task: scrape → OCR → NLP → multi-event loop → save → notify |
| `backend/app/workers/notification_tasks.py` | Celery task: email eligible users, batch per scrape run |
| `backend/app/services/notifications/brevo.py` | Brevo email service |
| `backend/app/core/config.py` | Env-var settings, feature flags |
| `backend/app/db/models.py` | SQLAlchemy models |
| `backend/app/api/v1/endpoints/admin.py` | Admin API — note: uses own NLP path (does not use segmentation yet) |
| `backend/test_extractor.py` | 90-test regression suite (67 classify_event + 4 B5 + 4 A11 + 15 screenshot). Run: `cd backend && venv/bin/python test_extractor.py` |
| `backend/audit_classifier.py` | LLM-based audit of full post history (silver-standard eval, GPT-4o-mini as judge) |
| `backend/audit_report.txt` | Last audit results (Phase A, 707 posts) |
| `backend/Important posts/` | 17 reference screenshots (IMG_3965–3991) used to build real-world regression tests |
