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
