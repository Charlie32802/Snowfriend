#services.py
import requests
import time
from typing import List, Dict
import os
# Import enhanced systems
from .safety import ContentSafety
from .context_analyzer import ContextAnalyzer, ConversationContext
from .response_generator import ResponseGenerator

class LLMService:
    """
    SNOWFRIEND 10/10 - CONTEXT-AWARE MENTAL HEALTH COMPANION WITH MEMORY
    Uses advanced semantic understanding + memory system for perfect responses
    """

    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_KEY environment variable not set")
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        print("⏳ Calling DeepSeek-V3...")

        self.primary_model = "deepseek-ai/DeepSeek-V3"
        self.conversation_memory = []

        # NEW: Initialize advanced systems
        self.context_analyzer = ContextAnalyzer()
        self.response_generator = ResponseGenerator()

        print("✓ Advanced Context Analyzer loaded")
        print("✓ Intelligent Response Generator loaded")
        print("✓ Conversation Memory System loaded")
        print("✓ Punctuation Intelligence enabled")
        # Removed: "🚨 CRITICAL: Minimal question mode enabled" as per Task 3

    def _call_api_with_retry(self, payload, max_retries=2):
        """Make API call with retry logic"""
        for attempt in range(max_retries + 1):
            payload["model"] = self.primary_model

            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=45
                )

                if response.status_code == 200:
                    result = response.json()
                    if 'choices' in result and len(result['choices']) > 0:
                        return result['choices'][0]['message']['content'].strip()
                    else:
                        print(f"✗ API returned no choices: {result}")
                else:
                    print(f"✗ API Error {response.status_code}: {response.text[:100]}")

            except requests.exceptions.Timeout:
                print(f"✗ Timeout on attempt {attempt + 1}")
            except requests.exceptions.RequestException as e:
                print(f"✗ Request failed: {e}")

            if attempt < max_retries:
                print(f"⏳ Retrying in 0.5 seconds...")
                time.sleep(0.5)

        return None

    def generate_response(
        self,
        conversation_history: List[Dict[str, str]],
        user_name: str = None,
        time_context: Dict = None # ✅ NEW: Time awareness
    ) -> str:
        """
        ENHANCED RESPONSE GENERATION with full context awareness + MEMORY + TIME

        Args:
            conversation_history: List of conversation messages
            user_name: User's first name (optional but recommended)
            time_context: Current time info from timezone_utils (optional)
        """

        # Update conversation memory
        if conversation_history:
            self.conversation_memory = conversation_history[-10:]

        # ====================================================================
        # STEP 1: SAFETY CHECK - NOW CONTEXT-AWARE
        # ====================================================================
        if conversation_history:
            last_msg = conversation_history[-1]['content']
            should_override, category, safety_response, needs_llm = ContentSafety.should_override_therapeutic_response(
                last_msg,
                conversation_history # ✅ Pass conversation history for context
            )

            if should_override:
                print(f"⚠️ Safety override triggered: {category}")

                # ✅ If needs_llm=True, let LLM handle with crisis-aware prompt
                if needs_llm:
                    print(f" → Using LLM with crisis-aware context instead of canned response")
                    # Continue to context analysis and LLM generation
                else:
                    # Use canned safety response
                    return safety_response

        # ====================================================================
        # STEP 2: CONTEXT ANALYSIS
        # ====================================================================
        if conversation_history:
            last_msg = conversation_history[-1]['content']
            context = self.context_analyzer.analyze_message(last_msg, conversation_history)

            print(f"📊 CONTEXT ANALYSIS:")
            print(f" Temporal Scope: {context.temporal_scope}")
            print(f" Emotional Tone: {context.emotional_tone}")
            print(f" Topic Type: {context.topic_type}")
            print(f" Urgency: {context.urgency_level}")
            print(f" Disclosure Depth: {context.disclosure_depth}/5")
            print(f" Needs Validation: {context.needs_validation}")
            print(f" Conversation Depth: {context.conversation_depth}")
            print(f" Post-Crisis: {context.is_post_crisis}")
            print(f" Expressing Gratitude: {context.expressing_gratitude}")
            if context.user_corrections > 0:
                print(f" ⚠️ User Corrections: {context.user_corrections}")
        else:
            # No history - initial greeting context
            context = ConversationContext(
                temporal_scope='none',
                emotional_tone='neutral',
                topic_type='greeting',
                urgency_level='none',
                disclosure_depth=1,
                needs_validation=False,
                key_entities=[],
                implicit_requests=[],
                contradictions=[],
                user_corrections=0,
                is_post_crisis=False,
                expressing_gratitude=False,
                conversation_depth=0
            )

        # ====================================================================
        # STEP 3: GENERATE CONTEXT-AWARE SYSTEM PROMPT WITH MEMORY + TIME (NEW!)
        # ====================================================================
        system_content, facts = self.response_generator.create_dynamic_system_prompt(
            context,
            conversation_history,
            user_name=user_name, # ✅ Pass user's name
            time_context=time_context # ✅ NEW: Pass time info
        )

        print(f"✓ Dynamic system prompt created ({len(system_content)} chars)")
        if user_name:
            print(f"✓ User name included: {user_name}")

        # ✅ NEW: Log memory facts
        if facts:
            print(f"📚 MEMORY FACTS:")
            print(f" Exchange count: {facts.get('exchange_count', 0)}")
            print(f" Substantive exchanges: {facts.get('substantive_exchanges', 0)}")
            print(f" First message: {facts.get('first_user_message', 'N/A')[:30]}...")
            if facts.get('topics_discussed'):
                print(f" Topics: {', '.join(facts['topics_discussed'])}")

        # ====================================================================
        # STEP 4: BUILD API PAYLOAD
        # ====================================================================
        messages = [{"role": "system", "content": system_content}]

        history_to_send = conversation_history[-6:] if conversation_history else []
        for msg in history_to_send:
            role = "user" if msg['role'] == 'user' else "assistant"
            messages.append({"role": role, "content": msg['content']})

        payload = {
            "model": self.primary_model,
            "messages": messages,
            "temperature": 0.68,
            "max_tokens": 600, # ✅ INCREASED from 400 to 600 for DEEP emotional responses
            "top_p": 0.84,
            "frequency_penalty": 0.92,
            "presence_penalty": 0.78,
            "stream": False
        }

        # ====================================================================
        # STEP 5: TRY API WITH CONTEXT-AWARE VALIDATION
        # ====================================================================
        print("⏳ Calling DeepSeek-R1...")
        api_response = self._call_api_with_retry(payload)

        if api_response:
            # Fix 1: Remove asterisks and format more casually
            api_response = api_response.replace('*', "'")

            # Try up to 3 times with context-aware validation
            for attempt in range(3):
                # Context-aware validation
                is_valid, failure_reason = self.response_generator.validate_response(
                    api_response,
                    context,
                    conversation_history[-1]['content'] if conversation_history else ""
                )

                if is_valid:
                    # ✅ Apply punctuation normalization
                    normalized_response = self.response_generator.normalize_punctuation(
                        api_response,
                        context
                    )

                    if normalized_response != api_response:
                        print(f"🔧 Punctuation normalized:")
                        print(f" Before: {api_response}")
                        print(f" After: {normalized_response}")

                    print(f"✓ Context-aware validation passed: {normalized_response[:60]}...")
                    self.response_generator.response_history.append(normalized_response)
                    return normalized_response
                else:
                    print(f"⚠️ Validation failed (attempt {attempt + 1}/3): {failure_reason}")

                    # Adjust parameters and retry
                    if attempt < 2:
                        payload["temperature"] = 0.62
                        payload["frequency_penalty"] = 0.95
                        api_response = self._call_api_with_retry(payload)
                        if api_response:
                            api_response = api_response.replace('*', "'") # Fix asterisks
                        if not api_response:
                            break

        # ====================================================================
        # STEP 6: BETTER FALLBACK RESPONSES (FIX 3)
        # ====================================================================
        print("⚠️ Using context-aware fallback")

        fallback = self.response_generator.generate_contextual_fallback(context, conversation_history)

        print(f"✓ Contextual fallback: {fallback}")
        self.response_generator.response_history.append(fallback)
        return fallback