import re
import unicodedata
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import pytz
import logging
from app.services.nlp.date_parser import DateParser
from app.services.nlp.time_parser import TimeParser

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
        self.time_parser = TimeParser()
        # building_aliases: lowercase alias -> official display name
        self.building_aliases = self.load_building_aliases()
        # sorted longest-first so specific matches beat short ones (e.g. "engineering building" before "engineering")
        self.ucd_buildings = sorted(self.building_aliases.keys(), key=len, reverse=True)
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
        
    
    def load_building_aliases(self) -> Dict[str, str]:
        """
        Map every known alias / abbreviation (lowercase) to the official building name.
        Sorted longest-first in __init__ so specific matches win over short ones.
        """
        return {
            # Newman Building
            'newman building': 'Newman Building',
            'arts building': 'Newman Building',
            'the arts block': 'Newman Building',
            'arts block': 'Newman Building',
            'newman': 'Newman Building',

            # O'Brien Centre for Science
            "o'brien centre for science": "O'Brien Centre for Science",
            'obrien centre for science': "O'Brien Centre for Science",
            'obrien centre': "O'Brien Centre for Science",
            'the science building': "O'Brien Centre for Science",
            'science building': "O'Brien Centre for Science",
            'science centre': "O'Brien Centre for Science",
            "o'brien": "O'Brien Centre for Science",
            'obrien': "O'Brien Centre for Science",
            'science': "O'Brien Centre for Science",

            # James Joyce Library
            'james joyce library': 'James Joyce Library',
            'the library': 'James Joyce Library',
            'library': 'James Joyce Library',
            'jj': 'James Joyce Library',

            # Sutherland School of Law
            'sutherland school of law': 'Sutherland School of Law',
            'sutherland': 'Sutherland School of Law',
            'law building': 'Sutherland School of Law',

            # Lochlann Quinn School of Business
            'lochlann quinn school of business': 'Lochlann Quinn School of Business',
            'the business school': 'Lochlann Quinn School of Business',
            'business school': 'Lochlann Quinn School of Business',
            'lochlann quinn': 'Lochlann Quinn School of Business',
            'quinn school': 'Lochlann Quinn School of Business',
            'quinn': 'Lochlann Quinn School of Business',

            # Engineering & Materials Science Centre
            'engineering & materials science centre': 'Engineering & Materials Science Centre',
            'engineering and materials science centre': 'Engineering & Materials Science Centre',
            'engineering building': 'Engineering & Materials Science Centre',
            'engineering': 'Engineering & Materials Science Centre',
            'eng building': 'Engineering & Materials Science Centre',
            'eng': 'Engineering & Materials Science Centre',

            # Agriculture & Food Science Centre
            'agriculture & food science centre': 'Agriculture & Food Science Centre',
            'agriculture and food science centre': 'Agriculture & Food Science Centre',
            'agriculture building': 'Agriculture & Food Science Centre',
            'ag building': 'Agriculture & Food Science Centre',
            'ag science': 'Agriculture & Food Science Centre',

            # Health Sciences Centre
            'health sciences centre': 'Health Sciences Centre',
            'health sciences': 'Health Sciences Centre',
            'health sci': 'Health Sciences Centre',

            # Veterinary Sciences Centre
            'veterinary sciences centre': 'Veterinary Sciences Centre',
            'the vet school': 'Veterinary Sciences Centre',
            'vet school': 'Veterinary Sciences Centre',
            'veterinary': 'Veterinary Sciences Centre',
            'vet': 'Veterinary Sciences Centre',

            # Computer Science & Informatics Centre
            'computer science & informatics centre': 'Computer Science & Informatics Centre',
            'computer science and informatics centre': 'Computer Science & Informatics Centre',
            'comp sci building': 'Computer Science & Informatics Centre',
            'cs building': 'Computer Science & Informatics Centre',
            'computer science': 'Computer Science & Informatics Centre',
            'comp sci': 'Computer Science & Informatics Centre',

            # Daedalus Building
            'daedalus building': 'Daedalus Building',
            'daedalus': 'Daedalus Building',

            # Confucius Institute
            'confucius institute': 'Confucius Institute',
            'confucius': 'Confucius Institute',

            # Hanna Sheehy-Skeffington Building
            'hanna sheehy-skeffington building': 'Hanna Sheehy-Skeffington Building',
            'skeffington': 'Hanna Sheehy-Skeffington Building',
            'arts annexe': 'Hanna Sheehy-Skeffington Building',

            # Agnes McGuire Social Work Building
            'agnes mcguire social work building': 'Agnes McGuire Social Work Building',
            'agnes mcguire': 'Agnes McGuire Social Work Building',

            # Tierney Building
            'tierney building': 'Tierney Building',
            'tierney': 'Tierney Building',

            # Gerard Manley Hopkins Centre
            'gerard manley hopkins centre': 'Gerard Manley Hopkins Centre',
            'international office': 'Gerard Manley Hopkins Centre',
            'ucd global': 'Gerard Manley Hopkins Centre',
            'gmh': 'Gerard Manley Hopkins Centre',

            # Student Centre
            'the student centre': 'Student Centre',
            'student centre': 'Student Centre',

            # UCD Village
            'ucd village': 'UCD Village',
            'the village': 'UCD Village',
            'village': 'UCD Village',

            # O'Reilly Hall
            "o'reilly hall": "O'Reilly Hall",
            'oreilly hall': "O'Reilly Hall",
            "o'reilly": "O'Reilly Hall",
            'oreilly': "O'Reilly Hall",

            # The Main Restaurant
            'the main restaurant': 'The Main Restaurant',
            'main restaurant': 'The Main Restaurant',
            'the main rest': 'The Main Restaurant',
            'the rest': 'The Main Restaurant',

            # UCD Sports Centre
            'ucd sports centre': 'UCD Sports Centre',
            'sports centre': 'UCD Sports Centre',
            'the gym': 'UCD Sports Centre',

            # The Pavilion
            'the pavilion': 'The Pavilion',
            'the pav': 'The Pavilion',
            'pav': 'The Pavilion',

            # Conway Institute
            'conway institute': 'Conway Institute',
            'conway': 'Conway Institute',

            # Charles Institute of Dermatology
            'charles institute of dermatology': 'Charles Institute of Dermatology',
            'charles institute': 'Charles Institute of Dermatology',
            'charles': 'Charles Institute of Dermatology',

            # Geary Institute for Public Policy
            'geary institute for public policy': 'Geary Institute for Public Policy',
            'geary institute': 'Geary Institute for Public Policy',
            'geary': 'Geary Institute for Public Policy',

            # Clinton Institute
            'clinton institute': 'Clinton Institute',
            'belfield house': 'Clinton Institute',
            'clinton': 'Clinton Institute',

            # NovaUCD
            'novaucd': 'NovaUCD',
            'merville house': 'NovaUCD',
            'nova': 'NovaUCD',

            # Richview School of Architecture
            'richview school of architecture': 'Richview School of Architecture',
            'richview': 'Richview School of Architecture',
            'architecture': 'Richview School of Architecture',

            # Newstead Building
            'newstead building': 'Newstead Building',
            'newstead': 'Newstead Building',

            # UCD Earth Institute
            'ucd earth institute': 'UCD Earth Institute',
            'earth institute': 'UCD Earth Institute',

            # Roebuck Hall / Castle
            'roebuck hall': 'Roebuck Hall',
            'roebuck castle': 'Roebuck Hall',
            'roebuck': 'Roebuck Hall',

            # Generic campus keywords (no specific building)
            'belfield': 'UCD Belfield',
            'ucd': 'UCD Belfield',
            'campus': 'UCD Belfield',
        }
    
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
        # Allow €2 membership only
        if re.search(r'€2\b|\beuro\s+2\b|\b2\s*euro\b', text) or '€2' in text:
            if any(word in text for word in ['membership', 'ucard', 'sign up', 'member']):
                # Check if there are OTHER prices mentioned
                euro_matches = re.findall(r'€\d+|\beuro\s+\d+|\b\d+\s*euro', text)
                if len(euro_matches) == 1:
                    logger.debug("Found €2 membership - allowed")
                    return False  # Only €2 mentioned, it's membership

        # Reject ANY other price mention
        if re.search(r'€\d+|\beuro\s+\d+|\b\d+\s*euro', text):
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

    def get_rejection_reason(self, text: str) -> str:
        """
        Return a human-readable reason why a post was rejected (or 'Accepted').
        Runs the same checks as classify_event but surfaces which rule fired.
        """
        clean_text = self._preprocess_text(text)

        if not self._has_explicit_food(clean_text):
            return "No explicit food keyword found"

        if self._is_other_college(clean_text):
            for college in self.other_colleges:
                if college in clean_text:
                    return f"Mentions other college: '{college}'"

        if self._is_off_campus(clean_text):
            for venue in self.off_campus_venues:
                if venue in clean_text:
                    return f"Mentions off-campus venue: '{venue}'"

        if self._is_paid_event(clean_text):
            return "Appears to be a paid event (price/ticket mention)"

        if self._is_nightlife_event(clean_text):
            for keyword in self.nightlife_keywords:
                if keyword in clean_text:
                    return f"Nightlife event keyword: '{keyword}'"

        return "Accepted"

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
        time_range = self.time_parser.parse_time_range(text.lower())
        time = time_range['start'] if time_range else None
        end_time_dict = time_range['end'] if time_range else None
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
        end_time = self._combine_datetime(date, end_time_dict) if end_time_dict else None

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
            'end_time': end_time,
            'confidence_score': confidence,
            'raw_text': text,
            'extracted_data': {
                'time_found': time is not None,
                'date_found': date is not None,
                'location_found': location is not None,
            }
        }
    
    def _extract_location(self, text: str) -> Optional[Dict]:
        """Extract location from text."""
        text_lower = text.lower()

        # Check against known UCD buildings (longest alias first for specificity)
        for alias in self.ucd_buildings:
            if alias in text_lower:
                official = self.building_aliases[alias]
                # Try to extract room number
                room_patterns = [
                    rf'{re.escape(alias)}\s+([A-Z]?\d+)',         # e.g. "engineering 321"
                    rf'{re.escape(alias)}\s+room\s+([A-Z]?\d+)',  # e.g. "engineering room 321"
                    rf'room\s+([A-Z]?\d+)\s+{re.escape(alias)}',  # e.g. "room 321 engineering"
                ]

                for pattern in room_patterns:
                    match = re.search(pattern, text_lower, re.IGNORECASE)
                    if match:
                        room = match.group(1).upper()
                        return {
                            'building': official,
                            'room': room,
                            'full_location': f"{official}, Room {room}"
                        }

                return {
                    'building': official,
                    'room': None,
                    'full_location': official
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
            # Validate hour and minute
            hour = time.get('hour', 18)
            minute = time.get('minute', 0)
            
            if not (0 <= hour <= 23):
                logger.warning(f"Invalid hour {hour}, defaulting to 18:00")
                hour = 18
                minute = 0
            
            if not (0 <= minute <= 59):
                logger.warning(f"Invalid minute {minute}, defaulting to 0")
                minute = 0
            
            return date.replace(hour=hour, minute=minute, second=0, microsecond=0)
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
    
# Made with Bob
