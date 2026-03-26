# media_views.py - UPDATED WITH PAGINATION SUPPORT
"""
Media-related views and utilities for Snowfriend chatbot.
Handles video and image search requests, media message creation,
and media-specific processing.

✅ NEW: Pagination support for "more" requests
"""

import json
import re

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .media_service import MediaService
from .models import UserMemory
from .response_generator import extract_conversation_facts
from .media_pagination import (
    MediaPaginationManager,
)

# Initialize pagination manager
pagination_manager = MediaPaginationManager()


# ======================================================================
# MEDIA QUERY EXTRACTION UTILITIES
# ======================================================================


def extract_image_query_smart(user_message: str, previous_query: str = None) -> str:
    """
    Extract the actual subject from image requests using semantic
    analysis
    """
    try:
        from .services import get_llm_service

        llm_service = get_llm_service()

        context_block = f'\nPREVIOUS TOPIC: "{previous_query}"\n' if previous_query else ""

        extraction_prompt = f"""The user is asking for images. Extract what they want images OF.
{context_block}
Message: "{user_message}"

Return ONLY the subject (2-5 words) that resolves any pronouns like "them", "those", "it". No explanation.

Subject:"""

        response = llm_service.generate_response(
            conversation_history=[
                {"role": "user", "content": extraction_prompt}
            ],
            user_name=None,
            time_context=None,
            max_retries=1,
            is_extraction=True,
        )

        if response and not (
            "[[EMAIL:" in response or "[[FEEDBACK:" in response
        ):
            query = response.strip().lower()
            query = re.sub(r'\s+', ' ', query)
            query = query.strip(".,!?")

            if len(query) >= 3:
                return query

    except Exception as e:
        print(f"⚠️ Image query extraction failed: {str(e)}")

    # Fallback: extract meaningful words
    words = user_message.lower().replace("?", "").split()
    meaningful = [w for w in words if len(w) > 3]

    if meaningful:
        query = " ".join(meaningful[-5:])
        query = query.strip(".,!?")
        return query

    return "this topic"


def extract_video_query_smart(user_message: str, previous_query: str = None) -> str:
    """
    Extract media search query from user's request using semantic
    analysis. Uses LLM to understand intent without hardcoded patterns.

    Returns:
        str: Extracted search query, or fallback if extraction fails
    """
    try:
        from .services import get_llm_service

        llm_service = get_llm_service()

        context_block = f'\nPREVIOUS TOPIC: "{previous_query}"\n' if previous_query else ""

        # Use LLM to extract the core topic/intent
        extraction_prompt = f"""The user is asking for videos. Extract the main topic they want videos about.
{context_block}
Message: "{user_message}"

Return ONLY the topic as a search query (2-6 words) that resolves any pronouns like "them", "those", "it". No explanation, no quotes.

Query:"""

        response = llm_service.generate_response(
            conversation_history=[
                {"role": "user", "content": extraction_prompt}
            ],
            user_name=None,
            time_context=None,
            max_retries=1,
            is_extraction=True,
        )

        if response and not (
            "[[EMAIL:" in response or "[[FEEDBACK:" in response
        ):
            query = response.strip().lower()
            query = re.sub(r'\s+', ' ', query)
            query = query.strip(".,!?")

            if len(query) >= 3:
                print(f"✅ LLM extracted query: '{query}'")
                return query

    except Exception as e:
        print(f"⚠️ Video query extraction failed: {str(e)}")

    # Fallback: extract context from conversation memory
    print("⚠️ Using fallback extraction")

    # Extract topics/entities from user message
    facts = extract_conversation_facts(
        [{"role": "user", "content": user_message}]
    )

    detected_topics = list(facts.get("topics_discussed", []))
    detected_entities = facts.get("entities_mentioned", {})
    detected_activities = list(detected_entities.get("activities", []))

    # Combine all detected context
    all_context = detected_topics + detected_activities

    if all_context:
        # Use first detected topic/activity
        query = all_context[0]
        print(f"✅ Memory-based extraction: '{query}'")
        return query

    # Final fallback: extract longest words from message
    words = user_message.lower().split()
    meaningful = [w for w in words if len(w) > 4]

    if len(meaningful) >= 3:
        query = " ".join(meaningful[-5:])
        query = re.sub(r"[?.!,]", "", query).strip()
        print(f"✅ Word-based fallback: '{query}'")
        return query
    elif meaningful:
        query = " ".join(meaningful)
        query = re.sub(r"[?.!,]", "", query).strip()
        return query

    # Absolute final fallback
    return "helpful content"


