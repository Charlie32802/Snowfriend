from django.contrib import admin
from .models import Conversation, Message, UserMemory, MessageLimit

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    # Use 'conversation_id' instead of 'id'
    list_display = ['conversation_id', 'user', 'created_at', 'updated_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'conversation_id']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    # Use 'message_id' instead of 'id'
    list_display = ['message_id', 'conversation', 'role', 'content_preview', 'timestamp', 'is_flagged']
    list_filter = ['role', 'is_flagged', 'timestamp']
    search_fields = ['content', 'conversation__user__username']
    readonly_fields = ['timestamp', 'message_id']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'

@admin.register(UserMemory)
class UserMemoryAdmin(admin.ModelAdmin):
    list_display = ['memory_id', 'user', 'first_conversation_date', 'last_conversation_date', 'updated_at', 'total_conversations']
    list_filter = ['first_conversation_date', 'last_conversation_date']
    search_fields = ['user__username']
    readonly_fields = ['memory_id', 'created_at', 'updated_at']
    
    # Add custom method to display summary in admin
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'memory_id', 'first_conversation_date', 'last_conversation_date')
        }),
        ('Memory Content', {
            'fields': ('mentioned_topics', 'mentioned_people', 'mentioned_places', 'mentioned_activities'),
            'classes': ('collapse',)
        }),
        ('Emotional Patterns', {
            'fields': ('common_emotions', 'recurring_problems'),
            'classes': ('collapse',)
        }),
        ('Preferences & Metadata', {
            'fields': ('communication_style', 'typical_session_length', 'last_topics_discussed', 
                      'total_conversations', 'total_messages', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(MessageLimit)
class MessageLimitAdmin(admin.ModelAdmin):
    list_display = ['ml_id', 'user', 'messages_remaining', 'total_messages', 'reset_time', 'last_reset']
    list_filter = ['reset_time', 'last_reset']
    search_fields = ['user__username']
    readonly_fields = ['ml_id', 'created_at', 'updated_at']
    
    def get_time_remaining(self, obj):
        return obj.get_formatted_time_remaining()
    get_time_remaining.short_description = 'Time Until Reset'