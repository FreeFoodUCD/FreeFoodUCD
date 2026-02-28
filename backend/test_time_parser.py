"""
Test script for the comprehensive time parser.
Run this to validate time extraction with various formats.
"""

from datetime import datetime
import pytz
from app.services.nlp.time_parser import TimeParser

def test_time_parser():
    """Test the time parser with various formats."""
    
    parser = TimeParser()
    
    test_cases = [
        # Format: (input_text, expected_hour, expected_minute, description)
        
        # Time ranges with minutes
        ("6:30pm to 7pm", 18, 30, "Range: 6:30pm to 7pm"),
        ("at 6:30pm to 7pm", 18, 30, "Range: at 6:30pm to 7pm"),
        ("from 6:30-7:30 PM", 18, 30, "Range: from 6:30-7:30 PM"),
        ("6:30-7:00 PM", 18, 30, "Range: 6:30-7:00 PM"),
        ("6.30pm to 7pm", 18, 30, "Range: 6.30pm to 7pm (dot separator)"),
        
        # Time ranges without minutes
        ("6pm to 7pm", 18, 0, "Range: 6pm to 7pm"),
        ("at 6pm to 7pm", 18, 0, "Range: at 6pm to 7pm"),
        ("from 6-7 PM", 18, 0, "Range: from 6-7 PM"),
        ("6-7 PM", 18, 0, "Range: 6-7 PM"),
        
        # Single times with minutes
        ("6:30 PM", 18, 30, "Single: 6:30 PM"),
        ("at 6:30pm", 18, 30, "Single: at 6:30pm"),
        ("6.30 PM", 18, 30, "Single: 6.30 PM (dot separator)"),
        ("11:45 PM", 23, 45, "Single: 11:45 PM"),
        
        # Single times without minutes
        ("6 PM", 18, 0, "Single: 6 PM"),
        ("at 6pm", 18, 0, "Single: at 6pm"),
        ("11 PM", 23, 0, "Single: 11 PM"),
        
        # 24-hour format
        ("18:30", 18, 30, "24-hour: 18:30"),
        ("09:00", 9, 0, "24-hour: 09:00"),
        ("23:45", 23, 45, "24-hour: 23:45"),
        
        # Special cases
        ("12 PM", 12, 0, "Noon: 12 PM"),
        ("12:00 PM", 12, 0, "Noon: 12:00 PM"),
        ("12 AM", 0, 0, "Midnight: 12 AM"),
        ("12:00 AM", 0, 0, "Midnight: 12:00 AM"),
        ("noon", 12, 0, "Special: noon"),
        ("midnight", 0, 0, "Special: midnight"),
        
        # Edge cases
        ("6:30pm-7pm", 18, 30, "Edge: 6:30pm-7pm (no space before dash)"),
        ("at 6:30 PM to 7:30 PM", 18, 30, "Edge: at 6:30 PM to 7:30 PM"),
        ("from 2-3:30 PM", 14, 0, "Edge: from 2-3:30 PM"),
        
        # Ambiguous (no AM/PM, should assume PM for events)
        ("6:30", 18, 30, "Ambiguous: 6:30 (assume PM)"),
        ("11:45", 11, 45, "Ambiguous: 11:45 (24h, no AM/PM → 11:45 AM)"),

        # T2: European hNN format
        ("Event at 13h30 Newman", 13, 30, "T2: European 13h30"),
        ("13h00-14h00 UCD Village", 13, 0, "T2: European range 13h00-14h00 (start)"),

        # T3: 4-digit compact military time
        ("Event at 1830", 18, 30, "T3: compact military 1830"),
        ("Doors at 0900", 9, 0, "T3: compact military 0900"),

        # T1: quarter to 1 (normalised in _normalize)
        ("Quarter to 1pm", 12, 45, "T1: quarter to 1pm → 12:45"),
        ("Quarter to 1am", 0, 45, "T1: quarter to 1am → 00:45"),
    ]
    
    print("=" * 80)
    print("TIME PARSER TEST RESULTS")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for text, expected_hour, expected_minute, description in test_cases:
        result = parser.parse_time(text.lower())
        
        if result:
            result_hour = result['hour']
            result_minute = result['minute']
            
            if result_hour == expected_hour and result_minute == expected_minute:
                status = "✅ PASS"
                passed += 1
            else:
                status = "❌ FAIL"
                failed += 1
            
            print(f"\n{status}")
            print(f"  Test: {description}")
            print(f"  Input: '{text}'")
            print(f"  Expected: {expected_hour}:{expected_minute:02d}")
            print(f"  Got: {result_hour}:{result_minute:02d}")
        else:
            failed += 1
            print(f"\n❌ FAIL")
            print(f"  Test: {description}")
            print(f"  Input: '{text}'")
            print(f"  Expected: {expected_hour}:{expected_minute:02d}")
            print(f"  Got: None")
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return passed, failed


def test_post_timestamp_disambiguation():
    """Test AM/PM disambiguation using post_timestamp (Fix 3)."""
    parser = TimeParser()
    tz = pytz.timezone('Europe/Dublin')

    # (input_text, post_hour, expected_hour, expected_minute, description)
    ts_cases = [
        ("join us at 9:30", 8,  9, 30, "Fix3: both future (08:00 post) → AM 09:30"),
        ("event at 1:30",  11, 13, 30, "Fix3: only PM future (11:00 post) → PM 13:30"),
        ("snacks at 9:30", 20, 21, 30, "Fix3: only PM future (20:00 post) → PM 21:30"),
    ]

    print("\n" + "=" * 80)
    print("POST-TIMESTAMP DISAMBIGUATION TESTS")
    print("=" * 80)

    passed = 0
    failed = 0

    for text, post_hour, exp_h, exp_m, desc in ts_cases:
        post_ts = tz.localize(datetime(2026, 2, 28, post_hour, 0))
        result = parser.parse_time(text.lower(), post_timestamp=post_ts)

        if result and result['hour'] == exp_h and result['minute'] == exp_m:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
        got = f"{result['hour']}:{result['minute']:02d}" if result else "None"
        print(f"\n{status}")
        print(f"  Test: {desc}")
        print(f"  Input: '{text}' (post @ {post_hour:02d}:00)")
        print(f"  Expected: {exp_h}:{exp_m:02d}")
        print(f"  Got: {got}")

    print("\n" + "=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(ts_cases)} tests")
    print("=" * 80)
    return passed, failed


if __name__ == "__main__":
    passed, failed = test_time_parser()
    p2, f2 = test_post_timestamp_disambiguation()
    exit(0 if (failed + f2) == 0 else 1)

# Made with Bob