from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Feedback


class SuspiciousFilter(admin.SimpleListFilter):
    """Filter for suspicious submissions"""
    title = 'Security Status'
    parameter_name = 'security_status'

    def lookups(self, request, model_admin):
        return (
            ('suspicious', 'Suspicious'),
            ('clean', 'Clean'),
            ('recent_suspicious', 'Suspicious (Last 24h)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'suspicious':
            return queryset.filter(is_suspicious=True)
        if self.value() == 'clean':
            return queryset.filter(is_suspicious=False)
        if self.value() == 'recent_suspicious':
            yesterday = timezone.now() - timedelta(days=1)
            return queryset.filter(is_suspicious=True, created_at__gte=yesterday)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing feedback submissions with security monitoring.
    """
    list_display = [
        'feedback_id',
        'security_indicator',
        'rating_display',
        'rating_text_display',
        'message_preview',
        'has_image',
        'created_at',
        'privacy_status'
    ]
    list_filter = [
        SuspiciousFilter,
        'rating',
        'created_at',
        'is_suspicious'
    ]
    search_fields = ['message', 'feedback_id']
    readonly_fields = [
        'feedback_id',
        'rating',
        'rating_display',
        'message',
        'message_analysis',
        'image_preview',
        'created_at',
        'ip_address_hash',
        'is_suspicious',
        'security_analysis'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Security Analysis', {
            'fields': ('security_analysis', 'is_suspicious'),
            'classes': ('wide',),
        }),
        ('Feedback Details', {
            'fields': ('feedback_id', 'rating', 'rating_display', 'message', 'message_analysis')
        }),
        ('Attachments', {
            'fields': ('image', 'image_preview'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'ip_address_hash'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_suspicious', 'mark_as_clean']

    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related()

    def security_indicator(self, obj):
        """Visual security status indicator"""
        if obj.is_suspicious:
            return format_html(
                '<span style="font-size: 1.5em; color: #e74c3c;" title="Suspicious content detected">⚠️</span>'
            )
        return format_html(
            '<span style="font-size: 1.5em; color: #27ae60;" title="Clean">✓</span>'
        )
    security_indicator.short_description = '🔒'
    security_indicator.admin_order_field = 'is_suspicious'

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
        max_length = 80
        if len(obj.message) > max_length:
            preview = obj.message[:max_length] + '...'
        else:
            preview = obj.message
        
        # Highlight suspicious messages
        if obj.is_suspicious:
            return format_html(
                '<span style="color: #e74c3c; font-weight: 500;">{}</span>',
                preview
            )
        return preview
    message_preview.short_description = 'Message'

    def message_analysis(self, obj):
        """Detailed message analysis"""
        length = len(obj.message)
        word_count = len(obj.message.split())
        
        return format_html(
            '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">'
            '<p><strong>Length:</strong> {} characters</p>'
            '<p><strong>Words:</strong> {}</p>'
            '<p><strong>Full Message:</strong></p>'
            '<div style="background: white; padding: 10px; border: 1px solid #dee2e6; '
            'border-radius: 3px; white-space: pre-wrap; max-height: 200px; overflow-y: auto;">{}</div>'
            '</div>',
            length,
            word_count,
            obj.message
        )
    message_analysis.short_description = 'Message Analysis'

    def security_analysis(self, obj):
        """Display security analysis"""
        # Check for recent submissions from same IP
        if obj.ip_address_hash:
            recent_submissions = Feedback.objects.filter(
                ip_address_hash=obj.ip_address_hash,
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
        else:
            recent_submissions = 0
        
        status_color = '#e74c3c' if obj.is_suspicious else '#27ae60'
        status_text = 'SUSPICIOUS - Review Required' if obj.is_suspicious else 'Clean'
        
        return format_html(
            '<div style="background: {}; color: white; padding: 15px; border-radius: 5px;">'
            '<h3 style="margin-top: 0; color: white;">Security Status: {}</h3>'
            '<p><strong>Submissions (24h):</strong> {} from this IP</p>'
            '<p><strong>Risk Level:</strong> {}</p>'
            '</div>',
            status_color,
            status_text,
            recent_submissions,
            'HIGH' if obj.is_suspicious else 'LOW'
        )
    security_analysis.short_description = 'Security Analysis'

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
                '<span style="color: #3498db;" title="IP is hashed (SHA-256)">🔒 Protected</span>'
            )
        return format_html(
            '<span style="color: #95a5a6;">No IP data</span>'
        )
    privacy_status.short_description = 'Privacy'

    def image_preview(self, obj):
        """Display image preview in admin"""
        if obj.image:
            return format_html(
                '<div style="border: 2px solid #dee2e6; border-radius: 8px; padding: 10px; '
                'background: #f8f9fa; display: inline-block;">'
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 400px; max-height: 400px; border-radius: 5px;" />'
                '</a>'
                '<p style="margin-top: 10px; font-size: 12px; color: #6c757d;">Click to view full size</p>'
                '</div>',
                obj.image.url,
                obj.image.url
            )
        return format_html(
            '<p style="color: #6c757d; font-style: italic;">No image attached</p>'
        )
    image_preview.short_description = 'Image Preview'

    def mark_as_suspicious(self, request, queryset):
        """Mark selected feedback as suspicious"""
        count = queryset.update(is_suspicious=True)
        self.message_user(request, f'{count} feedback(s) marked as suspicious.')
    mark_as_suspicious.short_description = 'Mark as suspicious'

    def mark_as_clean(self, request, queryset):
        """Mark selected feedback as clean"""
        count = queryset.update(is_suspicious=False)
        self.message_user(request, f'{count} feedback(s) marked as clean.')
    mark_as_clean.short_description = 'Mark as clean'

    def changelist_view(self, request, extra_context=None):
        """Add statistics to the change list view"""
        extra_context = extra_context or {}
        
        # Get statistics
        total_count = Feedback.objects.count()
        suspicious_count = Feedback.objects.filter(is_suspicious=True).count()
        recent_count = Feedback.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        extra_context['statistics'] = {
            'total': total_count,
            'suspicious': suspicious_count,
            'recent_week': recent_count,
        }
        
        return super().changelist_view(request, extra_context)

    def has_add_permission(self, request):
        """Disable adding feedback through admin"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deleting feedback"""
        return True

    def has_change_permission(self, request, obj=None):
        """Make feedback read-only except for is_suspicious field"""
        return request.user.is_superuser