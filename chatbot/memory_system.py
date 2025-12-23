# memory_system.py - CONVERSATION MEMORY & CONTINUITY
"""
MEMORY SYSTEM for Snowfriend
Tracks conversation history and injects relevant context into system prompts
"""

import re
from typing import Dict, List, Set, Optional
from datetime import datetime

class ConversationMemory:
    """
    Tracks and summarizes conversation history for better continuity
    """
    
    def __init__(self):
        self.facts_extracted = {}  # Per-user facts
    
    def extract_conversation_facts(self, conversation_history: List[Dict]) -> Dict:
        """
        Extract key facts from conversation history
        Returns: {
            'topics_discussed': ['school', 'friends'],
            'people_mentioned': ['mom', 'classmate'],
            'emotions_expressed': ['sad', 'frustrated'],
            'first_user_message': "heyy here",
            'exchange_count': 5,
            'has_shared_problem': True,
            'recent_topics': ['last 3 topics']
        }
        """
        facts = {
            'topics_discussed': set(),
            'people_mentioned': set(),
            'emotions_expressed': set(),
            'first_user_message': None,
            'exchange_count': 0,
            'has_shared_problem': False,
            'recent_topics': [],
            'greetings_count': 0,
            'substantive_exchanges': 0,
            'last_3_user_messages': []
        }
        
        user_messages = [msg for msg in conversation_history if msg['role'] == 'user']
        
        # Track first user message
        if user_messages:
            facts['first_user_message'] = user_messages[0]['content']
        
        # Track exchange count
        facts['exchange_count'] = len(user_messages)
        
        # Track last 3 user messages
        facts['last_3_user_messages'] = [msg['content'] for msg in user_messages[-3:]]
        
        # Analyze each user message
        for msg in user_messages:
            content_lower = msg['content'].lower()
            
            # Count greetings vs substantive messages
            if self._is_greeting_message(content_lower) and len(content_lower.split()) <= 4:
                facts['greetings_count'] += 1
            else:
                facts['substantive_exchanges'] += 1
            
            # Extract topics
            facts['topics_discussed'].update(self._extract_topics(content_lower))
            
            # Extract people
            facts['people_mentioned'].update(self._extract_people(content_lower))
            
            # Extract emotions
            facts['emotions_expressed'].update(self._extract_emotions(content_lower))
            
            # Check if user has shared a problem
            if not facts['has_shared_problem']:
                facts['has_shared_problem'] = self._has_shared_problem(content_lower)
        
        # Convert sets to lists for JSON serialization
        facts['topics_discussed'] = list(facts['topics_discussed'])
        facts['people_mentioned'] = list(facts['people_mentioned'])
        facts['emotions_expressed'] = list(facts['emotions_expressed'])
        
        # Get recent topics (last 3 substantive messages)
        facts['recent_topics'] = self._get_recent_topics(user_messages[-3:])
        
        return facts
    
    def _is_greeting_message(self, text: str) -> bool:
        """Check if message is just a greeting"""
        greeting_patterns = [
            r'^\s*(hi|hello|hey|hola|sup|yo|hiya|howdy)\s*$',
            r'^\s*(hi|hello|hey|hola|sup)\s+(there|friend|snowfriend)\s*$',
        ]
        return any(re.match(pattern, text) for pattern in greeting_patterns)
    
    def _extract_topics(self, text: str) -> Set[str]:
        """Extract topics from text"""
        topics = set()
        
        # Education
        if any(word in text for word in ['school', 'class', 'homework', 'exam', 'teacher', 'student']):
            topics.add('school')
        
        # Social
        if any(word in text for word in ['friend', 'classmate', 'peer', 'social', 'party', 'hangout']):
            topics.add('social life')
        
        # Family
        if any(word in text for word in ['family', 'mom', 'dad', 'parent', 'sibling', 'brother', 'sister']):
            topics.add('family')
        
        # Work
        if any(word in text for word in ['work', 'job', 'boss', 'coworker', 'career', 'office']):
            topics.add('work')
        
        # Relationships
        if any(word in text for word in ['boyfriend', 'girlfriend', 'partner', 'dating', 'relationship', 'crush']):
            topics.add('relationships')
        
        # Mental health
        if any(word in text for word in ['anxiety', 'depression', 'stress', 'therapy', 'mental health']):
            topics.add('mental health')
        
        return topics
    
    def _extract_people(self, text: str) -> Set[str]:
        """Extract people mentioned"""
        people = set()
        
        people_patterns = [
            (r'\bmy (mom|mother|dad|father|parent)', 'parent'),
            (r'\bmy (friend|classmate|peer)', 'friend'),
            (r'\bmy (boyfriend|girlfriend|partner)', 'partner'),
            (r'\bmy (boss|manager|coworker)', 'coworker'),
            (r'\bmy (sibling|brother|sister)', 'sibling'),
            (r'\bmy (teacher|professor|instructor)', 'teacher'),
        ]
        
        for pattern, label in people_patterns:
            if re.search(pattern, text):
                people.add(label)
        
        return people
    
    def _extract_emotions(self, text: str) -> Set[str]:
        """Extract emotions expressed"""
        emotions = set()
        
        # Negative emotions
        if any(word in text for word in ['sad', 'depressed', 'down', 'upset']):
            emotions.add('sadness')
        
        if any(word in text for word in ['angry', 'mad', 'frustrated', 'annoyed']):
            emotions.add('anger')
        
        if any(word in text for word in ['anxious', 'worried', 'nervous', 'scared']):
            emotions.add('anxiety')
        
        if any(word in text for word in ['lonely', 'alone', 'isolated']):
            emotions.add('loneliness')
        
        # Positive emotions
        if any(word in text for word in ['happy', 'excited', 'glad', 'good']):
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
            content_lower = msg['content'].lower()
            topics = self._extract_topics(content_lower)
            
            if topics:
                recent_topics.extend(list(topics))
        
        return list(set(recent_topics))  # Remove duplicates
    
    def generate_memory_context(self, facts: Dict, user_name: str = None) -> str:
        """
        Generate memory context string for system prompt
        
        Returns a natural language summary of conversation history
        """
        context_parts = []
        
        # Basic conversation info
        exchange_count = facts.get('exchange_count', 0)
        substantive_exchanges = facts.get('substantive_exchanges', 0)
        greetings_count = facts.get('greetings_count', 0)
        
        if exchange_count > 0:
            context_parts.append(f"📊 CONVERSATION STATE:")
            context_parts.append(f"- You've exchanged {exchange_count} messages with {user_name or 'this user'}")
            
            if greetings_count >= 3:
                context_parts.append(f"- User has sent {greetings_count} greetings - they might just be saying hi casually")
            
            if substantive_exchanges > 0:
                context_parts.append(f"- You've had {substantive_exchanges} substantive exchanges beyond greetings")
        
        # First message memory
        first_msg = facts.get('first_user_message')
        if first_msg and exchange_count >= 2:
            context_parts.append(f"\n💬 FIRST MESSAGE:")
            context_parts.append(f'- User\'s first message was: "{first_msg}"')
            context_parts.append(f"- If they ask what they first said, tell them this exactly")
        
        # Last 3 messages
        last_3 = facts.get('last_3_user_messages', [])
        if len(last_3) >= 2:
            context_parts.append(f"\n💬 RECENT MESSAGES:")
            for i, msg in enumerate(last_3[-3:], 1):
                context_parts.append(f"  {i}. \"{msg}\"")
        
        # Topics discussed
        topics = facts.get('topics_discussed', [])
        if topics:
            context_parts.append(f"\n📚 TOPICS DISCUSSED:")
            context_parts.append(f"- {', '.join(topics)}")
        
        # People mentioned
        people = facts.get('people_mentioned', [])
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
            context_parts.append(f"- Don't keep asking 'what's going on?' - acknowledge what they've told you")
        
        # Instructions based on state
        if exchange_count >= 4 and substantive_exchanges == 0:
            context_parts.append(f"\n🎯 RESPONSE STRATEGY:")
            context_parts.append(f"- User keeps sending casual greetings - match their energy but gently invite deeper sharing")
            context_parts.append(f"- Example: 'Hey! Still just hanging around? Anything on your mind?'")
        
        if exchange_count >= 3:
            context_parts.append(f"\n🎯 MEMORY REQUIREMENT:")
            context_parts.append(f"- You MUST remember previous messages")
            context_parts.append(f"- If asked about past messages, reference them specifically")
            context_parts.append(f"- Don't keep asking the same questions")
        
        return "\n".join(context_parts)
    
    def should_reference_memory(self, user_message: str, facts: Dict) -> bool:
        """
        Determine if bot should explicitly reference past conversation
        
        Returns True if:
        - User asks about previous messages
        - User repeats a topic
        - Conversation is deep enough to show continuity
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
        
        # User repeating a topic
        recent_topics = facts.get('recent_topics', [])
        topics_discussed = facts.get('topics_discussed', [])
        
        # If user mentions a topic they've discussed before
        for topic in topics_discussed:
            if topic in msg_lower:
                return True
        
        # Deep enough conversation
        exchange_count = facts.get('exchange_count', 0)
        if exchange_count >= 5:
            return True
        
        return False


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def inject_memory_into_prompt(
    base_prompt: str,
    conversation_history: List[Dict],
    user_name: str = None
) -> str:
    """
    Inject memory context into system prompt
    
    Args:
        base_prompt: Original system prompt
        conversation_history: Full conversation history
        user_name: User's first name
    
    Returns:
        Enhanced prompt with memory context
    """
    memory_system = ConversationMemory()
    
    # Extract facts
    facts = memory_system.extract_conversation_facts(conversation_history)
    
    # Generate memory context
    memory_context = memory_system.generate_memory_context(facts, user_name)
    
    # Inject into prompt (before the main instructions)
    if memory_context:
        enhanced_prompt = f"{base_prompt}\n\n{'='*60}\n{memory_context}\n{'='*60}\n"
    else:
        enhanced_prompt = base_prompt
    
    return enhanced_prompt, facts


def check_if_memory_question(user_message: str, facts: Dict) -> Optional[str]:
    """
    Check if user is asking about previous conversation
    Returns a direct answer if it's a memory question
    
    Examples:
    - "what's the first message I sent?" → Returns first message
    - "do you remember what I said about school?" → Returns relevant memory
    """
    msg_lower = user_message.lower()
    
    # First message question
    first_msg_patterns = [
        r'what.{0,20}first (message|thing)',
        r'first (message|thing).{0,20}(i|you)',
        r'what did i (first|initially) (say|send|tell)',
    ]
    
    if any(re.search(pattern, msg_lower) for pattern in first_msg_patterns):
        first_msg = facts.get('first_user_message')
        if first_msg:
            return f'Your first message was: "{first_msg}"'
        else:
            return "I don't have a record of your first message."
    
    # General memory question
    memory_patterns = [
        r'do you remember',
        r'what did i (say|tell|mention)',
        r'earlier i (said|told|mentioned)',
    ]
    
    if any(re.search(pattern, msg_lower) for pattern in memory_patterns):
        # Return a summary of what they've discussed
        topics = facts.get('topics_discussed', [])
        people = facts.get('people_mentioned', [])
        emotions = facts.get('emotions_expressed', [])
        
        summary_parts = []
        
        if topics:
            summary_parts.append(f"You've talked about: {', '.join(topics)}")
        
        if people:
            summary_parts.append(f"You mentioned: {', '.join(people)}")
        
        if emotions:
            summary_parts.append(f"You've expressed feeling: {', '.join(emotions)}")
        
        if summary_parts:
            return "Here's what I remember: " + ". ".join(summary_parts) + "."
        else:
            return "We've mostly just been exchanging greetings so far."
    
    return None