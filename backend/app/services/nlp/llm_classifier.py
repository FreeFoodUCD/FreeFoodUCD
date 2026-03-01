import base64
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional

import httpx
import redis as redis_lib

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini prompt (Phase E — Gemini-first, date-aware, dual-source cross-check)
# ---------------------------------------------------------------------------

# The prompt template has two dynamic slots injected per-call:
#   {today_line}     e.g. "Today is Sunday 1 March 2026."
#   {post_date_line} e.g. "This post was published on Sunday 1 March 2026."
_GEMINI_SYSTEM_PROMPT_TEMPLATE = """You analyse Instagram posts from UCD (University College Dublin) student society accounts.

{today_line}
{post_date_line}

Your task: determine if this post announces an UPCOMING event where FREE food or drinks will be provided to students at UCD Belfield campus.

ALWAYS reply with valid JSON only — no prose, no markdown, no explanation.

=== ACCEPT CRITERIA (ALL must be true) ===
- Free food or drinks are EXPLICITLY mentioned (not just implied by event type)
- The event is upcoming (not a past recap)
- The event is at UCD Belfield campus (or location unspecified — assume on-campus)
- Food/drinks are provided at no cost to attendees

=== SOCIETY MEMBERSHIP CONTEXT ===
UCD students join societies at Freshers Fair for €2/year. "Members only" events are
therefore open to virtually all UCD students. ACCEPT these events and set "members_only": true
so the app can display a badge. Only REJECT if a separate ticket/admission price is required
beyond the standard €2 society membership.

=== HARD REJECT (return {{"food": false}} immediately if ANY apply) ===
- Food is SOLD (bake sale, cake sale, fundraiser, raffle)
- Ticket or admission price required to attend (e.g. "tickets €10", "€15 entry")
- Event is at another college (Trinity, DCU, Maynooth, UCC, UL, NUIG)
- Event is at an off-campus venue (pub, bar, nightclub, Dundrum, Grafton Street, Temple Bar)
- Event is a nightlife event (ball, pub crawl, club night, pre-drinks, formal)
- Event is a social-media giveaway (enter to win, follow to win, prize draw)
- Event is a religious/faith community event (Ramadan iftar, Eid celebration, Suhoor)
- Event is staff/committee only (exec meeting, committee only)
- Post is a past-event recap ("thanks for coming", "what a night", "recap of last week")
- Food is only mentioned as a cooking/baking activity (baking class, cooking competition)

=== FOOD EVIDENCE ===
STRONG (sufficient alone to accept):
  pizza, refreshments, cookies, cake, snacks, sandwiches, sushi, curry, soup, pasta,
  tacos, burgers, croissants, pastries, pancakes, waffles, donuts, chocolate, biscuits,
  popcorn, nachos, crisps, ice cream, brunch, buffet, catering, coffee morning, tea morning,
  hot chocolate, kaffeeklatsch, free samples, handing out samples, food provided,
  food will be provided, complimentary food, welcome reception, freshers fair, treats,
  light bites, grub, munchies, sweet treats

WEAK (only accept if ALSO paired with: free, provided, complimentary, included, on us,
  on the house, kindly sponsored, brought to you by, at no cost, at no charge, for free):
  food, lunch, dinner, breakfast, drinks, drink, snack, tea, coffee, goodies, acai bowl

=== DATE & TIME EXTRACTION ===
Use today's date and the post publication date to resolve relative references:
- "this Friday" → calculate the actual date of the next Friday from today
- "next Tuesday" → calculate the actual date of the next Tuesday
- "tomorrow" → today + 1 day
- "tonight" → today

IMPORTANT DATE RULES:
- If a specific date or day is mentioned, return it as a full ISO 8601 datetime
- If NO specific date is mentioned ("soon", "this week", "coming up"), return start_datetime: null
- If a time is mentioned but NO date, return start_datetime: null (date unknown)
- Do NOT invent a date. "Soon", "this week", "coming up" are NOT specific dates.
- If only a date is mentioned (no time), use T12:00:00 as a placeholder time

=== MEMBERS ONLY DETECTION ===
Set "members_only": true if the post explicitly restricts attendance to society members
(e.g. "members only", "for members", "members are welcome", "sign up required").
Set "members_only": false if the event is open to all students or no restriction is mentioned.
A €2 society membership fee does NOT make an event members-only.

=== OUTPUT FORMAT ===
If food event:
{{
  "food": true,
  "title": "<short event name max 60 chars, from image or caption>",
  "start_datetime": "<ISO 8601 e.g. 2026-03-06T18:00:00, or null if no specific date/time>",
  "end_datetime": "<ISO 8601 or null>",
  "location": "<canonical UCD location from list below, or null>",
  "image_text": "<key text read from image if images provided, else null>",
  "members_only": false
}}

If NOT a food event:
{{"food": false}}

=== CANONICAL UCD LOCATIONS (use ONLY these exact names, or null) ===
Newman Building, Student Centre, Engineering & Materials Science Centre,
O'Brien Centre for Science, James Joyce Library, Sutherland School of Law,
Lochlann Quinn School of Business, Agriculture & Food Science Centre,
Health Sciences Centre, Veterinary Sciences Centre, Computer Science & Informatics Centre,
Daedalus Building, Confucius Institute, Hanna Sheehy-Skeffington Building,
Tierney Building, Newstead Building, Richview School of Architecture,
NovaUCD, Conway Institute, Geary Institute, O'Reilly Hall, The Pavilion,
UCD Sports Centre, Roebuck Hall, UCD Village, UCD Belfield

Student Centre rooms — use "Student Centre" as location:
  Harmony Studio, Blue Room, Red Room, FitzGerald Chamber, Astra Hall,
  UCD Cinema, Brava Lounge, Meeting Room 5/6/7, Atrium, Global Lounge,
  Newman Basement, Newstead Atrium

Common aliases to map:
  "Newman" / "Arts Block" / "Arts Building" → Newman Building
  "Science Building" / "O'Brien" → O'Brien Centre for Science
  "Engineering Building" / "Eng" → Engineering & Materials Science Centre
  "Business School" / "Quinn" → Lochlann Quinn School of Business
  "Vet School" → Veterinary Sciences Centre
  "Library" / "JJ" → James Joyce Library
  "Harmony" / "Harmony Studio" → Student Centre
  "Village" / "The Village" → UCD Village
  "Belfield" / "UCD" / "campus" → UCD Belfield

=== EXAMPLES ===
Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "Join us for free pizza in Newman Building at 1pm this Friday!"
→ {{"food": true, "title": "Free Pizza", "start_datetime": "2026-03-06T13:00:00", "end_datetime": null, "location": "Newman Building", "image_text": null, "members_only": false}}

Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "Tickets €15 — our annual charity ball is this Friday!"
→ {{"food": false}}

Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "Coffee morning ☕ — come chat with us in Harmony Studio, 10am–12pm this Tuesday"
→ {{"food": true, "title": "Coffee Morning", "start_datetime": "2026-03-03T10:00:00", "end_datetime": "2026-03-03T12:00:00", "location": "Student Centre", "image_text": null, "members_only": false}}

Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "Win a box of chocolates! Follow us and tag a friend to enter 🎉"
→ {{"food": false}}

Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "Free pizza in Newman sometime next week!"
→ {{"food": true, "title": "Free Pizza", "start_datetime": null, "end_datetime": null, "location": "Newman Building", "image_text": null, "members_only": false}}

Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "Ramadan Iftar dinner — all Muslim students welcome, free food provided"
→ {{"food": false}}

Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "Members only — free pizza for Eng Soc members in Engineering Building, Thursday 6pm"
→ {{"food": true, "title": "Free Pizza for Members", "start_datetime": "2026-03-05T18:00:00", "end_datetime": null, "location": "Engineering & Materials Science Centre", "image_text": null, "members_only": true}}

Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "Come join us! 🎉" [Image shows: FREE PIZZA 6PM THURSDAY NEWMAN BUILDING]
→ {{"food": true, "title": "Free Pizza", "start_datetime": "2026-03-05T18:00:00", "end_datetime": null, "location": "Newman Building", "image_text": "FREE PIZZA 6PM THURSDAY NEWMAN BUILDING", "members_only": false}}

Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "Free entry to our gig — food and drinks available at the bar (not free)"
→ {{"food": false}}

Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "What a deadly night last week 🍕 — this week join us for free sushi, Wednesday 7pm, Student Centre!"
→ {{"food": true, "title": "Free Sushi Night", "start_datetime": "2026-03-04T19:00:00", "end_datetime": null, "location": "Student Centre", "image_text": null, "members_only": false}}

Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "Kaffeeklatsch ☕ — free coffee and cake, Tuesday 11am, Harmony Studio"
→ {{"food": true, "title": "Kaffeeklatsch", "start_datetime": "2026-03-03T11:00:00", "end_datetime": null, "location": "Student Centre", "image_text": null, "members_only": false}}

Today is Sunday 1 March 2026. Post published Sunday 1 March 2026.
Caption: "Bake sale this Friday — all proceeds to charity! Also free pizza for volunteers 🍕"
→ {{"food": true, "title": "Volunteer Pizza", "start_datetime": "2026-03-06T12:00:00", "end_datetime": null, "location": null, "image_text": null, "members_only": false}}
"""

