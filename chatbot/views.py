# views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db import transaction
import json
import random
from django.http import JsonResponse, HttpResponse
from datetime import datetime

from .models import Conversation, Message
from .safety import ContentSafety
from .services import LLMService


# ============================================================================
# EXPORT & TITLE GENERATION
# ============================================================================

@login_required(login_url='login')
@require_http_methods(["POST"])
def generate_title(request):
    """Generate an AI title for the conversation"""
    try:
        # Get user's active conversation
        conversation = Conversation.objects.filter(
            user=request.user,
            is_active=True
        ).first()
        
        if not conversation:
            # No conversation, use default
            title = f"Conversation - {datetime.now().strftime('%b %d, %Y')}"
            return JsonResponse({'success': True, 'title': title})
        
        # Get recent messages for context
        messages = conversation.messages.filter(role='user').order_by('timestamp')[:5]
        
        if messages.exists():
            # Extract keywords from first user message
            first_message = messages.first()
            content = first_message.content.strip()
            
            # Create a meaningful title from first message (max 50 chars)
            words = content.split()[:8]  # Take first 8 words
            title = " ".join(words)
            
            if len(title) > 50:
                title = title[:47] + "..."
            
            # If title is too short, add date
            if len(title) < 10:
                title = f"{title} - {datetime.now().strftime('%b %d')}"
        else:
            # No user messages yet
            title = f"Snowfriend Chat - {datetime.now().strftime('%b %d, %Y')}"
        
        return JsonResponse({'success': True, 'title': title})
        
    except Exception as e:
        print(f"⚠️ Error generating title: {str(e)}")
        # Return default title on error
        title = f"Conversation - {datetime.now().strftime('%b %d, %Y')}"
        return JsonResponse({'success': True, 'title': title})


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
        
        # Sanitize filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:100]  # Limit length
        
        # Format text content
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
        
        # Create HTTP response with file
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
    """Singleton pattern for LLM service"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


# ============================================================================
# CONVERSATION MANAGEMENT
# ============================================================================

def get_active_conversation(user):
    """
    Safely get or create active conversation for a user
    Handles duplicate active conversations gracefully
    """
    try:
        # Try to get existing active conversation
        conversation = Conversation.objects.filter(
            user=user,
            is_active=True
        ).first()
        
        if conversation:
            # Check for duplicates (shouldn't happen with constraint, but defensive)
            active_count = Conversation.objects.filter(
                user=user,
                is_active=True
            ).count()
            
            if active_count > 1:
                # Fix duplicates: keep most recent, deactivate others
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
            # Create new active conversation
            conversation = Conversation.objects.create(user=user, is_active=True)
            return conversation
            
    except Exception as e:
        print(f"⚠️ Error getting active conversation: {str(e)}")
        # Fallback: create new conversation
        return Conversation.objects.create(user=user, is_active=True)


# ============================================================================
# TOKEN COUNTING & SLIDING WINDOW MEMORY
# ============================================================================

def count_tokens(text):
    """
    Estimate token count for DeepSeek API
    Conservative estimate: ~4 characters = 1 token
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def get_conversation_history_with_limit(conversation, max_tokens=24000):
    """
    Get conversation history with token limit management using sliding window.
    Removes oldest messages when approaching token limit.
    """
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
# API FALLBACK RESPONSES
# ============================================================================

FALLBACK_RESPONSES = [
    "I'm sorry, but I'm having trouble connecting right now. Please try again in a few moments—I'll be here when you're ready.",
    "I apologize, but I'm experiencing some technical difficulties. Your thoughts are important, so please try reaching out again shortly.",
    "I'm not able to respond at the moment due to a connection issue. Please give it another try in a little while—I'm here to listen.",
    "I'm really sorry—I'm having trouble right now. I know it can be frustrating when you're ready to talk. Please try again soon.",
    "I apologize for the interruption. I'm experiencing some difficulties, but I'll be back shortly. Thank you for your patience.",
]


# ============================================================================
# CONVERSATION INITIALIZATION
# ============================================================================

