from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
import hashlib


class Feedback(models.Model):
    """
    Model to store anonymous user feedback.
    No user association to maintain privacy.
    """
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    message = models.TextField(
        max_length=1000,
        help_text="User feedback message"
    )
    image = models.ImageField(
        upload_to='feedback_images/',
        null=True,
        blank=True,
        help_text="Optional screenshot or image"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when feedback was submitted"
    )
    ip_address_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Hashed IP address for spam prevention (privacy-friendly, cannot be reversed)"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'

    def __str__(self):
        return f"{self.rating} stars - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def star_display(self):
        """Return a visual representation of the rating"""
        return '⭐' * self.rating

    @property
    def rating_text(self):
        """Return text description of the rating"""
        ratings = {
            5: 'Excellent',
            4: 'Very Good',
            3: 'Good',
            2: 'Fair',
            1: 'Needs Improvement'
        }
        return ratings.get(self.rating, 'Unknown')
    
    @staticmethod
    def hash_ip_address(ip_address):
        """
        Hash an IP address using SHA-256 for privacy.
        The original IP cannot be recovered from the hash.
        """
        if not ip_address:
            return None
        return hashlib.sha256(ip_address.encode('utf-8')).hexdigest()
    
    @classmethod
    def check_rate_limit(cls, ip_hash, limit=3, hours=24):
        """
        Check if an IP hash has exceeded the rate limit.
        Returns True if rate limit exceeded, False otherwise.
        Default: 3 submissions per 24 hours (per day)
        """
        if not ip_hash:
            return False
            
        time_threshold = timezone.now() - timedelta(hours=hours)
        recent_count = cls.objects.filter(
            ip_address_hash=ip_hash,
            created_at__gte=time_threshold
        ).count()
        
        return recent_count >= limit