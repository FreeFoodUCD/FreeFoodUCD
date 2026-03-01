"""
EventExtractor — Phase E (Gemini-first, dual-source cross-check)

Architecture:
  1. Hard filters (fast regex) — paid/nightlife/off-campus/religious/other-college
  2. Gemini classify_and_extract() — primary classifier + full extraction
  3. _reconcile_datetime() — cross-check Gemini datetime against regex evidence
  4. _extract_location() — canonicalize Gemini's location string via alias dict
  5. Past-date validation + TBC skip

Deleted from Phase D:
  - classify_event() (11-gate rule-based classifier)
  - _try_llm_fallback() (grey-zone routing logic)
  - _has_explicit_food() / _has_weak_food_only() / _food_is_negated()
  - _is_past_tense_post() / _is_food_activity() / _is_giveaway_contest()
  - _is_staff_only() / _is_online_event()
  - _generate_title() (Gemini returns title directly)
  - _is_members_only() (Gemini returns members_only directly)
  - _preprocess_text() (Gemini handles raw text natively)
  - _combine_datetime() (replaced by ISO parse)
  - _FOOD_EMOJI_MAP (Gemini understands emojis natively)
  - All strong/weak food keyword lists
  - TimeParser (Gemini returns time; regex used only as cross-check)
  - DateParser (Gemini resolves dates; regex used only as cross-check)
"""

import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Tuple

import pytz

from app.core.config import settings

logger = logging.getLogger(__name__)

UTC = timezone.utc

# ---------------------------------------------------------------------------
# Regex patterns for cross-check validation
# ---------------------------------------------------------------------------

# Evidence that a specific date is mentioned in the text.
# Must be a concrete day/date reference — NOT vague words like "soon", "this week".
_DATE_EVIDENCE_RE = re.compile(
    r'\b('
    r'monday|tuesday|wednesday|thursday|friday|saturday|sunday|'
    r'mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun|'
    r'today|tomorrow|tonight|'
    r'\d{1,2}(?:st|nd|rd|th)\b'         # ordinal day numbers (must have suffix)
    r'|\d{1,2}[/\-]\d{1,2}'             # DD/MM or DD-MM
    r'|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*'  # "17 Feb"
    r')\b',
    re.IGNORECASE,
)

# Evidence that a specific time is mentioned in the text
_TIME_EVIDENCE_RE = re.compile(
    r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b'   # 1pm, 1:30pm
    r'|\b\d{1,2}:\d{2}\b'                    # 13:00
    r'|\b(?:noon|midnight)\b'
    r'|\bhalf\s+(?:past\s+)?\d{1,2}\b'       # half five, half past 5
    r'|\bquarter\s+(?:past|to)\s+\d{1,2}\b', # quarter past 3
    re.IGNORECASE,
)


