# views.py
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
import json, random, re
from .models import Conversation, Message, UserMemory, MessageLimit
from datetime import datetime, timedelta, date
from django.utils import timezone
from .safety import ContentSafety
from .services import LLMService
# ✅ CRITICAL FIX: Import API_FAILURE_FALLBACKS from response_generator
from .response_generator import API_FAILURE_FALLBACKS

def is_developer_account(user):
    """
    ✅ CRITICAL: Verify if user is Marc Daryll Trinidad (developer)
    
    Returns True ONLY for: marcdaryll.trinidad@gmail.com
    Returns False for: marc_doe@yahoo.com, marc.smith@gmail.com, etc.
    """
    if not user or not hasattr(user, 'email') or not user.email:
        return False
    
    DEVELOPER_EMAIL = 'marcdaryll.trinidad@gmail.com'
    user_email_normalized = user.email.lower().strip()
    
    is_match = (user_email_normalized == DEVELOPER_EMAIL.lower())
    
    if is_match:
        print(f"✓ Developer mode ACTIVATED for: {user.email}")
    
    return is_match

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_or_create_user_memory(user):
    memory, created = UserMemory.objects.get_or_create(user=user)
    if created:
        print(f"✓ Created new UserMemory for {user.username}")
    return memory


def generate_initial_greeting(user, user_memory):
    """
    Generate contextual greeting based on user's engagement history.
    
    Adjusts greeting tone and content based on:
    - Days since first conversation
    - User's conversation patterns
    - Relationship establishment level
    
    Returns:
        str: Personalized greeting message
    """
    user_first_name = user.first_name if user.first_name else 'there'
    days_since_first = user_memory.get_days_since_first_conversation()
    
    # Greeting templates keyed by engagement level
    greeting_templates = {
        'new_user': lambda name: f"Hi {name}! I'm Snowfriend. You can share your thoughts here at your own pace. I'm here to listen and help you reflect.\n\n",
        'returning_one_day': lambda name: f"Hi {name}, welcome back! It's been a day since we last talked. I'm still here to listen whenever you need.\n\n",
        'returning_few_days': lambda name, days: f"Hi {name}, welcome back! Looks like we've been talking for {days} days now. I'm still here to listen and help you reflect.\n\n",
        'regular_user': lambda name, days: f"Hi {name}, it's been over a week! We've been talking for {days} days now. I'm always here when you need me.\n\n"
    }
    
    if days_since_first == 0:
        return greeting_templates['new_user'](user_first_name)
    elif days_since_first == 1:
        return greeting_templates['returning_one_day'](user_first_name)
    elif 2 <= days_since_first <= 6:
        return greeting_templates['returning_few_days'](user_first_name, days_since_first)
    else:
        return greeting_templates['regular_user'](user_first_name, days_since_first)
    
    
def update_user_memory_after_conversation(user, conversation):
    try:
        user_memory = get_or_create_user_memory(user)
        
        from .memory_system import ConversationMemory
        memory_system = ConversationMemory()
        
        messages = conversation.messages.only('role', 'content').order_by('timestamp')
        conversation_history = [
            {'role': msg.role, 'content': msg.content}
            for msg in messages
        ]
        
        facts = memory_system.extract_conversation_facts(conversation_history)
        user_memory.update_from_conversation(facts)
        
        # ✅ NEW: Update conversation dates
        today = date.today()
        
        # Set first conversation date if this is the first time
        if not user_memory.first_conversation_date:
            user_memory.first_conversation_date = today
        
        # Always update last conversation date
        user_memory.last_conversation_date = today
        user_memory.save()
        
        print(f"✓ Updated UserMemory for {user.username}")
        print(f"  Topics: {user_memory.get_top_topics(3)}")
        print(f"  Days since first conversation: {user_memory.get_days_since_first_conversation()}")
        print(f"  Total conversations: {user_memory.total_conversations}")
        
    except Exception as e:
        print(f"⚠️ Error updating user memory: {str(e)}")
        import traceback
        traceback.print_exc()


def get_or_create_message_limit(user):
    """Get or create message limit for user"""
    limit, created = MessageLimit.objects.get_or_create(
        user=user,
        defaults={
            'total_messages': 15,
            'messages_remaining': 15,
            'reset_time': timezone.now() + timedelta(hours=4)
        }
    )
    
    if created:
        print(f"✓ Created message limit for {user.username}")
    
    # Check if reset time has passed
    if limit.get_time_remaining() <= 0:
        limit.reset_limit()
    
    return limit

def extract_user_topic_from_message(message: str) -> str:
    """
    Extract the actual topic user wants content about from their message.
    
    Strategy:
    - Identifies action phrases (improve, manage, deal with, etc.)
    - Extracts subject matter following these phrases
    - Removes conversational filler and normalizes spacing
    - Returns clean topic string for content search
    
    Returns:
        str: Extracted topic or "this topic" if extraction fails
    """
    msg_lower = message.lower()
    
    # Strategy 1: "improve/improving X"
    improve_patterns = [
        r'(improve|improving|boost|boosting|increase|increasing|enhance|enhancing) (?:my |the )?(.+?)(?:\?|$)',
        r'how to (improve|boost|increase) (.+?)(?:\?|$)',
        r'get better at (.+?)(?:\?|$)',
        r'be (better|good|great) at (.+?)(?:\?|$)',
    ]
    
    for pattern in improve_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            # Get the last group (the topic)
            topic = match.groups()[-1].strip()
            # Clean up
            topic = topic.split('even though')[0].strip()
            topic = topic.split('but')[0].strip()
            topic = re.sub(r'\s+', ' ', topic)
            if len(topic) > 3:
                return topic
    
    # Strategy 2: "dealing with/managing/coping with X"
    managing_patterns = [
        r'(deal|dealing|manage|managing|cope|coping|handle|handling) with (.+?)(?:\?|$)',
        r'how to (deal|manage|cope|handle) (.+?)(?:\?|$)',
    ]
    
    for pattern in managing_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            topic = match.groups()[-1].strip()
            topic = topic.split('even though')[0].strip()
            if len(topic) > 3:
                return topic
    
    # Strategy 3: "videos about X"
    if 'video' in msg_lower:
        about_match = re.search(r'videos? (?:about|on|for|to help with|that show) (.+?)(?:\?|$)', msg_lower)
        if about_match:
            topic = about_match.group(1).strip()
            if len(topic) > 3:
                return topic
    
    # Strategy 4: Extract last meaningful noun phrase
    # Remove stop words and get last 2-3 meaningful words
    words = msg_lower.replace('?', '').split()
    stop_words = {'video', 'videos', 'some', 'any', 'could', 'would', 'can', 'you',
                 'show', 'me', 'please', 'find', 'get', 'give', 'i', 'my', 'the', 'a', 'an'}
    
    meaningful = [w for w in words if len(w) > 3 and w not in stop_words]
    
    if meaningful:
        # Take last 3 meaningful words
        topic = ' '.join(meaningful[-3:])
        return topic
    
    return "this topic"

