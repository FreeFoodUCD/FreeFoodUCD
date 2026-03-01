"""
Pytest suite for EventExtractor NLP classifier.
Migrated from backend/test_extractor.py — all 108 tests, each shown individually.

Run with:
    cd backend && pytest tests/nlp/test_classifier.py -v
"""
import sys
import os

import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.nlp.extractor import EventExtractor
import app.services.nlp.llm_classifier as _llm_mod


# ── Shared fixture ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def extractor():
    return EventExtractor()


# ── classify_event() parametrized tests (79 cases) ────────────────────────────

CLASSIFY_CASES = [
    # FN1: "We'll bring" provision context
    (
        "We have a busy week coming up, so we're kicking it off with a crafternoon on Monday in the Red Room!! Bring your WIPs!! Bring your friends!! We'll bring the supplies and coffee ☕️🎨",
        True,
        "FN1: crafternoon — we'll bring coffee (weak keyword + provision)",
    ),
    # FP1: Bake sale / charity food sale
    (
        "Charity cookie sale! 🍪 Homemade cookies and brownies! All proceeds go to charity.",
        False,
        "FP1: charity cookie sale — cookies keyword + cookie sale negation",
    ),
    # FP3: 'wrap up' false positive
    (
        "Join us to wrap up the semester 🎉 Student Centre Friday 7pm",
        False,
        "FP3: wrap up semester — 'wrap' removed from strong keywords",
    ),
    # FP2: Bake-off competition (food activity, no provision)
    (
        "Bake-Off competition! Bake a cake and compete for glory! No entry fee. Student Centre Friday 4pm.",
        False,
        "FP2: bake-off competition — food activity, no provision",
    ),
    # FP2 override: Cookie decorating workshop WITH provision
    (
        "Cookie decorating workshop! 🍪 We'll provide the cookies and icing. Student Centre Saturday 2pm.",
        True,
        "FP2 override: cookie decorating — provision override fires",
    ),
    # FP4: BYOF snacks negation
    (
        "Movie night 🎬 bring your own snacks! Student Centre.",
        False,
        "FP4: BYOF snacks — negation now covers snacks",
    ),
    # FP5: refreshments for purchase
    (
        "Free talk this Thursday! Light refreshments available for purchase after.",
        False,
        "FP5: refreshments for purchase — negated by 'for purchase' pattern",
    ),
    # Post 4: strong "free food" keyword
    (
        "Free food throughout the day 📍 Astra Hall, UCD Belfield. Spaces are limited, please register via link in bio.",
        True,
        "Post 4: free food + Astra Hall — still passes correctly",
    ),
    # FN2: "food and drinks" new compound keyword
    (
        "Food and drinks this Friday at Newman 6pm! Come join us.",
        True,
        "FN2: food and drinks — new compound strong keyword",
    ),
    # FN2: "light bites" new keyword
    (
        "Light bites provided after the talk. Room G15, Newman.",
        True,
        "FN2: light bites — new strong keyword",
    ),
    # Members-only + pizza
    (
        "Members only 🍕 pizza provided, Newman 7pm",
        True,
        "Members only pizza — passes (members_only flagged separately)",
    ),
    # Post 2: entry fee €15
    (
        "The entry fee is €15. Anyone with a valid student ID may enter. Entry includes: A free pizza lunch",
        False,
        "Post 2: €15 entry fee — paid event overrides free pizza",
    ),
    # Post 5: snacks + pancakes
    (
        "tea, coffee and snacks available after!! ...free pancakes for pancake tuesday 👀",
        True,
        "Post 5: tea/coffee/snacks + free pancakes — passes correctly",
    ),
    # Wrap emoji remapped to sandwich
    (
        "🌯 sandwiches available at the event. Student Centre Wednesday.",
        True,
        "Wrap emoji remapped to sandwich — still strong keyword",
    ),
    # "grub" new informal keyword
    (
        "There'll be free grub after the AGM! Newman Building 5pm.",
        True,
        "FN2: grub — new informal strong keyword",
    ),
    # C1: fundraiser
    (
        "Chocolate fundraiser for the club! Newman Monday 6pm",
        False,
        "C1: fundraiser — 'fundraiser' keyword → paid event rejection",
    ),
    # C2: virtual event with no UCD location
    (
        "Virtual info session! Free pizza for the host 🍕",
        False,
        "C2: virtual event + no UCD location → rejected",
    ),
    # C2 hybrid: Zoom + UCD location
    (
        "Zoom talk with free food Newman Building 6pm (hybrid)",
        True,
        "C2 hybrid: zoom + UCD location → passes",
    ),
    # L2: Science West alias
    (
        "Free snacks in Science West 4pm",
        True,
        "L2: science west alias → on-campus location recognised",
    ),
    # L3: Village Kitchen
    (
        "Free lunch in Village Kitchen, UCD Village!",
        True,
        "L3: village kitchen → on-campus location recognised",
    ),
    # A3: Past-tense recap
    (
        "Thanks for coming to our event last night — pizza was amazing! See you next time 🍕",
        False,
        "A3-1: past-tense recap — 'thanks for coming' + 'pizza was amazing'",
    ),
    (
        "Hope everyone had a great time! We served some delicious coffee and cake 🎂",
        False,
        "A3-2: past-tense — 'hope everyone had' triggers recap filter",
    ),
    (
        "What a brilliant evening! Great to see everyone who joined us 🙌",
        False,
        "A3-3: past-tense — 'great to see everyone' without food still shouldn't sneak through",
    ),
    # A3: Future-tense with past-sounding words
    (
        "We've been busy planning our coffee morning this Friday! Biscuits and tea provided, Newman 2pm.",
        True,
        "A3-4: 'we've been' is present-perfect, not a recap — should ACCEPT",
    ),
    # A5: Staff/committee-only
    (
        "Exec training session this Saturday — lunch provided for committee members only.",
        False,
        "A5-1: exec training + committee members only → staff filter",
    ),
    (
        "Committee only meeting tonight! Pizza provided. Engineering Building 6pm.",
        False,
        "A5-2: 'committee only' → staff filter fires",
    ),
    (
        "Volunteers only event — sandwiches and drinks. Student Centre 5pm.",
        False,
        "A5-3: 'volunteers only' → staff filter",
    ),
    # A5: General society meeting (NOT committee-only)
    (
        "General meeting open to all members! Tea and biscuits provided. Newman 7pm.",
        True,
        "A5-4: open to all members — not committee-only → ACCEPT",
    ),
    # A6: Small fee without ticket language
    (
        "UCD 5K Fun Run — €5 registration, refreshments provided afterwards! All welcome.",
        True,
        "A6-1: €5 registration (no ticket language) + refreshments → ACCEPT",
    ),
    (
        "Coffee morning this Friday — €2 suggested donation, biscuits and tea available. Newman 10am.",
        True,
        "A6-2: €2 suggested donation + coffee/biscuits → ACCEPT",
    ),
    # A6: Membership price with member context
    (
        "UCD Economics Society members welcome! Annual membership €3. Free pizza at our first meeting.",
        True,
        "A6-3: membership €3 + member context + free pizza → ACCEPT",
    ),
    # A6: Large price without free-food
    (
        "Society Christmas dinner €15 per head — 3-course meal. Student Centre Friday.",
        False,
        "A6-4: €15 dinner, no free-food override → REJECT",
    ),
    # A6: Ticket language with price
    (
        "Get your tickets now — €8 a pop, includes refreshments! Book via link in bio.",
        False,
        "A6-5: 'get your tickets' + €8 → REJECT (ticket language)",
    ),
    # A6: €30 fundraiser gala
    (
        "Gala fundraiser dinner €30 per person. Free pizza reception beforehand for all! Student Centre 7pm.",
        False,
        "A6-6: €30 fundraiser gala — 'fundraiser' hard-blocks; free pizza mention doesn't override",
    ),
    # A2: Context modifiers
    (
        "Tea, coffee and snacks will be provided at our next meeting. Newman Building Tuesday 6pm.",
        True,
        "A2-1: 'provided' context modifier + tea/coffee/snacks → ACCEPT",
    ),
    (
        "Lunch is included for all attendees. Join us at the Student Centre Thursday.",
        True,
        "A2-2: 'included' context modifier + lunch → ACCEPT",
    ),
    (
        "Coffee and biscuits on us! Come to our open session at the Science Building Friday.",
        True,
        "A2-3: 'on us' context modifier + coffee/biscuits → ACCEPT",
    ),
    (
        "Kindly sponsored refreshments at our talk. UCD O'Brien Centre Thursday 5pm.",
        True,
        "A2-4: 'kindly sponsored' context modifier + refreshments → ACCEPT",
    ),
    # A4: Implied-free event types
    (
        "Welcome Reception for all new UCD students! Student Centre Monday 3pm.",
        True,
        "A4-1: 'welcome reception' implied-free event type → ACCEPT",
    ),
    (
        "UCD Freshers Fair this week! Come visit all the societies. Astra Hall.",
        True,
        "A4-2: 'freshers fair' implied-free event type → ACCEPT",
    ),
    # Members-only with flag
    (
        "For members only 🍕 Pizza night this Thursday. Engineering Building 7pm.",
        True,
        "Members-1: 'for members only' + pizza → ACCEPT (members_only flag set)",
    ),
    (
        "Members welcome! Sandwiches and soft drinks provided. Newman G15 Wednesday 5pm.",
        True,
        "Members-2: 'members welcome' + sandwiches → ACCEPT",
    ),
    # Screenshot-inspired posts
    (
        "COME JOIN US FOR FREE COOKIES ON THE 4TH OF FEBUARY IN HARMONY",
        True,
        "SC-A1: all-caps + typo 'FEBUARY' — 'free cookies' still recognised",
    ),
    (
        "🍪 Free sweet treat? Come grab cookies in Harmony Lounge! 4th Feb 11-11:30am.",
        True,
        "SC-A2: cookie emoji + 'free sweet treat' → ACCEPT",
    ),
    (
        "Pancake Tuesday — come join us for some pancakes and fun on Tuesday morning! Harmony Studio 11am.",
        True,
        "SC-B1: 'pancakes' strong keyword without explicit 'free' → ACCEPT",
    ),
    (
        "Coffee Morning ☕ Pop in for a coffee and chat to catch up and chill! Meeting rooms 8:30-9:30am.",
        True,
        "SC-B2: 'coffee morning' exact strong-keyword phrase → ACCEPT",
    ),
    (
        "Coppers Night Out 🎉 Free entry every Thursday before 23:30! See you there.",
        False,
        "SC-B3: 'free entry' nightclub (Coppers) — no food keyword → REJECT",
    ),
    (
        "Come along to our amazing events this week — Pancake Tuesday to celebrate one of the best days of the year, a coffee morning to wake you up before your lecture 🤣 and a healthcare debate! Student Centre.",
        True,
        "SC-B4: multi-event caption — 'pancakes' + 'coffee morning' in combined caption → ACCEPT",
    ),
    # Emoji tests
    (
        "🍕 provided tonight — come join us! Newman Building 7pm.",
        True,
        "EMO-1: pizza emoji → 'pizza' strong keyword after emoji map → ACCEPT",
    ),
    # More context modifiers (A2)
    (
        "Complimentary tea and coffee after the talk. Newman Building Thursday 5pm.",
        True,
        "A2-5: 'complimentary' context modifier + tea/coffee → ACCEPT",
    ),
    (
        "Coffee and snacks at no cost. Science Building Thursday 4pm.",
        True,
        "A2-6: 'at no cost' context modifier + coffee/snacks → ACCEPT",
    ),
    (
        "Refreshments brought to you by our sponsors. Student Centre Wednesday 6pm.",
        True,
        "A2-7: 'brought to you by' context modifier + refreshments → ACCEPT",
    ),
    # Missing staff-only patterns (A5)
    (
        "Exec meeting Thursday evening — pizza for all exec members! Engineering Building.",
        False,
        "A5-5: 'exec meeting' → staff filter fires even with pizza → REJECT",
    ),
    (
        "Board meeting this Friday — lunch provided. Newman Building 1pm.",
        False,
        "A5-6: 'board meeting' → staff filter fires → REJECT",
    ),
    # Weak-keyword edge cases
    (
        "Refreshers Week info session Tuesday 3pm. Come meet the committee!",
        False,
        "WK-1: 'refreshers' weak keyword, no context modifier → REJECT",
    ),
    # BYOF / potluck
    (
        "Potluck this Friday! Bring a dish and meet the society. Engineering Building 6pm.",
        True,
        "BYOF-1: 'potluck' strong keyword → ACCEPT",
    ),
    # Food-sale with small price (A6)
    (
        "€2 charity bake sale for club funds! All welcome. Student Centre Wednesday.",
        False,
        "A6-7: 'bake sale' food-sale keyword overrides small €2 price → REJECT",
    ),
    # Location / context edge cases
    (
        "Food festival in Ranelagh this weekend — loads of amazing food stalls!",
        False,
        "LOC-1: food festival off-campus ('Ranelagh') → REJECT",
    ),
    (
        "Grab some food before you come to our social! Newman Building 8pm.",
        False,
        "CTX-1: 'food' weak keyword + no provision context → REJECT",
    ),
    # A7: Social-media giveaway
    (
        "Giveaway Time!!! We are doing a Giveaway for a box of chocolate fudge brownies. "
        "How to Enter: 1) Follow this account 2) Share this post to your story "
        "3) Tag 3 friends in the comments. Giveaway Winner will be announced March 2nd 1pm!",
        False,
        "G1: social media giveaway — 'giveaway' keyword → reject despite 'chocolate'",
    ),
    # A8: kaffeeklatsch
    (
        "KAFFEEKLATSCH — Join us for tea, coffee and snacks! Global Lounge, Thursday 14:00-16:00.",
        True,
        "A8-1: 'kaffeeklatsch' strong keyword → ACCEPT",
    ),
    (
        "Kaffeeklatsch with the German Society this Friday. Come hang out!",
        True,
        "A8-2: 'kaffeeklatsch' alone (strong keyword, no other food term) → ACCEPT",
    ),
    # A9: free samples / handing out samples
    (
        "We're handing out samples of our new Indian and Thai dishes — come try them! UCD Food Hall.",
        True,
        "A9-1: 'handing out samples' strong keyword → ACCEPT",
    ),
    (
        "Free samples of our new menu items available at the UCD Food Hall today!",
        True,
        "A9-2: 'free samples' strong keyword → ACCEPT",
    ),
    # A10: 'night out' removed from nightlife_keywords
    (
        "Night out this Friday — everyone welcome! Student Bar 10pm.",
        False,
        "A10-1: 'night out' alone (no food keyword) → REJECT (no food found)",
    ),
    (
        "Pancake Tuesday morning + Night Out Friday! Come for the pancakes, Student Centre 11am.",
        True,
        "A10-2: 'pancakes' (strong) + 'night out' → ACCEPT after A10 (night_out removed from nightlife filter)",
    ),
    (
        "Club night at Coppers! Refreshments provided before midnight. Pre drinks at 10pm.",
        False,
        "A10-3: 'club night' + 'pre drinks' still in nightlife filter → REJECT",
    ),
    # A12: Religious event hard filter
    (
        "Ramadan Mubarak! 🌙 Wishing everyone a blessed month.",
        False,
        "A12-1: Ramadan mention, no food keywords → REJECT (religious filter)",
    ),
    (
        "Join us this Ramadan to spend a wonderful Iftar together. "
        "We will be breaking the fast with a scrumptious serving of food. Astra Hall 7pm.",
        False,
        "A12-2: Iftar with food mention → REJECT (religious filter, policy override)",
    ),
    # A13a: Explicit free-event declaration
    (
        "Join us this Wednesday for some pizza, cans, and a bit of countdown. "
        "*This is a free event* Newman Building 6pm",
        True,
        "A13a: 'this is a free event' override + pizza → ACCEPT",
    ),
    # A13b: Ticket language tightening
    (
        "After the chaos of Science Day and SciBall ticket sales, we're slowing things "
        "down this week with a Coffee Morning. Drop by for a cup of coffee!",
        True,
        "A13b: 'SciBall ticket sales' not paid ticket language; Coffee Morning → ACCEPT",
    ),
    # A14: 'ball' standalone replaced by specific phrases
    (
        "Hey PhysSoc! Come by the Student Centre for free caffeine and biscuits "
        "at our weekly coffee hour. Also our annual Physics Ball is coming up next month.",
        True,
        "A14: 'Physics Ball' not compound nightlife phrase; biscuits → ACCEPT",
    ),
    (
        "Annual Ball tickets now on sale! Grab yours before they sell out. "
        "Free drinks included for early birds.",
        False,
        "A14: 'annual ball' compound nightlife keyword → REJECT",
    ),
    # KW: Keyword demotions — goodies + acai bowl now weak
    (
        "We'll have goodies for everyone at Thursday's social",
        True,
        "KW-1: 'we'll have goodies' — provision regex fires → ACCEPT",
    ),
    (
        "Goodies and prizes up for grabs at our quiz night",
        False,
        "KW-2: 'goodies' = prizes context, no free-provision signal → REJECT",
    ),
    (
        "Free acai bowl for all attendees at the wellness fair",
        True,
        "KW-3: 'free acai bowl' — 'free' fires weak trigger → ACCEPT",
    ),
    (
        "Try our new acai bowl at the campus café — only €6",
        False,
        "KW-4: acai bowl for sale, no free context → REJECT",
    ),
    (
        "Açaí bowl provided at our sports society recovery session",
        True,
        "KW-5: 'açaí bowl' + 'provided' context modifier → ACCEPT",
    ),
    (
        "Açaí bowl €7 at the UCD food market this Saturday",
        False,
        "KW-6: açaí bowl for sale → REJECT",
    ),
]


