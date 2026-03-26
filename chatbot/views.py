import asyncio
import json
import random
import re
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from asgiref.sync import sync_to_async

from .media_views import detect_media_request
from .models import Conversation, Message, MessageLimit, UserMemory
from .response_generator import API_FAILURE_FALLBACKS
from .safety import ContentSafety
from .services import get_llm_service


def is_developer_account(user):
    if not user or not hasattr(user, "email") or not user.email:
        return False

    DEVELOPER_EMAIL = "marcdaryll.trinidad@gmail.com"
    user_email_normalized = user.email.lower().strip()
    is_match = user_email_normalized == DEVELOPER_EMAIL.lower()

    if is_match:
        print(f"Developer mode ACTIVATED for: {user.email}")

    return is_match


def get_or_create_user_memory(user):
    memory, created = UserMemory.objects.get_or_create(user=user)
    if created:
        print(f"Created new UserMemory for {user.username}")
    return memory


def generate_initial_greeting(user, user_memory):
    user_first_name = user.first_name if user.first_name else "there"
    days_since_first = user_memory.get_days_since_first_conversation()

    greeting_templates = {
        "new_user": lambda name: f"Hi {name}! I'm Snowfriend. You can share your thoughts here at your own pace. I'm here to listen and help you reflect.",
        "returning_one_day": lambda name: f"Hi {name}, welcome back! It's been a day since we last talked. I'm still here to listen whenever you need.",
        "returning_few_days": lambda name, days: f"Hi {name}, welcome back! Looks like we've been talking for {days} days now. I'm still here to listen and help you reflect.",
        "regular_user": lambda name, days: f"Hi {name}, it's been over a week! We've been talking for {days} days now. I'm always here when you need me.",
    }

    if days_since_first == 0:
        return greeting_templates["new_user"](user_first_name)
    elif days_since_first == 1:
        return greeting_templates["returning_one_day"](user_first_name)
    elif 2 <= days_since_first <= 6:
        return greeting_templates["returning_few_days"](user_first_name, days_since_first)
    else:
        return greeting_templates["regular_user"](user_first_name, days_since_first)


def update_user_memory_after_conversation(user, conversation):
    try:
        user_memory = get_or_create_user_memory(user)

        from .response_generator import extract_conversation_facts

        messages = conversation.messages.only("role", "content").order_by("timestamp")
        conversation_history = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        facts = extract_conversation_facts(conversation_history)
        user_memory.update_from_conversation(facts)

        today = date.today()

        if not user_memory.first_conversation_date:
            user_memory.first_conversation_date = today

        user_memory.last_conversation_date = today
        user_memory.save()

        print(f"Updated UserMemory for {user.username}")
        print(f"  Topics: {user_memory.get_top_topics(3)}")
        print(f"  Days since first conversation: {user_memory.get_days_since_first_conversation()}")
        print(f"  Total conversations: {user_memory.total_conversations}")

    except Exception as e:
        print(f"Error updating user memory: {str(e)}")
        import traceback
        traceback.print_exc()


def get_or_create_message_limit(user):
    limit, created = MessageLimit.objects.get_or_create(
        user=user,
        defaults={
            "total_messages": 15,
            "messages_remaining": 15,
            "reset_time": timezone.now() + timedelta(hours=4),
        },
    )

    if created:
        print(f"Created message limit for {user.username}")

    if limit.get_time_remaining() <= 0:
        limit.reset_limit()

    return limit


