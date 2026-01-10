# memory_system.py - ULTRA-FIXED VERSION WITH BOT CONTEXT TRACKING
# ✅ NO MORE HALLUCINATIONS - Topics extracted ONLY from actual user words
# ✅ UNIVERSAL topic detection - works for ANY topic, not hardcoded
# ✅ NEW: Tracks Snowfriend's recent questions to prevent repetition
# ✅ NEW: Detects when user has answered questions

import re
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime

class ConversationMemory:
    """
    Tracks and summarizes conversation history for better continuity
    ✅ FIXED: ULTRA-STRICT topic extraction - NO assumptions, NO hallucinations
    ✅ NEW: Bot context awareness - remembers own questions
    """
    
    def __init__(self):
        self.facts_extracted = {}  # Per-user facts
    
    def extract_conversation_facts(self, conversation_history: List[Dict]) -> Dict:
        """
        Extract key facts from conversation history with pattern combination tracking.
    
        Extraction strategy:
        - Identifies topics user explicitly mentioned in their messages
        - Detects entities (people, places, activities) through pattern matching
        - Tracks emotional expressions and problem-sharing indicators
        - Records bot's recent questions to prevent repetition
        - Monitors which questions user has already answered
    
        Args:
            conversation_history: List of message dictionaries with 'role' and 'content'
    
        Returns:
            Dict containing:
            - topics_discussed: Set of topic strings user mentioned
            - entities_mentioned: Dict of categorized entities (people, places, activities, objects)
            - emotions_expressed: Set of detected emotion indicators
            - first_user_message: Initial message content
            - exchange_count: Number of user messages
            - has_shared_problem: Boolean indicating problem disclosure
            - recent_topics: List of topics from last 3 messages
            - pattern_combinations: List of detected message pattern combinations
            - last_message_patterns: Dict of patterns in most recent message
            - bot_recent_questions: List of question types bot recently asked
            - user_answered_questions: Set of question types user addressed
        """
        facts = {
            'topics_discussed': set(),
            'entities_mentioned': {
                'people': set(),
                'places': set(),
                'activities': set(),
                'objects': set()
            },
            'emotions_expressed': set(),
            'first_user_message': None,
            'exchange_count': 0,
            'has_shared_problem': False,
            'recent_topics': [],
            'greetings_count': 0,
            'substantive_exchanges': 0,
            'last_3_user_messages': [],
            'pattern_combinations': [],
            'last_message_patterns': {},
            # ✅ NEW: Track Snowfriend's recent questions to prevent repetition
            'bot_recent_questions': [],  # Last 3 questions Snowfriend asked
            'user_answered_questions': set(),  # Topics user already addressed
        }
        
        user_messages = [msg for msg in conversation_history if msg['role'] == 'user']
        bot_messages = [msg for msg in conversation_history if msg['role'] == 'assistant']
        
        # ✅ NEW: Track Snowfriend's recent questions (last 3 bot messages)
        question_patterns = [
            (r"what'?s on your mind", 'whats_on_mind'),
            (r"what'?s been on your mind", 'whats_on_mind'),
            (r"what'?s going on", 'whats_going_on'),
            (r"what happened", 'what_happened'),
            (r"what are you (doing|up to)", 'what_doing'),
            (r"how are you (feeling|doing)", 'how_are_you'),
            (r"want to talk about", 'want_to_talk'),
            (r"tell me more", 'tell_more'),
            (r"anything (else |specific )?on your mind", 'whats_on_mind'),
        ]
        
        for bot_msg in bot_messages[-3:]:  # Last 3 bot messages
            bot_content_lower = bot_msg['content'].lower()
            for pattern, question_type in question_patterns:
                if re.search(pattern, bot_content_lower):
                    facts['bot_recent_questions'].append(question_type)
                    break  # Only add one question type per message
        
        # ✅ NEW: Check if user answered these questions
        if user_messages:
            last_user_msg = user_messages[-1]['content'].lower()
            
            # User gave status update (answered "how are you" / "what's on your mind")
            status_words = ['fine', 'good', 'okay', 'ok', 'alright', 'not much', 'nothing much', 
                          'same', 'usual', 'normal', 'decent', 'well']
            if any(word in last_user_msg for word in status_words):
                facts['user_answered_questions'].add('status_check')
                facts['user_answered_questions'].add('whats_on_mind')  # These are similar questions
            
            # User shared what they're doing
            doing_phrases = ['i\'m', 'im', 'just', 'doing', 'nothing', 'not much', 
                           'hanging out', 'chilling', 'relaxing', 'working', 'studying']
            if any(phrase in last_user_msg for phrase in doing_phrases):
                facts['user_answered_questions'].add('what_doing')
            
            # User deflected or redirected
            deflect_phrases = ['what about you', 'how about you', 'and you?', 'you?']
            if any(phrase in last_user_msg for phrase in deflect_phrases):
                facts['user_answered_questions'].add('deflection')
        
        # Track first user message
        if user_messages:
            facts['first_user_message'] = user_messages[0]['content']
        
        # Track exchange count
        facts['exchange_count'] = len(user_messages)
        
        # Track last 3 user messages
        facts['last_3_user_messages'] = [msg['content'] for msg in user_messages[-3:]]
        
        # Analyze LAST message for pattern combinations
        if user_messages:
            last_msg = user_messages[-1]['content'].lower()
            facts['last_message_patterns'] = self._extract_pattern_combinations(last_msg)
        
        # Analyze each user message
        for msg in user_messages:
            content = msg['content']
            content_lower = content.lower()
            
            # Count greetings vs substantive messages
            if self._is_greeting_message(content_lower) and len(content_lower.split()) <= 4:
                facts['greetings_count'] += 1
            else:
                facts['substantive_exchanges'] += 1
            
            # ✅ ULTRA-FIXED: Extract ONLY explicit nouns/topics from user's actual words
            topics, entities = self._extract_topics_universal(content, content_lower)
            facts['topics_discussed'].update(topics)
            
            # Merge entities
            for entity_type, entity_list in entities.items():
                facts['entities_mentioned'][entity_type].update(entity_list)
            
            # Extract emotions
            facts['emotions_expressed'].update(self._extract_emotions(content_lower))
            
            # Check if user has shared a problem
            if not facts['has_shared_problem']:
                facts['has_shared_problem'] = self._has_shared_problem(content_lower)
            
            # Extract pattern combinations for most recent message
            if msg == user_messages[-1]:
                pattern_analysis = self._analyze_pattern_combinations(content_lower)
                if pattern_analysis:
                    facts['pattern_combinations'].append(pattern_analysis)
        
        # Convert sets to lists for JSON serialization
        facts['topics_discussed'] = list(facts['topics_discussed'])
        facts['entities_mentioned'] = {
            k: list(v) for k, v in facts['entities_mentioned'].items()
        }
        facts['emotions_expressed'] = list(facts['emotions_expressed'])
        
        # Get recent topics (last 3 substantive messages)
        facts['recent_topics'] = self._get_recent_topics(user_messages[-3:])
        
        return facts
    
    def _extract_topics_universal(self, content: str, content_lower: str) -> Tuple[Set[str], Dict[str, Set[str]]]:
        """
        ✅ ULTRA-FIXED: CONTEXT-AWARE topic extraction
        
        Extracts ONLY topics/people that are clearly the SUBJECT of discussion.
        Prevents false positives like "be like a friend" → "friend".
        
        Examples:
            "My friend is mean" → people: {"friend"} ✅
            "Be like a friend" → people: {} ✅ (not a person!)
            "I have a friend" → people: {"friend"} ✅
            "Friend or therapist" → people: {} ✅ (comparison, not person)
        """
        topics = set()
        entities = {
            'people': set(),
            'places': set(),
            'activities': set(),
            'objects': set()
        }
        
        # ====================================================================
        # STEP 1: CONTEXT-AWARE PEOPLE EXTRACTION (NO FALSE POSITIVES!)
        # ====================================================================
        
        # ✅ CRITICAL: Only extract people when there's clear possessive/relationship context
        
        # FAMILY - requires possessive or relationship verb
        family_patterns = [
            # Possessive patterns (my, their, his, her)
            r'\b(my|our|their|his|her) (mom|mother|dad|father|parent|parents)\b',
            r'\b(my|our|their|his|her) (sibling|brother|sister|bro|sis)\b',
            r'\b(my|our|their|his|her) (grandma|grandmother|grandpa|grandfather|lola|lolo)\b',
            r'\b(my|our|their|his|her) (aunt|uncle|tita|tito|cousin)\b',
            
            # Relationship verbs (have, talk to, live with, etc.)
            r'\b(have|got|talk to|live with|stay with) (a |my |our )?(mom|mother|dad|father|parent)\b',
        ]
        
        for pattern in family_patterns:
            match = re.search(pattern, content_lower)
            if match:
                # Extract the relationship word (mom, dad, etc.)
                relationship = match.group(2) if len(match.groups()) >= 2 else match.group(1)
                
                # Map to generic category
                if relationship in ['mom', 'mother', 'dad', 'father', 'parent', 'parents']:
                    entities['people'].add('parent')
                elif relationship in ['sibling', 'brother', 'sister', 'bro', 'sis']:
                    entities['people'].add('sibling')
                elif relationship in ['grandma', 'grandmother', 'grandpa', 'grandfather', 'lola', 'lolo']:
                    entities['people'].add('grandparent')
                elif relationship in ['aunt', 'uncle', 'tita', 'tito', 'cousin']:
                    entities['people'].add('relative')
        
        # FRIENDS/SOCIAL - ✅ CRITICAL FIX: Only with possessive or relationship context
        friend_valid_patterns = [
            # Possessive
            r'\b(my|our|their|his|her) (friend|friends|buddy|buddies|classmate|classmates)\b',
            
            # Relationship verbs
            r'\b(have|got|know) (a |some |many )?(friend|friends)\b',
            r'\b(talk to|hang out with|meet) (my |a |some )?(friend|friends)\b',
            r'\b(friend|friends) (of mine|who|that)\b',  # "a friend who..."
            
            # Clear subject patterns
            r'\b(friend|friends) (is|are|was|were|said|told|did)\b',  # "my friend is mean"
        ]
        
        # ✅ BLACKLIST: Patterns that should NOT count as mentioning a friend
        friend_invalid_patterns = [
            r'\b(be |like |as |a) (friend|friends)\b',  # "be like a friend", "as a friend"
            r'\b(or |nor |not |versus |vs) (a )?(friend|friends)\b',  # "friend or therapist"
            r'\b(friend|friends) (or |nor |not |versus |vs)\b',  # "friend or therapist"
            r'\bmake friends\b',  # "want to make friends" (generic)
            r'\bneed friends\b',  # "need friends" (generic)
            r'\bwant friends\b',  # "want friends" (generic)
        ]
        
        # Check blacklist first
        is_invalid = any(re.search(pattern, content_lower) for pattern in friend_invalid_patterns)
        
        if not is_invalid:
            # Check valid patterns
            if any(re.search(pattern, content_lower) for pattern in friend_valid_patterns):
                entities['people'].add('friend')
        
        # ROMANTIC PARTNERS - requires possessive or relationship context
        partner_patterns = [
            r'\b(my|our|their|his|her) (boyfriend|girlfriend|partner|gf|bf)\b',
            r'\b(have|got|talk to|broke up with|dating) (a |my )?(boyfriend|girlfriend|partner)\b',
        ]
        
        if any(re.search(pattern, content_lower) for pattern in partner_patterns):
            entities['people'].add('partner')
        
        # AUTHORITY FIGURES - requires clear context
        authority_patterns = [
            r'\b(my|our|their|the) (boss|manager|supervisor|coworker|colleague|teacher|prof|professor)\b',
            r'\b(work with|report to|talk to) (a |my |the )?(boss|manager|coworker|teacher)\b',
        ]
        
        for pattern in authority_patterns:
            match = re.search(pattern, content_lower)
            if match:
                role = match.group(2) if len(match.groups()) >= 2 else match.group(1)
                
                if role in ['boss', 'manager', 'supervisor', 'coworker', 'colleague']:
                    entities['people'].add('coworker')
                elif role in ['teacher', 'prof', 'professor', 'instructor']:
                    entities['people'].add('teacher')
        
        # ====================================================================
        # STEP 2: Extract PLACES (with clear context)
        # ====================================================================
        
        place_patterns = [
            r'\bat (school|work|home|office|class|gym|mall|store|restaurant|cafe|park)\b',
            r'\bgo(?:ing)? to (school|work|office|gym|mall|store)\b',
            r'\bin (school|class|office|home)\b',
        ]
        
        for pattern in place_patterns:
            match = re.search(pattern, content_lower)
            if match:
                place = match.group(1)
                entities['places'].add(place)
        
        # ====================================================================
        # STEP 3: Extract ACTIVITIES (verb + noun)
        # ====================================================================
        
        activity_patterns = [
            r'\b(play(?:ing)?) (basketball|football|soccer|volleyball|tennis|badminton|chess|cards|games?)\b',
            r'\b(do(?:ing)?) (boxing|martial arts|karate|judo|taekwondo|mma)\b',
            r'\b(go(?:ing)?) (swimming|running|jogging|cycling|hiking|fishing)\b',
            r'\b(watch(?:ing)?) (movies?|shows?|tv|netflix|youtube|anime)\b',
            r'\b(listen(?:ing)?) to (music|podcast|radio)\b',
            r'\b(read(?:ing)?) (books?|novels?|manga|comics?)\b',
            r'\b(cook(?:ing)?|bak(?:ing)?)\b',
            r'\b(study(?:ing)?|learn(?:ing)?|practic(?:ing)?)\b',
        ]
        
        for pattern in activity_patterns:
            matches = re.findall(pattern, content_lower)
            for match in matches:
                if isinstance(match, tuple):
                    activity_phrase = ' '.join([m for m in match if m]).strip()
                    entities['activities'].add(activity_phrase)
                else:
                    entities['activities'].add(match)
        
        # ====================================================================
        # STEP 4: Extract TOPICS (explicit nouns as subjects of discussion)
        # ====================================================================
        
        # ✅ CRITICAL: Only add topic if it's clearly being DISCUSSED, not just mentioned
        
        topic_nouns = [
            # Education - only if discussing it
            r'\b(school|class|homework|assignment|exam|test) (is|was|today|tomorrow|sucks|hard|difficult)\b',
            r'\btalking about (school|class|homework)\b',
            r'\b(at|in|during) (school|class)\b',
            
            # Work
            r'\b(work|job|career|office) (is|was|today|tomorrow|sucks|hard|stressful)\b',
            r'\btalking about (work|job|career)\b',
            r'\b(at|in|during) (work|office)\b',
            
            # Activities/Sports (as topics)
            r'\b(boxing|basketball|football|soccer|sports?) (is|was|today|practice|game|match)\b',
            r'\btalking about (boxing|basketball|sports?)\b',
            
            # Hobbies
            r'\b(hobby|hobbies|game|games|gaming|movie|music|book) (is|was|I like|I love|I enjoy)\b',
        ]
        
        for pattern in topic_nouns:
            matches = re.findall(pattern, content_lower)
            for match in matches:
                if isinstance(match, tuple):
                    # Extract the topic word (first group)
                    topic = match[0]
                    topics.add(topic)
                else:
                    topics.add(match)
        
        # ====================================================================
        # STEP 5: Extract OBJECTS mentioned
        # ====================================================================
        
        object_patterns = [
            r'\b(my|the|a) (phone|computer|laptop|tablet|ipad|device|camera)\b',
            r'\b(my|the|a) (car|bike|bicycle|motorcycle|vehicle)\b',
        ]
        
        for pattern in object_patterns:
            matches = re.findall(pattern, content_lower)
            for match in matches:
                if isinstance(match, tuple):
                    obj = match[1]  # Second group is the object
                    entities['objects'].add(obj)
        
        return topics, entities
    
    def _is_greeting_message(self, text: str) -> bool:
        """Check if message is just a greeting"""
        greeting_patterns = [
            r'^\s*(hi|hello|hey|hola|sup|yo|hiya|howdy)\s*$',
            r'^\s*(hi|hello|hey|hola|sup)\s+(there|friend|snowfriend)\s*$',
        ]
        return any(re.match(pattern, text) for pattern in greeting_patterns)
    
    def _extract_emotions(self, text: str) -> Set[str]:
        """Extract emotions expressed"""
        emotions = set()
        
        # Negative emotions
        if any(word in text for word in ['sad', 'depressed', 'down', 'upset', 'unhappy', 'miserable']):
            emotions.add('sadness')
        
        if any(word in text for word in ['angry', 'mad', 'frustrated', 'annoyed', 'furious', 'pissed']):
            emotions.add('anger')
        
        if any(word in text for word in ['anxious', 'worried', 'nervous', 'scared', 'afraid', 'terrified']):
            emotions.add('anxiety')
        
        if any(word in text for word in ['lonely', 'alone', 'isolated']):
            emotions.add('loneliness')
        
        if any(word in text for word in ['embarrassed', 'ashamed', 'humiliated']):
            emotions.add('embarrassment')
        
        # Positive emotions
        if any(word in text for word in ['happy', 'excited', 'glad', 'good', 'great', 'joyful']):
            emotions.add('happiness')
        
        if any(word in text for word in ['calm', 'peaceful', 'relaxed']):
            emotions.add('calmness')
        
        return emotions
    
    def _has_shared_problem(self, text: str) -> bool:
        """Check if user has shared a problem"""
        problem_indicators = [
            r'\b(problem|issue|trouble|difficult|hard|struggle)',
            r'\b(can\'?t|cannot|won\'?t|unable to)',
            r'\b(hate|dislike|annoying|frustrating)',
            r'\b(nobody|no one).{0,20}(understand|listen|care)',
        ]
        
        return any(re.search(pattern, text) for pattern in problem_indicators)
    
    def _get_recent_topics(self, recent_messages: List[Dict]) -> List[str]:
        """Get topics from recent messages"""
        recent_topics = []
        
        for msg in recent_messages:
            content = msg['content']
            content_lower = content.lower()
            topics, _ = self._extract_topics_universal(content, content_lower)
            
            if topics:
                recent_topics.extend(list(topics))
        
        return list(set(recent_topics))  # Remove duplicates
    
    def _extract_pattern_combinations(self, text: str) -> Dict:
        """
        Extract multiple patterns from a single message
        """
        text_lower = text.lower()
        
        patterns = {
            'has_gratitude': bool(re.search(r'\b(thank|thanks|appreciate|grateful)\b', text_lower)),
            'has_problem': bool(re.search(r'\b(problem|issue|trouble|difficult|hard|struggle|can\'?t)\b', text_lower)),
            'has_playfulness': bool(
                re.search(r'\b(lol|haha|😂|😅|lmao)\b', text_lower) or
                re.search(r'\bjust kidding|jk|kidding\b', text_lower) or
                'laugh' in text_lower
            ),
            'has_emotion': bool(re.search(r'\b(sad|happy|angry|frustrated|anxious|worried|excited)\b', text_lower)),
            'has_question': bool(re.search(r'\b(what|why|how|when|where|who|can you|should i)\b', text_lower) and '?' in text_lower),
            'has_declining': bool(re.search(r'^\s*no,?\s+thank', text_lower)),
        }
        
        # Create pattern summary
        active_patterns = [key.replace('has_', '') for key, value in patterns.items() if value]
        patterns['pattern_summary'] = '+'.join(active_patterns) if active_patterns else 'simple'
        
        return patterns
    
    def _analyze_pattern_combinations(self, text: str) -> str:
        """
        Analyze which patterns are present and return guidance
        """
        patterns = self._extract_pattern_combinations(text)
        
        if not any(patterns.values()):
            return None
        
        # Generate combination-specific guidance
        if patterns['has_gratitude'] and patterns['has_problem'] and patterns['has_playfulness']:
            return "User mixed gratitude + problem + humor - Acknowledge all three"
        
        elif patterns['has_gratitude'] and patterns['has_problem']:
            return "User thanked while sharing problem - Acknowledge gratitude first, then address problem"
        
        elif patterns['has_emotion'] and patterns['has_playfulness']:
            return "User expressed emotion with humor - Validate feeling while matching light tone"
        
        elif patterns['has_question'] and patterns['has_problem']:
            return "User asked question about a problem - Answer directly if possible"
        
        return None
    
    def generate_memory_context(self, facts: Dict, user_name: str = None) -> str:
        """
        Generate memory context string for system prompt
        ✅ NEW: Includes bot context awareness
        """
        context_parts = []
        
        # ✅ NEW: Bot context awareness
        bot_questions = facts.get('bot_recent_questions', [])
        user_answered = facts.get('user_answered_questions', set())
        
        if bot_questions or user_answered:
            context_parts.append("🧠 CONVERSATION CONTEXT:")
            
            if bot_questions:
                context_parts.append(f"- You recently asked about: {', '.join(set(bot_questions))}")
            
            if user_answered:
                context_parts.append(f"- User already answered: {', '.join(user_answered)}")
                context_parts.append("- ⚠️ DON'T ask the same questions again!")
        
        # Basic conversation info
        exchange_count = facts.get('exchange_count', 0)
        substantive_exchanges = facts.get('substantive_exchanges', 0)
        
        if exchange_count > 0:
            context_parts.append(f"\n📊 CONVERSATION STATE:")
            context_parts.append(f"- You've exchanged {exchange_count} messages with {user_name or 'this user'}")
            
            if substantive_exchanges > 0:
                context_parts.append(f"- {substantive_exchanges} substantive exchanges")
        
        # First message memory
        first_msg = facts.get('first_user_message')
        if first_msg and exchange_count >= 2:
            context_parts.append(f"\n💬 FIRST MESSAGE:")
            context_parts.append(f'- User\'s first message was: "{first_msg}"')
        
        # Last 3 messages
        last_3 = facts.get('last_3_user_messages', [])
        if len(last_3) >= 2:
            context_parts.append(f"\n💬 RECENT MESSAGES:")
            for i, msg in enumerate(last_3[-3:], 1):
                context_parts.append(f"  {i}. \"{msg}\"")
        
        # Topics discussed - ✅ ONLY explicit topics
        topics = facts.get('topics_discussed', [])
        if topics:
            context_parts.append(f"\n📚 TOPICS USER MENTIONED:")
            context_parts.append(f"- {', '.join(topics)}")
            context_parts.append(f"- ⚠️ ONLY mention topics user EXPLICITLY said")
        
        # People mentioned
        entities = facts.get('entities_mentioned', {})
        people = entities.get('people', []) if isinstance(entities, dict) else []
        if people:
            context_parts.append(f"\n👥 PEOPLE MENTIONED:")
            context_parts.append(f"- {', '.join(people)}")
        
        # Emotions expressed
        emotions = facts.get('emotions_expressed', [])
        if emotions:
            context_parts.append(f"\n😔 EMOTIONS EXPRESSED:")
            context_parts.append(f"- {', '.join(emotions)}")
        
        # Problem sharing status
        has_problem = facts.get('has_shared_problem', False)
        if has_problem:
            context_parts.append(f"\n⚠️ USER HAS SHARED A PROBLEM")
            context_parts.append(f"- Acknowledge what they've told you")
        
        return "\n".join(context_parts)
    
    def should_reference_memory(self, user_message: str, facts: Dict) -> bool:
        """
        Determine if bot should explicitly reference past conversation
        """
        msg_lower = user_message.lower()
        
        # User explicitly asking about memory
        memory_questions = [
            r'\bwhat (did|have) i (say|said|tell|told)',
            r'\bdo you remember',
            r'\bfirst (thing|message)',
            r'\bearlier i (said|told|mentioned)',
            r'\bpreviously',
        ]
        
        if any(re.search(pattern, msg_lower) for pattern in memory_questions):
            return True
        
        return False

    def _generate_dynamic_follow_up(self, facts: Dict) -> str:
        """
        ✅ UNIVERSAL: Generate follow-up based on ACTUAL conversation
        Works for ANY topic user mentioned
        """
        topics = facts.get('topics_discussed', [])
        emotions = facts.get('emotions_expressed', [])
        has_shared_problem = facts.get('has_shared_problem', False)
        exchange_count = facts.get('exchange_count', 0)
        
        # For very short conversations
        if exchange_count <= 2:
            return "We're just getting started! What's on your mind now?"
        
        # If user shared a problem or difficult emotion
        if has_shared_problem or any(e in emotions for e in ['sadness', 'anger', 'anxiety', 'loneliness', 'embarrassment']):
            if topics:
                # Use ACTUAL topics user mentioned
                topic_str = ', '.join(topics[:2])  # First 2 topics
                return f"We've been talking about {topic_str} and how it's been tough. Still working through that?"
            else:
                return "We've been discussing some difficult feelings. Want to continue with that?"
        
        # If we have specific topics, reference them naturally
        if topics:
            if len(topics) == 1:
                topic = topics[0]
                return f"We've been talking about {topic}. Still on your mind?"
            else:
                topic_str = ', '.join(topics[:2])
                return f"We've discussed {topic_str}. Still thinking about any of that?"
        
        # If we have emotions mentioned
        if emotions:
            if any(e in emotions for e in ['happiness', 'calmness']):
                return "We've been talking about some positive stuff. Still in that good headspace?"
            else:
                return "We've discussed some feelings. Want to continue with that?"
        
        # Generic follow-up
        return "We've been chatting for a bit. What's on your mind now?"


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def inject_memory_into_prompt(
    base_prompt: str,
    conversation_history: List[Dict],
    user_name: str = None
) -> Tuple[str, Dict]:
    """
    Inject memory context into system prompt
    """
    memory_system = ConversationMemory()
    
    # Extract facts
    facts = memory_system.extract_conversation_facts(conversation_history)
    
    # Generate memory context
    memory_context = memory_system.generate_memory_context(facts, user_name)
    
    # Inject into prompt
    if memory_context:
        enhanced_prompt = f"{base_prompt}\n\n{'='*60}\n{memory_context}\n{'='*60}\n"
    else:
        enhanced_prompt = base_prompt
    
    return enhanced_prompt, facts


