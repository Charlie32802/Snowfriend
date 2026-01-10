from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import PasswordHistory

@admin.register(PasswordHistory)
class PasswordHistoryAdmin(admin.ModelAdmin):
    """Admin interface for PasswordHistory model"""
    list_display = [
        'ph_id', 
        'user', 
        'created_at', 
        'password_hash_preview'
    ]
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['ph_id', 'created_at', 'password_hash']
    ordering = ['-created_at']
    
    def password_hash_preview(self, obj):
        """Show a preview of the password hash"""
        return f"{obj.password_hash[:30]}..."
    password_hash_preview.short_description = 'Password Hash'
    
    def has_add_permission(self, request):
        """Disable adding password history manually through admin"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make password history read-only"""
        return False


# Custom User Admin to show related PasswordHistory
class CustomUserAdmin(UserAdmin):
    """Extend default UserAdmin to show PasswordHistory"""
    list_display = UserAdmin.list_display + ('date_joined', 'last_login')
    readonly_fields = UserAdmin.readonly_fields + ('date_joined', 'last_login')
    
    # Add PasswordHistory to User admin page
    def get_inlines(self, request, obj):
        """Add PasswordHistory inline for existing users"""
        if obj:
            return [PasswordHistoryInline]
        return []
    
    def get_fieldsets(self, request, obj=None):
        """Add custom fieldsets to User admin"""
        fieldsets = super().get_fieldsets(request, obj)
        # Add date_joined and last_login to personal info
        for fieldset in fieldsets:
            if fieldset[0] == 'Personal info':
                fieldset[1]['fields'] = fieldset[1]['fields'] + ('date_joined', 'last_login')
                break
        return fieldsets


class PasswordHistoryInline(admin.TabularInline):
    """Inline display of PasswordHistory for User admin"""
    model = PasswordHistory
    extra = 0
    max_num = 5
    can_delete = False
    readonly_fields = ['ph_id', 'password_hash_preview', 'created_at']
    
    def password_hash_preview(self, obj):
        """Show a preview of the password hash"""
        return f"{obj.password_hash[:30]}..."
    password_hash_preview.short_description = 'Password Hash'
    
    def has_add_permission(self, request, obj):
        """Disable adding through inline"""
        return False


# Unregister the default User admin and register with our custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)