def detect_media_count(user_message: str) -> int:
    """
    Determine if user wants 1 or 3 media items by analyzing the media
    word. Focuses on the core media term (video/videos) ignoring
    confusing context.

    Returns:
        1: Singular request
        3: Plural request
    """
    from .services import get_llm_service

    try:
        llm_service = get_llm_service()

        # ✅ FOCUSED: Analyze ONLY the media word, not full context
        focused_prompt = f'''Find the media word in this message (video/videos, image/images, etc.) and tell me if it's singular or plural.

Message: "{user_message}"

Return only:
"1" if media word is singular
"3" or "2" if media word is plural

Answer:'''

        response = llm_service.generate_response(
            conversation_history=[
                {"role": "user", "content": focused_prompt}
            ],
            user_name=None,
            time_context=None,
            max_retries=1,
            is_extraction=True,
        )

        if response and ("1" in response or "3" in response):
            count = 3 if "3" in response else 1
            print(f"✅ Media word analysis: {count} item(s)")
            return count

    except Exception as e:
        print(f"⚠️ Analysis failed: {str(e)}")

    # ✅ SMART FALLBACK: Check for common media words
    message_lower = user_message.lower()

    # Plural media words
    if any(w in message_lower for w in [
        'videos', 'images', 'pics', 'clips', 'vids'
    ]):
        print("✅ Fallback: plural media word → 3 items")
        return 3

    # Singular with article
    if any(p in message_lower for p in [
        'a video', 'an image', 'one video', 'one image'
    ]):
        print("✅ Fallback: singular phrase → 1 item")
        return 1

    # Check individual words
    for word in message_lower.split():
        clean = word.strip('.,!?;:')
        if clean in ['videos', 'images', 'vids', 'pics']:
            return 3
        elif clean in ['video', 'image', 'vid', 'pic']:
            return 1

    # Default to plural
    print("⚠️ Ambiguous → defaulting to 3 items")
    return 3


# ======================================================================
# MEDIA REQUEST DETECTION
# ======================================================================