def extract_video_query_smart(user_message: str, is_video_request: bool) -> str:
    """
    Extract media search query from user's request using pattern matching.
    
    Extraction strategies (in priority order):
    - Direct assistance requests ("help me with/to")
    - Guidance requests ("tips on/for", "advice about")
    - Topic indicators ("about", "for" - uses last occurrence for specificity)
    - Action phrases at sentence end ("managing", "improving", "learning")
    - Improvement queries ("how to improve/get better at")
    - Possessive constructions ("my/the X")
    - Final noun phrases before question marks
    
    Returns:
        str: Extracted search query, or fallback if extraction fails
    """
    import re
    
    msg_lower = user_message.lower()
    
    # Find the sentence containing video request
    sentences = msg_lower.split('.')
    video_sentence = None
    
    for sentence in sentences:
        if 'video' in sentence or 'videos' in sentence:
            video_sentence = sentence.strip()
            break
    
    if not video_sentence:
        video_sentence = msg_lower
    
    query = None
    
    # Strategy A: "help me with X" or "help me X"
    help_patterns = [
        r'help me (?:with |to )?(.+?)(?:\?|$|or|even)',
        r'help me (.+?)(?:\?|$|or|even)',
    ]
    for pattern in help_patterns:
        match = re.search(pattern, video_sentence)
        if match:
            query = match.group(1).strip()
            break
    
    # Strategy B: "tips on X" or "tips for X"
    if not query:
        tips_patterns = [
            r'tips? (?:on|for|about) (.+?)(?:\?|$|or|even)',
        ]
        for pattern in tips_patterns:
            match = re.search(pattern, video_sentence)
            if match:
                query = match.group(1).strip()
                break
    
    # Strategy C: "advice about X"
    if not query:
        advice_patterns = [
            r'advice (?:on|about|for) (.+?)(?:\?|$|or|even)',
        ]
        for pattern in advice_patterns:
            match = re.search(pattern, video_sentence)
            if match:
                query = match.group(1).strip()
                break
    
    # Strategy D: "about X" (take LAST occurrence = most specific)
    if not query:
        about_matches = list(re.finditer(r'about (.+?)(?:\?|$|or|even)', video_sentence))
        if about_matches:
            query = about_matches[-1].group(1).strip()
    
    # Strategy E: "for X" (take LAST occurrence)
    if not query:
        for_matches = list(re.finditer(r'for (.+?)(?:\?|$|or|even)', video_sentence))
        if for_matches:
            query = for_matches[-1].group(1).strip()
    
    # Strategy F: Action phrases at END of sentence
    if not query:
        action_patterns = [
            r'(managing|improving|learning|dealing with|coping with|understanding) (.+?)(?:\?|$)',
        ]
        for pattern in action_patterns:
            matches = list(re.finditer(pattern, video_sentence))
            if matches:
                query = matches[-1].group(0).strip('? ')
                break
            
    # ✅ NEW Strategy G: "how to improve/get better at X"
    if not query:
        how_to_patterns = [
            r'how to (improve|get better at|be good at|master) (.+?)(?:\?|$)',
            r'videos? (?:to |that )help (?:me )?(?:improve|get better|learn) (.+?)(?:\?|$)',
        ]
        for pattern in how_to_patterns:
            match = re.search(pattern, video_sentence)
            if match:
                query = match.groups()[-1].strip()
                break

    # ✅ NEW Strategy H: "my X" or "the X" (possessive + noun)
    if not query:
        possessive_match = re.search(r'(my |the |our )([\w\s]{3,20})(?:\?|$)', video_sentence)
        if possessive_match:
            potential_topic = possessive_match.group(2).strip()
            # Validate it's not a verb or filler
            filler_words = {'time', 'mind', 'thing', 'stuff', 'body', 'life', 'self', 'head'}
            if potential_topic not in filler_words:
                query = potential_topic

    # ✅ NEW Strategy I: Last noun phrase before "?"
    if not query:
        sentence_before_q = video_sentence.split('?')[0] if '?' in video_sentence else video_sentence
        words = sentence_before_q.split()
        # Get last 3-5 words
        if len(words) >= 3:
            potential_query = ' '.join(words[-5:])
            # Clean up
            potential_query = re.sub(r'^(on|for|about|with|at|in|to|the|a|an)\s+', '', potential_query)
            if len(potential_query) > 5:
                query = potential_query
    
    # Clean up the query
    if query:
        # Remove filler phrases
        query = re.sub(r'^(take my mind off all this|)', '', query).strip()
        query = re.sub(r'\s+', ' ', query)  # Collapse multiple spaces
        query = re.sub(r'\s+(or|even)$', '', query)  # Remove trailing "or" or "even"
        
        # If still too vague, extract meaningful words
        if len(query) < 3 or query in ['all this', 'this', 'that']:
            words = video_sentence.split()
            meaningful_words = [w for w in words if w not in [
                'video', 'videos', 'suggestion', 'suggestions', 'do', 'you', 
                'have', 'any', 'could', 'that', 'help', 'me', 'with', 'the'
            ]]
            if len(meaningful_words) >= 3:
                query = ' '.join(meaningful_words[-5:])  # Last 5 meaningful words
                query = query.strip('? .')
    
    # Final validation
    if not query or len(query) < 3:
        print(f"⚠️ Primary extraction failed, using fallback extraction for: {user_message[:50]}")
        
        # Universal fallback: extract meaningful nouns from entire message
        words = user_message.lower().split()
        
        # Remove filler words
        stop_words = {'video', 'videos', 'show', 'me', 'can', 'you', 'find', 
                     'get', 'give', 'any', 'some', 'please', 'thank', 'thanks',
                     'hello', 'hi', 'hey', 'feeling', 'right', 'now', 'even',
                     'though', 'worked', 'almost', 'years', 'not', 'is', 'my',
                     'the', 'a', 'an', 'as', 'at', 'by', 'for', 'from', 'in',
                     'of', 'on', 'to', 'with', 'has', 'have', 'had', 'been',
                     'this', 'that', 'these', 'those', 'are', 'was', 'were',
                     'be', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        
        meaningful_words = [w for w in words if len(w) > 3 and w not in stop_words]
        
        if len(meaningful_words) >= 3:
            # Take last 4-5 meaningful words (most likely the topic)
            query = ' '.join(meaningful_words[-5:])
            # Remove punctuation
            query = re.sub(r'[?.!,]', '', query).strip()
            print(f"✅ Fallback extracted: '{query}'")
            return query
        elif len(meaningful_words) >= 1:
            query = ' '.join(meaningful_words)
            query = re.sub(r'[?.!,]', '', query).strip()
            print(f"✅ Fallback extracted: '{query}'")
            return query
        else:
            # Absolute final fallback - still generic but better
            print("⚠️ No meaningful words found, using generic fallback")
            return "helpful tips and advice"
    
    # Clean up "on" at the start (e.g., "on managing time" → "managing time")
    query = re.sub(r'^(on|for|about)\s+', '', query)
    
    return query

def save_media_message(conversation, media_results, query, media_type):
    """
    Save media search results as a database message
    
    Args:
        conversation: Conversation object
        media_results: List of media results from MediaService
        query: User's search query
        media_type: 'video' or 'image'
    
    Returns:
        Message object
    """
    # Format intro text
    topic = query
    is_emotional = any(word in query.lower() for word in [
        'depressed', 'hopeless', 'sad', 'stressed', 'anxious', 'worried',
        'struggling', "can't", 'help me', 'feeling bad', 'down'
    ])
    
    if is_emotional:
        intro = f"I'm sorry you're going through this. Here are some {media_type}s about {topic} that might help:"
    else:
        intro = f"Here are some helpful {media_type}s about {topic}:"
    
    # Format outro
    if is_emotional:
        outro = f"These {media_type}s might give you some guidance. I'm here if you need to talk more about it."
    else:
        outro = "Let me know if you want more specific recommendations!"
    
    # Build media data structure
    media_data = {
        'intro': intro,
        'outro': outro,
        'query': query
    }
    
    if media_type == 'video':
        # ✅ FIXED: Use camelCase for frontend consistency
        media_data['videos'] = [
            {
                'title': video.get('title', ''),
                'url': video.get('url', ''),
                'videoId': video.get('video_id', ''),  # ✅ Changed from video_id to videoId
                'channel': video.get('channel_title', ''),
                'description': video.get('description', '')[:150] + '...' if video.get('description') else ''
            }
            for video in media_results
        ]
    elif media_type == 'image':
        media_data['images'] = [
            {
                'url': image.get('url', ''),
                'alt': image.get('alt', ''),
                'photographer': image.get('photographer', ''),
                'photographer_url': image.get('photographer_url', '')
            }
            for image in media_results
        ]
    
    # Create content string for text-based viewing (for export)
    content_lines = [intro, '']
    
    if media_type == 'video':
        for i, video in enumerate(media_data['videos'], 1):
            content_lines.append(f"{i}. {video['title']}")
            content_lines.append(f"🎬 {video['url']}")
            content_lines.append(f"By {video['channel']}")
            content_lines.append(f"{video['description']}")
            content_lines.append('')
    elif media_type == 'image':
        for i, image in enumerate(media_data['images'], 1):
            content_lines.append(f"{i}. {image['alt']}")
            content_lines.append(f"🖼️ {image['url']}")
            content_lines.append(f"📸 Photo by {image['photographer']}")
            if image['photographer_url']:
                content_lines.append(f"Source: {image['photographer_url']}")
            content_lines.append('')
    
    content_lines.append(outro)
    content_text = '\n'.join(content_lines)
    
    # Save message with media metadata
    message = Message.objects.create(
        conversation=conversation,
        role='assistant',
        content=content_text,  # Plain text version (for export)
        is_media_message=True,
        media_type=media_type,
        media_data=media_data  # Rich data (for rendering)
    )
    
    print(f"✅ Saved media message: {media_type}, {len(media_results)} items")
    
    return message

# ============================================================================
# STREAMING ENDPOINT
# ============================================================================

@login_required(login_url='login')
@csrf_exempt
@require_http_methods(["POST"])
def chat_api_send_streaming(request):
    """✅ FIXED: Streaming with media message persistence"""
    try:
        data = json.loads(request.body)
        limit = get_or_create_message_limit(request.user)
        
        if not limit.can_send_message():
            return JsonResponse({
                'error': 'Message limit reached',
                'message': f'You have no messages remaining. Please wait {limit.get_formatted_time_remaining()} to get another {limit.total_messages} messages.',
                'limit_reached': True,
                'time_remaining': limit.get_time_remaining()
            }, status=429)
        
        # ✅ DECREMENT MESSAGE COUNT
        limit.use_message()
        print(f"✓ Message used: {limit.messages_remaining}/{limit.total_messages} remaining")
        
        user_message = data.get('message', '').strip()

        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)

        user_message = ContentSafety.sanitize_input(user_message)
        conversation = get_active_conversation(request.user)
        ensure_initial_greeting(conversation, request.user)
        user_first_name = request.user.first_name if request.user.first_name else None
        
        is_developer = is_developer_account(request.user)
        developer_email = request.user.email if is_developer else None

        # Save user message first
        Message.objects.create(
            conversation=conversation,
            role='user',
            content=user_message
        )

        conversation_history, _ = get_conversation_history_with_limit(
            conversation, 
            max_tokens=24000
        )

        # ✅ CHECK FOR MEDIA REQUESTS FIRST
        from .media_service import MediaService
        
        # Detect media request patterns (DEFINE ONCE!)
        msg_lower = user_message.lower()
        
        video_patterns = [
            r'\b(give me|show me|find me|get me|can you (give|show|find|get))\s+.*\b(video|videos)\b',
            r'\b(video|videos)\s+(about|on|showing|for|regarding)\b',
            r'\b(recommend|suggest)\s+.*\bvideo\b',
            r'\bwatch.*video\b',
            r'show me (some |any )?videos?',
            r'find (me )?(some |any )?videos?',
            r'recommend (some |any )?videos?',
            r'\bvideo\s+(suggestion|recommendation)s?',
            r'\b(any|some)\s+videos?',
            r'\b(have|got|do you have|you got)\s+(any|some)?\s*videos?',
            r'\bvideos?\s+(that|which|to)\s+(could|can|would|might)',
        ]
        
        image_patterns = [
            r'\b(give me|show me|find me|get me|can you (give|show|find|get))\s+.*\b(image|images|picture|pictures|photo|photos)\b',
            r'\b(image|images|picture|pictures|photo|photos)\s+(of|about|showing)\b',
            r'show me (a |an |some )?((picture|image|photo)s?|pic)',
            r'find (me )?(a |an |some )?((picture|image|photo)s?|pic)',
        ]
        
        # Detect if this is a media request
        is_video_request = any(re.search(pattern, msg_lower) for pattern in video_patterns)
        is_image_request = any(re.search(pattern, msg_lower) for pattern in image_patterns)
