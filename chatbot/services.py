#services.py
import os
import random
import requests
import json
import re
from typing import Dict, List, Optional, Generator
from dotenv import load_dotenv
import time

from .response_generator import ResponseGenerator, API_FAILURE_FALLBACKS
from .context_analyzer import ContextAnalyzer   

load_dotenv()


class LLMService:
    """
    Intelligent LLM Service with MULTI-MODEL FALLBACK
    ✅ FIXED: Enhanced artifact removal for <|im_end_id|>, meta-commentary, Session markers
    ✅ FIXED: Stricter gibberish detection to catch nonsense responses
    ✅ NEW: Preserves [[EMAIL]] and [[FEEDBACK]] markers for API failure fallbacks
    """
    
    def __init__(self):
        """Initialize LLM service with multiple model options"""
        self.api_key = os.getenv('OPENROUTER_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_KEY not found in environment variables")
        
        self.api_base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        self.models = [
            {
                'name': 'mistralai/mistral-7b-instruct:free',
                'description': 'Mistral 7B Instruct - Free',
                'max_tokens': 8000,
                'temperature': 1.0,
                'priority': 1
            }
        ]
        
        self.system_prompt_version = "2.1.0" 
        self.current_model_index = 0
        self.streaming_timeout = 15 
        self.regular_timeout = 30  
        self.response_generator = ResponseGenerator()
        self.context_analyzer = ContextAnalyzer()
        
        print(f"✓ LLM Service initialized with {len(self.models)} fallback models")
        print(f"  Primary: {self.models[0]['name']}")
        print(f"  System Prompt Version: {self.system_prompt_version}")
    
    # ========================================================================
    # ✅ EMOJI FILTERING
    # ========================================================================
    
    def _remove_emojis(self, text: str) -> str:
        """Remove ALL emojis from text"""
        if not text:
            return ""
        
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F"
            "\U0001FA70-\U0001FAFF"
            "\U00002600-\U000026FF"
            "\U00002700-\U000027BF"
            "]+",
            flags=re.UNICODE
        )
        
        text = emoji_pattern.sub('', text)
        text = re.sub(r'  +', ' ', text)
        
        return text
    
    # ========================================================================
    # ✅ NEW: ASTERISK REPLACEMENT
    # ========================================================================
    
    def _replace_asterisks_with_quotes(self, text: str) -> str:
        """
        Replace asterisks used for emphasis with quotes
        Preserves AI disclaimer format: *(I'm here to listen...)*
        
        Rules:
        - 1-2 words: single quotes 'word'
        - 3+ words: double quotes "phrase"
        """
        if not text or '*' not in text:
            return text
        
        # Check if text contains valid AI disclaimer
        disclaimer_pattern = r'\*\([^)]*I\'m here to listen[^)]*professional[^)]*\)\*'
        has_disclaimer = re.search(disclaimer_pattern, text, re.IGNORECASE)
        
        if has_disclaimer:
            disclaimer = has_disclaimer.group(0)
            text_without_disclaimer = text.replace(disclaimer, '<<<DISCLAIMER_PLACEHOLDER>>>')
            processed_text = self._replace_asterisks_in_text(text_without_disclaimer)
            return processed_text.replace('<<<DISCLAIMER_PLACEHOLDER>>>', disclaimer)
        else:
            return self._replace_asterisks_in_text(text)
    
    def _replace_asterisks_in_text(self, text: str) -> str:
        """Helper to replace asterisks with appropriate quotes"""
        pattern = r'\*([^*]+)\*'
        
        def replace_with_quotes(match):
            content = match.group(1)
            word_count = len(content.split())
            
            # Single word or short phrase: single quotes
            if word_count <= 2:
                return f"'{content}'"
            # Longer phrase: double quotes
            else:
                return f'"{content}"'
        
        return re.sub(pattern, replace_with_quotes, text)
    
    def _fix_bullet_list_spacing(self, text: str) -> str:
        """
        Ensure proper spacing for bullet lists
        Adds blank line before list
        """
        if not text:
            return text
        
        lines = text.split('\n')
        fixed_lines = []
        in_list = False
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            is_list_item = line_stripped.startswith(('- ', '• ', '* ', '1. ', '2. ', '3. '))
            
            # Entering a list
            if is_list_item and not in_list:
                # Add blank line before list (if previous line wasn't empty)
                if i > 0 and fixed_lines and fixed_lines[-1].strip():
                    fixed_lines.append('')
                in_list = True
            
            # Exiting a list
            if not is_list_item and in_list and line_stripped:
                in_list = False
                # Add blank line after list
                if fixed_lines and fixed_lines[-1].strip():
                    fixed_lines.append('')
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    # ========================================================================
    # ✅ FIXED: UNIVERSAL TEXT CLEANING WITH FALLBACK MARKER PRESERVATION
    # ========================================================================
    
    def _clean_text(self, text: str) -> str:
        """
        Universal text cleaning with intelligent instruction leak detection
        - ✅ NEW: Intelligent instruction leak detector (catches ANY prompt leaks)
        - ✅ FIXED: Enhanced artifact removal (catches <|im_end_id|>, meta-commentary, Session markers)
        - ✅ NEW: Preserves [[EMAIL]] and [[FEEDBACK]] markers for API failure fallback messages
        - ✅ FIXED: Aggressive leading quote removal (all quote types)
        - Removes emojis
        - Replaces asterisks with quotes
        - Fixes list spacing
        - Cleans whitespace
        - ✅ FIXED: Stricter gibberish detection
        """
        if not text:
            return ""
        
        text = re.sub(r'<\/?[a-z_]+(?:\|[a-z_]+)*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<\|[^>]+\|>', '', text)
    
        # ✅ NEW: STEP 1 - Detect and remove leaked instructions FIRST
        text = self._remove_leaked_instructions(text)
    
        # ✅ STEP 2: Remove ALL types of leading quotes
        leading_quote_chars = ['"', "'", '"', '"', ''', ''', '„', '‟', '«', '»', '`']
        while text and text[0] in leading_quote_chars:
            text = text[1:].strip()

        # Also remove trailing quotes
        while text and text[-1] in leading_quote_chars:
            text = text[:-1].strip()

        has_fallback_markers = '[[EMAIL:' in text or '[[FEEDBACK:' in text
        
        if has_fallback_markers:
            # This is a fallback message - only do minimal cleaning
            print("✓ Detected API fallback message - preserving [[EMAIL]] and [[FEEDBACK]] markers")
            
            # Only remove obvious artifacts, but preserve markers
            text = text.replace('<|im_end|>', '').replace('<|im_end_id|>', '')
            text = text.replace('<|im_start|>', '')
            text = text.replace('Session end.', '').replace('Session begin.', '')
            
            # Remove emojis
            text = self._remove_emojis(text)
            
            # Basic whitespace cleanup
            text = ' '.join(text.split())
            
            # Return early without aggressive cleaning
            return text.strip()
        
        # ✅ CRITICAL: Check for gibberish FIRST (for non-fallback messages)
        if self._contains_gibberish(text):
            print(f"⚠️ Gibberish detected in response: {text[:100]}...")
            return ""  # Return empty to trigger fallback
        
        # ✅ CRITICAL: Remove model artifacts FIRST (EXPANDED LIST)
        artifact_patterns = [
            # Original artifacts
            r'\[\/(?:INST|B_INST)\]',
            r'\[/.*?\]',
            r'<s>|<\/s>',
            r'^Assistant:\s*',
            r'^Snowfriend:\s*',
            r'^\s*\(\s*I\'m',
            r'\[\s*assistant\s*\]',
            
            # ✅ NEW: LLM training artifacts
            r'<\|im_end(_id)?\|>',  # Catches <|im_end|> and <|im_end_id|>
            r'<\|im_start\|>',
            r'<\|.*?\|>',  # Any other special tokens
            
            # ✅ NEW: Session markers
            r'Session\s+(end|begin)\.',
            r'Session\s+(end|begin)\.<\|im_end_id\|>',
            
            # ✅ NEW: Meta-commentary in brackets (these should NEVER appear in user-facing text)
            r'\[YOU SHOULD\'?VE SAID:.*?\]',
            r'\[A BETTER RESPONSE WOULD BE:.*?\]',
            r'\[CORRECT RESPONSE:.*?\]',
            r'\[NOTE:.*?\]',
            r'\[IMPORTANT:.*?\]',
            r'\[INSTEAD:.*?\]',
            r'\[FIX:.*?\]',
        ]
        
        for pattern in artifact_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Direct string replacements for common artifacts
        text = text.replace('[/INST]', '').replace('[/B_INST]', '')
        text = text.replace('<s>', '').replace('</s>', '')
        text = text.replace('[assistant]', '').replace('[ASSISTANT]', '')
        text = text.replace('Assistant:', '').replace('Snowfriend:', '')
        text = text.replace('<|im_end|>', '').replace('<|im_end_id|>', '')
        text = text.replace('<|im_start|>', '')
        text = text.replace('Session end.', '').replace('Session begin.', '')
        
        # Remove emojis
        text = self._remove_emojis(text)
        
        # ✅ NEW: Remove confusing parenthetical statements
        confusing_patterns = [
            r'\(can\'t recall you mentioning it already[^)]*\)',
            r'\(if the fact is better known\)',
            r'\(not sure if[^)]*\)',
        ]
        
        for pattern in confusing_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Replace asterisks (preserve disclaimers)
        text = self._replace_asterisks_with_quotes(text)
        
        # Clean up line breaks
        lines = text.split('\n')
        cleaned_lines = []
        consecutive_empty = 0
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped:
                line_cleaned = ' '.join(line_stripped.split())
                cleaned_lines.append(line_cleaned)
                consecutive_empty = 0
            else:
                consecutive_empty += 1
                if consecutive_empty <= 1:
                    cleaned_lines.append('')
        
        text = '\n'.join(cleaned_lines)
        
        # Fix bullet list spacing
        text = self._fix_bullet_list_spacing(text)
        
        # Remove trailing whitespace
        text = text.strip()
        
        # Remove double punctuation
        text = text.replace('..', '.').replace(',,', ',').replace('??', '?').replace('!!', '!')
        
        # ✅ NEW: Fix incomplete sentences ending with "or?", "and?", etc.
        text = re.sub(r',?\s+(or|and|but)\?\s*$', '.', text, flags=re.IGNORECASE)
        
        # Final cleanup: remove any remaining artifact-like text
        if text.startswith('(') and text.endswith(')'):
            if not ("I'm here to listen" in text and "professional" in text):
                text = text[1:-1].strip()
        
        return text
    
    def _remove_leaked_instructions(self, text: str) -> str:
        """
        ✅ INTELLIGENT INSTRUCTION LEAK DETECTOR
    
        Detects when LLM starts leaking system prompt instructions
        and cuts off the response at that point.
    
        Detection signals:
        - High density of instruction keywords (MUST, NEVER, CRITICAL, etc.)
        - Presence of formatting markers (⚠️, 🚨, ✅, ❌)
        - Numbered/bulleted rule lists
        - Meta-commentary about response format
        - Sudden shift from conversational to instructional tone
        """
        if not text or len(text) < 50:
            return text
        
        text = re.sub(r'\n*```\s*$', '', text) 
        text = re.sub(r'^```\s*\n*', '', text)
    
        # Split into paragraphs (double newline separated)
        paragraphs = text.split('\n\n')
    
        # Analyze each paragraph for "instruction-like" characteristics
        cleaned_paragraphs = []
        found_leak = False
    
        for i, para in enumerate(paragraphs):
            para_stripped = para.strip()
        
            if not para_stripped:
                cleaned_paragraphs.append('')
                continue
        
            # Calculate "instruction score" for this paragraph
            instruction_score = 0
        
            # Signal 1: Instruction keywords (high weight)
            instruction_keywords = [
                'CRITICAL', 'MUST', 'NEVER', 'ALWAYS', 'REQUIRED', 'FORBIDDEN',
                'IMPORTANT', 'MANDATORY', 'STRICTLY', 'ABSOLUTELY', 'DO NOT',
                'YOU SHOULD', 'YOU MUST', 'ENSURE', 'MAKE SURE', 'REMEMBER TO'
            ]
            keyword_count = sum(1 for keyword in instruction_keywords if keyword in para_stripped.upper())
            instruction_score += keyword_count * 3
        
            # Signal 2: Warning emojis (medium weight)
            warning_emojis = ['⚠️', '🚨', '✅', '❌', '🔒', '📋', '🎯']
            emoji_count = sum(1 for emoji in warning_emojis if emoji in para_stripped)
            instruction_score += emoji_count * 2
        
             # Signal 3: Numbered rules pattern (high weight)
            if re.search(r'^\s*\d+[\.\)]\s+', para_stripped, re.MULTILINE):
                instruction_score += 4
        
            # Signal 4: "Rules" or "Guidelines" headings (high weight)
            rule_headings = [
                'RULES:', 'GUIDELINES:', 'INSTRUCTIONS:', 'REQUIREMENTS:',
                'CONSTRAINTS:', 'PRINCIPLES:', 'WHAT TO DO NEXT:'
            ]
            if any(heading in para_stripped.upper() for heading in rule_headings):
                instruction_score += 5
        
            # Signal 5: Meta-commentary brackets (high weight)
            if re.search(r'\[(CORRECT|WRONG|NOTE|IMPORTANT|FIX|INSTEAD)\]', para_stripped, re.IGNORECASE):
                instruction_score += 4
        
            # Signal 6: Excessive capitalization (medium weight)
            words = para_stripped.split()
            if len(words) > 5:
                caps_ratio = sum(1 for word in words if word.isupper() and len(word) > 2) / len(words)
                if caps_ratio > 0.3:
                    instruction_score += 3
        
            # Signal 7: Colon-separated directives (medium weight)
            directive_pattern = r'^[A-Z][a-z\s]+:\s*$'
            if re.search(directive_pattern, para_stripped, re.MULTILINE):
                instruction_score += 2
        
             # Signal 8: Position in response (context weight)
            if i > 2:  # After the first 2 paragraphs
                instruction_score += 1
        
            # ✅ DECISION THRESHOLD
            if instruction_score >= 8:
                print(f"⚠️ Instruction leak detected (score: {instruction_score})")
                print(f"   Truncating at: '{para_stripped[:80]}...'")
                found_leak = True
                break
        
            # Borderline check
            elif instruction_score >= 5:
                conversational_markers = [
                    "I understand", "I hear", "I'm here", "You", "your", 
                    "sounds like", "seems like", "that's", "I think"
                ]
                has_conversational_tone = any(
                    marker.lower() in para_stripped.lower() 
                    for marker in conversational_markers
                )
            
                if not has_conversational_tone:
                    print(f"⚠️ Borderline instruction leak detected (score: {instruction_score})")
                    print(f"   Truncating at: '{para_stripped[:80]}...'")
                    found_leak = True
                    break
        
            # This paragraph is safe
            cleaned_paragraphs.append(para)
    
        if found_leak:
            return '\n\n'.join(cleaned_paragraphs).strip()
    
        return text
    
    def _contains_gibberish(self, text: str) -> bool:
        """
        ✅ FIXED: Stricter gibberish detection
        Returns True if gibberish detected
        """
        if not text:
            return True
        
        # ✅ CRITICAL: Must have at least 3 characters
        if len(text.strip()) < 3:
            return True
        
        # ✅ NEW: Check for known gibberish patterns
        gibberish_patterns = [
            r'\bNASR\b',  # Random acronyms
            r'\bnigga\b',  # Slurs/offensive language
            r'\bmintysauce\b',  # Nonsense words
            r'\bnfty\b',  # Random short "words"
            r'\bThey be knowin\b',  # Broken grammar
            r'\billuminating when you\'re this well-equipped',  # Nonsense phrases
        ]
        
        for pattern in gibberish_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                print(f"⚠️ Gibberish pattern detected: {pattern}")
                return True
        
        # ✅ Check for code-like artifacts (HIGH CONFIDENCE only)
        code_artifacts = [
            r'puts\w+\(',  # putsAnnotationLeft(
            r'console\.',  # console.log
            r'function\s*\(',  # function(
            r'=>\s*{',  # arrow function
        ]
        
        for pattern in code_artifacts:
            if re.search(pattern, text):
                print(f"⚠️ Code artifact detected: {pattern}")
                return True
        
        # ✅ Check if text is ALL special characters (no letters)
        has_letters = bool(re.search(r'[a-zA-Z]', text))
        if not has_letters and len(text) > 5:
            print(f"⚠️ No letters detected in response")
            return True
        
        # ✅ Check if response is just whitespace or punctuation
        text_stripped = re.sub(r'[^\w\s]', '', text).strip()
        if len(text_stripped) < 3:
            print(f"⚠️ Response is only punctuation/whitespace")
            return True
        
        # ✅ NEW: Check for excessive randomness (random capital letters mid-word)
        random_caps_pattern = r'\b[a-z]+[A-Z][a-z]+\b'
        random_caps_count = len(re.findall(random_caps_pattern, text))
        if random_caps_count >= 3:
            print(f"⚠️ Excessive random capitalization detected")
            return True
        
        return False
    
    def _extract_response_from_validation_failure(self, response_text: str) -> Optional[str]:
        """Extract actual response if validation error was prepended"""
        if response_text.startswith('❌') or 'RESPONSE USES ASTERISKS' in response_text:
            lines = response_text.split('\n')
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('❌') and 'ASTERISKS' not in line:
                    return '\n'.join(lines[i:])
            return None
        return response_text
    
    def _remove_unnecessary_parentheses(self, text: str) -> str:
        """Remove parentheses wrapping UNLESS it's the AI disclaimer"""
        if not text:
            return ""
        
        if text.startswith('(') and text.endswith(')'):
            if "I'm here to listen" in text and "professional" in text and text.startswith('*('):
                return text  # Keep valid disclaimer
            else:
                text = text[1:-1].strip()
        
        return text
    
    # ========================================================================
    # MAIN GENERATION METHODS
    # ========================================================================
    
    def generate_response(
        self,
        conversation_history: List[Dict],
        user_name: str = None,
        time_context: Dict = None,
        max_retries: int = 2,
        is_developer: bool = False,
        developer_email: str = None
    ) -> Optional[str]:
        """Generate response with multi-model fallback"""
        if not conversation_history:
            return None
        
        last_message = conversation_history[-1]['content']
        context = self.context_analyzer.analyze_message(last_message, conversation_history)
        
        
        system_prompt, _ = self.response_generator.create_dynamic_system_prompt(
            context=context,
            conversation_history=conversation_history,
            user_name=user_name,
            time_context=time_context,
            is_developer=is_developer,
            developer_email=developer_email
        )
        
        messages = [
            {"role": "system", "content": system_prompt}
        ] + conversation_history
        
        for model_index, model_config in enumerate(self.models):
            model_name = model_config['name']
            print(f"🤖 Trying model {model_index + 1}/{len(self.models)}: {model_name}")
            
            for attempt in range(max_retries):
                try:
                    response = self._call_api(
                        messages=messages,
                        model=model_name,
                        stream=False,
                        timeout=self.regular_timeout,
                        temperature=model_config['temperature'],
                        max_tokens=model_config['max_tokens']
                    )
                    
                    if response and 'choices' in response:
                        bot_response = response['choices'][0]['message']['content'].strip()
                        
                        # ✅ STEP 1: Quality gate - check for gibberish BEFORE cleaning
                        if self._contains_gibberish(bot_response):
                            print(f"⚠️ Response failed quality check (gibberish detected, attempt {attempt + 1})")
                            continue  # Try again
                        
                        # ✅ STEP 2: Clean response (artifacts, emoji, asterisks, spacing)
                        bot_response = self._clean_text(bot_response)
                        bot_response = self._extract_response_from_validation_failure(bot_response)
                        bot_response = self._remove_unnecessary_parentheses(bot_response)
                        
                        # ✅ STEP 3: Check if cleaning resulted in empty response
                        if not bot_response or len(bot_response.strip()) < 3:
                            print(f"⚠️ Response became empty after cleaning (attempt {attempt + 1})")
                            continue  # Try again
                        
                        # ✅ STEP 4: Validate
                        is_valid, error_msg = self.response_generator.validate_response(
                            response=bot_response,
                            context=context,
                            user_message=last_message
                        )
                        
                        if is_valid:
                            # ✅ STEP 5: Normalize punctuation and return
                            normalized = self.response_generator.normalize_punctuation(
                                bot_response,
                                context
                            )
                            print(f"✅ Success with model: {model_name}")
                            self.current_model_index = model_index
                            return normalized
                        else:
                            print(f"⚠️ Response validation failed (attempt {attempt + 1}): {error_msg}")
                            continue
                
                except requests.exceptions.Timeout:
                    print(f"⚠️ Timeout with {model_name} (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    else:
                        print(f"❌ {model_name} failed after {max_retries} attempts, trying next model...")
                        break
                
                except Exception as e:
                    print(f"⚠️ Error with {model_name} (attempt {attempt + 1}): {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    else:
                        print(f"❌ {model_name} failed, trying next model...")
                        break
        
        print("❌ All models failed - using API failure fallback")
        fallback = random.choice(API_FAILURE_FALLBACKS)
        # ✅ CRITICAL: Don't over-clean fallback messages - preserve markers
        fallback = self._clean_text(fallback)
        return fallback
    
    def generate_response_streaming(
        self,
        conversation_history: List[Dict],
        user_name: str = None,
        time_context: Dict = None,
        is_developer: bool = False,
        developer_email: str = None
    ) -> Generator[str, None, None]:
        """Generate streaming response with model fallback"""
        if not conversation_history:
            return
        
        last_message = conversation_history[-1]['content']
        context = self.context_analyzer.analyze_message(last_message, conversation_history)
        
        system_prompt, _ = self.response_generator.create_dynamic_system_prompt(
            context=context,
            conversation_history=conversation_history,
            user_name=user_name,
            time_context=time_context,
            is_developer=is_developer,
            developer_email=developer_email
        )
        
        messages = [
            {"role": "system", "content": system_prompt}
        ] + conversation_history
        
        for model_index, model_config in enumerate(self.models):
            model_name = model_config['name']
            print(f"🤖 Trying streaming with model {model_index + 1}/{len(self.models)}: {model_name}")
            
            try:
                full_response = ""
                chunk_count = 0
                is_first_chunk = True
                
                for chunk in self._stream_api(
                    messages=messages,
                    model=model_name,
                    timeout=self.streaming_timeout,
                    temperature=model_config['temperature'],
                    max_tokens=model_config['max_tokens']
                ):
                    if chunk:
                        if is_first_chunk:
                            chunk = chunk.replace('<s>', '').replace('</s>', '')
                            chunk = chunk.replace('<|im_start|>', '').replace('<|im_end|>', '')
                            chunk = chunk.lstrip()
                            is_first_chunk = False
                        if chunk:
                            chunk_count += 1
                            full_response += chunk
                            yield chunk
                
                if chunk_count > 0:
                    print(f"✅ Streaming success with model: {model_name} (cleaned)")
                    self.current_model_index = model_index
                    
                    # Validate final response
                    full_response = self._clean_text(full_response)
                    full_response = self._extract_response_from_validation_failure(full_response)
                    full_response = self._remove_unnecessary_parentheses(full_response)
                    
                    is_valid, error_msg = self.response_generator.validate_response(
                        response=full_response,
                        context=context,
                        user_message=last_message
                    )
                    
                    if not is_valid:
                        print(f"⚠️ Streamed response validation failed: {error_msg}")
                    
                    return
                else:
                    print(f"⚠️ No chunks received from {model_name}, trying next model...")
                    continue
            
            except requests.exceptions.Timeout:
                print(f"⚠️ Streaming timeout with {model_name}, trying next model...")
                continue
            
            except Exception as e:
                print(f"❌ Streaming error with {model_name}: {str(e)}")
                continue
        
        print("❌ All models failed for streaming")
        return
    
    # ========================================================================
    # API METHODS
    # ========================================================================
    
    def _call_api(
        self,
        messages: List[Dict],
        model: str,
        stream: bool = False,
        timeout: int = 30,
        temperature: float = 1.0,
        max_tokens: int = 500
    ) -> Optional[Dict]:
        """Make API call to OpenRouter"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'HTTP-Referer': 'https://snowfriend.app',
            'X-Title': 'Snowfriend AI Companion'
        }
        
        payload = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': stream
        }
        
        try:
            response = requests.post(
                self.api_base_url,
                headers=headers,
                json=payload,
                timeout=timeout,
                stream=stream
            )
            
            response.raise_for_status()
            
            if stream:
                return response
            else:
                return response.json()
        
        except requests.exceptions.Timeout:
            raise
        
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed with {model}: {str(e)}")
            return None
    
    def _stream_api(
        self,
        messages: List[Dict],
        model: str,
        timeout: int = 15,
        temperature: float = 1.0,
        max_tokens: int = 500
    ) -> Generator[str, None, None]:
        """Stream API response chunks"""
        response = self._call_api(
            messages=messages,
            model=model,
            stream=True,
            timeout=timeout,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        if not response:
            return
        
        try:
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]
                        
                        if data_str.strip() == '[DONE]':
                            break
                        
                        try:
                            data = json.loads(data_str)
                            
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                
                                if content:
                                    # Filter emojis from chunks
                                    content = self._remove_emojis(content)
                                    
                                    if content:
                                        yield content
                        
                        except json.JSONDecodeError:
                            continue
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Streaming error with {model}: {str(e)}")
            return
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def test_connection(self) -> bool:
        """Test API connection with all models"""
        print("🔧 Testing connection with all models...")
        
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        working_models = []
        
        for model_config in self.models:
            model_name = model_config['name']
            try:
                print(f"  Testing {model_name}...")
                response = self._call_api(
                    messages=messages,
                    model=model_name,
                    timeout=10,
                    max_tokens=50
                )
                
                if response and 'choices' in response:
                    print(f"  ✅ {model_name} - Working")
                    working_models.append(model_name)
                else:
                    print(f"  ❌ {model_name} - Failed")
            
            except Exception as e:
                print(f"  ❌ {model_name} - Error: {str(e)}")
        
        if working_models:
            print(f"\n✓ {len(working_models)}/{len(self.models)} models are working")
            return True
        else:
            print("\n✗ No models are working!")
            return False
    
    def get_model_info(self) -> Dict:
        """Get information about current models"""
        return {
            'total_models': len(self.models),
            'current_model': self.models[self.current_model_index]['name'],
            'all_models': [
                {
                    'name': m['name'],
                    'description': m['description'],
                    'priority': m['priority']
                }
                for m in self.models
            ],
            'provider': 'OpenRouter',
            'streaming_supported': True,
            'emoji_filtering': True,
            'asterisk_replacement': True,
            'artifact_removal': True,
            'gibberish_detection': True,
            'fallback_marker_preservation': True  # ✅ New feature
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_llm_service_instance = None

def get_llm_service() -> LLMService:
    """Get or create global LLM service instance"""
    global _llm_service_instance
    
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    
    return _llm_service_instance


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("Testing Snowfriend Multi-Model LLM Service...")
    
    try:
        service = LLMService()
        
        if service.test_connection():
            print("\n✓ Service initialized successfully")
            print(f"\nModel Configuration:")
            info = service.get_model_info()
            print(f"  Total models: {info['total_models']}")
            print(f"  Primary model: {info['current_model']}")
            print(f"  Emoji filtering: {info['emoji_filtering']}")
            print(f"  Asterisk replacement: {info['asterisk_replacement']}")
            print(f"  Artifact removal: {info['artifact_removal']}")
            print(f"  Gibberish detection: {info['gibberish_detection']}")
            print(f"  Fallback marker preservation: {info['fallback_marker_preservation']}")
            
            conversation = [
                {"role": "user", "content": "Hi there!"}
            ]
            
            print("\nGenerating test response...")
            response = service.generate_response(conversation)
            
            if response:
                print(f"\n✓ Response received: {response[:100]}...")
            else:
                print("\n✗ No response received")
        else:
            print("\n✗ Connection test failed")
    
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")