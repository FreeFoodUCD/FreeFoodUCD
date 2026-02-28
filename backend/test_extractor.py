"""
Unit tests for EventExtractor classifier improvements.
Run with: cd backend && python test_extractor.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.nlp.extractor import EventExtractor

extractor = EventExtractor()

test_cases = [
    # (caption, expected_result, description)

    # FN1: "We'll bring" provision context
    (
        "We have a busy week coming up, so we're kicking it off with a crafternoon on Monday in the Red Room!! Bring your WIPs!! Bring your friends!! We'll bring the supplies and coffee ☕️🎨",
        True,
        "FN1: crafternoon — we'll bring coffee (weak keyword + provision)"
    ),

    # FP1: Bake sale / charity food sale
    (
        "Charity cookie sale! 🍪 Homemade cookies and brownies! All proceeds go to charity.",
        False,
        "FP1: charity cookie sale — cookies keyword + cookie sale negation"
    ),

    # FP3: 'wrap up' false positive
    (
        "Join us to wrap up the semester 🎉 Student Centre Friday 7pm",
        False,
        "FP3: wrap up semester — 'wrap' removed from strong keywords"
    ),

    # FP2: Bake-off competition (food activity, no provision)
    (
        "Bake-Off competition! Bake a cake and compete for glory! No entry fee. Student Centre Friday 4pm.",
        False,
        "FP2: bake-off competition — food activity, no provision"
    ),

    # FP2 override: Cookie decorating workshop WITH provision
    (
        "Cookie decorating workshop! 🍪 We'll provide the cookies and icing. Student Centre Saturday 2pm.",
        True,
        "FP2 override: cookie decorating — provision override fires"
    ),

    # FP4: BYOF snacks negation
    (
        "Movie night 🎬 bring your own snacks! Student Centre.",
        False,
        "FP4: BYOF snacks — negation now covers snacks"
    ),

    # FP5: refreshments for purchase
    (
        "Free talk this Thursday! Light refreshments available for purchase after.",
        False,
        "FP5: refreshments for purchase — negated by 'for purchase' pattern"
    ),

    # Post 4: strong "free food" keyword (should still pass)
    (
        "Free food throughout the day 📍 Astra Hall, UCD Belfield. Spaces are limited, please register via link in bio.",
        True,
        "Post 4: free food + Astra Hall — still passes correctly"
    ),

    # FN2: "food and drinks" new compound keyword
    (
        "Food and drinks this Friday at Newman 6pm! Come join us.",
        True,
        "FN2: food and drinks — new compound strong keyword"
    ),

    # FN2: "light bites" new keyword
    (
        "Light bites provided after the talk. Room G15, Newman.",
        True,
        "FN2: light bites — new strong keyword"
    ),

    # Members-only + pizza (should pass)
    (
        "Members only 🍕 pizza provided, Newman 7pm",
        True,
        "Members only pizza — passes (members_only flagged separately)"
    ),

    # Post 2: entry fee €15 (should fail)
    (
        "The entry fee is €15. Anyone with a valid student ID may enter. Entry includes: A free pizza lunch",
        False,
        "Post 2: €15 entry fee — paid event overrides free pizza"
    ),

    # Post 5: snacks + pancakes (should pass)
    (
        "tea, coffee and snacks available after!! ...free pancakes for pancake tuesday 👀",
        True,
        "Post 5: tea/coffee/snacks + free pancakes — passes correctly"
    ),

    # Wrap emoji should still work (remapped to sandwich)
    (
        "🌯 sandwiches available at the event. Student Centre Wednesday.",
        True,
        "Wrap emoji remapped to sandwich — still strong keyword"
    ),

    # "grub" new informal keyword
    (
        "There'll be free grub after the AGM! Newman Building 5pm.",
        True,
        "FN2: grub — new informal strong keyword"
    ),

    # C1: fundraiser — chocolate fundraiser should be rejected
    (
        "Chocolate fundraiser for the club! Newman Monday 6pm",
        False,
        "C1: fundraiser — 'fundraiser' keyword → paid event rejection"
    ),

    # C2: virtual event with no UCD location — should be rejected
    (
        "Virtual info session! Free pizza for the host 🍕",
        False,
        "C2: virtual event + no UCD location → rejected"
    ),

    # C2 hybrid: Zoom + UCD location — should pass
    (
        "Zoom talk with free food Newman Building 6pm (hybrid)",
        True,
        "C2 hybrid: zoom + UCD location → passes"
    ),

    # L2: Science West alias
    (
        "Free snacks in Science West 4pm",
        True,
        "L2: science west alias → on-campus location recognised"
    ),

    # L3: Village Kitchen
    (
        "Free lunch in Village Kitchen, UCD Village!",
        True,
        "L3: village kitchen → on-campus location recognised"
    ),

    # ── Phase A new test cases ─────────────────────────────────────────────────

    # A3: Past-tense recap — should be REJECTED
    (
        "Thanks for coming to our event last night — pizza was amazing! See you next time 🍕",
        False,
        "A3-1: past-tense recap — 'thanks for coming' + 'pizza was amazing'"
    ),
    (
        "Hope everyone had a great time! We served some delicious coffee and cake 🎂",
        False,
        "A3-2: past-tense — 'hope everyone had' triggers recap filter"
    ),
    (
        "What a brilliant evening! Great to see everyone who joined us 🙌",
        False,
        "A3-3: past-tense — 'great to see everyone' without food still shouldn't sneak through"
    ),

    # A3: Future-tense posts with past-sounding words — should NOT be rejected
    (
        "We've been busy planning our coffee morning this Friday! Biscuits and tea provided, Newman 2pm.",
        True,
        "A3-4: 'we've been' is present-perfect, not a recap — should ACCEPT"
    ),

    # A5: Staff/committee-only — should be REJECTED
    (
        "Exec training session this Saturday — lunch provided for committee members only.",
        False,
        "A5-1: exec training + committee members only → staff filter"
    ),
    (
        "Committee only meeting tonight! Pizza provided. Engineering Building 6pm.",
        False,
        "A5-2: 'committee only' → staff filter fires"
    ),
    (
        "Volunteers only event — sandwiches and drinks. Student Centre 5pm.",
        False,
        "A5-3: 'volunteers only' → staff filter"
    ),

    # A5: General society meeting (NOT committee-only) — should ACCEPT
    (
        "General meeting open to all members! Tea and biscuits provided. Newman 7pm.",
        True,
        "A5-4: open to all members — not committee-only → ACCEPT"
    ),

    # A6: Score-based paid penalty — small fee without ticket language should ACCEPT
    (
        "UCD 5K Fun Run — €5 registration, refreshments provided afterwards! All welcome.",
        True,
        "A6-1: €5 registration (no ticket language) + refreshments → ACCEPT"
    ),
    (
        "Coffee morning this Friday — €2 suggested donation, biscuits and tea available. Newman 10am.",
        True,
        "A6-2: €2 suggested donation + coffee/biscuits → ACCEPT"
    ),

    # A6: Membership price with member context — should ACCEPT
    (
        "UCD Economics Society members welcome! Annual membership €3. Free pizza at our first meeting.",
        True,
        "A6-3: membership €3 + member context + free pizza → ACCEPT"
    ),

    # A6: Large price (€15) without free-food → should REJECT
    (
        "Society Christmas dinner €15 per head — 3-course meal. Student Centre Friday.",
        False,
        "A6-4: €15 dinner, no free-food override → REJECT"
    ),

    # A6: Ticket language with price → should REJECT
    (
        "Get your tickets now — €8 a pop, includes refreshments! Book via link in bio.",
        False,
        "A6-5: 'get your tickets' + €8 → REJECT (ticket language)"
    ),

    # A6: €30 fundraiser gala → should REJECT (fundraiser hard-blocks even with free pizza mention)
    (
        "Gala fundraiser dinner €30 per person. Free pizza reception beforehand for all! Student Centre 7pm.",
        False,
        "A6-6: €30 fundraiser gala — 'fundraiser' hard-blocks; free pizza mention doesn't override"
    ),

    # A2: Context modifiers — "included", "on us", "kindly sponsored"
    (
        "Tea, coffee and snacks will be provided at our next meeting. Newman Building Tuesday 6pm.",
        True,
        "A2-1: 'provided' context modifier + tea/coffee/snacks → ACCEPT"
    ),
    (
        "Lunch is included for all attendees. Join us at the Student Centre Thursday.",
        True,
        "A2-2: 'included' context modifier + lunch → ACCEPT"
    ),
    (
        "Coffee and biscuits on us! Come to our open session at the Science Building Friday.",
        True,
        "A2-3: 'on us' context modifier + coffee/biscuits → ACCEPT"
    ),
    (
        "Kindly sponsored refreshments at our talk. UCD O'Brien Centre Thursday 5pm.",
        True,
        "A2-4: 'kindly sponsored' context modifier + refreshments → ACCEPT"
    ),

    # A4: Implied-free event types
    (
        "Welcome Reception for all new UCD students! Student Centre Monday 3pm.",
        True,
        "A4-1: 'welcome reception' implied-free event type → ACCEPT"
    ),
    (
        "UCD Freshers Fair this week! Come visit all the societies. Astra Hall.",
        True,
        "A4-2: 'freshers fair' implied-free event type → ACCEPT"
    ),

    # Members-only: should ACCEPT with flag (not rejected as paid/restricted)
    (
        "For members only 🍕 Pizza night this Thursday. Engineering Building 7pm.",
        True,
        "Members-1: 'for members only' + pizza → ACCEPT (members_only flag set)"
    ),
    (
        "Members welcome! Sandwiches and soft drinks provided. Newman G15 Wednesday 5pm.",
        True,
        "Members-2: 'members welcome' + sandwiches → ACCEPT"
    ),

    # ── Screenshot-inspired real-world posts ───────────────────────────────────

    # SCREENSHOT POST A: "Free Cookies" — NAMSOC (namsocucd)
    # All-caps caption with typo "FEBUARY" — preprocessing must normalise correctly
    (
        "COME JOIN US FOR FREE COOKIES ON THE 4TH OF FEBUARY IN HARMONY",
        True,
        "SC-A1: all-caps + typo 'FEBUARY' — 'free cookies' still recognised"
    ),
    # Cookie emoji → mapped to 'cookies' strong keyword; image text "free sweet treat"
    (
        "🍪 Free sweet treat? Come grab cookies in Harmony Lounge! 4th Feb 11-11:30am.",
        True,
        "SC-A2: cookie emoji + 'free sweet treat' → ACCEPT"
    ),

    # SCREENSHOT POST B: "Week 24" — NAMSOC weekly schedule
    # Pancake Tuesday: 'pancakes' is a strong keyword — no 'free' word needed
    (
        "Pancake Tuesday — come join us for some pancakes and fun on Tuesday morning! Harmony Studio 11am.",
        True,
        "SC-B1: 'pancakes' strong keyword without explicit 'free' → ACCEPT"
    ),
    # Coffee Morning: 'coffee morning' is an exact strong keyword phrase
    (
        "Coffee Morning ☕ Pop in for a coffee and chat to catch up and chill! Meeting rooms 8:30-9:30am.",
        True,
        "SC-B2: 'coffee morning' exact strong-keyword phrase → ACCEPT"
    ),
    # Coppers Night Out: "free entry" is nightlife, NOT free food — should REJECT
    (
        "Coppers Night Out 🎉 Free entry every Thursday before 23:30! See you there.",
        False,
        "SC-B3: 'free entry' nightclub (Coppers) — no food keyword → REJECT"
    ),
    # Full caption for Post B: mentions pancakes + coffee morning in combined text → ACCEPT
    (
        "Come along to our amazing events this week — Pancake Tuesday to celebrate one of the best days of the year, a coffee morning to wake you up before your lecture 🤣 and a healthcare debate! Student Centre.",
        True,
        "SC-B4: multi-event caption — 'pancakes' + 'coffee morning' in combined caption → ACCEPT"
    ),

    # ── Missing emoji tests ─────────────────────────────────────────────────────

    # Pizza emoji maps to 'pizza' (strong keyword) via emoji preprocessing
    (
        "🍕 provided tonight — come join us! Newman Building 7pm.",
        True,
        "EMO-1: pizza emoji → 'pizza' strong keyword after emoji map → ACCEPT"
    ),

    # ── Missing context modifiers (A2) ─────────────────────────────────────────

    # 'complimentary' is a context modifier that upgrades weak keyword 'tea'/'coffee'
    (
        "Complimentary tea and coffee after the talk. Newman Building Thursday 5pm.",
        True,
        "A2-5: 'complimentary' context modifier + tea/coffee → ACCEPT"
    ),
    # 'at no cost' context modifier
    (
        "Coffee and snacks at no cost. Science Building Thursday 4pm.",
        True,
        "A2-6: 'at no cost' context modifier + coffee/snacks → ACCEPT"
    ),
    # 'brought to you by' context modifier
    (
        "Refreshments brought to you by our sponsors. Student Centre Wednesday 6pm.",
        True,
        "A2-7: 'brought to you by' context modifier + refreshments → ACCEPT"
    ),

    # ── Missing staff-only patterns (A5) ───────────────────────────────────────

    # 'exec meeting' triggers _is_staff_only (exec meeting/training/session pattern)
    (
        "Exec meeting Thursday evening — pizza for all exec members! Engineering Building.",
        False,
        "A5-5: 'exec meeting' → staff filter fires even with pizza → REJECT"
    ),
    # 'board meeting' triggers _is_staff_only
    (
        "Board meeting this Friday — lunch provided. Newman Building 1pm.",
        False,
        "A5-6: 'board meeting' → staff filter fires → REJECT"
    ),

    # ── Missing weak-keyword edge cases ────────────────────────────────────────

    # 'refreshers' is a weak keyword — no context modifier → REJECT
    (
        "Refreshers Week info session Tuesday 3pm. Come meet the committee!",
        False,
        "WK-1: 'refreshers' weak keyword, no context modifier → REJECT"
    ),

    # ── Missing BYOF / potluck ─────────────────────────────────────────────────

    # 'potluck' is a strong keyword — no 'free' needed
    (
        "Potluck this Friday! Bring a dish and meet the society. Engineering Building 6pm.",
        True,
        "BYOF-1: 'potluck' strong keyword → ACCEPT"
    ),

    # ── Missing food-sale with small price (A6) ────────────────────────────────

    # food-sale keyword 'bake sale' hard-blocks even with €2
    (
        "€2 charity bake sale for club funds! All welcome. Student Centre Wednesday.",
        False,
        "A6-7: 'bake sale' food-sale keyword overrides small €2 price → REJECT"
    ),

    # ── Missing location / context edge cases ──────────────────────────────────

    # "food festival" in off-campus area (Ranelagh) → off-campus location → REJECT
    (
        "Food festival in Ranelagh this weekend — loads of amazing food stalls!",
        False,
        "LOC-1: food festival off-campus ('Ranelagh') → REJECT"
    ),
    # Food mentioned as pre-event activity (not provision), no context modifier
    (
        "Grab some food before you come to our social! Newman Building 8pm.",
        False,
        "CTX-1: 'food' weak keyword + no provision context → REJECT"
    ),
]

passed = 0
failed = 0
for caption, expected, description in test_cases:
    result = extractor.classify_event(caption)
    status = "PASS" if result == expected else "FAIL"
    if result == expected:
        passed += 1
    else:
        failed += 1
        reason = extractor.get_rejection_reason(caption)
        print(f"[{status}] {description}")
        print(f"       Expected: {expected}, Got: {result}, Reason: {reason}")
        print()

print(f"\n{'='*60}")
print(f"Results: {passed}/{len(test_cases)} passed, {failed} failed")
