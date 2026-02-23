"""
Comprehensive date parser for Instagram event posts.
Handles all common date formats with proper validation and edge case handling.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import pytz
import logging

logger = logging.getLogger(__name__)


class DateParser:
    """Robust date parser with comprehensive pattern matching and validation."""
    
    def __init__(self, timezone: pytz.timezone):
        self.timezone = timezone
        
        # Month name mappings (full and abbreviated)
        self.month_map = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sept': 9, 'sep': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        # Weekday mappings
        self.weekday_map = {
            'monday': 0, 'mon': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1,
            'wednesday': 2, 'wed': 2,
            'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
            'friday': 4, 'fri': 4,
            'saturday': 5, 'sat': 5,
            'sunday': 6, 'sun': 6
        }
        
        # Relative date keywords
        self.relative_keywords = {
            'today': 0,
            'tonight': 0,
            'tomorrow': 1,
        }
    
    def parse_date(self, text: str, reference_date: Optional[datetime] = None) -> Optional[datetime]:
        """
        Parse date from text with comprehensive pattern matching.
        
        Args:
            text: Text to parse (should be lowercase)
            reference_date: Reference date for relative dates (default: now)
            
        Returns:
            Parsed datetime or None if no valid date found
        """
        if reference_date is None:
            reference_date = datetime.now(self.timezone)
        
        text = text.lower().strip()
        
        # Collect all candidate dates with confidence scores
        candidates: List[Tuple[str, datetime, float]] = []
        
        # Pattern 1: Day + Month + Weekday (e.g., "23 February, Monday")
        candidates.extend(self._parse_day_month_weekday(text, reference_date))
        
        # Pattern 2: Weekday + Day + Month (e.g., "Monday 23 February")
        candidates.extend(self._parse_weekday_day_month(text, reference_date))
        
        # Pattern 3: Month + Day + Weekday (e.g., "February 23, Monday")
        candidates.extend(self._parse_month_day_weekday(text, reference_date))
        
        # Pattern 4: Day + Month (no weekday) (e.g., "23 February")
        candidates.extend(self._parse_day_month(text, reference_date))
        
        # Pattern 5: Month + Day (no weekday) (e.g., "February 23")
        candidates.extend(self._parse_month_day(text, reference_date))
        
        # Pattern 6: Numeric dates (e.g., "23/02", "23-02-26")
        candidates.extend(self._parse_numeric_date(text, reference_date))
        
        # Pattern 7: Weekday + Numeric date (e.g., "Monday 23/02")
        candidates.extend(self._parse_weekday_numeric(text, reference_date))
        
        # Pattern 8: Day only with ordinal (e.g., "23rd", "the 23rd")
        candidates.extend(self._parse_day_only(text, reference_date))
        
        # Pattern 9: Relative keywords (e.g., "tomorrow", "next Monday")
        candidates.extend(self._parse_relative(text, reference_date))
        
        # Validate and filter candidates
        valid_candidates = []
        for pattern_type, date, confidence in candidates:
            if self._validate_date(date, reference_date):
                valid_candidates.append((pattern_type, date, confidence))
                logger.debug(f"Valid candidate: {pattern_type} -> {date.strftime('%A %d/%m/%Y')} (confidence: {confidence})")
            else:
                logger.debug(f"Invalid candidate rejected: {pattern_type} -> {date.strftime('%A %d/%m/%Y')}")
        
        if not valid_candidates:
            logger.info("No valid date candidates found, using reference date")
            return reference_date
        
        # Sort by confidence (highest first), then by date (earliest first)
        valid_candidates.sort(key=lambda x: (-x[2], x[1]))
        
        best_pattern, best_date, best_confidence = valid_candidates[0]
        logger.info(f"Selected date: {best_date.strftime('%A %d/%m/%Y')} (pattern: {best_pattern}, confidence: {best_confidence:.2f})")
        
        return best_date
    
    def _parse_day_month_weekday(self, text: str, ref_date: datetime) -> List[Tuple[str, datetime, float]]:
        """Parse: 23 February, Monday | 23rd February Monday | 23 Feb, Mon"""
        candidates = []
        
        # Build month pattern (all month names and abbreviations)
        month_pattern = '|'.join(self.month_map.keys())
        weekday_pattern = '|'.join(self.weekday_map.keys())
        
        # Pattern: DD [ordinal] Month [,] Weekday
        pattern = rf'(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_pattern})[\s,]+(?:on\s+)?({weekday_pattern})'
        
        for match in re.finditer(pattern, text):
            day = int(match.group(1))
            month_name = match.group(2)
            weekday_name = match.group(3)
            
            month = self.month_map[month_name]
            expected_weekday = self.weekday_map[weekday_name]
            
            # Try current year
            date = self._create_date(ref_date.year, month, day)
            if date and date.weekday() == expected_weekday:
                if date >= ref_date - timedelta(days=1):
                    candidates.append(('day_month_weekday_validated', date, 1.0))
                    continue
            
            # Try next year
            date = self._create_date(ref_date.year + 1, month, day)
            if date and date.weekday() == expected_weekday:
                candidates.append(('day_month_weekday_validated', date, 1.0))
                continue
            
            # Weekday doesn't match - trust the date, not the weekday
            date = self._create_date(ref_date.year, month, day)
            if date:
                if date < ref_date - timedelta(days=1):
                    date = self._create_date(ref_date.year + 1, month, day)
                if date:
                    candidates.append(('day_month_weekday_mismatch', date, 0.9))
                    logger.warning(f"Weekday mismatch: {weekday_name} vs {date.strftime('%A')} for {day}/{month}")
        
        return candidates
    
    def _parse_weekday_day_month(self, text: str, ref_date: datetime) -> List[Tuple[str, datetime, float]]:
        """Parse: Monday 23 February | Mon, 23rd Feb"""
        candidates = []
        
        month_pattern = '|'.join(self.month_map.keys())
        weekday_pattern = '|'.join(self.weekday_map.keys())
        
        # Pattern: Weekday [,] [the] DD [ordinal] Month
        pattern = rf'({weekday_pattern})[\s,]+(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_pattern})'
        
        for match in re.finditer(pattern, text):
            weekday_name = match.group(1)
            day = int(match.group(2))
            month_name = match.group(3)
            
            month = self.month_map[month_name]
            expected_weekday = self.weekday_map[weekday_name]
            
            # Try current year
            date = self._create_date(ref_date.year, month, day)
            if date and date.weekday() == expected_weekday:
                if date >= ref_date - timedelta(days=1):
                    candidates.append(('weekday_day_month_validated', date, 1.0))
                    continue
            
            # Try next year
            date = self._create_date(ref_date.year + 1, month, day)
            if date and date.weekday() == expected_weekday:
                candidates.append(('weekday_day_month_validated', date, 1.0))
                continue
            
            # Weekday mismatch
            date = self._create_date(ref_date.year, month, day)
            if date:
                if date < ref_date - timedelta(days=1):
                    date = self._create_date(ref_date.year + 1, month, day)
                if date:
                    candidates.append(('weekday_day_month_mismatch', date, 0.9))
        
        return candidates
    
    def _parse_month_day_weekday(self, text: str, ref_date: datetime) -> List[Tuple[str, datetime, float]]:
        """Parse: February 23, Monday | Feb 23rd Mon"""
        candidates = []
        
        month_pattern = '|'.join(self.month_map.keys())
        weekday_pattern = '|'.join(self.weekday_map.keys())
        
        # Pattern: Month DD [ordinal] [,] Weekday
        pattern = rf'({month_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?[\s,]+({weekday_pattern})'
        
        for match in re.finditer(pattern, text):
            month_name = match.group(1)
            day = int(match.group(2))
            weekday_name = match.group(3)
            
            month = self.month_map[month_name]
            expected_weekday = self.weekday_map[weekday_name]
            
            # Try current year
            date = self._create_date(ref_date.year, month, day)
            if date and date.weekday() == expected_weekday:
                if date >= ref_date - timedelta(days=1):
                    candidates.append(('month_day_weekday_validated', date, 1.0))
                    continue
            
            # Try next year
            date = self._create_date(ref_date.year + 1, month, day)
            if date and date.weekday() == expected_weekday:
                candidates.append(('month_day_weekday_validated', date, 1.0))
                continue
            
            # Weekday mismatch
            date = self._create_date(ref_date.year, month, day)
            if date:
                if date < ref_date - timedelta(days=1):
                    date = self._create_date(ref_date.year + 1, month, day)
                if date:
                    candidates.append(('month_day_weekday_mismatch', date, 0.9))
        
        return candidates
    
    def _parse_day_month(self, text: str, ref_date: datetime) -> List[Tuple[str, datetime, float]]:
        """Parse: 23 February | 23rd Feb"""
        candidates = []
        
        month_pattern = '|'.join(self.month_map.keys())
        
        # Pattern: DD [ordinal] Month
        pattern = rf'(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_pattern})(?!\s+\d)'
        
        for match in re.finditer(pattern, text):
            day = int(match.group(1))
            month_name = match.group(2)
            month = self.month_map[month_name]
            
            # Try current year
            date = self._create_date(ref_date.year, month, day)
            if date and date >= ref_date - timedelta(days=1):
                candidates.append(('day_month', date, 0.85))
                continue
            
            # Try next year
            date = self._create_date(ref_date.year + 1, month, day)
            if date:
                candidates.append(('day_month', date, 0.85))
        
        return candidates
    
    def _parse_month_day(self, text: str, ref_date: datetime) -> List[Tuple[str, datetime, float]]:
        """Parse: February 23 | Feb 23rd"""
        candidates = []
        
        month_pattern = '|'.join(self.month_map.keys())
        
        # Pattern: Month DD [ordinal]
        pattern = rf'({month_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?!\s*/)'
        
        for match in re.finditer(pattern, text):
            month_name = match.group(1)
            day = int(match.group(2))
            month = self.month_map[month_name]
            
            # Try current year
            date = self._create_date(ref_date.year, month, day)
            if date and date >= ref_date - timedelta(days=1):
                candidates.append(('month_day', date, 0.85))
                continue
            
            # Try next year
            date = self._create_date(ref_date.year + 1, month, day)
            if date:
                candidates.append(('month_day', date, 0.85))
        
        return candidates
    
    def _parse_numeric_date(self, text: str, ref_date: datetime) -> List[Tuple[str, datetime, float]]:
        """Parse: 23/02 | 23-02 | 23.02 | 23/02/26 (DD/MM format - European)"""
        candidates = []
        
        # Pattern: DD/MM or DD/MM/YY or DD/MM/YYYY
        # Support separators: / - .
        pattern = r'(\d{1,2})[/\-\.](\d{1,2})(?:[/\-\.](\d{2,4}))?'
        
        for match in re.finditer(pattern, text):
            day = int(match.group(1))
            month = int(match.group(2))
            year_str = match.group(3)
            
            # Determine year
            if year_str:
                year = int(year_str)
                if year < 100:  # 2-digit year
                    year += 2000
            else:
                year = ref_date.year
            
            # Create date (DD/MM format)
            date = self._create_date(year, month, day)
            if date:
                if date < ref_date - timedelta(days=1):
                    # Try next year
                    date = self._create_date(year + 1, month, day)
                
                if date:
                    confidence = 0.8 if year_str else 0.75
                    candidates.append(('numeric_date', date, confidence))
        
        return candidates
    
    def _parse_weekday_numeric(self, text: str, ref_date: datetime) -> List[Tuple[str, datetime, float]]:
        """Parse: Monday 23/02 | Mon, 23-02"""
        candidates = []
        
        weekday_pattern = '|'.join(self.weekday_map.keys())
        
        # Pattern: Weekday [,] DD/MM
        pattern = rf'({weekday_pattern})[\s,]+(\d{{1,2}})[/\-\.](\d{{1,2}})'
        
        for match in re.finditer(pattern, text):
            weekday_name = match.group(1)
            day = int(match.group(2))
            month = int(match.group(3))
            
            expected_weekday = self.weekday_map[weekday_name]
            
            # Try current year
            date = self._create_date(ref_date.year, month, day)
            if date and date.weekday() == expected_weekday:
                if date >= ref_date - timedelta(days=1):
                    candidates.append(('weekday_numeric_validated', date, 0.95))
                    continue
            
            # Try next year
            date = self._create_date(ref_date.year + 1, month, day)
            if date and date.weekday() == expected_weekday:
                candidates.append(('weekday_numeric_validated', date, 0.95))
                continue
            
            # Weekday mismatch
            date = self._create_date(ref_date.year, month, day)
            if date:
                if date < ref_date - timedelta(days=1):
                    date = self._create_date(ref_date.year + 1, month, day)
                if date:
                    candidates.append(('weekday_numeric_mismatch', date, 0.8))
        
        return candidates
    
    def _parse_day_only(self, text: str, ref_date: datetime) -> List[Tuple[str, datetime, float]]:
        """Parse: 23rd | the 23rd"""
        candidates = []
        
        # Pattern: [the] DD [ordinal]
        pattern = r'(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)(?!\s*[:/]|\s+(?:am|pm|january|february|march|april|may|june|july|august|september|october|november|december))'
        
        for match in re.finditer(pattern, text):
            day = int(match.group(1))
            
            # Try current month
            date = self._create_date(ref_date.year, ref_date.month, day)
            if date and date >= ref_date - timedelta(days=1):
                candidates.append(('day_only', date, 0.5))
                continue
            
            # Try next month
            next_month = ref_date.month + 1
            next_year = ref_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            
            date = self._create_date(next_year, next_month, day)
            if date:
                candidates.append(('day_only', date, 0.5))
        
        return candidates
    
    def _parse_relative(self, text: str, ref_date: datetime) -> List[Tuple[str, datetime, float]]:
        """Parse: today | tomorrow | next Monday | this Friday"""
        candidates = []
        
        # Simple relative keywords
        for keyword, days_offset in self.relative_keywords.items():
            if keyword in text:
                date = ref_date + timedelta(days=days_offset)
                candidates.append((f'relative_{keyword}', date, 0.6))
        
        # Weekday references: "next Monday", "this Friday"
        weekday_pattern = '|'.join(self.weekday_map.keys())
        
        # "next [weekday]"
        pattern = rf'next\s+({weekday_pattern})'
        for match in re.finditer(pattern, text):
            weekday_name = match.group(1)
            target_weekday = self.weekday_map[weekday_name]
            
            # Find next occurrence of this weekday (at least 7 days away)
            days_ahead = (target_weekday - ref_date.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            
            date = ref_date + timedelta(days=days_ahead)
            candidates.append(('relative_next_weekday', date, 0.65))
        
        # "this [weekday]" or just "[weekday]" alone
        pattern = rf'(?:this\s+)?({weekday_pattern})(?!\s+\d)'
        for match in re.finditer(pattern, text):
            weekday_name = match.group(1)
            target_weekday = self.weekday_map[weekday_name]
            
            # Find next occurrence of this weekday (within next 7 days)
            days_ahead = (target_weekday - ref_date.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # Next week if same day
            
            date = ref_date + timedelta(days=days_ahead)
            candidates.append(('relative_this_weekday', date, 0.6))
        
        return candidates
    
    def _create_date(self, year: int, month: int, day: int) -> Optional[datetime]:
        """Safely create a datetime object."""
        try:
            return datetime(year, month, day, tzinfo=self.timezone)
        except ValueError:
            return None
    
    def _validate_date(self, date: datetime, ref_date: datetime) -> bool:
        """Validate that date is reasonable."""
        # Must not be more than 1 day in the past
        if date < ref_date - timedelta(days=1):
            return False
        
        # Must not be more than 90 days in the future
        if date > ref_date + timedelta(days=90):
            return False
        
        return True


# Made with Bob