@pytest.mark.parametrize("caption,expected,desc", CLASSIFY_CASES, ids=[c[2] for c in CLASSIFY_CASES])
def test_classify_event(extractor, caption, expected, desc):
    _preview = repr(caption[:60])
    assert extractor.classify_event(caption) == expected, (
        f"classify_event({_preview}) expected {expected}; "
        f"reason: {extractor.get_rejection_reason(caption)}"
    )


# ── B5: TBC detection in extract_event() ─────────────────────────────────────

B5_CASES = [
    (
        "Free pizza at our next meeting! Time TBC — we'll update you soon. Student Centre.",
        None,
        "B5-1: strong food keyword + 'Time TBC' → extract_event returns None",
    ),
    (
        "Coffee morning coming up! Date and time TBA. Location: Newman Building.",
        None,
        "B5-2: strong food keyword + 'TBA' → extract_event returns None",
    ),
    (
        "Join us for snacks and drinks — details to be confirmed, watch this space!",
        None,
        "B5-3: strong food keyword + 'to be confirmed' → extract_event returns None",
    ),
    (
        "Free lunch this Thursday at 1pm! Newman Building G15.",
        dict,
        "B5-4: no TBC phrase → extract_event returns event dict (not None)",
    ),
]


@pytest.mark.parametrize("caption,expected,desc", B5_CASES, ids=[c[2] for c in B5_CASES])
def test_b5_tbc_detection(extractor, caption, expected, desc):
    result = extractor.extract_event(caption)
    _prev = repr(caption[:60])
    if expected is None:
        assert result is None, f"Expected None for {_prev}, got {result}"
    else:
        assert isinstance(result, dict), f"Expected dict for {_prev}, got {type(result)}"


# ── A11: segment_post_text() ──────────────────────────────────────────────────

_NAMSOC_TEXT = (
    "PANCAKE TUESDAY\n"
    "Come join us for some pancakes on Tuesday morning!\n"
    "Harmony Studio 11am-12pm.\n\n"
    "COFFEE MORNING\n"
    "Pop in for a coffee and chat! Meeting rooms 8:30-9:30am.\n\n"
    "HEALTHCARE DEBATE\n"
    "Join our healthcare debate team! Fitzgerald chamber 1pm-2pm.\n\n"
    "COPPERS NIGHT OUT\n"
    "Free entry every Thursday before 23:30! See you there at Coppers nightclub."
)

_GERMAN_TEXT = (
    "KAFFEEKLATSCH\n"
    "Join us for tea, coffee and snacks in the Global Lounge! Thursday 14:00-16:00.\n\n"
    "GERMAN FOR BEGINNERS\n"
    "Come learn German with us — perfect for absolute beginners. Newman Building G15 Tuesday 6pm."
)

_SINGLE_TEXT = "Come for free pizza at Newman Building Friday 6pm! All welcome."

A11_CASES = [
    (_NAMSOC_TEXT, 4, "A11-1: NAMSOC schedule → 4 segments"),
    (_GERMAN_TEXT, 2, "A11-2: German Soc → 2 segments"),
    (_SINGLE_TEXT, 1, "A11-3: Normal short caption → 1 segment (fallback)"),
]


