# Date Extraction Specification

## Date Format Patterns Found in Instagram Posts

### 1. **Day + Month Name + Weekday**
- `23 February, Monday` → 23/02/2026
- `23rd February, Monday` → 23/02/2026
- `23 February Monday` (no comma) → 23/02/2026
- `23rd of February, Monday` → 23/02/2026

### 2. **Weekday + Day + Month Name**
- `Monday, 23 February` → 23/02/2026
- `Monday 23rd February` → 23/02/2026
- `Monday the 23rd of February` → 23/02/2026

### 3. **Month Name + Day + Weekday**
- `February 23, Monday` → 23/02/2026
- `February 23rd, Monday` → 23/02/2026

### 4. **Numeric Dates (DD/MM or DD/MM/YY)**
- `23/02` → 23/02/2026 (current year)
- `23/02/26` → 23/02/2026
- `23/2` → 23/02/2026 (single digit month)
- `23-02` → 23/02/2026 (dash separator)
- `23.02` → 23/02/2026 (dot separator)

### 5. **Weekday + Numeric Date**
- `Monday 23/02` → 23/02/2026
- `Monday, 23/02` → 23/02/2026

### 6. **Day Only (with ordinal)**
- `23rd` → 23rd of current month (or next month if past)
- `the 23rd` → 23rd of current month

### 7. **Relative Dates**
- `today` → today's date
- `tonight` → today's date
- `tomorrow` → tomorrow's date
- `this Monday` → next Monday
- `next Monday` → Monday of next week
- `this week` → within 7 days
- `next week` → 7-14 days from now

### 8. **Month Name + Day (no weekday)**
- `February 23` → 23/02/2026
- `23 February` → 23/02/2026
- `23rd February` → 23/02/2026

## Edge Cases & Ambiguities

### 1. **Past vs Future Dates**
- If extracted date is in the past, assume next occurrence
- Example: On Feb 25, "Monday 23rd" → March 23 (next Monday 23rd)

### 2. **Year Ambiguity**
- Default to current year
- If date is >1 day in past, try next year
- Don't accept dates >90 days in future (likely errors)

### 3. **Month Ambiguity in Numeric Dates**
- **ALWAYS use DD/MM format** (European/Irish standard)
- `23/02` = 23rd February, NOT February 23rd
- `02/03` = 2nd March, NOT March 2nd

### 4. **Weekday Validation**
- If weekday is mentioned, VALIDATE it matches the date
- `Monday 23 February` where Feb 23 is Tuesday → REJECT or find correct date
- Priority: Trust the explicit date over weekday

### 5. **Multiple Dates in Text**
- "Event on Monday 23rd, registration by Friday 20th"
- Extract the MAIN event date (usually first, or after "event on")
- Ignore registration/deadline dates

### 6. **Time Ranges Affecting Date**
- "Monday 11pm - Tuesday 2am" → Event is on Monday
- Extract start date, not end date

### 7. **Recurring Events**
- "Every Monday" → Next Monday
- "Weekly on Tuesdays" → Next Tuesday
- Don't create multiple events, just next occurrence

### 8. **Ambiguous Day Numbers**
- `23` alone could be day or time (23:00)
- Need context: "on the 23rd" vs "at 23:00"

### 9. **Month Name Abbreviations**
- `Feb`, `Sept`, `Dec` → Full month names
- Handle both abbreviated and full names

### 10. **Different Date Separators**
- `/` → 23/02
- `-` → 23-02
- `.` → 23.02
- ` ` → 23 02 (space)

## Priority Order for Date Extraction

1. **Explicit Date + Validated Weekday** (Highest confidence)
   - "Monday 23 February" where Feb 23 IS Monday
   - Confidence: 1.0

2. **Explicit Date + Weekday (Mismatch)**
   - "Monday 23 February" where Feb 23 is NOT Monday
   - Trust the date, ignore weekday
   - Confidence: 0.9

3. **Explicit Date (No Weekday)**
   - "23 February" or "23/02"
   - Confidence: 0.85

4. **Weekday + Day Number**
   - "Monday 23rd" (no month)
   - Infer month from context
   - Confidence: 0.7

5. **Relative Keywords**
   - "tomorrow", "next Monday"
   - Confidence: 0.6

6. **Day Only**
   - "23rd" (no month or weekday)
   - Confidence: 0.5

7. **No Date Found**
   - Default to post timestamp or today
   - Confidence: 0.3

## Validation Rules

1. **Date must be in future** (or today)
   - Allow up to 1 day in past (for late posts)
   - If >1 day past, try next year

2. **Date must be within 90 days**
   - Events >90 days away are likely errors
   - Reject or flag for manual review

3. **Weekday validation**
   - If weekday mentioned, verify it matches
   - If mismatch, trust explicit date over weekday

4. **Month validation**
   - Month must be 1-12
   - Day must be valid for that month (handle leap years)

5. **Year validation**
   - Current year or next year only
   - Don't accept dates in past years

## Implementation Strategy

### Phase 1: Pattern Matching
1. Try all patterns in priority order
2. Collect all candidate dates with confidence scores
3. Store pattern type for debugging

### Phase 2: Validation
1. Validate each candidate (future, range, weekday)
2. Adjust dates if needed (next year, next occurrence)
3. Filter out invalid candidates

### Phase 3: Selection
1. Sort by confidence score (highest first)
2. If multiple high-confidence candidates, choose earliest
3. Return best candidate with metadata

### Phase 4: Fallback
1. If no valid date found, use post timestamp
2. If post timestamp unavailable, use current time
3. Always return a date (never None for valid events)

## Test Cases

```python
# Test cases to validate
test_cases = [
    ("23 February, Monday", "2026-02-23"),  # DD Month, Weekday
    ("Monday 23 February", "2026-02-23"),   # Weekday DD Month
    ("February 23, Monday", "2026-02-23"),  # Month DD, Weekday
    ("23/02", "2026-02-23"),                # DD/MM
    ("23/02/26", "2026-02-23"),             # DD/MM/YY
    ("Monday 23/02", "2026-02-23"),         # Weekday DD/MM
    ("tomorrow", "2026-02-24"),             # Relative (if today is 23rd)
    ("next Monday", "2026-03-02"),          # Relative weekday
    ("23rd", "2026-02-23"),                 # Day only (current month)
    ("the 23rd", "2026-02-23"),             # Day only with article
]
```

## Error Handling

1. **Invalid date components** → Skip pattern, try next
2. **Weekday mismatch** → Log warning, use date
3. **Past date** → Try next year
4. **No date found** → Use fallback (post timestamp)
5. **Multiple dates** → Choose first/earliest

## Logging Strategy

- DEBUG: All pattern matches and candidates
- INFO: Selected date with confidence and pattern type
- WARNING: Weekday mismatches, past dates adjusted
- ERROR: Invalid dates that couldn't be parsed