async def chat_api_send_streaming(request):
    is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
    if not is_authenticated:
        return redirect("login")
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)

        get_limit = sync_to_async(get_or_create_message_limit)
        limit = await get_limit(request.user)

        if limit.messages_remaining <= 0 and timezone.now() < limit.reset_time:
            return JsonResponse(
                {
                    "error": "Message limit reached",
                    "message": f"You have no messages remaining. Please wait {limit.get_formatted_time_remaining()} to get another {limit.total_messages} messages.",
                    "limit_reached": True,
                    "time_remaining": limit.get_time_remaining(),
                },
                status=429,
            )

        check_limit = sync_to_async(limit.can_send_message)
        if not await check_limit():
            return JsonResponse(
                {"error": "Unexpected limit error", "limit_reached": True}, status=429
            )

        use_message = sync_to_async(limit.use_message)
        await use_message()
        print(f"Message used: {limit.messages_remaining}/{limit.total_messages} remaining")

        user_message = data.get("message", "").strip()

        if not user_message:
            return JsonResponse({"error": "Message is required"}, status=400)

        user_message = ContentSafety.sanitize_input(user_message)
        conversation = await sync_to_async(get_active_conversation)(request.user)
        await sync_to_async(ensure_initial_greeting)(conversation, request.user)
        user_first_name = request.user.first_name if request.user.first_name else None

        is_developer = is_developer_account(request.user)
        developer_email = request.user.email if is_developer else None

        await sync_to_async(Message.objects.create)(
            conversation=conversation, role="user", content=user_message
        )

        conversation_history, _ = await sync_to_async(get_conversation_history_with_limit)(
            conversation, max_tokens=24000
        )

        async def master_stream():
            full_response = ""
            error_occurred = False

            try:
                yield f"data: {json.dumps({'status': 'thinking'})}\n\n"

                from .models import UserMemory
                get_user_memory = sync_to_async(UserMemory.objects.get)
                previous_query = None
                try:
                    user_mem = await get_user_memory(user=request.user)
                    if "media_requests" in user_mem.mentioned_activities:
                        requests_list = user_mem.mentioned_activities["media_requests"]
                        if isinstance(requests_list, list) and requests_list:
                            previous_query = requests_list[-1].get("query")
                except Exception:
                    pass

                detect_media = sync_to_async(detect_media_request)
                media_detection = await detect_media(user_message, previous_query)

                if media_detection["is_media_request"]:
                    yield f"data: {json.dumps({'status': 'searching'})}\n\n"

                    handle_media = sync_to_async(handle_media_request)
                    response = await handle_media(
                        request,
                        user_message,
                        conversation,
                        conversation_history,
                        media_detection,
                        user_first_name,
                        is_developer,
                        developer_email,
                    )

                    data_dict = json.loads(response.content.decode('utf-8'))
                    yield f"data: {json.dumps(data_dict)}\n\n"
                    return

                yield f"data: {json.dumps({'status': 'typing'})}\n\n"

                is_safe, category, safety_response, needs_llm = ContentSafety.check_content(
                    user_message, conversation_history
                )

                if not is_safe and not needs_llm:
                    for word in safety_response.split():
                        chunk = word + " "
                        full_response += chunk
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                else:
                    llm_service = get_llm_service()
                    from .timezone_utils import get_time_context
                    time_context = get_time_context("Asia/Manila")

                    chunk_count = 0
                    async for chunk in llm_service.generate_response_streaming_async(
                        conversation_history,
                        user_name=user_first_name,
                        time_context=time_context,
                        is_developer=is_developer,
                        developer_email=developer_email,
                    ):
                        if chunk:
                            chunk_count += 1
                            full_response += chunk
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

                    if chunk_count == 0:
                        error_occurred = True
                        print("No chunks - using fallback")
                        fallback_msg = random.choice(API_FAILURE_FALLBACKS)
                        for word in fallback_msg.split():
                            chunk = word + " "
                            full_response += chunk
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        try:
                            message_create = sync_to_async(Message.objects.create)
                            conversation_save = sync_to_async(conversation.save)
                            await message_create(
                                conversation=conversation,
                                role="assistant",
                                content=full_response,
                            )
                            await conversation_save()
                        except Exception as save_error:
                            print(f"Failed to save: {save_error}")

                if full_response and not error_occurred:
                    message_create = sync_to_async(Message.objects.create)
                    conversation_save = sync_to_async(conversation.save)
                    update_memory = sync_to_async(update_user_memory_after_conversation)

                    await message_create(
                        conversation=conversation,
                        role="assistant",
                        content=full_response,
                    )
                    await conversation_save()
                    await update_memory(request.user, conversation)

                yield f"data: {json.dumps({'done': True, 'full_response': full_response})}\n\n"

            except Exception as e:
                print(f"Streaming error: {e}")
                import traceback
                traceback.print_exc()

                error_msg = random.choice(API_FAILURE_FALLBACKS)
                try:
                    message_create = sync_to_async(Message.objects.create)
                    conversation_save = sync_to_async(conversation.save)
                    await message_create(
                        conversation=conversation,
                        role="assistant",
                        content=error_msg,
                    )
                    await conversation_save()
                except Exception:
                    pass

                for word in error_msg.split():
                    chunk = word + " "
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"

                yield f"data: {json.dumps({'done': True, 'full_response': error_msg})}\n\n"

        return StreamingHttpResponse(
            master_stream(),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": "An unexpected error occurred. Please try again."}, status=500)



def handle_media_request(
    request,
    user_message,
    conversation,
    conversation_history,
    media_detection,
    user_first_name,
    is_developer,
    developer_email,
):
    from .media_service import MediaService
    from .media_pagination import (
        MediaPaginationManager,
        generate_more_response_message,
        generate_no_results_fallback,
    )
    import random
    from .response_generator import API_FAILURE_FALLBACKS
    from .media_views import (
        extract_image_query_smart,
        extract_video_query_smart,
        generate_media_context,
        update_memory_after_media_request,
    )
    from .models import Message

    pagination_manager = MediaPaginationManager()

    is_more_pattern = media_detection["is_more_request"]
    media_type = media_detection["media_type"]
    count = media_detection["count"]

    last_bot_msg = (
        conversation.messages.filter(role="assistant", is_media_message=True)
        .order_by("-timestamp")
        .first()
    )

    previous_query = last_bot_msg.media_data.get("query") if last_bot_msg and last_bot_msg.media_data else None
    previous_media_type = last_bot_msg.media_type if last_bot_msg else None

    is_actual_more_request = is_more_pattern and last_bot_msg is not None

    print(
        f"Request analysis: "
        f"pattern={is_more_pattern}, "
        f"has_previous={last_bot_msg is not None}, "
        f"actual_more={is_actual_more_request}, "
        f"count={count}"
    )

    if is_actual_more_request:
        print("Processing 'more' request with pagination...")

        previous_count = len(last_bot_msg.media_data.get(
            "videos" if previous_media_type == "video" else "images", []
        ))

        count = previous_count if previous_count > 0 else 3

        print(f"'More' request - query: '{previous_query}', type: {media_type}, count: {count}")

        query = previous_query
        media_type = media_detection.get("media_type") or previous_media_type

        media_service = MediaService()

        search_result = media_service.search_media(
            query=query,
            media_type=media_type,
            count=count * 3
        )

        if search_result.get("success") and search_result.get("results"):
            all_results = search_result["results"]

            next_batch, has_more = pagination_manager.get_next_batch(
                user_id=request.user.id,
                query=query,
                media_type=media_type,
                all_available_items=all_results
            )

            if len(next_batch) < count:
                print(f"Only {len(next_batch)} unseen items, forcing {count} items from fresh results")
                next_batch = all_results[:count]
                has_more = len(all_results) > count
                print(f"Using first {count} from fresh search results")

            if not next_batch or len(next_batch) == 0:
                no_more_msg = (
                    f"I don't have additional {media_type}s at the moment. "
                    "Feel free to explore the ones I shared earlier, "
                    "or ask about a different topic!"
                )

                Message.objects.create(
                    conversation=conversation,
                    role="assistant",
                    content=no_more_msg
                )

                return JsonResponse({
                    "success": True,
                    "response": no_more_msg,
                    "is_media": False
                })

            intro_text, outro_text = generate_media_context(
                user_message=user_message,
                conversation_history=conversation_history,
                media_type=media_type,
                query=query,
                user_first_name=user_first_name,
                is_developer=is_developer,
                developer_email=developer_email,
                is_more_request=True,
                has_more_available=has_more
            )

            if not intro_text or not outro_text:
                intro_text, outro_text = generate_more_response_message(
                    has_items=True,
                    item_count=len(next_batch),
                    has_more=has_more,
                    media_type=media_type,
                    query=query
                )

            if media_type == "video":
                media_data = {
                    "intro": intro_text,
                    "videos": [
                        {
                            "number": i + 1,
                            "videoId": result.get("video_id", ""),
                            "url": result.get("url", ""),
                            "title": result.get("title", "Untitled Video"),
                            "description": result.get("description", ""),
                            "thumbnail": result.get("thumbnail", ""),
                            "channel": result.get("channel_title", "Unknown Channel"),
                            "channel_title": result.get("channel_title", "Unknown Channel"),
                            "channel_url": result.get("channel_url", ""),
                        }
                        for i, result in enumerate(next_batch)
                    ],
                    "outro": outro_text,
                    "query": query
                }
            else:
                media_data = {
                    "intro": intro_text,
                    "images": [
                        {
                            "url": result.get("url", ""),
                            "alt": result.get("alt", ""),
                            "photographer": result.get("photographer", ""),
                            "photographer_url": result.get("photographer_url", ""),
                        }
                        for result in next_batch
                    ],
                    "outro": outro_text,
                    "query": query
                }

            media_msg = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content="",
                is_media_message=True,
                media_type=media_type,
                media_data=media_data,
            )

            pagination_manager.record_shown_items(
                user_id=request.user.id,
                query=query,
                media_type=media_type,
                items=next_batch,
                is_initial=False
            )

            update_memory_after_media_request(
                request.user, query, media_type, len(next_batch)
            )

            print(f"Returned {len(next_batch)} more items ({'singular' if count == 1 else 'plural'}), has_more: {has_more}")

            return JsonResponse({
                "success": True,
                "is_media": True,
                "media_type": media_type,
                "media_data": media_data,
                "message_id": media_msg.message_id,
            })

        else:
            no_results_msg = (
                f"I couldn't find any more {media_type}s about '{query}' "
                "at the moment."
            )

            Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=no_results_msg
            )

            return JsonResponse({
                "success": True,
                "response": no_results_msg,
                "is_media": False
            })

    print(f"Processing INITIAL media request (type={media_type}, count={count})")

    if media_type == "image":
        query = extract_image_query_smart(user_message, previous_query)
    elif media_type == "video":
        query = extract_video_query_smart(user_message, previous_query)
    else:
        query = extract_video_query_smart(user_message, previous_query)
        if not media_type:
            media_type = "video"

    print(f"Query: '{query}', Type: {media_type}, Count: {count} ({'singular' if count == 1 else 'plural'})")

    intro_text, outro_text = generate_media_context(
        user_message,
        conversation_history,
        media_type,
        query,
        user_first_name,
        is_developer,
        developer_email,
        is_more_request=False,
        has_more_available=False
    )

    if not intro_text or not outro_text:
        fallback_msg = random.choice(API_FAILURE_FALLBACKS)
        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=fallback_msg
        )
        return JsonResponse({
            "success": True,
            "response": fallback_msg,
            "is_media": False
        })

    media_service = MediaService()
    search_count = count * 2

    media_results = media_service.search_media(
        query=query,
        media_type=media_type,
        count=search_count
    )

    if media_results.get("success") and media_results.get("results"):
        all_results = media_results["results"]

        initial_batch = all_results[:count]
        has_more = len(all_results) > count

        print(
            f"Found {len(all_results)} total, "
            f"showing {len(initial_batch)} ({'singular' if count == 1 else 'plural'}), "
            f"has_more: {has_more}"
        )

        if has_more and outro_text:
            if not any(word in outro_text.lower() for word in ['more', 'additional']):
                outro_text = (
                    outro_text.rstrip('.!') +
                    " - let me know if you'd like to see more!"
                )

        if media_type == "video":
            media_data = {
                "intro": intro_text,
                "videos": [
                    {
                        "number": i + 1,
                        "videoId": result.get("video_id", ""),
                        "url": result.get("url", ""),
                        "title": result.get("title", "Untitled Video"),
                        "description": result.get("description", ""),
                        "thumbnail": result.get("thumbnail", ""),
                        "channel": result.get("channel_title", "Unknown Channel"),
                        "channel_title": result.get("channel_title", "Unknown Channel"),
                        "channel_url": result.get("channel_url", ""),
                    }
                    for i, result in enumerate(initial_batch)
                ],
                "outro": outro_text,
                "query": query
            }
        else:
            media_data = {
                "intro": intro_text,
                "images": [
                    {
                        "url": result.get("url", ""),
                        "alt": result.get("alt", ""),
                        "photographer": result.get("photographer", ""),
                        "photographer_url": result.get("photographer_url", ""),
                    }
                    for result in initial_batch
                ],
                "outro": outro_text,
                "query": query
            }

        media_msg = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content="",
            is_media_message=True,
            media_type=media_type,
            media_data=media_data,
        )

        print(f"Saved media message: {media_type}, {len(initial_batch)} items ({'singular' if count == 1 else 'plural'})")

        pagination_manager.record_shown_items(
            user_id=request.user.id,
            query=query,
            media_type=media_type,
            items=initial_batch,
            is_initial=True
        )

        update_memory_after_media_request(
            request.user, query, media_type, len(initial_batch)
        )

        return JsonResponse({
            "success": True,
            "is_media": True,
            "media_type": media_type,
            "media_data": media_data,
            "message_id": media_msg.message_id,
        })

    else:
        print(f"No {media_type} results for: {query}")

        no_results_msg = generate_no_results_fallback(
            query=query,
            media_type=media_type,
            count=count
        )

        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=no_results_msg
        )

        return JsonResponse({
            "success": True,
            "response": no_results_msg,
            "is_media": False
        })


