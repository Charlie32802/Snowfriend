# safety.py - ADVANCED CONTEXT-AWARE SAFETY SYSTEM
import re
from typing import Dict, List, Optional, Tuple

class ContentSafety:
    """
    ADVANCED CONTEXT-AWARE SAFETY SYSTEM
    Uses semantic understanding to distinguish real crisis from figurative language
    """
    
    @staticmethod
    def _extract_context_meaning(text: str) -> Dict[str, bool]:
        """
        Extract semantic meaning from text - understands what user is REALLY talking about
        Returns a dictionary of context flags
        """
        text_lower = text.lower()
        context = {
            'is_gaming': False,
            'is_school_work': False,
            'is_family_drama': False,
            'is_physical_injury': False,
            'is_tech_related': False,
            'is_idiomatic': False,
            'is_media_reference': False,
            'contains_hyperbole': False,
            'is_creative_writing': False,
        }
        
        # GAMING CONTEXT
        gaming_indicators = [
            r'\b(game|gaming|video game|playstation|xbox|nintendo|steam|epic games)\b',
            r'\b(zombie|monster|alien|enemy|boss|level|quest|mission|player|multiplayer)\b',
            r'\b(fps|rpg|mmo|strategy|action|adventure|simulation|sports)\b',
            r'\b(kill|shoot|attack|fight|defeat|destroy).{0,20}(zombie|monster|enemy|boss)\b',
            r'\b(call of duty|fortnite|minecraft|roblox|valorant|league of legends|dota)\b',
            r'\b(assault|warfare|battle|combat|fight).{0,20}(game|simulator|mode)\b',
        ]
        
        # SCHOOL/WORK CONTEXT
        school_work_indicators = [
            r'\b(school|college|university|class|homework|assignment|project|exam|test)\b',
            r'\b(work|job|office|boss|coworker|employee|employer|career|profession)\b',
            r'\b(OJT|internship|training|workshop|seminar|thesis|dissertation)\b',
            r'\b(code|coding|programming|develop|software|app|website|project)\b',
            r'\b(study|studying|learn|learning|practice|practicing|review|revising)\b',
            r'\b(deadline|due date|submission|presentation|report|paper|essay)\b',
        ]
        
        # FAMILY/RELATIONSHIP DRAMA (not abuse)
        family_drama_indicators = [
            r'\b(mom|mother|dad|father|parent|sibling|brother|sister|family)\b',
            r'\b(clean|tidy|organize).{0,20}(room|house|apartment|space)\b',
            r'\b(grounded|punished|in trouble|mad at|angry with|upset with)\b',
            r'\b(if i don\'t|unless i|or else|otherwise).{0,20}(clean|do|finish)\b',
            r'\b(typical|normal|usual).{0,20}(parent|family|mom|dad)\b',
        ]
        
        # MINOR PHYSICAL INJURY (not self-harm)
        minor_injury_indicators = [
            r'\b(hand|finger|arm|leg|foot|toe|back|shoulder|neck)\b',
            r'\b(hurt|pain|ache|sore|stiff|tired|exhausted|fatigued)\b',
            r'\b(after|from|because of|due to).{0,20}(open|lift|carry|move|exercise)\b',
            r'\b(can|jar|bottle|box|package|door|window|object)\b',
            r'\b(minor|small|little|slight|temporary|brief|momentary)\b',
        ]
        
        # TECH/CREATIVE CONTEXT
        tech_indicators = [
            r'\b(ai|chatgpt|gpt|artificial intelligence|machine learning)\b',
            r'\b(abuse|overuse|misuse|depend|rely).{0,20}(ai|chatgpt|gpt|tool)\b',
            r'\b(code|coding|program|software|app|website|project|portfolio)\b',
            r'\b(learn|practice|improve|develop|build|create|make|design)\b',
        ]
        
        # IDIOMATIC/HYPERBOLE EXPRESSIONS
        idiomatic_indicators = [
            r'\b(kill|murder|destroy|annihilate).{0,20}(me|you|us|them)\b',
            r'\b(i\'?m (dead|dying|finished|done for|toast|history))\b',
            r'\b(this will (kill|murder|destroy) me)\b',
            r'\b(i could (just )?die (of|from))\b',
            r'\b(i want to (die|kill myself) (from|because of))\b',
        ]
        
        # MEDIA/ENTERTAINMENT REFERENCES
        media_indicators = [
            r'\b(movie|film|tv|show|series|anime|manga|book|novel|comic)\b',
            r'\b(song|music|lyric|verse|chorus|album|artist|band)\b',
            r'\b(quote|reference|from the|in the|like in|similar to)\b',
            r'\b(".*"|\'.*\'|called|named|titled|entitled)\b',
        ]
        
        # Check each context
        context['is_gaming'] = any(re.search(pattern, text_lower) for pattern in gaming_indicators)
        context['is_school_work'] = any(re.search(pattern, text_lower) for pattern in school_work_indicators)
        context['is_family_drama'] = any(re.search(pattern, text_lower) for pattern in family_drama_indicators)
        context['is_physical_injury'] = any(re.search(pattern, text_lower) for pattern in minor_injury_indicators)
        context['is_tech_related'] = any(re.search(pattern, text_lower) for pattern in tech_indicators)
        context['is_idiomatic'] = any(re.search(pattern, text_lower) for pattern in idiomatic_indicators)
        context['is_media_reference'] = any(re.search(pattern, text_lower) for pattern in media_indicators)
        
        # HYPERBOLE DETECTION
        hyperbole_patterns = [
            r'\b(my (mom|dad|parent|boss|teacher) (is|will|is going to) (kill|murder) me)\b',
            r'\b(i could (just )?die (of|from) (embarrassment|shame|boredom))\b',
            r'\b(this (work|homework|project) is (killing|murdering) me)\b',
            r'\b(i\'?m so (tired|exhausted) i could (die|sleep for days))\b',
            r'\b(if i (don\'t|do) .{1,30} (i\'?ll die|i will die|kill me))\b',
        ]
        
        context['contains_hyperbole'] = any(re.search(pattern, text_lower) for pattern in hyperbole_patterns)
        
        # CREATIVE WRITING/STORYTELLING
        creative_patterns = [
            r'\b(story|plot|character|scene|chapter|setting|dialogue|narrative)\b',
            r'\b(write|writing|author|writer|novelist|poet|playwright)\b',
            r'\b(fiction|fantasy|sci-fi|science fiction|horror|mystery|romance)\b',
            r'\b(imagine|imagining|pretend|pretending|roleplay|role playing)\b',
        ]
        
        context['is_creative_writing'] = any(re.search(pattern, text_lower) for pattern in creative_patterns)
        
        return context
    
    @staticmethod
    def _is_figurative_language(text: str, context: Dict[str, bool]) -> bool:
        """
        Determine if violent/negative language is figurative, not literal
        """
        text_lower = text.lower()
        
        # If it's gaming/media/creative context, assume figurative
        if context['is_gaming'] or context['is_media_reference'] or context['is_creative_writing']:
            return True
        
        # Common figurative expressions
        figurative_patterns = [
            # Parental threats (hyperbole)
            r'\bmy (mom|mother|dad|father|parent) (is|will|is going to) (kill|murder) me (if|because)\b',
            
            # Exaggerated frustration
            r'\bi could (just )?die (of|from) (embarrassment|shame|boredom|frustration)\b',
            
            # Work/school stress hyperbole
            r'\bthis (work|homework|project|assignment|job) is (killing|murdering) me\b',
            
            # Fatigue exaggeration
            r'\bi\'?m so (tired|exhausted|sleepy) i could (die|sleep for days)\b',
            
            # Conditional hyperbole
            r'\bif i (don\'t|do) .{1,30} (i\'?ll die|i will die|kill me)\b',
            
            # Gaming language
            r'\b(kill|shoot|attack|destroy).{0,20}(zombie|monster|alien|enemy|boss|character)\b',
            
            # Storytelling
            r'\b(in the|in my|the character|the protagonist|the hero).{0,30}(kill|die|death)\b',
        ]
        
        if any(re.search(pattern, text_lower) for pattern in figurative_patterns):
            return True
        
        # Check for contextual clues of non-literal meaning
        if context['contains_hyperbole'] or context['is_idiomatic']:
            return True
        
        # Family drama with cleaning/chores context
        if context['is_family_drama'] and any(word in text_lower for word in ['clean', 'tidy', 'room', 'chore', 'homework']):
            return True
        
        # Minor physical complaints
        if context['is_physical_injury'] and any(word in text_lower for word in ['hand', 'finger', 'arm', 'leg', 'back', 'shoulder']):
            if not any(word in text_lower for word in ['cut', 'bleed', 'blood', 'wound', 'scar']):
                return True
        
        return False
    
    @staticmethod
    def _is_real_crisis(text: str, context: Dict[str, bool]) -> Tuple[bool, Optional[str]]:
        """
        Determine if text indicates REAL crisis (not figurative)
        Returns: (is_crisis: bool, category: str or None)
        """
        text_lower = text.lower()
    
        goodbye_note_patterns = [
            r'(write|writing|make|making|create|creating|draft|drafting|generate|generating|help.*with|compose|composing).{0,30}(goodbye|farewell|final|last|suicide).{0,20}(letter|note|message)',
            r'(goodbye|farewell|final|last|suicide).{0,20}(letter|note|message).{0,30}(to|for).{0,20}(family|friends|relatives|loved ones|everyone|parents|people)',
            r'request.*(goodbye|suicide|final).{0,20}(letter|note)',
            r'(roleplay|role.?play|act out|pretend).{0,40}(writing|write|creating|create).{0,20}(goodbye|farewell|final|suicide).{0,20}(letter|note|message)',
            r'(story|novel|character|scene).{0,40}(writing|writes|write).{0,20}(goodbye|farewell|final|suicide).{0,20}(letter|note)',
        ]
        
        if any(re.search(p, text_lower, re.IGNORECASE) for p in goodbye_note_patterns):
            return True, 'suicide'
        # ==========================================================

        # Now check for figurative language
        if ContentSafety._is_figurative_language(text, context):
            return False, None
        
        # ====================================================================
        # REAL CRISIS INDICATORS - Must be LITERAL
        # ====================================================================
        
        # SUICIDE/SELF-HARM (literal intent)
        literal_suicide_patterns = [
            r'\bi (want|wish|desire|hope) to (die|be dead|end my life|kill myself|commit suicide)\b',
            r'\bi (am|will be) (ending|taking) my life\b',
            r'\bi have (a|the) (plan|method|way|means) to (kill myself|end my life|commit suicide)\b',
            r'\bi (am going to|will) (kill myself|end it all|end my life)\b',
            r'\bthere\'?s no reason (for me )?to (live|go on|continue)\b',
            r'\beveryone (would be|will be) better off (without me|if i (was|were) dead)\b',
            r'\bi (can\'t|cannot) (take|handle|deal with) (this|it|life) anymore\b',
            r'\bi (have|am) nothing to live for\b',
            r'\b(before|prior to|in case) i (die|end my life|kill myself|take my own life|commit suicide)\b',
            r'\b(writing|write|make|create|draft).{0,30}(goodbye|farewell|final|last|suicide).{0,20}(letter|note|message)\b',
            r'\b(goodbye|farewell|final|last).{0,20}(letter|note|message).{0,30}(family|friends|loved ones|everyone)\b',
            r'\bi.?m (planning|thinking|considering|going) to (end|take) my (own )?life\b',
            r'\bi (don\'t|no longer) want to (live|be here|exist|go on)\b',
            r'\bi\'?m (done|finished) (with life|living)\b',
            r'\bnothing (left|to live for|worth living for)\b',
            r'\bi\'?m going to (end it|end it all|disappear|be gone forever)\b',
            r'\bthis is (my )?(final|last|goodbye|farewell)\b',
        ]
        
        # SELF-HARM BEHAVIOR
        self_harm_patterns = [
            r'\bi (cut|hurt|harm|burn|scratch) myself\b',
            r'\bi (want|feel like) (cutting|hurting|harming) myself\b',
            r'\bself.?harm|self.?injury\b',
        ]
        
        # PERSONAL VIOLENCE/ABUSE (not gaming/media)
        personal_violence_patterns = [
            r'\b(someone|he|she|they) (is|are) (abusing|hitting|beating|hurting) me\b',
            r'\bi (am|was) being (abused|beaten|hit|assaulted|attacked)\b',
            r'\b(domestic|family|partner) violence\b',
            r'\b(rape|sexual assault|molest|molestation)\b',
        ]
        
        # IMMINENT DANGER
        danger_patterns = [
            r'\bi (am|feel) (in danger|unsafe|threatened|endangered)\b',
            r'\bsomeone (is|will) (hurt|harm|kill) me\b',
            r'\bi (need|have to) get out (now|immediately|right away)\b',
            r'\bemergency situation\b',
        ]
        
        # Check for literal crisis indicators
        if any(re.search(pattern, text_lower) for pattern in literal_suicide_patterns):
            # Additional check: is it in gaming/media context?
            if not context['is_gaming'] and not context['is_media_reference']:
                return True, 'suicide'
        
        if any(re.search(pattern, text_lower) for pattern in self_harm_patterns):
            return True, 'self_harm'
        
        if any(re.search(pattern, text_lower) for pattern in personal_violence_patterns):
            if not context['is_gaming'] and not context['is_media_reference']:
                return True, 'violence'
        
        if any(re.search(pattern, text_lower) for pattern in danger_patterns):
            return True, 'danger'
        
        # EXISTENTIAL CRISIS (multiple indicators)
        existential_patterns = [
            r'\bwhat\'?s the (point|purpose|meaning) (of (life|everything|it all))\b',
            r'\beverything is (pointless|meaningless|useless|hopeless)\b',
            r'\bi (am|feel) (worthless|useless|hopeless|a failure|a burden)\b',
            r'\bnobody (cares|would care|would miss me) (if i (was|were) gone)\b',
        ]
        
        existential_count = sum(1 for p in existential_patterns if re.search(p, text_lower))

