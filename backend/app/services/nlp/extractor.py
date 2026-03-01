import re
import unicodedata
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import pytz
import logging
from app.services.nlp.date_parser import DateParser
from app.services.nlp.time_parser import TimeParser
from app.core.config import settings

logger = logging.getLogger(__name__)

# Map food/drink emojis to the text keyword they represent.
# Applied in _preprocess_text before ASCII stripping so that a caption like
# "🍕🍕 provided tonight" becomes "pizza pizza provided tonight" and is caught
# by the strong-keyword classifier.
_FOOD_EMOJI_MAP: Dict[str, str] = {
    # Pizza / burgers / handheld
    '🍕': 'pizza',
    '🍔': 'burger',
    '🌭': 'burger',
    '🌮': 'tacos',
    '🌯': 'sandwich',
    '🥙': 'sandwich',
    '🥪': 'sandwich',
    # Mains
    '🍜': 'food',
    '🍛': 'curry',
    '🍝': 'pasta',
    '🍲': 'soup',
    '🍣': 'sushi',
    '🍱': 'food',
    '🍟': 'food',
    '🍖': 'food',
    '🍗': 'food',
    '🥘': 'food',
    '🥗': 'food',
    '🥩': 'food',
    '🥓': 'food',
    '🧆': 'food',
    # Bread / pastries
    '🍞': 'food',
    '🥖': 'food',
    '🥐': 'croissant',
    '🥯': 'food',
    '🥨': 'snacks',
    # Breakfast
    '🧇': 'waffles',
    '🥞': 'pancakes',
    '🥚': 'food',
    '🧀': 'food',
    # Sweet / dessert
    '🍰': 'cake',
    '🎂': 'cake',
    '🧁': 'cupcakes',
    '🍩': 'donuts',
    '🍪': 'cookies',
    '🍫': 'chocolate',
    '🍿': 'popcorn',
    '🍭': 'sweets',
    '🍬': 'sweets',
    '🍦': 'ice cream',
    '🍨': 'ice cream',
    '🍧': 'ice cream',
    '🍮': 'food',
    # Snacks
    '🥜': 'snacks',
    '🧂': 'food',
    # Hot drinks
    '☕': 'coffee',
    '🫖': 'tea',
    '🍵': 'tea',
    # Cold drinks
    '🧋': 'drinks',
    '🥛': 'drinks',
    '🥤': 'drinks',
    '🧃': 'drinks',
    # Alcoholic (maps to drinks so weak-keyword + "free"/"provided" still fires)
    '🍷': 'drinks',
    '🍸': 'drinks',
    '🍹': 'drinks',
    '🍺': 'drinks',
    '🍻': 'drinks',
    '🥂': 'drinks',
}


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
            'global lounge': 'Global Lounge',
            'newman basement': 'Newman Basement',
            'newstead atrium': 'Newstead Atrium',
        }
        # Sorted longest-first so "clubhouse bar" matches before "clubhouse", etc.
        self.student_centre_rooms_sorted = sorted(
            self.student_centre_rooms.keys(), key=len, reverse=True
        )

        # Named rooms within UCD Village
        self.village_rooms = {
            'village auditorium': 'Auditorium',
            'auditorium': 'Auditorium',
            'village kitchen': 'Kitchen',
            'ucd village kitchen': 'Kitchen',
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
            'kombucha', 'potluck', 'banquet',
            'food provided', 'refreshments provided', 'food will be provided',
            'complimentary food', 'italian food', 'barbeque', 'bbq',
            'brunch', 'coffee morning',
            'popcorn', 'nachos', 'crisps', 'chips', 'chocolate', 'cake', 'waffles',
            'biscuits', 'donuts', 'doughnuts', 'sweets', 'cupcakes',
            'sandwich', 'sandwiches', 'sushi', 'curry',
            'soup', 'pasta', 'tacos', 'burger', 'burgers',
            # Hot drinks & morning events
            'hot chocolate', 'tea morning', 'tea afternoon', 'coffee afternoon',
            'fika',
            # Baked goods & pastries
            'croissant', 'croissants', 'pastries', 'pastry', 'baked goods',
            'gingerbread', 'pancakes',
            # General treats
            'treats', 'sweet treats', 'ice cream',
            # Snacks (unambiguous in society context)
            'snacks',
            # Informal food terms common in UCD/Irish society posts
            'light bites',
            'food and drinks', 'food and drink', 'food & drinks', 'food & drink',
            'food on the night',
            'grub', 'munchies',
            # Implied-free event types (cultural norm at UCD — these events always have food)
            'welcome reception', 'freshers fair', "fresher's fair",
            'open evening',
        ]
        # Weak food indicators — only count if "free", "provided", or "complimentary"
        # (or other context modifiers) also appears somewhere in the text
        self.weak_food_keywords = [
            'food', 'lunch', 'dinner', 'breakfast', 'drinks', 'drink',
            'snack', 'tea', 'coffee',
            'refreshers',   # demoted: "Refreshers Week" posts have no food mention
        ]
        # Context modifiers that make weak food keywords count as sufficient evidence.
        # Extends the original {"free", "provided", "complimentary"} set.
        self.context_modifiers = [
            'provided', 'complimentary', 'included', 'on us', 'on the house',
            'kindly sponsored', 'brought to you by', 'at no cost', 'at no charge',
            'for free',
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

            # O'Brien Centre for Science — East/West wings (L2)
            'science east': "O'Brien Centre for Science",
            'science west': "O'Brien Centre for Science",
            "o'brien east": "O'Brien Centre for Science",
            "o'brien west": "O'Brien Centre for Science",
            'obrien east': "O'Brien Centre for Science",
            'obrien west': "O'Brien Centre for Science",

            # UCD Village Kitchen (L3) — compound form only, 'kitchen' alone too generic
            'village kitchen': 'UCD Village',
            'ucd village kitchen': 'UCD Village',

            # UCD Horticulture Garden / Polytunnel (L4)
            'polytunnel': 'UCD Horticulture Garden',
            'horticulture garden': 'UCD Horticulture Garden',
            'ucd horticulture': 'UCD Horticulture Garden',
            'rosemount': 'UCD Rosemount',
            'rosemount complex': 'UCD Rosemount',

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

        # Replace food/drink emojis with their text equivalents BEFORE ASCII
        # stripping so "🍕 provided" → "pizza provided" (caught by classifier)
        for emoji, keyword in _FOOD_EMOJI_MAP.items():
            text = text.replace(emoji, f' {keyword} ')

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

        # Iftar block: exclude regardless of other food keywords
        _iftar_kw = ['iftar', 'iftaar', 'break the fast']
        if any(kw in clean_text for kw in _iftar_kw):
            logger.debug("REJECT: Iftar/religious event")
            return False

        # A3: Past-tense recap filter — before food detection (cheaper, high precision)
        if self._is_past_tense_post(clean_text):
            logger.debug("REJECT: Past-tense recap post")
            return False

        # Rule 1: MUST have explicit food keyword (A2: now uses richer context modifiers)
        if not self._has_explicit_food(clean_text):
            logger.debug("REJECT: No explicit food keyword")
            return False

        # Rule 1.5: NOT a food activity workshop/competition
        if self._is_food_activity(clean_text):
            logger.debug("REJECT: Food activity workshop")
            return False

        # A7: NOT a social-media giveaway/contest
        if self._is_giveaway_contest(clean_text):
            logger.debug("REJECT: Giveaway/contest")
            return False

        # A5: Staff/committee-only filter
        if self._is_staff_only(clean_text):
            logger.debug("REJECT: Staff/committee-only event")
            return False

        # Rule 2: MUST NOT be other college
        if self._is_other_college(clean_text):
            logger.debug("REJECT: Other college mentioned")
            return False

        # Rule 3: MUST NOT be off-campus (EXPLICIT rejection)
        if self._is_off_campus(clean_text):
            logger.debug("REJECT: Off-campus venue mentioned")
            return False

        # Rule 3.5: NOT an online-only event (reject if online signals + no UCD location)
        if self._is_online_event(clean_text) and not self._has_ucd_location(clean_text):
            logger.debug("REJECT: Online/virtual event with no UCD location")
            return False

        # Rule 4: MUST NOT be paid (A6: score-based, not purely binary)
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
            r'\bbring\s+your\s+own\s+(?:food|lunch|dinner|snacks?|drinks?)\b',
            r'\bbyof?\b',
            r'\b(?:food|drinks?|coffee|tea|snacks?|refreshments?)\s+(?:available\s+)?for\s+(?:sale|purchase)\b',
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

        # Weak keywords only count when a free/provision context modifier is present
        has_free_context = (
            'free' in text
            or any(mod in text for mod in self.context_modifiers)
            or bool(re.search(r"\bwe.(?:ll|will)\s+(?:be\s+)?(?:bring(?:ing)?|have|provide|serve|supply)\b", text))
        )
        if has_free_context and any(kw in text for kw in self.weak_food_keywords):
            return True

        return False

    def _has_weak_food_only(self, text: str) -> bool:
        """
        True when text has a weak food keyword but NO strong keyword and NO free context.
        Identifies grey-zone posts for LLM fallback (Phase B).
        text must already be preprocessed (lowercased, emoji-mapped).
        """
        if self._food_is_negated(text):
            return False
        if any(kw in text for kw in self.strong_food_keywords):
            return False
        has_free_context = (
            'free' in text
            or any(mod in text for mod in self.context_modifiers)
            or bool(re.search(
                r"\bwe.(?:ll|will)\s+(?:be\s+)?(?:bring(?:ing)?|have|provide|serve|supply)\b", text
            ))
        )
        if has_free_context:
            return False
        return any(kw in text for kw in self.weak_food_keywords)

    def _try_llm_fallback(self, text: str) -> Optional[dict]:
        """
        Called when classify_event() returns False. Runs grey-zone check + hard filters,
        then calls LLM for classification + extraction hints.
        Returns hint dict {food, location, time} if LLM accepts, else None.
        """
        if not (settings.USE_SCORING_PIPELINE and settings.OPENAI_API_KEY):
            return None

        clean = self._preprocess_text(text)

        if not self._has_weak_food_only(clean):
            return None  # not even borderline — hard reject

        # Hard filters still run before LLM — no bypassing safety checks
        if (self._is_food_activity(clean)
                or self._is_staff_only(clean)
                or self._is_other_college(clean)
                or self._is_off_campus(clean)
                or (self._is_online_event(clean) and not self._has_ucd_location(clean))
                or self._is_paid_event(clean)
                or self._is_nightlife_event(clean)):
            return None

        from app.services.nlp.llm_classifier import get_llm_classifier
        llm = get_llm_classifier()
        if llm is None:
            return None

        hints = llm.classify_and_extract(clean)
        if not hints or not hints.get('food'):
            return None

        return hints

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
        Return True only if the event is clearly a paid-access event.

        Improvements over original binary approach:
        - Small amounts (≤€5) without explicit ticket/admission language are NOT
          rejected — catches "€5 registration, refreshments provided" cases.
        - Membership context with reasonable price (≤€5) is always allowed.
        - Hard reject only for: explicit ticket language + any price, OR amounts ≥€10
          without an explicit free-food override.
        - Food-sale keywords (bake sale, fundraiser) are always hard-rejected.
        """
        # Step 1: Free overrides — explicit "free" / "no ticket needed" etc.
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

        # Step 2: Membership context — allow any price ≤€5 (UCD membership fees vary)
        is_member_context = bool(re.search(r'\b(?:membership|ucard)\b', text))
        euro_amounts = [int(x) for x in re.findall(r'€(\d+)', text)]
        if is_member_context and euro_amounts and all(a <= 5 for a in euro_amounts):
            logger.debug("Found membership price ≤€5 — allowed")
            return False

        # Step 3: Explicit ticket / admission language → always paid
        # (even without a price, registering for "tickets" implies a paid event)
        has_ticket_language = bool(re.search(
            r'\b(?:tickets?|admission|entry\s+fee|buy\s+(?:your\s+)?tickets?|get\s+(?:your\s+)?tickets?)\b',
            text
        ))
        if has_ticket_language:
            logger.debug("Found ticket/admission language")
            return True

        # Step 4: Large price (≥€10) without an explicit free-food statement → paid
        if euro_amounts and max(euro_amounts) >= 10:
            has_free_food_stated = bool(re.search(
                r'\bfree\s+(?:food|pizza|lunch|dinner|snacks?|refreshments?|drinks?|coffee|tea|breakfast)\b',
                text
            ))
            if not has_free_food_stated:
                logger.debug(f"Found large price €{max(euro_amounts)} with no free-food override")
                return True

        # Step 5: Food-sale keywords — food is sold, not given away
        food_sale_keywords = [
            'bake sale', 'cake sale', 'cookie sale', 'food sale', 'food stall',
            'fundraiser', 'charity sale', 'charity bake',
        ]
        for keyword in food_sale_keywords:
            if keyword in text:
                logger.debug(f"Found food-sale keyword: {keyword}")
                return True

        return False
    
    def _is_nightlife_event(self, text: str) -> bool:
        """Check if text indicates a nightlife event (ball, pub crawl, etc.)."""
        for keyword in self.nightlife_keywords:
            if keyword in text:
                logger.debug(f"Found nightlife keyword: {keyword}")
                return True
        return False

    def _is_giveaway_contest(self, text: str) -> bool:
        """Reject social-media giveaway/contest posts.
        These are entry-based competitions, not free food provision at an event.
        """
        patterns = [
            r'\bgiveaway\b',
            r'\benter\s+to\s+win\b',
            r'\bchance\s+to\s+win\b',
            r'\bprize\s+draw\b',
            r'\bsweepstakes?\b',
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def _is_food_activity(self, text: str) -> bool:
        """
        Reject food-making workshops/competitions where food is the activity
        material, not something freely provided to attendees.
        Returns True (reject) unless explicit provision language overrides.
        """
        activity_patterns = [
            r'\b(?:pizza|sushi|cookie|cake|bread|pasta|burger|chocolate|mochi|ramen|biscuit|brownie)\s+(?:making|workshop|class|tutorial|decorating|competition|contest)\b',
            r'\b(?:baking|cooking|pastry|barista)\s+(?:class|workshop|course|tutorial|competition|contest)\b',
            r'\bbake.?off\b',
            r'\bcook.?off\b',
            r'\bbaking\s+competition\b',
            r'\bcooking\s+competition\b',
        ]
        has_activity = any(re.search(p, text, re.IGNORECASE) for p in activity_patterns)
        if not has_activity:
            return False

        # Override: food IS being provided separately from the activity
        provision_overrides = [
            r'\bfood\s+(?:provided|included|served|on\s+us)\b',
            r'\brefreshments\s+(?:provided|available|included)\b',
            r'\bwe.(?:ll|will)\s+(?:be\s+)?(?:provide|have|serve|bring(?:ing)?)\s+(?:the\s+)?(?:food|refreshments|snacks?|pizza|cookies?|cake|treats?)\b',
            r'\bfree\s+(?:food|pizza|cookies?|cake|snacks?)\b',
        ]
        has_provision = any(re.search(p, text, re.IGNORECASE) for p in provision_overrides)
        return not has_provision

    def _is_online_event(self, text: str) -> bool:
        """
        Return True if the post describes an online/virtual-only event.
        Hybrid posts that ALSO mention a UCD location are NOT rejected here —
        the caller checks _has_ucd_location separately.
        """
        online_patterns = [
            r'\bonline\s+event\b',
            r'\bvirtual\s+(?:event|session|talk|seminar|workshop|class|lecture|info\s+session)\b',
            r'\bvia\s+zoom\b',
            r'\bon\s+zoom\b',
            r'\bzoom\s+(?:call|meeting|link|event)\b',
            r'\bremote(?:ly)?\s+(?:hosted|held|event)\b',
            r'\bwatch\s+(?:live\s+)?(?:online|on\s+youtube|on\s+twitch)\b',
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in online_patterns)

    def _is_members_only(self, text: str) -> bool:
        patterns = [
            r'\bfor\s+members\b',
            r'\bmembers\s+only\b',
            r'\bonly\s+for\s+members\b',
            r'\bmembers\s+welcome\b',
            r'\bjoin.*\bmember\b.*\battend\b',
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def _is_past_tense_post(self, text: str) -> bool:
        """
        Return True if the post is a recap of a PAST event rather than a future
        announcement — e.g. "Thanks for coming — pizza was amazing!"

        Only fires on patterns that clearly indicate a past-event framing, so as not
        to reject posts that use incidental past-tense ("we've been hosting...").
        """
        past_patterns = [
            # Explicit thank-you for attending
            r'\b(?:thanks|thank\s+you)\s+(?:to\s+(?:all|everyone)\s+)?(?:who\s+)?(?:came|joined|attended|turned\s+up|showed\s+up|came\s+out)\b',
            # Positive recap phrasing
            r'\bwhat\s+a\s+(?:great|amazing|wonderful|brilliant|fantastic)\s+(?:night|evening|day|event|time)\b',
            r'\bhope\s+(?:everyone|you\s+all)\s+(?:had|enjoyed)\b',
            r'\bgreat\s+(?:to\s+see|seeing)\s+(?:everyone|you\s+all)\b',
            # Food described in past tense as having been consumed
            r'\b(?:food|pizza|snacks?|refreshments?|coffee|tea|cake|sandwiches?)\s+(?:were?|was)\s+(?:amazing|great|delicious|lovely|tasty|so\s+good|perfect|a\s+hit)\b',
            r'\bwe\s+(?:had|served|enjoyed)\s+(?:some\s+)?(?:amazing|great|delicious|lovely)?\s*(?:food|pizza|snacks?|refreshments?|coffee|tea|cake|sandwiches?)\b',
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in past_patterns)

    def _is_staff_only(self, text: str) -> bool:
        """
        Return True if the event is restricted to committee/exec/volunteers/staff
        only — i.e. NOT open to general students.

        Distinct from _is_members_only: 'members' = society members = open students;
        'committee/exec/volunteers' = closed internal group.

        Keeps false-positive risk low by requiring explicit "only" or activity-specific
        words alongside the committee/exec identifier.
        """
        patterns = [
            r'\b(?:committee|exec(?:utive)?)\s+(?:members?\s+)?only\b',
            r'\bfor\s+(?:committee|exec(?:utive)?)\s+members?\s+only\b',
            r'\bvolunteers?\s+only\b',
            r'\bstaff\s+only\b',
            r'\bboard\s+(?:of\s+(?:directors|trustees)\s+)?(?:meeting|only)\b',
            r'\bexec(?:utive)?\s+(?:meeting|training|session)\b',
            r'\bcommittee\s+training\b',
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

        _iftar_kw = ['iftar', 'iftaar', 'break the fast']
        if any(kw in clean_text for kw in _iftar_kw):
            return "Iftar/religious event"

        if self._is_past_tense_post(clean_text):
            return "Past-tense recap post (not an upcoming event)"

        if not self._has_explicit_food(clean_text):
            return "No explicit food keyword found"

        if self._is_food_activity(clean_text):
            return "Food activity workshop/competition (not free food)"

        if self._is_staff_only(clean_text):
            return "Staff/committee-only event (not open to students)"

        if self._is_other_college(clean_text):
            for college in self.other_colleges:
                if college in clean_text:
                    return f"Mentions other college: '{college}'"

        if self._is_off_campus(clean_text):
            for venue in self.off_campus_venues:
                if venue in clean_text:
                    return f"Mentions off-campus venue: '{venue}'"

        if self._is_online_event(clean_text) and not self._has_ucd_location(clean_text):
            return "Online/virtual event with no UCD location"

        if self._is_paid_event(clean_text):
            return "Appears to be a paid event (price/ticket mention)"

        if self._is_nightlife_event(clean_text):
            for keyword in self.nightlife_keywords:
                if keyword in clean_text:
                    return f"Nightlife event keyword: '{keyword}'"

        return "Accepted"

    def get_classification_details(self, text: str) -> dict:
        """Return result, reason, and matched keywords for admin display."""
        clean_text = self._preprocess_text(text)

        # Iftar
        _iftar_kw = ['iftar', 'iftaar', 'break the fast']
        for kw in _iftar_kw:
            if kw in clean_text:
                return {'result': 'rejected', 'reason': 'Iftar/religious event', 'matched_keywords': [kw]}

        # Past-tense
        if self._is_past_tense_post(clean_text):
            past_phrases = [
                'thanks for coming', 'thank you for coming', 'thanks for joining',
                'was a great', 'was amazing', 'was fantastic', 'was so great',
                'hope everyone had', 'hope you had', 'it was great', 'what a night',
            ]
            triggers = [p for p in past_phrases if p in clean_text]
            return {'result': 'rejected', 'reason': 'Past-tense recap post (not an upcoming event)', 'matched_keywords': triggers}

        # Collect food keywords present
        matched_strong = [kw for kw in self.strong_food_keywords if kw in clean_text]
        matched_weak   = [kw for kw in self.weak_food_keywords   if kw in clean_text]
        matched_ctx    = [m  for m  in self.context_modifiers     if m  in clean_text]
        if 'free' in clean_text and 'free' not in matched_ctx:
            matched_ctx.append('free')

        # No food keyword
        if not self._has_explicit_food(clean_text):
            return {'result': 'rejected', 'reason': 'No explicit food keyword found',
                    'matched_keywords': matched_weak}

        # Food activity
        if self._is_food_activity(clean_text):
            for kw in ['baking workshop', 'cooking class', 'cupcake decorating',
                       'food competition', 'bake-off', 'bake off', 'food fight']:
                if kw in clean_text:
                    return {'result': 'rejected', 'reason': 'Food activity workshop/competition (not free food)',
                            'matched_keywords': [kw]}
            return {'result': 'rejected', 'reason': 'Food activity workshop/competition (not free food)',
                    'matched_keywords': []}

        # Giveaway/contest
        if self._is_giveaway_contest(clean_text):
            return {'result': 'rejected', 'reason': 'Social media giveaway or contest', 'matched_keywords': []}

        # Staff only
        if self._is_staff_only(clean_text):
            staff_triggers = ['committee only', 'exec only', 'exec meeting', 'exec training',
                              'volunteers only', 'staff only', 'board meeting']
            triggers = [t for t in staff_triggers if t in clean_text]
            return {'result': 'rejected', 'reason': 'Staff/committee-only event (not open to students)',
                    'matched_keywords': triggers}

        # Other college
        if self._is_other_college(clean_text):
            for college in self.other_colleges:
                if college in clean_text:
                    return {'result': 'rejected', 'reason': f"Mentions other college: '{college}'",
                            'matched_keywords': [college]}

        # Off-campus
        if self._is_off_campus(clean_text):
            for venue in self.off_campus_venues:
                if venue in clean_text:
                    return {'result': 'rejected', 'reason': f"Mentions off-campus venue: '{venue}'",
                            'matched_keywords': [venue]}

        # Online with no UCD location
        if self._is_online_event(clean_text) and not self._has_ucd_location(clean_text):
            return {'result': 'rejected', 'reason': 'Online/virtual event with no UCD location',
                    'matched_keywords': []}

        # Paid
        if self._is_paid_event(clean_text):
            return {'result': 'rejected', 'reason': 'Appears to be a paid event (price/ticket mention)',
                    'matched_keywords': []}

        # Nightlife
        if self._is_nightlife_event(clean_text):
            for kw in self.nightlife_keywords:
                if kw in clean_text:
                    return {'result': 'rejected', 'reason': f"Nightlife event keyword: '{kw}'",
                            'matched_keywords': [kw]}

        # Accepted — surface all food signals found
        all_food = list(dict.fromkeys(matched_strong + matched_ctx + matched_weak))
        return {'result': 'accepted', 'reason': 'Accepted', 'matched_keywords': all_food[:8]}

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
        llm_hints = None
        if not self.classify_event(text):
            llm_hints = self._try_llm_fallback(text)
            if llm_hints is None:
                return None
            logger.info("ACCEPT: LLM fallback approved borderline post")

        # Extract event details
        local_post_ts = None
        if post_timestamp:
            if getattr(post_timestamp, 'tzinfo', None) is None:
                post_timestamp = pytz.utc.localize(post_timestamp)
            local_post_ts = post_timestamp.astimezone(self.timezone)
        time_range = self.time_parser.parse_time_range(text.lower(), post_timestamp=local_post_ts)
        time = time_range['start'] if time_range else None
        end_time_dict = time_range['end'] if time_range else None
        date = self.date_parser.parse_date(text.lower(), post_timestamp)
        location = self._extract_location(text)

        # Fill time gap with LLM hint if rule-based found nothing
        if time is None and llm_hints and llm_hints.get('time'):
            try:
                from datetime import time as dt_time
                h, m = map(int, llm_hints['time'].split(':'))
                time = dt_time(h, m)
                time_range = {'start': time, 'end': None}
            except Exception:
                pass

        # Fill location gap with LLM hint if rule-based found nothing
        if location is None and llm_hints and llm_hints.get('location'):
            loc_str = llm_hints['location']
            location = {'building': loc_str, 'room': None, 'full_location': loc_str}
            logger.debug(f"Location filled by LLM hint: {loc_str}")

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

        # Calculate confidence
        if llm_hints:
            confidence = 0.7 if (time and location) else 0.5
        else:
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
                'llm_assisted': llm_hints is not None,
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

        # Room regex: two alternatives:
        #   1. LETTER(S)-DIGITS: G-14, AD-101 (hyphenated prefix)
        #   2. Optional letter prefix + digits + optional .subdiv + optional suffix: E1.32, C204A, AD1.01
        ROOM_RE = r'[A-Za-z]{1,3}-\d+[A-Za-z]?|[A-Za-z]{0,3}\d+(?:[.]\d+)?[A-Za-z]?'

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