def extract_topics_from_message(content: str) -> list:
    if not content or len(content.strip()) < 5:
        return []

    try:
        llm_service = get_llm_service()

        extraction_prompt = f"""Analyze this message and identify the main life topics being discussed.

Message: "{content}"

Return ONLY a comma-separated list of general topic categories.
Use broad category names. Maximum 5 topics. If no clear topics, return "general conversation".

Topics:"""

        response = llm_service.generate_response(
            conversation_history=[{"role": "user", "content": extraction_prompt}],
            user_name=None,
            time_context=None,
            max_retries=1,
            is_extraction=True,
        )

        if response and not ("[[EMAIL:" in response or "[[FEEDBACK:" in response):
            topics = [topic.strip().lower() for topic in response.split(",")]
            topics = [t for t in topics if t and len(t) > 2][:5]

            if topics and topics[0] != "general conversation":
                return topics

    except Exception as e:
        print(f"Topic extraction failed: {str(e)}")

    return extract_important_words(content, max_words=3)


def extract_emotions_from_message(content: str) -> list:
    if not content or len(content.strip()) < 5:
        return []

    try:
        llm_service = get_llm_service()

        extraction_prompt = f"""Analyze the emotional tone of this message.

Message: "{content}"

Return ONLY a comma-separated list of emotions detected.
Use simple emotion names. Maximum 3 emotions. If no clear emotions, return "neutral".

Emotions:"""

        response = llm_service.generate_response(
            conversation_history=[{"role": "user", "content": extraction_prompt}],
            user_name=None,
            time_context=None,
            max_retries=1,
            is_extraction=True,
        )

        if response and not ("[[EMAIL:" in response or "[[FEEDBACK:" in response):
            emotions = [emotion.strip().lower() for emotion in response.split(",")]
            emotions = [e for e in emotions if e and len(e) > 2][:3]

            if emotions and emotions[0] != "neutral":
                return emotions

    except Exception as e:
        print(f"Emotion extraction failed: {str(e)}")

    return []


