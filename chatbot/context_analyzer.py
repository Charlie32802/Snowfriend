# context_analyzer.py
import re
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class ConversationContext:
    """Rich context model for tracking conversation state"""
    temporal_scope: str # 'ongoing', 'single_event', 'past', 'future', 'hypothetical'
    emotional_tone: str # 'positive', 'negative', 'neutral', 'mixed', 'crisis', 'post_crisis'
    topic_type: str # 'problem', 'feeling', 'relationship', 'achievement', 'question', 'greeting', 'gratitude', 'playful_banter'
    urgency_level: str # 'crisis', 'high', 'medium', 'low', 'none'
    disclosure_depth: int # 1-5 scale (1=surface, 5=deep vulnerability)
    needs_validation: bool # Does user need empathy vs. questions?
    key_entities: List[str] # People, places, events mentioned
    implicit_requests: List[str] # What user might want (not explicitly stated)
    contradictions: List[str] # Conflicting info in conversation
    user_corrections: int # How many times user corrected the bot
    is_post_crisis: bool # User recovering from crisis moment
    expressing_gratitude: bool # User thanking the bot
    conversation_depth: int # Number of exchanges so far
    is_family_drama: bool = False  # New for Task 2
    minimal_question_mode: bool = True  # New for Task 2

class ContextAnalyzer:
    """
    ADVANCED SEMANTIC CONTEXT ANALYZER
    Understands MEANING, TEMPORAL SCOPE, EMOTIONAL STATE, and USER INTENT
    """

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
            'last_name_usage_turn': -999
        }

    # ========================================================================
    # TEMPORAL SCOPE DETECTION
    # ========================================================================

    def analyze_temporal_scope(self, text: str) -> str:
        """
        Detect timeframe: ongoing pattern, single event, past, future, hypothetical
        CRITICAL: This prevents "what happened today" when user says "always"
        """
        text_lower = text.lower()

        # ONGOING PATTERNS - continuous, repeated events
        ongoing_indicators = [
            r'\b(always|constantly|every (day|time|week)|keeps|never stops?|all the time)',
            r'\b(keeps? \w+ing|won\'?t stop|continues to|ongoing)',
            r'\b(habitually|repeatedly|continuously|persistently)',
        ]

        # SINGLE EVENTS - one-time occurrences
        single_event_indicators = [
            r'\b(today|yesterday|this morning|tonight|just now|earlier)',
            r'\b(happened|occurred|took place) (today|yesterday|just)',
            r'\b(one time|once|this time|that time)',
        ]

        # PAST - completed events (not current)
        past_indicators = [
            r'\b(used to|back then|in the past|before|previously|last (year|month))',
            r'\b(was|were|had been) \w+ing',
            r'\b(no longer|not anymore|stopped)',
        ]

        # FUTURE - upcoming events
        future_indicators = [
            r'\b(will|going to|planning to|next (week|month|year))',
            r'\b(tomorrow|soon|later|upcoming|in the future)',
        ]

        # HYPOTHETICAL - imagined scenarios
        hypothetical_indicators = [
            r'\b(what if|suppose|imagine|wonder if|thinking about)',
            r'\b(could|might|would|should) \w+ if',
        ]

        # Check each category
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
            return 'single_event' # Default assumption

    # ========================================================================
    # EMOTIONAL TONE DETECTION - ENHANCED
    # ========================================================================

    def analyze_emotional_tone(self, text: str, conversation_history: List[Dict]) -> str:
        """
        Detect emotional state with nuance: positive, negative, neutral, mixed, crisis, post_crisis
        Goes beyond simple keyword matching
        """
        text_lower = text.lower()

        # Check if user was recently in crisis
        if self.user_profile.get('recent_crisis', False):
            # Look for signs of stabilization
            stabilization_patterns = [
                r'\b(will|going to|thank|appreciate|better|calmer|okay)',
                r'\b(i\'ll (call|try|reach out))',
            ]

            if any(re.search(p, text_lower) for p in stabilization_patterns):
                return 'post_crisis' # User is recovering

        # CRISIS INDICATORS - immediate danger
        crisis_patterns = [
            r'\b(want to die|suicide|kill myself|end it all|no reason to live)',
            r'\b(can\'?t take it anymore|better off dead|no way out)',
        ]

        # NEGATIVE EMOTIONS - distress, sadness, anger
        negative_patterns = [
            r'\b(sad|depressed|upset|angry|frustrated|scared|anxious|worried)',
            r'\b(hate|terrible|awful|horrible|bad|worst|crying|hurt)',
            r'\b(not (good|ok|okay|fine)|feeling (bad|down|low))',
        ]

        # POSITIVE EMOTIONS - happiness, relief, excitement
        positive_patterns = [
            r'\b(happy|excited|glad|great|good|better|wonderful|amazing)',
            r'\b(relieved|proud|accomplished|love|enjoy)',
        ]

        # MIXED - contradictory emotions
        mixed_patterns = [
            r'\bbut\b', # "I'm happy but..."
            r'\balthough\b',
            r'\bhowever\b',
        ]

        # Count indicators
        crisis_count = sum(1 for p in crisis_patterns if re.search(p, text_lower))
        negative_count = sum(1 for p in negative_patterns if re.search(p, text_lower))
        positive_count = sum(1 for p in positive_patterns if re.search(p, text_lower))
        mixed_count = sum(1 for p in mixed_patterns if re.search(p, text_lower))

        # Determine tone
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

    # ========================================================================
    # ✅ FIX #1: TOPIC TYPE DETECTION - DECLINING VS GRATITUDE
    # ========================================================================

    def _is_declining_phrase(self, text: str) -> bool:
        """
        Detect if user is DECLINING (saying "no thanks") vs EXPRESSING GRATITUDE

        CRITICAL: "No, thank you" = declining, NOT gratitude!
        """
        text_lower = text.lower().strip()

        # Declining patterns (these are NOT gratitude)
        declining_patterns = [
            r'^\s*no,?\s+thank', # "No thank you", "No, thank you"
            r'^\s*nah,?\s+thank', # "Nah thank you"
            r'^\s*nope,?\s+thank', # "Nope, thanks"
            r'^\s*no\s+thanks?\b', # "No thanks"
            r'^\s*(i\'m|im)\s+(good|ok|okay|fine|alright),?\s+thank', # "I'm good, thanks"
            r'^\s*not?\s+(right now|now|at the moment|yet),?\s+thank', # "Not right now, thanks"
        ]

        return any(re.match(pattern, text_lower) for pattern in declining_patterns)

    def _is_literal_interpretation_humor(self, text: str, last_bot_message: str) -> bool:
        """
        Detect if user is giving a literal/humorous interpretation of bot's question
        This works for ANY phrase, not just specific ones
        """
        if not last_bot_message:
            return False

        text_lower = text.lower().strip()
        last_bot_lower = last_bot_message.lower()

        # Extract key phrases from bot's last message (questions or statements)
        bot_keywords = []

        # Common question patterns
        if "what's up" in last_bot_lower or "whats up" in last_bot_lower:
            bot_keywords.append("up")
        if "what's going on" in last_bot_lower or "whats going on" in last_bot_lower:
            bot_keywords.append("going on")
        if "how are you" in last_bot_lower or "how're you" in last_bot_lower:
            bot_keywords.append("are you")
        if "what's happening" in last_bot_lower or "whats happening" in last_bot_lower:
            bot_keywords.append("happening")

        # Check if user is giving a literal/dictionary definition or unexpected interpretation
        # Indicators of literal interpretation humor:
        # 1. User defines a word/phrase from bot's message
        # 2. User gives an unexpected, literal answer
        # 3. Response is short and doesn't match expected emotional depth

        literal_humor_indicators = [
            # Dictionary-style definitions
            r'\bis when\b', # "going on is when..."
            r'\bmeans\b', # "up means..."
            r'\b(is|are) (a|an|the)\b', # "ceiling is the..."

            # Unexpected literal objects/concepts
            r'\b(ceiling|sky|roof|stars|clouds)\b', # literal "up"
            r'\b(nothing|not much|nm|nmu)\b', # minimal response to "what's going on"
            r'\b(existing|surviving|vibing|chillin|alive)\b', # unexpected answers to "how are you"

            # Short, unexpectedly literal responses (under 15 words)
            # If response is <15 words AND contains a word from bot's question, likely humor
        ]

        # Check if user is defining/interpreting bot's words
        if any(re.search(pattern, text_lower) for pattern in literal_humor_indicators):
            return True

        # Check if response is short and contains keywords from bot's question
        word_count = len(text_lower.split())
        if word_count <= 15:
            # If user mentions a key phrase from bot's question in an unexpected way
            for keyword in bot_keywords:
                if keyword in text_lower:
                    # User is playing with the bot's words
                    return True

        return False

    def _is_playful_minimal_response(self, text: str, last_bot_message: str) -> bool:
        """
        Detect playful minimal responses (e.g., "nothing much", "nm", "just vibing")
        """
        text_lower = text.lower().strip()

        playful_minimal = [
            r'^\s*(nothing much|not much|nm|nmu|nuthin|nothin)\s*$',
            r'^\s*(just (vibing|chilling|existing|surviving|here))\s*$',
            r'^\s*(same old|the usual)\s*$',
            r'^\s*(alive|existing|surviving)\s*$',
            r'^\s*(you know|meh|eh)\s*$',
        ]

        return any(re.match(pattern, text_lower) for pattern in playful_minimal)

    # ✅ FIX #2: MOVE QUESTION CHECK HIGHER IN PRIORITY
    def analyze_topic_type(self, text: str, conversation_depth: int = 0, last_bot_message: str = None) -> str:
        """
        Identify what user is talking about: problem, feeling, relationship, gratitude, playful_banter, etc.

        ✅ FIX #1: Now correctly identifies "No, thank you" as 'general' (declining), NOT 'gratitude'
        ✅ FIX #2: Checks for questions EARLY to prevent misclassification as playful_banter

        Args:
            text: User's message
            conversation_depth: Number of exchanges so far (0 = first message)
            last_bot_message: Previous bot response for context awareness
        """
        text_lower = text.lower().strip()

        # ✅ FIX #1: CHECK FOR DECLINING FIRST (before gratitude check)
        if self._is_declining_phrase(text):
            # User is saying "No, thank you" = declining, NOT gratitude
            return 'general'

        # ✅ FIX #2: CHECK FOR QUESTIONS EARLY (before playful banter)
        # This prevents "what are good brands?" from being misclassified as playful_banter
        question_indicators = [
            r'^\s*(what|why|how|when|where|who|can you)',
            r'\b(recommend|suggest|any good|any ideas|what should|which)\b',
        ]

        if any(re.search(p, text_lower) for p in question_indicators):
            return 'question'

        # ✅ GLOBAL HUMOR DETECTION - Works for ANY conversational humor
        if last_bot_message and conversation_depth > 0:
            # Check for literal interpretation humor (works globally)
            if self._is_literal_interpretation_humor(text, last_bot_message):
                return 'playful_banter'

            # Check for playful minimal responses
            if self._is_playful_minimal_response(text, last_bot_message):
                return 'playful_banter'

        # General playful patterns (independent of bot's message)
        if conversation_depth > 2:
            playful_patterns = [
                r'\bwell (well|look)',
                r'\blook (what|who)',
                r'\bif it isn\'?t',
                r'\bwhat do we have here',
                r'\bfancy (seeing|meeting)',
                r'\bwould you look at (that|this)',
                r'\blol\b',
                r'\bhaha',
                r'\blmao\b',
            ]

            if any(re.search(p, text_lower) for p in playful_patterns):
                return 'playful_banter'

        # GREETING - no substantive content (ONLY if early in conversation)
        if conversation_depth <= 2 and len(text_lower.split()) <= 4 and any(g in text_lower for g in ['hi', 'hello', 'hey', 'hola', 'sup']):
            return 'greeting'

        # GRATITUDE - expressing thanks (HIGH PRIORITY - but AFTER declining check!)
        gratitude_indicators = [
            r'\b(thank|thanks|appreciate|grateful|gratitude)',
            r'\bthank you',
            r'\bthanks (a lot|so much|very much)',
            r'\bi appreciate',
            r'\bgrateful for',
        ]

        # Only classify as gratitude if NOT declining
        if any(re.search(p, text_lower) for p in gratitude_indicators):
            return 'gratitude'

        # PROBLEM - describing a difficulty
        problem_indicators = [
            r'\b(problem|issue|trouble|difficult|hard|struggle|can\'?t)',
        ]

        # FEELING - pure emotional expression
        feeling_indicators = [
            r'\b(feel|feeling|felt|emotion)',
            r'\b(sad|happy|angry|scared|anxious) (and|but|because)',
        ]

        # RELATIONSHIP - interpersonal issues
        relationship_indicators = [
            r'\b(friend|family|parent|mom|dad|partner|boyfriend|girlfriend|classmate)',
            r'\b(relationship|argument|fight|broke up)',
        ]

        # ACHIEVEMENT - positive accomplishment
        achievement_indicators = [
            r'\b(achieved|accomplished|succeed|won|got|finished|completed)',
        ]

        # Check categories
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

    # ========================================================================
    # URGENCY LEVEL DETECTION
    # ========================================================================

    def analyze_urgency(self, emotional_tone: str, text: str) -> str:
        """
        Determine how urgent the response needs to be
        """
        if emotional_tone == 'crisis':
            return 'crisis'

        if emotional_tone == 'post_crisis':
            return 'low' # User is recovering, no need for urgency

        text_lower = text.lower()

        # HIGH URGENCY - needs immediate support
        high_urgency_patterns = [
            r'\b(emergency|urgent|right now|immediately|help me)',
            r'\b(panic|freaking out|can\'?t breathe|spiraling)',
        ]

        # MEDIUM URGENCY - needs timely response
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

    # ========================================================================
    # DISCLOSURE DEPTH ANALYSIS
    # ========================================================================

    def analyze_disclosure_depth(self, text: str) -> int:
        """
        Rate how vulnerable/personal the disclosure is (1-5 scale)
        1 = surface level, 5 = deep vulnerability
        """
        text_lower = text.lower()

        # LEVEL 5 - Deep vulnerability
        level_5_indicators = [
            r'\b(abuse|trauma|suicide|rape|assault|self-harm)',
            r'\b(no one (knows|understands)|secret|ashamed)',
        ]

        # LEVEL 4 - Significant personal struggle
        level_4_indicators = [
            r'\b(depressed|anxious|scared|terrified|hopeless|lonely)',
            r'\b(family problems|broke up|fired|failed)',
            r'\balone (against the world|in the world)',
        ]

        # LEVEL 3 - Moderate sharing
        level_3_indicators = [
            r'\b(upset|frustrated|worried|concerned|bothered)',
            r'\b(argument|fight|disagreement)',
        ]

        # LEVEL 2 - Light sharing
        level_2_indicators = [
            r'\b(annoyed|tired|stressed|busy)',
        ]

        # Check levels (highest first)
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

    # ========================================================================
    # USER NEEDS ANALYSIS
    # ========================================================================

    def analyze_needs_validation(self, emotional_tone: str, topic_type: str) -> bool:
        """
        Determine if user needs validation vs. exploration
        Validation: "That sucks" / Exploration: "What happened?"
        """
        # High emotion = needs validation first
        if emotional_tone in ['negative', 'crisis']:
            return True

        # Achievements need validation
        if topic_type == 'achievement':
            return True

        # Gratitude needs acknowledgment
        if topic_type == 'gratitude':
            return True

        # Otherwise, explore
        return False

    # ========================================================================
    # KEY ENTITY EXTRACTION
    # ========================================================================

    def extract_key_entities(self, text: str) -> List[str]:
        """
        Extract people, places, events mentioned
        """
        entities = []
        text_lower = text.lower()

        # PEOPLE
        people_patterns = [
            r'\bmy (mom|dad|mother|father|parent|friend|partner|boyfriend|girlfriend|classmate|teacher)',
            r'\b(he|she|they) (said|did|told|made)',
        ]

        for pattern in people_patterns:
            matches = re.findall(pattern, text_lower)
            entities.extend(matches)

        # PLACES
        place_patterns = [
            r'\bat (school|work|home|office|class)',
        ]

        for pattern in place_patterns:
            matches = re.findall(pattern, text_lower)
            entities.extend(matches)

        return entities

    # ========================================================================
    # IMPLICIT REQUEST DETECTION - ENHANCED
    # ========================================================================

    def detect_implicit_requests(self, text: str, emotional_tone: str, topic_type: str, conversation_history: List[Dict] = None) -> List[str]:
        """
        Understand what user wants without saying it directly
        Example: "I'm sad" → implicit request: [empathy, understanding]
        """
        requests = []
        text_lower = text.lower()

        # ✅ NEW: USER QUESTIONING CRISIS HOTLINES
        if conversation_history and topic_type == 'question':
            # Check if last bot message provided crisis resources
            last_bot_msg = None
            for msg in reversed(conversation_history):
                if msg['role'] == 'assistant':
                    last_bot_msg = msg['content'].lower()
                    break

            if last_bot_msg and 'crisis hotline' in last_bot_msg:
                # User might be questioning the crisis resources
                resource_question_patterns = [
                    r'\bhow (does|will|can) (that|this|it|they).{0,20}help',
                    r'\bwhy (should|would) i (call|reach out|contact)',
                    r'\bwhat (can|will|do) they (do|say)',
                    r'\bwhat.?s (that|this).{0,20}(got to do|do|have to do).{0,20}with me',
                    r'\bhow.{0,10}(is|does) that.{0,10}(help|relevant|related)',
                ]

                if any(re.search(p, text_lower) for p in resource_question_patterns):
                    requests.append('crisis_resource_question')

        # ✅ NEW: USER QUESTIONING CRISIS RESPONSE
        if conversation_history and topic_type == 'question':
            # Check if last bot message was a crisis response
            last_bot_msg = None
            for msg in reversed(conversation_history):
                if msg['role'] == 'assistant':
                    last_bot_msg = msg['content'].lower()
                    break

            if last_bot_msg and ('crisis hotline' in last_bot_msg or 'extremely concerned' in last_bot_msg):
                # User is questioning the crisis response
                clarification_patterns = [
                    r'\b(what|why).{0,20}(concern|worry)',
                    r'\bjust (a|an)\b',
                    r'\bwhat are you.{0,20}(concern|worry|talking about)',
                ]

                if any(re.search(p, text_lower) for p in clarification_patterns):
                    requests.append('crisis_clarification')

        # USER WANTS EMPATHY
        if emotional_tone in ['negative', 'crisis']:
            requests.append('empathy')

        # USER EXPRESSING GRATITUDE
        if topic_type == 'gratitude':
            requests.append('acknowledge_gratitude')

        # USER IS POST-CRISIS
        if emotional_tone == 'post_crisis':
            requests.append('gentle_encouragement')

        # ✅ USER DOING PLAYFUL BANTER
        if topic_type == 'playful_banter':
            requests.append('match_playful_energy')

        # USER WANTS TO BE HEARD
        if any(word in text_lower for word in ['nobody listens', 'no one understands', 'alone']):
            requests.append('validation_of_experience')

        # USER WANTS ADVICE (rarely)
        if any(word in text_lower for word in ['what should i', 'help me', 'don\'t know what to do']):
            requests.append('guidance')

        # USER WANTS TO VENT
        if len(text_lower.split()) > 30 and '?' not in text:
            requests.append('space_to_talk')

        return requests

    # ========================================================================
    # CONVERSATION DEPTH TRACKING
    # ========================================================================

    def analyze_conversation_depth(self, conversation_history: List[Dict]) -> int:
        """
        Track how many exchanges have happened on current topic
        Returns: Number of back-and-forth exchanges
        """
        if not conversation_history:
            return 0

        # Count user messages (rough proxy for conversation depth)
        user_messages = [msg for msg in conversation_history if msg['role'] == 'user']
        return len(user_messages)

    def should_offer_guidance(self, conversation_history: List[Dict], context: 'ConversationContext') -> bool:
        """
        Determine if bot should offer guidance instead of just exploring

        Guidance appropriate when:
        - User has shared enough context (3+ exchanges)
        - Disclosure depth is significant (3+)
        - User seems stuck or seeking help
        """
        depth = self.analyze_conversation_depth(conversation_history)

        # After 3+ exchanges with significant disclosure, offer guidance
        if depth >= 3 and context.disclosure_depth >= 3:
            return True

        # If user explicitly asks for help
        last_msg = conversation_history[-1]['content'].lower() if conversation_history else ""
        if any(phrase in last_msg for phrase in ['help me', 'what should i', 'how do i', 'what can i do']):
            return True

        return False

    def analyze_message(self, text: str, conversation_history: List[Dict]) -> ConversationContext:
        """
        COMPREHENSIVE CONTEXT ANALYSIS
        Returns rich context object for response generation
        """
        # ✅ Calculate conversation depth first
        conversation_depth = self.analyze_conversation_depth(conversation_history)

        # ✅ Get last bot message for context-aware playfulness detection
        last_bot_message = None
        if conversation_history:
            for msg in reversed(conversation_history):
                if msg['role'] == 'assistant':
                    last_bot_message = msg['content']
                    break

        temporal_scope = self.analyze_temporal_scope(text)
        emotional_tone = self.analyze_emotional_tone(text, conversation_history)
        topic_type = self.analyze_topic_type(text, conversation_depth, last_bot_message) # ✅ Pass last bot message
        urgency_level = self.analyze_urgency(emotional_tone, text)
        disclosure_depth = self.analyze_disclosure_depth(text)
        needs_validation = self.analyze_needs_validation(emotional_tone, topic_type)
        key_entities = self.extract_key_entities(text)
        implicit_requests = self.detect_implicit_requests(text, emotional_tone, topic_type, conversation_history)

        # Track post-crisis recovery
        is_post_crisis = emotional_tone == 'post_crisis'
        if is_post_crisis:
            self.user_profile['crisis_recovery_turns'] += 1
            # After 3+ turns of stability, reset crisis flag
            if self.user_profile['crisis_recovery_turns'] >= 3:
                self.user_profile['recent_crisis'] = False

        # Check if expressing gratitude
        expressing_gratitude = topic_type == 'gratitude'

        # Track user corrections from conversation history
        user_corrections = sum(
            1 for msg in conversation_history
            if msg['role'] == 'user' and any(
                phrase in msg['content'].lower()
                for phrase in ["didn't i", "i just said", "i already told", "you're not listening"]
            )
        )

        # Detect contradictions in conversation
        contradictions = self._detect_contradictions(conversation_history)

        # ✅ NEW: Compute is_family_drama (from safety.py logic)
        family_drama_indicators = [
            r'\b(mom|mother|dad|father|parent|sibling|brother|sister|family)\b',
            r'\b(clean|tidy|organize).{0,20}(room|house|apartment|space)\b',
            r'\b(grounded|punished|in trouble|mad at|angry with|upset with)\b',
            r'\b(if i don\'t|unless i|or else|otherwise).{0,20}(clean|do|finish)\b',
            r'\b(typical|normal|usual).{0,20}(parent|family|mom|dad)\b',
        ]
        is_family_drama = any(re.search(pattern, text.lower()) for pattern in family_drama_indicators)

        # ✅ NEW: Task 2 - Refine Minimal question mode
        # Deactivate if is_family_drama or disclosure_depth >=4
        minimal_question_mode = not (is_family_drama or disclosure_depth >= 4)

        # Check if bot should offer guidance instead of just exploring
        should_guide = self.should_offer_guidance(conversation_history,
            ConversationContext(
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
                minimal_question_mode=minimal_question_mode
            )
        )

        # Add guidance flag to implicit requests
        if should_guide:
            implicit_requests.append('guidance_needed')

        return ConversationContext(
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
            minimal_question_mode=minimal_question_mode
        )

    def _detect_contradictions(self, conversation_history: List[Dict]) -> List[str]:
        """
        Find contradictory information in conversation
        Example: User says "I'm fine" then "I'm not doing well"
        """
        contradictions = []

        # This is a simplified version - full implementation would use NLP
        user_messages = [msg['content'].lower() for msg in conversation_history if msg['role'] == 'user']

        # Check for emotional contradictions
        has_positive = any(any(word in msg for word in ['fine', 'good', 'ok', 'okay']) for msg in user_messages)
        has_negative = any(any(word in msg for word in ['not good', 'bad', 'terrible', 'awful']) for msg in user_messages)

        if has_positive and has_negative:
            contradictions.append('emotional_state_mismatch')

        return contradictions