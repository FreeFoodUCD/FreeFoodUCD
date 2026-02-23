"""
Test script for the comprehensive date parser.
Run this to validate date extraction with various formats.
"""

from datetime import datetime
import pytz
from app.services.nlp.date_parser import DateParser

def test_date_parser():
    """Test the date parser with various formats."""
    
    timezone = pytz.timezone('Europe/Dublin')
    parser = DateParser(timezone)
    
    # Reference date: February 23, 2026 (Monday)
    ref_date = datetime(2026, 2, 23, 12, 0, 0, tzinfo=timezone)
    
    test_cases = [
        # Format: (input_text, expected_date_str, description)
        ("23 February, Monday", "2026-02-23", "DD Month, Weekday"),
        ("23rd February, Monday", "2026-02-23", "DD Month with ordinal, Weekday"),
        ("23 February Monday", "2026-02-23", "DD Month Weekday (no comma)"),
        ("Monday, 23 February", "2026-02-23", "Weekday, DD Month"),
        ("Monday 23rd February", "2026-02-23", "Weekday DD Month"),
        ("February 23, Monday", "2026-02-23", "Month DD, Weekday"),
        ("23 February", "2026-02-23", "DD Month (no weekday)"),
        ("February 23", "2026-02-23", "Month DD (no weekday)"),
        ("23/02", "2026-02-23", "DD/MM"),
        ("23/02/26", "2026-02-23", "DD/MM/YY"),
        ("23-02", "2026-02-23", "DD-MM (dash)"),
        ("23.02", "2026-02-23", "DD.MM (dot)"),
        ("Monday 23/02", "2026-02-23", "Weekday DD/MM"),
        ("tomorrow", "2026-02-24", "Relative: tomorrow"),
        ("today", "2026-02-23", "Relative: today"),
        ("next Monday", "2026-03-02", "Relative: next Monday"),
        ("this Friday", "2026-02-27", "Relative: this Friday"),
        ("23rd", "2026-02-23", "Day only (current month)"),
        ("the 23rd", "2026-02-23", "Day only with article"),
        
        # Edge cases
        ("Monday 24 February", "2026-02-24", "Weekday mismatch (24th is Tuesday)"),
        ("25/02", "2026-02-25", "Future date in same month"),
        ("1 March", "2026-03-01", "Next month"),
        ("20/02", "2026-02-20", "Past date (should use next year or reject)"),
        
        # Multiple date mentions (should pick first/main one)
        ("Event on Monday 23 February, registration by Friday 20th", "2026-02-23", "Multiple dates"),
    ]
    
    print("=" * 80)
    print("DATE PARSER TEST RESULTS")
    print("=" * 80)
    print(f"Reference Date: {ref_date.strftime('%A, %B %d, %Y')}")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for text, expected, description in test_cases:
        result = parser.parse_date(text.lower(), ref_date)
        
        if result:
            result_str = result.strftime("%Y-%m-%d")
            status = "✅ PASS" if result_str == expected else "❌ FAIL"
            
            if result_str == expected:
                passed += 1
            else:
                failed += 1
            
            print(f"\n{status}")
            print(f"  Test: {description}")
            print(f"  Input: '{text}'")
            print(f"  Expected: {expected}")
            print(f"  Got: {result_str} ({result.strftime('%A')})")
        else:
            failed += 1
            print(f"\n❌ FAIL")
            print(f"  Test: {description}")
            print(f"  Input: '{text}'")
            print(f"  Expected: {expected}")
            print(f"  Got: None")
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = test_date_parser()
    exit(0 if failed == 0 else 1)

# Made with Bob