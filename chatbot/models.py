# models.py - UPDATED WITH LONG-TERM MEMORY AND DATE TRACKING
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date

class Conversation(models.Model):
    """Represents a chat session between a user and Snowfriend"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['user', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_active=True),
                name='unique_active_conversation_per_user'
            )
        ]
    
    def __str__(self):
        return f"Conversation {self.id} - {self.user.username}"


class Message(models.Model):
    """Individual messages within a conversation"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_flagged = models.BooleanField(default=False)
    flagged_reason = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class UserMemory(models.Model):
    """
    ✅ UPDATED: Long-term memory for users across all conversations with date tracking
    Stores facts, preferences, and patterns learned about each user
    """
    memory_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='long_term_memory')
    
    # ====================================================================
    # ✅ NEW: DATE TRACKING
    # ====================================================================
    first_conversation_date = models.DateField(null=True, blank=True)
    last_conversation_date = models.DateField(null=True, blank=True)
    
    # ====================================================================
    # CORE FACTS - Things user has explicitly mentioned
    # ====================================================================
    mentioned_topics = models.JSONField(
        default=dict,
        help_text="Topics user has discussed: {'boxing': 5, 'school': 3, 'family': 2} (frequency count)"
    )
    
    mentioned_people = models.JSONField(
        default=dict,
        help_text="People in user's life: {'mom': True, 'friend': True, 'teacher': True}"
    )
    
    mentioned_places = models.JSONField(
        default=dict,
        help_text="Places user goes: {'school': True, 'gym': True, 'home': True}"
    )
    
    mentioned_activities = models.JSONField(
        default=dict,
        help_text="Activities user does: {'boxing': True, 'gaming': True, 'studying': True}"
    )
    
    # ====================================================================
    # EMOTIONAL PATTERNS
    # ====================================================================
    common_emotions = models.JSONField(
        default=dict,
        help_text="Emotions user frequently expresses: {'sadness': 3, 'anxiety': 2}"
    )
    
    recurring_problems = models.JSONField(
        default=list,
        help_text="Problems user talks about repeatedly: ['bullying', 'body image']"
    )
    
    # ====================================================================
    # PREFERENCES & PATTERNS
    # ====================================================================
    communication_style = models.CharField(
        max_length=20,
        default='casual',
        help_text="User's preferred communication style: casual, formal, brief, detailed"
    )
    
    typical_session_length = models.IntegerField(
        default=0,
        help_text="Average number of messages per conversation"
    )
    
    last_topics_discussed = models.JSONField(
        default=list,
        help_text="Most recent 10 topics user mentioned: ['boxing', 'food', 'weather']"
    )
    
    # ====================================================================
    # METADATA
    # ====================================================================
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    total_conversations = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'User Memory'
        verbose_name_plural = 'User Memories'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['-updated_at']),
        ]
    
    def __str__(self):
        return f"Memory for {self.user.username} (ID: {self.memory_id})"
    
    # ====================================================================
    # HELPER METHODS
    # ====================================================================
    
    def update_from_conversation(self, conversation_facts: dict):
        """
        Update long-term memory based on a conversation's facts
        
        Args:
            conversation_facts: Dict from memory_system.extract_conversation_facts()
        """
        # Update topics (with frequency)
        new_topics = conversation_facts.get('topics_discussed', [])
        for topic in new_topics:
            if topic in self.mentioned_topics:
                self.mentioned_topics[topic] += 1
            else:
                self.mentioned_topics[topic] = 1
        
        # Update people
        entities = conversation_facts.get('entities_mentioned', {})
        if isinstance(entities, dict):
            people = entities.get('people', [])
            for person in people:
                self.mentioned_people[person] = True
            
            # Update places
            places = entities.get('places', [])
            for place in places:
                self.mentioned_places[place] = True
            
            # Update activities
            activities = entities.get('activities', [])
            for activity in activities:
                self.mentioned_activities[activity] = True
        
        # Update emotions
        emotions = conversation_facts.get('emotions_expressed', [])
        for emotion in emotions:
            if emotion in self.common_emotions:
                self.common_emotions[emotion] += 1
            else:
                self.common_emotions[emotion] = 1
        
        # Update last topics discussed (keep last 10)
        self.last_topics_discussed = new_topics + self.last_topics_discussed
        self.last_topics_discussed = self.last_topics_discussed[:10]
        
        # Update metadata
        self.total_conversations += 1
        self.total_messages += conversation_facts.get('exchange_count', 0)
        
        self.save()
    
    def get_memory_summary(self) -> str:
        """
        Generate a text summary of user's long-term memory
        """
        summary_parts = []
        
        # Most discussed topics (top 5)
        if self.mentioned_topics:
            sorted_topics = sorted(self.mentioned_topics.items(), key=lambda x: x[1], reverse=True)[:5]
            topics_str = ', '.join([f"{topic} ({count}x)" for topic, count in sorted_topics])
            summary_parts.append(f"Frequently discusses: {topics_str}")
        
        # People in their life
        if self.mentioned_people:
            people_list = list(self.mentioned_people.keys())[:5]
            summary_parts.append(f"Has mentioned: {', '.join(people_list)}")
        
        # Common emotions
        if self.common_emotions:
            sorted_emotions = sorted(self.common_emotions.items(), key=lambda x: x[1], reverse=True)[:3]
            emotions_str = ', '.join([f"{emotion} ({count}x)" for emotion, count in sorted_emotions])
            summary_parts.append(f"Often feels: {emotions_str}")
        
        # Recent topics
        if self.last_topics_discussed:
            recent = self.last_topics_discussed[:3]
            summary_parts.append(f"Recently talked about: {', '.join(recent)}")
        
        if summary_parts:
            return "\n".join([f"- {part}" for part in summary_parts])
        else:
            return "- New user, building memory..."
    
    def get_top_topics(self, limit=5) -> list:
        """Get user's most discussed topics"""
        if not self.mentioned_topics:
            return []
        sorted_topics = sorted(self.mentioned_topics.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, count in sorted_topics[:limit]]
    
    def has_mentioned(self, topic: str) -> bool:
        """Check if user has ever mentioned a specific topic"""
        return (
            topic in self.mentioned_topics or
            topic in self.mentioned_people or
            topic in self.mentioned_places or
            topic in self.mentioned_activities
        )
    
    def get_days_since_first_conversation(self) -> int:
        """
        ✅ NEW: Calculate how many days since first conversation
        Returns 0 if no first conversation date set
        """
        if not self.first_conversation_date:
            return 0
        
        today = date.today()
        delta = today - self.first_conversation_date
        return delta.days