def ensure_initial_greeting(conversation, user):
    """
    Ensure conversation has initial greeting with user's name AND DISCLAIMER
    This makes the bot remember who it's talking to AND sets expectations
    """
    # Check if conversation is empty
    if conversation.messages.count() == 0:
        # Create personalized initial greeting WITH DISCLAIMER
        user_first_name = user.first_name if user.first_name else 'there'
        initial_greeting = (
            f"Hi {user_first_name}! I'm Snowfriend. You can share your thoughts "
            f"here at your own pace. I'm here to listen and help you reflect.\n\n"
        )
        
        # Save initial greeting to database
        Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=initial_greeting
        )
        
        print(f"✓ Created initial greeting with disclaimer for {user_first_name}")


# ============================================================================
# VIEW FUNCTIONS
# ============================================================================

@login_required(login_url='login')
@require_http_methods(["POST"])
def send_message(request):
    """
    Handle incoming user messages and generate bot responses - ENHANCED
    Now includes: Name memory + Therapeutic guidance + Context awareness + Crisis clarification
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({
                'success': False,
                'error': 'Message cannot be empty'
            }, status=400)
        
        # Sanitize input
        user_message = ContentSafety.sanitize_input(user_message)
        
        # ✅ FIXED: Use safe conversation retrieval instead of get_or_create
        conversation = get_active_conversation(request.user)
        
        # ✅ Ensure conversation has initial greeting with user's name
        ensure_initial_greeting(conversation, request.user)
        
        # ✅ Get user's first name for the bot to remember
        user_first_name = request.user.first_name if request.user.first_name else None
        
        # Get conversation history for context-aware safety check
        conversation_history, _ = get_conversation_history_with_limit(
            conversation, 
            max_tokens=24000
        )
        
        # ✅ CRITICAL FIX: Check content safety - NOW RETURNS 4 VALUES
        is_safe, category, safety_response, needs_llm = ContentSafety.check_content(
            user_message,
            conversation_history  # Pass history for context awareness
        )
        
        # Save user message
        user_msg = Message.objects.create(
            conversation=conversation,
            role='user',
            content=user_message,
            is_flagged=not is_safe,
            flagged_reason=category if not is_safe else None
        )
        
        # Determine bot response based on safety check
        if not is_safe and not needs_llm:
            # Use canned safety response (crisis hotlines, etc.)
            bot_response = safety_response
            truncation_occurred = False

            import logging
            logger = logging.getLogger('snowfriend.crisis')
            logger.warning(f"CRISIS DETECTED - User: {request.user.username}, Category: {category}, Message: {user_message[:100]}")
        else:
            # Generate LLM response (either safe content OR crisis clarification)
            try:
                llm_service = get_llm_service()
                
                # Refresh conversation history to include the just-saved user message
                conversation_history, truncation_occurred = get_conversation_history_with_limit(
                    conversation, 
                    max_tokens=24000
                )
                
                from .timezone_utils import get_time_context
                time_context = get_time_context('Asia/Manila')
                bot_response = llm_service.generate_response(
                    conversation_history,
                    user_name=user_first_name,
                    time_context=time_context  # Add this parameter
                )
                
                if bot_response is None:
                    bot_response = random.choice(FALLBACK_RESPONSES)
                    print("⚠️ LLM returned None - using fallback response")
                    
            except Exception as api_error:
                print(f"⚠️ API Error: {str(api_error)} - using fallback response")
                bot_response = random.choice(FALLBACK_RESPONSES)
                truncation_occurred = False
        
        # Save bot response
        with transaction.atomic():
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=bot_response
            )
            conversation.save()
        
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
        traceback.print_exc()  # Print full error for debugging
        return JsonResponse({
            'success': True,
            'response': random.choice(FALLBACK_RESPONSES)
        })


@login_required(login_url='login')
@require_http_methods(["GET"])
def get_conversation_history(request):
    """
    Retrieve conversation history for the current user
    Now includes automatic initial greeting if needed
    """
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
        
        # ✅ Ensure initial greeting exists
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
    """
    PERMANENTLY delete all conversations and messages for the current user
    """
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