@pytest.mark.parametrize("text,expected_count,desc", A11_CASES, ids=[c[2] for c in A11_CASES])
def test_a11_segmentation(extractor, text, expected_count, desc):
    segs = extractor.segment_post_text(text)
    assert len(segs) == expected_count, (
        f"Expected {expected_count} segments, got {len(segs)}: {[s[:40] for s in segs]}"
    )


def test_a11_namsoc_segment_classify(extractor):
    """A11 inline: each NAMSOC segment classified correctly."""
    segs = extractor.segment_post_text(_NAMSOC_TEXT)
    expected = [True, True, False, False]  # pancakes, coffee morning, debate, coppers
    for i, (seg, exp) in enumerate(zip(segs, expected)):
        got = extractor.classify_event(seg)
        assert got == exp, (
            f"NAMSOC segment {i}: expected {exp}, got {got}\n  Segment: {seg[:80]!r}"
        )


# ── Screenshot-based real-world tests ────────────────────────────────────────

SC_CASES = [
    (
        "TUESDAY COFFEE MORNING! AGAIN! And this time it's final; our coffee mornings for this term will be held in Newman Basement every Tuesday.\n\n[Image Text]\nUCD ARTS SOC COFFEE MORNING Free coffee Free tea Free snacks Good company! NEWMAN BASEMENT 11AM-1PM",
        True,
        "SC-IMG3965: Arts Soc Coffee Morning — 'coffee morning' strong keyword → ACCEPT",
    ),
    (
        "Week 6 is here! Another week, another lineup of good events and even better company. We've got lots in store and we're so excited to share it all with you. Make sure to stay tuned for everything coming up — you won't want to miss it!\n\n[Image Text]\nWEEK 6 24th COFFEE MORNING NEWMAN BASEMENT 11 AM-2 PM 25th MOVIE SCREENING APOCALYPSE NOW NEWMAN NT1 5 PM-7:45 PM 27th NATIONAL GALLERY OF IRELAND NATIONAL GALLERY 3 PM-6 PM",
        True,
        "SC-IMG3966: Arts Soc Week 6 schedule — 'coffee morning' only in OCR text → ACCEPT",
    ),
    (
        "Have you tried out the UCD Farmers Market yet? Well now is your chance! Come join us at the UCD Farmers Market this Tuesday the 28th of January from 11am to 3pm on the main concourse. We have a wide variety of stalls selling fresh, local produce, artisan foods, and more! Don't miss out on this amazing opportunity to support local businesses and enjoy some delicious food!",
        False,
        "SC-IMG3967: UCD Farmers Market — 'selling' food-sale context → REJECT",
    ),
    (
        "Mindfulness and Wellbeing Workshop with UCD Student Counselling — free attendance, just register on the website. Link in bio. Newman Building Thursday 2pm.\n\n[Image Text]\nMINDFULNESS AND WELLBEING WORKSHOP REGISTRATION REQUIRED FREE",
        False,
        "SC-IMG3968: Mindfulness Workshop — 'free' = free attendance, no food keyword → REJECT",
    ),
    (
        "To celebrate the end of semester, we are hosting a FREE Christmas Party on Friday the 6th of December! Newman Building G15 at 6pm.\n\n[Image Text]\nFREE CHRISTMAS PARTY FOOD AND DRINKS INCLUDED NEWMAN G15 6TH DECEMBER 6PM",
        True,
        "SC-IMG3969: Christmas Party — 'food and drinks included' in OCR text → ACCEPT",
    ),
    (
        "We'll have refreshments available at our meeting on Wednesday. Feel free to join us at Newman Building at 5pm!\n\n[Image Text]\nWEEKLY MEETING NEWMAN BUILDING 5PM REFRESHMENTS PROVIDED",
        True,
        "SC-IMG3970: Weekly Meeting — 'refreshments provided' in OCR text → ACCEPT",
    ),
    (
        "Come join us in the Blue Room in the Students Union Centre to hear the very interesting Padraic Heneghan discuss some of the current research happening in the Wolfe Lab! Tea, coffee and snacks will be provided! Also if you are looking to become a member of MicroSoc we will be taking on new members at this seminar series (€2 for students, €15 for staff - cash only :D) Thursday, 6th October Blue Room, UCD SU Centre 11:00-12:00",
        True,
        "SC-IMG3971: MicroSoc Seminar — 'snacks will be provided' strong+modifier; €15 is membership not ticket → ACCEPT",
    ),
    (
        "We are going to be hosting a coffee afternoon next Wednesday in collaboration with DrawSoc and MusicSoc. Destress from exams with some free coffee and biscuits! Relax with some music and drawing to take your mind off of exams! Global Lounge 13th November 2.45pm-4.45pm",
        True,
        "SC-IMG3972: NorthSoc Coffee Afternoon — 'coffee afternoon' strong + 'biscuits' strong → ACCEPT",
    ),
    (
        "Join us for a hands-on meal prep session with Healthy UCD x UCD PLAN'EAT x UCD Nutrition Society. Crean Lounge 3rd March 1-3pm Limited spots - first come, first served Scan the QR code or use the link to sign up!\n\n[Image Text]\nFUEL FOR THE WEEK COME AND JOIN US! FREE LUNCH INCLUDED HANDS-ON MEAL PREP SESSION CREAN LOUNGE 3RD MARCH 1-3PM",
        True,
        "SC-IMG3975: Plan'Eat Free Lunch — 'free lunch' strong keyword (OCR only) → ACCEPT",
    ),
    (
        "Join us for a 5K fun run/walk starting and finishing in UCD followed by refreshments. Tickets: €5. All proceeds go to Nurture Africa. When: Tuesday 24/02 at 3pm outside Sports Centre. refreshments kindly sponsored by @avonprotein. Tickets can be purchased by donating €5.",
        False,
        "SC-IMG3976+3977: RADSOC Run 5 — 'Tickets: €5' is ticket language → REJECT despite refreshments",
    ),
    (
        "Join us for a FREE breakfast for all Radiography & Diagnostic Imaging staff and students, kindly organised by the Radiography Section to celebrate world Radiography day. This Thursday 6/11/25 8-11am First come, first served\n\n[Image Text]\nfree Breakfast Charles Institute 8am-11am to celebrate world radiography day",
        True,
        "SC-IMG3978: RADSOC Free Breakfast — 'free breakfast' strong keyword → ACCEPT",
    ),
    (
        "Come along to our amazing events this week — Pancake Tuesday to celebrate one of the best days of the year. The incredible healthcare debate (this will be an interesting one), Then a coffee morning to wake you up before your lecture.\n\n[Image Text]\nWEEK 24 FEBRUARY 17/02 TUE PANCAKE TUESDAY Harmony studio 11:00-12:00 Come join us for some pancakes and fun on Tuesday morning! 17/02 TUE HEALTHCARE DEBATE Fitzgerald chamber 18:00 18/02 WED COFFEE MORNING Meeting rooms 08:30-09:30 Pop in for a coffee and chat to catch up and chill 19/02 THU COPPERS NIGHT OUT Free entry every Thursday before 23:30",
        True,
        "SC-IMG3986: NAMSOC Week 24 — 'pancakes'+'coffee morning' strong; 'night out' no longer blocks after A10 → ACCEPT",
    ),
    (
        "COME JOIN US FOR FREE COOKIES ON THE 4TH OF FEBUARY IN HARMONY\n\n[Image Text]\nWould You Rather Nothing sounds better than free cookies to kick start your day right? Join us in the Harmony Lounge 4th February from 11-11:30am Cookies mandatory questions optional",
        True,
        "SC-IMG3987: NAMSOC Free Cookies — 'cookies' strong keyword → ACCEPT",
    ),
    (
        "We are so excited to announce our events for Finlay Week this year! From a Journalling Workshop to Acai Breakfast, we are gearing up to have a fantastic week in the lead up to International Women's Day. Please do join us at any of our events this coming week!\n\n[Image Text]\nFinlay Week Build up to International Women's Day 2nd-6th March 2026 4 March Acai Breakfast TBC all proceeds to Womens Aid",
        False,
        "SC-IMG3988: Finlay Week Acai Breakfast TBC — 'breakfast' weak, no modifier → classify REJECT (B5 would block extract_event too)",
    ),
    (
        "KAFFEEKLATSCH Monday, March 3rd 14:00-16:00 in the Global Lounge Join us for a relaxed coffee afternoon filled with conversation, games, tea, coffee, snacks and a chance to practice your German (all levels welcome!) GERMAN FOR BEGINNERS Thursday, March 5th 13:00-14:00 in the O'Connor Centre for Learning Room L1.05 Always wanted to learn German but didn't know where to start? This session is perfect for complete beginners.\n\n[Image Text]\nEVENTS WEEK 7 MAR 2 KAFFEEKLATSCH 2:00-4:00 PM GLOBAL LOUNGE MAR 5 GERMAN FOR BEGINNERS 1:00-2:00 PM LLO5 O'CONNOR",
        True,
        "SC-IMG3989+3990: German Soc Kaffeeklatsch — 'kaffeeklatsch' strong (A8) + 'coffee afternoon' + 'snacks' → ACCEPT",
    ),
    (
        "Not had a chance to try out new menu yet? We'll be handing out samples of our new Indian and Thai dishes for you to try! Just come to the Foodhall 12:30pm - 13:30pm to grab one!\n\n[Image Text]\nBLASTA Want to try some of our dishes? We'll be handing out samples of our new Indian and Thai dishes in the Foodhall! Thursday 5th February 12:30pm - 13:30pm",
        True,
        "SC-IMG3991: Food Hall BLASTA — 'handing out samples' strong keyword (A9) → ACCEPT",
    ),
]