def detect_media_request(user_message: str, previous_query: str = None) -> dict:
    """
    Detect if user message is requesting media (videos/images)
    Uses LLM-based semantic analysis instead of pattern matching

    Returns:
        dict: {
            'is_media_request': bool,
            'media_type': 'video' | 'image' | None,
            'is_more_request': bool,
            'count': int
        }
    """

    try:
        from .services import get_llm_service

        llm_service = get_llm_service()

        context_block = f'\nPREVIOUS SEARCH TOPIC: "{previous_query}"\n' if previous_query else ""

        detection_prompt = f"""Analyze this user message to determine media request intent.
{context_block}
Message: "{user_message}"

You MUST respond with ONLY a valid JSON object. No markdown, no explanations, no text outside the JSON.
The JSON object must use this exact format:
{{
    "is_media_request": true or false,
    "media_type": "video" or "image" or null,
    "is_continuation": true or false
}}

Rules:
- set "is_media_request" to true if they ask for videos, pictures, images, photos, clips, etc.
- set "is_continuation" to true if they are asking for MORE examples OR if they want the SAME previous topic in a DIFFERENT format (e.g. videos instead of pictures)."""

        response = llm_service.generate_response(
            conversation_history=[
                {"role": "user", "content": detection_prompt}
            ],
            user_name=None,
            time_context=None,
            max_retries=1,
            is_extraction=True,
        )

        if response and not (
            "[[EMAIL:" in response or "[[FEEDBACK:" in response
        ):
            # Parse response
            try:
                # In case the model wrapped it in markdown code blocks
                clean_response = response.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                elif clean_response.startswith("```"):
                    clean_response = clean_response[3:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]
                
                parsed_json = json.loads(clean_response.strip())
                
                is_media = bool(parsed_json.get("is_media_request", False))
                media_type_raw = parsed_json.get("media_type")
                is_more = bool(parsed_json.get("is_continuation", False))
                
                # If it's a continuation of the previous media search, force is_media to True
                if is_more:
                    is_media = True

                media_type = None
                if media_type_raw in ["video", "image"]:
                    media_type = media_type_raw

                count = detect_media_count(user_message) if is_media else 1

                result = {
                    "is_media_request": is_media,
                    "media_type": media_type,
                    "is_more_request": is_more,
                    "count": count,
                }
            except Exception as e:
                print(f"⚠️ Failed to parse LLM JSON: {e}")
                # Fallback on failure
                pass

            if 'result' in locals():
                print(f"✅ LLM detected media request: {result}")
                return result

    except Exception as e:
        print(f"⚠️ Media detection failed: {str(e)}")

    # Fallback: assume not a media request
    return {
        "is_media_request": False,
        "media_type": None,
        "is_more_request": False,
        "count": 1,
    }


# ======================================================================
# MEDIA SEARCH API ENDPOINT
# ======================================================================


@login_required(login_url="login")
@require_http_methods(["POST"])
def search_media_api(request):
    """
    Search for YouTube videos or images

    🚨 STRICT LIMITS:
    - Minimum: 1 result
    - Maximum: 3 results (even if user requests 10 or 100)

    POST /chat/api/media/search/
    {
        "query": "healthy relationships advice",
        "media_type": "video",  // or "image"
        "count": 3
    }
    """
    try:
        data = json.loads(request.body)
        query = data.get("query", "").strip()
        media_type = data.get("media_type", "video")
        count = data.get("count", 3)

        if not query:
            return JsonResponse(
                {"success": False, "error": "Query is required"},
                status=400
            )

        # 🚨 STRICT LIMIT: Force maximum of 3 results, minimum of 1
        count = max(1, min(count, 3))

        print(
            f"📺 Media search: query='{query}', "
            f"type={media_type}, count={count}"
        )

        # Initialize media service
        media_service = MediaService()

        # Search media with enforced limit
        result = media_service.search_media(
            query=query, media_type=media_type, count=count
        )

        # 🚨 DOUBLE-CHECK: Ensure we never return more than 3
        if result.get("success") and result.get("results"):
            if len(result["results"]) > 3:
                print(
                    f"⚠️ WARNING: Got {len(result['results'])} results, "
                    "truncating to 3"
                )
                result["results"] = result["results"][:3]
                result["count"] = 3

        return JsonResponse(result)

    except Exception as e:
        print(f"❌ Error in search_media_api: {str(e)}")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500
        )


# ======================================================================
# HELPER: Update User Memory After Media Request
# ======================================================================


