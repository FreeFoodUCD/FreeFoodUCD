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
    # A7: Social-media giveaway — food keyword present but it's a contest entry
    (
        "Giveaway Time!!! We are doing a Giveaway for a box of chocolate fudge brownies. "
        "How to Enter: 1) Follow this account 2) Share this post to your story "
        "3) Tag 3 friends in the comments. Giveaway Winner will be announced March 2nd 1pm!",
        False,
        "G1: social media giveaway — 'giveaway' keyword → reject despite 'chocolate'"
    ),

    # ── Phase A8: kaffeeklatsch ─────────────────────────────────────────────────
    (
        "KAFFEEKLATSCH — Join us for tea, coffee and snacks! Global Lounge, Thursday 14:00-16:00.",
        True,
        "A8-1: 'kaffeeklatsch' strong keyword → ACCEPT"
    ),
    (
        "Kaffeeklatsch with the German Society this Friday. Come hang out!",
        True,
        "A8-2: 'kaffeeklatsch' alone (strong keyword, no other food term) → ACCEPT"
    ),

    # ── Phase A9: free samples / handing out samples ────────────────────────────
    (
        "We're handing out samples of our new Indian and Thai dishes — come try them! UCD Food Hall.",
        True,
        "A9-1: 'handing out samples' strong keyword → ACCEPT"
    ),
    (
        "Free samples of our new menu items available at the UCD Food Hall today!",
        True,
        "A9-2: 'free samples' strong keyword → ACCEPT"
    ),

    # ── Phase A10: 'night out' removed from nightlife_keywords ──────────────────
    # 'night out' alone (no food) still rejects — fails at no-food-keyword step
    (
        "Night out this Friday — everyone welcome! Student Bar 10pm.",
        False,
        "A10-1: 'night out' alone (no food keyword) → REJECT (no food found)"
    ),
    # 'night out' + strong food keyword → now ACCEPT (not blocked by nightlife filter)
    (
        "Pancake Tuesday morning + Night Out Friday! Come for the pancakes, Student Centre 11am.",
        True,
        "A10-2: 'pancakes' (strong) + 'night out' → ACCEPT after A10 (night_out removed from nightlife filter)"
    ),
    # Actual nightlife terms still block correctly
    (
        "Club night at Coppers! Refreshments provided before midnight. Pre drinks at 10pm.",
        False,
        "A10-3: 'club night' + 'pre drinks' still in nightlife filter → REJECT"
    ),

    # ── Phase A12: Religious event hard filter ───────────────────────────────
    # Ramadan post with no food keywords → reject (already rejected, now explicit)
    (
        "Ramadan Mubarak! 🌙 Wishing everyone a blessed month.",
        False,
        "A12-1: Ramadan mention, no food keywords → REJECT (religious filter)"
    ),
    # Iftar with explicit food mention → still reject (policy)
    (
        "Join us this Ramadan to spend a wonderful Iftar together. "
        "We will be breaking the fast with a scrumptious serving of food. Astra Hall 7pm.",
        False,
        "A12-2: Iftar with food mention → REJECT (religious filter, policy override)"
    ),

    # ── Phase A13a: Explicit free-event declaration ──────────────────────────
    (
        "Join us this Wednesday for some pizza, cans, and a bit of countdown. "
        "*This is a free event* Newman Building 6pm",
        True,
        "A13a: 'this is a free event' override + pizza → ACCEPT"
    ),

    # ── Phase A13b: Ticket language tightening ───────────────────────────────
    # 'ticket' in 'SciBall ticket sales' should NOT block an unrelated Coffee Morning
    (
        "After the chaos of Science Day and SciBall ticket sales, we're slowing things "
        "down this week with a Coffee Morning. Drop by for a cup of coffee!",
        True,
        "A13b: 'SciBall ticket sales' not paid ticket language; Coffee Morning → ACCEPT"
    ),

    # ── Phase A14: 'ball' standalone replaced by specific phrases ────────────
    # 'ball' in non-nightlife context should not block free biscuits
    (
        "Hey PhysSoc! Come by the Student Centre for free caffeine and biscuits "
        "at our weekly coffee hour. Also our annual Physics Ball is coming up next month.",
        True,
        "A14: 'Physics Ball' not compound nightlife phrase; biscuits → ACCEPT"
    ),
    # Real ball compound still rejects
    (
        "Annual Ball tickets now on sale! Grab yours before they sell out. "
        "Free drinks included for early birds.",
        False,
        "A14: 'annual ball' compound nightlife keyword → REJECT"
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

# ── Phase B5: TBC detection in extract_event() ─────────────────────────────
print("\n" + "="*60)
print("B5: TBC detection (extract_event returns None)")
print("="*60)

b5_tests = [
    (
        "Free pizza at our next meeting! Time TBC — we'll update you soon. Student Centre.",
        None,
        "B5-1: strong food keyword + 'Time TBC' → extract_event returns None"
    ),
    (
        "Coffee morning coming up! Date and time TBA. Location: Newman Building.",
        None,
        "B5-2: strong food keyword + 'TBA' → extract_event returns None"
    ),
    (
        "Join us for snacks and drinks — details to be confirmed, watch this space!",
        None,
        "B5-3: strong food keyword + 'to be confirmed' → extract_event returns None"
    ),
    (
        "Free lunch this Thursday at 1pm! Newman Building G15.",
        dict,  # not None — normal post should still return a dict
        "B5-4: no TBC phrase → extract_event returns event dict (not None)"
    ),
]

b5_passed = 0
b5_failed = 0
for caption, expected, description in b5_tests:
    result = extractor.extract_event(caption)
    if expected is None:
        ok = result is None
    else:
        ok = isinstance(result, dict)
    status = "PASS" if ok else "FAIL"
    if ok:
        b5_passed += 1
    else:
        b5_failed += 1
        print(f"[{status}] {description}")
        print(f"       Expected: {expected}, Got: {type(result).__name__ if result is not None else None}")
        print()

print(f"B5 Results: {b5_passed}/{len(b5_tests)} passed, {b5_failed} failed")

# ── Phase A11: segment_post_text() ─────────────────────────────────────────
print("\n" + "="*60)
print("A11: segment_post_text() segmentation")
print("="*60)

namsoc_text = (
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

german_text = (
    "KAFFEEKLATSCH\n"
    "Join us for tea, coffee and snacks in the Global Lounge! Thursday 14:00-16:00.\n\n"
    "GERMAN FOR BEGINNERS\n"
    "Come learn German with us — perfect for absolute beginners. Newman Building G15 Tuesday 6pm."
)

single_text = "Come for free pizza at Newman Building Friday 6pm! All welcome."

a11_tests = [
    (namsoc_text, 4, "A11-1: NAMSOC schedule → 4 segments (all ≥80 chars, max 6)"),
    (german_text, 2, "A11-2: German Soc → 2 segments"),
    (single_text, 1, "A11-3: Normal short caption → 1 segment (fallback)"),
]

a11_passed = 0
a11_failed = 0
for text, expected_count, description in a11_tests:
    segs = extractor.segment_post_text(text)
    ok = len(segs) == expected_count
    status = "PASS" if ok else "FAIL"
    if ok:
        a11_passed += 1
    else:
        a11_failed += 1
        print(f"[{status}] {description}")
        print(f"       Expected {expected_count} segments, got {len(segs)}")
        for i, s in enumerate(segs):
            print(f"       Seg {i}: {s[:60]!r}")
        print()

# Verify correct classify results per segment for NAMSOC
namsoc_segs = extractor.segment_post_text(namsoc_text)
expected_classify = [True, True, False, False]  # pancakes, coffee morning, debate, coppers
all_match = True
for i, (seg, exp) in enumerate(zip(namsoc_segs, expected_classify)):
    got = extractor.classify_event(seg)
    if got != exp:
        all_match = False
        print(f"[FAIL] A11 NAMSOC segment {i} classify: expected {exp}, got {got}")
        print(f"       Segment: {seg[:80]!r}")
if all_match:
    a11_passed += 1
    a11_total = len(a11_tests) + 1
else:
    a11_failed += 1
    a11_total = len(a11_tests) + 1

print(f"A11 Results: {a11_passed}/{len(a11_tests) + 1} passed, {a11_failed} failed")

# ── Screenshot-based real-world tests (Important Posts) ─────────────────────
# Text is caption + key phrases OCR would extract from the image,
# combined as the scraper does: "{caption}\n\n[Image Text]\n{ocr_text}"
print("\n" + "="*60)
print("SCREENSHOT TESTS: real posts from Important Posts folder")
print("="*60)

screenshot_tests = [
    # IMG_3965 — Arts Soc Coffee Morning
    # Image: "UCD ARTS SOC COFFEE MORNING / Free coffee / Free tea / Free snacks / NEWMAN BASEMENT 11AM-1PM"
    # Caption: "TUESDAY COFFEE MORNING! AGAIN! ... Newman Basement every Tuesday"
    (
        "TUESDAY COFFEE MORNING! AGAIN! And this time it's final; our coffee mornings for this term will be held in Newman Basement every Tuesday.\n\n[Image Text]\nUCD ARTS SOC COFFEE MORNING Free coffee Free tea Free snacks Good company! NEWMAN BASEMENT 11AM-1PM",
        True,
        "SC-IMG3965: Arts Soc Coffee Morning — 'coffee morning' strong keyword → ACCEPT"
    ),

    # IMG_3966 — Arts Soc Week 6 schedule (caption has NO food keyword; OCR is the only path)
    # Image: schedule with "COFFEE MORNING" as first event
    (
        "Week 6 is here! Another week, another lineup of good events and even better company. We've got lots in store and we're so excited to share it all with you. Make sure to stay tuned for everything coming up — you won't want to miss it!\n\n[Image Text]\nWEEK 6 24th COFFEE MORNING NEWMAN BASEMENT 11 AM-2 PM 25th MOVIE SCREENING APOCALYPSE NOW NEWMAN NT1 5 PM-7:45 PM 27th NATIONAL GALLERY OF IRELAND NATIONAL GALLERY 3 PM-6 PM",
        True,
        "SC-IMG3966: Arts Soc Week 6 schedule — 'coffee morning' only in OCR text → ACCEPT"
    ),

    # IMG_3967 — Hispanic Society Día de la Bandera
    # "tacos, nachos & guac, mex snacks" are all strong keywords
    # "WINNER GETS A VERY SPECIAL PRIZE" does NOT match any A7 giveaway pattern → should pass
    (
        "we're presenting EL DIA DE LA BANDERA. Where, alongside traditional Mexican food (tacos, nachos & guac, mex snacks...) we'll use this opportunity to learn about the country's culture and traditions. A quiz will be carried out to test your acquired knowledge, WINNER GETS A VERY SPECIAL PRIZE! Global Lounge, Wednesday 24th, 4:15pm",
        True,
        "SC-IMG3967: Hispanic Soc Dia de la Bandera — tacos/nachos/snacks strong; 'WINNER GETS A VERY SPECIAL PRIZE' not a giveaway pattern → ACCEPT"
    ),

    # IMG_3969 — Economics Refreshers Week (no food keyword at all)
    (
        "Refresher's Week is here! New semester, new events. Sign up to the UCD Economics Society at Ad Astra Hall this week to get access to all of our talks, careers events, socials and more for the semester ahead. Ad Astra Hall Tues 27th: 10am - 4pm Don't miss out — we've got a big semester planned",
        False,
        "SC-IMG3969: Econ Soc Refreshers Week — 'refreshers' is weak keyword, no context modifier → REJECT"
    ),

    # IMG_3970 — Economics Coffee Morning
    # Caption: "Coffee Morning" in body text
    (
        "Coffee, chats, and a mid-week break. We're hosting a Coffee Morning this Tuesday 10th of February, 10-11am, in the Red Room, Student Centre. Drop by for a cup of coffee, meet fellow Econ students, and take a breather between lectures!\n\n[Image Text]\nECONOMICS SOCIETY Coffee Morning Tuesday 10th February 10:00am - 11:00am Red Room Student Centre",
        True,
        "SC-IMG3970: Econ Soc Coffee Morning — 'coffee morning' strong keyword → ACCEPT"
    ),

    # IMG_3971 — MicroSoc Lunchtime Seminar Series
    # "tea, coffee and snacks will be provided" — snacks = strong, provided = context modifier
    # €2 for students (membership context), €15 for staff (membership) — no ticket language
    (
        "Come join us in the Blue Room in the Students Union Centre to hear the very interesting Padraic Heneghan discuss some of the current research happening in the Wolfe Lab! Tea, coffee and snacks will be provided! Also if you are looking to become a member of MicroSoc we will be taking on new members at this seminar series (€2 for students, €15 for staff - cash only :D) Thursday, 6th October Blue Room, UCD SU Centre 11:00-12:00",
        True,
        "SC-IMG3971: MicroSoc Seminar — 'snacks will be provided' strong+modifier; €15 is membership not ticket → ACCEPT"
    ),

    # IMG_3972 — NorthSoc Coffee Afternoon (DrawSoc + MusicSoc collab)
    # "coffee afternoon" = strong keyword; "biscuits" = strong; "free coffee" also present
    (
        "We are going to be hosting a coffee afternoon next Wednesday in collaboration with DrawSoc and MusicSoc. Destress from exams with some free coffee and biscuits! Relax with some music and drawing to take your mind off of exams! Global Lounge 13th November 2.45pm-4.45pm",
        True,
        "SC-IMG3972: NorthSoc Coffee Afternoon — 'coffee afternoon' strong + 'biscuits' strong → ACCEPT"
    ),

    # IMG_3975 — Plan'Eat "FUEL FOR THE WEEK" (caption alone has no food keyword; OCR critical)
    # Image: "FREE LUNCH INCLUDED"
    (
        "Join us for a hands-on meal prep session with Healthy UCD x UCD PLAN'EAT x UCD Nutrition Society. Crean Lounge 3rd March 1-3pm Limited spots - first come, first served Scan the QR code or use the link to sign up!\n\n[Image Text]\nFUEL FOR THE WEEK COME AND JOIN US! FREE LUNCH INCLUDED HANDS-ON MEAL PREP SESSION CREAN LOUNGE 3RD MARCH 1-3PM",
        True,
        "SC-IMG3975: Plan'Eat Free Lunch — 'free lunch' strong keyword (OCR only) → ACCEPT"
    ),

    # IMG_3976+3977 — RADSOC Run 5 Donate 5 (ticket language + €5)
    # "Tickets: €5" and "€5 ticket including post run refreshments" → hard reject
    (
        "Join us for a 5K fun run/walk starting and finishing in UCD followed by refreshments. Tickets: €5. All proceeds go to Nurture Africa. When: Tuesday 24/02 at 3pm outside Sports Centre. refreshments kindly sponsored by @avonprotein. Tickets can be purchased by donating €5.",
        False,
        "SC-IMG3976+3977: RADSOC Run 5 — 'Tickets: €5' is ticket language → REJECT despite refreshments"
    ),

    # IMG_3978 — RADSOC Free Breakfast (World Radiography Day)
    # "FREE breakfast" = strong keyword; "kindly organised" ≠ exact modifier but "free breakfast" is strong alone
    # €15 for second-hand scrubs is a separate sale, not for the food
    (
        "Join us for a FREE breakfast for all Radiography & Diagnostic Imaging staff and students, kindly organised by the Radiography Section to celebrate world Radiography day. This Thursday 6/11/25 8-11am First come, first served\n\n[Image Text]\nfree Breakfast Charles Institute 8am-11am to celebrate world radiography day",
        True,
        "SC-IMG3978: RADSOC Free Breakfast — 'free breakfast' strong keyword → ACCEPT"
    ),

    # IMG_3986 — NAMSOC Week 24 schedule (THE KEY BUG-FIX TEST)
    # Previously: "night out" in OCR text → nightlife reject → false negative
    # After A10: "night out" removed from nightlife_keywords → ACCEPT (pancakes + coffee morning = strong)
    (
        "Come along to our amazing events this week — Pancake Tuesday to celebrate one of the best days of the year. The incredible healthcare debate (this will be an interesting one), Then a coffee morning to wake you up before your lecture.\n\n[Image Text]\nWEEK 24 FEBRUARY 17/02 TUE PANCAKE TUESDAY Harmony studio 11:00-12:00 Come join us for some pancakes and fun on Tuesday morning! 17/02 TUE HEALTHCARE DEBATE Fitzgerald chamber 18:00 18/02 WED COFFEE MORNING Meeting rooms 08:30-09:30 Pop in for a coffee and chat to catch up and chill 19/02 THU COPPERS NIGHT OUT Free entry every Thursday before 23:30",
        True,
        "SC-IMG3986: NAMSOC Week 24 — 'pancakes'+'coffee morning' strong; 'night out' no longer blocks after A10 → ACCEPT"
    ),

    # IMG_3987 — NAMSOC Free Cookies ("Would You Rather")
    (
        "COME JOIN US FOR FREE COOKIES ON THE 4TH OF FEBUARY IN HARMONY\n\n[Image Text]\nWould You Rather Nothing sounds better than free cookies to kick start your day right? Join us in the Harmony Lounge 4th February from 11-11:30am Cookies mandatory questions optional",
        True,
        "SC-IMG3987: NAMSOC Free Cookies — 'cookies' strong keyword → ACCEPT"
    ),

    # IMG_3988 — UCDLNH Finlay Week (Açaí Breakfast TBC)
    # "breakfast" = weak keyword, no context modifier in text → classify REJECT
    # Even if LLM approved, B5 would block extract_event due to TBC
    (
        "We are so excited to announce our events for Finlay Week this year! From a Journalling Workshop to Acai Breakfast, we are gearing up to have a fantastic week in the lead up to International Women's Day. Please do join us at any of our events this coming week!\n\n[Image Text]\nFinlay Week Build up to International Women's Day 2nd-6th March 2026 4 March Acai Breakfast TBC all proceeds to Womens Aid",
        False,
        "SC-IMG3988: Finlay Week Acai Breakfast TBC — 'breakfast' weak, no modifier → classify REJECT (B5 would block extract_event too)"
    ),

    # IMG_3989+3990 — UCD German Society Kaffeeklatsch (A8 fix)
    # Full caption has "kaffeeklatsch" (strong, A8), "coffee afternoon" (strong), "snacks" (strong)
    (
        "KAFFEEKLATSCH Monday, March 3rd 14:00-16:00 in the Global Lounge Join us for a relaxed coffee afternoon filled with conversation, games, tea, coffee, snacks and a chance to practice your German (all levels welcome!) GERMAN FOR BEGINNERS Thursday, March 5th 13:00-14:00 in the O'Connor Centre for Learning Room L1.05 Always wanted to learn German but didn't know where to start? This session is perfect for complete beginners.\n\n[Image Text]\nEVENTS WEEK 7 MAR 2 KAFFEEKLATSCH 2:00-4:00 PM GLOBAL LOUNGE MAR 5 GERMAN FOR BEGINNERS 1:00-2:00 PM LLO5 O'CONNOR",
        True,
        "SC-IMG3989+3990: German Soc Kaffeeklatsch — 'kaffeeklatsch' strong (A8) + 'coffee afternoon' + 'snacks' → ACCEPT"
    ),

    # IMG_3991 — The Food Hall UCD "BLASTA" (A9 fix)
    # "handing out samples" = strong keyword after A9
    (
        "Not had a chance to try out new menu yet? We'll be handing out samples of our new Indian and Thai dishes for you to try! Just come to the Foodhall 12:30pm - 13:30pm to grab one!\n\n[Image Text]\nBLASTA Want to try some of our dishes? We'll be handing out samples of our new Indian and Thai dishes in the Foodhall! Thursday 5th February 12:30pm - 13:30pm",
        True,
        "SC-IMG3991: Food Hall BLASTA — 'handing out samples' strong keyword (A9) → ACCEPT"
    ),
]

sc_passed = 0
sc_failed = 0
for caption, expected, description in screenshot_tests:
    result = extractor.classify_event(caption)
    status = "PASS" if result == expected else "FAIL"
    if result == expected:
        sc_passed += 1
    else:
        sc_failed += 1
        reason = extractor.get_rejection_reason(caption)
        print(f"[{status}] {description}")
        print(f"       Expected: {expected}, Got: {result}, Reason: {reason}")
        print()

total_sc = len(screenshot_tests)
print(f"\nScreenshot test results: {sc_passed}/{total_sc} passed, {sc_failed} failed")

# ── B6 Vision LLM fallback tests ─────────────────────────────────────────────
# These mock the vision LLM call so no OpenAI key is required.
# They verify the routing logic: OCR low-yield + image_urls → vision path accepted.
print("\n" + "="*60)
print("B6 VISION LLM FALLBACK TESTS (mocked)")
print("="*60)

from unittest.mock import patch, MagicMock

b6_passed = 0
b6_failed = 0

def _run_b6(description: str, caption: str, vision_response: dict,
            image_urls: list, expected_not_none: bool, ocr_low_yield: bool = True):
    """
    Simulate a post where Tesseract returned <20 chars (ocr_low_yield=True).
    Patches settings and the LLM singleton so no real API key is needed.
    """
    global b6_passed, b6_failed

    mock_llm = MagicMock()
    mock_llm.classify_with_vision.return_value = vision_response

    with patch('app.services.nlp.extractor.settings') as mock_settings, \
         patch('app.services.nlp.llm_classifier.get_llm_classifier', return_value=mock_llm), \
         patch('app.services.nlp.llm_classifier.LLMClassifier.classify_with_vision',
               return_value=vision_response):
        mock_settings.USE_SCORING_PIPELINE = True
        mock_settings.OPENAI_API_KEY = "sk-fake"
        mock_settings.USE_VISION_FALLBACK = True

        # The local import inside _try_llm_fallback resolves to llm_classifier module;
        # patch its get_llm_classifier function directly.
        import app.services.nlp.llm_classifier as _llm_mod
        original_getter = _llm_mod.get_llm_classifier
        _llm_mod.get_llm_classifier = lambda: mock_llm
        try:
            result = extractor.extract_event(
                caption,
                source_type='post',
                image_urls=image_urls,
                ocr_low_yield=ocr_low_yield,
            )
        finally:
            _llm_mod.get_llm_classifier = original_getter

    ok = (result is not None) == expected_not_none
    status = "PASS" if ok else "FAIL"
    if ok:
        b6_passed += 1
    else:
        b6_failed += 1
        print(f"[{status}] {description}")
        print(f"       Expected not-None={expected_not_none}, Got result={result}")
        print()
    if ok:
        print(f"[{status}] {description}")


# B6-1: OCR low-yield + vision says food=True → extract_event should return a dict
_run_b6(
    "B6-1: OCR failed, vision sees 'FREE PIZZA Student Centre 1pm' → ACCEPT",
    caption="Join us for our weekly meeting this Tuesday.",  # no food keyword → rule-based rejects
    vision_response={
        "food": True,
        "text": "FREE PIZZA Student Centre 1pm Tuesday",
        "location": "Student Centre",
        "time": "13:00",
    },
    image_urls=["https://example.com/fake-image.jpg"],
    expected_not_none=True,
)

# B6-2: OCR low-yield + vision says food=False → should return None
_run_b6(
    "B6-2: OCR failed, vision sees no food → REJECT",
    caption="Exciting announcement coming soon! Stay tuned.",
    vision_response={"food": False, "text": ""},
    image_urls=["https://example.com/fake-image.jpg"],
    expected_not_none=False,
)

# B6-3: OCR low-yield + vision says food=True but hard filter fires (paid event)
# Caption already has ticket language — hard filter should block before vision call
_run_b6(
    "B6-3: OCR failed, vision food=True but caption has 'Tickets: €20' → hard-filter REJECT",
    caption="Tickets: €20 per person. Get yours now before they sell out!",
    vision_response={
        "food": True,
        "text": "FREE CANAPES with every ticket",
        "location": "Newman Building",
        "time": "19:00",
    },
    image_urls=["https://example.com/fake-image.jpg"],
    expected_not_none=False,
)


_run_b6(
    "B6-4b: ocr_low_yield=False → vision LLM never called even with food vision response",
    caption="Don't miss our general meeting this week.",
    vision_response={"food": True, "text": "FREE PIZZA", "location": None, "time": None},
    image_urls=["https://example.com/fake-image.jpg"],
    expected_not_none=False,  # text path: no food keyword → reject
    ocr_low_yield=False,
)

print(f"\nB6 vision fallback results: {b6_passed}/{b6_passed + b6_failed} passed, {b6_failed} failed")

# ── Grand total ───────────────────────────────────────────────────────────────
print("\n" + "="*60)
total_all = len(test_cases) + len(b5_tests) + len(a11_tests) + 1 + total_sc + b6_passed + b6_failed
passed_all = sum(1 for _, exp, _ in test_cases if extractor.classify_event(_) == exp)  # recount inline
# Use the already-accumulated counters
print(f"GRAND TOTAL: classify={passed}/{len(test_cases)}, B5={b5_passed}/{len(b5_tests)+1}, "
      f"A11={a11_passed}/{len(a11_tests)+1}, SC={sc_passed}/{total_sc}, B6={b6_passed}/{b6_passed+b6_failed}")