def check_if_memory_question(user_message: str, facts: Dict, conversation_history: List[Dict] = None) -> Optional[str]:
    """
    ✅ ULTRA-FIXED: Check if user is asking about previous conversation
    Returns a direct answer if it's a memory question
    
    ✅ CRITICAL: Gets first message from conversation_history, NOT facts
    """
    msg_lower = user_message.lower()
    
    # First message question
    first_msg_patterns = [
        r'what.{0,20}first (message|thing)',
        r'first (message|thing).{0,20}(i|you)',
        r'what did i (first|initially) (say|send|tell)',
        r'what was my (first|initial) (message|thing)',
    ]
    
    if any(re.search(pattern, msg_lower) for pattern in first_msg_patterns):
        # ✅ CRITICAL FIX: Get first message from conversation_history, not facts
        first_msg = None
        if conversation_history:
            user_messages = [msg for msg in conversation_history if msg.get('role') == 'user']
            if user_messages:
                first_msg = user_messages[0].get('content', '').strip()
        
        if first_msg:
            memory_system = ConversationMemory()
            follow_up = memory_system._generate_dynamic_follow_up(facts)
            
            # ✅ Clear, accurate response
            return f"""Your very first message to me was:

"{first_msg}"

{follow_up}"""
        else:
            return "We just started chatting. What would you like to talk about?"
    
    # General memory question
    memory_patterns = [
        r'do you remember',
        r'what did i (say|tell|mention)',
        r'earlier i (said|told|mentioned)',
        r'did i (say|tell|mention)',
        r'what (have|did) we talk',
    ]
    
    if any(re.search(pattern, msg_lower) for pattern in memory_patterns):
        topics = facts.get('topics_discussed', [])
        entities = facts.get('entities_mentioned', {})
        people = entities.get('people', []) if isinstance(entities, dict) else []
        emotions = facts.get('emotions_expressed', [])
        
        summary_parts = []
        
        if topics:
            if len(topics) == 1:
                summary_parts.append(f"You mentioned {topics[0]}")
            else:
                topics_str = ', '.join(topics[:-1]) + f", and {topics[-1]}"
                summary_parts.append(f"You've talked about {topics_str}")
        
        if people:
            if len(people) == 1:
                summary_parts.append(f"you mentioned your {people[0]}")
            else:
                people_str = ', '.join(people[:-1]) + f", and {people[-1]}"
                summary_parts.append(f"you talked about your {people_str}")
        
        if emotions:
            if len(emotions) == 1:
                summary_parts.append(f"you expressed feeling {emotions[0]}")
            else:
                emotions_str = ', '.join(emotions[:-1]) + f", and {emotions[-1]}"
                summary_parts.append(f"you shared feeling {emotions_str}")
        
        # Validate topics actually exist in conversation
        validated_summary = []
        
        for part in summary_parts:
            # Check if the content of this part actually appears in conversation
            is_valid = False
            
            if conversation_history:
                conversation_text = ' '.join([
                    msg.get('content', '').lower() 
                    for msg in conversation_history 
                    if msg.get('role') == 'user'
                ])
                
                # Extract key words from summary part
                key_words = re.findall(r'\b\w{4,}\b', part.lower())
                
                # Check if at least one key word exists in conversation
                for word in key_words:
                    if word in conversation_text:
                        is_valid = True
                        break
            
            if is_valid:
                validated_summary.append(part)
        
        summary_parts = validated_summary
        
        if summary_parts:
            if len(summary_parts) == 1:
                summary = summary_parts[0] + "."
            elif len(summary_parts) == 2:
                summary = summary_parts[0] + ", and " + summary_parts[1] + "."
            else:
                summary = ", ".join(summary_parts[:-1]) + ", and " + summary_parts[-1] + "."
            
            memory_system = ConversationMemory()
            follow_up_question = memory_system._generate_dynamic_follow_up(facts)
            
            return f"I remember we've been chatting. {summary} {follow_up_question}"
        else:
            return "We've mostly just been exchanging greetings so far. What would you like to talk about?"
    
    return None