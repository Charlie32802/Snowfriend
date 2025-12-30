from django.contrib import admin
from django.utils.html import format_html
from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing feedback submissions.
    """
    list_display = [
        'rating_display',
        'rating_text_display',
        'message_preview',
        'has_image',
        'created_at',
        'privacy_status'
    ]
    list_filter = ['rating', 'created_at']
    search_fields = ['message']
    readonly_fields = [
        'rating',
        'rating_display',
        'message',
        'image_preview',
        'created_at',
        'ip_address_hash'  # Changed from 'ip_address' to 'ip_address_hash'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Feedback Details', {
            'fields': ('rating', 'rating_display', 'message')
        }),
        ('Attachments', {
            'fields': ('image', 'image_preview'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'ip_address_hash'),  # Changed from 'ip_address' to 'ip_address_hash'
            'classes': ('collapse',)
        }),
    )

    def rating_display(self, obj):
        """Display rating as stars"""
        return format_html(
            '<span style="font-size: 1.2em; color: #f39c12;">{}</span>',
            obj.star_display
        )
    rating_display.short_description = 'Rating'

    def rating_text_display(self, obj):
        """Display rating as text"""
        colors = {
            5: '#27ae60',
            4: '#2ecc71',
            3: '#f39c12',
            2: '#e67e22',
            1: '#e74c3c'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.rating, '#95a5a6'),
            obj.rating_text
        )
    rating_text_display.short_description = 'Description'

    def message_preview(self, obj):
        """Show a preview of the message"""
        if len(obj.message) > 100:
            return obj.message[:100] + '...'
        return obj.message
    message_preview.short_description = 'Message'

    def has_image(self, obj):
        """Show if feedback has an image"""
        if obj.image:
            return format_html(
                '<span style="color: #27ae60;">✓ Yes</span>'
            )
        return format_html(
            '<span style="color: #95a5a6;">✗ No</span>'
        )
    has_image.short_description = 'Image'

    def privacy_status(self, obj):
        """Show privacy protection status"""
        if obj.ip_address_hash:
            return format_html(
                '<span style="color: #3498db;" title="IP is hashed for privacy">🔒 Protected</span>'
            )
        return format_html(
            '<span style="color: #95a5a6;">No IP data</span>'
        )
    privacy_status.short_description = 'Privacy'

    def image_preview(self, obj):
        """Display image preview in admin"""
        if obj.image:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 400px; max-height: 400px; border-radius: 8px;" />'
                '</a>',
                obj.image.url,
                obj.image.url
            )
        return 'No image attached'
    image_preview.short_description = 'Image Preview'

    def has_add_permission(self, request):
        """Disable adding feedback through admin"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deleting feedback"""
        return True

    def has_change_permission(self, request, obj=None):
        """Make feedback read-only"""
        return False