def extract_important_words(text: str, max_words: int = 5) -> list:
    if not text:
        return []

    words = text.lower().split()
    important = []

    for word in words:
        cleaned = re.sub(r'[^\w]', '', word)

        if len(cleaned) < 4 or cleaned.isdigit():
            continue

        if len(cleaned) <= 4:
            continue

        important.append(cleaned)

        if len(important) >= max_words:
            break

    return important


def extract_semantic_title_from_message(content: str, max_length: int = 40) -> str:
    if not content or len(content.strip()) < 5:
        return "New Chat"

    try:
        llm_service = get_llm_service()

        title_prompt = f"""Generate a brief, natural title for a conversation that starts with this message.

Message: "{content[:200]}"

Create a title that captures the main subject (maximum 6 words, no quotes).
Make it sound like a journal entry title.

Title:"""

        response = llm_service.generate_response(
            conversation_history=[{"role": "user", "content": title_prompt}],
            user_name=None,
            time_context=None,
            max_retries=1,
            is_extraction=True,
        )

        if response and not ("[[EMAIL:" in response or "[[FEEDBACK:" in response):
            title = response.replace('"', '').replace("'", '').strip()
            title = re.sub(r'\s+', ' ', title)

            if len(title) > max_length:
                title = title[:max_length - 3] + "..."

            if len(title) >= 5:
                return title

    except Exception as e:
        print(f"Semantic title extraction failed: {str(e)}")

    words = content.split()[:6]
    title = " ".join(words)

    if len(title) > max_length:
        title = title[:max_length - 3] + "..."

    return title if title else "New Chat"


