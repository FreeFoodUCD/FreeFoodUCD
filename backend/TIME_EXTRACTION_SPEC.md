# Time Extraction Specification

## Time Format Patterns Found in Instagram Posts

### 1. **Time Ranges (Extract Start Time)**

#### With Minutes
- `6:30pm to 7pm` → 18:30
- `6:30pm - 7pm` → 18:30
- `6:30 PM to 7:30 PM` → 18:30
- `at 6:30pm to 7pm` → 18:30
- `from 6:30pm to 7pm` → 18:30
- `6:30-7:00 PM` → 18:30
- `from 6:30-7:30 PM` → 18:30

#### Without Minutes
- `6pm to 7pm` → 18:00
- `6pm - 7pm` → 18:00
- `6 PM to 7 PM` → 18:00
- `at 6pm to 7pm` → 18:00
- `from 6pm to 7pm` → 18:00

#### Mixed Formats
- `6:30pm-7pm` (no space before dash) → 18:30
- `6.30pm to 7pm` (dot separator) → 18:30
- `18:30 to 19:00` (24-hour) → 18:30

### 2. **Single Times**

#### With Minutes
- `6:30 PM` → 18:30
- `6:30pm` → 18:30
- `6.30 PM` → 18:30
- `at 6:30 PM` → 18:30
- `at 6:30pm` → 18:30

#### Without Minutes
- `6 PM` → 18:00
- `6pm` → 18:00
- `at 6 PM` → 18:00
- `at 6pm` → 18:00

#### 24-Hour Format
- `18:30` → 18:30
- `18.30` → 18:30
- `1830` → 18:30 (no separator)

### 3. **Special Cases**

#### Noon/Midnight
- `12 PM` → 12:00 (noon)
- `12:00 PM` → 12:00 (noon)
- `12 AM` → 00:00 (midnight)
- `12:00 AM` → 00:00 (midnight)
- `noon` → 12:00
- `midnight` → 00:00

#### Prepositions
- `at 6pm` → 18:00
- `by 6pm` → 18:00 (deadline, but still extract)
- `until 6pm` → 18:00 (end time, but extract)
- `around 6pm` → 18:00 (approximate)

## Edge Cases & Ambiguities

### 1. **Separator Variations**
- Colon: `6:30 PM`
- Dot: `6.30 PM`
- No separator: `630 PM` (rare)
- Space: `6 30 PM` (very rare)

### 2. **AM/PM Variations**
- Uppercase: `PM`, `AM`
- Lowercase: `pm`, `am`
- With dots: `p.m.`, `a.m.`
- No space: `6pm`, `6:30pm`
- With space: `6 pm`, `6:30 PM`

### 3. **Range Separators**
- Dash: `6-7pm`, `6:30-7pm`
- En dash: `6–7pm`
- Em dash: `6—7pm`
- To: `6 to 7pm`, `6pm to 7pm`
- Hyphen with spaces: `6 - 7pm`

### 4. **Ambiguous Numbers**
- `23` could be:
  - Day of month: "23rd February"
  - Hour in 24-hour format: "23:00"
  - Part of date: "23/02"
- **Solution**: Context matters - check for AM/PM or colon

### 5. **Multiple Times in Text**
- "Registration at 5pm, event at 6pm"
  - Extract: 6pm (main event time)
  - Ignore: 5pm (registration)
- "Event from 6-7pm, afterparty at 8pm"
  - Extract: 6pm (main event start)
  - Ignore: 7pm (end), 8pm (afterparty)

### 6. **Time Without AM/PM**
- `6:30` - Is it 6:30 AM or PM?
  - **Solution**: If no AM/PM, assume PM for events (18:30)
  - Most UCD events are in the evening

### 7. **24-Hour Format Ambiguity**
- `6:30` vs `18:30`
  - If hour > 12, it's 24-hour format
  - If hour ≤ 12 and no AM/PM, assume PM

### 8. **Overlapping Patterns**
- "at 6:30pm to 7pm" matches multiple patterns
  - Range pattern should take priority
  - Extract start time (6:30pm)