def update_memory_after_media_request(
    user, query, media_type, result_count
):
    """
    Update user memory to track media requests

    Args:
        user: User object
        query: Search query used
        media_type: 'video' or 'image'
        result_count: Number of results returned
    """
    try:
        user_memory = UserMemory.objects.get(user=user)

        if "media_requests" not in user_memory.mentioned_activities:
            user_memory.mentioned_activities["media_requests"] = []

        user_memory.mentioned_activities["media_requests"].append(
            {
                "query": query,
                "type": media_type,
                "count": result_count,
                "timestamp": timezone.now().isoformat(),
            }
        )

        # Extract and update topics from query
        topic_words = query.split()
        for word in topic_words:
            if len(word) > 3:
                word_lower = word.lower()
                if word_lower not in user_memory.mentioned_topics:
                    user_memory.mentioned_topics[word_lower] = 1
                else:
                    if isinstance(
                        user_memory.mentioned_topics[word_lower], int
                    ):
                        user_memory.mentioned_topics[word_lower] += 1
                    else:
                        user_memory.mentioned_topics[word_lower] = 1

        user_memory.save()
        print(f"✅ Updated memory: {query}")

    except UserMemory.DoesNotExist:
        print("⚠️ User memory not found")
    except Exception as e:
        print(f"⚠️ Error updating memory: {str(e)}")


# ======================================================================
# MEDIA CONTEXT GENERATION (LLM-based intro/outro)
# ======================================================================


