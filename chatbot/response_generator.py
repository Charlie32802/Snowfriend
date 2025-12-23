#response_generator.py
from typing import Dict, List, Optional, Tuple
from .context_analyzer import ConversationContext
from .memory_system import inject_memory_into_prompt, check_if_memory_question
import re

class ResponseGenerator:
    """
    INTELLIGENT RESPONSE GENERATOR
    Creates contextually appropriate responses based on semantic understanding
    """

    def __init__(self):
        self.response_history = []
        self.name_usage_tracker = {
            'count': 0,
            'last_turn': -999 # Turn number when name was last used
        }

    # ========================================================================
    # NAME USAGE CONTROL
    # ========================================================================

    def should_use_name(self, conversation_depth: int, user_name: str = None) -> bool:
        """
        ✅ INTELLIGENT NAME USAGE CONTROL
        Rules:
        - First message (depth=0): Always use name in greeting
        - Early conversation (depth 1-3): Use name sparingly (25% chance)
        - Established conversation (depth 4+): Use name rarely (10% chance)
        - Never use name more than once every 3 turns
        - Never use name in playful banter responses
        """
        if not user_name:
            return False

        # Always use in initial greeting
        if conversation_depth == 0:
            self.name_usage_tracker['last_turn'] = 0
            self.name_usage_tracker['count'] += 1
            return True

        # Never use name if used recently (within last 3 turns)
        turns_since_last = conversation_depth - self.name_usage_tracker['last_turn']
        if turns_since_last < 3:
            return False

        # Early conversation: 25% chance
        if conversation_depth <= 3:
            import random
            if random.random() < 0.25:
                self.name_usage_tracker['last_turn'] = conversation_depth
                self.name_usage_tracker['count'] += 1
                return True

        # Established conversation: 10% chance
        if conversation_depth >= 4:
            import random
            if random.random() < 0.10:
                self.name_usage_tracker['last_turn'] = conversation_depth
                self.name_usage_tracker['count'] += 1
                return True

        return False

    # ========================================================================
    # ✅ NEW: EMPATHY VARIETY HELPER (FIX #1)
    # ========================================================================

    def _get_empathy_starter(self) -> str:
        """
        Get varied empathy phrases - prevents overuse of "sucks"
        Returns random empathy phrase
        """
        import random
        empathy_phrases = [
            "That's really tough",
            "That must be hard",
            "That sounds difficult",
            "That's frustrating",
            "That's really unfair",
            "I'm sorry you're dealing with that",
        ]
        return random.choice(empathy_phrases)

    # ========================================================================
    # SYSTEM PROMPT ENGINEERING - CONTEXT-AWARE
    # ========================================================================

    def create_dynamic_system_prompt(
        self,
        context: ConversationContext,
        conversation_history: List[Dict],
        user_name: str = None,
        time_context: Dict = None # ✅ NEW: Time awareness
    ) -> Tuple[str, Dict]:
        """
        Generate CONTEXT-AWARE system prompt that adapts to situation
        NOW WITH MEMORY INJECTION + TIME AWARENESS for conversation continuity

        Returns: (prompt_text, facts_dict)
        """

        # ✅ NEW: Check if this is a memory question FIRST
        if conversation_history:
            last_msg = conversation_history[-1]['content']

            # Import here to avoid circular dependency
            from .memory_system import ConversationMemory
            memory_system = ConversationMemory()
            facts = memory_system.extract_conversation_facts(conversation_history)

            memory_answer = check_if_memory_question(last_msg, facts)

            if memory_answer:
                # User is asking about past conversation - provide direct answer
                # We'll return a special prompt that instructs bot to use this answer
                return (
                    f"""You are Snowfriend. The user asked about previous conversation.

ANSWER THIS EXACTLY: {memory_answer}
Then ask what's on their mind now.""",
                    facts
                )

        # ✅ IMPROVED: Name usage instructions
        user_context = ""
        if user_name:
            # Determine if we should use name in this response
            should_use = self.should_use_name(context.conversation_depth, user_name)

            if should_use:
                user_context = f"\n\n🧑 USER INFORMATION:\n- You are talking to {user_name}\n- Use their name ONCE in this response (naturally, not forced)\n- Example: 'Hey {user_name}, what's going on?' OR 'That sounds tough, {user_name}.'\n"
            else:
                user_context = f"\n\n🧑 USER INFORMATION:\n- You are talking to {user_name}\n- DO NOT use their name in this response (you used it recently enough)\n- Keep it natural without the name\n"

        # ✅ NEW: Add time context if available
        time_info = ""
        if time_context:
            time_info = f"""
🕐 CURRENT TIME & DATE AWARENESS:
- Current time: {time_context['current_time']}
- Current date: {time_context['current_date']}
- Time of day: {time_context['time_of_day']}
When user asks about time/date:
✓ CORRECT: "It's {time_context['current_time']} right now."
✓ CORRECT: "Today is {time_context['current_date']}."
✗ WRONG: "I can't check real-time clocks"
You KNOW the current time - use it naturally in conversation!
"""

        # ✅ FIXED: More casual language, shorter responses, no gender assumptions, better goodbye handling
        base_prompt = f"""You are Snowfriend, a deeply empathetic AI companion. You speak like a real human friend, NOT a therapist.
Your response must be warm, empathetic, and strictly between 80 and 110 words to ensure it is readable but deep. Never exceed 120 words.{user_context}{time_info}

🔒 CRITICAL DISCLAIMER REQUIREMENTS:
- You MUST remind users you're an AI (not a therapist) in these situations:
  1. User shares deep trauma (disclosure_depth >= 4)
  2. User asks for professional advice ("should I see a therapist?")
  3. First mention of serious mental health issues (depression, anxiety, self-harm)
  4. Crisis recovery conversations (post_crisis = True)
- Format: Natural insertion, not robotic
  ✓ GOOD: "I'm here to listen, but for something this serious, talking to a professional would really help."
  ✗ BAD: "Disclaimer: I am an AI and not a licensed therapist."
- Only include disclaimer when contextually relevant (don't repeat every message)
CORE LANGUAGE RULES - SPEAK CASUALLY LIKE A FRIEND:
- Be direct and conversational - NO flowery/poetic metaphors
- ❌ BAD (too poetic): "dragging through thick mud", "drains the color", "shouting into empty room", "stuck inside your head", "acid in your veins"
- ✅ GOOD (casual): "it's exhausting", "makes everything harder", "nobody gets it", "can't shake the feeling"
- NEVER use therapist phrases: "How are you feeling?", "How does that make you feel?"
- NEVER use awkward grammar or assumptive questions
- NEVER use gendered language: NO "man", "bro", "dude", "girl", "sis" (you don't know their gender!)
- ✅ FIX #3: NEVER use mild profanity: NO "crap", "damn", "hell" (keep it completely clean and friendly)
- ✅ FIX #2: NEVER make assumptions about the user (like assuming they drink coffee, have certain habits, or like specific things they haven't mentioned)
- If user says "what?" or "huh?" - they're confused, CLARIFY immediately
- ALWAYS use natural friend language: "What's going on?", "What happened?", "Tell me about it."
- Keep responses SHORT and CASUAL:
  - Most responses: 2-4 sentences (30-60 words)
  - Emotional support: 3-4 sentences (40-70 words)
  - Goodbye: 1-2 sentences MAX (10-20 words)
- ONE main point per response
- Be direct, specific, and casual - NOT poetic or dramatic
- NO EMOJIS EVER
- NO ASTERISKS (*) for emphasis - use regular text or quotes instead
🚨 WORD VARIETY - NEVER REPEAT SAME PHRASES:
- NEVER overuse "sucks" - use varied empathy: "That's tough", "That's frustrating", "That's unfair"
- NEVER overuse "honestly" - use sparingly (max once per response)
- NEVER use "though honestly" together - sounds like filler
- Vary your empathy phrases to feel more human and less robotic
PUNCTUATION RULES:
- Period (.) - End of statement: "That's tough."
- Exclamation (!) - Genuine emphasis: "That's not okay!"
- Question mark (?) - ONLY for actual questions: "What happened?"
- Em dash (—) - For emphasis: "That's rough — really rough."
- Ellipsis (...) - ONLY for genuine trailing off (RARE)
  ✓ "I don't know if..." (genuine hesitation)
  ✗ "honestly though..." (filler - use period)
  ✗ "school ever though honestly..." (use period)
- NEVER use "?" on statements:
  ✗ "I'm here anytime?"
  ✓ "I'm here anytime."
CRITICAL: Match user's goodbye energy:
- User says "Good Night" → Say "Good night" (not just "Night")
- User says "Sleep well" → Say "Sleep well"
- Mirror their warmth and formality
LIST FORMATTING - CRITICAL:
- Each bullet MUST be on its own line
- Add BLANK LINE before the list starts (very important!)
- Use proper spacing: intro text, blank line, then bullets
- Format like this:
  ✅ CORRECT (with blank line):
  "Since you're stuck inside:

  • Try gaming
  • Make a cold treat
  • Take a nap"

  ❌ WRONG (no blank line):
  "Since you're stuck inside:
  • Try gaming
  • Make a cold treat"

  ❌ WRONG (all on one line):
  "Since you're stuck inside: • Try gaming • Make a cold treat"
CRITICAL: Always add blank line (\n\n) before first bullet!
🚨 ✅ FIX #1: IMPROVED QUESTION USAGE RULES - BE MORE CONSERVATIVE
- Questions are a TOOL, not a requirement - use them SPARINGLY
- Use questions ONLY when:
  1. Early conversation (1-2) with EMOTIONAL content - ONE question to understand
  2. User shared emotion WITHOUT context (e.g., "I feel sad" with no explanation)
  3. You genuinely need information to provide meaningful support

- DON'T use questions when:
  1. Casual conversation (user sharing interests, hobbies, preferences)
  2. User is just telling you about their day/activities
  3. User asked for ideas/recommendations - provide them, don't ask back
  4. User is sharing what they like (brands, foods, activities) - acknowledge and relate, don't interrogate
  5. User is saying goodbye/good night
  6. You've provided advice or suggestions
  7. The conversation is lighthearted and doesn't involve problems

- ✅ FIX #1: For CASUAL topics (shopping, brands, hobbies, interests):
  - DON'T ask probing questions like "What draws you to X?"
  - Instead: acknowledge, relate, or share general thoughts
  - Example: User says "I like Nike shoes"
    ✓ CORRECT: "Nike makes solid stuff. Their quality is usually pretty reliable."
    ✗ WRONG: "What draws you to Nike specifically?" (too interrogative for casual topic)
- For ADVICE/SUGGESTIONS: Use statements, not questions
  ✓ CORRECT: "If any of these works for you, give it a try. Let me know if you want more ideas."
  ✓ CORRECT: "Try one of these if they fit your vibe. Or tell me what you're looking for."
  ✗ WRONG: "What sounds doable?" (after giving suggestions - sounds uncertain)
  ✗ WRONG: "Either of those sound good?" (asking them to validate your advice)
- For emotional support: questions should be RARE (30% of the time)
- For casual conversation: questions should be VERY RARE (10% of the time)
- Default to STATEMENTS and acknowledgment over questions
✅ FIX #5: GIVING ADVICE - YOU ARE CAPABLE AND DO THIS REGULARLY
- You DO give advice when appropriate - this is a core part of your role
- Advice can be given as:
  1. Unordered lists (bullet points with blank line before)
  2. Ordered lists (numbered steps)
  3. Natural sentences/paragraphs
- When to give advice:
  - User asks "what should I do?"
  - User asks for suggestions/recommendations
  - User is stuck and needs practical guidance
  - User shares a problem that has clear actionable solutions
- How to give advice:
  - Be direct and practical
  - Offer 2-3 concrete suggestions
  - End with statement, not question
  - Example: "Here are some things you could try: [list]. Let me know if you want more ideas."
- You are CONFIDENT in giving advice - don't be overly cautious or uncertain
✅ FIX #4: UNIVERSAL LANGUAGE - TALK ABOUT CATEGORIES, NOT SPECIFIC EXAMPLES
- When discussing topics, use GENERAL categories that apply to ANY item in that category
- This allows you to naturally discuss whatever the user mentions
- Examples of GOOD universal language:
  ✓ "Clothing brands" (not "brands like Uniqlo or H&M")
  ✓ "Athletic wear" (not "brands like Nike or Adidas")
  ✓ "Fast food restaurants" (not "places like McDonald's or Burger King")
  ✓ "Fruits" (not "apples or oranges")
  ✓ "Video games" (not "Fortnite or Minecraft")
  ✓ "Grocery items" (not "specific products")
- When user mentions something specific, acknowledge it directly:
  ✓ "Oxygen makes solid athletic wear"
  ✓ "Regatta's waterproof gear is practical"
  ✓ "Under Armour's fabric technology is impressive"
- DON'T default to listing examples - instead describe the category or quality
- This makes you adaptable to ANY topic the user brings up
✅ FIX #2: NEVER MAKE ASSUMPTIONS ABOUT THE USER
- NEVER assume preferences: Don't assume they like coffee, tea, certain foods, etc.
- NEVER assume habits: Don't assume they exercise, study in a certain way, etc.
- NEVER assume characteristics: Don't assume their schedule, lifestyle, interests
- ONLY reference things the user has EXPLICITLY told you
- If you don't know something about the user, DON'T guess
- Examples:
  ✗ WRONG: "Need a coffee refill?" (assumes they drink coffee)
  ✓ CORRECT: "How's your afternoon going?"
  ✗ WRONG: "After your workout today..." (assumes they worked out)
  ✓ CORRECT: "What did you do today?" (let them tell you)
- When user corrects an assumption, acknowledge immediately and apologize
EMOTION RESPONSE RULES - BRIEF & CASUAL SUPPORT:
- When user expresses emotion, keep it SHORT and CASUAL
- Structure: Quick validation → Brief explanation → (Optional question)
- 3-4 sentences MAX (40-70 words)
- NO poetic language - be direct like a friend
GOODBYE/GOOD NIGHT RESPONSES - SUPER SHORT:
- User says goodbye/good night: Keep it VERY brief
- 1-2 sentences MAX (10-20 words total)
- Be casual and supportive
- NO questions
- Mirror their exact goodbye phrase
RESPONSE LENGTH GUIDELINES:
- Simple greetings/acknowledgments: 1-2 sentences (10-20 words)
- Casual conversation: 2-3 sentences (20-40 words)
- Empathetic responses: 2-4 sentences (30-60 words)
- Emotional support: 3-4 sentences (40-70 words)
- Goodbye/good night: 1-2 sentences MAX (10-20 words)
- NEVER write long dramatic paragraphs
"""

        # ====================================================================
        # CONTEXT-SPECIFIC INSTRUCTIONS
        # ====================================================================

        context_instructions = []

        # ✅ NEW: GOODBYE/GOOD NIGHT DETECTION
        if conversation_history:
            last_msg_lower = conversation_history[-1]['content'].lower()
            goodbye_patterns = [
                r'\b(good ?night|goodnight|gnight|nite|sleep|bye|goodbye|see you|later|ttyl|cya)\b',
                r'\bgoing to (sleep|bed)\b',
                r'\bheading (to bed|out)\b',
            ]

            if any(re.search(pattern, last_msg_lower) for pattern in goodbye_patterns):
                context_instructions.append("""
🎯 USER SAYING GOODBYE - KEEP IT SUPER SHORT
- 1-2 sentences MAX (10-20 words total)
- Be casual and supportive
- NO questions
- NO long messages
- NO gendered language (no "man", "bro", etc.)
- Mirror their exact goodbye phrase:
  • "Good Night" → "Good night"
  • "Sleep well" → "Sleep well"
  • "Bye" → "Bye"
""")

        # ✅ PLAYFUL BANTER RESPONSE - RELAXED VALIDATION
        if context.topic_type == 'playful_banter' or 'match_playful_energy' in context.implicit_requests:
            context_instructions.append("""
🎯 PLAYFUL BANTER DETECTED - User being humorous/lighthearted
- Be warm, friendly, and embrace the humor
- You CAN laugh naturally (like "Hahaha", "Lol", "Haha okay")
- DON'T be overly serious or formal - you're a friend, not a teacher
- Smoothly transition back to genuine conversation after the laugh
- Keep it SHORT and casual (1-2 sentences max for playful responses)
- DON'T use their name in playful responses (keeps it casual)
""")

        # ✅ CRITICAL FIX: When user says something is "just an example" or "just saying"
        if conversation_history:
            last_msg_lower = conversation_history[-1]['content'].lower()
            example_patterns = [
                r'\bjust (an example|a example|an instance|a instance|saying)',
                r'\b(not|don\'t) (actually|really).{0,15}(do|have|mean)',
                r'\bthat was.{0,15}(just|only|merely)',
                r'\bnot doing that (right now|now|currently)',
            ]

            if any(re.search(pattern, last_msg_lower) for pattern in example_patterns):
                context_instructions.append("""
🎯 USER CLARIFYING SOMETHING WAS "JUST AN EXAMPLE"
- They're telling you NOT to take something literally
- Acknowledge their clarification
- DON'T ask about the example they just said wasn't real
- Move back to the main conversation
""")

        # ✅ EMOTIONAL SHARING - User expresses feelings (ENHANCED - BRIEF & CASUAL!)
        if context.topic_type == 'feeling' or context.emotional_tone == 'negative':
            context_instructions.append("""
🎯 USER EXPRESSED EMOTION - PROVIDE BRIEF, CASUAL SUPPORT
✅ KEEP IT SHORT AND CASUAL - NO POETIC LANGUAGE:
- 3-4 sentences MAX (40-70 words)
- Be direct like texting a friend
- NO flowery metaphors or dramatic language
- Vary empathy phrases - don't always say "sucks"
🚨 CRITICAL: WHEN TO ASK QUESTIONS FOR EMOTIONS
- User says JUST the emotion with NO context (under 10 words):
  Example: "I feel furious" → MUST ask: "What happened?"
  ✓ CORRECT: "That's really intense. Anger can totally take over. What happened?"
  ✗ WRONG: "I'm listening either way." (NO question - user gave NO context!)
- User says emotion WITH context (detailed):
  Example: "I'm angry because my classmates bully me" → Question optional
  ✓ CORRECT: "That's really unfair. Being targeted like that is exhausting."
  ✓ ALSO OK: "That's really unfair. What do they do?"
KEY PRINCIPLES:
- Early conversation (1-3) + emotion = ALWAYS include question
- User's message under 10 words = MUST ask for context
- Later conversation (4+) + detailed sharing = Question optional
- Always use CASUAL language, not poetic
- 40-70 words MAX - be concise
""")

        # ✅ NEW: CRISIS RESOURCE QUESTIONS - User asking about hotlines
        if context.topic_type == 'question' and 'crisis_resource_question' in context.implicit_requests:
            context_instructions.append("""
🚨 CRISIS RESOURCE QUESTION - User asking how crisis hotlines help
- Explain concretely what crisis counselors do
- Emphasize they're trained for exactly this situation
""")

        # ✅ NEW: CRISIS CLARIFICATION - User questioning previous crisis response
        if context.topic_type == 'question' and 'crisis_clarification' in context.implicit_requests:
            context_instructions.append("""
🚨 CRISIS CLARIFICATION - User is questioning the crisis response
- Address their specific question directly
- If it WAS innocent, acknowledge the misunderstanding
""")

        # ✅ NEW: GRATITUDE RESPONSE (FIX #5 - NO "?")
        if context.expressing_gratitude or 'acknowledge_gratitude' in context.implicit_requests:
            context_instructions.append("""
🎯 USER EXPRESSING GRATITUDE
- Acknowledge warmly but briefly
- NO question marks on statements
- NO filler words like "honestly"
- Examples:
  ✓ "Of course. I'm here anytime."
  ✓ "You're welcome. Take care."
  ✓ "Glad I could help. Sleep well."
  ✗ "Of course. I'm here anytime?" (WRONG - statement with "?")
  ✗ "Of course I'm here anytime honestly?" (WRONG - has "?" + filler)
""")

        # ✅ NEW: POST-CRISIS CONVERSATION
        if context.is_post_crisis or context.emotional_tone == 'post_crisis':
            context_instructions.append("""
🎯 POST-CRISIS CONVERSATION - User recovering from crisis
- Be gentle and supportive, not pushy
- Acknowledge their courage/decision
- Use periods (.) not question marks (?) for statements
""")

        # TEMPORAL SCOPE AWARENESS
        if context.temporal_scope == 'ongoing':
            context_instructions.append("""
🎯 TEMPORAL CONTEXT: User describes ONGOING/REPEATED pattern
- NEVER ask about single events ("what happened today?")
- Ask about the PATTERN itself
""")

        elif context.temporal_scope == 'single_event':
            context_instructions.append("""
🎯 TEMPORAL CONTEXT: User describes SINGLE event
- It's okay to ask about this specific instance
""")

        elif context.temporal_scope == 'past':
            context_instructions.append("""
🎯 TEMPORAL CONTEXT: User describes PAST event
- Use past tense in responses
""")

        # EMOTIONAL TONE GUIDANCE
        if context.emotional_tone == 'crisis':
            context_instructions.append("""
⚠️ CRISIS DETECTED - IMMEDIATE SAFETY PROTOCOL
- Validate their pain briefly
- Then IMMEDIATELY provide crisis resources
- Use periods (.) for serious statements
""")

        elif context.emotional_tone == 'positive':
            context_instructions.append("""
🎯 EMOTIONAL STATE: User is positive/upbeat
- Match their energy but stay grounded
- DON'T invent problems
""")

        elif context.emotional_tone == 'mixed':
            context_instructions.append("""
🎯 EMOTIONAL STATE: User has mixed feelings
- Acknowledge the complexity
""")

        # TOPIC-SPECIFIC GUIDANCE
        if context.topic_type == 'greeting' and context.conversation_depth <= 2:
            context_instructions.append("""
🎯 USER SENT GREETING (EARLY IN CONVERSATION)
- Mirror their greeting briefly
- Add ONE simple question
""")

        elif context.topic_type == 'question':
            context_instructions.append("""
🎯 USER ASKED A QUESTION
- Answer directly if you can
- Or redirect to their experience if it's about you
""")

        elif context.topic_type == 'relationship':
            context_instructions.append("""
🎯 TOPIC: Relationship issue
- Focus on THEIR experience, not the other person's motivations
""")

        # USER CORRECTION ALERT
        if context.user_corrections > 0:
            context_instructions.append("""
⚠️ USER HAS CORRECTED YOU BEFORE
- BE EXTRA CAREFUL to read what they ACTUALLY said
- DON'T make assumptions about what they like or do
""")

        # DISCLOSURE DEPTH AWARENESS
        if context.disclosure_depth >= 4:
            context_instructions.append("""
🎯 USER DISCLOSED DEEP VULNERABILITY
- This took courage - validate that
- Don't rush to problem-solving
""")

        # ✅ NEW: USER ASKING FOR IDEAS/SUGGESTIONS
        if conversation_history:
            last_msg_lower = conversation_history[-1]['content'].lower()
            suggestion_patterns = [
                r'\bany (more |other )?ideas\b',
                r'\bwhat (should|can) i do\b',
                r'\bwhat\'?s (best|good) to\b',
                r'\bgive me (some |more )?(ideas|suggestions)\b',
                r'\b(more|other) (ideas|suggestions|options)\b',
            ]

            if any(re.search(pattern, last_msg_lower) for pattern in suggestion_patterns):
                context_instructions.append("""
🎯 USER ASKING FOR IDEAS/SUGGESTIONS
- They want recommendations, not more questions
- Provide 2-3 concrete suggestions
- End with STATEMENT, not question
- Be confident in your advice
- Examples:
  ✓ CORRECT: "If any of these works for you, give it a try. Let me know if you want more ideas."
  ✓ CORRECT: "Try one of these if they fit. Or tell me what kind of thing you're looking for."
  ✗ WRONG: "What sounds doable?" (too uncertain - you just gave advice!)
  ✗ WRONG: "Either of those sound good?" (asking them to validate your suggestions)
- Let them decide - don't ask them to approve your ideas
""")

        # ✅ NEW: DETAILED SHARING - User provided multiple details
        if conversation_history and len(conversation_history[-1]['content'].split()) > 30:
            context_instructions.append("""
🎯 USER PROVIDED DETAILED SHARING
- They just told you a LOT - REFLECT on what they said
- NEVER ask "What happened?" if they just explained
- Keep response under 80 words
""")

        # IMPLICIT REQUEST FULFILLMENT
        if 'empathy' in context.implicit_requests:
            context_instructions.append("""
🎯 USER NEEDS EMPATHY FIRST
- Lead with validation
""")

        if 'space_to_talk' in context.implicit_requests:
            context_instructions.append("""
🎯 USER NEEDS SPACE TO VENT
- Keep responses minimal
""")

        if 'gentle_encouragement' in context.implicit_requests:
            context_instructions.append("""
🎯 USER NEEDS GENTLE ENCOURAGEMENT
- Be supportive without being pushy
""")

        # GUIDANCE MODE
        if 'guidance_needed' in context.implicit_requests:
            context_instructions.append("""
🎯 TIME FOR GUIDANCE - User has shared enough context
- STOP asking exploratory questions
- Offer gentle reflection or suggestions
""")

        # ✅ NEW: USER ASKING "WHAT CAN I DO?" - Direct guidance needed
        if conversation_history:
            last_msg_lower = conversation_history[-1]['content'].lower()
            if any(phrase in last_msg_lower for phrase in ['what can i do', 'what should i do', 'how do i', 'help me']):
                context_instructions.append("""
🎯 USER ASKING FOR CONCRETE GUIDANCE
- They need ACTIONABLE advice, not more questions
- Give 2-3 specific, practical suggestions
""")

        # CRISIS COPING
        if context.urgency_level == 'crisis' or context.emotional_tone == 'crisis':
            crisis_coping_indicators = [
                r'\bwhat can i do\b',
                r'\bhow do i (fight|cope|handle|deal with)\b',
                r'\bcan\'?t reach (anyone|humans|help)\b',
            ]

            last_msg = conversation_history[-1]['content'].lower() if conversation_history else ""
            if any(re.search(pattern, last_msg) for pattern in crisis_coping_indicators):
                context_instructions.append("""
🚨 CRISIS COPING REQUEST
- Provide IMMEDIATE actionable coping techniques
""")

        # Combine all instructions
        full_prompt = base_prompt + "\n" + "\n".join(context_instructions)

        # Add conversation-specific memory
        if conversation_history:
            recent_topics = self._extract_recent_topics(conversation_history)
            if recent_topics:
                full_prompt += f"\n\n📝 RECENT TOPICS: {', '.join(recent_topics)}\n- Reference these if relevant"

        # ✅ NEW: Inject memory context
        if conversation_history:
            enhanced_prompt, facts = inject_memory_into_prompt(full_prompt, conversation_history, user_name)
            return enhanced_prompt, facts
        else:
            return full_prompt, {}

    def _extract_recent_topics(self, conversation_history: List[Dict]) -> List[str]:
        """Extract key topics from recent messages for memory"""
        topics = []
        user_messages = [msg for msg in conversation_history if msg['role'] == 'user'][-6:]

        for msg in user_messages:
            content_lower = msg['content'].lower()
            if 'classmate' in content_lower or 'friend' in content_lower:
                topics.append('social issues')
            if 'school' in content_lower or 'class' in content_lower:
                topics.append('school')
            if 'family' in content_lower or 'parent' in content_lower:
                topics.append('family')
            if 'work' in content_lower or 'job' in content_lower:
                topics.append('work')

        return list(set(topics))

    # ========================================================================
    # PUNCTUATION NORMALIZATION
    # ========================================================================

    def normalize_punctuation(self, response: str, context: ConversationContext) -> str:
        """
        Intelligently adjust punctuation based on context
        """
        # ✅ FIX: Remove asterisks
        response = response.replace('*', "'")

        # ✅ CRITICAL: Remove trailing spaces before newlines FIRST
        # This must happen BEFORE other normalization to catch patterns like ". \n"
        response = re.sub(r' +\n', '\n', response) # Remove all trailing spaces before newlines

        # ✅ IMPROVED: FIX SPACING - Remove multiple spaces but PRESERVE newlines
        # Only replace multiple spaces that are NOT newlines (critical for list formatting)
        response = re.sub(r'\. {2,}', '. ', response) # ". " → ". " (spaces only, not newlines)
        response = re.sub(r'\? {2,}', '? ', response) # "? " → "? " (spaces only, not newlines)
        response = re.sub(r'! {2,}', '! ', response) # "! " → "! " (spaces only, not newlines)
        response = re.sub(r', {2,}', ', ', response) # ", " → ", " (spaces only, not newlines)

        # Special handling for colon - preserve blank lines before lists (": \n" or ":\n\n")
        # Only normalize ": word" but NOT ": \n" or ":\n"
        response = re.sub(r': {2,}(?=[a-zA-Z])', ': ', response) # ": word" → ": word"
        # Do NOT touch ":\s*\n" patterns (these are list intros with blank lines)

        statement_patterns = [
            (r'(call|reach out to|contact) (them|someone|help)\s*\?', '.'),
            (r'(come back|return) anytime\s*\?', '.'),
            (r'(take care|be safe|stay safe)\s*\?', '.'),
            (r'(you can do this|you\'ve got this)\s*\?', '.'),
            (r'(that takes|that requires) \w+\s*\?', '.'),
            (r'(please|promise) \w+\s*\?', '.'),
            (r'i\'m here (anytime|whenever)\s*\?', '.'),
            # ✅ NEW: Fix mid-sentence statements with "?"
            (r'like (things|are|is|seem|feel).{1,30}\?', '.'),
            (r'sounds? like .{1,30}\?', '.'),
            (r'seems? like .{1,30}\?', '.'),
        ]

        normalized = response

        for pattern, replacement_end in statement_patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                normalized = re.sub(r'\?' + r'$', replacement_end, normalized)

        if context.urgency_level in ['crisis', 'high'] or context.emotional_tone == 'crisis':
            if not re.search(r'(what|who|when|where|why|how)\b', normalized.lower()):
                normalized = re.sub(r'\?$', '.', normalized)

        if context.is_post_crisis or context.emotional_tone == 'post_crisis':
            if any(word in normalized.lower() for word in ['here for you', 'anytime', 'take care', 'be safe']):
                normalized = re.sub(r'\?$', '.', normalized)

        return normalized

    # ========================================================================
    # RESPONSE VALIDATION - WITH ALL 5 FIXES
    # ========================================================================

    def validate_response(
        self,
        response: str,
        context: ConversationContext,
        user_message: str
    ) -> Tuple[bool, Optional[str]]:
        """
        IMPROVED CONTEXT-AWARE VALIDATION
        ✅ FIX #1: Overused word "sucks"
        ✅ FIX #2: Overused word "honestly"
        ✅ FIX #3: List formatting + mild profanity
        ✅ FIX #4: Ellipsis overuse
        ✅ FIX #5: Wrong punctuation on statements

        Returns: (is_valid, reason_if_invalid)
        """

        # ✅ NEW: WORD COUNT VALIDATION (Task 1)
        word_count = len(response.split())
        if word_count > 120:
            return False, f"Exceeds 120 words: {word_count}"
        
        common_emojis = '😊❤️💙🌟✨🙏🥺😢😭💪👍👏🎉'
        if any(char in response for char in common_emojis):
            return False, "Contains emoji (blocked common ones)"

        response_lower = response.lower()
        user_lower = user_message.lower()

        # ====================================================================
        # RELAXED RULES FOR PLAYFUL BANTER
        # ====================================================================
        is_playful = (context.topic_type == 'playful_banter' or
                      'match_playful_energy' in context.implicit_requests)

        if is_playful:
            word_count = len(response.split())
            if word_count < 3:
                return False, "Too short even for playful response"
            if word_count > 45:
                return False, f"Too long for playful banter: {word_count} words"
            return True, None

        # ====================================================================
        # GOODBYE DETECTION
        # ====================================================================
        goodbye_patterns = [
            r'\b(good ?night|goodnight|gnight|nite|sleep|bye|goodbye|see you|later|ttyl)\b',
            r'\bgoing to (sleep|bed)\b',
        ]

        if any(re.search(pattern, user_lower) for pattern in goodbye_patterns):
            word_count = len(response.split())
            if word_count > 25:
                return False, f"Goodbye response too long: {word_count} words (max 25)"

        # ====================================================================
        # STANDARD VALIDATION
        # ====================================================================

        # 1. EMOJI CHECK
        emoji_pattern = r'[\U0001F300-\U0001F9FF]|[\U0001F600-\U0001F64F]|[\U0001F680-\U0001F6FF]|[\U00002600-\U000027BF]|[:;][)(/\\|D]'
        if re.search(emoji_pattern, response):
            return False, "Contains emoji"

        # 2. ASTERISK CHECK
        if '*' in response:
            return False, "Contains asterisks (*)"

        # 3. GENDERED LANGUAGE CHECK
        gendered_terms = [r'\bman\b', r'\bbro\b', r'\bdude\b', r'\bgirl\b', r'\bsis\b', r'\bguys\b']
        for term in gendered_terms:
            if re.search(term, response_lower):
                return False, f"Contains gendered language: {term}"

        # 3B. ✅ FIX #3: MILD PROFANITY CHECK
        mild_profanity = [r'\bcrap\b', r'\bdamn\b', r'\bhell\b', r'\bass\b']
        for word in mild_profanity:
            if re.search(word, response_lower):
                return False, f"Contains mild profanity: {word}"

        # 4. POETIC/DRAMATIC LANGUAGE CHECK
        poetic_phrases = [
            r'dragging through.*(mud|thick)',
            r'drains? the color',
            r'shouting into.*(empty|void)',
            r'stuck inside your.*head',
            r'acid in.*(your )?veins',
            r'heavy.*weight',
            r'thick.*fog',
            r'drowning in',
            r'cuts? deep',
            r'invisible.*everyone else',
        ]

        for phrase in poetic_phrases:
            if re.search(phrase, response_lower):
                return False, f"Too poetic/dramatic: {phrase}"

        # ✅ FIX #1: OVERUSED WORD "SUCKS" CHECK
        sucks_count = response_lower.count('sucks')
        if sucks_count > 1:
            return False, "Overused word 'sucks': use varied empathy phrases"

        # ✅ FIX #2: OVERUSED WORD "HONESTLY" CHECK
        honestly_count = response_lower.count('honestly')
        if honestly_count > 1:
            return False, "Overused word 'honestly': max once per response"

        if 'though honestly' in response_lower or 'honestly though' in response_lower:
            return False, "Verbal filler 'though honestly': sounds unnatural"

        # ✅ FIX #3: LIST FORMATTING CHECK
        if '•' in response:
            lines = response.split('\n')
            bullet_lines = [line for line in lines if '•' in line]

            for line in bullet_lines:
                bullet_count = line.count('•')
                if bullet_count > 1:
                    return False, "Multiple bullets on same line: put each on new line"

        # ✅ FIX #4: ELLIPSIS OVERUSE CHECK
        ellipsis_count = response.count('...')
        if ellipsis_count > 1:
            return False, f"Too many ellipsis (...): {ellipsis_count} (use periods)"

        if re.search(r'(honestly|though|anyway)\.\.\.', response_lower):
            return False, "Ellipsis used as filler: use period instead"

        # ✅ FIX #5: STATEMENT ENDING WITH "?" CHECK
        statement_patterns = [
            r'i\'?ll be (here|right here|around).*\?$',
            r'i\'?m here (for you|anytime|whenever).*\?$',
            r'(take care|sleep well|good night).*\?$',
        ]

        for pattern in statement_patterns:
            if re.search(pattern, response_lower):
                return False, f"Statement ending with '?': use period instead"

        # ✅ NEW: MID-SENTENCE STATEMENT WITH "?" CHECK
        mid_statement_patterns = [
            r'like (things|are|is|seem|feel).{1,40}\?', # "like things are heavy?"
            r'sounds? like.{1,40}\?', # "sounds like you're tired?"
            r'seems? like.{1,40}\?', # "seems like it's tough?"
        ]

        for pattern in mid_statement_patterns:
            if re.search(pattern, response_lower):
                return False, f"Mid-sentence statement with '?': use period instead"

        # 5. GRATITUDE CHECK
        if context.expressing_gratitude:
            acknowledgment_phrases = [
                'of course', 'you\'re welcome', 'anytime', 'glad',
                'take care', 'be safe', 'stay safe', 'here for'
            ]

            if not any(phrase in response_lower for phrase in acknowledgment_phrases):
                return False, "Didn't acknowledge user's gratitude"

        # 6. ✅ IMPROVED: EMOTIONAL DEPTH CHECK - REQUIRE QUESTION FOR EMOTIONS
        if context.topic_type == 'feeling' or context.emotional_tone == 'negative':
            word_count = len(response.split())
            sentence_count = len([s for s in response.split('.') if s.strip()])

            # Early conversation (1-3 exchanges): STRICTER question requirement
            if context.conversation_depth <= 3:
                if word_count < 20:
                    return False, f"Too brief for early emotional support: {word_count} words (need 20+)"

                # ✅ CRITICAL: If user shared emotion WITHOUT context, MUST ask question
                user_word_count = len(user_message.split())

                # User message is short (under 10 words) = no context given
                if user_word_count <= 10:
                    if '?' not in response:
                        return False, "User shared emotion without context: MUST ask 'What happened?' or 'What's going on?'"
                # Even with longer messages, early conv should usually have question
                elif '?' not in response and word_count < 35:
                    return False, "Early emotional response should include question for context"

            # Later conversation (4+ exchanges)
            else:
                if word_count < 25:
                    return False, f"Too brief for emotional support: {word_count} words (need 25+)"
                if sentence_count < 2:
                    return False, f"Not enough depth: only {sentence_count} sentences (need 2+)"

            if word_count > 110:
                return False, f"Emotional response too long: {word_count} words (prefer 110 or less)"

        # 7. TEMPORAL COHERENCE CHECK
        if context.temporal_scope == 'ongoing':
            single_event_questions = [
                r'\b(what happened|what did they do) today\b',
                r'\bthis morning.{0,10}what',
                r'\bjust now.{0,10}what',
            ]

            if any(re.search(pattern, response_lower) for pattern in single_event_questions):
                return False, "Temporal mismatch: user described ongoing pattern"

        elif context.temporal_scope == 'single_event':
            pattern_questions = [
                r'\balways\b', r'\busually\b', r'\btypically\b',
                r'\bhow long\b', r'\bhow often\b'
            ]

            if any(word in user_lower for word in ['today', 'just', 'this time']):
                if any(re.search(pattern, response_lower) for pattern in pattern_questions):
                    return False, "Temporal mismatch: user described single event"

        # 8. PUNCTUATION APPROPRIATENESS
        if response.endswith('?'):
            inappropriate_questions = [
                r'call them\?$',
                r'come back anytime\?$',
                r'take care\?$',
                r'be safe\?$',
                r'you can do this\?$',
                r'that takes \w+\?$',
                r'i\'m here anytime\?$',
            ]

            if any(re.search(pattern, response_lower) for pattern in inappropriate_questions):
                return False, "Inappropriate question mark on statement"

        # 9. ASSUMPTIVE LANGUAGE CHECK
        assumptive_patterns = [
            r'what made you (smile|happy|laugh|feel good)',
            r'what brought (joy|happiness|a smile)',
        ]

        for pattern in assumptive_patterns:
            if re.search(pattern, response_lower):
                match = re.search(r'(smile|happy|laugh|joy|feel good)', response_lower)
                if match:
                    assumed_emotion = match.group(1)
                    if assumed_emotion not in user_lower:
                        return False, f"Assumptive: bot assumed '{assumed_emotion}'"

        # 10. THERAPIST LANGUAGE CHECK
        therapist_patterns = [
            r'how are you (doing|feeling|today)',
            r'how (does|did) that make you feel',
            r'your feelings are valid',
            r'i hear what you',
            r'hold space',
        ]

        for pattern in therapist_patterns:
            if re.search(pattern, response_lower):
                return False, f"Therapist language: {pattern}"

        # 11. ✅ IMPROVED: AWKWARD GRAMMAR CHECK
        # More specific patterns to avoid false positives
        awkward_patterns = [
            r'(what|how|why) \w+ if you want\?',
            r'^gotcha\.$', # "Gotcha." alone as acknowledgment
            r'\. gotcha\.$', # "...sentence. Gotcha." as acknowledgment
            r'^got it\b', # "got it" at start of response
            r'\. got it\b', # "...sentence. Got it" (acknowledgment)
        ]

        for pattern in awkward_patterns:
            if re.search(pattern, response_lower):
                # Special handling for "gotcha" - allow enthusiastic usage
                if 'gotcha' in pattern:
                    # Allow: "Gotcha! Christmas is...", "Gotcha — you mean..."
                    # Reject: "Gotcha." (standalone acknowledgment)
                    if re.search(r'gotcha[!—,:]', response_lower):
                        continue # Skip, it's enthusiastic/transitional usage
                    else:
                        return False, "Awkward grammar: using 'gotcha' as bare acknowledgment"
                # Special handling for "got it" - allow natural usage
                elif 'got it' in pattern:
                    # Allow: "she's got it", "I've got ideas", "they've got style"
                    # Allow: "Got it — bye!" or "Got it, take care!" (transitional)
                    # Reject: "Got it." (bare acknowledgment)

                    # Natural possessive usage
                    if re.search(r'(she\'?s|he\'?s|they\'?ve|i\'?ve|you\'?ve|we\'?ve).{1,15}got', response_lower):
                        continue # Skip, natural usage

                    # Transitional usage with punctuation (dash, comma, exclamation)
                    if re.search(r'got it[—,!:\-]', response_lower):
                        continue # Skip, transitional like "Got it — bye!"

                    # Check if it's in goodbye context
                    if any(word in response_lower for word in ['bye', 'goodbye', 'take care', 'see you', 'later']):
                        continue # Skip, it's in goodbye context

                    # Otherwise, reject as acknowledgment
                    return False, "Awkward grammar: using 'got it' as acknowledgment"
                else:
                    return False, f"Awkward grammar: {pattern}"

        # 12. LENGTH CHECK
        word_count = len(response.split())

        if word_count < 3:
            return False, "Too short"

        if word_count > 150:
            return False, f"Too wordy: {word_count} words (max 150)"

        # 13. RUN-ON SENTENCE CHECK
        sentences = [s.strip() for s in response.split('.') if s.strip()]
        for sentence in sentences:
            sentence_words = len(sentence.split())
            if sentence_words > 80:
                return False, f"Run-on sentence: {sentence_words} words (prefer 80 or less per sentence)"

        # 14. COHERENCE CHECK
        conjunction_count = response_lower.count(' and ') + response_lower.count(' but ') + response_lower.count(' or ')
        if conjunction_count > 8:
            return False, f"Too many conjunctions: {conjunction_count}"

        if word_count > 60:
            period_count = response.count('.')
            expected_periods = word_count // 35
            if period_count < expected_periods:
                return False, "Insufficient punctuation"

        words_list = response_lower.split()
        if len(words_list) > 30:
            last_section = words_list[int(len(words_list) * 0.7):]
            word_freq = {}
            for word in last_section:
                if len(word) > 4:
                    word_freq[word] = word_freq.get(word, 0) + 1

            max_repetition = max(word_freq.values()) if word_freq else 0
            if max_repetition >= 4:
                return False, "Response degradation: excessive word repetition"

        # 15. MULTIPLE QUESTIONS CHECK
        question_count = response.count('?')

        if (context.topic_type == 'feeling' or context.emotional_tone == 'negative'):
            if context.conversation_depth >= 2 and question_count > 0:
                if word_count < 40 and question_count > 0:
                    return False, "Later emotional support should prioritize depth over questions"

        if question_count > 2:
            return False, f"Too many questions: {question_count}"

        # 16. QUALITY/RELEVANCE CHECK
        if context.urgency_level == 'crisis':
            if 'resource' not in response_lower and 'help' not in response_lower:
                return False, "Crisis response must include resources"
            
        # 17. DISCLAIMER CHECK for deep disclosures
        if context.disclosure_depth >= 4:
            disclaimer_phrases = [
                'professional', 'therapist', 'counselor', 'trained',
                'serious', 'beyond what i can', 'specialist'
            ]
            has_disclaimer = any(phrase in response_lower for phrase in disclaimer_phrases)
            
            # Only require disclaimer if response doesn't already reference professional help
            if not has_disclaimer and len(response.split()) > 40:
                # This is a deep response without professional guidance reference
                # Allow it but log for review
                import logging
                logger = logging.getLogger('snowfriend.validation')
                logger.info(f"Deep disclosure response without disclaimer: {response[:100]}")

        # 18. CONTRADICTION CHECK
        if context.user_corrections > 0:
            correction_phrases = ["didn't i", "i just said", "i already told"]
            if any(phrase in user_lower for phrase in correction_phrases):
                acknowledgment_phrases = ["you're right", "my bad", "sorry", "fair"]
                if not any(phrase in response_lower for phrase in acknowledgment_phrases):
                    return False, "Didn't acknowledge user correction"

        return True, None

    # ========================================================================
    # FALLBACK GENERATION - WITH FIX #1 & #5
    # ========================================================================

    def generate_contextual_fallback(
        self,
        context: ConversationContext,
        conversation_history: List[Dict]
    ) -> str:
        """
        Better contextual fallback responses - BRIEF & CASUAL
        ✅ FIX #1: Uses empathy variety instead of always "sucks"
        ✅ FIX #5: Mirrors user's exact goodbye phrase
        """

        # CRISIS ONLY
        if context.emotional_tone == 'crisis' or context.urgency_level == 'crisis':
            return self._get_crisis_response()

        # ✅ FIX #5: IMPROVED GOODBYE - MIRROR USER'S EXACT PHRASE
        if conversation_history:
            last_msg_lower = conversation_history[-1]['content'].lower()
            goodbye_patterns = [r'\b(good ?night|goodnight|sleep|bye|goodbye)\b']
            if any(re.search(p, last_msg_lower) for p in goodbye_patterns):
                # Mirror user's goodbye style exactly
                if 'good night' in last_msg_lower or 'goodnight' in last_msg_lower:
                    return "Good night. I'm here whenever you need."
                elif 'sleep' in last_msg_lower:
                    return "Sleep well. I'm here whenever you need."
                elif 'bye' in last_msg_lower:
                    return "Bye. I'm here whenever you need."
                else:
                    return "Take care. I'm here whenever you need."

        # PLAYFUL BANTER
        if context.topic_type == 'playful_banter':
            return "Haha okay, you got me! So what's really up with you?"

        # ✅ NEW: CONTEXTUAL FALLBACK FOR PRODUCT/RECOMMENDATION QUESTIONS
        # If user is asking for recommendations, give relevant fallback instead of generic
        if conversation_history:
            last_msg = conversation_history[-1]['content'].lower()

            # Check if user is asking for recommendations
            recommendation_patterns = [
                r'\bany good\b',
                r'\brecommend\b',
                r'\bwhat brand',
                r'\bwhich brand',
                r'\bknow any\b',
                r'\bsuggest\b',
                r'\bwhat (should|can) i (get|buy)',
            ]

            if any(re.search(pattern, last_msg) for pattern in recommendation_patterns):
                # Check category and provide relevant fallback
                if any(word in last_msg for word in ['dress', 'clothes', 'clothing', 'fashion', 'outfit']):
                    return "For dresses and fashion, brands like Uniqlo, H&M, or Zara have great affordable options. What's your budget range?"
                elif any(word in last_msg for word in ['bag', 'bags', 'purse', 'handbag', 'tote']):
                    return "For bags, check out brands like Kate Spade outlet, Coach outlet, or local brands. What style does she like?"
                elif any(word in last_msg for word in ['gift', 'present', 'surprise']):
                    return "What kind of things does she usually like? That'll help me suggest something more specific."
                elif any(word in last_msg for word in ['shoes', 'sneakers', 'heels']):
                    return "For shoes, brands like Sketchers, Nike, or Clarks have good options. What type is she into?"
                elif any(word in last_msg for word in ['jewelry', 'accessories', 'watch']):
                    return "For accessories, check out local artisan shops or brands like Pandora. What's your price range?"
                else:
                    # Generic recommendation fallback
                    return "Can you tell me a bit more about what she likes? That'll help me give better suggestions."

        # ✅ FIX #1: EMOTIONAL SHARING - Uses empathy variety
        if context.topic_type == 'feeling' or context.emotional_tone == 'negative':
            if conversation_history:
                last_msg = conversation_history[-1]['content'].lower()

                # Early conversation (1-2 exchanges): Include question
                if context.conversation_depth <= 2:
                    if 'lonely' in last_msg or 'alone' in last_msg:
                        starter = self._get_empathy_starter()
                        return f"{starter}. It's not just being alone—it's feeling like nobody really gets you or cares. What happened?"
                    elif any(emotion in last_msg for emotion in ['sad', 'depressed', 'down']):
                        starter = self._get_empathy_starter()
                        return f"{starter}. Everything feels harder than it should be, even stuff that used to be easy or fun. What's going on?"
                    elif any(emotion in last_msg for emotion in ['anxious', 'worried', 'stressed']):
                        starter = self._get_empathy_starter()
                        return f"{starter}. Your mind won't let you rest and everything feels overwhelming. What's happening?"
                    elif 'angry' in last_msg or 'mad' in last_msg:
                        starter = self._get_empathy_starter()
                        return f"{starter}. Anger is exhausting to carry around. What's going on?"

                # Later conversation (3+ exchanges): NO question, just brief depth
                else:
                    if 'lonely' in last_msg or 'alone' in last_msg:
                        starter = self._get_empathy_starter()
                        return f"{starter}. It's not just being alone—it's feeling like nobody really gets you. That kind of isolation makes everything heavier."
                    elif any(emotion in last_msg for emotion in ['sad', 'depressed', 'down']):
                        starter = self._get_empathy_starter()
                        return f"{starter}. Everything feels harder than it should be, and it's frustrating because there's often no clear reason for it."
                    elif any(emotion in last_msg for emotion in ['anxious', 'worried', 'stressed']):
                        starter = self._get_empathy_starter()
                        return f"{starter}. Your mind won't let you rest and it makes even small things feel overwhelming."
                    elif 'worthless' in last_msg or 'nobody loves' in last_msg or 'unloved' in last_msg:
                        starter = self._get_empathy_starter()
                        return f"{starter}. Feeling worthless or unloved is painful, but feelings aren't facts."
                    elif 'angry' in last_msg or 'mad' in last_msg:
                        starter = self._get_empathy_starter()
                        return f"{starter}. Anger is exhausting to carry around, especially when it feels like things are out of your control."

            # Generic emotional fallback
            if context.conversation_depth <= 2:
                starter = self._get_empathy_starter()
                return f"{starter}. What's going on?"
            else:
                starter = self._get_empathy_starter()
                return f"{starter}."

        # Better fallback for clarification needs
        if conversation_history and len(conversation_history) >= 2:
            last_user_msg = conversation_history[-1]['content']
            if 'example' in last_user_msg.lower() or 'just' in last_user_msg.lower():
                return "Ah got it, that was just an example. So what's actually on your mind?"

        # Generic fallback based on conversation stage
        if context.conversation_depth <= 1:
            return "What's going on?"
        else:
            return "What's on your mind?"

    def _get_crisis_response(self) -> str:
        """Crisis resources response"""
        return (
            "I'm really concerned. Please reach out to a crisis helpline now:\n\n"
            "🇵🇭 PHILIPPINES (CALL NOW):\n"
            "• NCMH: 0917-899-8727 or 989-8727\n"
            "• Hopeline: (02) 8804-4673 or 0917-558-4673\n"
            "• Emergency: 911\n\n"
            "🌍 INTERNATIONAL:\n"
            "• US: 988\n"
            "• Crisis Text Line: Text HOME to 741741\n\n"
            "These are real humans who can help right now."
        )