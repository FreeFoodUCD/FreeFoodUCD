import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import pytz


class EventExtractor:
    """Extract event details from text using NLP and pattern matching."""
    
    def __init__(self):
        self.timezone = pytz.timezone('Europe/Dublin')
        self.ucd_buildings = self.load_ucd_buildings()
        
        # Time patterns
        self.time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)',  # 6:30 PM
            r'(\d{1,2})\s*(am|pm|AM|PM)',  # 6 PM
            r'at\s+(\d{1,2})',  # at 6
            r'(\d{1,2})\.(\d{2})',  # 18.30
        ]
        
        # Free food keywords
        self.free_food_keywords = [
            'free food', 'free pizza', 'free', 'pizza', 'refreshments',
            'snacks', 'food', 'drinks', 'lunch', 'dinner', 'breakfast',
            'catering', 'buffet', 'nibbles'
        ]
        
        # Date keywords
        self.date_keywords = {
            'today': 0,
            'tonight': 0,
            'tomorrow': 1,
            'monday': self._days_until_weekday(0),
            'tuesday': self._days_until_weekday(1),
            'wednesday': self._days_until_weekday(2),
            'thursday': self._days_until_weekday(3),
            'friday': self._days_until_weekday(4),
            'saturday': self._days_until_weekday(5),
            'sunday': self._days_until_weekday(6),
        }
    
    def load_ucd_buildings(self) -> List[str]:
        """Load list of UCD buildings."""
        return [
            'Newman Building', 'Newman', 'O\'Brien Centre', 'O\'Brien',
            'James Joyce Library', 'Library', 'Student Centre',
            'Science Centre', 'Science', 'Engineering Building',
            'Quinn School', 'Sutherland School', 'Moore Centre',
            'Roebuck Castle', 'Belfield', 'Arts Building',
            'Agriculture Building', 'Veterinary', 'Smurfit',
            'Lochlann Quinn', 'Health Sciences', 'Conway Institute'
        ]
    
    def extract_event(self, text: str, source_type: str = 'post') -> Optional[Dict]:
        """
        Extract event details from text.
        
        Args:
            text: Text to extract from
            source_type: 'post' or 'story'
            
        Returns:
            Dictionary with event details or None if not a free food event
        """
        text_lower = text.lower()
        
        # Check for free food keywords
        if not self._contains_free_food(text_lower):
            return None
        
        # Extract components
        time = self._extract_time(text)
        date = self._extract_date(text_lower)
        location = self._extract_location(text)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(time, date, location)
        
        # Require minimum confidence
        if confidence < 0.4:
            return None
        
        # Combine date and time
        start_time = self._combine_datetime(date, time)
        
        # Generate title
        title = self._generate_title(text, location)
        
        return {
            'title': title,
            'description': text[:500] if len(text) > 500 else text,
            'location': location.get('full_location') if location else None,
            'location_building': location.get('building') if location else None,
            'location_room': location.get('room') if location else None,
            'start_time': start_time,
            'end_time': None,  # Could be enhanced
            'confidence_score': confidence,
            'raw_text': text,
            'extracted_data': {
                'time_found': time is not None,
                'date_found': date is not None,
                'location_found': location is not None,
            }
        }
    
    def _contains_free_food(self, text: str) -> bool:
        """Check if text contains free food keywords."""
        return any(keyword in text for keyword in self.free_food_keywords)
    
    def _extract_time(self, text: str) -> Optional[Dict]:
        """Extract time from text."""
        for pattern in self.time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                if len(groups) == 3:  # HH:MM AM/PM
                    hour = int(groups[0])
                    minute = int(groups[1])
                    period = groups[2].upper()
                    
                    if period == 'PM' and hour != 12:
                        hour += 12
                    elif period == 'AM' and hour == 12:
                        hour = 0
                    
                    return {'hour': hour, 'minute': minute}
                
                elif len(groups) == 2 and groups[1].upper() in ['AM', 'PM']:  # H AM/PM
                    hour = int(groups[0])
                    period = groups[1].upper()
                    
                    if period == 'PM' and hour != 12:
                        hour += 12
                    elif period == 'AM' and hour == 12:
                        hour = 0
                    
                    return {'hour': hour, 'minute': 0}
                
                elif len(groups) == 2 and groups[1].isdigit():  # HH.MM
                    hour = int(groups[0])
                    minute = int(groups[1])
                    return {'hour': hour, 'minute': minute}
        
        return None
    
    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract date from text."""
        now = datetime.now(self.timezone)
        
        # Check for date keywords
        for keyword, days_offset in self.date_keywords.items():
            if keyword in text:
                if callable(days_offset):
                    days_offset = days_offset()
                return now + timedelta(days=days_offset)
        
        # Try to parse date formats (dd/mm, mm/dd, etc.)
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})',  # dd/mm or mm/dd
            r'(\d{1,2})-(\d{1,2})',  # dd-mm
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                day = int(match.group(1))
                month = int(match.group(2))
                
                # Assume current year
                try:
                    date = datetime(now.year, month, day, tzinfo=self.timezone)
                    if date < now:
                        # If date is in the past, assume next year
                        date = datetime(now.year + 1, month, day, tzinfo=self.timezone)
                    return date
                except ValueError:
                    # Invalid date, try swapping day/month
                    try:
                        date = datetime(now.year, day, month, tzinfo=self.timezone)
                        if date < now:
                            date = datetime(now.year + 1, day, month, tzinfo=self.timezone)
                        return date
                    except ValueError:
                        pass
        
        # Default to today
        return now
    
    def _extract_location(self, text: str) -> Optional[Dict]:
        """Extract location from text."""
        # Check against known UCD buildings
        for building in self.ucd_buildings:
            if building.lower() in text.lower():
                # Try to extract room number
                room_patterns = [
                    rf'{building}\s+([A-Z]?\d+)',  # Newman A105
                    rf'{building}\s+room\s+([A-Z]?\d+)',  # Newman room A105
                    rf'room\s+([A-Z]?\d+)\s+{building}',  # room A105 Newman
                ]
                
                for pattern in room_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        return {
                            'building': building,
                            'room': match.group(1),
                            'full_location': f"{building} {match.group(1)}"
                        }
                
                return {
                    'building': building,
                    'room': None,
                    'full_location': building
                }
        
        # Try to find any location-like text
        location_patterns = [
            r'(?:at|in|@)\s+([A-Z][a-zA-Z\s]+(?:Building|Centre|Hall|Room))',
            r'(?:at|in|@)\s+([A-Z][a-zA-Z\s]+\d+)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                return {
                    'building': None,
                    'room': None,
                    'full_location': match.group(1).strip()
                }
        
        return None
    
    def _calculate_confidence(self, time: Optional[Dict], date: Optional[datetime], location: Optional[Dict]) -> float:
        """Calculate confidence score for extracted event."""
        score = 0.0
        
        # Base score for being detected as free food
        score += 0.3
        
        # Time found
        if time:
            score += 0.3
        
        # Date found (explicit date keyword)
        if date:
            score += 0.2
        
        # Location found
        if location:
            score += 0.2
            # Bonus for known UCD building
            if location.get('building'):
                score += 0.1
            # Bonus for room number
            if location.get('room'):
                score += 0.1
        
        return min(score, 1.0)
    
    def _combine_datetime(self, date: Optional[datetime], time: Optional[Dict]) -> datetime:
        """Combine date and time into single datetime."""
        if not date:
            date = datetime.now(self.timezone)
        
        if time:
            return date.replace(hour=time['hour'], minute=time['minute'], second=0, microsecond=0)
        else:
            # Default to 6 PM if no time specified
            return date.replace(hour=18, minute=0, second=0, microsecond=0)
    
    def _generate_title(self, text: str, location: Optional[Dict]) -> str:
        """Generate event title from text."""
        # Try to extract a meaningful title
        lines = text.split('\n')
        first_line = lines[0].strip()
        
        # If first line is short and descriptive, use it
        if len(first_line) < 100 and len(first_line) > 5:
            return first_line
        
        # Otherwise, generate generic title
        if location and location.get('building'):
            return f"Free Food at {location['building']}"
        
        return "Free Food Event"
    
    def _days_until_weekday(self, target_weekday: int):
        """Calculate days until target weekday."""
        def calculate():
            now = datetime.now(self.timezone)
            current_weekday = now.weekday()
            days = (target_weekday - current_weekday) % 7
            if days == 0:
                days = 7  # Next week if same day
            return days
        return calculate

# Made with Bob
