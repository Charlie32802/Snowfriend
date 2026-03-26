import os
import random
import json
import re
from typing import Dict, List, Optional, Generator, AsyncGenerator
from dotenv import load_dotenv
import time
import asyncio

import httpx
import requests

from .response_generator import API_FAILURE_FALLBACKS, get_system_prompt

load_dotenv()


class LLMService:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        if not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is not set. "
                "Please configure your Groq API key in the .env file. "
                "Get your API key at: https://console.groq.com/keys"
            )

        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"
        self.max_tokens = 8000
        self.temperature = 1.0
        self.system_prompt_version = "4.0.0"
        self.streaming_timeout = 30
        self.regular_timeout = 60

        print(f"[OK] LLM Service initialized | {self.model} via Groq Cloud")

    def _get_headers(self) -> Dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.groq_api_key}",
        }

    def _remove_emojis(self, text: str) -> str:
        if not text:
            return ""

        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"
            "\U0001f300-\U0001f5ff"
            "\U0001f680-\U0001f6ff"
            "\U0001f1e0-\U0001f1ff"
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "\U0001f900-\U0001f9ff"
            "\U0001fa00-\U0001fa6f"
            "\U0001fa70-\U0001faff"
            "\U00002600-\U000026ff"
            "\U00002700-\U000027bf"
            "]+",
            flags=re.UNICODE,
        )

        text = emoji_pattern.sub("", text)
        text = re.sub(r"  +", " ", text)
        return text

    def _replace_asterisks_with_quotes(self, text: str) -> str:
        if not text or "*" not in text:
            return text

        disclaimer_pattern = r"\*\([^)]*I\'m here to listen[^)]*professional[^)]*\)\*"
        has_disclaimer = re.search(disclaimer_pattern, text, re.IGNORECASE)

        if has_disclaimer:
            disclaimer = has_disclaimer.group(0)
            text_without_disclaimer = text.replace(
                disclaimer, "<<<DISCLAIMER_PLACEHOLDER>>>"
            )
            processed_text = self._replace_asterisks_in_text(text_without_disclaimer)
            return processed_text.replace("<<<DISCLAIMER_PLACEHOLDER>>>", disclaimer)
        else:
            return self._replace_asterisks_in_text(text)

    def _replace_asterisks_in_text(self, text: str) -> str:
        pattern = r"\*([^*]+)\*"

        def replace_with_quotes(match):
            content = match.group(1)
            word_count = len(content.split())
            if word_count <= 2:
                return f"'{content}'"
            else:
                return f'"{content}"'

        return re.sub(pattern, replace_with_quotes, text)

    def _fix_bullet_list_spacing(self, text: str) -> str:
        if not text:
            return text
        lines = text.split("\n")
        fixed_lines = []
        in_list = False
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            is_numbered = bool(re.match(r"^\d+[\.]\s", line_stripped))
            is_bulleted = line_stripped.startswith(("- ", "• ", "* "))
            is_list_item = is_numbered or is_bulleted
            if is_list_item and not in_list:
                if fixed_lines and fixed_lines[-1].strip():
                    fixed_lines.append("")
                in_list = True
            elif not is_list_item and in_list and line_stripped:
                if fixed_lines and fixed_lines[-1].strip():
                    fixed_lines.append("")
                in_list = False
            fixed_lines.append(line)
        return "\n".join(fixed_lines)

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""

        text = self._remove_emojis(text)
        text = self._replace_asterisks_with_quotes(text)

        lines = text.split("\n")
        cleaned_lines = []
        consecutive_empty = 0

        for line in lines:
            line_stripped = line.strip()

            if line_stripped:
                line_cleaned = re.sub(r"  +", " ", line_stripped)
                cleaned_lines.append(line_cleaned)
                consecutive_empty = 0
            else:
                consecutive_empty += 1
                if consecutive_empty <= 2:
                    cleaned_lines.append("")

        text = "\n".join(cleaned_lines)
        text = self._fix_bullet_list_spacing(text)
        text = re.sub(r"([.!?])\s{2,}", r"\1 ", text)
        text = re.sub(r"  +", " ", text)
        text = text.strip()

        return text

    def generate_response(
        self,
        conversation_history: List[Dict],
        user_name: str = None,
        time_context: Dict = None,
        max_retries: int = 2,
        is_developer: bool = False,
        developer_email: str = None,
        is_extraction: bool = False,
    ) -> Optional[str]:
        if not conversation_history:
            return None

        messages = list(conversation_history)
        if not is_extraction:
            system_prompt = get_system_prompt(
                conversation_history=conversation_history,
                user_name=user_name,
                time_context=time_context,
                is_developer=is_developer,
                developer_email=developer_email,
            )
            messages = [{"role": "system", "content": system_prompt}] + messages

        for attempt in range(max_retries):
            try:
                current_temp = 0.1 if is_extraction else self.temperature
                response = self._call_api(
                    messages=messages,
                    model=self.model,
                    stream=False,
                    timeout=self.regular_timeout,
                    temperature=current_temp,
                    max_tokens=self.max_tokens,
                )

                if response and "choices" in response:
                    bot_response = response["choices"][0]["message"]["content"].strip()

                    if not is_extraction:
                        bot_response = self._clean_text(bot_response)

                        if not bot_response or len(bot_response.strip()) < 3:
                            print(f"[WARN] Response became empty after cleaning (attempt {attempt + 1})")
                            continue

                    print(f"[SUCCESS] Response from {self.model} via Groq Cloud")
                    return bot_response

            except requests.exceptions.Timeout:
                print(f"[WARN] Timeout with {self.model} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    break

            except Exception as e:
                print(f"[ERROR] Error with {self.model} (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    break

        print("[ERROR] Groq Cloud failed - using API failure fallback")
        if is_extraction:
            return ""

        fallback = random.choice(API_FAILURE_FALLBACKS)
        fallback = self._clean_text(fallback)
        return fallback

    def generate_response_streaming(
        self,
        conversation_history: List[Dict],
        user_name: str = None,
        time_context: Dict = None,
        is_developer: bool = False,
        developer_email: str = None,
    ) -> Generator[str, None, None]:
        if not conversation_history:
            return

        system_prompt = get_system_prompt(
            conversation_history=conversation_history,
            user_name=user_name,
            time_context=time_context,
            is_developer=is_developer,
            developer_email=developer_email,
        )

        messages = [{"role": "system", "content": system_prompt}] + conversation_history

        try:
            full_response = ""
            chunk_count = 0
            is_first_chunk = True

            for chunk in self._stream_api(
                messages=messages,
                model=self.model,
                timeout=self.streaming_timeout,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            ):
                if chunk:
                    if is_first_chunk:
                        chunk = chunk.lstrip()
                        is_first_chunk = False
                    if chunk:
                        chunk_count += 1
                        full_response += chunk
                        yield chunk

            if chunk_count > 0:
                print(f"[SUCCESS] Streaming success with {self.model} via Groq Cloud")
                return
            else:
                print(f"[WARN] No chunks received from {self.model}")
                return

        except requests.exceptions.Timeout:
            print(f"[WARN] Streaming timeout with {self.model}")
            return
        except Exception as e:
            print(f"[ERROR] Streaming error with {self.model}: {str(e)}")
            return

    def _call_api(
        self,
        messages: List[Dict],
        model: str,
        stream: bool = False,
        timeout: int = 60,
        temperature: float = 1.0,
        max_tokens: int = 500,
    ) -> Optional[Dict]:
        headers = self._get_headers()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=timeout,
                stream=stream,
            )
            response.raise_for_status()
            if stream:
                return response
            else:
                return response.json()
        except requests.exceptions.Timeout:
            raise
        except requests.exceptions.RequestException as e:
            error_body = ""
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = f" | Body: {e.response.text}"
                except Exception:
                    pass
            print(f"[ERROR] API request failed with {model}: {str(e)}{error_body}")
            return None

    def _stream_api(
        self,
        messages: List[Dict],
        model: str,
        timeout: int = 30,
        temperature: float = 1.0,
        max_tokens: int = 500,
    ) -> Generator[str, None, None]:
        response = self._call_api(
            messages=messages,
            model=model,
            stream=True,
            timeout=timeout,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if not response:
            return

        try:
            for line in response.iter_lines():
                if line:
                    line_text = line.decode("utf-8")
                    if line_text.startswith("data: "):
                        data_str = line_text[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    content = self._remove_emojis(content)
                                    if content:
                                        yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"[ERROR] Streaming error with {model}: {str(e)}")
            return

    async def _acall_api(
        self,
        messages: List[Dict],
        model: str,
        stream: bool = False,
        timeout: int = 60,
        temperature: float = 1.0,
        max_tokens: int = 500,
    ) -> Optional[Dict]:
        headers = self._get_headers()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                if stream:
                    return response
                else:
                    return response.json()
        except httpx.TimeoutException:
            raise
        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = f" | Body: {e.response.text}"
            except Exception:
                pass
            print(f"[ERROR] API request failed with {model}: {str(e)}{error_body}")
            return None
        except Exception as e:
            print(f"[ERROR] API request failed with {model}: {str(e)}")
            return None

    async def _astream_api(
        self,
        messages: List[Dict],
        model: str,
        timeout: int = 30,
        temperature: float = 1.0,
        max_tokens: int = 500,
    ) -> AsyncGenerator[str, None]:
        headers = self._get_headers()
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", self.api_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            content = self._remove_emojis(content)
                                            if content:
                                                yield content
                                except json.JSONDecodeError:
                                    continue
        except Exception as e:
            print(f"[ERROR] Streaming error with {model}: {str(e)}")
            return

    async def generate_response_streaming_async(
        self,
        conversation_history: List[Dict],
        user_name: str = None,
        time_context: Dict = None,
        is_developer: bool = False,
        developer_email: str = None,
    ) -> AsyncGenerator[str, None]:
        if not conversation_history:
            return

        system_prompt = get_system_prompt(
            conversation_history=conversation_history,
            user_name=user_name,
            time_context=time_context,
            is_developer=is_developer,
            developer_email=developer_email,
        )

        messages = [{"role": "system", "content": system_prompt}] + conversation_history

        try:
            chunk_count = 0
            is_first_chunk = True

            async for chunk in self._astream_api(
                messages=messages,
                model=self.model,
                timeout=self.streaming_timeout,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            ):
                if chunk:
                    if is_first_chunk:
                        chunk = chunk.lstrip()
                        is_first_chunk = False
                    if chunk:
                        chunk_count += 1
                        yield chunk

            if chunk_count > 0:
                print(f"[SUCCESS] Streaming success with {self.model} via Groq Cloud")
                return
            else:
                print(f"[WARN] No chunks received from {self.model}")
                return

        except httpx.TimeoutException:
            print(f"[WARN] Streaming timeout with {self.model}")
            return
        except Exception as e:
            print(f"[ERROR] Streaming error with {self.model}: {str(e)}")
            return

    async def generate_response_async(
        self,
        conversation_history: List[Dict],
        user_name: str = None,
        time_context: Dict = None,
        is_developer: bool = False,
        developer_email: Optional[str] = None,
        max_retries: int = 2,
        is_extraction: bool = False,
    ) -> Optional[str]:
        if not conversation_history:
            return None

        messages = list(conversation_history)

        if not is_extraction:
            system_prompt = get_system_prompt(
                conversation_history=conversation_history,
                user_name=user_name,
                time_context=time_context,
                is_developer=is_developer,
                developer_email=developer_email,
            )
            messages = [{"role": "system", "content": system_prompt}] + messages

        for attempt in range(max_retries):
            try:
                current_temp = 0.1 if is_extraction else self.temperature
                response = await self._acall_api(
                    messages=messages,
                    model=self.model,
                    stream=False,
                    timeout=self.regular_timeout,
                    temperature=current_temp,
                    max_tokens=self.max_tokens,
                )

                if response and "choices" in response:
                    bot_response = response["choices"][0]["message"]["content"].strip()

                    if not is_extraction:
                        bot_response = self._clean_text(bot_response)

                        if not bot_response or len(bot_response.strip()) < 3:
                            print(f"[WARN] Response became empty after cleaning (attempt {attempt + 1})")
                            continue

                    print(f"[SUCCESS] Response from {self.model} via Groq Cloud")
                    return bot_response

            except httpx.TimeoutException:
                print(f"[WARN] Timeout with {self.model} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    break

            except Exception as e:
                print(f"[ERROR] Error with {self.model} (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    break

        if is_extraction:
            return ""

        print("[ERROR] Groq Cloud failed - using API failure fallback")
        fallback = random.choice(API_FAILURE_FALLBACKS)
        fallback = self._clean_text(fallback)
        return fallback

    def test_connection(self) -> bool:
        print("[TEST] Testing connection with Groq Cloud...")
        messages = [{"role": "user", "content": "Hello"}]
        try:
            print(f"  Testing {self.model} via Groq Cloud...")
            response = self._call_api(
                messages=messages,
                model=self.model,
                timeout=10,
                max_tokens=50
            )
            if response and "choices" in response:
                print(f"  [OK] {self.model} via Groq Cloud - Working")
                return True
            else:
                print(f"  [ERROR] {self.model} via Groq Cloud - Failed")
                return False
        except Exception as e:
            print(f"  [ERROR] {self.model} via Groq Cloud - Error: {str(e)}")
            return False

    def get_model_info(self) -> Dict:
        return {
            "current_model": self.model,
            "provider": "groq",
            "streaming_supported": True,
            "emoji_filtering": True,
            "artifact_filtering": False,
            "instruction_leakage_filtering": False,
            "minimal_cleaning": True,
        }


_llm_service_instance = None


def get_llm_service() -> LLMService:
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance