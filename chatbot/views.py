# views.py - UPDATED WITH DYNAMIC GREETINGS AND DATE TRACKING
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
    ✅ NEW: Generate dynamic greeting based on user's conversation history
    
    Returns different greetings based on how many days the user has been using Snowfriend
    """
    user_first_name = user.first_name if user.first_name else 'there'
    days_since_first = user_memory.get_days_since_first_conversation()
    
    # First time user (0 days)
    if days_since_first == 0:
        return (
            f"Hi {user_first_name}! I'm Snowfriend. You can share your thoughts "
            f"here at your own pace. I'm here to listen and help you reflect.\n\n"
        )
    
    # 1 day
    elif days_since_first == 1:
        return (
            f"Hi {user_first_name}, welcome back! It's been a day since we last talked. "
            f"I'm still here to listen whenever you need.\n\n"
        )
    
    # 2-3 days
    elif 2 <= days_since_first <= 3:
        return (
            f"Hi {user_first_name}, welcome back! Looks like we've been talking for "
            f"{days_since_first} days now. I'm still here to listen and help you reflect.\n\n"
        )
    
    # 4-6 days
    elif 4 <= days_since_first <= 6:
        return (
            f"Hi {user_first_name}, great to see you again! We've been connecting for "
            f"about {days_since_first} days. I'm here whenever you need to talk.\n\n"
        )
    
    # 7+ days
    else:
        return (
            f"Hi {user_first_name}, it's been over a week! We've been talking for "
            f"{days_since_first} days now. I'm always here when you need me.\n\n"
        )


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

# ============================================================================
# STREAMING ENDPOINT
# ============================================================================

@login_required(login_url='login')
@csrf_exempt
@require_http_methods(["POST"])
def chat_api_send_streaming(request):
    """✅ FIXED: Streaming with proper timeout fallback"""
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
        # END OF ADDITION
        
        user_message = data.get('message', '').strip()

        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)

        user_message = ContentSafety.sanitize_input(user_message)
        conversation = get_active_conversation(request.user)
        ensure_initial_greeting(conversation, request.user)
        user_first_name = request.user.first_name if request.user.first_name else None

        conversation_history, _ = get_conversation_history_with_limit(
            conversation, 
            max_tokens=24000
        )

        is_safe, category, safety_response, needs_llm = ContentSafety.check_content(
            user_message,
            conversation_history
        )

        Message.objects.create(
            conversation=conversation,
            role='user',
            content=user_message,
            is_flagged=not is_safe,
            flagged_reason=category if not is_safe else None
        )

        conversation_history, _ = get_conversation_history_with_limit(
            conversation, 
            max_tokens=24000
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
                    
                    # ✅ CRITICAL FIX: Properly handle timeout fallbacks
                    chunk_count = 0
                    for chunk in llm_service.generate_response_streaming(
                        conversation_history,
                        user_name=user_first_name,
                        time_context=time_context
                    ):
                        if chunk:
                            chunk_count += 1
                            full_response += chunk
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    
                    # ✅ If no chunks received, it means timeout occurred
                    if chunk_count == 0:
                        error_occurred = True
                        print("⚠️ No response chunks received - using fallback")
                
                # ✅ Save response if we got one
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
                
                # ✅ Generate contextual fallback
                error_msg = "I'm taking a moment to process that. Could you try sending your message again?"
                
                # Try to save fallback
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
                
                # ✅ Stream fallback word by word
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
        print(f"❌ Error in chat_api_send_streaming: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

# ============================================================================
# ✅ FIXED: SMART TOPIC DETECTION (NO MORE FALSE POSITIVES!)
# ============================================================================

def extract_topics_from_message(content: str) -> list:
    """
    ✅ ULTRA-FIXED: Context-aware topic extraction with STRICT word boundaries
    No more false positives - only detects topics user ACTUALLY mentioned
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
    ✅ UNIVERSAL: Extract meaningful title from any user message
    
    Strategy:
    1. Find the main subject/topic (nouns and noun phrases)
    2. Extract key verbs related to actions
    3. Identify emotional words
    4. Build concise title from most relevant elements
    
    Examples:
        "I'm struggling with my IT competence" → "Struggling with IT Competence"
        "My friend is being mean to me" → "Friend Being Mean"
        "I love playing basketball" → "Playing Basketball"
        "Feeling lonely tonight" → "Feeling Lonely"
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
    """Generate an AI title for the conversation - ULTRA-FIXED VERSION"""
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

        topics = []
        emotions = []
        
        for msg in user_messages[:10]:
            msg_topics = extract_topics_from_message(msg.content)
            topics.extend(msg_topics)
            
            msg_emotions = extract_emotions_from_message(msg.content)
            emotions.extend(msg_emotions)
        
        # Remove duplicates and keep order
        topics = list(dict.fromkeys(topics))
        emotions = list(dict.fromkeys(emotions))
        
        # Build conversation summary for LLM
        conversation_summary = ""
        for msg in user_messages[:10]:
            conversation_summary += f"User: {msg.content}\n"
        
        # ✅ IMPROVED: Better LLM title generation with STRICT validation
        try:
            from .services import LLMService
            llm_service = get_llm_service()
            
            # ✅ CRITICAL: Tell LLM the EXACT topics detected
            detected_topics_str = ', '.join(topics) if topics else 'general conversation'
            
            title_prompt = f"""Based on this conversation, generate a creative, emotionally resonant title (maximum 50 characters).

**DETECTED TOPICS (YOU MUST ONLY USE THESE):** {detected_topics_str}

**STRICT RULES:**
1. ONLY use topics from the detected list above - DO NOT invent or assume topics
2. If no topics detected, use generic phrases like "Sharing thoughts", "Opening up", "Casual chat"
3. Capture the EMOTIONAL CORE, not just topics
4. Be poetic but concise
5. Avoid generic phrases
6. Think like a journal entry title

Conversation:
{conversation_summary}

Examples of GOOD titles:
  * "Wrestling with change"
  * "Finding light in dark moments"  
  * "The weight of expectations"
  * "Searching for belonging"
  * "When words fail me"
  * "Faith as my anchor"
  * "Learning to let go"

Generate ONLY the title (no quotes, no explanation):"""

            # ✅ Use multi-model generation with short conversation
            conversation_for_api = [
                {'role': 'user', 'content': title_prompt}
            ]

            llm_title = llm_service.generate_response(
                conversation_history=conversation_for_api,
                user_name=None,
                time_context=None,
                max_retries=1
            )  
            if llm_title:
                llm_title = llm_title.replace('"', '').replace("'", '').strip()
                
                # ✅ VALIDATION: Ensure title doesn't mention topics not in detected list
                title_lower = llm_title.lower()
                all_known_topics = [
                    'spirituality', 'school', 'friendship', 'family', 'work', 
                    'relationships', 'hobbies', 'food', 'entertainment', 'finances',
                    'health', 'body image', 'future plans', 'technology', 'social media',
                    'pets', 'weather', 'sleep', 'mental health', 'home life', 
                    'stress', 'loneliness'
                ]
                
                # Check if title mentions topics NOT in detected list
                detected_topics_lower = [t.lower() for t in topics]
                for known_topic in all_known_topics:
                    if known_topic in title_lower and known_topic not in detected_topics_lower:
                        # LLM hallucinated a topic - reject this title
                        print(f"⚠️ LLM hallucinated topic '{known_topic}' - using fallback")
                        raise ValueError(f"Title mentions undetected topic: {known_topic}")
                
                if len(llm_title) > 55:
                    llm_title = llm_title[:52] + "..."
                
                title = f"{llm_title} - {date_str}"
                return JsonResponse({'success': True, 'title': title})
        
        except Exception as llm_error:
            print(f"⚠️ LLM title generation failed: {str(llm_error)}")
        
        # ✅ IMPROVED: Smarter fallback titles based on DETECTED topics only
        title_variations = []
        
        # Style 1: Topic-focused (using ACTUAL detected topics)
        if topics:
            if len(topics) == 1:
                title = f"{topics[0].capitalize()} chat - {date_str}"
            elif len(topics) == 2:
                title = f"{topics[0].capitalize()} and {topics[1]} - {date_str}"
            else:
                title = f"{topics[0].capitalize()}, {topics[1]}, and more - {date_str}"
            
            return JsonResponse({'success': True, 'title': title})
        
        # Priority 2: Use emotions if no topics
        if emotions:
            if 'happiness' in emotions:
                title = f"Positive moments - {date_str}"
            elif any(e in emotions for e in ['sadness', 'anxiety', 'anger']):
                title = f"Working through feelings - {date_str}"
            else:
                title = f"Sharing emotions - {date_str}"
            
            return JsonResponse({'success': True, 'title': title})
        
        first_user_msg = user_messages.first()
        if first_user_msg:
            content = first_user_msg.content.strip()
            
            # ✅ VALIDATION: Ensure content is from user (not bot phrase)
            if not content or len(content) < 3:
                title = f"Conversation - {date_str}"
            else:
                # ✅ NEW: CRITICAL - Validate that this doesn't contain bot-like phrases
                bot_phrases = [
                    "i'm snowfriend",
                    "i'm here to listen",
                    "i'm here for you",
                    "you can share",
                    "at your own pace",
                    "that's a good question",
                    "i'm here whenever",
                    "good question",
                    "here whenever you need",
                ]
                
                content_lower = content.lower()
                if any(phrase in content_lower for phrase in bot_phrases):
                    # This looks like a bot message somehow - use generic title
                    print(f"⚠️ First user message looks like bot message: {content[:50]}")
                    title = f"Conversation - {date_str}"
                else:
                    # ✅ NEW: Extract semantic title using UNIVERSAL method
                    try:
                        semantic_title = extract_semantic_title_from_message(content, max_length=50)
                        title = f"{semantic_title} - {date_str}"
                        print(f"✓ Generated semantic title: {semantic_title}")
                    except Exception as e:
                        print(f"⚠️ Semantic extraction failed: {str(e)}")
                        # Final final fallback - just use first few words
                        words = content.split()[:6]
                        title_text = " ".join(words)
                        
                        if len(title_text) > 50:
                            title_text = title_text[:47] + "..."
                        
                        title = f"{title_text} - {date_str}"
        else:
            title = f"Conversation - {date_str}"
        
        if len(title) > 80:
            title = title[:77] + "..."
        
        return JsonResponse({'success': True, 'title': title})
        
    except Exception as e:
        print(f"⚠️ Error generating title: {str(e)}")
        import traceback
        traceback.print_exc()
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
# FALLBACK RESPONSES
# ============================================================================