class EventExtractor:
    """
    Gemini-first event extractor.
    Gemini is the primary classifier and extractor.
    Regex parsers are used only as cross-check validators for datetime.
    """

    def __init__(self):
        self.timezone = pytz.timezone('Europe/Dublin')
        self.building_aliases = self._load_building_aliases()
        # sorted longest-first so specific matches beat short ones
        self.ucd_buildings = sorted(self.building_aliases.keys(), key=len, reverse=True)
        self.other_colleges = self._load_other_colleges()
        self.off_campus_venues = self._load_off_campus_venues()
        self.nightlife_keywords = self._load_nightlife_keywords()

        # Named rooms within Student Centre
        self.student_centre_rooms = {
            'blue room': 'Blue Room',
            'red room': 'Red Room',
            'fitzgerald chamber': 'FitzGerald Chamber',
            'fitzgerald': 'FitzGerald Chamber',
            'meeting room 5': 'Meeting Room 5',
            'meeting room 6': 'Meeting Room 6',
            'meeting room 7': 'Meeting Room 7',
            'harmony studio': 'Harmony Studio',
            'harmony': 'Harmony Studio',
            'astra hall': 'Astra Hall',
            'ucd cinema': 'UCD Cinema',
            'brava lounge': 'Brava Lounge',
            'atrium': 'Atrium',
            'main foyer': 'Main Foyer',
            'clubhouse bar': 'Clubhouse Bar',
            'clubhouse': 'Clubhouse Bar',
            "o'neill lounge": "O'Neill Lounge",
            'oneill lounge': "O'Neill Lounge",
            'global lounge': 'Global Lounge',
            'newman basement': 'Newman Basement',
            'newstead atrium': 'Newstead Atrium',
        }
        self.student_centre_rooms_sorted = sorted(
            self.student_centre_rooms.keys(), key=len, reverse=True
        )

        # Named rooms within UCD Village
        self.village_rooms = {
            'village auditorium': 'Auditorium',
            'auditorium': 'Auditorium',
            'village kitchen': 'Kitchen',
            'ucd village kitchen': 'Kitchen',
        }
        self.village_rooms_sorted = sorted(
            self.village_rooms.keys(), key=len, reverse=True
        )

    # ── Hard filters ─────────────────────────────────────────────────────────

    # Soft-filter hints: patterns that don't hard-reject but inject a clarifying
    # note into the Gemini prompt so it can make a more informed decision.
    _SOFT_FILTER_HINTS: dict = {
        r'\bbake\s+sale\b': (
            "Note: post mentions 'bake sale' — only accept if free food is ALSO "
            "explicitly offered alongside the sale (e.g. 'free pizza for volunteers')."
        ),
        r'\bcake\s+sale\b': (
            "Note: post mentions 'cake sale' — only accept if free samples or free "
            "food are explicitly offered in addition to the sale."
        ),
    }

    def _passes_hard_filters(self, text: str) -> tuple:
        """
        Fast pre-filter before calling Gemini.
        Returns (passes: bool, rejection_reason: str).
        rejection_reason is '' when the post passes.

        These are high-precision, low-recall checks — they only fire on
        unambiguous signals (explicit ticket language, named off-campus venues, etc.)
        Audit-logged at INFO level so rejections are queryable in Railway logs.
        """
        text_lower = text.lower()
        if self._is_paid_event(text_lower):
            logger.info(f"HARD_FILTER_REJECT:paid_event | {text[:80]!r}")
            return False, "paid_event"
        if self._is_nightlife_event(text_lower):
            logger.info(f"HARD_FILTER_REJECT:nightlife | {text[:80]!r}")
            return False, "nightlife"
        if self._is_off_campus(text_lower):
            logger.info(f"HARD_FILTER_REJECT:off_campus | {text[:80]!r}")
            return False, "off_campus"
        if self._is_other_college(text_lower):
            logger.info(f"HARD_FILTER_REJECT:other_college | {text[:80]!r}")
            return False, "other_college"
        if self._is_religious_event(text_lower):
            logger.info(f"HARD_FILTER_REJECT:religious | {text[:80]!r}")
            return False, "religious"
        return True, ""

    def _is_paid_event(self, text: str) -> bool:
        """
        Return True only if the event is clearly a paid-access event.
        Small amounts (≤€5) without explicit ticket language are NOT rejected.
        Membership context with reasonable price (≤€5) is always allowed.
        """
        # Free overrides
        free_overrides = [
            r'\bfree\s+(?:of\s+)?(?:charge|cost|entry|admission)\b',
            r'\bno\s+(?:entry\s+)?(?:fee|cost|charge)\b',
            r'\bno\s+tickets?\s+(?:needed|required)\b',
            r"(?:don'?t|do\s+not|doesn'?t|does\s+not)\s+(?:need\s+to\s+)?pay\b",
            r'\bno\s+(?:need\s+to\s+)?pay\b',
            r'\bno\s+charge\b',
            r'\bfree\s+(?:event|to\s+attend|for\s+all|for\s+everyone)\b',
            r'\bcompletely\s+free\b',
            r'\b(?:this\s+is\s+(?:a\s+)?free|it\s+is\s+free)\b',
        ]
        for pattern in free_overrides:
            if re.search(pattern, text):
                return False

        # Membership context — allow any price ≤€5
        is_member_context = bool(re.search(r'\b(?:membership|ucard)\b', text))
        euro_amounts = [int(x) for x in re.findall(r'€(\d+)', text)]
        if is_member_context and euro_amounts and all(a <= 5 for a in euro_amounts):
            return False

        # Explicit ticket / admission language → always paid
        has_ticket_language = bool(re.search(
            r'(?:'
            r'\b(?:buy|get|purchase|book|grab|order)\s+(?:your\s+)?tickets?\b'
            r'|\btickets?\s+(?:are\s+)?(?:available|on\s+sale|priced|cost)\b'
            r'|\btickets?:'
            r'|\btickets?\s+(?:can\s+be\s+)?(?:purchased|sold|bought)\b'
            r'|\bticket\s+prices?\b'
            r'|\b(?:reduced|early.bird|vip)\s+ticket\b'
            r'|\badmission\b'
            r'|\bentry\s+fee\b'
            r')',
            text
        ))
        if has_ticket_language:
            return True

        # Large price (≥€10) without explicit free-food statement → paid
        if euro_amounts and max(euro_amounts) >= 10:
            has_free_food_stated = bool(re.search(
                r'\bfree\s+(?:food|pizza|lunch|dinner|snacks?|refreshments?|drinks?|coffee|tea|breakfast)\b',
                text
            ))
            if not has_free_food_stated:
                return True

        # Food-sale keywords — 'bake sale' and 'cake sale' moved to soft filters
        # (they can co-exist with free food; Gemini decides with a hint injected)
        food_sale_keywords = [
            'cookie sale', 'food sale', 'food stall',
            'fundraiser', 'charity sale', 'charity bake',
        ]
        for keyword in food_sale_keywords:
            if keyword in text:
                return True

        return False

    def _is_nightlife_event(self, text: str) -> bool:
        """Check if text indicates a nightlife event."""
        for keyword in self.nightlife_keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                return True
        return False

    # Venues that need word-boundary matching (short words that appear in other contexts).
    # 'bar' removed — too many false positives: "chocolate bar", "granola bar", "bar of soap".
    # 'bar' is only rejected when it appears as a standalone venue word via _is_off_campus logic.
    _BOUNDARY_VENUES = {'pub', 'grill', 'diner', 'tavern', 'brewery'}

    def _is_off_campus(self, text: str) -> bool:
        """
        Check if text mentions off-campus venues.
        Skip check if a known UCD building is already mentioned — on-campus wins.
        """
        if self._has_ucd_location(text):
            return False
        for venue in self.off_campus_venues:
            if venue in self._BOUNDARY_VENUES:
                if re.search(r'\b' + re.escape(venue) + r'\b', text):
                    return True
            else:
                if venue in text:
                    return True
        return False

    def _is_other_college(self, text: str) -> bool:
        """Check if text mentions other Irish colleges."""
        for college in self.other_colleges:
            if len(college) <= 4:
                if re.search(r'\b' + re.escape(college) + r'\b', text):
                    return True
            else:
                if college in text:
                    return True
        return False

    def _is_religious_event(self, text: str) -> bool:
        """Reject religious/faith-community events."""
        patterns = [
            r'\biftar\b', r'\brahman\b', r'\bramadan\b',
            r'\beid\b', r'\bsuhoor\b', r'\bsahoor\b',
            r'\bfriday\s+prayer\b', r'\bjumu\'?ah\b',
            r'\bchurch\s+service\b',
            # "mass" alone is too broad — blocks "mass catering", "en masse", "mass email".
            # Only reject when used in a clearly religious context:
            #   "sunday mass", "going to mass", "attend mass", "after mass"
            r'\bsunday\s+mass\b',
            r'\b(?:going\s+to|attend(?:ing)?|after|before|at)\s+mass\b',
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_ucd_location(self, text: str) -> bool:
        """Return True if text contains a known UCD building name."""
        for alias in self.ucd_buildings:
            if len(alias) <= 4:
                if re.search(r'\b' + re.escape(alias) + r'\b', text):
                    return True
            else:
                if alias in text:
                    return True
        return False

    # ── Datetime reconciliation ───────────────────────────────────────────────

    def _reconcile_datetime(
        self,
        gemini_start: Optional[str],
        gemini_end: Optional[str],
        text: str,
        post_timestamp: Optional[datetime],
    ) -> Tuple[Optional[datetime], Optional[datetime], float]:
        """
        Cross-check Gemini's datetime against text evidence.

        Returns (start_dt, end_dt, confidence_modifier).

        Rules:
        1. Parse Gemini's ISO datetime strings
        2. Reject if in the past (>1h grace)
        3. Reject if >30 days in the future (suspiciously far)
        4. Reject date component if no date evidence in text
        5. Strip time component if no time evidence in text (use noon as default)
        6. Cross-check with regex parsers; if they agree → confidence 1.0
        """
        now_utc = datetime.now(UTC)
        now_local = datetime.now(self.timezone)
        ref = post_timestamp or now_utc

        has_date_evidence = bool(_DATE_EVIDENCE_RE.search(text))
        has_time_evidence = bool(_TIME_EVIDENCE_RE.search(text))

        def _parse_iso(s: Optional[str]) -> Optional[datetime]:
            if not s:
                return None
            try:
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = self.timezone.localize(dt)
                return dt
            except (ValueError, TypeError):
                return None

        # Use the config value; fall back to 30 if settings is mocked or misconfigured.
        # NOTE: int(MagicMock()) returns 1 (MagicMock.__int__ default), so we must
        # check isinstance before casting.
        _raw = getattr(settings, 'GEMINI_MAX_FUTURE_DAYS', 30)
        max_future_days = _raw if isinstance(_raw, int) else 30

        # Track whether Gemini's datetime was explicitly in the past.
        # If so, the post is about a past event — do NOT fall back to regex
        # (DateParser resolves bare weekday names like "Friday" to the *next*
        # occurrence, which would create a false future event).
        gemini_raw_dt = _parse_iso(gemini_start)
        gemini_is_past = (
            gemini_raw_dt is not None
            and gemini_raw_dt < now_utc - timedelta(hours=1)
        )

        def _validate(dt: Optional[datetime]) -> Optional[datetime]:
            if dt is None:
                return None
            # Reject past events (>1h grace for "happening now")
            if dt < now_utc - timedelta(hours=1):
                logger.debug(f"Datetime {dt} is in the past — rejected")
                return None
            # Reject suspiciously far future
            if dt > now_utc + timedelta(days=max_future_days):
                logger.debug(f"Datetime {dt} is >{max_future_days} days out — rejected")
                return None
            # Reject if no date evidence in text
            if not has_date_evidence:
                logger.debug("Gemini returned datetime but no date evidence in text — rejected")
                return None
            # Strip time if no time evidence
            if not has_time_evidence:
                dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)
            return dt

        gemini_start_dt = _validate(_parse_iso(gemini_start))
        gemini_end_dt = _validate(_parse_iso(gemini_end))

        # If Gemini explicitly returned a past datetime, reject entirely.
        # Don't fall back to regex — the post is about a past event.
        # Use confidence=-1.0 as a sentinel so extract_event() can distinguish
        # "past event" (reject whole post) from "no datetime found" (keep post, start_time=None).
        if gemini_is_past:
            logger.debug("Gemini datetime was past — rejecting post entirely (no regex fallback)")
            return None, None, -1.0

        # Cross-check with regex parsers (use same window as Gemini validation)
        regex_date = self._regex_parse_date(text, ref, max_future_days=max_future_days)
        regex_time = self._regex_parse_time(text)

        # Determine confidence
        if gemini_start_dt and regex_date:
            # Both found a date — check agreement (within 1 day)
            if abs((gemini_start_dt.date() - regex_date.date()).days) <= 1:
                confidence = 1.0  # agreement
            else:
                # Disagreement — trust regex date, use Gemini's time if available
                logger.debug(
                    f"Date disagreement: Gemini={gemini_start_dt.date()}, "
                    f"regex={regex_date.date()} — trusting regex"
                )
                if regex_time and has_time_evidence:
                    gemini_start_dt = self.timezone.localize(
                        regex_date.replace(
                            hour=regex_time['hour'],
                            minute=regex_time['minute'],
                            second=0, microsecond=0,
                            tzinfo=None,
                        )
                    )
                else:
                    gemini_start_dt = self.timezone.localize(
                        regex_date.replace(tzinfo=None)
                    )
                gemini_end_dt = None
                confidence = 0.85
        elif gemini_start_dt:
            confidence = 0.75  # Gemini only
        elif regex_date and has_date_evidence:
            # Regex found date, Gemini didn't — use regex only if text has evidence
            # Also apply the same plausibility window as Gemini validation
            regex_dt_candidate = self.timezone.localize(regex_date.replace(tzinfo=None))
            if regex_dt_candidate > now_utc + timedelta(days=max_future_days):
                logger.debug(f"Regex date {regex_dt_candidate.date()} is >{max_future_days} days out — rejected")
                confidence = 0.0
            else:
                if regex_time and has_time_evidence:
                    gemini_start_dt = self.timezone.localize(
                        regex_date.replace(
                            hour=regex_time['hour'],
                            minute=regex_time['minute'],
                            second=0, microsecond=0,
                            tzinfo=None,
                        )
                    )
                else:
                    gemini_start_dt = self.timezone.localize(
                        regex_date.replace(tzinfo=None)
                    )
                gemini_end_dt = None
                confidence = 0.85
        else:
            confidence = 0.0  # no datetime found

        return gemini_start_dt, gemini_end_dt, confidence

    def _regex_parse_date(
        self, text: str, post_timestamp: Optional[datetime], max_future_days: int = 30
    ) -> Optional[datetime]:
        """Thin wrapper — use DateParser for cross-check.
        max_future_days is passed through so DateParser uses the same plausibility
        window as _reconcile_datetime (default 30 days, matching GEMINI_MAX_FUTURE_DAYS).
        """
        try:
            from app.services.nlp.date_parser import DateParser
            dp = DateParser(self.timezone, max_future_days=max_future_days)
            return dp.parse_date(text.lower(), post_timestamp)
        except Exception:
            return None

    def _regex_parse_time(self, text: str) -> Optional[Dict]:
        """Thin wrapper — use TimeParser for cross-check."""
        try:
            from app.services.nlp.time_parser import TimeParser
            tp = TimeParser()
            result = tp.parse_time_range(text.lower())
            return result['start'] if result else None
        except Exception:
            return None

    # ── Location extraction ───────────────────────────────────────────────────

    def _extract_location(self, text: str) -> Optional[Dict]:
        """
        Extract and canonicalize location from text.
        Checks Student Centre rooms first, then building aliases.
        Returns {building, room, full_location} or None.
        """
        if not text:
            return None
        text_lower = text.lower().strip()

        # Named Student Centre rooms — check before generic building scan
        for room_key in self.student_centre_rooms_sorted:
            if self._alias_in_text(room_key, text_lower):
                room_name = self.student_centre_rooms[room_key]
                return {
                    'building': 'Student Centre',
                    'room': room_name,
                    'full_location': f'{room_name}, Student Centre',
                }

        # Named UCD Village rooms
        for room_key in self.village_rooms_sorted:
            if self._alias_in_text(room_key, text_lower):
                room_name = self.village_rooms[room_key]
                return {
                    'building': 'UCD Village',
                    'room': room_name,
                    'full_location': f'{room_name}, UCD Village',
                }

        # Generic building scan (longest-first)
        for alias in self.ucd_buildings:
            if self._alias_in_text(alias, text_lower):
                building = self.building_aliases[alias]
                # Try to find a room code (e.g. E1.32, C204A, AD1.01, G01)
                room = self._extract_room_code(text_lower)
                if room:
                    return {
                        'building': building,
                        'room': room,
                        'full_location': f'{room}, {building}',
                    }
                return {
                    'building': building,
                    'room': None,
                    'full_location': building,
                }

        return None

    def _alias_in_text(self, alias: str, text: str) -> bool:
        """Match alias in text; use word boundaries for short aliases (≤4 chars)."""
        if len(alias) <= 4:
            return bool(re.search(r'\b' + re.escape(alias) + r'\b', text))
        return alias in text

    def _extract_room_code(self, text: str) -> Optional[str]:
        """
        Extract room codes like E1.32, C204A, AD1.01, G01, LG18, etc.
        Returns the room code string or None.
        """
        pattern = r'\b([A-Z]{1,3}\d{1,2}(?:\.\d{1,2})?[A-Z]?)\b'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None

    def segment_post_text(self, text: str) -> list:
        """
        Phase E stub — segmentation removed; Gemini handles multi-event posts natively.
        Returns the full text as a single segment (zero regression risk).
        Called by scraping_tasks.py for backwards compatibility.
        """
        return [text]

    # ── Main entry point ──────────────────────────────────────────────────────

    def extract_event(
        self,
        text: str,
        source_type: str = 'post',
        post_timestamp: Optional[datetime] = None,
        image_urls: Optional[list] = None,
        ocr_low_yield: bool = False,
    ) -> Optional[Dict]:
        """
        Extract event details from text using Gemini as primary classifier.

        Args:
            text: Combined Instagram caption + OCR text
            source_type: 'post' or 'story'
            post_timestamp: When the post was published (for date context)
            image_urls: Raw image URLs — passed to Gemini for vision analysis
            ocr_low_yield: Unused in Phase E (Gemini handles vision natively)

        Returns:
            Dictionary with event details or None if rejected
        """
        from app.services.nlp.llm_classifier import get_llm_classifier

        # Step 1: Hard filters — fast, high-precision, no LLM needed
        passes, reject_reason = self._passes_hard_filters(text)
        if not passes:
            return None

        # Step 2: TBC/TBA skip — society will post again with details
        _tbc_patterns = [r'\btbc\b', r'\btba\b', r'\bto\s+be\s+confirmed\b', r'\bto\s+be\s+announced\b']
        if any(re.search(p, text, re.IGNORECASE) for p in _tbc_patterns):
            logger.info("SKIP: Time/details TBC — deferred pending follow-up")
            return None

        # Step 2b: Soft filter hints — inject clarifying notes into Gemini prompt
        # for borderline patterns (bake sale, cake sale) rather than hard-rejecting.
        soft_hints = []
        for pattern, hint in self._SOFT_FILTER_HINTS.items():
            if re.search(pattern, text, re.IGNORECASE):
                soft_hints.append(hint)
        text_for_gemini = text
        if soft_hints:
            text_for_gemini = text + "\n\n[Classifier Hints]\n" + "\n".join(soft_hints)
            logger.info(f"Soft filter hints injected ({len(soft_hints)}): {soft_hints}")

        # Step 3: Gemini classify + extract
        if not settings.USE_GEMINI:
            logger.debug("USE_GEMINI=False — LLM disabled, rejecting post")
            return None

        llm = get_llm_classifier()
        if llm is None:
            logger.warning("No LLM classifier available — rejecting post")
            return None

        gemini_result = llm.classify_and_extract(
            text=text_for_gemini,
            image_urls=image_urls or [],
            post_timestamp=post_timestamp,
        )

        if not gemini_result or not gemini_result.get('food'):
            logger.debug("Gemini rejected post (food=false or API failure)")
            return None

        logger.info("ACCEPT: Gemini approved post")

        # Step 4: Inject image_text BEFORE datetime reconciliation so that
        # _DATE_EVIDENCE_RE and _TIME_EVIDENCE_RE can match dates/times from the image.
        # (e.g. caption is vague but flyer says "Thursday 5th March, 6pm")
        image_text = gemini_result.get('image_text')
        if image_text:
            text = f"{text}\n\n[Image Text]\n{image_text}"

        # Step 5: Reconcile datetime (Gemini + regex cross-check — now has image text)
        start_dt, end_dt, dt_confidence = self._reconcile_datetime(
            gemini_start=gemini_result.get('start_datetime'),
            gemini_end=gemini_result.get('end_datetime'),
            text=text,
            post_timestamp=post_timestamp,
        )

        # dt_confidence == -1.0 is a sentinel meaning Gemini returned an explicitly
        # past datetime — the post is a past-event recap, reject the whole event.
        if dt_confidence < 0:
            logger.debug("Past-event sentinel from _reconcile_datetime — rejecting post")
            return None

        # Step 6: Location — canonicalize Gemini's location string
        gemini_location_str = gemini_result.get('location')
        location = None
        if gemini_location_str:
            location = (
                self._extract_location(gemini_location_str)
                or {'building': gemini_location_str, 'room': None, 'full_location': gemini_location_str}
            )
        # Also try extracting from full text (catches room codes Gemini might miss)
        if location is None:
            location = self._extract_location(text)

        # Step 7: Title (from Gemini, truncated to 60 chars)
        title = (gemini_result.get('title') or 'Free Food Event')[:60].strip()

        # Step 8: Members-only (from Gemini)
        members_only = bool(gemini_result.get('members_only', False))

        # Step 9: Confidence score
        base_confidence = 1.0 if location else 0.8
        if dt_confidence > 0:
            confidence = base_confidence * ((1.0 + dt_confidence) / 2)
        else:
            confidence = base_confidence * 0.7  # no datetime found

        return {
            'title': title,
            'description': text[:500] if len(text) > 500 else text,
            'location': location.get('full_location') if location else None,
            'location_building': location.get('building') if location else None,
            'location_room': location.get('room') if location else None,
            'start_time': start_dt,
            'end_time': end_dt,
            'confidence_score': round(confidence, 2),
            'raw_text': text,
            'extracted_data': {
                'time_found': start_dt is not None,
                'date_found': start_dt is not None,
                'location_found': location is not None,
                'members_only': members_only,
                'llm_assisted': True,
                'llm_provider': 'gemini',
                'stage_reached': 'gemini',
                'llm_called': True,
                'llm_food': True,
                'dt_confidence': dt_confidence,
            }
        }

    # ── Data loaders ──────────────────────────────────────────────────────────

    def _load_building_aliases(self) -> Dict[str, str]:
        """Map every known alias (lowercase) to the official building name."""
        return {
            # Newman Building
            'newman building': 'Newman Building',
            'arts building': 'Newman Building',
            'the arts block': 'Newman Building',
            'arts block': 'Newman Building',
            'newman': 'Newman Building',

            # O'Brien Centre for Science
            "o'brien centre for science": "O'Brien Centre for Science",
            'obrien centre for science': "O'Brien Centre for Science",
            'obrien centre': "O'Brien Centre for Science",
            'the science building': "O'Brien Centre for Science",
            'science building': "O'Brien Centre for Science",
            'science centre': "O'Brien Centre for Science",
            "o'brien": "O'Brien Centre for Science",
            'obrien': "O'Brien Centre for Science",
            'science': "O'Brien Centre for Science",

            # James Joyce Library
            'james joyce library': 'James Joyce Library',
            'the library': 'James Joyce Library',
            'library': 'James Joyce Library',
            'jj': 'James Joyce Library',

            # Sutherland School of Law
            'sutherland school of law': 'Sutherland School of Law',
            'sutherland': 'Sutherland School of Law',
            'law building': 'Sutherland School of Law',

            # Lochlann Quinn School of Business
            'lochlann quinn school of business': 'Lochlann Quinn School of Business',
            'the business school': 'Lochlann Quinn School of Business',
            'business school': 'Lochlann Quinn School of Business',
            'lochlann quinn': 'Lochlann Quinn School of Business',
            'quinn school': 'Lochlann Quinn School of Business',
            'quinn': 'Lochlann Quinn School of Business',

            # Engineering & Materials Science Centre
            'engineering & materials science centre': 'Engineering & Materials Science Centre',
            'engineering and materials science centre': 'Engineering & Materials Science Centre',
            'engineering building': 'Engineering & Materials Science Centre',
            'engineering': 'Engineering & Materials Science Centre',
            'eng building': 'Engineering & Materials Science Centre',
            'eng': 'Engineering & Materials Science Centre',

            # Agriculture & Food Science Centre
            'agriculture & food science centre': 'Agriculture & Food Science Centre',
            'agriculture and food science centre': 'Agriculture & Food Science Centre',
            'agriculture building': 'Agriculture & Food Science Centre',
            'ag building': 'Agriculture & Food Science Centre',
            'ag science': 'Agriculture & Food Science Centre',

            # Health Sciences Centre
            'health sciences centre': 'Health Sciences Centre',
            'health sciences': 'Health Sciences Centre',
            'health sci': 'Health Sciences Centre',

            # Veterinary Sciences Centre
            'veterinary sciences centre': 'Veterinary Sciences Centre',
            'the vet school': 'Veterinary Sciences Centre',
            'vet school': 'Veterinary Sciences Centre',
            'veterinary': 'Veterinary Sciences Centre',
            'vet': 'Veterinary Sciences Centre',

            # Computer Science & Informatics Centre
            'computer science & informatics centre': 'Computer Science & Informatics Centre',
            'computer science and informatics centre': 'Computer Science & Informatics Centre',
            'comp sci building': 'Computer Science & Informatics Centre',
            'cs building': 'Computer Science & Informatics Centre',
            'computer science': 'Computer Science & Informatics Centre',
            'comp sci': 'Computer Science & Informatics Centre',

            # Daedalus Building
            'daedalus building': 'Daedalus Building',
            'daedalus': 'Daedalus Building',

            # Confucius Institute
            'confucius institute': 'Confucius Institute',
            'confucius': 'Confucius Institute',

            # Hanna Sheehy-Skeffington Building
            'hanna sheehy-skeffington building': 'Hanna Sheehy-Skeffington Building',
            'skeffington': 'Hanna Sheehy-Skeffington Building',
            'arts annexe': 'Hanna Sheehy-Skeffington Building',

            # Agnes McGuire Social Work Building
            'agnes mcguire social work building': 'Agnes McGuire Social Work Building',
            'agnes mcguire': 'Agnes McGuire Social Work Building',

            # Tierney Building
            'tierney building': 'Tierney Building',
            'tierney': 'Tierney Building',

            # Gerard Manley Hopkins Centre
            'gerard manley hopkins centre': 'Gerard Manley Hopkins Centre',
            'international office': 'Gerard Manley Hopkins Centre',
            'ucd global': 'Gerard Manley Hopkins Centre',
            'gmh': 'Gerard Manley Hopkins Centre',

            # Student Centre
            'the student centre': 'Student Centre',
            'student centre': 'Student Centre',
            'harmony studio': 'Student Centre',
            'harmony': 'Student Centre',
            'blue room': 'Student Centre',
            'red room': 'Student Centre',
            'fitzgerald chamber': 'Student Centre',
            'fitzgerald': 'Student Centre',
            'meeting room 5': 'Student Centre',
            'meeting room 6': 'Student Centre',
            'meeting room 7': 'Student Centre',
            'astra hall': 'Student Centre',
            'ucd cinema': 'Student Centre',
            'brava lounge': 'Student Centre',
            'atrium': 'Student Centre',
            'main foyer': 'Student Centre',
            'clubhouse bar': 'Student Centre',
            'clubhouse': 'Student Centre',
            "o'neill lounge": 'Student Centre',
            'oneill lounge': 'Student Centre',
            'global lounge': 'Student Centre',
            'newman basement': 'Student Centre',
            'newstead atrium': 'Student Centre',

            # UCD Village
            'ucd village': 'UCD Village',
            'the village': 'UCD Village',
            'village': 'UCD Village',

            # O'Reilly Hall
            "o'reilly hall": "O'Reilly Hall",
            'oreilly hall': "O'Reilly Hall",
            "o'reilly": "O'Reilly Hall",
            'oreilly': "O'Reilly Hall",

            # The Main Restaurant
            'the main restaurant': 'The Main Restaurant',
            'main restaurant': 'The Main Restaurant',
            'the main rest': 'The Main Restaurant',
            'the rest': 'The Main Restaurant',

            # UCD Sports Centre
            'ucd sports centre': 'UCD Sports Centre',
            'sports centre': 'UCD Sports Centre',
            'the gym': 'UCD Sports Centre',

            # The Pavilion
            'the pavilion': 'The Pavilion',
            'the pav': 'The Pavilion',
            'pav': 'The Pavilion',

            # Conway Institute
            'conway institute': 'Conway Institute',
            'conway': 'Conway Institute',

            # Charles Institute of Dermatology
            'charles institute of dermatology': 'Charles Institute of Dermatology',
            'charles institute': 'Charles Institute of Dermatology',
            'charles': 'Charles Institute of Dermatology',

            # Geary Institute for Public Policy
            'geary institute for public policy': 'Geary Institute for Public Policy',
            'geary institute': 'Geary Institute for Public Policy',
            'geary': 'Geary Institute for Public Policy',

            # Clinton Institute
            'clinton institute': 'Clinton Institute',
            'belfield house': 'Clinton Institute',
            'clinton': 'Clinton Institute',

            # NovaUCD
            'novaucd': 'NovaUCD',
            'merville house': 'NovaUCD',
            'nova': 'NovaUCD',

            # Richview School of Architecture
            'richview school of architecture': 'Richview School of Architecture',
            'richview': 'Richview School of Architecture',
            'architecture': 'Richview School of Architecture',

            # Newstead Building
            'newstead building': 'Newstead Building',
            'newstead': 'Newstead Building',

            # UCD Earth Institute
            'ucd earth institute': 'UCD Earth Institute',
            'earth institute': 'UCD Earth Institute',

            # Roebuck Hall / Castle
            'roebuck hall': 'Roebuck Hall',
            'roebuck castle': 'Roebuck Hall',
            'roebuck': 'Roebuck Hall',

            # O'Brien Centre wings
            'science east': "O'Brien Centre for Science",
            'science west': "O'Brien Centre for Science",
            "o'brien east": "O'Brien Centre for Science",
            "o'brien west": "O'Brien Centre for Science",
            'obrien east': "O'Brien Centre for Science",
            'obrien west': "O'Brien Centre for Science",

            # UCD Village Kitchen
            'village kitchen': 'UCD Village',
            'ucd village kitchen': 'UCD Village',

            # UCD Horticulture
            'polytunnel': 'UCD Horticulture Garden',
            'horticulture garden': 'UCD Horticulture Garden',
            'ucd horticulture': 'UCD Horticulture Garden',
            'rosemount': 'UCD Rosemount',
            'rosemount complex': 'UCD Rosemount',

            # Generic campus keywords
            'belfield': 'UCD Belfield',
            'ucd': 'UCD Belfield',
            'campus': 'UCD Belfield',
        }

    def _load_other_colleges(self) -> List[str]:
        return [
            'dcu', 'trinity', 'tcd', 'maynooth', 'mu', 'nuig', 'ucc', 'ul',
            'dublin city university', 'trinity college', 'maynooth university'
        ]

    def _load_off_campus_venues(self) -> List[str]:
        return [
            'kennedys', 'doyles', 'sinnotts', 'johnnie foxs',
            'blue light', 'taylors three rock', 'pub crawl',
            'brewery', 'tavern', 'pub', 'grill', 'diner',
            # 'bar' removed from simple list — too many false positives.
            # It's still caught via _BOUNDARY_VENUES word-boundary matching
            # when used as a standalone venue word (e.g. "the bar", "at a bar").
            # But "chocolate bar", "granola bar", "bar of soap" won't match.
            'nandos', 'supermacs', 'eddie rockets',
            'temple bar', 'grafton street', 'oconnell street',
            'rathmines', 'ranelagh', 'dundrum', 'city centre',
            'dublin 2', 'dublin 4', 'dublin mountains',
        ]

    def _load_nightlife_keywords(self) -> List[str]:
        return [
            'ball tickets', 'ball ticket',
            'charity ball', 'end of year ball', 'annual ball',
            'summer ball', 'winter ball', 'freshers ball', "fresher's ball",
            'halloween ball', 'christmas ball', 'masked ball', 'gala ball',
            'society ball', 'rag ball', 'sports ball',
            'gala', 'formal', 'pub crawl',
            'nightclub', 'club night', 'bar crawl',
            'pre drinks', 'afters', 'sesh', 'going out'
        ]

# Made with Bob