### 9. **Invalid Times**
- `25:00` → Invalid hour
- `6:75 PM` → Invalid minute
- `13 PM` → Invalid (13 doesn't exist in 12-hour)
- **Solution**: Validate and default to 18:00

### 10. **Time Zones**
- "6pm GMT", "6pm IST"
  - **Solution**: Ignore timezone, assume Dublin time
  - UCD events are local

## Priority Order for Time Extraction

1. **Time Ranges with Minutes** (Highest confidence)
   - "6:30pm to 7pm"
   - Confidence: 1.0

2. **Time Ranges without Minutes**
   - "6pm to 7pm"
   - Confidence: 0.95

3. **Single Time with Minutes**
   - "6:30 PM"
   - Confidence: 0.9

4. **Single Time without Minutes**
   - "6 PM"
   - Confidence: 0.85

5. **24-Hour Format**
   - "18:30"
   - Confidence: 0.8

6. **Special Keywords**
   - "noon", "midnight"
   - Confidence: 0.7

7. **No Time Found**
   - Default to 18:00 (6 PM)
   - Confidence: 0.3

## Validation Rules

1. **Hour must be 0-23** (24-hour format)
2. **Minute must be 0-59**
3. **12-hour to 24-hour conversion**:
   - 1-11 AM → 1-11
   - 12 AM → 0 (midnight)
   - 1-11 PM → 13-23
   - 12 PM → 12 (noon)
4. **If no AM/PM and hour ≤ 12**: Assume PM
5. **If hour > 12**: It's 24-hour format

## Implementation Strategy

### Phase 1: Pattern Matching (Priority Order)
1. Try time range patterns first (highest priority)
2. Try single time patterns
3. Try special keywords (noon, midnight)
4. Default to 18:00 if nothing found

### Phase 2: Parsing
1. Extract hour, minute, period (AM/PM)
2. Handle different separators (`:`, `.`, none)
3. Handle spacing variations

### Phase 3: Conversion
1. Convert 12-hour to 24-hour if AM/PM present
2. If no AM/PM and hour ≤ 12, assume PM
3. Validate hour (0-23) and minute (0-59)

### Phase 4: Validation
1. Check hour and minute ranges
2. If invalid, log warning and return None
3. Fallback to 18:00 in calling code

## Test Cases

```python
test_cases = [
    # Time ranges with minutes
    ("6:30pm to 7pm", "18:30"),
    ("at 6:30pm to 7pm", "18:30"),
    ("from 6:30-7:30 PM", "18:30"),
    ("6:30-7:00 PM", "18:30"),
    
    # Time ranges without minutes
    ("6pm to 7pm", "18:00"),
    ("at 6pm to 7pm", "18:00"),
    ("from 6-7 PM", "18:00"),
    
    # Single times with minutes
    ("6:30 PM", "18:30"),
    ("at 6:30pm", "18:30"),
    ("6.30 PM", "18:30"),
    
    # Single times without minutes
    ("6 PM", "18:00"),
    ("at 6pm", "18:00"),
    
    # 24-hour format
    ("18:30", "18:30"),
    ("18.30", "18:30"),
    
    # Special cases
    ("12 PM", "12:00"),  # noon
    ("12 AM", "00:00"),  # midnight
    ("noon", "12:00"),
    ("midnight", "00:00"),
    
    # Edge cases
    ("6:30pm-7pm", "18:30"),  # no space before dash
    ("6.30pm to 7pm", "18:30"),  # dot separator
    ("at 6:30 PM to 7:30 PM", "18:30"),  # full format
    
    # Ambiguous (no AM/PM, assume PM)
    ("6:30", "18:30"),
    ("6", "18:00"),
    
    # Invalid (should return None or default)
    ("25:00", None),
    ("6:75 PM", None),
    ("13 PM", None),
]
```

## Regex Patterns (Comprehensive)

### Time Range Patterns
```python
# Pattern 1: H:MM AM/PM to H:MM AM/PM
r'(?:at|from)?\s*(\d{1,2})\s*[:.]?\s*(\d{2})?\s*(am|pm|AM|PM)\s*(?:to|-|–)\s*\d{1,2}\s*[:.]?\s*\d{2}?\s*(?:am|pm|AM|PM)'

# Pattern 2: H AM/PM to H AM/PM (no minutes)
r'(?:at|from)?\s*(\d{1,2})\s*(am|pm|AM|PM)\s*(?:to|-|–)\s*\d{1,2}\s*(?:am|pm|AM|PM)'

# Pattern 3: H:MM-H:MM AM/PM (single AM/PM at end)
r'(\d{1,2})\s*[:.]?\s*(\d{2})?\s*(?:-|–)\s*\d{1,2}\s*[:.]?\s*\d{2}?\s*(am|pm|AM|PM)'
```

### Single Time Patterns
```python
# Pattern 1: H:MM AM/PM
r'(?:at|by|around)?\s*(\d{1,2})\s*[:.](\d{2})\s*(am|pm|AM|PM)'

# Pattern 2: H AM/PM
r'(?:at|by|around)?\s*(\d{1,2})\s*(am|pm|AM|PM)'

# Pattern 3: H:MM (24-hour or ambiguous)
r'(?:at|by|around)?\s*(\d{1,2})\s*[:.](\d{2})(?!\s*(?:am|pm|AM|PM))'

# Pattern 4: HH:MM (24-hour, hour must be 2 digits)
r'(?:at|by|around)?\s*(\d{2}):(\d{2})'
```

### Special Keywords
```python
r'\b(noon|midnight)\b'
```

## Error Handling

1. **No match found** → Default to 18:00
2. **Invalid hour** → Log warning, return None
3. **Invalid minute** → Log warning, return None
4. **Multiple matches** → Use first match (highest priority pattern)
5. **Ambiguous time** → Assume PM if hour ≤ 12

## Logging Strategy

- **DEBUG**: All pattern matches and candidates
- **INFO**: Selected time with confidence
- **WARNING**: Invalid times, ambiguous cases
- **ERROR**: Parsing failures

---

This specification provides a comprehensive approach to time extraction with proper handling of all edge cases and ambiguities.