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
    
    def parse_time(self, text: str) -> Optional[Dict[str, int]]:
        """
        Parse time from text with comprehensive pattern matching.
        
        Args:
            text: Text to parse (should be lowercase)
            
        Returns:
            Dict with 'hour' and 'minute' keys, or None if no valid time found
        """
        text = text.lower().strip()
        
        # Collect all candidate times with confidence scores
        candidates: List[Tuple[str, Dict[str, int], float]] = []
        
        # Pattern 1: Time ranges (extract start time)
        candidates.extend(self._parse_time_ranges(text))
        
        # Pattern 2: Single times
        candidates.extend(self._parse_single_times(text))
        
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
        
        # Pattern 1: H:MM AM/PM to H:MM AM/PM (most specific)
        # Examples: "6:30pm to 7pm", "at 6:30pm to 7:30pm", "from 6:30-7:30 PM"
        pattern = r'(?:at|from)?\s*(\d{1,2})\s*[:.](\d{2})\s*(am|pm)\s*(?:to|-|–)\s*\d{1,2}\s*[:.]?\d{0,2}\s*(?:am|pm)?'
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            minute = int(match.group(2))
            period = match.group(3).upper()
            
            hour = self._convert_to_24h(hour, period)
            if hour is not None:
                candidates.append(('range_with_minutes_and_period', {'hour': hour, 'minute': minute}, 1.0))
        
        # Pattern 2: H AM/PM to H AM/PM (no minutes on start time)
        # Examples: "6pm to 7pm", "at 6pm to 7pm", "from 6-7 PM"
        pattern = r'(?:at|from)?\s*(\d{1,2})\s*(am|pm)\s*(?:to|-|–)\s*\d{1,2}\s*(?:am|pm)?'
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            period = match.group(2).upper()
            
            hour = self._convert_to_24h(hour, period)
            if hour is not None:
                candidates.append(('range_without_minutes', {'hour': hour, 'minute': 0}, 0.95))
        
        # Pattern 3: H:MM-H:MM AM/PM (single AM/PM at end)
        # Examples: "6:30-7:30 PM", "6:30-7 PM"
        pattern = r'(\d{1,2})\s*[:.](\d{2})\s*(?:-|–)\s*\d{1,2}\s*[:.]?\d{0,2}\s*(am|pm)'
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            minute = int(match.group(2))
            period = match.group(3).upper()
            
            hour = self._convert_to_24h(hour, period)
            if hour is not None:
                candidates.append(('range_single_period', {'hour': hour, 'minute': minute}, 0.9))
        
        # Pattern 4: H-H AM/PM (no minutes, single AM/PM at end)
        # Examples: "6-7 PM", "6-7pm"
        pattern = r'(\d{1,2})\s*(?:-|–)\s*\d{1,2}\s*(am|pm)'
        for match in re.finditer(pattern, text):
            hour = int(match.group(1))
            period = match.group(2).upper()
            
            hour = self._convert_to_24h(hour, period)
            if hour is not None:
                candidates.append(('range_no_minutes_single_period', {'hour': hour, 'minute': 0}, 0.85))
        
        return candidates
    
    def _parse_single_times(self, text: str) -> List[Tuple[str, Dict[str, int], float]]:
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
                # Assume PM for events
                converted_hour = hour + 12 if hour != 12 else 12
                candidates.append(('ambiguous_assume_pm', {'hour': converted_hour, 'minute': minute}, 0.7))
        
        return candidates
    
    def parse_time_range(self, text: str) -> Optional[Dict[str, Optional[Dict[str, int]]]]:
        """
        Parse time range from text, returning both start and end times.

        Returns:
            Dict with 'start' and 'end' keys if a range is found.
            Returns {'start': time_dict, 'end': None} if only a single time found.
            Returns None if no time found at all.
        """
        text = text.lower().strip()

        # Pattern 1: H:MM AM/PM to H:MM AM/PM  (e.g. "6:30pm to 7pm", "from 6:30pm-7:30pm")
        pattern = r'(?:at|from)?\s*(\d{1,2})\s*[:.](\d{2})\s*(am|pm)\s*(?:to|-|–)\s*(\d{1,2})\s*(?:[:.](\d{2}))?\s*(am|pm)?'
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
        pattern = r'(?:at|from)?\s*(\d{1,2})\s*(am|pm)\s*(?:to|-|–)\s*(\d{1,2})\s*(am|pm)?'
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
        pattern = r'(\d{1,2})\s*[:.](\d{2})\s*(?:-|–)\s*(\d{1,2})\s*(?:[:.](\d{2}))?\s*(am|pm)'
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
        pattern = r'(\d{1,2})\s*(?:-|–)\s*(\d{1,2})\s*(am|pm)'
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

        # No range found — fall back to single time
        start = self.parse_time(text)
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
    
    def _convert_to_24h(self, hour: int, period: str) -> Optional[int]:
        """
        Convert 12-hour format to 24-hour format.
        
        Args:
            hour: Hour in 12-hour format (1-12)
            period: 'AM' or 'PM'
            
        Returns:
            Hour in 24-hour format (0-23), or None if invalid
        """
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