@pytest.mark.parametrize("caption,expected,desc", SC_CASES, ids=[c[2] for c in SC_CASES])
def test_screenshot_classify(extractor, caption, expected, desc):
    got = extractor.classify_event(caption)
    assert got == expected, (
        f"classify_event expected {expected}, got {got}; "
        f"reason: {extractor.get_rejection_reason(caption)}"
    )


# ── B6: Vision LLM fallback (mocked) ─────────────────────────────────────────

def _run_b6_extract(extractor, caption, vision_response, image_urls, ocr_low_yield=True):
    """Run extract_event with mocked vision LLM; returns result."""
    mock_llm = MagicMock()
    mock_llm.classify_with_vision.return_value = vision_response

    original_getter = _llm_mod.get_llm_classifier
    _llm_mod.get_llm_classifier = lambda: mock_llm
    try:
        with patch('app.services.nlp.extractor.settings') as mock_settings:
            mock_settings.USE_SCORING_PIPELINE = True
            mock_settings.OPENAI_API_KEY = "sk-fake"
            mock_settings.USE_VISION_FALLBACK = True
            result = extractor.extract_event(
                caption,
                source_type='post',
                image_urls=image_urls,
                ocr_low_yield=ocr_low_yield,
            )
    finally:
        _llm_mod.get_llm_classifier = original_getter
    return result


