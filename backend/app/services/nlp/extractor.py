import re
import unicodedata
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import pytz
import logging
from app.services.nlp.date_parser import DateParser

logger = logging.getLogger(__name__)


class EventExtractor:
    """
    Strict TRUE/FALSE classifier for free food events at UCD.
    
    Returns TRUE only if:
    - Free food is explicitly mentioned
    - Event is at UCD Belfield campus (or assumed on-campus)
    - NOT at another college
    - NOT off-campus venue
    - NOT a paid event (except €2 membership)
    - NOT a nightlife event (ball, pub crawl, etc.)
    """
    
    def __init__(self):
        self.timezone = pytz.timezone('Europe/Dublin')
        self.date_parser = DateParser(self.timezone)
        self.ucd_buildings = self.load_ucd_buildings()
        self.other_colleges = self.load_other_colleges()
        self.off_campus_venues = self.load_off_campus_venues()
        self.nightlife_keywords = self.load_nightlife_keywords()
        
        # Explicit food keywords only (removed vague terms like "free", "join us", "study session")
        self.explicit_food_keywords = [
            # Explicit free food phrases
            'free food', 'free pizza', 'free lunch', 'free dinner',
            'free breakfast', 'free snacks', 'free snack',
            
            # Food types (include both singular and plural)
            'pizza', 'refreshments', 'snacks', 'snack', 'food', 'drinks', 'drink',
            'lunch', 'dinner', 'breakfast', 'catering', 'buffet',
            'nibbles', 'tea', 'coffee', 'cookies', 'cookie', 'dessert',
            'protein bar', 'protein bars', 'kombucha',
            
            # Cultural/special events
            'potluck', 'iftar', 'break the fast', 'banquet',
            
            # Provision phrases
            'food provided', 'refreshments provided',
            'complimentary food', 'italian food'
        ]
        
        # Time patterns (for extraction after classification)
        self.time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)',  # 6:30 PM
            r'(\d{1,2})\s*(am|pm|AM|PM)',  # 6 PM
            r'at\s+(\d{1,2})',  # at 6
            r'(\d{1,2})\.(\d{2})',  # 18.30
        ]
        
        # Date keywords (for extraction after classification)
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
        """Load list of UCD buildings and campus keywords."""
        return [
            'newman building', 'newman', 'obrien centre', 'obrien',
            'james joyce library', 'library', 'student centre',
            'science centre', 'science', 'engineering building',
            'quinn school', 'sutherland school', 'moore centre',
            'roebuck castle', 'belfield', 'arts building',
            'agriculture building', 'veterinary', 'smurfit',
            'lochlann quinn', 'health sciences', 'conway institute',
            'astra hall', 'ucd', 'campus'
        ]
    
    def load_other_colleges(self) -> List[str]:
        """Load list of other Irish colleges to reject."""
        return [
            'dcu', 'trinity', 'tcd', 'maynooth', 'mu', 'nuig', 'ucc', 'ul',
            'dublin city university', 'trinity college', 'maynooth university'
        ]
    
    def load_off_campus_venues(self) -> List[str]:
        """Load list of off-campus venues to reject."""
        return [
            # Pubs/Bars
            'pub', 'bar', 'brewery', 'tavern',
            'kennedys', 'doyles', 'sinnotts',
            'johnnie foxs', 'blue light', 'taylors',
            'three rock', 'pub crawl',
            
            # Restaurants/Cafes
            'restaurant', 'cafe', 'bistro', 'grill', 'diner',
            'nandos', 'supermacs', 'eddie rockets',
            
            # Dublin Areas (off-campus)
            'soho', 'temple bar', 'grafton street', 'oconnell street',
            'rathmines', 'ranelagh', 'dundrum', 'city centre',
            'dublin 2', 'dublin 4', 'dublin mountains',
            
            # Social outings
            'night out', 'mixer at', 'meet at', 'heading to'
        ]
    
    def load_nightlife_keywords(self) -> List[str]:
        """Load list of nightlife event keywords to reject."""
        return [
            'ball', 'gala', 'formal', 'pub crawl', 'night out',
            'nightclub', 'club night', 'bar crawl',
            'pre drinks', 'afters', 'sesh', 'going out'
        ]
    
    def _preprocess_text(self, text: str) -> str:
        """
        Clean and normalize text before classification.
        
        - Remove URLs
        - Remove @mentions
        - Remove emojis
        - Normalize unicode (é → e)
        - Clean whitespace
        - Lowercase
        """
        # Remove URLs
        text = re.sub(r'http\S+|www\.\S+', '', text)
        
        # Remove @mentions
        text = re.sub(r'@\w+', '', text)
        
        # Normalize unicode (é → e, ñ → n)
        text = unicodedata.normalize('NFKD', text)
        
        # Remove non-ASCII characters (emojis, special chars)
        text = text.encode('ascii', 'ignore').decode('ascii')
        
        # Clean whitespace
        text = ' '.join(text.split())
        
        # Lowercase
        return text.lower()
    
    def classify_event(self, text: str) -> bool:
        """
        Strict TRUE/FALSE classifier for free food events.
        
        Returns TRUE only if ALL conditions met:
        1. Explicit food keyword present
        2. NOT other college
        3. NOT off-campus venue (explicit rejection)
        4. NOT paid event (except €2 membership)
        5. NOT nightlife event
        6. UCD location is OPTIONAL (assume on-campus if not mentioned)
        
        Args:
            text: Combined Instagram caption + OCR text
            
        Returns:
            True if free food event at UCD, False otherwise
        """
        # Preprocess text
        clean_text = self._preprocess_text(text)
        
        logger.debug(f"Classifying text: {clean_text[:100]}...")
        
        # Rule 1: MUST have explicit food keyword
        if not self._has_explicit_food(clean_text):
            logger.debug("REJECT: No explicit food keyword")
            return False
        
        # Rule 2: MUST NOT be other college
        if self._is_other_college(clean_text):
            logger.debug("REJECT: Other college mentioned")
            return False
        
        # Rule 3: MUST NOT be off-campus (EXPLICIT rejection)
        if self._is_off_campus(clean_text):
            logger.debug("REJECT: Off-campus venue mentioned")
            return False
        
        # Rule 4: MUST NOT be paid (except €2 membership)
        if self._is_paid_event(clean_text):
            logger.debug("REJECT: Paid event indicator")
            return False
        
        # Rule 5: MUST NOT be nightlife event
        if self._is_nightlife_event(clean_text):
            logger.debug("REJECT: Nightlife event")
            return False
        
        # UCD location is OPTIONAL
        # If mentioned → great
        # If not mentioned → assume on-campus (UCD society default)
        # If off-campus → already rejected in Rule 3
        
        has_ucd_location = self._has_ucd_location(clean_text)
        if has_ucd_location:
            logger.info("ACCEPT: Free food event at UCD (explicit location)")
        else:
            logger.info("ACCEPT: Free food event at UCD (assumed on-campus)")
        
        return True
    
    def _has_explicit_food(self, text: str) -> bool:
        """
        Check for explicit food keywords.
        
        REJECT "free entry" without food mention.
        """
        # "free entry" alone is NOT enough
        if 'free entry' in text:
            has_food = any(
                food in text for food in ['food', 'pizza', 'snacks', 'refreshments', 'lunch', 'dinner']
            )
            if not has_food:
                logger.debug("REJECT: 'free entry' without food mention")
                return False
        
        # Check for explicit food keywords
        return any(keyword in text for keyword in self.explicit_food_keywords)
    
    def _is_other_college(self, text: str) -> bool:
        """Check if text mentions other Irish colleges."""
        for college in self.other_colleges:
            if college in text:
                logger.debug(f"Found other college: {college}")
                return True
        return False
    
    def _is_off_campus(self, text: str) -> bool:
        """Check if text mentions off-campus venues."""
        for venue in self.off_campus_venues:
            if venue in text:
                logger.debug(f"Found off-campus venue: {venue}")
                return True
        return False
    
    def _is_paid_event(self, text: str) -> bool:
        """
        Check if text indicates a paid event.
        
        Allow €2 membership only.
        Reject ANY other price mention.
        """
        # Allow €2 or e2 membership only
        if 'e2' in text or '€2' in text or 'euro 2' in text:
            if any(word in text for word in ['membership', 'ucard', 'sign up', 'member']):
                # Check if there are OTHER prices mentioned
                euro_matches = re.findall(r'€\d+|e\d+|euro \d+', text)
                if len(euro_matches) == 1:
                    logger.debug("Found €2 membership - allowed")
                    return False  # Only €2 mentioned, it's membership
        
        # Reject ANY other price mention
        if re.search(r'€\d+|e\d+|euro \d+', text):
            logger.debug("Found price indicator")
            return True
        
        # Reject ticket/entry fee keywords
        paid_keywords = ['ticket', 'tickets', 'entry fee', 'admission', 'cost', 'price', 'pay']
        for keyword in paid_keywords:
            if keyword in text:
                logger.debug(f"Found paid keyword: {keyword}")
                return True
        
        return False
    
    def _is_nightlife_event(self, text: str) -> bool:
        """Check if text indicates a nightlife event (ball, pub crawl, etc.)."""
        for keyword in self.nightlife_keywords:
            if keyword in text:
                logger.debug(f"Found nightlife keyword: {keyword}")
                return True
        return False
    
    def _has_ucd_location(self, text: str) -> bool:
        """Check if text mentions UCD campus location."""
        return any(building in text for building in self.ucd_buildings)
    
    # ========== Event Detail Extraction (called AFTER classification) ==========
    
    def extract_event(self, text: str, source_type: str = 'post', post_timestamp: Optional[datetime] = None) -> Optional[Dict]:
        """
        Extract event details from text.
        
        This method should be called AFTER classify_event() returns True.
        It extracts time, date, location, and generates event details.
        
        Args:
            text: Text to extract from (caption + OCR text combined)
            source_type: 'post' or 'story'
            post_timestamp: When the post was made (for date validation)
            
        Returns:
            Dictionary with event details or None if classification fails
        """
        # First, classify the event
        if not self.classify_event(text):
            return None
        
        # Extract event details
        time = self._extract_time(text)
        date = self.date_parser.parse_date(text.lower(), post_timestamp)
        location = self._extract_location(text)
        
        # Validate date is not in the past
        if date:
            now = datetime.now(self.timezone)
            if date < now - timedelta(days=1):
                logger.warning(f"Extracted date {date} is in the past, rejecting event")
                return None
        
        # Combine date and time
        start_time = self._combine_datetime(date, time)
        
        # Generate title
        title = self._generate_title(text, location)
        
        # Calculate confidence (simplified - just for compatibility)
        confidence = 1.0 if (time and location) else 0.8
        
        return {
            'title': title,
            'description': text[:500] if len(text) > 500 else text,
            'location': location.get('full_location') if location else None,
            'location_building': location.get('building') if location else None,
            'location_room': location.get('room') if location else None,
            'start_time': start_time,
            'end_time': None,
            'confidence_score': confidence,
            'raw_text': text,
            'extracted_data': {
                'time_found': time is not None,
                'date_found': date is not None,
                'location_found': location is not None,
            }
        }
    
    def _extract_time(self, text: str) -> Optional[Dict]:
        """Extract time from text, prioritizing start times in ranges."""
        # First, check for time ranges (e.g., "from 2-3:30 PM", "2:00-3:30 PM")
        range_patterns = [
            r'from\s+(\d{1,2})\s*(?::(\d{2}))?\s*(?:-|–|to)\s*\d{1,2}(?::\d{2})?\s*(am|pm|AM|PM)',  # from 2-3:30 PM
            r'(\d{1,2})\s*(?::(\d{2}))?\s*(?:-|–)\s*\d{1,2}(?::\d{2})?\s*(am|pm|AM|PM)',  # 2-3:30 PM
            r'from\s+(\d{1,2})\s*(am|pm|AM|PM)\s*(?:-|–|to)',  # from 2 PM to
        ]
        
        for pattern in range_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    hour = int(groups[0])
                    # Check if groups[1] is a number (minute) or AM/PM
                    if groups[1] and groups[1].lower() not in ['am', 'pm']:
                        minute = int(groups[1])
                        period = groups[2].upper() if len(groups) > 2 and groups[2] else None
                    else:
                        # groups[1] is AM/PM, not minute
                        minute = 0
                        period = groups[1].upper() if groups[1] else None
                    
                    if period:
                        if period == 'PM' and hour != 12:
                            hour += 12
                        elif period == 'AM' and hour == 12:
                            hour = 0
                    
                    return {'hour': hour, 'minute': minute}
                except (ValueError, IndexError) as e:
                    logger.debug(f"Error parsing time range: {e}")
                    continue
        
        # If no range found, use regular time patterns
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
                
                elif len(groups) == 2:
                    try:
                        if groups[1] and groups[1].upper() in ['AM', 'PM']:  # H AM/PM
                            hour = int(groups[0])
                            period = groups[1].upper()
                            
                            if period == 'PM' and hour != 12:
                                hour += 12
                            elif period == 'AM' and hour == 12:
                                hour = 0
                            
                            return {'hour': hour, 'minute': 0}
                        elif groups[1] and groups[1].isdigit():  # HH.MM
                            hour = int(groups[0])
                            minute = int(groups[1])
                            return {'hour': hour, 'minute': minute}
                    except (ValueError, AttributeError) as e:
                        logger.debug(f"Error parsing time: {e}")
                        continue
        
        return None
    
    def _extract_location(self, text: str) -> Optional[Dict]:
        """Extract location from text."""
        text_lower = text.lower()
        
        # Check against known UCD buildings
        for building in self.ucd_buildings:
            if building in text_lower:
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
                            'building': building.title(),
                            'room': match.group(1),
                            'full_location': f"{building.title()} {match.group(1)}"
                        }
                
                return {
                    'building': building.title(),
                    'room': None,
                    'full_location': building.title()
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