#======================================================================================================
        has_media_request = is_video_request or is_image_request
        
        # ✅ IF MEDIA REQUEST DETECTED
        if has_media_request:
            media_type = 'video' if is_video_request else 'image'
            
            print(f"🎬 Media request detected: video={is_video_request}, image={is_image_request}")
            
            # Analyze context
            from .context_analyzer import ContextAnalyzer
            analyzer = ContextAnalyzer()
            context = analyzer.analyze_message(user_message, conversation_history)
            message_elements = context.message_elements
            
            has_greeting = (message_elements.get('has_greeting', False) or 
                            any(word in msg_lower[:20] for word in ['hi', 'hello', 'hey', 'hola', 'sup']))
            has_emotion = message_elements.get('has_emotion', False)
            has_problem = message_elements.get('has_problem', False)
            
            needs_llm_acknowledgment = has_greeting or has_emotion or has_problem
            
            print(f"📊 Other elements: greeting={has_greeting}, emotion={has_emotion}, problem={has_problem}")
            print(f"🧠 Needs LLM acknowledgment: {needs_llm_acknowledgment}")
            
            # ✅ CRITICAL FIX: Try LLM acknowledgment, but catch API failures
            intro_text = None
            llm_failed = False
            
            if needs_llm_acknowledgment:
                print("🧠 Complex message - generating empathetic acknowledgment")
                
                user_topic = extract_user_topic_from_message(user_message)
                
                ack_prompt = f"""User shared: "{user_message}"

Generate a brief (2-3 sentences) empathetic response that:
1. Acknowledges their greeting if present
2. Validates their feelings/struggles
3. Ends with transitioning to videos about {user_topic}

Keep it natural and supportive. End by mentioning you found videos about {user_topic}."""
                
                try:
                    llm_service = get_llm_service()
                    ack_response = llm_service.generate_response(
                        conversation_history=[{'role': 'user', 'content': ack_prompt}],
                        user_name=user_first_name,
                        time_context=None,
                        max_retries=1,
                        is_developer=is_developer,
                        developer_email=developer_email
                    )
                    
                    # ✅ CRITICAL CHECK: Is this an API failure fallback?
                    if ack_response and ('[[EMAIL:' in ack_response or '[[FEEDBACK:' in ack_response):
                        print("❌ LLM returned API failure fallback - aborting media response")
                        llm_failed = True
                    elif ack_response and len(ack_response) > 10:
                        intro_text = ack_response.strip()
                        if 'video' not in intro_text.lower():
                            intro_text += f" Here are some videos about {user_topic} that might help:"
                    else:
                        print("⚠️ LLM returned empty/short response - using fallback intro")
                        intro_text = f"I hear you. Here are some videos about {user_topic} that might help:"
                        
                except Exception as e:
                    print(f"⚠️ LLM acknowledgment failed: {e}")
                    llm_failed = True
            
            # ✅ CRITICAL: If LLM failed, return API failure fallback WITHOUT media
            if llm_failed or (needs_llm_acknowledgment and intro_text is None):
                print("❌ API failure detected - returning fallback message WITHOUT media")
                
                # Use API failure fallback
                fallback_msg = random.choice(API_FAILURE_FALLBACKS)
                
                # Save as regular message (NOT media message)
                Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=fallback_msg
                )
                
                # Return as regular JSON response (NOT media response)
                return JsonResponse({
                    'success': True,
                    'response': fallback_msg,
                    'is_media': False  # ✅ Important: NOT a media response
                })
            
            # ✅ Continue with normal media response only if LLM succeeded
            if intro_text is None:
                user_topic = extract_user_topic_from_message(user_message)
                intro_text = f"Here are some helpful {media_type}s about {user_topic}:"
            
            # Extract query and search for media
            query = extract_video_query_smart(user_message, is_video_request)
            print(f"📝 Extracted query: '{query}'")
            
            media_service = MediaService()
            media_results = media_service.search_media(query=query, media_type=media_type, count=3)
            
            if media_results.get('success') and media_results.get('results'):
                actual_results = media_results['results']
                print(f"✅ Found {len(actual_results)} {media_type}s for: {query}")
                
                # ✅ GENERATE RESPONSE (LLM first if complex message)
                full_response = ""
                
                    # ✅ FIXED: ACTUALLY CALL LLM FOR ACKNOWLEDGMENT
                if needs_llm_acknowledgment:
                    print("🧠 Complex message - generating empathetic acknowledgment")
                    
                    # ✅ CRITICAL: Extract ACTUAL topic from user's words
                    user_topic = extract_user_topic_from_message(user_message)
                    
                    # Build SHORT prompt for quick acknowledgment
                    ack_prompt = f"""User shared: "{user_message}"

Generate a brief (2-3 sentences) empathetic response that:
1. Acknowledges their greeting if present
2. Validates their feelings/struggles
3. Ends with transitioning to videos about {user_topic}

Keep it natural and supportive. End by mentioning you found videos about {user_topic}."""
                    
                    # Call LLM for acknowledgment
                    try:
                        llm_service = get_llm_service()
                        ack_response = llm_service.generate_response(
                            conversation_history=[{'role': 'user', 'content': ack_prompt}],
                            user_name=user_first_name,
                            time_context=None,
                            max_retries=1
                        )
                        
                        if ack_response and len(ack_response) > 10:
                            intro_text = ack_response.strip()
                            # ✅ CRITICAL: If LLM didn't mention videos, add it
                            if 'video' not in intro_text.lower():
                                intro_text += f" Here are some videos about {user_topic} that might help:"
                        else:
                            # Fallback if LLM fails
                            intro_text = f"I hear you - sounds like you're dealing with a lot. Here are some videos about {user_topic} that might help:"
                    except Exception as e:
                        print(f"⚠️ LLM acknowledgment failed: {e}")
                        intro_text = f"I hear you. Here are some videos about {user_topic} that might help:"
                else:
                    # SIMPLE MESSAGE: Just video request
                    user_topic = extract_user_topic_from_message(user_message)
                    intro_text = f"Here are some helpful {media_type}s about {user_topic}:"
                
                # ✅ FIXED: GENERATE PROPER OUTRO
                is_emotional = any(word in msg_lower for word in [
                    'struggling', 'stressed', 'anxious', 'worried', 'frustrated',
                    'overwhelmed', 'difficult', 'hard', 'problem', 'disaster'
                ])
                
                if is_emotional or has_problem:
                    outro = "I hope these videos give you some useful guidance. I'm here if you want to talk more about what you're going through."
                elif has_greeting:
                    outro = "Let me know if you'd like more recommendations, or if you want to chat about anything else!"
                else:
                    outro = "Feel free to ask if you need more specific recommendations!"
                
                # ✅ PREPARE MEDIA DATA (use camelCase for frontend!)
                if media_type == 'video':
                    media_data = {
                        'intro': intro_text,
                        'videos': [
                            {
                                'number': i + 1,
                                'videoId': result.get('video_id', ''),  # ✅ camelCase
                                'url': result.get('url', ''),
                                'title': result.get('title', 'Untitled Video'),
                                'description': result.get('description', ''),
                                'thumbnail': result.get('thumbnail', ''),
                                'channel': result.get('channel_title', 'Unknown Channel'),
                                'channel_title': result.get('channel_title', 'Unknown Channel'),
                                'channel_url': result.get('channel_url', ''),
                            }
                            for i, result in enumerate(actual_results)
                        ],
                        'outro': outro
                    }
                elif media_type == 'image':
                    media_data = {
                        'intro': intro_text,
                        'images': [
                            {
                                'url': result.get('url', ''),
                                'alt': result.get('alt', ''),
                                'photographer': result.get('photographer', ''),
                                'photographer_url': result.get('photographer_url', '')
                            }
                            for result in actual_results
                        ],
                        'outro': ''
                    }
                
                # ✅ SAVE MEDIA MESSAGE TO DATABASE
                media_msg = Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=full_response,
                    is_media_message=True,
                    media_type=media_type,
                    media_data=media_data
                )
                
                print(f"✅ Saved media message: {media_type}, {len(actual_results)} items")
                
                # ✅ UPDATE USER MEMORY
                try:
                    user_memory = UserMemory.objects.get(user=request.user)
                    
                    # Track media request in topics
                    if 'media_requests' not in user_memory.mentioned_topics:
                        user_memory.mentioned_topics['media_requests'] = []
                    
                    user_memory.mentioned_topics['media_requests'].append({
                        'query': query,
                        'type': media_type,
                        'count': len(actual_results),
                        'timestamp': timezone.now().isoformat()
                    })
                    
                    # Also add topic words to general topics
                    topic_words = query.split()
                    for word in topic_words:
                        if len(word) > 3:  # Skip short words
                            word_lower = word.lower()
                            if word_lower not in user_memory.mentioned_topics:
                                user_memory.mentioned_topics[word_lower] = 1
                            else:
                                user_memory.mentioned_topics[word_lower] += 1
                    
                    user_memory.save()
                    print(f"✅ Updated memory with media interaction: {query}")
                    
                except UserMemory.DoesNotExist:
                    print("⚠️ User memory not found - skipping memory update")
 #=====================================================================================================               
                # ✅ RETURN MEDIA RESPONSE TO FRONTEND
                return JsonResponse({
                    'success': True,
                    'is_media': True,
                    'media_type': media_type,
                    'media_data': media_data,
                    'message_id': media_msg.message_id
                })
            
            else:
                # No results found - let LLM respond naturally
                print(f"⚠️ No {media_type} results found for: {query}")
                # Fall through to normal LLM response below

        # ✅ CONTINUE WITH NORMAL LLM RESPONSE
        # (This runs if: no media request OR media search failed)
        is_safe, category, safety_response, needs_llm = ContentSafety.check_content(
            user_message,
            conversation_history
        )

        def response_generator():
            full_response = ""
            error_occurred = False
            
            try:
                if not is_safe and not needs_llm:
                    # Safety response
                    for word in safety_response.split():
                        chunk = word + " "
                        full_response += chunk
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                else:
                    llm_service = get_llm_service()
                    
                    from .timezone_utils import get_time_context
                    time_context = get_time_context('Asia/Manila')
                    
                    chunk_count = 0
                    for chunk in llm_service.generate_response_streaming(
                        conversation_history,
                        user_name=user_first_name,
                        time_context=time_context,
                        is_developer=is_developer,
                        developer_email=developer_email
                    ):
                        if chunk:
                            chunk_count += 1
                            full_response += chunk
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    
                    if chunk_count == 0:
                        error_occurred = True
                        print("⚠️ No response chunks received - using API_FAILURE_FALLBACKS")
                        
                        fallback_msg = random.choice(API_FAILURE_FALLBACKS)
                        print(f"✓ Streaming fallback: {fallback_msg[:50]}...")
                        
                        for word in fallback_msg.split():
                            chunk = word + " "
                            full_response += chunk
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        
                        try:
                            with transaction.atomic():
                                Message.objects.create(
                                    conversation=conversation,
                                    role='assistant',
                                    content=full_response
                                )
                                conversation.save()
                        except Exception as save_error:
                            print(f"⚠️ Failed to save fallback: {save_error}")
                
                if full_response and not error_occurred:
                    with transaction.atomic():
                        Message.objects.create(
                            conversation=conversation,
                            role='assistant',
                            content=full_response
                        )
                        conversation.save()
                        update_user_memory_after_conversation(request.user, conversation)
                
                yield f"data: {json.dumps({'done': True, 'full_response': full_response})}\n\n"
                
            except Exception as e:
                print(f"❌ Streaming error: {e}")
                import traceback
                traceback.print_exc()
                
                error_msg = random.choice(API_FAILURE_FALLBACKS)
                print(f"✓ Using API_FAILURE_FALLBACK: {error_msg[:50]}...")
                
                try:
                    with transaction.atomic():
                        Message.objects.create(
                            conversation=conversation,
                            role='assistant',
                            content=error_msg
                        )
                        conversation.save()
                except:
                    pass
                
                for word in error_msg.split():
                    chunk = word + " "
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                
                yield f"data: {json.dumps({'done': True, 'full_response': error_msg})}\n\n"

        return StreamingHttpResponse(
            response_generator(),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )

    except Exception as e:
        print(f"❌ Error in chat_api_send_streaming: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

# ============================================================================
# ✅ FIXED: SMART TOPIC DETECTION (NO MORE FALSE POSITIVES!)
# ============================================================================

def extract_topics_from_message(content: str) -> list:
    """
    Extract topics from message content using pattern-based detection.
    
    Uses word boundary matching to identify topic categories mentioned by the user.
    Returns list of detected topic strings for conversation analysis.
    
    Returns:
        list: Detected topic categories (e.g., ['school', 'friendship'])
    """
    content_lower = content.lower()
    topics = []
    
    # ====================================================================
    # SPIRITUALITY & RELIGION - Must have explicit religious context
    # ====================================================================
    religious_patterns = [
        r'\b(god|jesus|christ|holy|sacred|divine|prayer|pray|praying)\b',
        r'\b(church|chapel|mosque|temple|synagogue|cathedral)\b',
        r'\b(faith|belief|believe|religion|religious|spiritual|spirituality)\b',
        r'\b(bible|quran|koran|scripture|gospel|sermon)\b',
        r'\b(worship|worshipping|blessing|blessed|grace|salvation)\b',
        r'\b(christian|muslim|buddhist|hindu|catholic|protestant)\b',
    ]
    
    if any(re.search(pattern, content_lower) for pattern in religious_patterns):
        topics.append('spirituality')
    
    # ====================================================================
    # SCHOOL & EDUCATION
    # ====================================================================
    school_patterns = [
        r'\b(school|class|homework|assignment|exam|test)\b',
        r'\b(quiz|teacher|professor|study|student|college)\b',
        r'\b(university|grade|semester|course|lecture)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in school_patterns):
        topics.append('school')
    
    # ====================================================================
    # FRIENDSHIP & SOCIAL
    # ====================================================================
    friendship_patterns = [
        r'\b(friend|friends|classmate|classmates|peer|peers)\b',
        r'\b(bully|bullying|bullied|exclude|excluded|ignored|left out)\b',
        r'\b(hang out|hangout|meet up|party|gathering)\b',
    ]
    
    if any(re.search(pattern, content_lower) for pattern in friendship_patterns):
        topics.append('friendship')
    
    # ====================================================================
    # FAMILY
    # ====================================================================
    family_patterns = [
        r'\b(family|mom|dad|mother|father|parent|parents)\b',
        r'\b(sibling|brother|sister|aunt|uncle|grandma)\b',
        r'\b(grandpa|cousin|relative)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in family_patterns):
        topics.append('family')
    
    # ====================================================================
    # WORK & CAREER
    # ====================================================================
    work_patterns = [
        r'\b(work|job|boss|career|office|coworker)\b',
        r'\b(colleague|employee|workplace|interview|salary)\b',
        r'\b(promotion|manager)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in work_patterns):
        topics.append('work')
    
    # ====================================================================
    # RELATIONSHIPS & DATING
    # ====================================================================
    relationship_patterns = [
        r'\b(boyfriend|girlfriend|partner|dating|crush)\b',
        r'\b(love|romance|relationship|breakup|ex)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in relationship_patterns):
        topics.append('relationships')
    
    # ====================================================================
    # HOBBIES & ACTIVITIES
    # ====================================================================
    hobby_patterns = [
        r'\b(hobby|hobbies|interest|interests)\b',
        r'\b(game|gaming|play|sport|sports|exercise|workout)\b',
        r'\b(basketball|football|soccer|volleyball|tennis|boxing)\b',
        r'\b(running|swimming|cycling|gym|fitness)\b',
    ]
    
    if any(re.search(pattern, content_lower) for pattern in hobby_patterns):
        topics.append('hobbies')
    
    # ====================================================================
    # FOOD & COOKING - ✅ STRICT: Must have explicit food/cooking words
    # ====================================================================
    food_patterns = [
        r'\b(food|eat|eating|cook|cooking|recipe)\b',
        r'\b(restaurant|meal|lunch|dinner|breakfast|hungry)\b',
        r'\b(snack|diet|cuisine|dish)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in food_patterns):
        topics.append('food')
    
    # ====================================================================
    # ENTERTAINMENT (Music, Movies, Books)
    # ====================================================================
    entertainment_patterns = [
        r'\b(music|movie|film|show|series|tv|book)\b',
        r'\b(reading|novel|art|draw|paint|watch|listen)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in entertainment_patterns):
        topics.append('entertainment')
    
    # ====================================================================
    # FINANCES & MONEY
    # ====================================================================
    finance_patterns = [
        r'\b(money|financial|budget|spend|spending|save)\b',
        r'\b(saving|buy|buying|shopping|afford|cost|price)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in finance_patterns):
        topics.append('finances')
    
    # ====================================================================
    # HEALTH & WELLNESS
    # ====================================================================
    health_patterns = [
        r'\b(health|sick|illness|disease|doctor|hospital)\b',
        r'\b(clinic|medicine|medication|pain|injury)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in health_patterns):
        topics.append('health')
    
    # ====================================================================
    # BODY IMAGE & APPEARANCE
    # ====================================================================
    body_patterns = [
        r'\b(fat|skinny|thin|weight|body|stomach|appearance)\b',
        r'\b(ugly|beautiful|pretty|handsome|insecure|self-conscious)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in body_patterns):
        topics.append('body image')
    
    # ====================================================================
    # FUTURE PLANS & GOALS
    # ====================================================================
    future_patterns = [
        r'\b(future|plan|planning|goal|dream|aspiration)\b',
        r'\b(hope|wish|ambition)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in future_patterns):
        topics.append('future plans')
    
    # ====================================================================
    # TECHNOLOGY
    # ====================================================================
    tech_patterns = [
        r'\b(phone|computer|laptop|tablet|ipad|device)\b',
        r'\b(internet|wifi|online|app|website|software|hardware)\b',
    ]
    
    if any(re.search(pattern, content_lower) for pattern in tech_patterns):
        topics.append('technology')
    
    # ====================================================================
    # SOCIAL MEDIA - ✅ STRICT: Must have platform name OR explicit action
    # ====================================================================
    social_media_platforms = [
        r'\b(instagram|facebook|twitter|tiktok|snapchat)\b',
        r'\b(youtube|reddit|discord|whatsapp|telegram)\b',
    ]
    
    social_media_actions = [
        r'\b(posting|post on|shared on)\b',
        r'\b(followers?|following)\b',
        r'\b(dm|dms|direct message)\b',
        r'\bstory\b.*(instagram|snapchat|facebook)',
        r'\bsocial media\b',
    ]
    
    has_platform = any(re.search(p, content_lower) for p in social_media_platforms)
    has_action = any(re.search(p, content_lower) for p in social_media_actions)
    
    if has_platform or has_action:
        topics.append('social media')
    
    # ====================================================================
    # PETS & ANIMALS
    # ====================================================================
    pet_patterns = [
        r'\b(pet|dog|cat|puppy|kitten|animal|bird|fish)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in pet_patterns):
        topics.append('pets')
    
    # ====================================================================
    # WEATHER - ✅ STRICT: Must have explicit weather words
    # ====================================================================
    weather_patterns = [
        r'\b(weather|rain|raining|rainy|sunny|cloudy|hot|cold|storm|snow)\b',
        r'\b(temperature|forecast|humid|dry)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in weather_patterns):
        topics.append('weather')
    
    # ====================================================================
    # SLEEP & REST
    # ====================================================================
    sleep_patterns = [
        r'\b(sleep|sleeping|sleepy|tired|exhausted|nap)\b',
        r'\b(rest|insomnia)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in sleep_patterns):
        topics.append('sleep')
    
    # ====================================================================
    # MENTAL HEALTH (explicit context only)
    # ====================================================================
    mental_health_patterns = [
        r'\b(therapy|therapist|counseling|counselor|psychologist)\b',
        r'\b(psychiatrist|antidepressant|medication)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in mental_health_patterns):
        topics.append('mental health')
    
    # ====================================================================
    # HOME LIFE
    # ====================================================================
    home_patterns = [
        r'\b(room|house|home|apartment|bedroom|clean)\b',
        r'\b(messy|organize)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in home_patterns):
        topics.append('home life')
    
    # ====================================================================
    # STRESS & PRESSURE
    # ====================================================================
    stress_patterns = [
        r'\b(pressure|stress|stressed|overwhelm|overwhelmed|busy)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in stress_patterns):
        topics.append('stress')
    
    # ====================================================================
    # LONELINESS & ISOLATION
    # ====================================================================
    loneliness_patterns = [
        r'\b(lonely|alone|isolation|isolated|nobody|no one)\b',
    ]
    if any(re.search(pattern, content_lower) for pattern in loneliness_patterns):
        topics.append('loneliness')
    
    # Remove duplicates
    return list(set(topics))


def extract_emotions_from_message(content: str) -> list:
    """Extract emotions from message"""
    content_lower = content.lower()
    emotions = []
    
    if any(word in content_lower for word in [
        'sad', 'depressed', 'down', 'unhappy', 'miserable', 'hopeless'
    ]):
        emotions.append('sadness')
    
    if any(word in content_lower for word in [
        'anxious', 'worried', 'stress', 'stressed', 'nervous', 'panic', 'overwhelmed'
    ]):
        emotions.append('anxiety')
    
    if any(word in content_lower for word in [
        'angry', 'mad', 'frustrated', 'annoyed', 'furious', 'irritated'
    ]):
        emotions.append('anger')
    
    if any(word in content_lower for word in [
        'embarrass', 'ashamed', 'shame', 'humiliat', 'awkward', 'self-conscious'
    ]):
        emotions.append('embarrassment')
    
    if any(word in content_lower for word in [
        'happy', 'excited', 'good', 'great', 'wonderful', 'joy', 'glad'
    ]):
        emotions.append('happiness')
    
    if any(word in content_lower for word in [
        'problem', 'issue', 'trouble', 'difficult', 'hard', 'struggle'
    ]):
        emotions.append('challenges')
    
    return list(set(emotions))

def extract_semantic_title_from_message(content: str, max_length: int = 40) -> str:
    """
    Extract meaningful conversation title from user message content.
    
    Extraction strategy:
    1. Identify primary subject matter using pattern matching
    2. Extract action verbs and emotional indicators
    3. Construct concise title from most relevant elements
    4. Apply length constraints and formatting
    
    Args:
        content: User message text to analyze
        max_length: Maximum character length for title (default: 40)
    
    Returns:
        str: Formatted title string or "New Chat" if extraction fails
    """
    import re
    
    if not content or len(content.strip()) < 3:
        return "New Chat"
    
    content = content.strip()
    content_lower = content.lower()
    
    # ====================================================================
    # STEP 1: Extract key phrases using NLP-like patterns
    # ====================================================================
    
    key_phrases = []
    
    # Pattern 1: "I'm/I am [feeling/doing] [something]"
    feeling_patterns = [
        r"i'?m (feeling|having|experiencing|dealing with|struggling with|working on|learning|studying|playing) (.+?)(?:\.|,|$)",
        r"i (feel|have|am|struggle with|deal with|work on|love|hate|like|enjoy) (.+?)(?:\.|,|$)",
    ]
    
    for pattern in feeling_patterns:
        match = re.search(pattern, content_lower)
        if match:
            verb = match.group(1)
            subject = match.group(2).strip()
            # Take first 4 words max
            subject_words = subject.split()[:4]
            subject = ' '.join(subject_words)
            key_phrases.append(f"{verb} {subject}")
            break
    
    # Pattern 2: "[Someone] is [doing something]"
    someone_patterns = [
        r"(my |our |their |his |her )?(friend|mom|dad|parent|teacher|classmate|partner|sibling) (?:is|are|was|were) (.+?)(?:\.|,|$)",
        r"(people|everyone|they|someone) (?:is|are|was|were) (.+?)(?:\.|,|$)",
    ]
    
    for pattern in someone_patterns:
        match = re.search(pattern, content_lower)
        if match:
            groups = match.groups()
            if len(groups) >= 3:
                possessive = groups[0] or ""
                person = groups[1]
                action = groups[2].strip()
                action_words = action.split()[:3]
                action = ' '.join(action_words)
                key_phrases.append(f"{possessive}{person} {action}")
                break
    
    # Pattern 3: Topic + emotion words
    emotion_words = ['lonely', 'sad', 'happy', 'anxious', 'worried', 'excited', 
                    'frustrated', 'angry', 'scared', 'depressed', 'stressed']
    
    topic_words = ['school', 'work', 'family', 'friend', 'relationship', 'health',
                  'career', 'future', 'life', 'body', 'self', 'confidence']
    
    for topic in topic_words:
        if topic in content_lower:
            for emotion in emotion_words:
                if emotion in content_lower:
                    key_phrases.append(f"{emotion} about {topic}")
                    break
    
    # Pattern 4: Questions about self
    question_patterns = [
        r"(?:why|how) (?:am i|do i|can i) (.+?)\?",
        r"what (?:should i|can i|do i) (.+?)\?",
    ]
    
    for pattern in question_patterns:
        match = re.search(pattern, content_lower)
        if match:
            question_subject = match.group(1).strip()
            question_words = question_subject.split()[:4]
            question_subject = ' '.join(question_words)
            key_phrases.append(f"Question: {question_subject}")
            break
    
    # ====================================================================
    # STEP 2: If no patterns matched, extract most important words
    # ====================================================================
    
    if not key_phrases:
        # Extract nouns and adjectives (words 3+ chars, not common stop words)
        stop_words = {
            'the', 'is', 'am', 'are', 'was', 'were', 'been', 'being', 'have', 'has', 
            'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 
            'might', 'must', 'can', 'about', 'into', 'through', 'during', 'before', 
            'after', 'above', 'below', 'from', 'here', 'there', 'when', 'where', 
            'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 
            'some', 'such', 'only', 'own', 'same', 'than', 'too', 'very', 'just',
            'now', 'then', 'once', 'also', 'well', 'even', 'still', 'yet', 'hello',
            'hey', 'hi', 'hola', 'good', 'evening', 'morning', 'afternoon', 'night',
            'today', 'tonight', 'kind', 'like', 'felt', 'feel', 'little', 'lot',
            'something', 'anything', 'nothing', 'everything'
        }
        
        words = content.split()
        important_words = []
        
        for word in words[:20]:  # Only check first 20 words
            cleaned = re.sub(r'[^\w\s]', '', word.lower())
            if (len(cleaned) >= 3 and 
                cleaned not in stop_words and 
                not cleaned.isdigit()):
                important_words.append(word.capitalize())
            
            if len(important_words) >= 5:  # Max 5 words
                break
        
        if important_words:
            key_phrases.append(' '.join(important_words))
    
    # ====================================================================
    # STEP 3: Build title from best phrase
    # ====================================================================
    
    if key_phrases:
        title = key_phrases[0]
        
        # Capitalize first letter
        if title:
            title = title[0].upper() + title[1:]
        
        # Truncate if too long
        if len(title) > max_length:
            title = title[:max_length-3] + "..."
        
        return title
    
    # ====================================================================
    # STEP 4: Final fallback - use first few words
    # ====================================================================
    
    words = content.split()[:6]
    title = ' '.join(words)
    
    if len(title) > max_length:
        title = title[:max_length-3] + "..."
    
    return title if title else "New Chat"


# ============================================================================
# ✅ IMPROVED: TITLE GENERATION WITH SMART TOPIC DETECTION
# ============================================================================

@login_required(login_url='login')
@require_http_methods(["POST"])
def generate_title(request):
    """Generate an AI title for the conversation"""
    try:
        conversation = Conversation.objects.filter(
            user=request.user,
            is_active=True
        ).first()
        
        if not conversation:
            title = f"Conversation - {datetime.now().strftime('%b %d, %Y')}"
            return JsonResponse({'success': True, 'title': title})
        
        first_message = conversation.messages.order_by('timestamp').first()
        conversation_date = first_message.timestamp if first_message else datetime.now()
        date_str = conversation_date.strftime('%b %d, %Y')
        
        user_messages = conversation.messages.filter(role='user').order_by('timestamp')
        
        if not user_messages.exists():
            title = f"New Chat - {date_str}"
            return JsonResponse({'success': True, 'title': title})

        # Get topics and emotions
        topics = []
        emotions = []
        
        for msg in user_messages[:10]:
            msg_topics = extract_topics_from_message(msg.content)
            topics.extend(msg_topics)
            
            msg_emotions = extract_emotions_from_message(msg.content)
            emotions.extend(msg_emotions)
        
        topics = list(dict.fromkeys(topics))
        emotions = list(dict.fromkeys(emotions))
        
        # Build conversation summary
        conversation_summary = ""
        for msg in user_messages[:10]:
            conversation_summary += f"User: {msg.content}\n"
        
        # ✅ TRY LLM TITLE GENERATION
        try:
            from .services import LLMService
            llm_service = get_llm_service()
            
            detected_topics_str = ', '.join(topics) if topics else 'general conversation'
            
            title_prompt = f"""Based on this conversation, generate a creative, emotionally resonant title (maximum 50 characters).

**DETECTED TOPICS (YOU MUST ONLY USE THESE):** {detected_topics_str}

**STRICT RULES:**
1. ONLY use topics from the detected list above - DO NOT invent or assume topics
2. If no topics detected, use generic phrases for general conversation themes
3. Capture the emotional core through topic treatment, not just topic listing
4. Maintain concise, journal-entry style formatting
5. Avoid formulaic or repetitive phrasing patterns

**TITLE STRUCTURE PRINCIPLES:**
- Begin with emotional state or action when appropriate
- Reference specific topics from detected list
- Use metaphorical language sparingly for impact
- Keep length under 50 characters total

Conversation:
{conversation_summary}

Generate ONLY the title (no quotes, no explanation):"""

            conversation_for_api = [
                {'role': 'user', 'content': title_prompt}
            ]

            llm_title = llm_service.generate_response(
                conversation_history=conversation_for_api,
                user_name=None,
                time_context=None,
                max_retries=1
            )

            # ✅ Detect API failure messages
            if llm_title and ('[[EMAIL:' in llm_title or '[[FEEDBACK:' in llm_title):
                print("⚠️ API failure detected - using hardcoded fallback")
                raise ValueError("API failure response")

            if llm_title:
                llm_title = llm_title.replace('"', '').replace("'", '').strip()
        
                # Validate title doesn't hallucinate topics
                title_lower = llm_title.lower()
                all_known_topics = [
                    'spirituality', 'school', 'friendship', 'family', 'work', 
                    'relationships', 'hobbies', 'food', 'entertainment', 'finances',
                    'health', 'body image', 'future plans', 'technology', 'social media',
                    'pets', 'weather', 'sleep', 'mental health', 'home life', 
                    'stress', 'loneliness'
                ]
        
                detected_topics_lower = [t.lower() for t in topics]
                for known_topic in all_known_topics:
                    if known_topic in title_lower and known_topic not in detected_topics_lower:
                        print(f"⚠️ LLM hallucinated topic '{known_topic}' - using fallback")
                        raise ValueError(f"Title mentions undetected topic: {known_topic}")
        
                if len(llm_title) > 55:
                    llm_title = llm_title[:52] + "..."
        
                title = f"{llm_title} - {date_str}"
                return JsonResponse({'success': True, 'title': title})
            
        except Exception as llm_error:
            print(f"⚠️ LLM title generation failed: {str(llm_error)}")
        
        # ====================================================================
        # ✅ HARDCODED FALLBACK TITLES (5 options)
        # ====================================================================
        import time
        time.sleep(2)  # 2-second UX delay
        
        user_first_name = request.user.first_name if request.user.first_name else None
        first_user_msg = user_messages.first()
        
        fallback_titles = []
        
        # 1. Conversation
        fallback_titles.append(f"Conversation - {date_str}")
        
        # 2. (User's Name) & Snowfriend
        if user_first_name:
            fallback_titles.append(f"{user_first_name} & Snowfriend - {date_str}")
        
        # 3. First message from user (natural words, no ellipsis)
        if first_user_msg:
            first_content = first_user_msg.content.strip()
            
            bot_phrases = ["i'm snowfriend", "i'm here to listen", "you can share"]
            is_bot_phrase = any(phrase in first_content.lower() for phrase in bot_phrases)
            
            if not is_bot_phrase and len(first_content) >= 10:
                words = first_content.split()
                natural_length = min(7, len(words))
                title_words = words[:natural_length]
                
                if title_words:
                    title_words[-1] = title_words[-1].rstrip('.,!?;:')
                
                first_msg_title = ' '.join(title_words)
                
                if len(first_msg_title) >= 10:
                    fallback_titles.append(f"{first_msg_title} - {date_str}")
        
        # 4. Talking with Snowfriend
        fallback_titles.append(f"Talking with Snowfriend - {date_str}")
        
        # 5. Companionship variations
        companionship_options = [
            "A Moment of Connection",
            "Heart to Heart", 
            "Friendly Chat",
            "Sharing Thoughts",
            "Safe Space"
        ]
        fallback_titles.append(f"{random.choice(companionship_options)} - {date_str}")
        
        # Pick random fallback
        title = random.choice(fallback_titles)
        
        print(f"✓ Using hardcoded fallback title: {title}")
        return JsonResponse({'success': True, 'title': title})
        
    except Exception as e:
        print(f"⚠️ Error generating title: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Absolute final fallback
        import time
        time.sleep(2)
        title = f"Conversation - {datetime.now().strftime('%b %d, %Y')}"
        return JsonResponse({'success': True, 'title': title})

# ============================================================================
# EXPORT CONVERSATION
# ============================================================================

@login_required(login_url='login')
@require_http_methods(["POST"])
def export_conversation(request):
    """Export conversation as text file"""
    try:
        data = json.loads(request.body)
        title = data.get('title', 'Snowfriend Conversation')
        messages = data.get('messages', [])
        
        if not messages:
            return JsonResponse({
                'success': False,
                'error': 'No messages to export'
            }, status=400)
        
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:100]
        
        text_content = f"{'='*60}\n"
        text_content += f"Snowfriend Conversation Export\n"
        text_content += f"{'='*60}\n\n"
        text_content += f"Title: {title}\n"
        text_content += f"User: {request.user.username}\n"
        text_content += f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        text_content += f"Total Messages: {len(messages)}\n"
        text_content += f"\n{'='*60}\n\n"
        
        for i, msg in enumerate(messages, 1):
            sender = msg.get('sender', 'Unknown')
            content = msg.get('content', '').strip()
            timestamp = msg.get('formattedTime', 'No timestamp')
            
            text_content += f"Message {i} - {sender}\n"
            text_content += f"Time: {timestamp}\n"
            text_content += f"{'-'*60}\n"
            text_content += f"{content}\n"
            text_content += f"\n{'='*60}\n\n"
        
        text_content += f"\n\n--- End of Conversation ---\n"
        text_content += f"Exported from Snowfriend © 2025\n"
        
        response = HttpResponse(text_content, content_type='text/plain; charset=utf-8')
        filename = f"{safe_title.replace(' ', '_')}.txt"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        print(f"⚠️ Error exporting conversation: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Export failed: {str(e)}'
        }, status=500)


# ============================================================================
# LLM SERVICE SINGLETON
# ============================================================================

_llm_service = None

def get_llm_service():
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


# ============================================================================
# CONVERSATION MANAGEMENT
# ============================================================================

def get_active_conversation(user):
    try:
        conversation = Conversation.objects.filter(
            user=user,
            is_active=True
        ).first()
        
        if conversation:
            active_count = Conversation.objects.filter(
                user=user,
                is_active=True
            ).count()
            
            if active_count > 1:
                active_conversations = Conversation.objects.filter(
                    user=user,
                    is_active=True
                ).order_by('-updated_at')
                
                with transaction.atomic():
                    for conv in active_conversations[1:]:
                        conv.is_active = False
                        conv.save()
                
                conversation = active_conversations.first()
                print(f"⚠️ Fixed {active_count-1} duplicate active conversations for {user.username}")
            
            return conversation
        else:
            conversation = Conversation.objects.create(user=user, is_active=True)
            return conversation
            
    except Exception as e:
        print(f"⚠️ Error getting active conversation: {str(e)}")
        return Conversation.objects.create(user=user, is_active=True)


# ============================================================================
# TOKEN COUNTING & MEMORY
# ============================================================================

def count_tokens(text):
    if not text:
        return 0
    return max(1, len(text) // 4)


def get_conversation_history_with_limit(conversation, max_tokens=24000):
    all_messages = conversation.messages.only('role', 'content').order_by('timestamp')
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
            selected_messages.append({
                'role': msg.role,
                'content': msg.content
            })
            total_tokens += msg_tokens
        else:
            was_truncated = True
            break
    
    selected_messages.reverse()
    return selected_messages, was_truncated

# ============================================================================
# ✅ UPDATED: INITIALIZATION WITH DYNAMIC GREETING
# ============================================================================

def ensure_initial_greeting(conversation, user):
    """Create initial greeting message if conversation is empty"""
    if conversation.messages.count() == 0:
        # ✅ Get user memory to generate dynamic greeting
        user_memory = get_or_create_user_memory(user)
        initial_greeting = generate_initial_greeting(user, user_memory)
        
        Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=initial_greeting
        )
        
        print(f"✓ Created dynamic initial greeting for {user.username} ({user_memory.get_days_since_first_conversation()} days)")


# ============================================================================
# VIEW FUNCTIONS
# ============================================================================

@login_required(login_url='login')
@require_http_methods(["POST"])
@login_required(login_url='login')
@require_http_methods(["POST"])
def send_message(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({
                'success': False,
                'error': 'Message cannot be empty'
            }, status=400)
        
        user_message = ContentSafety.sanitize_input(user_message)
        conversation = get_active_conversation(request.user)
        ensure_initial_greeting(conversation, request.user)
        user_first_name = request.user.first_name if request.user.first_name else None
        
        is_developer = is_developer_account(request.user)
        developer_email = request.user.email if is_developer else None
        
        conversation_history, _ = get_conversation_history_with_limit(
            conversation, 
            max_tokens=24000
        )
        
        is_safe, category, safety_response, needs_llm = ContentSafety.check_content(
            user_message,
            conversation_history
        )
        
        user_msg = Message.objects.create(
            conversation=conversation,
            role='user',
            content=user_message,
            is_flagged=not is_safe,
            flagged_reason=category if not is_safe else None
        )
        
        if not is_safe and not needs_llm:
            bot_response = safety_response
            truncation_occurred = False

            import logging
            logger = logging.getLogger('snowfriend.crisis')
            logger.warning(f"CRISIS DETECTED - User: {request.user.username}, Category: {category}, Message: {user_message[:100]}")
        else:
            try:
                llm_service = get_llm_service()
                
                conversation_history, truncation_occurred = get_conversation_history_with_limit(
                    conversation, 
                    max_tokens=24000
                )
                
                from .timezone_utils import get_time_context
                time_context = get_time_context('Asia/Manila')
                
                bot_response = llm_service.generate_response(
                    conversation_history,
                    user_name=user_first_name,
                    time_context=time_context,
                    is_developer=is_developer,
                    developer_email=developer_email
                )
                
                if bot_response is None:
                    bot_response = random.choice(API_FAILURE_FALLBACKS)
                    print("⚠️ LLM returned None - using API_FAILURE_FALLBACKS")
                    
            except Exception as api_error:
                print(f"⚠️ API Error: {str(api_error)} - using API_FAILURE_FALLBACKS")
                bot_response = random.choice(API_FAILURE_FALLBACKS)
                truncation_occurred = False
        
        with transaction.atomic():
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=bot_response
            )
            conversation.save()
            update_user_memory_after_conversation(request.user, conversation)
        
        response_data = {
            'success': True,
            'response': bot_response
        }
        
        if truncation_occurred:
            response_data['notification'] = {
                'message': 'Some earlier messages have been removed to continue our conversation smoothly.',
                'type': 'info'
            }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    
    except Exception as e:
        print(f"✗ Error in send_message: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': True,
            'response': random.choice(API_FAILURE_FALLBACKS)
        })

@login_required(login_url='login')
@require_http_methods(["GET"])
def get_conversation_history(request):
    """✅ UPDATED: Load conversation history with media message support"""
    try:
        conversation = Conversation.objects.filter(
            user=request.user,
            is_active=True
        ).only('conversation_id').first()
        
        if not conversation:
            return JsonResponse({
                'success': True,
                'messages': []
            })
        
        ensure_initial_greeting(conversation, request.user)
        messages = conversation.messages.only(
            'role', 'content', 'timestamp', 
            'is_media_message', 'media_type', 'media_data'
        ).all()
        
        messages_data = []
        for msg in messages:
            message_obj = {
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
            }
            
            # ✅ Include media data if present
            if msg.is_media_message:
                message_obj['is_media_message'] = True
                message_obj['media_type'] = msg.media_type
                message_obj['media_data'] = msg.media_data
            
            messages_data.append(message_obj)
        
        return JsonResponse({
            'success': True,
            'messages': messages_data
        })
        
    except Exception as e:
        print(f"✗ Error in get_conversation_history: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Could not retrieve conversation history'
        }, status=500)

@login_required(login_url='login')
@require_http_methods(["POST"])
def clear_conversation(request):
    try:
        conversations = Conversation.objects.filter(user=request.user)
        count = conversations.count()
        
        if count > 0:
            conversations.delete()
            print(f"✓ Permanently deleted {count} conversation(s) for user: {request.user.username}")
            
            return JsonResponse({
                'success': True,
                'message': f'All {count} conversation(s) permanently deleted',
                'cleared': True
            })
        else:
            return JsonResponse({
                'success': True,
                'message': 'No conversations to clear',
                'cleared': False
            })
        
    except Exception as e:
        print(f"✗ Error in clear_conversation: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Could not clear conversation'
        }, status=500)


@login_required(login_url='login')
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
            print(f"✓ Permanently deleted UserMemory for {request.user.username}")
        except UserMemory.DoesNotExist:
            memory_deleted = False
            print(f"⚠️ No UserMemory found for {request.user.username}")
        
        print(f"✓ Permanently deleted {conv_count} conversation(s) for user: {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': f'All {conv_count} conversation(s) and memory permanently deleted',
            'cleared': True,
            'memory_deleted': memory_deleted
        })
        
    except Exception as e:
        print(f"✗ Error in clear_conversation_and_memory: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Could not clear conversation and memory'
        }, status=500)


@login_required(login_url='login')
@require_http_methods(["GET"])
def get_user_memory_summary(request):
    try:
        user_memory = get_or_create_user_memory(request.user)
        
        summary = {
            'total_conversations': user_memory.total_conversations,
            'total_messages': user_memory.total_messages,
            'top_topics': user_memory.get_top_topics(5),
            'mentioned_people': list(user_memory.mentioned_people.keys())[:5],
            'common_emotions': dict(sorted(
                user_memory.common_emotions.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]),
            'last_topics': user_memory.last_topics_discussed[:5],
            'memory_summary': user_memory.get_memory_summary()
        }
        
        return JsonResponse({
            'success': True,
            'memory': summary
        })
        
    except Exception as e:
        print(f"✗ Error getting user memory: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Could not retrieve user memory'
        }, status=500)


@login_required(login_url='login')
@require_http_methods(["GET"])
def get_message_limit(request):
    """Get current message limit status"""
    try:
        limit = get_or_create_message_limit(request.user)
        
        # Check for notifications
        notifications = []
        
        if limit.should_notify_half():
            notifications.append({
                'type': 'half',
                'message': f"You've used half your messages! {limit.messages_remaining} remaining."
            })
            limit.mark_notified('half')
        
        if limit.should_notify_three():
            notifications.append({
                'type': 'three',
                'message': 'Only 3 messages left! Use them wisely.'
            })
            limit.mark_notified('three')
        
        if limit.should_notify_zero():
            notifications.append({
                'type': 'zero',
                'message': "No messages remaining."
            })
            limit.mark_notified('zero')
        
        return JsonResponse({
            'success': True,
            'total_messages': limit.total_messages,
            'messages_remaining': limit.messages_remaining,
            'can_send': limit.can_send_message(),
            'time_remaining_seconds': limit.get_time_remaining(),
            'time_remaining_formatted': limit.get_formatted_time_remaining(),
            'reset_time': limit.reset_time.isoformat(),
            'notifications': notifications
        })
    
    except Exception as e:
        print(f"❌ Error getting message limit: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
# ============================================================================
# MEDIA SEARCH ENDPOINT
# ============================================================================

from .media_service import MediaService

@login_required(login_url='login')
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
        query = data.get('query', '').strip()
        media_type = data.get('media_type', 'video')
        count = data.get('count', 3)
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query is required'
            }, status=400)
        
        # 🚨 STRICT LIMIT: Force maximum of 3 results, minimum of 1
        # Even if user requests 10 or 100, we only send 3 max
        count = max(1, min(count, 3))
        
        print(f"📺 Media search: query='{query}', type={media_type}, count={count}")
        
        # Initialize media service
        media_service = MediaService()
        
        # Search media with enforced limit
        result = media_service.search_media(
            query=query,
            media_type=media_type,
            count=count
        )
        
        # 🚨 DOUBLE-CHECK: Ensure we never return more than 3
        if result.get('success') and result.get('results'):
            if len(result['results']) > 3:
                print(f"⚠️ WARNING: Got {len(result['results'])} results, truncating to 3")
                result['results'] = result['results'][:3]
                result['count'] = 3
        
        return JsonResponse(result)
    
    except Exception as e:
        print(f"❌ Error in search_media_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)