def test_b6_1_vision_accepts(extractor):
    """B6-1: OCR failed, vision sees 'FREE PIZZA Student Centre 1pm' → ACCEPT."""
    result = _run_b6_extract(
        extractor,
        caption="Join us for our weekly meeting this Tuesday.",
        vision_response={"food": True, "text": "FREE PIZZA Student Centre 1pm Tuesday", "location": "Student Centre", "time": "13:00"},
        image_urls=["https://example.com/fake-image.jpg"],
    )
    assert result is not None


def test_b6_2_vision_rejects_no_food(extractor):
    """B6-2: OCR failed, vision sees no food → REJECT."""
    result = _run_b6_extract(
        extractor,
        caption="Exciting announcement coming soon! Stay tuned.",
        vision_response={"food": False, "text": ""},
        image_urls=["https://example.com/fake-image.jpg"],
    )
    assert result is None


def test_b6_3_hard_filter_blocks(extractor):
    """B6-3: OCR failed, vision food=True but caption has 'Tickets: €20' → hard-filter REJECT."""
    result = _run_b6_extract(
        extractor,
        caption="Tickets: €20 per person. Get yours now before they sell out!",
        vision_response={"food": True, "text": "FREE CANAPES with every ticket", "location": "Newman Building", "time": "19:00"},
        image_urls=["https://example.com/fake-image.jpg"],
    )
    assert result is None


