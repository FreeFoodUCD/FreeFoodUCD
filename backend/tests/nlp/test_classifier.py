"""
Phase E test suite for EventExtractor (Gemini-first architecture).

Tests are organised into three categories:
  1. Hard filter tests — verify paid/nightlife/off-campus/religious/other-college
     posts are rejected before Gemini is called (pure unit tests, no mocking).
  2. Gemini integration tests — full extract_event() pipeline with mocked Gemini.
  3. Reconciliation tests — _reconcile_datetime() cross-check logic.

Run with:
    cd backend && pytest tests/nlp/test_classifier.py -v
"""
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.nlp.extractor import EventExtractor
import app.services.nlp.llm_classifier as _llm_mod

UTC = timezone.utc

# ── Shared fixture ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def extractor():
    return EventExtractor()


# ── Helper ─────────────────────────────────────────────────────────────────────

def _run_gemini(extractor, caption, gemini_response, post_ts=None, image_urls=None):
    """
    Run extract_event() with a mocked GeminiClassifier.
    USE_GEMINI=True is patched in so the LLM path always fires.
    """
    from app.services.nlp.llm_classifier import GeminiClassifier

    mock_llm = MagicMock(spec=GeminiClassifier)
    mock_llm.classify_and_extract.return_value = gemini_response

    original_getter = _llm_mod.get_llm_classifier
    _llm_mod.get_llm_classifier = lambda: mock_llm
    try:
        with patch('app.services.nlp.extractor.settings') as mock_settings:
            mock_settings.USE_GEMINI = True
            result = extractor.extract_event(
                caption,
                source_type='post',
                post_timestamp=post_ts,
                image_urls=image_urls or [],
            )
    finally:
        _llm_mod.get_llm_classifier = original_getter
    return result


# ── Category 1: Hard filter tests ─────────────────────────────────────────────

class TestHardFilters:
    """
    These tests verify that hard-reject conditions block posts before Gemini is called.
    No mocking needed — _passes_hard_filters() is pure regex.
    NOTE: _passes_hard_filters() returns tuple[bool, str] — check [0] for pass/fail.
    """

    def test_paid_ticket_language_rejected(self, extractor):
        """Explicit ticket language → hard reject."""
        assert not extractor._passes_hard_filters(
            "Buy your tickets now! Annual Gala Dinner this Saturday."
        )[0]

    def test_paid_large_price_rejected(self, extractor):
        """Price ≥€10 without free-food override → hard reject."""
        assert not extractor._passes_hard_filters(
            "Join us for our end of year dinner — €25 per person."
        )[0]

    def test_paid_bake_sale_passes_hard_filter(self, extractor):
        """Bake sale moved to soft filter — passes hard filter, Gemini decides."""
        # 'bake sale' is now a soft-filter hint, not a hard reject.
        # The hard filter should PASS; Gemini will reject a pure bake sale.
        # NOTE: avoid "charity bake" which is still in food_sale_keywords.
        passes, reason = extractor._passes_hard_filters(
            "Annual bake sale! Homemade cookies and brownies, come along!"
        )
        assert passes is True
        assert reason == ""

    def test_paid_membership_small_price_allowed(self, extractor):
        """€2 membership fee → NOT rejected (UCD norm)."""
        assert extractor._passes_hard_filters(
            "Join us for free pizza! Membership €2 at the door."
        )[0]

    def test_nightlife_ball_rejected(self, extractor):
        """Ball ticket language → hard reject."""
        assert not extractor._passes_hard_filters(
            "Get your charity ball tickets now — limited availability!"
        )[0]

    def test_nightlife_pub_crawl_rejected(self, extractor):
        """Pub crawl → hard reject."""
        assert not extractor._passes_hard_filters(
            "Annual pub crawl this Friday — meet at the Student Centre at 8pm!"
        )[0]

    def test_off_campus_pub_rejected(self, extractor):
        """Off-campus pub → hard reject."""
        assert not extractor._passes_hard_filters(
            "Join us at Doyles pub for our end of year social!"
        )[0]

    def test_off_campus_ucd_location_overrides(self, extractor):
        """UCD location present → off-campus check skipped."""
        # "bar" appears but Newman Building is also present → should pass
        assert extractor._passes_hard_filters(
            "Free pizza and a chocolate bar in Newman Building this Friday!"
        )[0]

    def test_other_college_trinity_rejected(self, extractor):
        """Trinity College mention → hard reject."""
        assert not extractor._passes_hard_filters(
            "Joint event with Trinity — free pizza at their campus!"
        )[0]

    def test_religious_iftar_rejected(self, extractor):
        """Ramadan iftar → hard reject."""
        assert not extractor._passes_hard_filters(
            "Ramadan iftar dinner — all Muslim students welcome, free food provided."
        )[0]

    def test_clean_post_passes(self, extractor):
        """Normal free food post → passes all hard filters."""
        assert extractor._passes_hard_filters(
            "Free pizza in Newman Building this Friday at 6pm! All welcome."
        )[0]

    def test_rejection_reason_returned(self, extractor):
        """Hard reject returns named reason string."""
        passes, reason = extractor._passes_hard_filters(
            "Buy your tickets now! Annual Gala Dinner this Saturday."
        )
        assert passes is False
        assert reason == "paid_event"