#======================This is the updated model for message limits======================#

class MessageLimit(models.Model):
    """
    Track message limits per user to manage API usage
    
    Features:
    - 15 messages per user per period (UPDATED from 20)
    - 4-hour reset period
    - Automatic reset when time expires
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='message_limit')
    
    # Message tracking
    total_messages = models.IntegerField(default=15)
    messages_remaining = models.IntegerField(default=15)
    
    # Time tracking  
    reset_time = models.DateTimeField(default=timezone.now)
    last_reset = models.DateTimeField(default=timezone.now)
    
    # Notification tracking
    notified_half = models.BooleanField(default=False)
    notified_three = models.BooleanField(default=False)
    notified_zero = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'message_limits'
        verbose_name = 'Message Limit'
        verbose_name_plural = 'Message Limits'
    
    def __str__(self):
        return f"{self.user.username} - {self.messages_remaining}/{self.total_messages}"
    
    def can_send_message(self):
        """Check if user can send a message"""
        if timezone.now() >= self.reset_time:
            self.reset_limit()
            return True
        return self.messages_remaining > 0
    
    def use_message(self):
        """Decrement message count"""
        if self.messages_remaining > 0:
            self.messages_remaining -= 1
            self.save()
            return True
        return False
    
    def reset_limit(self):
        """Reset message limit after cooldown"""
        from datetime import timedelta
        self.messages_remaining = self.total_messages
        self.reset_time = timezone.now() + timedelta(hours=4)
        self.last_reset = timezone.now()
        self.notified_half = False
        self.notified_three = False
        self.notified_zero = False
        self.save()
    
    def get_time_remaining(self):
        """Get seconds until reset"""
        if timezone.now() >= self.reset_time:
            return 0
        delta = self.reset_time - timezone.now()
        return int(delta.total_seconds())
    
    def get_formatted_time_remaining(self):
        """Get HH:MM:SS format"""
        seconds = self.get_time_remaining()
        if seconds <= 0:
            return "00:00:00"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def should_notify_half(self):
        half = self.total_messages // 2
        return (self.messages_remaining <= half and 
                self.messages_remaining > 3 and 
                not self.notified_half)
    
    def should_notify_three(self):
        return (self.messages_remaining == 3 and not self.notified_three)
    
    def should_notify_zero(self):
        return (self.messages_remaining == 0 and not self.notified_zero)
    
    def mark_notified(self, notification_type):
        if notification_type == 'half':
            self.notified_half = True
        elif notification_type == 'three':
            self.notified_three = True
        elif notification_type == 'zero':
            self.notified_zero = True
        self.save()