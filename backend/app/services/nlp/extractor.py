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
        
        # Named rooms within Student Centre: lowercase alias -> canonical display name
        # Checked first in _extract_location so "Blue Room" → "Blue Room, Student Centre"
        self.student_centre_rooms = {
            'blue room': 'Blue Room',
            'red room': 'Red Room',
            'fitzgerald chamber': 'FitzGerald Chamber',
            'fitzgerald': 'FitzGerald Chamber',
            'meeting room 5': 'Meeting Room 5',
            'meeting room 6': 'Meeting Room 6',
            'meeting room 7': 'Meeting Room 7',
            'harmony studio': 'Harmony Studio',
            'harmony': 'Harmony Studio',
            'astra hall': 'Astra Hall',
            'ucd cinema': 'UCD Cinema',
            'brava lounge': 'Brava Lounge',
            'atrium': 'Atrium',
            'main foyer': 'Main Foyer',
            'clubhouse bar': 'Clubhouse Bar',
            'clubhouse': 'Clubhouse Bar',
            "o'neill lounge": "O'Neill Lounge",
            'oneill lounge': "O'Neill Lounge",
        }
        # Sorted longest-first so "clubhouse bar" matches before "clubhouse", etc.
        self.student_centre_rooms_sorted = sorted(
            self.student_centre_rooms.keys(), key=len, reverse=True
        )

        # Named rooms within UCD Village
        self.village_rooms = {
            'village auditorium': 'Auditorium',
            'auditorium': 'Auditorium',
        }
        self.village_rooms_sorted = sorted(
            self.village_rooms.keys(), key=len, reverse=True
        )

        # Strong food indicators — sufficient on their own
        self.strong_food_keywords = [
            'free food', 'free pizza', 'free lunch', 'free dinner',
            'free breakfast', 'free snacks', 'free snack',
            'pizza', 'refreshments', 'catering', 'buffet', 'nibbles',
            'cookies', 'cookie', 'dessert', 'protein bar', 'protein bars',
            'kombucha', 'potluck', 'iftar', 'break the fast', 'banquet',
            'food provided', 'refreshments provided', 'food will be provided',
            'complimentary food', 'italian food', 'barbeque', 'bbq',
            'refreshers',
            'popcorn', 'nachos', 'crisps', 'chips', 'chocolate', 'cake', 'waffles',
            'biscuits', 'donuts', 'doughnuts', 'sweets', 'cupcakes',
            'sandwich', 'sandwiches', 'wrap', 'wraps', 'sushi', 'curry',
            'soup', 'pasta', 'tacos', 'burger', 'burgers',
        ]
        # Weak food indicators — only count if "free", "provided", or "complimentary"
        # also appears somewhere in the text
        self.weak_food_keywords = [
            'food', 'lunch', 'dinner', 'breakfast', 'drinks', 'drink',
            'snacks', 'snack', 'tea', 'coffee',
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
            # Named rooms — also listed so _has_ucd_location fires on room-only mentions
            'harmony studio': 'Student Centre',
            'harmony': 'Student Centre',
            'blue room': 'Student Centre',
            'red room': 'Student Centre',
            'fitzgerald chamber': 'Student Centre',
            'fitzgerald': 'Student Centre',
            'meeting room 5': 'Student Centre',
            'meeting room 6': 'Student Centre',
            'meeting room 7': 'Student Centre',
            'astra hall': 'Student Centre',
            'ucd cinema': 'Student Centre',
            'brava lounge': 'Student Centre',
            'atrium': 'Student Centre',
            'main foyer': 'Student Centre',
            'clubhouse bar': 'Student Centre',
            'clubhouse': 'Student Centre',
            "o'neill lounge": 'Student Centre',
            'oneill lounge': 'Student Centre',

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
        """
        Load list of off-campus venues to reject.
        Keep entries specific — avoid generic words that appear in on-campus contexts.
        Short words (bar, pub, grill) are matched with word boundaries in _is_off_campus.
        """
        return [
            # Named pubs/bars (specific — safe to substring-match)
            'kennedys', 'doyles', 'sinnotts', 'johnnie foxs',
            'blue light', 'taylors three rock', 'pub crawl',
            # Generic venue words — matched with word boundaries
            'brewery', 'tavern', 'pub', 'bar', 'grill', 'diner',
            # Named fast-food/restaurants
            'nandos', 'supermacs', 'eddie rockets',
            # Dublin off-campus areas
            'temple bar', 'grafton street', 'oconnell street',
            'rathmines', 'ranelagh', 'dundrum', 'city centre',
            'dublin 2', 'dublin 4', 'dublin mountains',
            # Social outings
            'night out', 'pub crawl',
        ]

    # Words in off_campus_venues that need word-boundary matching (too short/generic otherwise)
    _BOUNDARY_VENUES = {'pub', 'bar', 'grill', 'diner', 'tavern', 'brewery'}
    
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
    
    def _food_is_negated(self, text: str) -> bool:
        """
        Return True if food is explicitly negated in the text.
        Catches: "no food", "food not provided", "bring your own food", etc.
        """
        negation_patterns = [
            r'\bno\s+(?:free\s+)?(?:food|pizza|snacks?|refreshments?|lunch|dinner|breakfast|drinks?)\b',
            r'\b(?:food|pizza|snacks?|refreshments?|lunch|dinner|breakfast|drinks?)\s+(?:is\s+|are\s+)?not\s+(?:provided|available|included|served)\b',
            r'\bbring\s+your\s+own\s+(?:food|lunch|dinner)\b',
            r'\bbyof?\b',
            r'\bunfortunately\s+(?:\w+\s+){0,4}no\s+(?:food|pizza|snacks?|refreshments?)\b',
            r'\bno\s+food\s+(?:this\s+time|available|today)\b',
        ]
        for pattern in negation_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"Food negation matched: {pattern}")
                return True
        return False

    def _has_explicit_food(self, text: str) -> bool:
        """
        Two-tier food detection with negation check.

        Strong keywords: sufficient on their own (pizza, refreshments, etc.)
        Weak keywords: only count if "free" / "provided" / "complimentary" is also in the text.
        """
        # Negation check first
        if self._food_is_negated(text):
            logger.debug("REJECT: food keyword is negated")
            return False

        # "free entry" alone is NOT enough — must also have a food keyword
        if 'free entry' in text:
            has_food = any(kw in text for kw in self.strong_food_keywords + self.weak_food_keywords)
            if not has_food:
                logger.debug("REJECT: 'free entry' without food mention")
                return False

        # Strong keywords are always sufficient
        if any(kw in text for kw in self.strong_food_keywords):
            return True

        # Weak keywords only count when "free", "provided", or "complimentary" is present
        has_free_context = (
            'free' in text or 'provided' in text or 'complimentary' in text
        )
        if has_free_context and any(kw in text for kw in self.weak_food_keywords):
            return True

        return False
    
    def _is_other_college(self, text: str) -> bool:
        """Check if text mentions other Irish colleges.
        Short abbreviations (<=4 chars) use word boundaries to avoid false matches
        (e.g. 'ul' in 'full', 'mu' in 'music', 'dcu' in 'educational').
        """
        for college in self.other_colleges:
            if len(college) <= 4:
                if re.search(r'\b' + re.escape(college) + r'\b', text):
                    logger.debug(f"Found other college: {college}")
                    return True
            else:
                if college in text:
                    logger.debug(f"Found other college: {college}")
                    return True
        return False
    
    def _is_off_campus(self, text: str) -> bool:
        """
        Check if text mentions off-campus venues.
        Short/generic venue words use word boundaries to avoid false matches
        (e.g. 'bar' in 'candy bar', 'pub' in 'publication').
        Skip check if a known UCD building is already mentioned — on-campus wins.
        """
        if self._has_ucd_location(text):
            return False
        for venue in self.off_campus_venues:
            if venue in self._BOUNDARY_VENUES:
                if re.search(r'\b' + re.escape(venue) + r'\b', text):
                    logger.debug(f"Found off-campus venue (boundary): {venue}")
                    return True
            else:
                if venue in text:
                    logger.debug(f"Found off-campus venue: {venue}")
                    return True
        return False
    
    def _is_paid_event(self, text: str) -> bool:
        """
        Check if text indicates a paid event.

        Allow €2 membership. Ignore price mentions that are explicitly negated.
        Removed 'cost', 'price', 'pay' as standalone keywords — too many false
        positives ("no cost", "you don't need to pay", "free of charge").
        """
        # Explicit "it's free" overrides — check these first
        free_overrides = [
            r'\bfree\s+(?:of\s+)?(?:charge|cost|entry|admission)\b',
            r'\bno\s+(?:entry\s+)?(?:fee|cost|charge)\b',
            r'\bno\s+tickets?\s+(?:needed|required)\b',
            r"(?:don'?t|do\s+not|doesn'?t|does\s+not)\s+(?:need\s+to\s+)?pay\b",
            r'\bno\s+(?:need\s+to\s+)?pay\b',
            r'\bno\s+charge\b',
        ]
        for pattern in free_overrides:
            if re.search(pattern, text):
                logger.debug(f"Free override matched: {pattern}")
                return False

        # Allow €2 membership only
        if re.search(r'€2\b|\beuro\s+2\b|\b2\s*euro\b', text) or '€2' in text:
            if any(word in text for word in ['membership', 'ucard', 'sign up', 'member']):
                euro_matches = re.findall(r'€\d+|\beuro\s+\d+|\b\d+\s*euro', text)
                if len(euro_matches) == 1:
                    logger.debug("Found €2 membership - allowed")
                    return False

        # Reject any other explicit € price
        if re.search(r'€\d+|\beuro\s+\d+|\b\d+\s*euro', text):
            logger.debug("Found price indicator")
            return True

        # Reject ticket/entry fee keywords (not 'cost'/'price'/'pay' — too broad)
        paid_keywords = ['ticket', 'tickets', 'entry fee', 'admission']
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
    
    def _is_members_only(self, text: str) -> bool:
        patterns = [
            r'\bfor\s+members\b',
            r'\bmembers\s+only\b',
            r'\bonly\s+for\s+members\b',
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def _alias_in_text(self, alias: str, text_lower: str) -> bool:
        """
        Check if an alias appears in text.
        Aliases ≤ 4 chars use word boundaries to avoid false substring matches
        (e.g. 'eng' in 'england', 'vet' in 'veteran', 'jj' in 'hajj').
        """
        if len(alias) <= 4:
            return bool(re.search(r'\b' + re.escape(alias) + r'\b', text_lower))
        return alias in text_lower

    def _has_ucd_location(self, text: str) -> bool:
        """Check if text mentions UCD campus location."""
        return any(self._alias_in_text(alias, text) for alias in self.ucd_buildings)

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
                'members_only': self._is_members_only(text),
            }
        }
    
    def _extract_location(self, text: str) -> Optional[Dict]:
        """
        Extract location from text.

        Improvements over original:
        - Short aliases (≤4 chars) use word boundaries via _alias_in_text
        - Room format expanded: handles E1.32, C204A, AD1.01, G01 etc.
        - Global room scan: finds room even when it's in a separate sentence
        """
        text_lower = text.lower()

        # Named Student Centre rooms — check before generic building scan so
        # "Blue Room" → "Blue Room, Student Centre" rather than just "Student Centre"
        for alias in self.student_centre_rooms_sorted:
            if self._alias_in_text(alias, text_lower):
                room_name = self.student_centre_rooms[alias]
                return {
                    'building': 'Student Centre',
                    'room': room_name,
                    'full_location': f'{room_name}, Student Centre',
                }

        # Named UCD Village rooms — e.g. "auditorium" → "Auditorium, UCD Village"
        for alias in self.village_rooms_sorted:
            if self._alias_in_text(alias, text_lower):
                room_name = self.village_rooms[alias]
                return {
                    'building': 'UCD Village',
                    'room': room_name,
                    'full_location': f'{room_name}, UCD Village',
                }

        # Room regex: optional letter prefix, digits, optional .subdiv, optional suffix
        # Matches: 321, A5, G01, E1.32, C204A, AD1.01
        ROOM_RE = r'[A-Za-z]{0,3}\d+(?:[.\-]\d+)?[A-Za-z]?'

        # Check against known UCD buildings (longest alias first for specificity)
        for alias in self.ucd_buildings:
            if not self._alias_in_text(alias, text_lower):
                continue

            official = self.building_aliases[alias]

            # 1. Try room adjacent to building name
            adjacent_patterns = [
                rf'{re.escape(alias)}\s+(?:room\s+)?({ROOM_RE})',   # "engineering room 321" / "engineering E1.32"
                rf'room\s+({ROOM_RE})\s+(?:in\s+)?{re.escape(alias)}',  # "room 321 in engineering"
            ]
            for pattern in adjacent_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    room = match.group(1).upper()
                    return {
                        'building': official,
                        'room': room,
                        'full_location': f"{official}, Room {room}"
                    }

            # 2. Global room scan — room in a separate sentence/clause
            global_room = re.search(
                rf'\b(?:room|rm\.?)\s*({ROOM_RE})', text_lower
            )
            if global_room:
                room = global_room.group(1).upper()
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

        # Fallback: generic location-like text
        for pattern in [
            r'(?:at|in|@)\s+([A-Z][a-zA-Z\s]+(?:Building|Centre|Hall|Room))',
            r'(?:at|in|@)\s+([A-Z][a-zA-Z\s]+\d+)',
        ]:
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
