from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
import logging
from .models import PasswordHistory

admin_logger = logging.getLogger('accounts.admin')


class SecureAdminSite(admin.AdminSite):
    site_header = 'Snowfriend Administration'
    site_title = 'Snowfriend Admin'
    index_title = 'Secure Administration Panel'

    def has_permission(self, request):
        has_perm = super().has_permission(request)

        if not has_perm:
            admin_logger.warning(
                f"Unauthorized admin access attempt from IP: {self.get_client_ip(request)} "
                f"User: {request.user if request.user.is_authenticated else 'Anonymous'}"
            )
        else:
            admin_logger.info(
                f"Admin access: {request.user.username} from IP: {self.get_client_ip(request)}"
            )

        return has_perm

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip


admin_site = SecureAdminSite(name='secure_admin')


@admin.register(PasswordHistory, site=admin_site)
class PasswordHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'ph_id',
        'user_link',
        'created_at_display',
        'password_hash_masked',
        'age_display'
    ]
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = [
        'ph_id',
        'user',
        'created_at',
        'password_hash_masked_detail',
        'password_hash_length',
        'hash_algorithm'
    ]
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def user_link(self, obj):
        url = reverse('secure_admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    created_at_display.short_description = 'Created'
    created_at_display.admin_order_field = 'created_at'

    def password_hash_masked(self, obj):
        if obj.password_hash:
            return f"{obj.password_hash[:8]}... ({len(obj.password_hash)} chars)"
        return "No hash"
    password_hash_masked.short_description = 'Password Hash'

    def password_hash_masked_detail(self, obj):
        if obj.password_hash:
            parts = obj.password_hash.split('$')
            if len(parts) >= 1:
                algorithm = parts[0] if parts[0] else 'unknown'
                return format_html(
                    '<div style="font-family: monospace; background: #f5f5f5; padding: 10px; border-radius: 4px;">'
                    '<strong>Algorithm:</strong> {}<br>'
                    '<strong>Hash Preview:</strong> {}...<br>'
                    '<strong>Length:</strong> {} characters<br>'
                    '<span style="color: #666; font-size: 0.9em;">Full hash hidden for security</span>'
                    '</div>',
                    algorithm,
                    obj.password_hash[:30],
                    len(obj.password_hash)
                )
        return "No hash available"
    password_hash_masked_detail.short_description = 'Password Hash Details'

    def password_hash_length(self, obj):
        return len(obj.password_hash) if obj.password_hash else 0
    password_hash_length.short_description = 'Hash Length'

    def hash_algorithm(self, obj):
        if obj.password_hash:
            parts = obj.password_hash.split('$')
            return parts[0] if parts[0] else 'unknown'
        return 'N/A'
    hash_algorithm.short_description = 'Algorithm'

    def age_display(self, obj):
        age = timezone.now() - obj.created_at
        days = age.days
        hours = age.seconds // 3600

        if days > 0:
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif hours > 0:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            return "Just now"
    age_display.short_description = 'Age'

    def changelist_view(self, request, extra_context=None):
        admin_logger.info(
            f"Password history list viewed by: {request.user.username} "
            f"from IP: {SecureAdminSite.get_client_ip(request)}"
        )
        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        admin_logger.warning(
            f"Password history detail viewed by: {request.user.username} "
            f"for user: {obj.user.username if obj else 'unknown'} "
            f"from IP: {SecureAdminSite.get_client_ip(request)}"
        )
        return super().change_view(request, object_id, form_url, extra_context)


class PasswordHistoryInline(admin.TabularInline):
    model = PasswordHistory
    extra = 0
    max_num = 3
    can_delete = False
    readonly_fields = ['ph_id', 'password_hash_masked', 'created_at', 'age']
    fields = ['ph_id', 'password_hash_masked', 'created_at', 'age']
    ordering = ['-created_at']

    def password_hash_masked(self, obj):
        if obj.password_hash:
            return f"{obj.password_hash[:8]}... (hidden)"
        return "No hash"
    password_hash_masked.short_description = 'Password Hash (Masked)'

    def age(self, obj):
        age = timezone.now() - obj.created_at
        days = age.days
        if days > 0:
            return f"{days}d ago"
        else:
            hours = age.seconds // 3600
            return f"{hours}h ago"
    age.short_description = 'Age'

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class CustomUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + (
        'date_joined_display',
        'last_login_display',
        'password_age',
        'is_active_display'
    )
    list_filter = UserAdmin.list_filter + ('date_joined', 'last_login')
    readonly_fields = UserAdmin.readonly_fields + (
        'date_joined',
        'last_login',
        'password_history_count',
        'account_age_display',
        'last_password_change'
    )

    fieldsets = UserAdmin.fieldsets + (
        ('Security Information', {
            'fields': (
                'password_history_count',
                'account_age_display',
                'last_password_change'
            ),
            'classes': ('collapse',)
        }),
    )

    def get_inlines(self, request, obj=None):
        if obj:
            return [PasswordHistoryInline]
        return []

    def date_joined_display(self, obj):
        return obj.date_joined.strftime('%Y-%m-%d')
    date_joined_display.short_description = 'Joined'
    date_joined_display.admin_order_field = 'date_joined'

    def last_login_display(self, obj):
        if obj.last_login:
            return obj.last_login.strftime('%Y-%m-%d %H:%M')
        return 'Never'
    last_login_display.short_description = 'Last Login'
    last_login_display.admin_order_field = 'last_login'

    def is_active_display(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Active</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Inactive</span>'
        )
    is_active_display.short_description = 'Status'
    is_active_display.admin_order_field = 'is_active'

    def password_age(self, obj):
        last_change = PasswordHistory.objects.filter(user=obj).order_by('-created_at').first()
        if last_change:
            age = timezone.now() - last_change.created_at
            days = age.days
            if days == 0:
                return "Today"
            elif days == 1:
                return "1 day"
            elif days < 30:
                return f"{days} days"
            elif days < 365:
                months = days // 30
                return f"{months} month{'s' if months != 1 else ''}"
            else:
                years = days // 365
                return f"{years} year{'s' if years != 1 else ''}"
        return "Unknown"
    password_age.short_description = 'Password Age'

    def password_history_count(self, obj):
        count = PasswordHistory.objects.filter(user=obj).count()
        return f"{count} change{'s' if count != 1 else ''}"
    password_history_count.short_description = 'Password Changes'

    def account_age_display(self, obj):
        age = timezone.now() - obj.date_joined
        days = age.days
        if days < 30:
            return f"{days} day{'s' if days != 1 else ''}"
        elif days < 365:
            months = days // 30
            return f"{months} month{'s' if months != 1 else ''}"
        else:
            years = days // 365
            return f"{years} year{'s' if years != 1 else ''}"
    account_age_display.short_description = 'Account Age'

    def last_password_change(self, obj):
        last_change = PasswordHistory.objects.filter(user=obj).order_by('-created_at').first()
        if last_change:
            return last_change.created_at.strftime('%Y-%m-%d %H:%M:%S')
        return "Never changed"
    last_password_change.short_description = 'Last Password Change'

    def save_model(self, request, obj, form, change):
        if change:
            admin_logger.warning(
                f"User modified: {obj.username} by {request.user.username} "
                f"from IP: {SecureAdminSite.get_client_ip(request)}"
            )
        else:
            admin_logger.info(
                f"User created: {obj.username} by {request.user.username} "
                f"from IP: {SecureAdminSite.get_client_ip(request)}"
            )
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        admin_logger.critical(
            f"User deleted: {obj.username} by {request.user.username} "
            f"from IP: {SecureAdminSite.get_client_ip(request)}"
        )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        usernames = list(queryset.values_list('username', flat=True))
        admin_logger.critical(
            f"Bulk user deletion: {len(usernames)} users by {request.user.username} "
            f"Users: {', '.join(usernames)} "
            f"from IP: {SecureAdminSite.get_client_ip(request)}"
        )
        super().delete_queryset(request, queryset)


admin.site.unregister(User)
admin_site.register(User, CustomUserAdmin)