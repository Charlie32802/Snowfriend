# safety.py - UNIVERSAL CRISIS DETECTION SYSTEM
# ✅ UPDATED: Removed all asterisks from crisis responses to prevent validation issues
"""
COMPREHENSIVE SAFETY MODULE
- Universal crisis pattern detection
- Context-aware severity scoring
- Multiple crisis types (suicide, VAWC, abuse, self-harm)
- Appropriate hotlines for each crisis type
"""

import re
from typing import Tuple, List, Dict, Optional

class ContentSafety:
    """
    INTELLIGENT MULTI-LAYERED CRISIS DETECTION
    Detects ANY pattern indicating user is in danger
    """
    
    # ========================================================================
    # CRISIS TYPE 1: SUICIDE & SELF-HARM
    # ========================================================================
    
    SUICIDE_IMMEDIATE = [
        # Direct suicide intent
        r'\b(want to die|suicide|suicidal|kill myself|end (my )?life|no reason to live)\b',
        r'\b(better off dead|can\'?t go on|end it all|not worth living)\b',
        r'\b(planning to (die|kill myself)|going to (die|kill myself))\b',
        r'\b(tonight i\'?ll|today i\'?ll).{0,20}(die|end it|kill myself)\b',
        r'\b(goodbye (world|everyone)|this is (goodbye|the end))\b',
        r'\b(final (message|goodbye)|last (words|message))\b',
        
        # Method mentions
        r'\b(pills?|overdose|jump (off|from)|bridge|rope|gun|knife).{0,30}(myself|end|die)\b',
        r'\b(hanging myself|shoot myself|cut (my )?wrists?)\b',
    ]
    
    SELF_HARM_SEVERE = [
        r'\b(self[- ]?harm|cut myself|hurt myself|harm myself)\b',
        r'\b(cutting|burning|hitting) myself\b',
        r'\b(want to hurt|need to hurt|going to hurt) myself\b',
        r'\b(scars|wounds|blood).{0,20}(my|myself)\b',
    ]
    
    SUICIDE_SEVERE = [
        r'\b(can\'?t take it anymore|no way out|hopeless|no hope)\b',
        r'\b(everyone would be better|world would be better without me)\b',
        r'\b(gave up|giving up on life|done trying)\b',
        r'\b(nothing (left|to live for)|no point (in|to) living)\b',
        r'\b(tired of (living|life|everything))\b',
    ]
    
    # ========================================================================
    # CRISIS TYPE 2: DOMESTIC VIOLENCE / VAWC (Violence Against Women & Children)
    # ========================================================================
    
    DOMESTIC_VIOLENCE_IMMEDIATE = [
        # Physical violence by partner/family
        r'\b(husband|boyfriend|partner|father|dad).{0,30}(hit|beat|punch|kick|hurt|harm|attack|abuse)\b',
        r'\b(he|they) (hit|beat|punch|kick|hurt|harm|attack|abuse).{0,30}me\b',
        r'\b(beaten|hit|punched|kicked|hurt|attacked) (by|from).{0,30}(husband|boyfriend|partner|father)\b',
        
        # Sexual violence
        r'\b(force|forced|forcing) (me to|myself to).{0,20}(sex|sexual)\b',
        r'\b(rape|raped|sexual assault|molest)\b',
        r'\b(touch|touched|touching) me.{0,20}(inappropriately|sexually)\b',
        
        # Ongoing abuse
        r'\b(always|constantly|every (day|night)).{0,30}(hit|beat|hurt|abuse)\b',
        r'\b(scared|afraid|terrified).{0,30}(husband|boyfriend|partner|father)\b',
        r'\b(threatens?|threatening).{0,30}(to (kill|hurt|harm))\b',
    ]
    
    DOMESTIC_VIOLENCE_SEVERE = [
        r'\b(control|controls|controlling).{0,30}(everything|my life|me)\b',
        r'\b(not allowed|can\'?t|won\'?t let me).{0,30}(leave|go|talk to)\b',
        r'\b(trapped|prisoner|can\'?t escape)\b',
        r'\b(bruise|bruises|injury|injuries|wound|wounds)\b',
    ]
    
    # ========================================================================
    # CRISIS TYPE 3: CHILD ABUSE (if user is a minor)
    # ========================================================================
    
    CHILD_ABUSE_IMMEDIATE = [
        r'\b(parent|parents|mom|mother|dad|father|guardian).{0,30}(hit|beat|hurt|abuse|molest)\b',
        r'\b(uncle|aunt|cousin|relative|teacher).{0,30}(touch|touched|abuse|molest)\b',
        r'\b(not safe|unsafe|scared) (at home|home)\b',
    ]
    
    # ========================================================================
    # CRISIS TYPE 4: EMOTIONAL/PSYCHOLOGICAL DISTRESS
    # ========================================================================
    
    SEVERE_DISTRESS = [
        r'\b(depressed|depression|severely depressed|deeply depressed)\b',
        r'\b(alone (in this|in the world)|nobody cares|no one cares)\b',
        r'\b(can\'?t handle|too much to handle|overwhelmed beyond)\b',
        r'\b(breaking (down|apart)|falling apart|losing (it|my mind))\b',
        r'\b(panic attack|can\'?t breathe|hyperventilat)\b',
    ]
    
    # ========================================================================
    # FALSE POSITIVE FILTERS
    # ========================================================================
    
    FALSE_POSITIVE_INDICATORS = {
        'hypothetical': [
            r'\b(what if|suppose|imagine|wonder if|thinking about)\b',
            r'\b(would (never|not)|wouldn\'?t actually|not really)\b',
            r'\b(just (thinking|wondering|curious)|curious about)\b',
        ],
        'past_tense': [
            r'\b(used to|in the past|before|previously|long ago)\b',
            r'\b(was feeling|felt like|had thoughts)\b',
            r'\b(not anymore|no longer|stopped)\b',
        ],
        'discussion': [
            r'\b(read about|heard about|saw something about)\b',
            r'\b(someone (else|i know)|friend|family member)\b',
            r'\b(article|news|story) about\b',
        ],
        'family_drama': [
            r'\b(mom|mother|dad|father|parent).{0,30}(mad|angry|upset|grounded)\b',
            r'\b(clean|tidy).{0,20}(room|house|apartment)\b',
            r'\b(if i don\'t|unless i|or else).{0,20}(clean|do|finish)\b',
            r'\b(typical|normal|usual).{0,20}(parent|family)\b',
        ],
    }
    
    # ========================================================================
    # UNIVERSAL CRISIS SCORING SYSTEM
    # ========================================================================
    
    @staticmethod
    def calculate_crisis_score(
        text: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Tuple[int, str, List[str]]:
        """
        UNIVERSAL CRISIS SCORING
        
        Returns:
            (score, crisis_type, matched_patterns)
            
        Score ranges:
            0-2: Safe
            3-5: Moderate concern
            6-8: Severe distress
            9-10: IMMEDIATE CRISIS
        """
        text_lower = text.lower()
        score = 0
        crisis_types = []
        matched_patterns = []
        
        # Check for false positives FIRST
        if ContentSafety._is_false_positive(text_lower, conversation_history):
            return (0, 'safe', [])
        
        # ============================================================
        # SCORE CALCULATION
        # ============================================================
        
        # SUICIDE (highest priority)
        for pattern in ContentSafety.SUICIDE_IMMEDIATE:
            if re.search(pattern, text_lower):
                score += 10  # Immediate crisis
                crisis_types.append('suicide')
                matched_patterns.append(pattern)
                break  # Stop checking, already at max
        
        if score < 10:  # Only check if not already max
            for pattern in ContentSafety.SELF_HARM_SEVERE:
                if re.search(pattern, text_lower):
                    score += 8
                    crisis_types.append('self_harm')
                    matched_patterns.append(pattern)
        
        if score < 10:
            for pattern in ContentSafety.SUICIDE_SEVERE:
                if re.search(pattern, text_lower):
                    score += 7
                    crisis_types.append('suicide_ideation')
                    matched_patterns.append(pattern)
        
        # DOMESTIC VIOLENCE
        for pattern in ContentSafety.DOMESTIC_VIOLENCE_IMMEDIATE:
            if re.search(pattern, text_lower):
                score = max(score, 10)  # Immediate crisis
                crisis_types.append('domestic_violence')
                matched_patterns.append(pattern)
                break
        
        if score < 10:
            for pattern in ContentSafety.DOMESTIC_VIOLENCE_SEVERE:
                if re.search(pattern, text_lower):
                    score = max(score, 8)
                    crisis_types.append('domestic_violence')
                    matched_patterns.append(pattern)
        
        # CHILD ABUSE
        for pattern in ContentSafety.CHILD_ABUSE_IMMEDIATE:
            if re.search(pattern, text_lower):
                score = max(score, 10)  # Immediate crisis
                crisis_types.append('child_abuse')
                matched_patterns.append(pattern)
                break
        
        # SEVERE EMOTIONAL DISTRESS
        distress_count = 0
        for pattern in ContentSafety.SEVERE_DISTRESS:
            if re.search(pattern, text_lower):
                distress_count += 1
                matched_patterns.append(pattern)
        
        if distress_count >= 2:
            score = max(score, 7)
            crisis_types.append('severe_distress')
        elif distress_count == 1:
            score = max(score, 5)
            crisis_types.append('moderate_distress')
        
        # Determine primary crisis type
        if crisis_types:
            primary_type = crisis_types[0]  # First detected type
        else:
            primary_type = 'safe'
        
        return (score, primary_type, matched_patterns)
    
    # ========================================================================
    # MAIN SAFETY CHECK
    # ========================================================================
    
    @staticmethod
    def check_content(
        message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Tuple[bool, str, str, bool]:
        """
        COMPREHENSIVE SAFETY CHECK
        
        Returns:
            (is_safe, category, safety_response, needs_llm)
        """
        # Calculate crisis score
        score, crisis_type, patterns = ContentSafety.calculate_crisis_score(
            message, conversation_history
        )
        
        # IMMEDIATE CRISIS (score 9-10)
        if score >= 9:
            if crisis_type == 'suicide':
                response = ContentSafety._get_suicide_crisis_response()
            elif crisis_type == 'domestic_violence':
                response = ContentSafety._get_domestic_violence_response()
            elif crisis_type == 'child_abuse':
                response = ContentSafety._get_child_abuse_response()
            elif crisis_type == 'self_harm':
                response = ContentSafety._get_self_harm_response()
            else:
                response = ContentSafety._get_general_crisis_response()
            
            return (False, crisis_type, response, False)
        
        # SEVERE CONCERN (score 6-8)
        elif score >= 6:
            # Let LLM handle with crisis-aware context
            return (True, crisis_type, None, True)
        
        # MODERATE CONCERN (score 3-5)
        elif score >= 3:
            # Let LLM handle normally but be supportive
            return (True, crisis_type, None, True)
        
        # SAFE (score 0-2)
        else:
            return (True, None, None, True)
    
    # ========================================================================
    # ✅ UPDATED: CRISIS RESPONSE TEMPLATES (NO ASTERISKS)
    # ========================================================================
    
    @staticmethod
    def _get_suicide_crisis_response() -> str:
        """Suicide crisis response with comprehensive hotlines - NO ASTERISKS"""
        return """I'm deeply concerned about what you've shared. Your life matters, and help is available right now.

🚨 PLEASE REACH OUT IMMEDIATELY:

🇵🇭 PHILIPPINES - 24/7 CRISIS SUPPORT:
• NCMH Crisis Hotline: 0917-899-8727 or 989-8727
• Hopeline Philippines: (02) 8804-4673 or 0917-558-4673
• Mental Health Crisis Hotline: 0919-057-1553
• Tawag Paglaum:
  - SMART/TNT: 0939-936-5433 / 0939-937-5433
  - GLOBE/TM: 0966-467-9626
• Emergency Services: 911

🌍 INTERNATIONAL:
• US: 988 (Suicide & Crisis Lifeline)
• Crisis Text Line: Text HOME to 741741
• UK: 116 123 (Samaritans)
• Canada: 1-833-456-4566
• Australia: 13 11 14 (Lifeline)

These are trained professionals who can help you right now. Please reach out - you don't have to face this alone."""
    
    @staticmethod
    def _get_domestic_violence_response() -> str:
        """VAWC/Domestic violence response with specialized hotlines - NO ASTERISKS"""
        return """I'm very concerned about your safety. What you're describing sounds dangerous, and you deserve to be safe.

🚨 IMMEDIATE SAFETY RESOURCES:

🇵🇭 DOMESTIC VIOLENCE & VAWC SUPPORT:
• Emergency Services: 911 (for immediate danger)
• Philippine National Police: 0998-539-8568
• NCMH Crisis Hotline: 0917-899-8727 or 989-8727
• Tawag Paglaum:
  - SMART/TNT: 0939-936-5433 / 0939-937-5433
  - GLOBE/TM: 0966-467-9626

REGIONAL CRISIS HOTLINES:
• Cagayan Valley Medical Center: 0929-646-2625 / 0967-125-7906
• Zamboanga City Medical Center: 0938-300-4003 / 0936-491-9398
• LGU Quezon City: 122
• LGU Cavite Province: 0977-006-9226 / 0930-763-6069

🌍 INTERNATIONAL:
• US Domestic Violence Hotline: 1-800-799-7233
• UK Domestic Abuse Helpline: 0808 2000 247

If you're in immediate danger, please call 911 or go to a safe place. These resources are here to help you."""
    
    @staticmethod
    def _get_child_abuse_response() -> str:
        """Child abuse response with appropriate hotlines - NO ASTERISKS"""
        return """I'm very concerned about what you've shared. What you're describing sounds unsafe, and you deserve to be protected.

🚨 HELP IS AVAILABLE:

🇵🇭 CHILD PROTECTION:
• Emergency Services: 911
• Philippine National Police: 0998-539-8568
• NCMH Crisis Hotline: 0917-899-8727 or 989-8727
• Mental Health Crisis Hotline: 0919-057-1553
• Tawag Paglaum:
  - SMART/TNT: 0939-936-5433 / 0939-937-5433
  - GLOBE/TM: 0966-467-9626

REGIONAL SUPPORT:
• Baguio General Hospital: 0956-991-6841
• Taguig City Health Office: 0929-521-8373 / 0967-039-3456
• BARMM Mental Health Unit: 0962-683-2476 / 0953-884-2462

🌍 INTERNATIONAL:
• US Childhelp Hotline: 1-800-422-4453
• UK NSPCC: 0808 800 5000

Please reach out to someone you trust or call one of these numbers. You're not alone, and help is available."""
    
    @staticmethod
    def _get_self_harm_response() -> str:
        """Self-harm crisis response - NO ASTERISKS"""
        return """I'm really concerned about you. Self-harm is a sign that you're going through something very difficult, and you deserve support.

🚨 PLEASE REACH OUT:

🇵🇭 IMMEDIATE SUPPORT:
• NCMH Crisis Hotline: 0917-899-8727 or 989-8727
• Mental Health Crisis Hotline: 0919-057-1553
• Hopeline Philippines: (02) 8804-4673 or 0917-558-4673
• Emergency Services: 911
• Tawag Paglaum:
  - SMART/TNT: 0939-936-5433 / 0939-937-5433
  - GLOBE/TM: 0966-467-9626

REGIONAL HOTLINES:
• Philippine Navy Crisis Hotline: 0939-982-8339 / 0917-512-8339
• Bureau of Fire Protection: 0962-4584-237

🌍 INTERNATIONAL:
• US: 988 (Suicide & Crisis Lifeline)
• Crisis Text Line: Text HOME to 741741

These professionals can help you find safer ways to cope. Please reach out."""
    
    @staticmethod
    def _get_general_crisis_response() -> str:
        """General crisis response - NO ASTERISKS"""
        return """I'm concerned about what you're going through. Please reach out for support:

🇵🇭 24/7 CRISIS SUPPORT:
• Emergency: 911
• NCMH Crisis Hotline: 0917-899-8727 or 989-8727
• Mental Health Crisis: 0919-057-1553
• Tawag Paglaum: 0939-936-5433 / 0966-467-9626

🌍 INTERNATIONAL:
• US: 988
• Crisis Text Line: Text HOME to 741741

You don't have to face this alone. Help is available right now."""
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    @staticmethod
    def _is_false_positive(text: str, conversation_history: Optional[List[Dict]]) -> bool:
        """Check if crisis keywords are false positives"""
        for category, patterns in ContentSafety.FALSE_POSITIVE_INDICATORS.items():
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                return True
        
        # Check if user is questioning previous crisis response
        if conversation_history:
            last_bot_msg = None
            for msg in reversed(conversation_history):
                if msg['role'] == 'assistant':
                    last_bot_msg = msg['content'].lower()
                    break
            
            if last_bot_msg and 'crisis hotline' in last_bot_msg:
                questioning_patterns = [
                    r'\b(what|why).{0,20}(concern|worry)',
                    r'\bjust (a|an)\b',
                    r'\bwhat are you.{0,20}(concern|worry|talking about)',
                ]
                if any(re.search(p, text, re.IGNORECASE) for p in questioning_patterns):
                    return True
        
        return False
    
    @staticmethod
    def should_override_therapeutic_response(
        message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Tuple[bool, str, str, bool]:
        """Alias for backward compatibility"""
        return ContentSafety.check_content(message, conversation_history)
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        text = text.strip()
        
        return text