async def generate_title(request):
    is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
    if not is_authenticated:
        return redirect("login")
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        get_conversation = sync_to_async(
            lambda: Conversation.objects.filter(user=request.user, is_active=True).first()
        )
        conversation = await get_conversation()

        if not conversation:
            title = f"Conversation - {datetime.now().strftime('%b %d, %Y')}"
            return JsonResponse({"success": True, "title": title})

        get_first_message = sync_to_async(
            lambda: conversation.messages.order_by("timestamp").first()
        )
        get_user_messages = sync_to_async(
            lambda: conversation.messages.filter(role="user").order_by("timestamp")
        )

        first_message = await get_first_message()
        conversation_date = first_message.timestamp if first_message else datetime.now()
        date_str = conversation_date.strftime("%b %d, %Y")

        user_messages_qs = await get_user_messages()
        user_messages = await sync_to_async(lambda: list(user_messages_qs))()

        if not user_messages:
            title = f"New Chat - {date_str}"
            return JsonResponse({"success": True, "title": title})

        conversation_summary = ""
        for msg in user_messages[:10]:
            conversation_summary += f"User: {msg.content}\n"

        try:
            llm_service = get_llm_service()

            title_prompt = f"""Based on this conversation, generate a creative, emotionally resonant title (maximum 50 characters).

Capture the essence and emotional core of the conversation.
Use concise, journal-entry style phrasing.
Avoid generic or formulaic titles.

Conversation:
{conversation_summary}

Generate ONLY the title (no quotes, no explanation):"""

            conversation_for_api = [{"role": "user", "content": title_prompt}]

            llm_title = await llm_service.generate_response_async(
                conversation_history=conversation_for_api,
                user_name=None,
                time_context=None,
                max_retries=1,
            )

            if llm_title and not ("[[EMAIL:" in llm_title or "[[FEEDBACK:" in llm_title):
                llm_title = llm_title.replace('"', "").replace("'", "").strip()

                if len(llm_title) > 55:
                    llm_title = llm_title[:52] + "..."

                if len(llm_title) >= 5:
                    title = f"{llm_title} - {date_str}"
                    return JsonResponse({"success": True, "title": title})

        except Exception as llm_error:
            print(f"LLM title generation failed: {str(llm_error)}")

        await asyncio.sleep(2)

        user_first_name = request.user.first_name if request.user.first_name else None
        first_user_msg = user_messages[0] if user_messages else None

        fallback_titles = []
        fallback_titles.append(f"Conversation - {date_str}")

        if user_first_name:
            fallback_titles.append(f"{user_first_name} & Snowfriend - {date_str}")

        if first_user_msg:
            first_content = first_user_msg.content.strip()

            appears_to_be_greeting = (
                len(first_content) < 20 or
                first_content.lower().startswith(('hi ', 'hello ', 'hey '))
            )

            if not appears_to_be_greeting and len(first_content) >= 10:
                words = first_content.split()
                natural_length = min(7, len(words))
                title_words = words[:natural_length]

                if title_words:
                    title_words[-1] = re.sub(r'[.,!?;:]+$', '', title_words[-1])

                first_msg_title = " ".join(title_words)

                if len(first_msg_title) >= 10:
                    fallback_titles.append(f"{first_msg_title} - {date_str}")

        fallback_titles.append(f"Talking with Snowfriend - {date_str}")

        companionship_options = [
            "A Moment of Connection",
            "Heart to Heart",
            "Friendly Chat",
            "Sharing Thoughts",
            "Safe Space",
        ]
        fallback_titles.append(f"{random.choice(companionship_options)} - {date_str}")

        title = random.choice(fallback_titles)

        print(f"Using hardcoded fallback title: {title}")
        return JsonResponse({"success": True, "title": title})

    except Exception as e:
        print(f"Error generating title: {str(e)}")
        import traceback
        traceback.print_exc()

        await asyncio.sleep(2)
        title = f"Conversation - {datetime.now().strftime('%b %d, %Y')}"
        return JsonResponse({"success": True, "title": title})