FALLBACK_RESPONSES = [
    "I'm sorry, but I'm having trouble connecting right now. Please try again in a few moments—I'll be here when you're ready.",
    "I apologize, but I'm experiencing some technical difficulties. Your thoughts are important, so please try reaching out again shortly.",
    "I'm not able to respond at the moment due to a connection issue. Please give it another try in a little while—I'm here to listen.",
    "I'm really sorry—I'm having trouble right now. I know it can be frustrating when you're ready to talk. Please try again soon.",
    "I apologize for the interruption. I'm experiencing some difficulties, but I'll be back shortly. Thank you for your patience.",
]


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
                    time_context=time_context
                )
                
                if bot_response is None:
                    bot_response = random.choice(FALLBACK_RESPONSES)
                    print("⚠️ LLM returned None - using fallback response")
                    
            except Exception as api_error:
                print(f"⚠️ API Error: {str(api_error)} - using fallback response")
                bot_response = random.choice(FALLBACK_RESPONSES)
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
            'response': random.choice(FALLBACK_RESPONSES)
        })


@login_required(login_url='login')
@require_http_methods(["GET"])
def get_conversation_history(request):
    try:
        conversation = Conversation.objects.filter(
            user=request.user,
            is_active=True
        ).only('id').first()
        
        if not conversation:
            return JsonResponse({
                'success': True,
                'messages': []
            })
        
        ensure_initial_greeting(conversation, request.user)
        messages = conversation.messages.only('role', 'content', 'timestamp').all()
        
        messages_data = [
            {
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat()
            }
            for msg in messages
        ]
        
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
                'message': f"No messages remaining. Come back in {limit.get_formatted_time_remaining()}."
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