# Enhanced: Check for HIGH severity indicators (immediate crisis language)
        high_severity_patterns = [
            r'\bi (am|feel) (worthless|useless|hopeless|a burden) (and|,)',
            r'\bnobody (cares|would care|would miss me)',
            r'\beverything is (pointless|meaningless|hopeless)',
        ]
        high_severity_count = sum(1 for p in high_severity_patterns if re.search(p, text_lower))
# Trigger with: 2+ existential indicators OR 1+ high severity indicator
        if existential_count >= 2 or high_severity_count >= 1:
            return True, 'existential_crisis'
        
        return False, None
    
    @staticmethod
    def _get_crisis_response(category: str) -> str:
        """Get appropriate crisis response with PHILIPPINE numbers FIRST"""
        responses = {
            'suicide': (
                "I'm extremely concerned about what you've shared. Please reach out for help RIGHT NOW.\n\n"
                "🇵🇭 PHILIPPINE CRISIS HOTLINES (CALL IMMEDIATELY):\n"
                "• Emergency: 911\n"
                "• NCMH Crisis Hotline (24/7): 0917-899-8727 or 989-8727\n"
                "• Hopeline Philippines (24/7): (02) 8804-4673 or 0917-558-4673\n\n"
                "🌍 INTERNATIONAL:\n"
                "• US: 988 (Suicide & Crisis Lifeline)\n"
                "• Crisis Text Line: Text HOME to 741741\n"
                "• UK: 116 123 (Samaritans)\n\n"
                "Your life is valuable. These professionals can help you right now."
            ),
            'self_harm': (
                "I'm really concerned. Please reach out to a mental health professional immediately.\n\n"
                "🇵🇭 PHILIPPINE CRISIS HOTLINES (CALL NOW):\n"
                "• NCMH Crisis Hotline (24/7): 0917-899-8727 or 989-8727\n"
                "• Hopeline Philippines (24/7): (02) 8804-4673 or 0917-558-4673\n"
                "• Emergency: 911\n\n"
                "🌍 INTERNATIONAL:\n"
                "• Crisis Text Line: Text HOME to 741741\n"
                "• UK: 116 123 (Samaritans)\n\n"
                "You don't have to face this alone. Help is available."
            ),
            'violence': (
                "It sounds like you're in a dangerous situation. Please reach out for help:\n\n"
                "🇵🇭 PHILIPPINE HOTLINES:\n"
                "• Emergency: 911\n"
                "• PNP Hotline: (02) 8723-0401 to 20\n"
                "• PNP Women & Children Protection: (02) 3410-3213\n"
                "• DSWD Hotline: (02) 8931-8101 to 07\n\n"
                "Your safety is important. These professionals can help."
            ),
            'danger': (
                "Your safety is the priority right now. Please seek help:\n\n"
                "🇵🇭 PHILIPPINE:\n"
                "• Emergency: 911\n"
                "• PNP Hotline: (02) 8723-0401 to 20\n"
                "• NCMH Crisis: 0917-899-8727\n\n"
                "If you're in immediate danger, go to a safe place first."
            ),
            'existential_crisis': (
                "What you're describing sounds deeply painful. When feelings become overwhelming:\n\n"
                "🇵🇭 PHILIPPINE SUPPORT (24/7):\n"
                "• NCMH Crisis Hotline: 0917-899-8727 or 989-8727\n"
                "• Hopeline Philippines: (02) 8804-4673 or 0917-558-4673\n"
                "• Emergency: 911\n\n"
                "🌍 INTERNATIONAL:\n"
                "• Crisis Text Line: Text HOME to 741741\n\n"
                "These professionals are trained to help with exactly these feelings."
            ),
        }
        return responses.get(category, "Please reach out for professional support.")
    
    @staticmethod
    def check_content(text: str, conversation_history: List[Dict] = None) -> Tuple[bool, Optional[str], Optional[str], bool]:
        """
        ADVANCED CONTEXT-AWARE SAFETY CHECK
        Understands difference between figurative language and real crisis
        
        Returns: (is_safe: bool, category: str, response: str, needs_llm: bool)
        """
        if not text or len(text.strip()) < 3:
            return True, None, None, False
        
        # Step 1: Extract semantic context
        context = ContentSafety._extract_context_meaning(text)
        
        print(f"🔍 SAFETY CONTEXT ANALYSIS:")
        for key, value in context.items():
            if value:
                print(f"   {key}: {value}")
        
        # Step 2: Check for real crisis (not figurative)
        is_crisis, crisis_category = ContentSafety._is_real_crisis(text, context)
        
        if is_crisis:
            print(f"🚨 REAL CRISIS DETECTED: {crisis_category}")
            crisis_response = ContentSafety._get_crisis_response(crisis_category)
            return False, crisis_category, crisis_response, False
        
        # Step 3: Boundary checks (always enforce)
        text_lower = text.lower()
        
        # ROMANTIC BOUNDARIES (directed at bot)
        romantic_patterns = [
            r'\b(i )?(love|adore|worship|am in love with|have feelings for) you\b',
            r'\byou are (my|the) (everything|world|life|soulmate|perfect match)\b',
            r'\b(let\'?s|can we|should we) (date|kiss|marry|have sex|make love|hook up)\b',
            r'\bi (want|wish|desire) to (kiss|touch|be with|sleep with) you\b',
        ]
        
        for pattern in romantic_patterns:
            if re.search(pattern, text_lower):
                return False, 'boundary', "I'm here for emotional support. Let's focus on what you're experiencing.", False
        
        # DELUSIONAL/ROLEPLAY BOUNDARIES
        delusional_patterns = [
            r'\b(i am|i\'m) (god|jesus|christ|the messiah|the devil|satan|an angel)\b',
            r'\b(i can|i have the power to) (read minds|see the future|control thoughts)\b',
            r'\b(the (government|cia|fbi|aliens) (is|are) (watching|following|controlling) me)\b',
            r'\b(this is (all|everything) (a simulation|the matrix|not real|a dream))\b',
        ]
        
        for pattern in delusional_patterns:
            if re.search(pattern, text_lower):
                return False, 'boundary', "I'm here to talk about your real life experiences.", False
        
        # Step 4: Everything else is safe for normal conversation
        print(f"✅ CONTEXT SAFE: Allowing normal conversation")
        return True, None, None, False
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Enhanced input sanitization"""
        if not text:
            return ""
        
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'[<>\"\']', '', text)
        
        if len(text) > 1000:
            text = text[:1000] + " [message truncated]"
        
        return text
    
    @staticmethod
    def should_override_therapeutic_response(text: str, conversation_history: List[Dict] = None) -> Tuple[bool, Optional[str], Optional[str], bool]:
        """
        Check if content should trigger safety override
        Returns: (should_override, category, response, needs_llm)
        """
        is_safe, category, response, needs_llm = ContentSafety.check_content(text, conversation_history)
        return not is_safe, category, response, needs_llm