@login_required(login_url="login")
@require_http_methods(["POST"])
def export_conversation(request):
    try:
        data = json.loads(request.body)
        title = data.get("title", "Snowfriend Conversation")
        messages = data.get("messages", [])

        if not messages:
            return JsonResponse(
                {"success": False, "error": "No messages to export"}, status=400
            )

        safe_title = "".join(
            c for c in title if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        safe_title = safe_title[:100]

        text_content = f"{'='*60}\n"
        text_content += "Snowfriend Conversation Export\n"
        text_content += f"{'='*60}\n\n"
        text_content += f"Title: {title}\n"
        text_content += f"User: {request.user.username}\n"
        text_content += f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        text_content += f"Total Messages: {len(messages)}\n"
        text_content += f"\n{'='*60}\n\n"

        for i, msg in enumerate(messages, 1):
            sender = msg.get("sender", "Unknown")
            content = msg.get("content", "").strip()
            timestamp = msg.get("formattedTime", "No timestamp")

            text_content += f"Message {i} - {sender}\n"
            text_content += f"Time: {timestamp}\n"
            text_content += f"{'-'*60}\n"
            text_content += f"{content}\n"
            text_content += f"\n{'='*60}\n\n"

        text_content += "\n\n--- End of Conversation ---\n"
        text_content += "Exported from Snowfriend © 2025\n"

        response = HttpResponse(text_content, content_type="text/plain; charset=utf-8")
        filename = f"{safe_title.replace(' ', '_')}.txt"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON data"}, status=400
        )
    except Exception as e:
        print(f"Error exporting conversation: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {"success": False, "error": f"Export failed: {str(e)}"}, status=500
        )


def get_active_conversation(user):
    try:
        conversation = Conversation.objects.filter(user=user, is_active=True).first()

        if conversation:
            active_count = Conversation.objects.filter(user=user, is_active=True).count()

            if active_count > 1:
                active_conversations = Conversation.objects.filter(
                    user=user, is_active=True
                ).order_by("-updated_at")

                with transaction.atomic():
                    for conv in active_conversations[1:]:
                        conv.is_active = False
                        conv.save()

                conversation = active_conversations.first()
                print(f"Fixed {active_count-1} duplicate active conversations for {user.username}")

            return conversation
        else:
            conversation = Conversation.objects.create(user=user, is_active=True)
            return conversation

    except Exception as e:
        print(f"Error getting active conversation: {str(e)}")
        return Conversation.objects.create(user=user, is_active=True)