def test_b6_4b_not_low_yield(extractor):
    """B6-4b: ocr_low_yield=False → vision LLM never called even with food vision response."""
    result = _run_b6_extract(
        extractor,
        caption="Don't miss our general meeting this week.",
        vision_response={"food": True, "text": "FREE PIZZA", "location": None, "time": None},
        image_urls=["https://example.com/fake-image.jpg"],
        ocr_low_yield=False,
    )
    assert result is None


# ── B2: Classification Decision Logging ──────────────────────────────────────

def test_b2_1_rule_based_stage(extractor):
    """B2-1: Rule-based accept → stage_reached='rule_based', llm_called=False, llm_food=None."""
    result = extractor.extract_event("Free pizza at Newman Building this Friday 6pm!")
    assert result is not None
    ed = result['extracted_data']
    assert ed['stage_reached'] == 'rule_based'
    assert ed['llm_called'] == False
    assert ed['llm_food'] is None


def _run_b2_llm_text(extractor):
    """Run extract_event with mocked classify_and_extract for text LLM path."""
    mock_llm = MagicMock()
    mock_llm.classify_and_extract.return_value = {
        'food': True, 'location': 'Newman Building', 'time': '13:00'
    }
    original_getter = _llm_mod.get_llm_classifier
    _llm_mod.get_llm_classifier = lambda: mock_llm
    try:
        with patch('app.services.nlp.extractor.settings') as mock_settings:
            mock_settings.USE_SCORING_PIPELINE = True
            mock_settings.OPENAI_API_KEY = "sk-fake"
            mock_settings.USE_VISION_FALLBACK = True
            result = extractor.extract_event("Join us for our weekly coffee catch-up")
    finally:
        _llm_mod.get_llm_classifier = original_getter
    return result


def test_b2_2_llm_text_stage(extractor):
    """B2-2: LLM text path → stage_reached='llm_text', llm_called=True, llm_food=True."""
    result = _run_b2_llm_text(extractor)
    assert result is not None
    ed = result['extracted_data']
    assert ed['stage_reached'] == 'llm_text'
    assert ed['llm_called'] == True
    assert ed['llm_food'] == True
