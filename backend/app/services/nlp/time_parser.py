"""
Comprehensive time parser for Instagram event posts.
Handles all common time formats with proper validation and edge case handling.
"""

import re
from typing import Optional, List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


class TimeParser:
    """Robust time parser with comprehensive pattern matching and validation."""
    
    def __init__(self):
        # Special time keywords
        self.special_times = {
            'noon': {'hour': 12, 'minute': 0},
            'midnight': {'hour': 0, 'minute': 0},
        }

    @staticmethod
    def _normalize(text: str) -> str:
        """
        Normalise common OCR artefacts and informal time spellings before parsing.

        - "6 : 30 pm"  → "6:30pm"   (OCR spaces around colon/digits)
        - "6 pm"       → "6pm"       (space before am/pm)
        - "half five"  → "5:30"      (Irish English)
        - "half past 5" → "5:30"
        - "quarter past 5" → "5:15"
        - "quarter to 6"   → "5:45"
        - "5 o'clock" / "5 oclock" → "5:00"
        - "till" / "until" already handled in patterns but normalise anyway
        """
        t = text

        # OCR: collapse spaces around colons between digits  "6 : 30" → "6:30"
        t = re.sub(r'(\d)\s*:\s*(\d)', r'\1:\2', t)

        # OCR: collapse space between digit and am/pm  "6 pm" → "6pm"
        t = re.sub(r'(\d)\s+(am|pm)\b', r'\1\2', t, flags=re.IGNORECASE)

        # "o'clock" / "oclock" → ":00"
        t = re.sub(r"(\d{1,2})\s+o'?clock\b", r'\1:00', t, flags=re.IGNORECASE)

        # "half past N [am/pm]" → "N:30[am/pm]"
        def _half_past(m):
            h = int(m.group(1))
            period = m.group(2) or ''
            return f'{h}:30{period}'
        t = re.sub(r'half\s+past\s+(\d{1,2})\s*(am|pm)?', _half_past, t, flags=re.IGNORECASE)

        # "half N [am/pm]" (Irish English: "half five" = 5:30)
        def _half_n(m):
            h = int(m.group(1))
            period = m.group(2) or ''
            return f'{h}:30{period}'
        t = re.sub(r'\bhalf\s+(\d{1,2})\s*(am|pm)?\b', _half_n, t, flags=re.IGNORECASE)

        # "quarter past N [am/pm]" → "N:15[am/pm]"
        def _quarter_past(m):
            h = int(m.group(1))
            period = m.group(2) or ''
            return f'{h}:15{period}'
        t = re.sub(r'quarter\s+past\s+(\d{1,2})\s*(am|pm)?', _quarter_past, t, flags=re.IGNORECASE)

        # "quarter to N [am/pm]" → "(N-1):45[am/pm]"
        def _quarter_to(m):
            h = int(m.group(1))
            period = m.group(2) or ''
            h = h - 1 if h > 1 else 12
            return f'{h}:45{period}'
        t = re.sub(r'quarter\s+to\s+(\d{1,2})\s*(am|pm)?', _quarter_to, t, flags=re.IGNORECASE)

        # European hNN format: "13h00" → "13:00", "13h30" → "13:30"
        t = re.sub(r'\b([01]?\d|2[0-3])h([0-5]\d)\b', r'\1:\2', t, flags=re.IGNORECASE)

        return t
    
    def parse_time(self, text: str, post_timestamp=None) -> Optional[Dict[str, int]]:
        """
        Parse time from text with comprehensive pattern matching.
        
        Args:
            text: Text to parse (should be lowercase)
            
        Returns:
            Dict with 'hour' and 'minute' keys, or None if no valid time found
        """
        text = self._normalize(text.lower().strip())

        # Collect all candidate times with confidence scores
        candidates: List[Tuple[str, Dict[str, int], float]] = []

        # Pattern 1: Time ranges (extract start time)
        candidates.extend(self._parse_time_ranges(text))

        # Pattern 2: Single times
        candidates.extend(self._parse_single_times(text, post_timestamp))
        
        # Pattern 3: Special keywords
        candidates.extend(self._parse_special_keywords(text))
        
        # Validate and filter candidates
        valid_candidates = []
        for pattern_type, time_dict, confidence in candidates:
            if self._validate_time(time_dict['hour'], time_dict['minute']):
                valid_candidates.append((pattern_type, time_dict, confidence))
                logger.debug(f"Valid time candidate: {pattern_type} -> {time_dict['hour']}:{time_dict['minute']:02d} (confidence: {confidence})")
            else:
                logger.debug(f"Invalid time candidate rejected: {pattern_type} -> {time_dict}")
        
        if not valid_candidates:
            logger.info("No valid time candidates found")
            return None
        
        # Sort by confidence (highest first)
        valid_candidates.sort(key=lambda x: -x[2])
        
        best_pattern, best_time, best_confidence = valid_candidates[0]
        logger.info(f"Selected time: {best_time['hour']}:{best_time['minute']:02d} (pattern: {best_pattern}, confidence: {best_confidence:.2f})")
        
        return best_time
    
    def _parse_time_ranges(self, text: str) -> List[Tuple[str, Dict[str, int], float]]:
        """Parse time ranges and extract start time."""
        candidates = []
        SEP = r'(?:to|till|until|-|–)'

        # Pattern 1: H:MM AM/PM to H:MM AM/PM (most specific)
        # Examples: "6:30pm to 7pm", "at 6:30pm to 7:30pm", "from 6:30-7:30 PM"
        pattern = rf'(?:at|from)?\s*(\d{{1,2}})\s*[:.](\d{{2}})\s*(am|pm)\s*{SEP}\s*\d{{1,2}}\s*[:.]?\d{{0,2}}\s*(?:am|pm)?'
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            minute = int(match.group(2))
            period = match.group(3).upper()
            
            hour = self._convert_to_24h(hour, period)
            if hour is not None:
                candidates.append(('range_with_minutes_and_period', {'hour': hour, 'minute': minute}, 1.0))
        
        # Pattern 2: H AM/PM to H AM/PM (no minutes on start time)
        # Examples: "6pm to 7pm", "at 6pm to 7pm", "from 6-7 PM"
        pattern = rf'(?:at|from)?\s*(\d{{1,2}})\s*(am|pm)\s*{SEP}\s*\d{{1,2}}\s*(?:am|pm)?'
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            period = match.group(2).upper()
            
            hour = self._convert_to_24h(hour, period)
            if hour is not None:
                candidates.append(('range_without_minutes', {'hour': hour, 'minute': 0}, 0.95))
        
        # Pattern 3: H:MM-H:MM AM/PM (single AM/PM at end)
        # Examples: "6:30-7:30 PM", "6:30-7 PM"
        pattern = rf'(\d{{1,2}})\s*[:.](\d{{2}})\s*{SEP}\s*\d{{1,2}}\s*[:.]?\d{{0,2}}\s*(am|pm)'
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            minute = int(match.group(2))
            period = match.group(3).upper()
            
            hour = self._convert_to_24h(hour, period)
            if hour is not None:
                candidates.append(('range_single_period', {'hour': hour, 'minute': minute}, 0.9))
        
        # Pattern 4: H-H AM/PM (no minutes, single AM/PM at end)
        # Examples: "6-7 PM", "6-7pm"
        pattern = rf'(\d{{1,2}})\s*{SEP}\s*\d{{1,2}}\s*(am|pm)'
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            period = match.group(2).upper()

            hour = self._convert_to_24h(hour, period)
            if hour is not None:
                candidates.append(('range_no_minutes_single_period', {'hour': hour, 'minute': 0}, 0.85))

        # Pattern 5: H-H:MM AM/PM (no minutes on start, minutes on end)
        # Examples: "from 2-3:30 PM"
        pattern = rf'(?:at|from)?\s*(\d{{1,2}})\s*{SEP}\s*\d{{1,2}}\s*[:.]\d{{2}}\s*(am|pm)'
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            period = match.group(2).upper()

            hour = self._convert_to_24h(hour, period)
            if hour is not None:
                candidates.append(('range_asymmetric', {'hour': hour, 'minute': 0}, 0.92))

        return candidates
    
    def _parse_single_times(self, text: str, post_timestamp=None) -> List[Tuple[str, Dict[str, int], float]]:
        """Parse single time mentions."""
        candidates = []
        
        # Pattern 1: H:MM AM/PM (most specific)
        # Examples: "6:30 PM", "at 6:30pm", "6.30 PM"
        pattern = r'(?:at|by|around)?\s*(\d{1,2})\s*[:.](\d{2})\s*(am|pm)'
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            minute = int(match.group(2))
            period = match.group(3).upper()
            
            hour = self._convert_to_24h(hour, period)
            if hour is not None:
                candidates.append(('single_with_minutes', {'hour': hour, 'minute': minute}, 0.9))
        
        # Pattern 2: H AM/PM (no minutes)
        # Examples: "6 PM", "at 6pm", "6pm"
        pattern = r'(?:at|by|around)?\s*(\d{1,2})\s*(am|pm)(?!\s*to|-|–)'  # Negative lookahead to avoid ranges
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            period = match.group(2).upper()
            
            hour = self._convert_to_24h(hour, period)
            if hour is not None:
                candidates.append(('single_without_minutes', {'hour': hour, 'minute': 0}, 0.85))
        
        # Pattern 3: HH:MM (24-hour format, 2-digit hour)
        # Examples: "18:30", "09:00"
        pattern = r'(?:at|by|around)?\s*(\d{2}):(\d{2})(?!\s*(?:am|pm))'  # Negative lookahead for AM/PM
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            minute = int(match.group(2))
            
            # Must be valid 24-hour format
            if 0 <= hour <= 23:
                candidates.append(('24hour_format', {'hour': hour, 'minute': minute}, 0.8))
        
        # Pattern 4: H:MM (ambiguous - no AM/PM, assume PM if hour <= 12)
        # Examples: "6:30", "11:45"
        pattern = r'(?:at|by|around)?\s*(\d{1,2}):(\d{2})(?!\s*(?:am|pm))'
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            minute = int(match.group(2))

            # If hour > 12, it's 24-hour format
            if hour > 12:
                if hour <= 23:
                    candidates.append(('ambiguous_24hour', {'hour': hour, 'minute': minute}, 0.75))
            else:
                # Use post_timestamp to disambiguate, fall back to PM
                converted_hour = self._pick_am_or_pm(hour, minute, post_timestamp)
                candidates.append(('ambiguous_assume_pm', {'hour': converted_hour, 'minute': minute}, 0.7))

        # Pattern 5: 4-digit compact military time (1830, 0900, 1200)
        # Must be at a word boundary, not preceded or followed by another digit
        # Lower confidence (0.75) since it can conflict with room numbers
        pattern = r'(?<!\d)\b([01]\d|2[0-3])([0-5]\d)\b(?!\d)'
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            minute = int(match.group(2))
            candidates.append(('compact_24hour', {'hour': hour, 'minute': minute}, 0.75))

        return candidates
    
    def parse_time_range(self, text: str, post_timestamp=None) -> Optional[Dict[str, Optional[Dict[str, int]]]]:
        """
        Parse time range from text, returning both start and end times.

        Returns:
            Dict with 'start' and 'end' keys if a range is found.
            Returns {'start': time_dict, 'end': None} if only a single time found.
            Returns None if no time found at all.
        """
        text = self._normalize(text.lower().strip())

        # Shared separator group used in all range patterns
        SEP = r'(?:to|till|until|-|–)'

        # Pattern 1: H:MM AM/PM to H:MM AM/PM  (e.g. "6:30pm to 7pm", "from 6:30pm-7:30pm")
        pattern = rf'(?:at|from)?\s*(\d{{1,2}})\s*[:.](\d{{2}})\s*(am|pm)\s*{SEP}\s*(\d{{1,2}})\s*(?:[:.](\d{{2}}))?\s*(am|pm)?'
        match = re.search(pattern, text)
        if match:
            s_hour, s_min = int(match.group(1)), int(match.group(2))
            s_period = match.group(3).upper()
            e_hour = int(match.group(4))
            e_min = int(match.group(5)) if match.group(5) else 0
            e_period = match.group(6).upper() if match.group(6) else s_period

            s_h24 = self._convert_to_24h(s_hour, s_period)
            e_h24 = self._convert_to_24h(e_hour, e_period)
            if (s_h24 is not None and e_h24 is not None
                    and self._validate_time(s_h24, s_min) and self._validate_time(e_h24, e_min)):
                return {'start': {'hour': s_h24, 'minute': s_min},
                        'end':   {'hour': e_h24, 'minute': e_min}}

        # Pattern 2: H AM/PM to H AM/PM  (e.g. "6pm to 7pm")
        pattern = rf'(?:at|from)?\s*(\d{{1,2}})\s*(am|pm)\s*{SEP}\s*(\d{{1,2}})\s*(am|pm)?'
        match = re.search(pattern, text)
        if match:
            s_hour = int(match.group(1))
            s_period = match.group(2).upper()
            e_hour = int(match.group(3))
            e_period = match.group(4).upper() if match.group(4) else s_period

            s_h24 = self._convert_to_24h(s_hour, s_period)
            e_h24 = self._convert_to_24h(e_hour, e_period)
            if (s_h24 is not None and e_h24 is not None
                    and self._validate_time(s_h24, 0) and self._validate_time(e_h24, 0)):
                return {'start': {'hour': s_h24, 'minute': 0},
                        'end':   {'hour': e_h24, 'minute': 0}}

        # Pattern 3: H:MM-H:MM AM/PM  (single period at end, e.g. "6:30-7:30 PM")
        pattern = rf'(\d{{1,2}})\s*[:.](\d{{2}})\s*{SEP}\s*(\d{{1,2}})\s*(?:[:.](\d{{2}}))?\s*(am|pm)'
        match = re.search(pattern, text)
        if match:
            s_hour, s_min = int(match.group(1)), int(match.group(2))
            e_hour = int(match.group(3))
            e_min = int(match.group(4)) if match.group(4) else 0
            period = match.group(5).upper()

            s_h24 = self._convert_to_24h(s_hour, period)
            e_h24 = self._convert_to_24h(e_hour, period)
            if (s_h24 is not None and e_h24 is not None
                    and self._validate_time(s_h24, s_min) and self._validate_time(e_h24, e_min)):
                return {'start': {'hour': s_h24, 'minute': s_min},
                        'end':   {'hour': e_h24, 'minute': e_min}}

        # Pattern 4: H-H AM/PM  (e.g. "6-7 PM")
        pattern = rf'(\d{{1,2}})\s*{SEP}\s*(\d{{1,2}})\s*(am|pm)'
        match = re.search(pattern, text)
        if match:
            s_hour = int(match.group(1))
            e_hour = int(match.group(2))
            period = match.group(3).upper()

            s_h24 = self._convert_to_24h(s_hour, period)
            e_h24 = self._convert_to_24h(e_hour, period)
            if (s_h24 is not None and e_h24 is not None
                    and self._validate_time(s_h24, 0) and self._validate_time(e_h24, 0)):
                return {'start': {'hour': s_h24, 'minute': 0},
                        'end':   {'hour': e_h24, 'minute': 0}}

        # Pattern 5: H-H:MM AM/PM (asymmetric: no minutes on start)
        # Examples: "from 2-3:30 PM"
        pattern = rf'(?:at|from)?\s*(\d{{1,2}})\s*{SEP}\s*(\d{{1,2}})\s*[:.](\d{{2}})\s*(am|pm)'
        match = re.search(pattern, text)
        if match:
            s_hour, e_hour, e_min = int(match.group(1)), int(match.group(2)), int(match.group(3))
            period = match.group(4).upper()

            s_h24 = self._convert_to_24h(s_hour, period)
            e_h24 = self._convert_to_24h(e_hour, period)
            if (s_h24 is not None and e_h24 is not None
                    and self._validate_time(s_h24, 0) and self._validate_time(e_h24, e_min)):
                return {'start': {'hour': s_h24, 'minute': 0},
                        'end':   {'hour': e_h24, 'minute': e_min}}

        # No range found — fall back to single time
        start = self.parse_time(text, post_timestamp)
        if start:
            return {'start': start, 'end': None}

        return None

    def _parse_special_keywords(self, text: str) -> List[Tuple[str, Dict[str, int], float]]:
        """Parse special time keywords like 'noon' and 'midnight'."""
        candidates = []
        
        for keyword, time_dict in self.special_times.items():
            if keyword in text:
                candidates.append((f'special_{keyword}', time_dict.copy(), 0.7))
        
        return candidates
    
    def _pick_am_or_pm(self, hour_12: int, minute: int, post_timestamp) -> int:
        """Use post timestamp to pick AM vs PM for ambiguous times. Falls back to PM."""
        if post_timestamp is None:
            return (hour_12 + 12) if hour_12 != 12 else 12
        am_24 = 0 if hour_12 == 12 else hour_12
        pm_24 = 12 if hour_12 == 12 else hour_12 + 12
        post_total = post_timestamp.hour * 60 + post_timestamp.minute
        am_total = am_24 * 60 + minute
        pm_total = pm_24 * 60 + minute
        am_future = am_total > post_total
        pm_future = pm_total > post_total
        if am_future and not pm_future:
            return am_24
        elif pm_future and not am_future:
            return pm_24
        elif am_future and pm_future:
            return am_24  # Both future: pick sooner (AM)
        else:
            return pm_24  # Both past: fall back to PM

    def _convert_to_24h(self, hour: int, period: str) -> Optional[int]:
        """
        Convert 12-hour format to 24-hour format.
        
        Args:
            hour: Hour in 12-hour format (1-12)
            period: 'AM' or 'PM'
            
        Returns:
            Hour in 24-hour format (0-23), or None if invalid
        """
        # Guard against minutes being passed as hour (common regex group mixup).
        # Return None silently — the caller already discards this candidate.
        if hour == 0 or hour > 12:
            return None

        if not (1 <= hour <= 12):
            logger.warning(f"Invalid 12-hour format hour: {hour}")
            return None
        
        if period == 'AM':
            return 0 if hour == 12 else hour
        elif period == 'PM':
            return 12 if hour == 12 else hour + 12
        else:
            logger.warning(f"Invalid period: {period}")
            return None
    
    def _validate_time(self, hour: int, minute: int) -> bool:
        """Validate that time is reasonable."""
        if not (0 <= hour <= 23):
            logger.warning(f"Invalid hour: {hour}")
            return False
        
        if not (0 <= minute <= 59):
            logger.warning(f"Invalid minute: {minute}")
            return False
        
        return True


# Made with Bob