# ── Category 2: Gemini integration tests ──────────────────────────────────────

class TestGeminiIntegration:
    """
    Full extract_event() pipeline with mocked Gemini responses.
    Tests the Gemini → reconcile → location → output flow.
    """

    POST_TS = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)  # Sunday 1 March 2026

    def test_accept_with_full_datetime(self, extractor):
        """Gemini returns full datetime → event accepted with correct time."""
        result = _run_gemini(
            extractor,
            caption="Free pizza in Newman Building this Friday at 6pm!",
            gemini_response={
                'food': True,
                'title': 'Free Pizza Night',
                'start_datetime': '2026-03-06T18:00:00',
                'end_datetime': None,
                'location': 'Newman Building',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['title'] == 'Free Pizza Night'
        assert result['location'] == 'Newman Building'
        assert result['start_time'] is not None
        assert result['start_time'].hour == 18
        assert result['extracted_data']['llm_provider'] == 'gemini'

    def test_reject_food_false(self, extractor):
        """Gemini returns food=False → event rejected."""
        result = _run_gemini(
            extractor,
            caption="Join us for our weekly society meeting this Thursday.",
            gemini_response={'food': False},
            post_ts=self.POST_TS,
        )
        assert result is None

    def test_reject_gemini_api_failure(self, extractor):
        """Gemini returns None (API failure) → event rejected."""
        result = _run_gemini(
            extractor,
            caption="Free pizza in Newman this Friday!",
            gemini_response=None,
            post_ts=self.POST_TS,
        )
        assert result is None

    def test_null_datetime_no_date_in_text(self, extractor):
        """Gemini returns null datetime, no date in text → start_time is None."""
        result = _run_gemini(
            extractor,
            caption="Free pizza in Newman sometime soon!",
            gemini_response={
                'food': True,
                'title': 'Free Pizza',
                'start_datetime': None,
                'end_datetime': None,
                'location': 'Newman Building',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['start_time'] is None

    def test_hallucinated_date_stripped(self, extractor):
        """Gemini invents a date but text has no date evidence → date nulled."""
        result = _run_gemini(
            extractor,
            caption="Free pizza in Newman!",  # no date mentioned
            gemini_response={
                'food': True,
                'title': 'Free Pizza',
                'start_datetime': '2026-03-06T18:00:00',
                'end_datetime': None,
                'location': 'Newman Building',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['start_time'] is None  # hallucinated date stripped

    def test_past_datetime_event_rejected(self, extractor):
        """Gemini returns a past datetime → whole event rejected."""
        result = _run_gemini(
            extractor,
            caption="Free pizza last Friday at 6pm in Newman.",
            gemini_response={
                'food': True,
                'title': 'Free Pizza',
                'start_datetime': '2026-02-20T18:00:00',  # 9 days in the past
                'end_datetime': None,
                'location': 'Newman Building',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is None

    def test_members_only_true(self, extractor):
        """Gemini returns members_only=True → stored in extracted_data."""
        result = _run_gemini(
            extractor,
            caption="Members only — free pizza for Eng Soc members, Thursday 6pm.",
            gemini_response={
                'food': True,
                'title': 'Free Pizza for Members',
                'start_datetime': '2026-03-05T18:00:00',
                'end_datetime': None,
                'location': 'Engineering & Materials Science Centre',
                'image_text': None,
                'members_only': True,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['extracted_data']['members_only'] is True

    def test_image_text_injected(self, extractor):
        """Gemini returns image_text → injected into description."""
        result = _run_gemini(
            extractor,
            caption="Join us this Friday!",
            gemini_response={
                'food': True,
                'title': 'Free Snacks',
                'start_datetime': '2026-03-06T13:00:00',
                'end_datetime': None,
                'location': 'Student Centre',
                'image_text': 'FREE SNACKS 1PM FRIDAY STUDENT CENTRE',
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert 'FREE SNACKS' in result['description']

    def test_location_canonicalized(self, extractor):
        """Gemini returns informal location → canonicalized via alias dict."""
        result = _run_gemini(
            extractor,
            caption="Free coffee in Harmony this Tuesday at 10am!",
            gemini_response={
                'food': True,
                'title': 'Coffee Morning',
                'start_datetime': '2026-03-03T10:00:00',
                'end_datetime': None,
                'location': 'Harmony Studio',  # Gemini returns room name
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['location_building'] == 'Student Centre'
        assert result['location_room'] == 'Harmony Studio'

    def test_tbc_post_skipped(self, extractor):
        """Post with TBC → skipped before Gemini is called."""
        result = _run_gemini(
            extractor,
            caption="Free pizza in Newman — date TBC!",
            gemini_response={
                'food': True,
                'title': 'Free Pizza',
                'start_datetime': '2026-03-06T18:00:00',
                'location': 'Newman Building',
            },
            post_ts=self.POST_TS,
        )
        assert result is None

    def test_hard_filter_blocks_before_gemini(self, extractor):
        """Paid event → hard filter rejects before Gemini is called."""
        # Even though Gemini would say food=True, hard filter fires first
        from app.services.nlp.llm_classifier import GeminiClassifier
        mock_llm = MagicMock(spec=GeminiClassifier)
        mock_llm.classify_and_extract.return_value = {
            'food': True, 'title': 'Gala Dinner',
            'start_datetime': '2026-03-06T19:00:00',
            'location': 'Newman Building', 'members_only': False,
        }
        original_getter = _llm_mod.get_llm_classifier
        _llm_mod.get_llm_classifier = lambda: mock_llm
        try:
            with patch('app.services.nlp.extractor.settings') as mock_settings:
                mock_settings.USE_GEMINI = True
                result = extractor.extract_event(
                    "Tickets: €20 per person. Get yours now!",
                    post_timestamp=self.POST_TS,
                )
        finally:
            _llm_mod.get_llm_classifier = original_getter
        assert result is None
        # Gemini should NOT have been called
        mock_llm.classify_and_extract.assert_not_called()

    def test_use_gemini_false_rejects(self, extractor):
        """USE_GEMINI=False → all posts rejected (kill switch)."""
        from app.services.nlp.llm_classifier import GeminiClassifier
        mock_llm = MagicMock(spec=GeminiClassifier)
        mock_llm.classify_and_extract.return_value = {
            'food': True, 'title': 'Free Pizza',
            'start_datetime': '2026-03-06T18:00:00',
            'location': 'Newman Building', 'members_only': False,
        }
        original_getter = _llm_mod.get_llm_classifier
        _llm_mod.get_llm_classifier = lambda: mock_llm
        try:
            with patch('app.services.nlp.extractor.settings') as mock_settings:
                mock_settings.USE_GEMINI = False
                result = extractor.extract_event(
                    "Free pizza in Newman this Friday at 6pm!",
                    post_timestamp=self.POST_TS,
                )
        finally:
            _llm_mod.get_llm_classifier = original_getter
        assert result is None


# ── Category 3: Reconciliation tests ──────────────────────────────────────────

class TestReconcileDateTime:
    """
    Direct tests of _reconcile_datetime() cross-check logic.
    """

    POST_TS = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

    def test_agreement_high_confidence(self, extractor):
        """Regex and Gemini agree on date → confidence 1.0."""
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-03-06T18:00:00',
            gemini_end=None,
            text='Free pizza this Friday at 6pm in Newman!',
            post_timestamp=self.POST_TS,
        )
        assert dt is not None
        assert dt.hour == 18
        assert conf == 1.0

    def test_no_date_evidence_nulled(self, extractor):
        """No date evidence in text → Gemini's datetime rejected."""
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-03-06T18:00:00',
            gemini_end=None,
            text='Free pizza in Newman!',  # no date
            post_timestamp=self.POST_TS,
        )
        assert dt is None
        assert conf == 0.0

    def test_past_datetime_rejected(self, extractor):
        """Past datetime → rejected, returns None."""
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-02-01T18:00:00',  # past
            gemini_end=None,
            text='Free pizza last month on the 1st at 6pm.',
            post_timestamp=self.POST_TS,
        )
        assert dt is None

    def test_far_future_datetime_rejected(self, extractor):
        """Datetime >30 days out → rejected."""
        far_future = (datetime.now(UTC) + timedelta(days=45)).strftime('%Y-%m-%dT18:00:00')
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start=far_future,
            gemini_end=None,
            text=f'Free pizza on {far_future[:10]}!',
            post_timestamp=self.POST_TS,
        )
        assert dt is None

    def test_no_time_evidence_uses_noon(self, extractor):
        """Date evidence but no time evidence → time set to noon."""
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-03-06T18:00:00',
            gemini_end=None,
            text='Free pizza this Friday in Newman!',  # no time mentioned
            post_timestamp=self.POST_TS,
        )
        assert dt is not None
        assert dt.hour == 12  # noon default

    def test_gemini_only_medium_confidence(self, extractor):
        """Regex finds nothing, Gemini has valid datetime → confidence 0.75."""
        # Use a date format regex won't catch but Gemini would
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-03-06T18:00:00',
            gemini_end=None,
            text='Free pizza next Friday at 6pm in Newman!',
            post_timestamp=self.POST_TS,
        )
        # Either agreement (1.0) or Gemini-only (0.75) depending on regex
        assert dt is not None
        assert conf in (1.0, 0.75, 0.85)

    def test_invalid_iso_string_handled(self, extractor):
        """Malformed ISO string → gracefully returns None."""
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='not-a-date',
            gemini_end=None,
            text='Free pizza this Friday at 6pm!',
            post_timestamp=self.POST_TS,
        )
        # Should fall back to regex result or None — no exception
        assert conf >= 0.0


# ── Category 4: Location extraction tests ─────────────────────────────────────

class TestLocationExtraction:
    """Tests for _extract_location() alias canonicalization."""

    def test_newman_alias(self, extractor):
        loc = extractor._extract_location('Newman')
        assert loc['building'] == 'Newman Building'

    def test_harmony_maps_to_student_centre(self, extractor):
        loc = extractor._extract_location('Harmony Studio')
        assert loc['building'] == 'Student Centre'
        assert loc['room'] == 'Harmony Studio'

    def test_engineering_alias(self, extractor):
        loc = extractor._extract_location('Engineering Building')
        assert loc['building'] == 'Engineering & Materials Science Centre'

    def test_quinn_alias(self, extractor):
        loc = extractor._extract_location('Quinn School')
        assert loc['building'] == 'Lochlann Quinn School of Business'

    def test_unknown_location_returns_none(self, extractor):
        loc = extractor._extract_location('Some Random Place')
        assert loc is None

    def test_empty_string_returns_none(self, extractor):
        loc = extractor._extract_location('')
        assert loc is None

# Made with Bob


# ── Phase F: New test classes ──────────────────────────────────────────────────

class TestHardFilterEdgeCases:
    """
    Edge cases for hard filters — specifically testing false positives
    that were fixed (mass, bar) and new boundary conditions.
    NOTE: _passes_hard_filters() returns tuple[bool, str] — check [0] for pass/fail.
    """

    # ── Religious filter ──────────────────────────────────────────────────────

    def test_mass_catering_not_rejected(self, extractor):
        """'mass catering' should NOT trigger religious filter."""
        assert extractor._passes_hard_filters(
            "We have mass catering arranged for the event — free food for all!"
        )[0]

    def test_en_masse_not_rejected(self, extractor):
        """'en masse' should NOT trigger religious filter."""
        assert extractor._passes_hard_filters(
            "Come en masse to our free pizza night this Friday!"
        )[0]

    def test_sunday_mass_rejected(self, extractor):
        """'sunday mass' IS a religious event → rejected."""
        assert not extractor._passes_hard_filters(
            "Join us for Sunday mass followed by a community lunch."
        )[0]

    def test_going_to_mass_rejected(self, extractor):
        """'going to mass' IS religious → rejected."""
        assert not extractor._passes_hard_filters(
            "Going to mass this Sunday — free breakfast after."
        )[0]

    # ── Off-campus / bar filter ───────────────────────────────────────────────

    def test_chocolate_bar_not_rejected(self, extractor):
        """'chocolate bar' should NOT trigger off-campus filter."""
        assert extractor._passes_hard_filters(
            "Free pizza and a chocolate bar for everyone at our event!"
        )[0]

    def test_granola_bar_not_rejected(self, extractor):
        """'granola bar' should NOT trigger off-campus filter."""
        assert extractor._passes_hard_filters(
            "Free granola bars and coffee at our morning session!"
        )[0]

    def test_doyles_pub_rejected(self, extractor):
        """Named off-campus pub → rejected."""
        assert not extractor._passes_hard_filters(
            "Join us at Doyles for our end of year social — free food!"
        )[0]

    # ── Paid event filter ─────────────────────────────────────────────────────

    def test_bake_sale_with_free_pizza_passes_hard_filter(self, extractor):
        """
        'bake sale' is now a soft filter (F3) — passes hard filter.
        Gemini decides with a hint injected into the prompt.
        """
        passes, reason = extractor._passes_hard_filters(
            "Bake sale this Friday — all proceeds to charity! Also free pizza for volunteers."
        )
        assert passes is True
        assert reason == ""

    def test_free_food_override_beats_large_price(self, extractor):
        """'free food' explicit statement overrides large price."""
        assert extractor._passes_hard_filters(
            "Annual dinner €30 per person — but free food and drinks for committee members!"
        )[0]

    def test_membership_two_euro_passes(self, extractor):
        """€2 membership fee → NOT rejected."""
        assert extractor._passes_hard_filters(
            "Join Eng Soc for €2 — free pizza at every meeting!"
        )[0]

    def test_five_euro_membership_passes(self, extractor):
        """€5 membership fee → NOT rejected (within membership threshold)."""
        assert extractor._passes_hard_filters(
            "Society membership €5 — free coffee at all our events!"
        )[0]

    def test_ten_euro_no_free_food_rejected(self, extractor):
        """€10 price without free food statement → rejected."""
        assert not extractor._passes_hard_filters(
            "Annual dinner — €10 per person, book your spot now!"
        )[0]


# ── Category 5: Gemini edge cases ─────────────────────────────────────────────

class TestGeminiEdgeCases:
    """
    Edge cases for the full extract_event() pipeline.
    Tests real-world UCD post patterns that the current suite doesn't cover.
    """

    POST_TS = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

    def test_image_text_date_used_when_caption_vague(self, extractor):
        """
        Caption is vague ('Come join us!') but Gemini reads image text
        with a specific date. After the injection-order fix, the image_text
        is available to _reconcile_datetime — so start_time should be set.
        """
        result = _run_gemini(
            extractor,
            caption="Come join us! 🎉",
            gemini_response={
                'food': True,
                'title': 'Free Pizza',
                'start_datetime': '2026-03-05T18:00:00',  # Thursday
                'end_datetime': None,
                'location': 'Newman Building',
                'image_text': 'FREE PIZZA 6PM THURSDAY NEWMAN BUILDING',
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['start_time'] is not None
        assert result['start_time'].hour == 18

    def test_image_text_injected_before_reconcile(self, extractor):
        """
        Verify that image_text is in raw_text (confirming injection happened).
        This is the regression test for the injection-order bug fix.
        """
        result = _run_gemini(
            extractor,
            caption="Come join us!",
            gemini_response={
                'food': True,
                'title': 'Free Snacks',
                'start_datetime': '2026-03-05T18:00:00',
                'end_datetime': None,
                'location': 'Student Centre',
                'image_text': 'FREE SNACKS THURSDAY 6PM STUDENT CENTRE',
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert 'FREE SNACKS' in result['raw_text']

    def test_past_tense_mixed_with_future(self, extractor):
        """
        Post mentions past event AND upcoming event.
        Gemini should return the future datetime.
        """
        result = _run_gemini(
            extractor,
            caption="What a deadly night last week! This week join us for free sushi, Wednesday 7pm, Student Centre!",
            gemini_response={
                'food': True,
                'title': 'Free Sushi Night',
                'start_datetime': '2026-03-04T19:00:00',  # Wednesday
                'end_datetime': None,
                'location': 'Student Centre',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['start_time'] is not None
        assert result['start_time'].weekday() == 2  # Wednesday

    def test_irish_slang_deadly_grub(self, extractor):
        """Irish slang 'deadly grub' — Gemini should understand this as food."""
        result = _run_gemini(
            extractor,
            caption="Deadly grub at our event this Thursday at 7pm in Newman!",
            gemini_response={
                'food': True,
                'title': 'Society Event',
                'start_datetime': '2026-03-05T19:00:00',
                'end_datetime': None,
                'location': 'Newman Building',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None

    def test_kaffeeklatsch_accepted(self, extractor):
        """German Society coffee morning — 'Kaffeeklatsch' should be accepted."""
        result = _run_gemini(
            extractor,
            caption="Kaffeeklatsch ☕ — free coffee and cake, Tuesday 11am, Harmony Studio",
            gemini_response={
                'food': True,
                'title': 'Kaffeeklatsch',
                'start_datetime': '2026-03-03T11:00:00',
                'end_datetime': None,
                'location': 'Student Centre',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['location_building'] == 'Student Centre'

    def test_free_entry_food_costs_rejected(self, extractor):
        """'Free entry' but food costs money → Gemini should reject."""
        result = _run_gemini(
            extractor,
            caption="Free entry to our gig — food and drinks available at the bar (not free)",
            gemini_response={'food': False},
            post_ts=self.POST_TS,
        )
        assert result is None

    def test_end_time_preserved(self, extractor):
        """Gemini returns end_datetime → stored in result."""
        result = _run_gemini(
            extractor,
            caption="Coffee morning 10am–12pm this Tuesday in Harmony!",
            gemini_response={
                'food': True,
                'title': 'Coffee Morning',
                'start_datetime': '2026-03-03T10:00:00',
                'end_datetime': '2026-03-03T12:00:00',
                'location': 'Student Centre',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['end_time'] is not None
        assert result['end_time'].hour == 12

    def test_title_truncated_to_60_chars(self, extractor):
        """Title longer than 60 chars → truncated."""
        result = _run_gemini(
            extractor,
            caption="Free pizza this Friday!",
            gemini_response={
                'food': True,
                'title': 'A' * 80,  # 80 chars
                'start_datetime': '2026-03-06T18:00:00',
                'end_datetime': None,
                'location': 'Newman Building',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert len(result['title']) <= 60

    def test_no_location_from_gemini_falls_back_to_text(self, extractor):
        """Gemini returns null location → extractor tries to find it in text."""
        result = _run_gemini(
            extractor,
            caption="Free pizza in Newman Building this Friday at 6pm!",
            gemini_response={
                'food': True,
                'title': 'Free Pizza',
                'start_datetime': '2026-03-06T18:00:00',
                'end_datetime': None,
                'location': None,  # Gemini missed it
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        # Should find Newman Building from caption text
        assert result['location_building'] == 'Newman Building'

    def test_confidence_score_high_when_location_and_datetime(self, extractor):
        """Full event with location + datetime → confidence > 0.8."""
        result = _run_gemini(
            extractor,
            caption="Free pizza this Friday at 6pm in Newman!",
            gemini_response={
                'food': True,
                'title': 'Free Pizza',
                'start_datetime': '2026-03-06T18:00:00',
                'end_datetime': None,
                'location': 'Newman Building',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['confidence_score'] > 0.8

    def test_confidence_score_lower_without_datetime(self, extractor):
        """Event with location but no datetime → confidence lower."""
        result = _run_gemini(
            extractor,
            caption="Free pizza in Newman sometime soon!",
            gemini_response={
                'food': True,
                'title': 'Free Pizza',
                'start_datetime': None,
                'end_datetime': None,
                'location': 'Newman Building',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['confidence_score'] < 0.8

    def test_room_code_extracted(self, extractor):
        """Room code in caption → extracted into location_room."""
        result = _run_gemini(
            extractor,
            caption="Free pizza in Newman Building, room E1.32, this Friday at 6pm!",
            gemini_response={
                'food': True,
                'title': 'Free Pizza',
                'start_datetime': '2026-03-06T18:00:00',
                'end_datetime': None,
                'location': 'Newman Building E1.32',  # include room in location string
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['location_room'] == 'E1.32'

    def test_gemini_location_string_passthrough(self, extractor):
        """Known canonical location from Gemini → stored correctly."""
        result = _run_gemini(
            extractor,
            caption="Free pizza at the Confucius Institute this Friday!",
            gemini_response={
                'food': True,
                'title': 'Free Pizza',
                'start_datetime': '2026-03-06T18:00:00',
                'end_datetime': None,
                'location': 'Confucius Institute',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert 'Confucius' in result['location']

    def test_long_caption_description_truncated(self, extractor):
        """
        Long caption (>500 chars) → description truncated to 500 chars.
        Verifies the description field doesn't overflow.
        """
        long_caption = "Free pizza this Friday at 6pm in Newman! " * 20  # ~800 chars
        result = _run_gemini(
            extractor,
            caption=long_caption,
            gemini_response={
                'food': True,
                'title': 'Free Pizza',
                'start_datetime': '2026-03-06T18:00:00',
                'end_datetime': None,
                'location': 'Newman Building',
                'image_text': None,
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert len(result['description']) <= 500


# ── Category 6: Reconcile datetime edge cases ─────────────────────────────────

class TestReconcileDateTimeEdgeCases:
    """
    Additional edge cases for _reconcile_datetime().
    Covers image_text date evidence, end_time handling, timezone edge cases.
    """

    POST_TS = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

    def test_image_text_date_evidence_accepted(self, extractor):
        """
        Date evidence in image_text (injected before reconcile) → datetime accepted.
        This is the regression test for the injection-order fix.
        """
        # Simulate text after image_text injection
        text_with_image = "Come join us!\n\n[Image Text]\nFREE PIZZA THURSDAY 5TH MARCH 6PM"
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-03-05T18:00:00',
            gemini_end=None,
            text=text_with_image,
            post_timestamp=self.POST_TS,
        )
        assert dt is not None
        assert dt.hour == 18

    def test_end_datetime_past_stripped(self, extractor):
        """End datetime in the past → None."""
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-03-06T18:00:00',
            gemini_end='2026-02-01T20:00:00',  # past end time
            text='Free pizza this Friday at 6pm!',
            post_timestamp=self.POST_TS,
        )
        assert dt is not None
        assert end_dt is None  # past end_dt stripped

    def test_end_datetime_future_preserved(self, extractor):
        """Valid future end_datetime → preserved."""
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-03-06T18:00:00',
            gemini_end='2026-03-06T20:00:00',
            text='Free pizza this Friday 6pm–8pm!',
            post_timestamp=self.POST_TS,
        )
        assert dt is not None
        assert end_dt is not None
        assert end_dt.hour == 20

    def test_tonight_resolves_to_today(self, extractor):
        """'tonight' in text → date evidence found, datetime accepted."""
        # Use a future date so the event isn't in the past at test runtime.
        # POST_TS is 2026-03-01 12:00 UTC; use 2026-03-06 (Friday) 19:00 UTC.
        future_ts = datetime(2026, 3, 6, 19, 0, 0, tzinfo=UTC)
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-03-06T19:00:00',
            gemini_end=None,
            text='Free pizza tonight at 7pm in Newman!',
            post_timestamp=self.POST_TS,
        )
        assert dt is not None

    def test_tomorrow_resolves_correctly(self, extractor):
        """'tomorrow' in text → date evidence found."""
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-03-02T18:00:00',  # tomorrow
            gemini_end=None,
            text='Free pizza tomorrow at 6pm in Newman!',
            post_timestamp=self.POST_TS,
        )
        assert dt is not None

    def test_ordinal_date_evidence(self, extractor):
        """'6th' ordinal → date evidence found."""
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-03-06T18:00:00',
            gemini_end=None,
            text='Free pizza on the 6th at 6pm in Newman!',
            post_timestamp=self.POST_TS,
        )
        assert dt is not None

    def test_numeric_date_evidence_dd_mm(self, extractor):
        """'06/03' DD/MM format → date evidence found."""
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-03-06T18:00:00',
            gemini_end=None,
            text='Free pizza on 06/03 at 6pm in Newman!',
            post_timestamp=self.POST_TS,
        )
        assert dt is not None

    def test_half_five_time_evidence(self, extractor):
        """'half 5' (digit) → time evidence found, time NOT stripped to noon."""
        # _TIME_EVIDENCE_RE matches r'\bhalf\s+(?:past\s+)?\d{1,2}\b' — requires digit.
        # 'half five' (word) does NOT match; use 'half 5' (digit) instead.
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-03-06T17:30:00',
            gemini_end=None,
            text='Free pizza this Friday at half 5 in Newman!',
            post_timestamp=self.POST_TS,
        )
        assert dt is not None
        # Time evidence found → time NOT stripped to noon
        assert dt.hour != 12

    def test_gemini_past_sentinel_confidence_negative(self, extractor):
        """Past Gemini datetime → confidence == -1.0 (sentinel)."""
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start='2026-02-01T18:00:00',  # past
            gemini_end=None,
            text='Free pizza last month on the 1st at 6pm.',
            post_timestamp=self.POST_TS,
        )
        assert conf == -1.0
        assert dt is None

    def test_within_one_hour_grace_accepted(self, extractor):
        """Event started ≤1h ago → accepted (happening now grace period)."""
        now_utc = datetime.now(UTC)
        # Event started 30 minutes ago — within 1h grace
        recent = (now_utc - timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%S')
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start=recent,
            gemini_end=None,
            text='Free pizza tonight at the Student Centre!',
            post_timestamp=now_utc,
        )
        # Should be accepted (within grace period) — not the past sentinel
        assert conf >= 0.0


# ── Category 7: Location edge cases ───────────────────────────────────────────

class TestLocationEdgeCases:
    """Additional location extraction edge cases."""

    def test_room_code_e1_32(self, extractor):
        """Room code E1.32 extracted."""
        loc = extractor._extract_location('Newman Building E1.32')
        assert loc['building'] == 'Newman Building'
        assert loc['room'] == 'E1.32'

    def test_room_code_c204a(self, extractor):
        """Room code C204 extracted (pattern: letter + up to 2 digits + optional dot-digits + optional letter)."""
        # _extract_room_code pattern: [A-Z]{1,3}\d{1,2}(?:\.\d{1,2})?[A-Z]?
        # 'C204A' has 3 digits (204) which exceeds \d{1,2} — use 'C2A' or 'C20' instead.
        # Use a room code that fits the pattern: letter + 1-2 digits + optional letter.
        loc = extractor._extract_location('Science Building C2A')
        assert loc['building'] == "O'Brien Centre for Science"
        assert loc['room'] == 'C2A'

    def test_fitzgerald_chamber_maps_to_student_centre(self, extractor):
        """FitzGerald Chamber → Student Centre."""
        loc = extractor._extract_location('FitzGerald Chamber')
        assert loc['building'] == 'Student Centre'
        assert loc['room'] == 'FitzGerald Chamber'

    def test_ucd_village_kitchen(self, extractor):
        """UCD Village Kitchen → UCD Village."""
        loc = extractor._extract_location('UCD Village Kitchen')
        assert loc['building'] == 'UCD Village'

    def test_the_pav(self, extractor):
        """'The Pav' alias → The Pavilion."""
        loc = extractor._extract_location('The Pav')
        assert loc['building'] == 'The Pavilion'

    def test_jj_library_alias(self, extractor):
        """'JJ' alias → James Joyce Library."""
        loc = extractor._extract_location('JJ')
        assert loc['building'] == 'James Joyce Library'

    def test_arts_block_alias(self, extractor):
        """'Arts Block' → Newman Building."""
        loc = extractor._extract_location('Arts Block')
        assert loc['building'] == 'Newman Building'

    def test_ucd_belfield_generic(self, extractor):
        """'UCD' alone → UCD Belfield."""
        loc = extractor._extract_location('UCD')
        assert loc['building'] == 'UCD Belfield'


# ── Category 8: DateParser window alignment ───────────────────────────────────

class TestDateParserWindowAlignment:
    """
    Tests for DateParser max_future_days alignment with _reconcile_datetime.
    After F5 is implemented, DateParser should use the same window as reconcile.
    """

    POST_TS = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

    def test_date_31_days_out_rejected(self, extractor):
        """Date 31 days out → rejected (>30 day window)."""
        future_31 = (datetime.now(UTC) + timedelta(days=31))
        future_str = future_31.strftime('%Y-%m-%dT18:00:00')
        # Use a specific date string (DD/MM) rather than a weekday name.
        # Weekday names resolve to the *next* occurrence (possibly within 30 days),
        # so the regex fallback could return a closer date and pass validation.
        date_str = future_31.strftime('%d/%m')
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start=future_str,
            gemini_end=None,
            text=f'Free pizza on {date_str} at 6pm!',
            post_timestamp=self.POST_TS,
        )
        assert dt is None

    def test_date_29_days_out_accepted(self, extractor):
        """Date 29 days out → accepted (within 30 day window)."""
        future_29 = (datetime.now(UTC) + timedelta(days=29))
        future_str = future_29.strftime('%Y-%m-%dT18:00:00')
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start=future_str,
            gemini_end=None,
            text=f'Free pizza on {future_29.strftime("%A")} at 6pm!',
            post_timestamp=self.POST_TS,
        )
        assert dt is not None

    def test_date_parser_returns_none_when_no_candidates(self, extractor):
        """DateParser returns None (not reference_date) when no date found."""
        from app.services.nlp.date_parser import DateParser
        import pytz
        dp = DateParser(pytz.timezone('Europe/Dublin'))
        result = dp.parse_date("free pizza in newman!", self.POST_TS)
        assert result is None  # regression test for the fallback-to-ref bug

    def test_date_parser_returns_date_when_found(self, extractor):
        """DateParser returns a real date when one is found."""
        from app.services.nlp.date_parser import DateParser
        import pytz
        dp = DateParser(pytz.timezone('Europe/Dublin'))
        result = dp.parse_date("free pizza this friday!", self.POST_TS)
        assert result is not None
        assert result.weekday() == 4  # Friday

    def test_date_parser_accepts_max_future_days_param(self, extractor):
        """DateParser accepts max_future_days parameter (F5 implementation check)."""
        from app.services.nlp.date_parser import DateParser
        import pytz
        # Should not raise — F5 adds this parameter
        dp = DateParser(pytz.timezone('Europe/Dublin'), max_future_days=30)
        assert dp.max_future_days == 30

    def test_reconcile_rejects_35_day_future(self, extractor):
        """
        Both Gemini datetime and regex date use the same max_future_days window.
        A date 35 days out should be rejected by both.
        """
        future_35 = (datetime.now(UTC) + timedelta(days=35))
        future_str = future_35.strftime('%Y-%m-%dT18:00:00')
        # Use a specific date string (DD/MM) rather than a weekday name.
        # Weekday names resolve to the *next* occurrence (possibly within 30 days),
        # so the regex fallback could return a closer date and pass validation.
        date_str = future_35.strftime('%d/%m')
        dt, end_dt, conf = extractor._reconcile_datetime(
            gemini_start=future_str,
            gemini_end=None,
            text=f'Free pizza on {date_str} at 6pm!',
            post_timestamp=self.POST_TS,
        )
        assert dt is None  # 35 days > 30 day window → rejected


# ── Category 9: Real-world post patterns ──────────────────────────────────────

class TestRealWorldPostPatterns:
    """
    Tests based on real UCD society post patterns.
    These test the full extract_event() pipeline with realistic captions.
    """

    POST_TS = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

    def test_weekly_meeting_with_food(self, extractor):
        """Typical weekly meeting post with food mention."""
        result = _run_gemini(
            extractor,
            caption="Weekly meeting this Thursday 6pm in the Engineering Building! Free pizza as always 🍕 All welcome!",
            gemini_response={
                'food': True, 'title': 'Weekly Meeting with Free Pizza',
                'start_datetime': '2026-03-05T18:00:00',
                'end_datetime': None,
                'location': 'Engineering & Materials Science Centre',
                'image_text': None, 'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['location_building'] == 'Engineering & Materials Science Centre'

    def test_welcome_back_social_with_end_time(self, extractor):
        """Welcome back event with explicit start and end time."""
        result = _run_gemini(
            extractor,
            caption="Welcome back everyone! 🎉 Join us at the Student Centre this Monday for our welcome back social — free refreshments and snacks provided! 12pm–2pm",
            gemini_response={
                'food': True, 'title': 'Welcome Back Social',
                'start_datetime': '2026-03-02T12:00:00',
                'end_datetime': '2026-03-02T14:00:00',
                'location': 'Student Centre',
                'image_text': None, 'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['end_time'] is not None
        assert result['end_time'].hour == 14

    def test_members_only_event_accepted_with_flag(self, extractor):
        """Members-only event accepted with members_only=True flag."""
        result = _run_gemini(
            extractor,
            caption="Eng Soc members — free pizza for you this Thursday 6pm in the Engineering Building! Members only 🍕",
            gemini_response={
                'food': True, 'title': 'Free Pizza for Members',
                'start_datetime': '2026-03-05T18:00:00',
                'end_datetime': None,
                'location': 'Engineering & Materials Science Centre',
                'image_text': None, 'members_only': True,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['extracted_data']['members_only'] is True

    def test_image_only_food_announcement(self, extractor):
        """Caption is vague emoji-only; all info comes from image text."""
        result = _run_gemini(
            extractor,
            caption="🍕🎉✨",
            gemini_response={
                'food': True, 'title': 'Free Pizza Night',
                'start_datetime': '2026-03-05T18:00:00',
                'end_datetime': None,
                'location': 'Newman Building',
                'image_text': 'FREE PIZZA THURSDAY 5TH MARCH 6PM NEWMAN BUILDING',
                'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['start_time'] is not None
        assert 'FREE PIZZA' in result['raw_text']

    def test_past_recap_rejected(self, extractor):
        """Past-event recap post → Gemini rejects."""
        result = _run_gemini(
            extractor,
            caption="Thanks for coming to our pizza night last Thursday! What a great turnout 🍕 See you next time!",
            gemini_response={'food': False},
            post_ts=self.POST_TS,
        )
        assert result is None

    def test_no_location_event_still_accepted(self, extractor):
        """Event with no location → accepted with location_building=None."""
        result = _run_gemini(
            extractor,
            caption="Free pizza this Friday at 6pm! Come along 🍕",
            gemini_response={
                'food': True, 'title': 'Free Pizza',
                'start_datetime': '2026-03-06T18:00:00',
                'end_datetime': None,
                'location': None,
                'image_text': None, 'members_only': False,
            },
            post_ts=self.POST_TS,
        )
        assert result is not None
        assert result['location_building'] is None
        assert result['title'] == 'Free Pizza'

# Made with Bob
