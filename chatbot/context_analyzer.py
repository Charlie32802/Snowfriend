# context_analyzer.py - UNIVERSAL MESSAGE ELEMENT DETECTION - ENHANCED v2.1
# ✅ NEW: Formula-based complexity scoring (scales infinitely)
# ✅ NEW: Dynamic element registry (easier maintenance)
# ✅ NEW: Disclaimer tracking for hybrid approach
from pydoc import text
import re
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass

@dataclass
class ConversationContext:
    """Rich context model for tracking conversation state"""
    temporal_scope: str
    emotional_tone: str
    topic_type: str
    urgency_level: str
    disclosure_depth: int
    needs_validation: bool
    key_entities: List[str]
    implicit_requests: List[str]
    contradictions: List[str]
    user_corrections: int
    is_post_crisis: bool
    expressing_gratitude: bool
    conversation_depth: int
    is_family_drama: bool = False
    minimal_question_mode: bool = True
    message_elements: Dict[str, any] = None
    element_priorities: Dict[str, int] = None
    disclaimer_shown: bool = False

class ContextAnalyzer:
    """
    ADVANCED SEMANTIC CONTEXT ANALYZER with UNIVERSAL MESSAGE ELEMENT DETECTION
    ✅ v2.1: Enhanced with formula-based complexity scoring and dynamic element registry
    """

    # ========================================================================
    # ✅ NEW: ELEMENT REGISTRY - Add new elements here for easy maintenance
    # ========================================================================
    
    ELEMENT_LABELS = {
        'has_gratitude': 'Gratitude',
        'has_goodbye': 'Goodbye',
        'has_name_change': 'Name change',
        'has_question': 'Question',
        'has_problem': 'Problem',
        'has_emotion': 'Emotion',
        'has_future_plans': 'Future plans',
        'has_playfulness': 'Playfulness',
        'has_request': 'Request',
        'has_time_reference': 'Time reference',
    }

    def __init__(self):
        self.conversation_memory = []
        self.user_profile = {
            'mentioned_people': set(),
            'recurring_topics': {},
            'correction_count': 0,
            'preferred_response_style': 'exploratory',
            'recent_crisis': False,
            'crisis_recovery_turns': 0,
            'name_usage_count': 0,
            'last_name_usage_turn': -999,
            'user_names': [],
            'disclaimer_shown': False,
        }
    
        self.verb_blacklist = {
            'trying', 'working', 'going', 'doing', 'feeling', 'thinking', 
            'being', 'getting', 'making', 'having', 'taking', 'coming',
            'looking', 'wanting', 'needing', 'hoping', 'planning', 'starting',
            'leaving', 'staying', 'moving', 'running', 'walking', 'talking',
            'living', 'dying', 'sleeping', 'eating', 'drinking', 'cooking',
            'studying', 'reading', 'writing', 'learning', 'teaching', 'playing',
            'watching', 'listening', 'waiting', 'wondering', 'worrying', 'caring',
            'loving', 'hating', 'liking', 'enjoying', 'suffering', 'struggling',
            'fighting', 'winning', 'losing', 'failing', 'succeeding', 'helping',
            'hurting', 'healing', 'growing', 'changing', 'improving', 'worsening',
            'fine', 'good', 'okay', 'ok', 'alright', 'bad', 'sad', 'happy',
            'angry', 'scared', 'worried', 'nervous', 'excited', 'tired', 'exhausted',
            'sick', 'ill', 'better', 'worse', 'great', 'terrible', 'awful',
            'amazing', 'wonderful', 'horrible', 'beautiful', 'ugly', 'pretty',
            'alone', 'single', 'free', 'busy', 'ready', 'done', 'finished',
            'confused', 'lost', 'stuck', 'trapped', 'scared', 'afraid',
            'crying', 'laughing', 'smiling', 'frowning', 'yelling', 'screaming',
            'was', 'were', 'been', 'had', 'did', 'made', 'went', 'came',
            'will', 'would', 'could', 'should', 'might', 'may', 'can',
            'anxious', 'depressed', 'stressed', 'overwhelmed', 'frustrated',
            'disappointed', 'hopeless', 'helpless', 'devastated', 'broken',
            'hurt', 'upset', 'annoyed', 'irritated', 'furious', 'enraged',
            'terrified', 'frightened', 'panicked', 'paranoid', 'guilty',
            'ashamed', 'embarrassed', 'humiliated', 'jealous', 'envious',
            'lonely', 'isolated', 'abandoned', 'rejected', 'worthless',
            'miserable', 'pathetic', 'useless', 'weak', 'strong', 'brave',
            'confident', 'proud', 'grateful', 'thankful', 'blessed', 'lucky',
            'curious', 'interested', 'bored', 'indifferent', 'numb', 'empty',
            'drained', 'burnt', 'motivated', 'determined', 'focused', 'distracted',
            'comfortable', 'uncomfortable', 'uneasy', 'tense', 'relaxed', 'calm',
            'peaceful', 'content', 'satisfied', 'pleased', 'delighted', 'thrilled',
            'ecstatic', 'euphoric', 'joyful', 'cheerful', 'optimistic', 'pessimistic',
            'hopeful', 'doubtful', 'uncertain', 'sure', 'positive', 'negative',
            'eager', 'reluctant', 'willing', 'unwilling', 'patient', 'impatient',
            'tolerant', 'intolerant', 'understanding', 'judgmental', 'supportive',
            'critical', 'encouraging', 'discouraging', 'inspiring', 'demotivating',
            'actually', 'basically', 'really', 'truly', 'honestly', 'literally',
            'seriously', 'totally', 'completely', 'absolutely', 'definitely',
            'probably', 'possibly', 'maybe', 'perhaps', 'surely', 'certainly',
            'obviously', 'clearly', 'apparently', 'supposedly', 'allegedly',
            'generally', 'usually', 'normally', 'typically', 'commonly',
            'recently', 'currently', 'presently', 'eventually', 'finally',
        }

    # ========================================================================
    # QUESTION TYPE DETECTION
    # ========================================================================

    def detect_question_type(self, text: str, conversation_history: List[Dict] = None) -> str:
        """
        Detect if user is:
        - OFFERING to share information ("You want to know what I'm doing?")
        - ASKING a question ("What are you doing?")
        - DEFLECTING ("What about you?")
        
        Returns: 'offer', 'question', 'deflection', 'other'
        """
        text_lower = text.lower().strip()
        
        offer_patterns = [
            r'^you want to know',
            r'^want to know what',
            r'^should i tell you',
            r'^do you want to (hear|know)',
            r'^interested in (what|how|why)',
            r'^wanna know what',
            r'^you wanna hear',
            r'^curious (about|what)',
        ]
        
        if any(re.match(pattern, text_lower) for pattern in offer_patterns):
            return 'offer'
        
        deflect_patterns = [
            r'what about you',
            r'how about you',
            r'and you\?',
            r'what about (yourself|snowfriend)',
            r'how about (yourself|snowfriend)',
        ]
        
        if any(re.search(pattern, text_lower) for pattern in deflect_patterns):
            return 'deflection'
        
        question_patterns = [
            r'^what are you',
            r'^how are you',
            r'^are you',
            r'^do you',
            r'^can you',
            r'^have you',
        ]
        
        if any(re.match(pattern, text_lower) for pattern in question_patterns):
            return 'question'
        
        return 'other'

    # ========================================================================
    # ✅ ENHANCED: UNIVERSAL MESSAGE ELEMENT DETECTION v2.1
    # ========================================================================

    def extract_message_elements(self, text: str, conversation_history: List[Dict] = None) -> Dict[str, any]:
        """
        ✅ v2.1 ENHANCED: Universal element extraction with formula-based complexity
        
        Returns dict with detected elements:
        {
            'has_gratitude': bool,
            'has_goodbye': bool,
            'has_name_change': bool,
            'new_name': str or None,
            'has_question': bool,
            'questions': List[str],
            'has_problem': bool,
            'has_emotion': bool,
            'has_future_plans': bool,
            'has_playfulness': bool,
            'has_request': bool,
            'requests': List[str],
            'element_count': int,
            'complexity_score': int  # ✅ Now formula-based (scales infinitely)
        }
        """
        text_lower = text.lower()
        elements = {}
        
        # 1. GRATITUDE DETECTION
        gratitude_patterns = [
            r'\b(thank|thanks|appreciate|grateful|gratitude)',
            r'\bthank you',
            r'\bthanks (a lot|so much|very much|for)',
            r'\bi appreciate',
        ]
        elements['has_gratitude'] = any(re.search(p, text_lower) for p in gratitude_patterns)
        
        # 2. GOODBYE DETECTION
        goodbye_patterns = [
            r'\b(good ?night|goodnight|gnight|nite|bye|goodbye|see you|later|ttyl|cya|peace out)',
            r'\b(going to|gonna|heading to) (sleep|bed)',
            r'\bi\'?m (out|off|done)',
            r'\btalk (to you |to ya )?(later|soon|tomorrow)',
            r'\b(sleep well|sweet dreams|rest well)',
        ]
        elements['has_goodbye'] = any(re.search(p, text_lower) for p in goodbye_patterns)
        
        # 3. SMART NAME CHANGE DETECTION
        name_change_patterns = [
            r'call me ["\']?(\w+)["\']?',
            r'my name is ["\']?(\w+)["\']?',
            r'you can call me ["\']?(\w+)["\']?',
            r'refer to me as ["\']?(\w+)["\']?',
            r'use ["\']?(\w+)["\']? instead',
            # More cautious pattern for "I'm [name]"
            r'i\'?m\s+([A-Z][a-zA-Z]+)(?:,|\s|$|\.)'
        ]
        
        elements['has_name_change'] = False
        elements['new_name'] = None
        
        for pattern in name_change_patterns:
            # ✅ FIX: Check if pattern requires capitalization
            if pattern == r'i\'?m\s+([A-Z][a-zA-Z]+)(?:,|\s|$|\.)':
                requires_capitalization = True
            else:
                requires_capitalization = False
            
            # Search in original text if pattern checks capitalization
            search_text = text if requires_capitalization else text.lower()
            match = re.search(pattern, search_text, re.IGNORECASE)
            
            if match:
                potential_name = match.group(1)
                
                # ✅ CRITICAL CHECK: Filter out verbs and common words
                if potential_name.lower() not in self.verb_blacklist:
                    # For patterns that don't require capitalization, verify in original
                    if not requires_capitalization:
                        # Find in original text to check capitalization
                        original_match = re.search(pattern, text, re.IGNORECASE)
                        if original_match:
                            actual_word = original_match.group(1)
                            # Accept if capitalized OR explicitly after markers
                            if (actual_word[0].isupper() or 
                                'call me' in text.lower() or 
                                'my name is' in text.lower() or
                                'you can call me' in text.lower()):
                                elements['has_name_change'] = True
                                elements['new_name'] = actual_word.capitalize()
                                self.user_profile['user_names'].append(elements['new_name'])
                                break
                    else:
                        # Pattern already checks capitalization, trust it
                        elements['has_name_change'] = True
                        elements['new_name'] = potential_name.capitalize()
                        self.user_profile['user_names'].append(elements['new_name'])
                        break
        
        # 4. QUESTION DETECTION
        question_indicators = [
            r'^\s*(what|why|how|when|where|who|can you|could you|would you)',
            r'\?',
            r'\b(tell me|explain|help me understand)',
        ]
        elements['has_question'] = any(re.search(p, text_lower) for p in question_indicators)
        
        elements['questions'] = []
        sentences = re.split(r'[.!]\s+', text)
        for sentence in sentences:
            if '?' in sentence or re.search(r'^\s*(what|why|how|when|where|who)', sentence.lower()):
                elements['questions'].append(sentence.strip())
        
        # 5. PROBLEM/ISSUE DETECTION
        problem_patterns = [
            r'\b(problem|issue|trouble|difficult|hard|struggle|can\'?t|cannot)',
            r'\b(wrong|bad|awful|terrible|hate|dislike)',
            r'\b(not (good|ok|okay|fine|working))',
        ]
        elements['has_problem'] = any(re.search(p, text_lower) for p in problem_patterns)
        
        # 6. EMOTION DETECTION
        emotion_patterns = [
            r'\b(feel|feeling|felt|emotion)',
            r'\b(sad|happy|angry|scared|anxious|worried|excited|frustrated|lonely|depressed)',
        ]
        elements['has_emotion'] = any(re.search(p, text_lower) for p in emotion_patterns)
        
        # 7. FUTURE PLANS DETECTION
        future_patterns = [
            r'\b(will|going to|gonna|planning to)',
            r'\b(tomorrow|later|soon|next (week|month|time))',
            r'\b(when i|after i|once i)',
        ]
        elements['has_future_plans'] = any(re.search(p, text_lower) for p in future_patterns)
        
        # 8. PLAYFULNESS DETECTION
        playful_patterns = [
            r'\b(lol|haha|lmao|hehe|lmfao)',
            r'\b(just kidding|jk|kidding)',
            r'😂|😅|🤣',
        ]
        elements['has_playfulness'] = any(re.search(p, text_lower) for p in playful_patterns)
        
        # 9. REQUEST DETECTION
        request_patterns = [
            r'\b(can you|could you|would you|will you|please)',
            r'\b(help me|show me|tell me|give me)',
            r'\b(i need|i want|i\'d like)',
        ]
        elements['has_request'] = any(re.search(p, text_lower) for p in request_patterns)
        
        elements['requests'] = []
        for pattern in request_patterns:
            matches = re.finditer(pattern + r'.{0,50}[.?!]', text_lower)
            for match in matches:
                elements['requests'].append(match.group(0).strip())
        
        # 10. TIME REFERENCE DETECTION
        time_patterns = [
            r'\b(now|today|tonight|this (morning|afternoon|evening))',
            r'\b(yesterday|last (night|week|month))',
            r'\b(in a (minute|moment|bit|sec))',
        ]
        elements['has_time_reference'] = any(re.search(p, text_lower) for p in time_patterns)
        
        # ====================================================================
        # ✅ NEW: DYNAMIC ELEMENT COUNT using registry
        # ====================================================================
        
        element_count = sum(1 for key in self.ELEMENT_LABELS.keys() if elements.get(key, False))
        elements['element_count'] = element_count
        
        # ====================================================================
        # ✅ NEW: FORMULA-BASED COMPLEXITY SCORING (scales infinitely)
        # ====================================================================
        
        # Formula: complexity = min(10, element_count * 2)
        # This ensures: 1 element=2, 2=4, 3=6, 4=8, 5=10, 6+=10 (capped)
        elements['complexity_score'] = min(10, element_count * 2)
        
        return elements

    def calculate_element_priorities(self, elements: Dict[str, any], context: 'ConversationContext') -> Dict[str, int]:
        """
        UNIVERSAL priority calculation - determines what MUST be addressed
        
        Priority levels:
        1 = MUST address (critical)
        2 = SHOULD address (important)
        3 = CAN address (optional)
        
        Returns: {'element_name': priority_level}
        """
        priorities = {}
        
        # CRITICAL (Priority 1)
        if elements.get('has_name_change'):
            priorities['name_change'] = 1
        
        if elements.get('has_gratitude'):
            priorities['gratitude'] = 1
        
        if context.emotional_tone == 'crisis':
            priorities['crisis'] = 1
        
        # IMPORTANT (Priority 2)
        if elements.get('has_goodbye'):
            priorities['goodbye'] = 2
        
        if elements.get('has_question'):
            priorities['question'] = 2
        
        if elements.get('has_emotion') and context.disclosure_depth >= 3:
            priorities['emotion'] = 2
        
        if elements.get('has_request'):
            priorities['request'] = 2
        
        # OPTIONAL (Priority 3)
        if elements.get('has_problem'):
            priorities['problem'] = 3
        
        if elements.get('has_future_plans'):
            priorities['future_plans'] = 3
        
        if elements.get('has_playfulness'):
            priorities['playfulness'] = 3
        
        return priorities

    # ========================================================================
    # EXISTING METHODS (ALL PRESERVED)
    # ========================================================================

    def analyze_temporal_scope(self, text: str) -> str:
        """Detect timeframe: ongoing pattern, single event, past, future, hypothetical"""
        text_lower = text.lower()

        ongoing_indicators = [
            r'\b(always|constantly|every (day|time|week)|keeps|never stops?|all the time)',
            r'\b(keeps? \w+ing|won\'?t stop|continues to|ongoing)',
            r'\b(habitually|repeatedly|continuously|persistently)',
        ]

        single_event_indicators = [
            r'\b(today|yesterday|this morning|tonight|just now|earlier)',
            r'\b(happened|occurred|took place) (today|yesterday|just)',
            r'\b(one time|once|this time|that time)',
        ]

        past_indicators = [
            r'\b(used to|back then|in the past|before|previously|last (year|month))',
            r'\b(was|were|had been) \w+ing',
            r'\b(no longer|not anymore|stopped)',
        ]

        future_indicators = [
            r'\b(will|going to|planning to|next (week|month|year))',
            r'\b(tomorrow|soon|later|upcoming|in the future)',
        ]

        hypothetical_indicators = [
            r'\b(what if|suppose|imagine|wonder if|thinking about)',
            r'\b(could|might|would|should) \w+ if',
        ]

        if any(re.search(pattern, text_lower) for pattern in ongoing_indicators):
            return 'ongoing'
        elif any(re.search(pattern, text_lower) for pattern in single_event_indicators):
            return 'single_event'
        elif any(re.search(pattern, text_lower) for pattern in past_indicators):
            return 'past'
        elif any(re.search(pattern, text_lower) for pattern in future_indicators):
            return 'future'
        elif any(re.search(pattern, text_lower) for pattern in hypothetical_indicators):
            return 'hypothetical'
        else:
            return 'single_event'

    def analyze_emotional_tone(self, text: str, conversation_history: List[Dict]) -> str:
        """Detect emotional state with nuance"""
        text_lower = text.lower()

        if self.user_profile.get('recent_crisis', False):
            stabilization_patterns = [
                r'\b(will|going to|thank|appreciate|better|calmer|okay)',
                r'\b(i\'ll (call|try|reach out))',
            ]

            if any(re.search(p, text_lower) for p in stabilization_patterns):
                return 'post_crisis'

        crisis_patterns = [
            r'\b(want to die|suicide|kill myself|end it all|no reason to live)',
            r'\b(can\'?t take it anymore|better off dead|no way out)',
    ]

    # ✅ NEW: Anxiety-specific patterns (check BEFORE negative patterns)
        anxiety_patterns = [
            r'\b(anxious|anxiety|nervous|worried about|stress|stressed|overwhelm)',
            r'\b(afraid|scared|terrified|panic|panicking)',
            r'\bdon\'?t know what to expect',
            r'\bnot sure (what|how|if)',
            r'\bworried that',
        ]

        anxiety_count = sum(1 for p in anxiety_patterns if re.search(p, text_lower))

        if anxiety_count > 0:
        # Check if it's severe anxiety (multiple indicators or severe words)
            if anxiety_count >= 2 or any(word in text_lower for word in ['terrified', 'panic', 'panicking']):
                return 'crisis'  # Severe anxiety → crisis handling
            else:
                return 'anxiety'  # Moderate anxiety → special anxiety handling

        negative_patterns = [
            r'\b(sad|depressed|upset|angry|frustrated|scared|worried)',
            r'\b(hate|terrible|awful|horrible|bad|worst|crying|hurt)',
            r'\b(not (good|ok|okay|fine)|feeling (bad|down|low))',
        ]

        positive_patterns = [
            r'\b(happy|excited|glad|great|good|better|wonderful|amazing)',
            r'\b(relieved|proud|accomplished|love|enjoy)',
        ]

        mixed_patterns = [
            r'\bbut\b',
            r'\balthough\b',
            r'\bhowever\b',
        ]

        crisis_count = sum(1 for p in crisis_patterns if re.search(p, text_lower))
        negative_count = sum(1 for p in negative_patterns if re.search(p, text_lower))
        positive_count = sum(1 for p in positive_patterns if re.search(p, text_lower))
        mixed_count = sum(1 for p in mixed_patterns if re.search(p, text_lower))

        if crisis_count > 0:
            self.user_profile['recent_crisis'] = True
            self.user_profile['crisis_recovery_turns'] = 0
            return 'crisis'
        elif mixed_count > 0 and (positive_count > 0 and negative_count > 0):
            return 'mixed'
        elif negative_count > positive_count:
            return 'negative'
        elif positive_count > negative_count:
            return 'positive'
        else:
            return 'neutral'

    def _is_declining_phrase(self, text: str) -> bool:
        """Detect if user is DECLINING vs EXPRESSING GRATITUDE"""
        text_lower = text.lower().strip()

        declining_patterns = [
            r'^\s*no,?\s+thank',
            r'^\s*nah,?\s+thank',
            r'^\s*nope,?\s+thank',
            r'^\s*no\s+thanks?\b',
            r'^\s*(i\'m|im)\s+(good|ok|okay|fine|alright),?\s+thank',
            r'^\s*not?\s+(right now|now|currently|yet),?\s+thank',
        ]

        return any(re.match(pattern, text_lower) for pattern in declining_patterns)

    def _is_literal_interpretation_humor(self, text: str, last_bot_message: str) -> bool:
        """Detect literal/humorous interpretation of bot's question"""
        if not last_bot_message:
            return False

        text_lower = text.lower().strip()
        last_bot_lower = last_bot_message.lower()

        bot_keywords = []
        if "what's up" in last_bot_lower or "whats up" in last_bot_lower:
            bot_keywords.append("up")
        if "what's going on" in last_bot_lower or "whats going on" in last_bot_lower:
            bot_keywords.append("going on")
        if "how are you" in last_bot_lower or "how're you" in last_bot_lower:
            bot_keywords.append("are you")
        if "what's happening" in last_bot_lower or "whats happening" in last_bot_lower:
            bot_keywords.append("happening")

        literal_humor_indicators = [
            r'\bis when\b',
            r'\bmeans\b',
            r'\b(is|are) (a|an|the)\b',
            r'\b(ceiling|sky|roof|stars|clouds)\b',
            r'\b(nothing|not much|nm|nmu)\b',
            r'\b(existing|surviving|vibing|chillin|alive)\b',
        ]

        if any(re.search(pattern, text_lower) for pattern in literal_humor_indicators):
            return True

        word_count = len(text_lower.split())
        if word_count <= 15:
            for keyword in bot_keywords:
                if keyword in text_lower:
                    return True

        return False

    def _is_playful_minimal_response(self, text: str, last_bot_message: str) -> bool:
        """Detect playful minimal responses"""
        text_lower = text.lower().strip()

        playful_minimal = [
            r'^\s*(nothing much|not much|nm|nmu|nuthin|nothin)\s*$',
            r'^\s*(just (vibing|chilling|existing|surviving|here))\s*$',
            r'^\s*(same old|the usual)\s*$',
            r'^\s*(alive|existing|surviving)\s*$',
            r'^\s*(you know|meh|eh)\s*$',
        ]

        return any(re.match(pattern, text_lower) for pattern in playful_minimal)

    def analyze_topic_type(self, text: str, conversation_depth: int = 0, last_bot_message: str = None) -> str:
        """Identify what user is talking about"""
        text_lower = text.lower().strip()

        if self._is_declining_phrase(text):
            return 'general'

        question_indicators = [
            r'^\s*(what|why|how|when|where|who|can you)',
            r'\b(recommend|suggest|any good|any ideas|what should|which)\b',
        ]

        if any(re.search(p, text_lower) for p in question_indicators):
            return 'question'

        if last_bot_message:
            if self._is_literal_interpretation_humor(text, last_bot_message):
                return 'playful_banter'
            if self._is_playful_minimal_response(text, last_bot_message):
                return 'playful_banter'

        playful_patterns = [
            r'\b(lol|haha|lmao|hehe|lmfao)\b',
            r'\b(just kidding|jk|kidding)\b',
            r'(😂|😅|🤣)',
            r'\b(well well|look what|look who)\b',
            r'\bif it isn\'?t\b',
            r'\bwhat do we have here\b',
            r'\bfancy (seeing|meeting)\b',
        ]

        if any(re.search(p, text_lower) for p in playful_patterns):
            return 'playful_banter'

        if conversation_depth <= 2 and len(text_lower.split()) <= 4 and any(g in text_lower for g in ['hi', 'hello', 'hey', 'hola', 'sup']):
            return 'greeting'

        gratitude_indicators = [
            r'\b(thank|thanks|appreciate|grateful|gratitude)',
            r'\bthank you',
            r'\bthanks (a lot|so much|very much)',
            r'\bi appreciate',
            r'\bgrateful for',
        ]

        if any(re.search(p, text_lower) for p in gratitude_indicators):
            return 'gratitude'

        problem_indicators = [
            r'\b(problem|issue|trouble|difficult|hard|struggle|can\'?t)',
        ]

        feeling_indicators = [
            r'\b(feel|feeling|felt|emotion)',
            r'\b(sad|happy|angry|scared|anxious) (and|but|because)',
        ]

        relationship_indicators = [
            r'\b(friend|family|parent|mom|dad|partner|boyfriend|girlfriend|classmate)',
            r'\b(relationship|argument|fight|broke up)',
        ]

        achievement_indicators = [
            r'\b(achieved|accomplished|succeed|won|got|finished|completed)',
        ]

        if any(re.search(p, text_lower) for p in achievement_indicators):
            return 'achievement'
        elif any(re.search(p, text_lower) for p in relationship_indicators):
            return 'relationship'
        elif any(re.search(p, text_lower) for p in feeling_indicators):
            return 'feeling'
        elif any(re.search(p, text_lower) for p in problem_indicators):
            return 'problem'
        else:
            return 'general'

    def analyze_urgency(self, emotional_tone: str, text: str) -> str:
        """Determine how urgent the response needs to be"""
        if emotional_tone == 'crisis':
            return 'crisis'

        if emotional_tone == 'post_crisis':
            return 'low'

        text_lower = text.lower()

        high_urgency_patterns = [
            r'\b(emergency|urgent|right now|immediately|help me)',
            r'\b(panic|freaking out|can\'?t breathe|spiraling)',
        ]

        medium_urgency_patterns = [
            r'\b(today|this morning|just happened|just now)',
            r'\b(really need|desperate|overwhelmed)',
        ]

        if any(re.search(p, text_lower) for p in high_urgency_patterns):
            return 'high'
        elif any(re.search(p, text_lower) for p in medium_urgency_patterns):
            return 'medium'
        else:
            return 'low'

    def analyze_disclosure_depth(self, text: str) -> int:
        """Rate how vulnerable/personal the disclosure is (1-5 scale)"""
        text_lower = text.lower()

        level_5_indicators = [
            r'\b(abuse|trauma|suicide|rape|assault|self-harm)',
            r'\b(no one (knows|understands)|secret|ashamed)',
        ]

        level_4_indicators = [
            r'\b(depressed|depression|deeply depressed|severely depressed)\b',
            r'\b(hopeless|no hope|giving up|gave up)\b',
            r'\b(terrified|petrified|paralyzed with fear)\b',
            r'\b(anxious (all the time|constantly|every day))\b',
            r'\b(panic attack|anxiety attack|breakdown)\b',
        ]

        level_3_indicators = [
            # Situational fear/anxiety (normal responses to life events)
            r'\b(scared|nervous|anxious|worried) (about|for|of).{0,30}(exam|test|interview|presentation|OJT|internship|job|school|class|assignment|project|deadline)\b',
            r'\b(stressed|overwhelmed|pressured).{0,30}(about|by|from).{0,30}(school|work|exam|deadline|assignment)\b',
        
            # Interpersonal conflicts (normal relationship issues)
            r'\b(argument|fight|disagreement|conflict).{0,30}(with|about)\b',
            r'\b(upset|frustrated|annoyed|bothered).{0,30}(with|by|about)\b',
        
            # Future-oriented worry (normal anticipatory anxiety)
            r'\b(worried about|concerned about|nervous about).{0,30}(next|upcoming|tomorrow|future)\b',
            r'\b(don\'?t know (what|how|if)).{0,30}(will|going to|next|future)\b',
        ]

        level_2_indicators = [
            r'\b(annoyed|tired|stressed|busy)',
        ]

        if any(re.search(p, text_lower) for p in level_5_indicators):
            return 5
        elif any(re.search(p, text_lower) for p in level_4_indicators):
            return 4
        elif any(re.search(p, text_lower) for p in level_3_indicators):
            return 3
        elif any(re.search(p, text_lower) for p in level_2_indicators):
            return 2
        else:
            return 1
        
    def detect_identity_question(self, text: str) -> Dict[str, bool]:
        """
        ✅ UNIVERSAL: Detect when user is asking about their own identity
    
        Returns:
            {
                'is_identity_question': bool,
                'asking_about_email': bool,
                'asking_who_they_are': bool,
                'asking_if_known': bool
            }
        """
        text_lower = text.lower()
    
    # "Who am I?" / "Don't you know who I am?"
        who_am_i_patterns = [
            r'\b(who am i|who i am)\b',
            r'\bdon\'?t you know who i am\b',
            r'\bdo you know who i am\b',
            r'\bknow who i am\b',
            r'\bdo you remember me\b',
            r'\bremember who i am\b',
        ]
    
    # "Do you know my email?"
        email_patterns = [
            r'\b(do you know|don\'?t you know|know).{0,20}(my )?(email|e-?mail)\b',
            r'\bmy email (address|is)\b',
            r'\bwhat\'?s my email\b',
            r'\bknow my (email|e-?mail)\b',
        ]   
    
    # General "do you know me?"
        know_me_patterns = [
            r'\bdo you know me\b',
            r'\bdon\'?t you know me\b',
            r'\bknow (anything about|who) me\b',
            r'\bremember (anything about|who) me\b',
        ]
    
        asking_who_they_are = any(re.search(p, text_lower) for p in who_am_i_patterns)
        asking_about_email = any(re.search(p, text_lower) for p in email_patterns)
        asking_if_known = any(re.search(p, text_lower) for p in know_me_patterns)
    
        is_identity_question = asking_who_they_are or asking_about_email or asking_if_known
    
        return {
            'is_identity_question': is_identity_question,
            'asking_about_email': asking_about_email,
            'asking_who_they_are': asking_who_they_are,
            'asking_if_known': asking_if_known,
        }

    def analyze_needs_validation(self, emotional_tone: str, topic_type: str) -> bool:
        """Determine if user needs validation vs. exploration"""
        if emotional_tone in ['negative', 'crisis']:
            return True

        if topic_type == 'achievement':
            return True

        if topic_type == 'gratitude':
            return True

        return False

    def extract_key_entities(self, text: str) -> List[str]:
        """Extract people, places, events mentioned"""
        entities = []
        text_lower = text.lower()

        people_patterns = [
            r'\bmy (mom|dad|mother|father|parent|friend|partner|boyfriend|girlfriend|classmate|teacher)',
            r'\b(he|she|they) (said|did|told|made)',
        ]

        for pattern in people_patterns:
            matches = re.findall(pattern, text_lower)
            entities.extend(matches)

        place_patterns = [
            r'\bat (school|work|home|office|class)',
        ]

        for pattern in place_patterns:
            matches = re.findall(pattern, text_lower)
            entities.extend(matches)

        return entities

    def detect_implicit_requests(self, text: str, emotional_tone: str, topic_type: str, conversation_history: List[Dict] = None) -> List[str]:
        """Understand what user wants without saying it directly"""
        requests = []
        text_lower = text.lower()

        if conversation_history and topic_type == 'question':
            last_bot_msg = None
            for msg in reversed(conversation_history):
                if msg['role'] == 'assistant':
                    last_bot_msg = msg['content'].lower()
                    break

            if last_bot_msg and 'crisis hotline' in last_bot_msg:
                resource_question_patterns = [
                    r'\bhow (does|will|can) (that|this|it|they).{0,20}help',
                    r'\bwhy (should|would) i (call|reach out|contact)',
                    r'\bwhat (can|will|do) they (do|say)',
                    r'\bwhat.?s (that|this).{0,20}(got to do|do|have to do).{0,20}with me',
                    r'\bhow.{0,10}(is|does) that.{0,10}(help|relevant|related)',
                ]

                if any(re.search(p, text_lower) for p in resource_question_patterns):
                    requests.append('crisis_resource_question')

        if conversation_history and topic_type == 'question':
            last_bot_msg = None
            for msg in reversed(conversation_history):
                if msg['role'] == 'assistant':
                    last_bot_msg = msg['content'].lower()
                    break

            if last_bot_msg and ('crisis hotline' in last_bot_msg or 'extremely concerned' in last_bot_msg):
                clarification_patterns = [
                    r'\b(what|why).{0,20}(concern|worry)',
                    r'\bjust (a|an)\b',
                    r'\bwhat are you.{0,20}(concern|worry|talking about)',
                ]

                if any(re.search(p, text_lower) for p in clarification_patterns):
                    requests.append('crisis_clarification')

        if emotional_tone in ['negative', 'crisis']:
            requests.append('empathy')

        if topic_type == 'gratitude':
            requests.append('acknowledge_gratitude')

        if emotional_tone == 'post_crisis':
            requests.append('gentle_encouragement')

        if topic_type == 'playful_banter':
            requests.append('match_playful_energy')

        if any(word in text_lower for word in ['nobody listens', 'no one understands', 'alone']):
            requests.append('validation_of_experience')

        if any(word in text_lower for word in ['what should i', 'help me', 'don\'t know what to do']):
            requests.append('guidance')

        if len(text_lower.split()) > 30 and '?' not in text:
            requests.append('space_to_talk')

        return requests

    def analyze_conversation_depth(self, conversation_history: List[Dict]) -> int:
        """Track how many exchanges have happened"""
        if not conversation_history:
            return 0

        user_messages = [msg for msg in conversation_history if msg['role'] == 'user']
        return len(user_messages)

    def should_offer_guidance(self, conversation_history: List[Dict], context: 'ConversationContext') -> bool:
        """Determine if bot should offer guidance instead of just exploring"""
        depth = self.analyze_conversation_depth(conversation_history)

        if depth >= 3 and context.disclosure_depth >= 3:
            return True

        last_msg = conversation_history[-1]['content'].lower() if conversation_history else ""
        if any(phrase in last_msg for phrase in ['help me', 'what should i', 'how do i', 'what can i do']):
            return True

        return False

    def analyze_message(self, text: str, conversation_history: List[Dict]) -> ConversationContext:
        """COMPREHENSIVE CONTEXT ANALYSIS with UNIVERSAL MESSAGE ELEMENTS"""
        conversation_depth = self.analyze_conversation_depth(conversation_history)

        last_bot_message = None
        if conversation_history:
            for msg in reversed(conversation_history):
                if msg['role'] == 'assistant':
                    last_bot_message = msg['content']
                    break

        temporal_scope = self.analyze_temporal_scope(text)
        emotional_tone = self.analyze_emotional_tone(text, conversation_history)
        topic_type = self.analyze_topic_type(text, conversation_depth, last_bot_message)
        urgency_level = self.analyze_urgency(emotional_tone, text)
        disclosure_depth = self.analyze_disclosure_depth(text)
        needs_validation = self.analyze_needs_validation(emotional_tone, topic_type)
        key_entities = self.extract_key_entities(text)
        implicit_requests = self.detect_implicit_requests(text, emotional_tone, topic_type, conversation_history)

    # ✅ NEW: Identity question detection
        identity_info = self.detect_identity_question(text)
        if identity_info['is_identity_question']:
            implicit_requests.append('identity_verification')
            if identity_info['asking_about_email']:
                implicit_requests.append('asking_about_email')
            if identity_info['asking_who_they_are']:
                implicit_requests.append('asking_who_they_are')

        question_type = self.detect_question_type(text, conversation_history)
    
        if question_type == 'offer':
            implicit_requests.append('user_offering_to_share')
        elif question_type == 'deflection':
            implicit_requests.append('user_deflecting')

        is_post_crisis = emotional_tone == 'post_crisis'
        if is_post_crisis:
            self.user_profile['crisis_recovery_turns'] += 1
            if self.user_profile['crisis_recovery_turns'] >= 3:
                self.user_profile['recent_crisis'] = False

        expressing_gratitude = topic_type == 'gratitude'

        user_corrections = sum(
            1 for msg in conversation_history
            if msg['role'] == 'user' and any(
                phrase in msg['content'].lower()
                for phrase in ["didn't i", "i just said", "i already told", "you're not listening"]
            )
        )

        contradictions = self._detect_contradictions(conversation_history)

        family_drama_indicators = [
            r'\b(mom|mother|dad|father|parent|sibling|brother|sister|family)\b',
            r'\b(clean|tidy|organize).{0,20}(room|house|apartment|space)\b',
            r'\b(grounded|punished|in trouble|mad at|angry with|upset with)\b',
            r'\b(if i don\'t|unless i|or else|otherwise).{0,20}(clean|do|finish)\b',
            r'\b(typical|normal|usual).{0,20}(parent|family|mom|dad)\b',
        ]
        is_family_drama = any(re.search(pattern, text.lower()) for pattern in family_drama_indicators)

        minimal_question_mode = not (is_family_drama or disclosure_depth >= 4)

        message_elements = self.extract_message_elements(text, conversation_history)
    
        initial_context = ConversationContext(
            temporal_scope=temporal_scope,
            emotional_tone=emotional_tone,
            topic_type=topic_type,
            urgency_level=urgency_level,
            disclosure_depth=disclosure_depth,
            needs_validation=needs_validation,
            key_entities=key_entities,
            implicit_requests=implicit_requests,
            contradictions=contradictions,
            user_corrections=user_corrections,
            is_post_crisis=is_post_crisis,
            expressing_gratitude=expressing_gratitude,
            conversation_depth=conversation_depth,
            is_family_drama=is_family_drama,
            minimal_question_mode=minimal_question_mode,
            message_elements=message_elements,
            element_priorities={},
            disclaimer_shown=self.user_profile.get('disclaimer_shown', False)
        )
    
        element_priorities = self.calculate_element_priorities(message_elements, initial_context)
        initial_context.element_priorities = element_priorities

        should_guide = self.should_offer_guidance(conversation_history, initial_context)

        if should_guide:
            implicit_requests.append('guidance_needed')

        return initial_context

    def _detect_contradictions(self, conversation_history: List[Dict]) -> List[str]:
        """Find contradictory information in conversation"""
        contradictions = []

        user_messages = [msg['content'].lower() for msg in conversation_history if msg['role'] == 'user']

        has_positive = any(any(word in msg for word in ['fine', 'good', 'ok', 'okay']) for msg in user_messages)
        has_negative = any(any(word in msg for word in ['not good', 'bad', 'terrible', 'awful']) for msg in user_messages)

        if has_positive and has_negative:
            contradictions.append('emotional_state_mismatch')

        return contradictions