_CACHE_VERSION = "v2"        # bump whenever the prompt changes — auto-invalidates old keys
_CACHE_TTL = 24 * 3600       # 24h — posts older than 24h are filtered out anyway


# ---------------------------------------------------------------------------
# Gemini classifier (Phase E — primary classifier, date-aware)
# ---------------------------------------------------------------------------

class GeminiClassifier:
    """
    Gemini Flash classifier — primary classifier for all posts.
    Single call returns {food, title, start_datetime, end_datetime, location, image_text, members_only}.
    Uses Gemini 2.0 Flash free tier (1,500 req/day — sufficient for current volume).
    Redis-cached 7 days (keyed by caption + image URLs + today's date).
    Today's date is injected into the prompt so Gemini can resolve relative dates.
    """

    def __init__(self, api_key: str, redis_url: str):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._genai = genai
            # Model is created per-call with dynamic system instruction (date injection)
            self._api_key = api_key
        except ImportError:
            raise ImportError(
                "google-generativeai package not installed. "
                "Run: pip install google-generativeai>=0.8.0"
            )
        self._redis = redis_lib.from_url(redis_url, decode_responses=False)

        # F1: Langfuse observability — graceful degradation if SDK absent or keys missing.
        # Never blocks classification; all Langfuse calls are wrapped in try/except.
        self._langfuse = None
        try:
            from langfuse import Langfuse
            if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
                self._langfuse = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST,
                )
                logger.info("Langfuse observability enabled")
            else:
                logger.debug("Langfuse keys not set — observability disabled")
        except ImportError:
            logger.debug("langfuse package not installed — observability disabled")
        except Exception as lf_exc:
            logger.warning(f"Langfuse init failed (non-fatal): {lf_exc}")

    def classify_and_extract(
        self,
        text: str,
        image_urls: Optional[list] = None,
        post_timestamp: Optional[datetime] = None,
    ) -> Optional[dict]:
        """
        Classify + extract in one call. Accepts caption text + optional image URLs (up to 3).
        Returns {food, title, start_datetime, end_datetime, location, image_text, members_only}
        or None on API failure.

        post_timestamp: when the post was published (used for date context injection).
        Redis-cached 7 days. Cache key includes today's date so stale date context
        doesn't persist across days.
        """
        import google.generativeai as genai

        image_urls = image_urls or []
        now = datetime.now()
        today_str = now.strftime('%A %-d %B %Y')  # e.g. "Sunday 1 March 2026"

        if post_timestamp:
            post_date_str = post_timestamp.strftime('%A %-d %B %Y')
        else:
            post_date_str = today_str

        # Cache key includes today's date so relative date resolution stays fresh.
        # _CACHE_VERSION prefix means prompt changes auto-invalidate all cached results.
        cache_input = text + "|".join(sorted(image_urls)) + now.strftime('%Y-%m-%d')
        cache_key = f"llm_gemini_{_CACHE_VERSION}:{hashlib.sha256(cache_input.encode()).hexdigest()[:16]}"

        # Cache read
        was_cache_hit = False
        try:
            cached = self._redis.get(cache_key)
            if cached is not None:
                logger.debug("Gemini cache hit")
                was_cache_hit = True
                return json.loads(cached)
        except Exception:
            pass

        # Build system prompt with today's date injected
        system_prompt = _GEMINI_SYSTEM_PROMPT_TEMPLATE.format(
            today_line=f"Today is {today_str}.",
            post_date_line=f"This post was published on {post_date_str}.",
        )

        # Build caption — first 1000 + last 400 chars to capture hashtags/details at end
        if len(text) <= 1500:
            caption_for_gemini = text
        else:
            caption_for_gemini = text[:1000] + "\n...\n" + text[-400:]
        parts: list = [f"Caption: {caption_for_gemini}"]

        # Attach images as inline_data (base64) — NOT file_uri which requires GCS URIs.
        # Instagram CDN URLs are plain HTTPS; we download and encode them here.
        for url in image_urls[:3]:
            try:
                resp = httpx.get(url, timeout=8, follow_redirects=True)
                resp.raise_for_status()
                mime = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                b64 = base64.b64encode(resp.content).decode("utf-8")
                parts.append({"inline_data": {"mime_type": mime, "data": b64}})
                logger.debug(f"Attached image ({len(resp.content)} bytes, {mime}): {url[:60]}")
            except Exception as img_exc:
                logger.debug(f"Skipping image {url}: {img_exc}")

        try:
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=system_prompt,
            )
            response = model.generate_content(
                parts,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0,
                    max_output_tokens=200,
                ),
            )
            result = json.loads(response.text)
            logger.info(
                f"Gemini classified post: food={result.get('food')}, "
                f"title={result.get('title')!r}, "
                f"start_datetime={result.get('start_datetime')}, "
                f"location={result.get('location')}, "
                f"members_only={result.get('members_only')}"
            )
        except Exception as exc:
            logger.warning(f"Gemini classifier unavailable: {exc}")
            return None

        # Cache write (non-fatal)
        try:
            self._redis.setex(cache_key, _CACHE_TTL, json.dumps(result))
        except Exception:
            pass

        # F1: Langfuse trace — record every Gemini call for observability.
        # Wrapped in try/except so a Langfuse outage never breaks classification.
        if self._langfuse and not was_cache_hit:
            try:
                trace = self._langfuse.trace(
                    name="gemini_classify",
                    input={
                        "caption_preview": text[:200],
                        "image_count": len(image_urls),
                    },
                    output=result,
                    metadata={
                        "food_detected": result.get("food") if result else None,
                        "has_datetime": bool(result.get("start_datetime")) if result else False,
                        "has_location": bool(result.get("location")) if result else False,
                        "cache_hit": False,
                        "post_date": post_date_str,
                    },
                )
                self._langfuse.generation(
                    trace_id=trace.id,
                    name="gemini_flash",
                    model="gemini-2.0-flash",
                    input={
                        "system_preview": system_prompt[:300],
                        "caption_preview": str(parts[0])[:300] if parts else "",
                    },
                    output=result,
                    usage={"input": 0, "output": 0},  # Gemini SDK doesn't expose token counts
                )
            except Exception as lf_exc:
                logger.debug(f"Langfuse trace failed (non-fatal): {lf_exc}")

        return result


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_instance: Optional[GeminiClassifier] = None


def get_llm_classifier() -> Optional[GeminiClassifier]:
    """
    Lazy singleton — returns GeminiClassifier if GEMINI_API_KEY is set, else None.
    USE_GEMINI flag acts as a master kill switch (False = no LLM at all).
    """
    global _instance
    if _instance is None:
        if settings.USE_GEMINI and settings.GEMINI_API_KEY:
            try:
                _instance = GeminiClassifier(
                    api_key=settings.GEMINI_API_KEY,
                    redis_url=settings.REDIS_URL,
                )
                logger.info("LLM provider: Gemini Flash (Phase E — Gemini-first)")
            except Exception as exc:
                logger.error(f"Failed to initialise GeminiClassifier: {exc}")
    return _instance

# Made with Bob