def count_tokens(text):
    if not text:
        return 0
    return max(1, len(text) // 4)


def get_conversation_history_with_limit(conversation, max_tokens=24000):
    all_messages = conversation.messages.only("role", "content").order_by("timestamp")
    messages_to_process = list(all_messages)

    if not messages_to_process:
        return [], False

    messages_reversed = list(reversed(messages_to_process))
    selected_messages = []
    total_tokens = 0
    was_truncated = False

    for msg in messages_reversed:
        msg_tokens = count_tokens(msg.content)

        if total_tokens + msg_tokens <= max_tokens:
            selected_messages.append({"role": msg.role, "content": msg.content})
            total_tokens += msg_tokens
        else:
            was_truncated = True
            break

    selected_messages.reverse()
    return selected_messages, was_truncated


def ensure_initial_greeting(conversation, user):
    if conversation.messages.count() == 0:
        user_memory = get_or_create_user_memory(user)
        initial_greeting = generate_initial_greeting(user, user_memory)

        Message.objects.create(
            conversation=conversation, role="assistant", content=initial_greeting
        )

        print(f"Created dynamic initial greeting for {user.username} ({user_memory.get_days_since_first_conversation()} days)")


async def send_message(request):
    is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
    if not is_authenticated:
        return redirect("login")
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()

        if not user_message:
            return JsonResponse(
                {"success": False, "error": "Message cannot be empty"}, status=400
            )

        user_message = ContentSafety.sanitize_input(user_message)

        get_conversation = sync_to_async(get_active_conversation)
        ensure_greeting = sync_to_async(ensure_initial_greeting)
        conversation = await get_conversation(request.user)
        await ensure_greeting(conversation, request.user)

        user_first_name = request.user.first_name if request.user.first_name else None

        is_developer = is_developer_account(request.user)
        developer_email = request.user.email if is_developer else None

        get_history = sync_to_async(get_conversation_history_with_limit)
        conversation_history, _ = await get_history(conversation, max_tokens=24000)

        is_safe, category, safety_response, needs_llm = ContentSafety.check_content(
            user_message, conversation_history
        )

        create_message = sync_to_async(Message.objects.create)
        await create_message(
            conversation=conversation,
            role="user",
            content=user_message,
            is_flagged=not is_safe,
            flagged_reason=category if not is_safe else None,
        )

        if not is_safe and not needs_llm:
            bot_response = safety_response
            truncation_occurred = False

            import logging
            logger = logging.getLogger("snowfriend.crisis")
            logger.warning(
                f"CRISIS DETECTED - User: {request.user.username}, Category: {category}, Message: {user_message[:100]}"
            )
        else:
            try:
                llm_service = get_llm_service()

                conversation_history, truncation_occurred = await get_history(conversation, max_tokens=24000)

                from .timezone_utils import get_time_context
                time_context = get_time_context("Asia/Manila")

                bot_response = await llm_service.generate_response_async(
                    conversation_history,
                    user_name=user_first_name,
                    time_context=time_context,
                    is_developer=is_developer,
                    developer_email=developer_email,
                )

                if bot_response is None:
                    bot_response = random.choice(API_FAILURE_FALLBACKS)
                    print("LLM returned None - using API_FAILURE_FALLBACKS")

            except Exception as api_error:
                print(f"API Error: {str(api_error)} - using API_FAILURE_FALLBACKS")
                bot_response = random.choice(API_FAILURE_FALLBACKS)
                truncation_occurred = False

        create_bot_message = sync_to_async(Message.objects.create)
        save_conversation = sync_to_async(conversation.save)
        update_memory = sync_to_async(update_user_memory_after_conversation)

        await create_bot_message(
            conversation=conversation, role="assistant", content=bot_response
        )
        await save_conversation()
        await update_memory(request.user, conversation)

        response_data = {"success": True, "response": bot_response}

        if truncation_occurred:
            response_data["notification"] = {
                "message": "Some earlier messages have been removed to continue our conversation smoothly.",
                "type": "info",
            }

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON data"}, status=400
        )

    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {"success": True, "response": random.choice(API_FAILURE_FALLBACKS)}
        )