def generate_media_context(
    user_message,
    conversation_history,
    media_type,
    query,
    user_first_name=None,
    is_developer=False,
    developer_email=None,
    is_more_request=False,
    has_more_available=False
):
    """
    Generate contextual intro and outro for media responses using LLM

    ✅ NEW: Support for "more" requests with different messaging

    Args:
        user_message: Original user request
        conversation_history: List of previous messages
        media_type: 'video' or 'image'
        query: Extracted search query
        user_first_name: User's first name (optional)
        is_developer: Whether user is developer
        developer_email: Developer email if applicable
        is_more_request: Whether this is a "more" pagination request
        has_more_available: Whether more items are available after
                           this batch

    Returns:
        tuple: (intro_text, outro_text) or (None, None) if LLM fails
    """
    try:
        from .services import get_llm_service
        from .response_generator import extract_conversation_facts

        llm_service = get_llm_service()

        # Extract conversation facts
        facts = extract_conversation_facts(
            conversation_history + [
                {"role": "user", "content": user_message}
            ]
        )

        # Extract detected values
        detected_emotions = list(facts.get("emotions_expressed", []))
        detected_topics = list(facts.get("topics_discussed", []))
        detected_entities = facts.get("entities_mentioned", {})
        detected_activities = list(
            detected_entities.get("activities", [])
        )

        # Build emotion context
        emotion_context = ""
        if detected_emotions:
            emotion_list = ", ".join(detected_emotions)
            emotion_context = f"User is experiencing: {emotion_list}\n"

        # Build topic context
        topic_context = ""
        if detected_topics:
            topic_list = ", ".join(detected_topics)
            topic_context = f"User mentioned topics: {topic_list}\n"
        elif detected_activities:
            activity_list = ", ".join(detected_activities)
            topic_context = (
                f"User mentioned activities: {activity_list}\n"
            )

        # Build search query context
        query_context = f"Search query: {query}\n"

        # ✅ NEW: Add pagination context
        pagination_context = ""
        if is_more_request:
            pagination_context = (
                "User requested MORE content (pagination request)\n"
            )
            pagination_context += (
                "Previous content was already shown for this topic\n"
            )
            if has_more_available:
                pagination_context += (
                    "More content is available after this batch\n"
                )
            else:
                pagination_context += (
                    "This is the LAST batch available\n"
                )

        # Build LLM prompt
        intro_ack = (
            'Acknowledge this is additional content for the same topic.'
            if is_more_request else
            'Acknowledge the topic or request naturally.'
        )
        outro_guide = (
            'Let them know if more is available or if this is the '
            'last batch.' if is_more_request else
            'Offer an open invitation for further discussion or '
            'exploration, without pressure.'
        )
        more_intro = (
            '- For "more" requests: Keep intro brief, focus on '
            'continuing the topic' if is_more_request else ''
        )
        more_outro = (
            '- For "more" requests: Clearly state if more is '
            'available or if this is the end' if is_more_request else ''
        )

        llm_prompt = f"""You're Snowfriend. User made a request.

USER MESSAGE: "{user_message}"

CONTEXT:
{emotion_context}{topic_context}{query_context}{pagination_context}

Generate exactly TWO parts:

INTRO:
{intro_ack} Indicate that you found relevant materials.

OUTRO:
{outro_guide}

CORE PRINCIPLES - READ CAREFULLY:

**Emotional Awareness Rules:**
- Do NOT assert emotional states unless explicitly stated by user
- Treat any emotional interpretation as uncertain/possible, not definite
- Neutral messages deserve neutral responses
- Match the user's emotional level without escalating

**Intro Guidelines:**
- Focus on acknowledging the user's topic or request
- Avoid presumptive language about feelings or internal states
- Respond informationally if the message is informational
- Do not introduce emotional narratives that the user did not express
{more_intro}

**Outro Guidelines:**
- Invite continuation without implying the user needs support
- Allow the user to engage further or disengage without pressure
- Maintain a supportive but non-assumptive tone
{more_outro}

**Tone Calibration:**
- Information seeking → Information providing
- Curiosity → Helpful response
- Neutral tone → Neutral response
- Explicit distress → Warm support (only if clearly expressed)

Write ONLY these two sections in plain text (no markdown):

INTRO:

OUTRO:
"""

        llm_response = llm_service.generate_response(
            conversation_history=[
                {"role": "user", "content": llm_prompt}
            ],
            user_name=user_first_name,
            time_context=None,
            is_developer=is_developer,
            developer_email=developer_email,
            max_retries=1,
            is_extraction=True,
        )

        if not llm_response:
            raise ValueError("LLM returned empty response")

        # Check for API failure markers
        if "[[EMAIL:" in llm_response or "[[FEEDBACK:" in llm_response:
            raise ValueError("LLM returned API failure fallback")

        # Validate response doesn't contain technical jargon
        validation_prompt = f"""Does this response contain technical jargon about APIs, search engines, or systems?

Response: "{llm_response}"

Return ONLY "yes" or "no".

Contains technical jargon:"""

        validation = llm_service.generate_response(
            conversation_history=[
                {"role": "user", "content": validation_prompt}
            ],
            user_name=None,
            time_context=None,
            is_developer=is_developer,
            developer_email=developer_email,
            max_retries=1,
            is_extraction=True,
        )

        if validation and "yes" in validation.lower():
            raise ValueError("LLM returned technical message")

        # Extract INTRO and OUTRO
        intro_match = re.search(
            r"INTRO:\s*(.+?)(?=OUTRO:|$)",
            llm_response,
            re.DOTALL | re.IGNORECASE
        )
        outro_match = re.search(
            r"OUTRO:\s*(.+?)$",
            llm_response,
            re.DOTALL | re.IGNORECASE
        )

        intro_text = None
        outro_text = None

        if intro_match:
            intro_text = intro_match.group(1).strip()
            intro_text = re.sub(
                r"\s*OUTRO:.*$", "", intro_text, flags=re.IGNORECASE
            ).strip()
            intro_text = re.sub(r"^#+\s*", "", intro_text).strip()

        if outro_match:
            outro_text = outro_match.group(1).strip()
            outro_text = re.sub(r"^#+\s*", "", outro_text).strip()

        # Fallback parsing if extraction failed
        if not intro_text or not outro_text:
            lines = [
                line.strip() for line in llm_response.split("\n")
                if line.strip()
            ]

            if len(lines) >= 2:
                intro_text = lines[0]
                outro_text = lines[-1]
                print("✅ Fallback parsing succeeded")

        if intro_text and outro_text:
            print(f"✅ LLM generated intro: {intro_text[:50]}...")
            print(f"✅ LLM generated outro: {outro_text[:50]}...")
            return intro_text, outro_text
        else:
            raise ValueError(
                "Failed to extract intro/outro from LLM response"
            )

    except Exception as e:
        print(f"❌ LLM failed for media context: {e}")
        return None, None