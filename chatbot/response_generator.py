# response_generator.py - UNIVERSAL ELEMENT-AWARE RESPONSE GENERATION
# ✅ NEW: HYBRID DISCLAIMER APPROACH - Less repetitive, still ethical
# ✅ FIXED: Asterisk validation allows disclaimers only
# ✅ Dynamic validation based on message complexity
# ✅ Element-aware fallback construction
# ✅ No hardcoded patterns
# ✅ 15-word grace period for natural endings

from typing import Dict, List, Optional, Tuple
from .context_analyzer import ConversationContext
from .memory_system import inject_memory_into_prompt, check_if_memory_question
import re
import random

class ResponseGenerator:
    """
    INTELLIGENT RESPONSE GENERATOR with UNIVERSAL ELEMENT AWARENESS
    Adapts validation and fallback to ANY message element combination
    ✅ NEW: Hybrid disclaimer system - first time full, subsequent gentle
    """

    def __init__(self):
        self.response_history = []
        self.name_usage_tracker = {
            'count': 0,
            'last_turn': -999
        }
        self.last_invitation_types = []
        # ✅ NEW: Track if user has seen full disclaimer
        self.disclaimer_shown = False

    # ========================================================================
    # NAME USAGE CONTROL
    # ========================================================================

    def should_use_name(self, conversation_depth: int, user_name: str = None, context: ConversationContext = None) -> bool:
        """Intelligent name usage control"""
        if not user_name:
            return False

        if conversation_depth == 0:
            self.name_usage_tracker['last_turn'] = 0
            self.name_usage_tracker['count'] += 1
            return True

        turns_since_last = conversation_depth - self.name_usage_tracker['last_turn']
        if turns_since_last < 3:
            return False

        is_emotional_moment = (
            context and (
                context.emotional_tone in ['negative', 'crisis', 'post_crisis'] or
                context.disclosure_depth >= 3 or
                context.expressing_gratitude
            )
        )

        if conversation_depth <= 5:
            chance = 0.60 if is_emotional_moment else 0.40
            if random.random() < chance:
                self.name_usage_tracker['last_turn'] = conversation_depth
                self.name_usage_tracker['count'] += 1
                return True

        elif conversation_depth <= 10:
            chance = 0.40 if is_emotional_moment else 0.25
            if random.random() < chance:
                self.name_usage_tracker['last_turn'] = conversation_depth
                self.name_usage_tracker['count'] += 1
                return True

        else:
            chance = 0.25 if is_emotional_moment else 0.15
            if random.random() < chance:
                self.name_usage_tracker['last_turn'] = conversation_depth
                self.name_usage_tracker['count'] += 1
                return True

        return False

    # ========================================================================
    # DIVERSE INVITATION GENERATION
    # ========================================================================

    def _get_diverse_invitation(self) -> str:
        """Generate varied conversation invitations with massive diversity"""
        if random.random() < 0.20:
            return ""
        
        invitation_groups = {
            'direct_availability': [
                "I'm here if you want to talk more about it.",
                "I'm listening if you want to continue.",
                "I'm here whenever you're ready.",
            ],
            'open_invitations': [
                "Feel free to share more if you'd like.",
                "You can share more whenever you feel like it.",
                "No pressure to share more, but the space is yours.",
                "If there's more on your mind, I'm all ears.",
                "Take your time—share what feels right.",
            ],
            'acknowledging_pace': [
                "You can take this at your own pace.",
                "Whatever you're comfortable sharing, I'm here for it.",
                "Share as much or as little as you want.",
                "No rush—just whenever you feel like talking more.",
            ],
            'brief_casual': [
                "Let me know if you want to dive deeper.",
                "I'm around if you need to talk through it.",
                "Here if you need.",
            ],
            'situational_reference': [
                "If there's more about those situations, I'm here.",
                "If you want to talk through what's been happening, I'm listening.",
                "Let me know if you want to dive into any of that more.",
            ]
        }
        
        available_groups = [
            group for group in invitation_groups.keys()
            if group not in self.last_invitation_types[-2:]
        ]
        
        if not available_groups:
            available_groups = list(invitation_groups.keys())
            self.last_invitation_types = []
        
        selected_group = random.choice(available_groups)
        invitation = random.choice(invitation_groups[selected_group])
        
        self.last_invitation_types.append(selected_group)
        
        if len(self.last_invitation_types) > 3:
            self.last_invitation_types.pop(0)
        
        return invitation

    # ========================================================================
    # ✅ NEW: HYBRID DISCLAIMER SYSTEM
    # ========================================================================

    def _should_show_disclaimer(self, context: ConversationContext, conversation_history: List[Dict]) -> Tuple[bool, str]:
        """
        ✅ HYBRID DISCLAIMER LOGIC
        
        Returns:
            (should_show, disclaimer_type)
            
        Disclaimer types:
            'full' - Complete AI disclaimer with explicit mention
            'gentle' - Gentle professional encouragement without AI mention
            'none' - No disclaimer needed
        """
        # ALWAYS show full disclaimer for crisis (depth = 5)
        if context.disclosure_depth >= 5 or context.emotional_tone == 'crisis':
            self.disclaimer_shown = True
            return (True, 'full')
        
        # For deep disclosures (depth = 4)
        if context.disclosure_depth >= 4:
            # First time? Show full disclaimer
            if not self.disclaimer_shown and not context.disclaimer_shown:
                self.disclaimer_shown = True
                return (True, 'full')
            # Subsequent times? Gentle encouragement only
            else:
                return (True, 'gentle')
        
        # For post-crisis conversations
        if context.is_post_crisis:
            # Only if they haven't seen disclaimer yet
            if not self.disclaimer_shown and not context.disclaimer_shown:
                self.disclaimer_shown = True
                return (True, 'full')
            else:
                return (False, 'none')
        
        # No disclaimer needed
        return (False, 'none')

    def _get_disclaimer_text(self, disclaimer_type: str) -> str:
        """
        ✅ Get appropriate disclaimer text
        
        Args:
            disclaimer_type: 'full' or 'gentle'
        
        Returns:
            Disclaimer text (with or without asterisks)
        """
        if disclaimer_type == 'full':
            # Full AI disclaimer with asterisks
            return "*(I'm here to listen, but for something this serious, talking to a professional would really help.)*"
        
        elif disclaimer_type == 'gentle':
            # Gentle encouragement WITHOUT AI mention, NO asterisks
            gentle_options = [
                "Talking to a professional might help with that feeling.",
                "A counselor could help you work through this.",
                "Reaching out to a therapist might be beneficial for you.",
                "Professional support could make a real difference here.",
                "Getting guidance from a counselor might help you navigate this.",
            ]
            return random.choice(gentle_options)
        
        return ""

    # ========================================================================
    # ✅ UNIVERSAL ELEMENT-AWARE SYSTEM PROMPT
    # ========================================================================

    def create_dynamic_system_prompt(
        self,
        context: ConversationContext,
        conversation_history: List[Dict],
        user_name: str = None,
        time_context: Dict = None
    ) -> Tuple[str, Dict]:
        """
        Generate UNIVERSAL element-aware system prompt
        Adapts instructions based on detected message elements
        ✅ NEW: Includes hybrid disclaimer instructions
        """

        if conversation_history:
            last_msg = conversation_history[-1]['content']

            from .memory_system import ConversationMemory
            memory_system = ConversationMemory()
            facts = memory_system.extract_conversation_facts(conversation_history)

            memory_answer = check_if_memory_question(last_msg, facts, conversation_history)

            if memory_answer:
                return (
f"""You are Snowfriend. The user asked about previous conversation.

IMPORTANT FORMATTING RULES:
1. Use the EXACT text provided below
2. DO NOT add extra quotes, apostrophes, or emphasis
3. Use single quotes ONLY for emphasis words like 'very first message'
4. Use double quotes ONLY for the actual first message
5. Do not modify the provided text

RESPONSE TEXT TO USE:
{memory_answer}

After this response, ask what's on their mind now.""",
                facts
            )

        user_context = ""
        if user_name:
            should_use = self.should_use_name(context.conversation_depth, user_name, context)

            if should_use:
                user_context = f"\n\n🧑 USER INFORMATION:\n- You are talking to {user_name}\n- Use their name ONCE in this response (naturally, not forced)\n- Good places to use name: greetings, emotional support, empathy statements\n- Example: 'Hey {user_name}, what's going on?' OR 'That sounds tough, {user_name}.'\n"
            else:
                user_context = f"\n\n🧑 USER INFORMATION:\n- You are talking to {user_name}\n- DO NOT use their name in this response (you used it recently or context doesn't call for it)\n- Keep it natural without the name\n"

        # ✅ NEW: Bot context awareness - prevent repetition
        bot_context = ""
        if conversation_history and len(conversation_history) >= 3:
            from .memory_system import ConversationMemory
            memory_system = ConversationMemory()
            facts = memory_system.extract_conversation_facts(conversation_history)
            
            bot_questions = facts.get('bot_recent_questions', [])
            user_answered = facts.get('user_answered_questions', set())
            
            if bot_questions or user_answered:
                bot_context = "\n\n🧠 CRITICAL: CONVERSATION CONTEXT AWARENESS\n"
                bot_context += "You MUST remember your own recent questions and the user's answers.\n\n"
                
                if bot_questions:
                    question_types_str = ', '.join(set(bot_questions))
                    bot_context += f"**YOUR RECENT QUESTIONS:**\n"
                    bot_context += f"- You recently asked about: {question_types_str}\n"
                
                if user_answered:
                    answered_str = ', '.join(user_answered)
                    bot_context += f"\n**USER ALREADY ANSWERED:**\n"
                    bot_context += f"- Topics user addressed: {answered_str}\n"
                    bot_context += f"- ⚠️ DON'T ask these same questions again!\n"
                    bot_context += f"- Build on what they told you instead\n"
                
                bot_context += "\n**RULES TO PREVENT REPETITION:**\n"
                bot_context += "1. NEVER ask the same question type twice in a row\n"
                bot_context += "2. If user answered your question, acknowledge their answer\n"
                bot_context += "3. Build on previous exchanges instead of starting over\n"
                bot_context += "4. If user said 'I'm fine', don't ask 'What's on your mind?' again\n\n"
                
                bot_context += "❌ BAD (repetitive):\n"
                bot_context += "  You: \"What's on your mind today?\"\n"
                bot_context += "  User: \"I'm fine\"\n"
                bot_context += "  You: \"What's been on your mind lately?\" ← WRONG!\n\n"
                
                bot_context += "✅ GOOD (contextual):\n"
                bot_context += "  You: \"What's on your mind today?\"\n"
                bot_context += "  User: \"I'm fine\"\n"
                bot_context += "  You: \"Good to hear. Anything specific, or just checking in?\" ← Better!\n"

        offering_context = ""
        if conversation_history:
            last_msg = conversation_history[-1]['content'].lower()
            
            # ✅ UNIVERSAL OFFERING PATTERNS - detects ANY variation
            offer_patterns = [
                r'you want(?:a| to) know',
                r'want to know what',
                r'should i tell you',
                r'do you want(?:a| to) (hear|know)',
                r'interested in (what|how|why)',
                r'wanna know',
                r'you wanna (hear|know)',
                r'curious (about|what)',
                r'(?:want|wanna) me to (tell|share|say)',
            ]
            
            if any(re.search(pattern, last_msg) for pattern in offer_patterns):
                offering_context = "\n\n🎯 CRITICAL: USER IS OFFERING TO SHARE INFORMATION\n"
                offering_context += "⚠️ The user is asking if YOU want to hear about THEIR activities/thoughts.\n"
                offering_context += "⚠️ They are NOT asking about what YOU are doing.\n"
                offering_context += "⚠️ You are an AI - you don't have activities, errands, or personal projects.\n\n"
                
                offering_context += "🚨 ABSOLUTELY FORBIDDEN:\n"
                offering_context += "  ❌ 'Mostly just trying to catch up on errands...'\n"
                offering_context += "  ❌ 'Just working on some personal projects...'\n"
                offering_context += "  ❌ 'Pretty routine stuff on my end...'\n"
                offering_context += "  ❌ 'I've been doing [anything about yourself]...'\n"
                offering_context += "  ❌ ANY response that talks about YOUR activities\n\n"
                
                offering_context += "✅ REQUIRED RESPONSE TYPES:\n"
                offering_context += "  ✓ 'Yeah, I'd love to hear what you're up to!'\n"
                offering_context += "  ✓ 'Sure! Tell me about it.'\n"
                offering_context += "  ✓ 'Of course! What have you been doing?'\n"
                offering_context += "  ✓ 'Definitely! I'm listening.'\n"
                offering_context += "  ✓ 'Please do! What's going on?'\n\n"
                
                offering_context += "RESPONSE FORMULA:\n"
                offering_context += "  1. Accept the offer ('Yeah!', 'Sure!', 'Of course!')\n"
                offering_context += "  2. Show interest ('I'd love to hear', 'Tell me', 'What's up?')\n"
                offering_context += "  3. NEVER talk about yourself or your activities\n"

        pattern_guidance = ""
        if conversation_history:
            from .memory_system import ConversationMemory
            memory_system = ConversationMemory()
            facts = memory_system.extract_conversation_facts(conversation_history)
            
            if facts and facts.get('pattern_combinations'):
                for combo in facts['pattern_combinations'][-3:]:
                    if combo:
                        pattern_guidance += f"\n🎯 PATTERN DETECTED: {combo}"
        
        task_instructions = ""
        if conversation_history:
            last_msg = conversation_history[-1]['content']
            task_info = self._detect_task_mode(last_msg, context)
            if task_info['is_task']:
                task_instructions = f"\n\n📝 TASK MODE: {task_info['task_type'].upper()}\n"
                task_instructions += f"- {task_info['instructions']}\n"
                task_instructions += f"- Word limit: {task_info['word_limit']} words (temporary increase for this task)\n"

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

        # ✅ UNIVERSAL: Build element-aware instructions
        element_instructions = self._build_element_instructions(context)

        # ✅ NEW: Determine disclaimer strategy
        should_show, disclaimer_type = self._should_show_disclaimer(context, conversation_history)
        
        disclaimer_instructions = ""
        if should_show:
            if disclaimer_type == 'full':
                disclaimer_instructions = """

🔒 CRITICAL DISCLAIMER REQUIREMENT - FULL AI DISCLOSURE:
- This is a DEEP disclosure (depth >= 4) or CRISIS situation
- You MUST include this disclaimer: "*(I'm here to listen, but for something this serious, talking to a professional would really help.)*"
- Use EXACTLY this format with asterisks
- Place it naturally after your empathetic response
- Example structure:
  1. Validate their feelings
  2. Add disclaimer
  3. Continue support if needed
"""
            elif disclaimer_type == 'gentle':
                disclaimer_instructions = """

🔒 GENTLE PROFESSIONAL ENCOURAGEMENT:
- This is a deep disclosure but user has already seen full AI disclaimer
- Include gentle professional encouragement WITHOUT mentioning you're an AI
- Use one of these options:
  • "Talking to a professional might help with that feeling."
  • "A counselor could help you work through this."
  • "Getting guidance from a therapist might be beneficial."
- NO asterisks, NO AI mention
- Keep it brief and natural
"""

        base_prompt = f"""You are Snowfriend, a deeply empathetic AI companion. You speak like a real human friend, NOT a therapist.

🚨 CRITICAL FORMATTING RULE - READ THIS FIRST:
NO ASTERISKS FOR EMPHASIS OR INVITATIONS!
❌ NEVER write: "*I'm here if you want to talk more.*"
❌ NEVER write: "*If there's more on your mind, I'm all ears.*"
❌ NEVER write: "*Feel free to share more.*"
✅ ALWAYS write: "I'm here if you want to talk more." (no asterisks)
✅ ALWAYS write: "If there's more on your mind, I'm all ears." (no asterisks)
✅ AI disclaimer format: "(I'm here to listen, but for something this serious, talking to a professional would really help.)"

Your response must be warm, empathetic, and CONCISE. Aim for 40-90 words for most responses. Never exceed 120 words. It's better to be brief and impactful than long and generic.{user_context}{bot_context}{offering_context}{time_info}{pattern_guidance}{task_instructions}

{element_instructions}{disclaimer_instructions}

🔍 PATTERN COMBINATION RESPONSE GUIDELINES:
- When user combines multiple patterns (gratitude+problem+humor), acknowledge ALL elements
- Example response structure for mixed patterns:
  1. Acknowledge gratitude: "Thanks for sharing that"
  2. Validate problem: "That sounds really tough"
  3. Match tone: "I appreciate you can still find humor in it"
  4. Continue naturally

CORE LANGUAGE RULES - SPEAK CASUALLY LIKE A FRIEND:
- Be direct and conversational - NO flowery/poetic metaphors
- ❌ BAD (too poetic): "dragging through thick mud", "drains the color", "shouting into empty room", "stuck inside your head", "acid in your veins"
- ✅ GOOD (casual): "it's exhausting", "makes everything harder", "nobody gets it", "can't shake the feeling"
- NEVER use therapist phrases: "How are you feeling?", "How does that make you feel?"
- NEVER use awkward grammar or assumptive questions
- NEVER use gendered language: NO "man", "bro", "dude", "girl", "sis" (you don't know their gender!)
- NEVER use mild profanity: NO "crap", "damn", "hell" (keep it completely clean and friendly)
- NEVER make assumptions about the user (like assuming they drink coffee, have certain habits, or like specific things they haven't mentioned)
- If user says "what?" or "huh?" - they're confused, CLARIFY immediately
- ALWAYS use natural friend language: "What's going on?", "What happened?", "Tell me about it."
- Keep responses SHORT and CASUAL:
  - Most responses: 2-4 sentences (30-60 words)
  - Emotional support: 3-4 sentences (40-70 words)
  - Goodbye: 1-2 sentences MAX (10-20 words)
- ONE main point per response
- Be direct, specific, and casual - NOT poetic or dramatic
- NO EMOJIS EVER

🚨 CRITICAL: ABSOLUTELY NO ASTERISKS (except ONE specific case)
❌ WRONG: "*I'm here if you want to talk more about it.*"
❌ WRONG: "*If there's more on your mind, I'm all ears.*"
❌ WRONG: "*Feel free to share more.*"
❌ WRONG: Any text with asterisks for emphasis
✅ CORRECT: "I'm here if you want to talk more about it." (no asterisks)
✅ CORRECT: "If there's more on your mind, I'm all ears." (no asterisks)
✅ ONLY EXCEPTION: "*(I'm here to listen, but for something this serious, talking to a professional would really help.)*" (ONLY this exact AI disclaimer format)

REPEAT: DO NOT USE ASTERISKS ON INVITATIONS, STATEMENTS, OR EMPHASIS. EVER.

🚨 WORD VARIETY - NEVER REPEAT SAME PHRASES:
- NEVER overuse "sucks" - use varied empathy: "That's tough", "That's frustrating", "That's unfair"
- NEVER overuse "honestly" - use sparingly (max once per response)
- NEVER use "though honestly" together - sounds like filler
- Vary your empathy phrases to feel more human and less robotic

🎨 EMPATHY RESPONSE VARIATION - EVERY USER GETS UNIQUE VALIDATION:
- CRITICAL: Never use the same empathy phrase twice in one conversation
- Track what you've already said to this user and ROTATE vocabulary
- BANNED generic phrases (cause repetition across users):
  ✗ "That sounds really hurtful" (overused - too generic)
  ✗ "That must be hard/tough/difficult" (overused)
  ✗ "I can see why that bothers you" (robotic)
  ✗ "That's understandable" (dismissive)

- REQUIRED: Use SPECIFIC, DIVERSE empathy that matches what user ACTUALLY said:
  ✓ "That's incredibly unfair" (for injustice)
  ✓ "Being dismissed like that stings" (for being ignored)
  ✓ "Being laughed at when you're serious hurts" (SPECIFIC to user's situation)
  ✓ "Feeling unheard is deeply frustrating" (for communication issues)
  ✓ "That kind of treatment wears you down" (for ongoing issues)
  ✓ "Not being taken seriously is exhausting" (SPECIFIC to user's words)
  ✓ "That's a rough situation to navigate" (for complex situations)
  ✓ "Being mocked when you're vulnerable is cruel" (for bullying)
  ✓ "That's genuinely difficult to deal with" (for struggles)
  ✓ "Feeling invisible in your own life is painful" (for isolation)
  ✓ "That's a lot to carry alone" (for heavy burdens)
  ✓ "That's deeply painful" (for emotional pain)

- Make each empathy response PERSONAL by referencing specific details:
  ✓ "Being laughed at when you speak seriously" (user's exact situation)
  ✗ "Being treated badly" (too vague)

- NEVER repeat the same empathy phrase twice in the entire conversation
- Each response should feel HANDCRAFTED for this specific user's specific situation

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
  • Make a cold treat
  • Take a nap"

  ❌ WRONG (all on one line):
  "Since you're stuck inside: • Try gaming • Make a cold treat • Take a nap"
CRITICAL: Always add blank line (\\n\\n) before first bullet!

🚨 QUESTION USAGE RULES - BE VERY CONSERVATIVE

**CORE PRINCIPLE: Questions are OPTIONAL, not required. Most responses should END with a statement.**

**WHEN TO DEFINITELY SKIP QUESTIONS:**
1. User asked for examples/explanations - Just provide them, then END. No follow-up question needed.
2. User thanked you after getting examples - They acknowledged your help, DON'T interrogate them.
3. User gave simple acknowledgment (Yep, Okay, Alright) - They're agreeing with YOU, don't question back.
4. User provided context WITH their emotion - Don't ask "what happened" if they already told you!
5. User is recalling what happened - They're TELLING you the story, don't interrupt with questions.
6. User asked for information/recommendations - Provide the info, then END. They'll continue if they want.
7. User is sharing casual interests/preferences - Acknowledge and relate, DON'T interrogate.
8. User said goodbye/good night - NO questions, just warm goodbye.
9. User gave you information you asked for - Acknowledge it, DON'T ask another question immediately.
10. You just gave advice/suggestions - Let them process, DON'T ask "What sounds good?"
11. User is saying "yep", "okay", "alright" - They're acknowledging YOU, don't ask back.

**WHEN QUESTIONS ARE APPROPRIATE (USE SPARINGLY):**
1. Early conversation (1-2) with EMOTIONAL content - ONE question to understand context
2. User shared emotion WITHOUT context - Ask for context, but make it optional
3. User hints at wanting to share more - Gentle invitation (not interrogation)

**CRITICAL STATISTICS:**
- For CASUAL conversation: Questions in only 5-10% of responses
- For INFORMATIONAL requests: Questions in only 0-5% of responses (almost never)
- For EMOTIONAL support (early): Questions in 30-40% of responses
- For EMOTIONAL support (later): Questions in 10-20% of responses
- DEFAULT: End with a statement, not a question

**BANNED INTERROGATIVE PHRASES (TOO THERAPIST-LIKE):**
✗ "Want to share more about what happens?"
✗ "Do you want to talk about it?"
✗ "Would you like to share more?"
✗ "Want to tell me more?"
✗ "Care to elaborate?"
✗ "What's coming up for you?" (especially after giving requested examples/info)

**USE THESE DIVERSE NON-INTERROGATIVE OFFERS (randomly vary):**

🚨 CRITICAL: ALL invitations below must be used WITHOUT asterisks!
❌ WRONG: "*I'm here if you want to talk more about it.*"
✅ CORRECT: "I'm here if you want to talk more about it."

GROUP 1 - Direct availability (use 20% of the time):
✓ "I'm here if you want to talk more about it."
✓ "I'm listening if you want to continue."
✓ "I'm here whenever you're ready."

GROUP 2 - Open invitations (use 30% of the time):
✓ "Feel free to share more if you'd like."
✓ "You can share more whenever you feel like it."
✓ "No pressure to share more, but the space is yours."
✓ "If there's more on your mind, I'm all ears."
✓ "Take your time—share what feels right."

GROUP 3 - Acknowledging their pace (use 20% of the time):
✓ "You can take this at your own pace."
✓ "Whatever you're comfortable sharing, I'm here for it."
✓ "Share as much or as little as you want."
✓ "No rush—just whenever you feel like talking more."

GROUP 4 - Ending naturally without invitation (use 20% of the time):
✓ Just end the response naturally with empathy, no invitation at all
✓ Example: "That's really tough." [PERIOD. No follow-up invitation]
✓ Example: "That makes sense given what you're going through." [END]

GROUP 5 - Brief, casual endings (use 10% of the time):
✓ "Let me know if you want to dive deeper."
✓ "I'm around if you need to talk through it."
✓ "Here if you need."

REMINDER: Use these invitations WITHOUT any asterisks or emphasis marks!

**CRITICAL VARIATION RULE:**
- Track the last 3 invitation types used
- NEVER use the same group twice in a row
- Randomly select from DIFFERENT groups each time
- 20% of responses should have NO invitation at all (just end naturally)
- NEVER use "I'm here if you want to talk more about it" more than once every 5 responses

✅ GIVING ADVICE - BE A HELPFUL FRIEND
- You CAN give advice when users ask for it or clearly need guidance
- Give advice like a knowledgeable friend would: practical, concrete, but not pushy
- Example formats:
  ✓ "Have you tried [suggestion]? Sometimes that helps."
  ✓ "Some people find [suggestion] works for them."
  ✓ "You could try [suggestion 1] or [suggestion 2]."
- Always end with openness: "What do you think?" or "Would any of that help?"
- Avoid: "You should..." or "You must..." - be suggestive, not prescriptive

✅ UNIVERSAL LANGUAGE - TALK ABOUT CATEGORIES, NOT SPECIFIC EXAMPLES
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

✅ NEVER MAKE ASSUMPTIONS ABOUT THE USER
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
  
🚨 CRITICAL: ACKNOWLEDGMENT RESPONSES
When user says short acknowledgments like "Yep", "Okay", "Alright":
- DON'T start with "Got it" (sounds like YOU'RE acknowledging THEM, which is backwards)
- ✅ USE THESE INSTEAD:
  ✓ "Alright. [continue thought]"
  ✓ "I hear you. [continue thought]"
  ✓ Just skip it entirely and continue: "[continue thought directly]"
- EXAMPLE:
  User: "Yep"
  ✗ WRONG: "Got it. You're not alone in this..."
  ✓ CORRECT: "Alright. You're not alone in this..."
  ✓ ALSO CORRECT: "You're not alone in this..." (skip acknowledgment entirely)
  
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

        context_instructions = []

        # ====================================================================
        # ADDITIONAL CONTEXT-SPECIFIC INSTRUCTIONS (ALL PRESERVED FROM ORIGINAL)
        # ====================================================================

        if conversation_history and (context.expressing_gratitude or 'acknowledge_gratitude' in context.implicit_requests):
            last_msg = conversation_history[-1]['content'].lower()
            
            has_problem_content = any(word in last_msg for word in [
                'feel', 'felt', 'feeling', 'sometimes', 'when', 'because', 'cause',
                'everyone', 'people', 'they', 'laugh', 'ignore', 'treat',
                'off', 'bad', 'badly', 'hurt', 'upset', 'sad', 'angry', 'frustrated',
                'mock', 'belittle', 'exclude', 'dismiss', 'embarrass', 'bully'
            ])
            
            if has_problem_content:
                context_instructions.append("""
