from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
import hashlib


class Feedback(models.Model):
    """Model to store anonymous user feedback with security tracking"""
    feedback_id = models.AutoField(primary_key=True)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    message = models.TextField(
        max_length=1000,
        help_text="User feedback message (sanitized)"
    )
    image = models.ImageField(
        upload_to='feedback_images/%Y/%m/%d/',  # Organize by date
        null=True,
        blank=True,
        help_text="Optional screenshot or image (processed and sanitized)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,  # Index for faster queries
        help_text="Timestamp when feedback was submitted"
    )
    ip_address_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,  # Index for rate limiting queries
        help_text="Hashed IP address for spam prevention (SHA-256)"
    )
    is_suspicious = models.BooleanField(
        default=False,
        help_text="Flagged if suspicious patterns detected"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'
        db_table = 'feedback_feedback'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['ip_address_hash', '-created_at']),
            models.Index(fields=['is_suspicious', '-created_at']),
        ]

    def __str__(self):
        suspicious_flag = " [SUSPICIOUS]" if self.is_suspicious else ""
        return f"{self.rating} stars - {self.created_at.strftime('%Y-%m-%d %H:%M')}{suspicious_flag}"

    @property
    def star_display(self):
        return '⭐' * self.rating

    @property
    def rating_text(self):
        ratings = {5: 'Excellent', 4: 'Very Good', 3: 'Good', 2: 'Fair', 1: 'Needs Improvement'}
        return ratings.get(self.rating, 'Unknown')
    
    @staticmethod
    def hash_ip_address(ip_address):
        """
        Hash IP address using SHA-256 for privacy.
        Adds salt for additional security.
        """
        if not ip_address:
            return None
        # Add a salt to make rainbow table attacks harder
        salt = "snowfriend_feedback_salt_2025"  # Store this in environment variable in production
        salted_ip = f"{salt}{ip_address}".encode('utf-8')
        return hashlib.sha256(salted_ip).hexdigest()
    
    @classmethod
    def check_rate_limit(cls, ip_hash, limit=3, hours=24):
        """
        Check if IP has exceeded rate limit.
        """
        if not ip_hash:
            return False
        time_threshold = timezone.now() - timedelta(hours=hours)
        recent_count = cls.objects.filter(
            ip_address_hash=ip_hash,
            created_at__gte=time_threshold
        ).count()
        return recent_count >= limit
    
    @classmethod
    def get_suspicious_count(cls, hours=24):
        """
        Get count of suspicious submissions in the last X hours.
        """
        time_threshold = timezone.now() - timedelta(hours=hours)
        return cls.objects.filter(
            is_suspicious=True,
            created_at__gte=time_threshold
        ).count()
    
    @classmethod
    def cleanup_old_submissions(cls, days=90):
        """
        Clean up old feedback submissions (GDPR compliance).
        Call this periodically via management command or cron job.
        """
        threshold = timezone.now() - timedelta(days=days)
        deleted_count, _ = cls.objects.filter(created_at__lt=threshold).delete()
        return deleted_count
    
    def save(self, *args, **kwargs):
        """
        Override save to ensure message is always under limit.
        """
        if self.message and len(self.message) > 1000:
            self.message = self.message[:1000]
        super().save(*args, **kwargs)