@login_required(login_url="login")
@require_http_methods(["GET"])
def get_conversation_history(request):
    try:
        conversation = (
            Conversation.objects.filter(user=request.user, is_active=True)
            .only("conversation_id")
            .first()
        )

        if not conversation:
            return JsonResponse({"success": True, "messages": []})

        ensure_initial_greeting(conversation, request.user)
        messages = conversation.messages.only(
            "role",
            "content",
            "timestamp",
            "is_media_message",
            "media_type",
            "media_data",
        ).all()

        messages_data = []
        for msg in messages:
            message_obj = {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }

            if msg.is_media_message:
                message_obj["is_media_message"] = True
                message_obj["media_type"] = msg.media_type
                message_obj["media_data"] = msg.media_data

            messages_data.append(message_obj)

        return JsonResponse({"success": True, "messages": messages_data})

    except Exception as e:
        print(f"Error in get_conversation_history: {str(e)}")
        return JsonResponse(
            {"success": False, "error": "Could not retrieve conversation history"},
            status=500,
        )


@login_required(login_url="login")
@require_http_methods(["POST"])
def clear_conversation(request):
    try:
        conversations = Conversation.objects.filter(user=request.user)
        count = conversations.count()

        if count > 0:
            conversations.delete()
            print(f"Permanently deleted {count} conversation(s) for user: {request.user.username}")

            return JsonResponse(
                {
                    "success": True,
                    "message": f"All {count} conversation(s) permanently deleted",
                    "cleared": True,
                }
            )
        else:
            return JsonResponse(
                {
                    "success": True,
                    "message": "No conversations to clear",
                    "cleared": False,
                }
            )

    except Exception as e:
        print(f"Error in clear_conversation: {str(e)}")
        return JsonResponse(
            {"success": False, "error": "Could not clear conversation"}, status=500
        )


@login_required(login_url="login")
@require_http_methods(["POST"])
def clear_conversation_and_memory(request):
    try:
        conversations = Conversation.objects.filter(user=request.user)
        conv_count = conversations.count()
        conversations.delete()

        try:
            user_memory = UserMemory.objects.get(user=request.user)
            user_memory.delete()
            memory_deleted = True
            print(f"Permanently deleted UserMemory for {request.user.username}")
        except UserMemory.DoesNotExist:
            memory_deleted = False
            print(f"No UserMemory found for {request.user.username}")

        from .media_pagination import MediaPaginationManager
        pagination_manager = MediaPaginationManager()
        pagination_manager.clear_all_user_states(request.user.id)

        print(f"Permanently deleted {conv_count} conversation(s) for user: {request.user.username}")

        return JsonResponse(
            {
                "success": True,
                "message": f"All {conv_count} conversation(s) and memory permanently deleted",
                "cleared": True,
                "memory_deleted": memory_deleted,
            }
        )

    except Exception as e:
        print(f"Error in clear_conversation_and_memory: {str(e)}")
        return JsonResponse(
            {"success": False, "error": "Could not clear conversation and memory"},
            status=500,
        )


@login_required(login_url="login")
@require_http_methods(["GET"])
def get_user_memory_summary(request):
    try:
        user_memory = get_or_create_user_memory(request.user)

        summary = {
            "total_conversations": user_memory.total_conversations,
            "total_messages": user_memory.total_messages,
            "top_topics": user_memory.get_top_topics(5),
            "mentioned_people": list(user_memory.mentioned_people.keys())[:5],
            "common_emotions": dict(
                sorted(
                    user_memory.common_emotions.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
            ),
            "last_topics": user_memory.last_topics_discussed[:5],
            "memory_summary": user_memory.get_memory_summary(),
        }

        return JsonResponse({"success": True, "memory": summary})

    except Exception as e:
        print(f"Error getting user memory: {str(e)}")
        return JsonResponse(
            {"success": False, "error": "Could not retrieve user memory"}, status=500
        )


@login_required(login_url="login")
@require_http_methods(["GET"])
def get_message_limit(request):
    try:
        limit = get_or_create_message_limit(request.user)

        notifications = []

        if limit.should_notify_half():
            notifications.append(
                {
                    "type": "half",
                    "message": f"You've used half your messages! {limit.messages_remaining} remaining.",
                }
            )
            limit.mark_notified("half")

        if limit.should_notify_three():
            notifications.append(
                {"type": "three", "message": "Only 3 messages left! Use them wisely."}
            )
            limit.mark_notified("three")

        if limit.should_notify_zero():
            notifications.append({"type": "zero", "message": "No messages remaining."})
            limit.mark_notified("zero")

        return JsonResponse(
            {
                "success": True,
                "total_messages": limit.total_messages,
                "messages_remaining": limit.messages_remaining,
                "can_send": limit.can_send_message(),
                "time_remaining_seconds": limit.get_time_remaining(),
                "time_remaining_formatted": limit.get_formatted_time_remaining(),
                "reset_time": limit.reset_time.isoformat(),
                "notifications": notifications,
            }
        )

    except Exception as e:
        print(f"Error getting message limit: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)