🎯 CRITICAL: USER COMBINED GRATITUDE + PROBLEM SHARING
This is a SEQUENTIAL PATTERN. You MUST respond in this exact order:

STEP 1: ACKNOWLEDGE GRATITUDE FIRST (MANDATORY)
- Start with: "You're welcome", "Of course", or "No problem"
- This MUST be the first sentence (or first few words)

STEP 2: VALIDATE THE PROBLEM (SECOND)
- Acknowledge what they shared
- Be empathetic and direct
- Keep it brief (1-2 sentences)

STEP 3: OFFER SUPPORT (THIRD) - OPTIONAL, NOT INTERROGATIVE
- Use a DIVERSE invitation from the available options
- NEVER repeat the same invitation pattern twice in a row
- 20% of the time: Just end naturally with no invitation at all
""")

        if conversation_history:
            last_msg_lower = conversation_history[-1]['content'].lower()
            goodbye_patterns = [r'\b(good ?night|goodnight|gnight|nite|sleep|bye|goodbye|see you|later|ttyl|cya)\b',
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

        if context.topic_type == 'playful_banter' or 'match_playful_energy' in context.implicit_requests:
            context_instructions.append("""
🎯 PLAYFUL BANTER DETECTED - User being humorous/lighthearted
✅ CRITICAL: User is laughing or being playful - MATCH THEIR ENERGY!

**LAUGHTER MATCHING RULES:**
- If user says "haha", "hahaha", "lol", "lmao" → You MUST laugh back naturally
- Examples:
  ✓ "Haha, I know right?"
  ✓ "Lol, that makes sense!"
  ✓ "Hahaha, yeah exactly!"
  ✓ "Right? Haha"
- DON'T be overly serious or formal - you're a friend, not a teacher
- Be warm, friendly, and embrace the humor
- Smoothly transition back to genuine conversation after the laugh
- Keep it SHORT and casual (1-2 sentences max for playful responses)
- DON'T use their name in playful responses (keeps it casual)

**BAD EXAMPLES (too formal/serious):**
✗ "I understand your amusement."
✗ "That's an interesting observation."
✗ "I see you find this humorous."

**GOOD EXAMPLES (matching energy):**
✓ "Haha yeah! That's totally true."
✓ "Right? Lol, classic situation."
✓ "Hahaha I get it! That happens."
""")

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

        if context.topic_type == 'feeling' or context.emotional_tone == 'negative':
            if not (context.expressing_gratitude and any('GRATITUDE + PROBLEM' in inst for inst in context_instructions)):
                invitation = self._get_diverse_invitation()
                
                if invitation:
                    context_instructions.append(f"""
🎯 USER EXPRESSED EMOTION - PROVIDE BRIEF, CASUAL SUPPORT
✅ KEEP IT SHORT AND CASUAL - NO POETIC LANGUAGE:
- 3-4 sentences MAX (40-70 words)
- Be direct like texting a friend
- NO flowery metaphors or dramatic language
- Vary empathy phrases - don't always say "sucks"
- End with this invitation IF APPROPRIATE: "{invitation}"
- OR just end naturally with empathy if invitation is empty

