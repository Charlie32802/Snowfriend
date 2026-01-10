from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class PasswordHistory(models.Model):
    """Store password history to prevent reusing the immediate previous password"""
    ph_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_history')
    password_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Password History'
        verbose_name_plural = 'Password Histories'
        db_table = 'accounts_passwordhistory'
    
    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"