🚨 CRITICAL: WHEN TO ASK QUESTIONS FOR EMOTIONS
- User says JUST the emotion with NO context (under 10 words):
  Example: "I feel furious" → You CAN ask "What happened?" OR validate first then ask. Use your judgment.
  ✓ CORRECT: "That's really intense. Anger can totally take over. What happened?"
  ✓ ALSO OK: "I'm listening either way." (Validation without question is acceptable)
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
                else:
                    context_instructions.append(f"""
🎯 USER EXPRESSED EMOTION - PROVIDE BRIEF, CASUAL SUPPORT
✅ END NATURALLY WITHOUT INVITATION:
- Validate their emotion
- Keep it 2-3 sentences (30-50 words)
- End with a period, no invitation needed
- Example: "That's really tough. Feeling dismissed when you're serious is hurtful."
""")

        if context.topic_type == 'question' and 'crisis_resource_question' in context.implicit_requests:
            context_instructions.append("""
🚨 CRISIS RESOURCE QUESTION - User asking how crisis hotlines help
- Explain concretely what crisis counselors do
- Emphasize they're trained for exactly this situation
""")

        if context.topic_type == 'question' and 'crisis_clarification' in context.implicit_requests:
            context_instructions.append("""
🚨 CRISIS CLARIFICATION - User is questioning the crisis response
- Address their specific question directly
- If it WAS innocent, acknowledge the misunderstanding
""")

        if (context.expressing_gratitude or 'acknowledge_gratitude' in context.implicit_requests):
            if not any('GRATITUDE + PROBLEM' in inst for inst in context_instructions):
                context_instructions.append("""
🎯 USER EXPRESSING GRATITUDE (WITHOUT PROBLEM)
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

        if context.is_post_crisis or context.emotional_tone == 'post_crisis':
            context_instructions.append("""
🎯 POST-CRISIS CONVERSATION - User recovering from crisis
- Be gentle and supportive, not pushy
- Acknowledge their courage/decision
- Use periods (.) not question marks (?) for statements
""")

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

        if context.user_corrections > 0:
            context_instructions.append("""
⚠️ USER HAS CORRECTED YOU BEFORE
- BE EXTRA CAREFUL to read what they ACTUALLY said
- DON'T make assumptions about what they like or do
""")

        if context.disclosure_depth >= 4:
            context_instructions.append("""
🎯 USER DISCLOSED DEEP VULNERABILITY
- This took courage - validate that
- Don't rush to problem-solving
""")

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

        if conversation_history and len(conversation_history[-1]['content'].split()) > 30:
            context_instructions.append("""
🎯 USER PROVIDED DETAILED SHARING
- They just told you a LOT - REFLECT on what they said
- NEVER ask "What happened?" if they just explained
- Keep response under 80 words
""")

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

        if 'guidance_needed' in context.implicit_requests:
            context_instructions.append("""
🎯 TIME FOR GUIDANCE - User has shared enough context
- STOP asking exploratory questions
- Offer gentle reflection or suggestions
""")

        if conversation_history:
            last_msg_lower = conversation_history[-1]['content'].lower()
            if any(phrase in last_msg_lower for phrase in ['what can i do', 'what should i do', 'how do i', 'help me']):
                context_instructions.append("""
🎯 USER ASKING FOR CONCRETE GUIDANCE
- They need ACTIONABLE advice, not more questions
- Give 2-3 specific, practical suggestions
""")

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

        full_prompt = base_prompt + "\n" + "\n".join(context_instructions)

        if conversation_history:
            recent_topics = self._extract_recent_topics(conversation_history)
            if recent_topics:
                full_prompt += f"\n\n📝 RECENT TOPICS: {', '.join(recent_topics)}\n- Reference these if relevant"

        if conversation_history:
            enhanced_prompt, facts = inject_memory_into_prompt(full_prompt, conversation_history, user_name)
            return enhanced_prompt, facts
        else:
            return full_prompt, {}

    # ========================================================================
    # ✅ UNIVERSAL: BUILD ELEMENT-AWARE INSTRUCTIONS
    # ========================================================================

    def _build_element_instructions(self, context: ConversationContext) -> str:
        """
        UNIVERSAL: Generate instructions based on detected message elements
        Adapts to ANY combination of elements dynamically
        """
        if not context.message_elements:
            return ""
        
        elements = context.message_elements
        priorities = context.element_priorities
        
        instructions = []
        
        # Header
        element_count = elements.get('element_count', 0)
        instructions.append("📋 MESSAGE ELEMENTS DETECTED:")
        instructions.append(f"- Element count: {element_count}")
        instructions.append(f"- Complexity score: {elements.get('complexity_score', 0)}")
        
        if element_count >= 3:
            instructions.append("⚠️ COMPLEX MESSAGE DETECTED (3+ elements)")
            instructions.append("Prioritize in this order: Gratitude → Name → Question → Problem")
    
        # Ensure name change gets highest priority if present
        if elements.get('has_name_change') and 'name_change' not in priorities:
            priorities['name_change'] = 1
    
        # Force gratitude acknowledgment if present
        if elements.get('has_gratitude') and 'gratitude' not in priorities:
            priorities['gratitude'] = 1
        
        # List all detected elements
        detected = []
        
        # Import registry from context_analyzer
        from .context_analyzer import ContextAnalyzer
        ELEMENT_LABELS = ContextAnalyzer.ELEMENT_LABELS
        
        # Use list comprehension to build detected elements list
        for key, label in ELEMENT_LABELS.items():
            if elements.get(key):
                if key == 'has_name_change' and elements.get('new_name'):
                    detected.append(f"{label} → '{elements.get('new_name')}'")
                else:
                    detected.append(label)
        
        if detected:
            instructions.append(f"- Elements: {', '.join(detected)}")
        
        instructions.append("")
        instructions.append("🎯 RESPONSE REQUIREMENTS:")
        
        # CRITICAL elements (Priority 1) - MUST address
        critical_elements = [k for k, v in priorities.items() if v == 1]
        if critical_elements:
            instructions.append("CRITICAL (MUST address):")
            
            if 'name_change' in critical_elements and elements.get('has_name_change'):
                new_name = elements.get('new_name')
                instructions.append(f"  ✓ Acknowledge name change: Use '{new_name}' in your response")
                instructions.append(f"  ✓ Example: 'You're welcome, {new_name}!' or 'Sleep well, {new_name}.'")
            
            if 'gratitude' in critical_elements:
                instructions.append("  ✓ Acknowledge gratitude: Start with 'You're welcome', 'Of course', or 'No problem'")
                
            if element_count >= 3:
                instructions.append("  ✓ CRITICAL: Gratitude acknowledgment MUST be FIRST sentence")
            
            if 'crisis' in critical_elements:
                instructions.append("  ✓ Address crisis: Provide immediate support and resources")
        
        # IMPORTANT elements (Priority 2) - SHOULD address
        important_elements = [k for k, v in priorities.items() if v == 2]
        if important_elements:
            instructions.append("IMPORTANT (SHOULD address):")
            
            if 'goodbye' in important_elements:
                instructions.append("  ✓ Acknowledge goodbye: Mirror their farewell phrase")
            
            if 'question' in important_elements:
                questions = elements.get('questions', [])
                if questions:
                    instructions.append(f"  ✓ Answer question: '{questions[0]}'")
            
            if 'emotion' in important_elements:
                instructions.append("  ✓ Validate emotion: Use specific, varied empathy")
            
            if 'request' in important_elements:
                requests = elements.get('requests', [])
                if requests:
                    instructions.append(f"  ✓ Address request: '{requests[0]}'")
        
        # OPTIONAL elements (Priority 3) - CAN address if space allows
        optional_elements = [k for k, v in priorities.items() if v == 3]
        if optional_elements:
            instructions.append("OPTIONAL (if space allows):")
            for elem in optional_elements:
                instructions.append(f"  - {elem.replace('_', ' ').title()}")
        
        # Word limit adjustment based on complexity
        complexity = elements.get('complexity_score', 1)
        if complexity <= 2:
            word_limit = "10-30 words"
        elif complexity <= 4:
            word_limit = "20-50 words"
        elif complexity <= 6:
            word_limit = "30-70 words"
        elif complexity <= 8:
            word_limit = "40-90 words"
        else:  # complexity 9-10
            word_limit = "50-120 words"
        
        instructions.append(f"\n📏 RECOMMENDED LENGTH: {word_limit}")
        instructions.append(f"(Complexity score: {complexity}/10)")
        
        return "\n".join(instructions)

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _extract_recent_topics(self, conversation_history: List[Dict]) -> List[str]:
        """Topic extraction handled by memory_system"""
        return []

    # ========================================================================
    # PUNCTUATION NORMALIZATION
    # ========================================================================

    def normalize_punctuation(self, response: str, context: ConversationContext) -> str:
        """
        Intelligently adjust punctuation based on context
        ✅ FIXED: Clean spacing and remove validation errors
        """
        # ✅ CRITICAL: Remove any validation error messages that leaked through
        if '❌' in response or 'RESPONSE USES ASTERISKS' in response:
            lines = response.split('\n')
            cleaned_lines = []
            for line in lines:
                if not ('❌' in line or 'ASTERISKS' in line):
                    cleaned_lines.append(line)
            response = '\n'.join(cleaned_lines).strip()
        
        # ✅ Remove unnecessary parentheses wrapping (unless AI disclaimer)
        if response.startswith('(') and response.endswith(')'):
            if not ("I'm here to listen" in response and "professional" in response):
                response = response[1:-1].strip()
        
        # Clean up excessive whitespace
        response = re.sub(r' +\n', '\n', response)  # Remove trailing spaces before newlines
        response = re.sub(r'\n{3,}', '\n\n', response)  # Max 2 consecutive newlines
        response = re.sub(r' {2,}', ' ', response)  # Remove multiple spaces
        
        # Clean up punctuation spacing
        response = re.sub(r' +\.', '.', response)  # Remove space before period
        response = re.sub(r' +\?', '?', response)  # Remove space before question mark
        response = re.sub(r' +!', '!', response)  # Remove space before exclamation
        response = re.sub(r' +,', ',', response)  # Remove space before comma
        
        # Fix punctuation repetition
        response = re.sub(r'\.{2,}(?!\.)', '.', response)  # Fix double periods (except ellipsis)
        response = re.sub(r'\?{2,}', '?', response)
        response = re.sub(r'!{2,}', '!', response)
        response = re.sub(r',{2,}', ',', response)
        
        # Fix spacing after punctuation
        response = re.sub(r'\.(?=[A-Z])', '. ', response)  # Add space after period before capital
        response = re.sub(r'\?(?=[A-Z])', '? ', response)  # Add space after ? before capital
        response = re.sub(r'!(?=[A-Z])', '! ', response)  # Add space after ! before capital
        
        # ✅ FIX: Remove extra space at the start of lines
        lines = response.split('\n')
        cleaned_lines = [line.strip() if line.strip() else '' for line in lines]
        response = '\n'.join(cleaned_lines)
        
        # Final cleanup
        response = response.strip()

        # ✅ CRITICAL FIX: More comprehensive patterns for suggestion statements
        statement_patterns = [
            # Direct suggestions/commands
            (r'(call|reach out to|contact) (them|someone|help)\s*\?', '.'),
            (r'(come back|return) anytime\s*\?', '.'),
            (r'(take care|be safe|stay safe)\s*\?', '.'),
            (r'(you can do this|you\'ve got this)\s*\?', '.'),
            (r'(that takes|that requires) \w+\s*\?', '.'),
            (r'(please|promise) \w+\s*\?', '.'),
            (r'i\'m here (anytime|whenever)\s*\?', '.'),
            
            # "Like" statements
            (r'like (things|are|is|seem|feel).{1,30}\?', '.'),
            (r'sounds? like .{1,30}\?', '.'),
            (r'seems? like .{1,30}\?', '.'),
            
            # Suggestions with "could/might"
            (r'(you could|could) (try|talk|speak).{1,50}\?', '.'),
            (r'(try|consider) (talking|speaking|reaching out).{1,50}\?', '.'),
            
            # ✅ NEW: "help" patterns (more general)
            (r'(would|might|could|may) help\s+\w+.{0,50}\?', '.'),  # "would help bridge..."
            (r'help (you|them|us|bridge|with|to).{0,50}\?', '.'),    # "help bridge that gap"
            
            # ✅ NEW: Keeping/maintaining patterns
            (r'(keeping|maintaining|having|getting) \w+.{0,40}\?', '.'),  # "keeping an umbrella"
            
            # ✅ NEW: Modal verbs in suggestions
            (r'(maybe|perhaps|possibly) \w+.{0,50}\?', '.'),  # "maybe keeping..."
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

        if context.emotional_tone == 'negative':
            normalized = re.sub(r'\.{3,}', '...', normalized)
            normalized = re.sub(r'(sad|hard|tough|difficult)\.{2,}', r'\1.', normalized)
        
        elif context.emotional_tone == 'positive':
            exclamation_count = normalized.count('!')
            if exclamation_count > 3:
                sentences = normalized.split('!')
                normalized_parts = []
                for i, sentence in enumerate(sentences):
                    if i < 2:
                        normalized_parts.append(sentence.strip() + '!')
                    else:
                        normalized_parts.append(sentence.strip() + '.')
                normalized = ' '.join(normalized_parts)
        
        filipino_patterns = [
            (r'\.{4,}', '...'),
            (r'\!{3,}', '!!'),
            (r'\?{2,}', '?'),
        ]
        
        for pattern, replacement in filipino_patterns:
            normalized = re.sub(pattern, replacement, normalized)

        return normalized

    # ========================================================================
    # ✅ IMPROVED: SMART VALIDATION WITH ASTERISK EXCEPTION FOR DISCLAIMERS
    # ========================================================================

    def validate_response(
        self,
        response: str,
        context: ConversationContext,
        user_message: str
    ) -> Tuple[bool, Optional[str]]:
        """
        ✅ UPDATED: Allows asterisks ONLY for AI disclaimers
        UNIVERSAL validation - adapts to message complexity and elements
        """

        user_lower = user_message.lower()
        user_wants_longer = any(phrase in user_lower for phrase in [
            'longer response', 'more detail', 'explain more', 'elaborate',
            'write longer', 'more words', 'expand on that'
        ])
        
        user_wants_shorter = any(phrase in user_lower for phrase in [
            'shorter', 'brief', 'concise', 'summarize', 'tl;dr', 'tl dr'
        ])
        
        task_info = self._detect_task_mode(user_message, context)
        
        # ✅ DYNAMIC WORD LIMITS based on message complexity
        if task_info['is_task']:
            word_limit = task_info['word_limit']
        elif user_wants_longer:
            word_limit = 180
        elif user_wants_shorter:
            word_limit = 80
        else:
            # ✅ UNIVERSAL: Adjust limit based on element count
            if context.message_elements:
                complexity = context.message_elements.get('complexity_score', 1)
                if complexity <= 1:
                    word_limit = 60  # Simple message
                elif complexity <= 3:
                    word_limit = 90  # Medium complexity
                elif complexity <= 5:
                    word_limit = 120  # Complex
                else:
                    word_limit = 150  # Very complex (multiple elements)
            else:
                word_limit = 120  # Default
        
        word_count = len(response.split())
        
        # ✅ NEW: SMART VALIDATION WITH 15-WORD GRACE PERIOD
        smart_limit = word_limit + 15  # Grace period for natural endings
        
        if word_count > smart_limit:
            return False, f"Exceeds {word_limit} words: {word_count} (hard limit: {smart_limit})"
        elif word_count > word_limit:
            # Check if overflow is justified (ends naturally)
            if response.strip().endswith(('.', '!', '?')):
                pass  # Allow it - ends naturally with proper punctuation
            else:
                return False, f"Exceeds {word_limit} words: {word_count} (incomplete thought)"
        
        # ✅ ALL OTHER VALIDATION RULES BELOW ARE PRESERVED FROM ORIGINAL
        
        common_emojis = '😊❤️💙🌟✨🙏🥺😢😭💪👍👏🎉'
        if any(char in response for char in common_emojis):
            return False, "Contains emoji (blocked common ones)"

        response_lower = response.lower()
        user_lower = user_message.lower()

        is_playful = (context.topic_type == 'playful_banter' or
                      'match_playful_energy' in context.implicit_requests)

        if is_playful:
            word_count = len(response.split())
            if word_count < 3:
                return False, "Too short even for playful response"
            if word_count > 45:
                return False, f"Too long for playful banter: {word_count} words"
            return True, None

        # ✅ UNIVERSAL: Validate critical elements are addressed
        if context.element_priorities:
            critical_elements = [k for k, v in context.element_priorities.items() if v == 1]
            
            for elem in critical_elements:
                if elem == 'name_change' and context.message_elements.get('has_name_change'):
                    new_name = context.message_elements.get('new_name')
                    if new_name and new_name.lower() not in response.lower():
                        return False, f"CRITICAL: Must acknowledge name change (use '{new_name}')"
                
                if elem == 'gratitude':
                    gratitude_acknowledgments = ['you\'re welcome', 'of course', 'no problem', 'glad', 'welcome']
                    if not any(phrase in response.lower() for phrase in gratitude_acknowledgments):
                        return False, "CRITICAL: Must acknowledge user's gratitude"

        # GOODBYE DETECTION
        goodbye_patterns = [
            r'\b(good ?night|goodnight|gnight|nite|sleep|bye|goodbye|see you|later|ttyl)\b',
            r'\bgoing to (sleep|bed)\b',
        ]

        if any(re.search(pattern, user_lower) for pattern in goodbye_patterns):
            # ✅ RELAXED: More generous limits for complex goodbye messages
            element_count = context.message_elements.get('element_count', 1) if context.message_elements else 1
            
            # More generous formula: 30 base + 10 per element (instead of 25 + 5)
            goodbye_limit = 30 + (element_count * 10)
            
            word_count = len(response.split())
            if word_count > goodbye_limit:
                return False, f"Goodbye response too long: {word_count} words (max {goodbye_limit} for {element_count} elements)"

        # STANDARD VALIDATION
        emoji_pattern = r'[\U0001F300-\U0001F9FF]|[\U0001F600-\U0001F64F]|[\U0001F680-\U0001F6FF]|[\U00002600-\U000027BF]|[:;][)(/\\|D]'
        if re.search(emoji_pattern, response):
            return False, "Contains emoji"

        # ✅ CRITICAL UPDATE: Check asterisks - ONLY exact disclaimer format allowed
        if '*' in response:
            # ONLY allow this EXACT format: *(I'm here to listen, but...talking to a professional...)*
            # Must have: parentheses + "I'm here to listen" + "professional"
            exact_disclaimer_pattern = r'\*\(I\'m here to listen, but for something this serious, talking to a professional would really help\.\)\*'
            
            # Also check for the shorter valid patterns
            valid_disclaimer_patterns = [
                r'\*\(I\'m here to listen, but for something this serious, talking to a professional would really help\.\)\*',
                r'\*\([^)]*\bI\'m here to listen\b[^)]*\bprofessional\b[^)]*\)\*',  # More flexible
            ]
            
            has_valid_disclaimer = any(re.search(pattern, response, re.IGNORECASE) for pattern in valid_disclaimer_patterns)
            
            if not has_valid_disclaimer:
                # Asterisks found but NOT in valid disclaimer format
                # Provide helpful error message showing what was found
                asterisk_context = response[max(0, response.index('*')-20):min(len(response), response.index('*')+50)]
                return False, f"Contains asterisks (*) for emphasis: '{asterisk_context}' - Remove all asterisks except AI disclaimer format: *(I'm here to listen...)*"

        gendered_terms = [r'\bman\b', r'\bbro\b', r'\bdude\b', r'\bgirl\b', r'\bsis\b', r'\bguys\b']
        for term in gendered_terms:
            if re.search(term, response_lower):
                return False, f"Contains gendered language: {term}"

        mild_profanity = [r'\bcrap\b', r'\bdamn\b', r'\bhell\b', r'\bass\b']
        for word in mild_profanity:
            if re.search(word, response_lower):
                return False, f"Contains mild profanity: {word}"

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

        interrogative_banned = [
            r'\bwant to share more about what happens\?',
            r'\bdo you want to talk about it\?',
            r'\bwould you like to share more\?',
            r'\bwant to tell me more\?',
            r'\bcare to elaborate\?',
            r'\bwould you like to elaborate\?',
            r'\bwhat\'?s coming up for you\?',
        ]
        
        for pattern in interrogative_banned:
            if re.search(pattern, response_lower):
                return False, f"Contains banned interrogative phrase (too therapist-like or unnecessary)"

        sucks_count = response_lower.count('sucks')
        if sucks_count > 1:
            return False, "Overused word 'sucks': use varied empathy phrases"

        honestly_count = response_lower.count('honestly')
        if honestly_count > 1:
            return False, "Overused word 'honestly': max once per response"

        if 'though honestly' in response_lower or 'honestly though' in response_lower:
            return False, "Verbal filler 'though honestly': sounds unnatural"

        if '•' in response:
            lines = response.split('\n')
            bullet_lines = [line for line in lines if '•' in line]

            for line in bullet_lines:
                bullet_count = line.count('•')
                if bullet_count > 1:
                    return False, "Multiple bullets on same line: put each on new line"

        ellipsis_count = response.count('...')
        if ellipsis_count > 1:
            return False, f"Too many ellipsis (...): {ellipsis_count} (use periods)"

        if re.search(r'(honestly|though|anyway)\.\.\.', response_lower):
            return False, "Ellipsis used as filler: use period instead"

        statement_patterns = [
            r'i\'?ll be (here|right here|around).*\?',
            r'i\'?m here (for you|anytime|whenever).*\?',
            r'(take care|sleep well|good night).*\?',
        ]

        for pattern in statement_patterns:
            if re.search(pattern, response_lower):
                return False, f"Statement ending with '?': use period instead"

        mid_statement_patterns = [
            r'like (things|are|is|seem|feel).{1,40}\?',
            r'sounds? like.{1,40}\?',
            r'seems? like.{1,40}\?',
        ]

        for pattern in mid_statement_patterns:
            if re.search(pattern, response_lower):
                return False, f"Mid-sentence statement with '?': use period instead"

        if context.expressing_gratitude:
            acknowledgment_phrases = [
                'of course', 'you\'re welcome', 'anytime', 'glad',
                'take care', 'be safe', 'stay safe', 'here for', 'welcome', 'no problem', 'no worries'
            ]

            if user_message:
                last_msg = user_message.lower()
                
                problem_patterns = [
                    r'\b(problem|issue|trouble|difficult|hard|struggle|can\'?t|cannot)\b',
                    r'\b(wrong|bad|awful|terrible|hate|dislike)\b',
                    r'\b(not (good|ok|okay|fine|working))\b',
                ]
                has_problem_content = any(re.search(p, last_msg) for p in problem_patterns)
                
                if has_problem_content:
                    first_sentence = response.split('.')[0].lower() if '.' in response else response.lower()
                    
                    if not any(phrase in first_sentence for phrase in acknowledgment_phrases):
                        return False, "Gratitude + Problem: Must acknowledge gratitude FIRST (start with 'You're welcome', 'Of course', etc.)"
                else:
                    if not any(phrase in response_lower for phrase in acknowledgment_phrases):
                        return False, "Didn't acknowledge user's gratitude"
            else:
                if not any(phrase in response_lower for phrase in acknowledgment_phrases):
                    return False, "Didn't acknowledge user's gratitude"

        if context.topic_type == 'feeling' or context.emotional_tone == 'negative':
            word_count = len(response.split())
            sentence_count = len([s for s in response.split('.') if s.strip()])

            if context.conversation_depth <= 3:
                if word_count < 15:  # ✅ RELAXED: 20 → 15
                    return False, f"Too brief for early emotional support: {word_count} words (need 15+)"

                user_word_count = len(user_message.split())

                # ✅ REMOVED: No longer require questions for emotional support
                # Questions are optional, validation only happens through empathy now

            else:
                if word_count < 25:
                    return False, f"Too brief for emotional support: {word_count} words (need 25+)"
                if sentence_count < 2:
                    return False, f"Not enough depth: only {sentence_count} sentences (need 2+)"

            if word_count > 110:
                return False, f"Emotional response too long: {word_count} words (prefer 110 or less)"

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

        if response.endswith('?'):
            inappropriate_questions = [
                r'call them\?',
                r'come back anytime\?',
                r'take care\?',
                r'be safe\?',
                r'you can do this\?',
                r'that takes \w+\?',
                r'i\'m here anytime\?',
            ]

            if any(re.search(pattern, response_lower) for pattern in inappropriate_questions):
                return False, "Inappropriate question mark on statement"

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

        therapist_patterns = [
            r'how are you (doing|feeling|today)',
            r'how (does|did) that make you feel',
            #r'your feelings are valid',
            r'i hear what you',
            r'hold space',
        ]

        for pattern in therapist_patterns:
            if re.search(pattern, response_lower):
                return False, f"Therapist language: {pattern}"

        awkward_patterns = [
            r'(what|how|why) \w+ if you want\?',
            r'^gotcha\.',
            r'\. gotcha\.',
            r'^got it\b',
            r'\. got it\b',
        ]

        user_is_acknowledging = user_message.strip().lower() in ['yep', 'yeah', 'yes', 'ok', 'okay', 'alright', 'sure']
        
        for pattern in awkward_patterns:
            if re.search(pattern, response_lower):
                if 'gotcha' in pattern:
                    if re.search(r'gotcha[!—,:]', response_lower):
                        continue
                    else:
                        return False, "Awkward grammar: using 'gotcha' as bare acknowledgment"
                        
                elif 'got it' in pattern:
                    if re.search(r'(she\'?s|he\'?s|they\'?ve|i\'?ve|you\'?ve|we\'?ve).{1,15}got', response_lower):
                        continue

                    if re.search(r'got it[—,!:\-]', response_lower):
                        continue

                    if any(word in response_lower for word in ['bye', 'goodbye', 'take care', 'see you', 'later']):
                        continue

                    if user_is_acknowledging:
                        return False, "Awkward: User said 'Yep' (acknowledging YOU), don't respond with 'Got it' (as if YOU're acknowledging THEM)"
                    
                    return False, "Awkward grammar: using 'got it' as acknowledgment"
                else:
                    return False, f"Awkward grammar: {pattern}"

        word_count = len(response.split())

        if word_count < 3:
            return False, "Too short"

        if word_count > 150:
            return False, f"Too wordy: {word_count} words (max 150)"

        sentences = [s.strip() for s in response.split('.') if s.strip()]
        for sentence in sentences:
            sentence_words = len(sentence.split())
            if sentence_words > 80:
                return False, f"Run-on sentence: {sentence_words} words (prefer 80 or less per sentence)"

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

        question_count = response.count('?')

        if question_count > 2:
            return False, f"Too many questions: {question_count}"

        if context.urgency_level == 'crisis':
            if 'resource' not in response_lower and 'help' not in response_lower:
                return False, "Crisis response must include resources"
            
        if context.disclosure_depth >= 4:
            # ✅ Check if disclaimer was shown (either full or gentle)
            has_full_disclaimer = bool(re.search(r'\*\([^)]*professional[^)]*\)\*', response_lower))
            has_gentle_encouragement = any(phrase in response_lower for phrase in [
                'professional', 'therapist', 'counselor', 'trained'
            ])
            
            if not (has_full_disclaimer or has_gentle_encouragement) and len(response.split()) > 40:
                import logging
                logger = logging.getLogger('snowfriend.validation')
                logger.info(f"Deep disclosure response without disclaimer: {response[:100]}")

        if context.user_corrections > 0:
            correction_phrases = ["didn't i", "i just said", "i already told"]
            if any(phrase in user_lower for phrase in correction_phrases):
                acknowledgment_phrases = ["you're right", "my bad", "sorry", "fair"]
                if not any(phrase in response_lower for phrase in acknowledgment_phrases):
                    return False, "Didn't acknowledge user correction"

        return True, None

    # ========================================================================
    # ✅ UNIVERSAL ELEMENT-AWARE FALLBACK
    # ========================================================================

    def generate_contextual_fallback(
        self,
        context: ConversationContext,
        conversation_history: List[Dict]
    ) -> str:
        """
        UNIVERSAL fallback - constructs response from detected elements
        """

        if context.emotional_tone == 'crisis' or context.urgency_level == 'crisis':
            return self._get_crisis_response()

        if conversation_history:
            last_msg_lower = conversation_history[-1]['content'].lower()
            goodbye_patterns = [r'\b(good ?night|goodnight|bye|goodbye|sleep)\b']
            if any(re.search(p, last_msg_lower) for p in goodbye_patterns):
                # ✅ UNIVERSAL: Check for name change
                if context.message_elements and context.message_elements.get('has_name_change'):
                    new_name = context.message_elements.get('new_name')
                    return f"Good night, {new_name}. I'm here whenever you need."
                else:
                    return "Good night. I'm here whenever you need."

        # ✅ UNIVERSAL: Construct fallback from elements
        if context.message_elements and context.element_priorities:
            return self._construct_element_fallback(context)

        # Generic fallback
        GLOBAL_FALLBACKS = [
            "Sorry, I couldn't process that properly. Could you try rephrasing it?",
            "Something didn't handle your message correctly on my end. Try wording it differently.",
            "I understood parts of your message, but I couldn't form a full response. Please rephrase.",
            "I'm having trouble responding to that input right now. Could you try another way of saying it?",
            "That didn't process as expected on my side. Try simplifying your message.",
            "I couldn't handle that response properly this time. Please try rewording it.",
            "Something went wrong while processing your message. Could you try again with different wording?",
            "I'm not able to respond properly to that right now. Try phrasing it another way.",
            "I caught parts of your message, but something didn't process correctly. Please rephrase.",
            "Sorry about that—your message didn't come together properly on my end. Try again?",
            "I'm having difficulty generating a response to that input. Could you restate it?",
            "That message was a bit complex for me to handle just now. Try rewording it.",
            "I couldn't respond to that as intended due to a processing issue. Please try again.",
            "Something didn't go quite right when handling your message. Try saying it differently.",
            "I wasn't able to process your message thoroughly this time. Could you rephrase it?",
        ]

        return random.choice(GLOBAL_FALLBACKS)

    def _construct_element_fallback(self, context: ConversationContext) -> str:
        """
        UNIVERSAL: Construct fallback response from detected elements
        Ensures critical elements are addressed even in fallback
        """
        elements = context.message_elements
        priorities = context.element_priorities
        
        parts = []
        
        # CRITICAL elements (Priority 1)
        if 'gratitude' in priorities and priorities['gratitude'] == 1:
            parts.append("You're welcome.")
        
        if 'name_change' in priorities and priorities['name_change'] == 1:
            new_name = elements.get('new_name')
            if new_name:
                if parts:
                    parts[-1] = parts[-1].rstrip('.') + f", {new_name}."
                else:
                    parts.append(f"I'll remember that, {new_name}.")
        
        # IMPORTANT elements (Priority 2)
        if 'goodbye' in priorities and priorities['goodbye'] == 2:
            if elements.get('has_goodbye'):
                if 'night' in context.implicit_requests or 'sleep' in elements.get('new_name', '').lower():
                    parts.append("Sleep well.")
                else:
                    parts.append("Take care.")
        
        if 'question' in priorities and priorities['question'] == 2:
            questions = elements.get('questions', [])
            if questions:
                parts.append("That's a good question.")
        
        # Closing
        if not any('bye' in p.lower() or 'sleep' in p.lower() for p in parts):
            parts.append("I'm here whenever you need.")
        
        return " ".join(parts)

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

    def _detect_task_mode(self, user_message: str, context: ConversationContext) -> Dict:
        """Detect if user wants help with a specific task"""
        msg_lower = user_message.lower()
        
        task_patterns = {
            'letter': [
                r'\b(christmas letter|holiday letter|greeting card|write.*letter)\b',
                r'\b(message for|note to|card for)\b',
                r'\b(tula|poem|sulat|liham)\b',
            ],
            'list': [
                r'\b(make a list|list of|things to|steps for)\b',
                r'\b(ideas for|suggestions for|options for)\b',
            ],
            'plan': [
                r'\b(plan for|schedule|organize|arrange)\b',
                r'\b(how to.*prepare|prepare for)\b',
            ]
        }
        
        for task_type, patterns in task_patterns.items():
            if any(re.search(p, msg_lower) for p in patterns):
                word_limit = 200 if task_type == 'letter' else 150
                
                instructions = {
                    'letter': 'Write in warm, personal tone. Keep it heartfelt but not overly formal.',
                    'list': 'Use bullet points with clear, actionable items.',
                    'plan': 'Provide step-by-step guidance in chronological order.'
                }
                
                return {
                    'is_task': True,
                    'task_type': task_type,
                    'word_limit': word_limit,
                    'instructions': instructions.get(task_type, '')
                }
        
        return {'is_task': False}