"""
Security middleware for Snowfriend feedback system.
Adds security headers and additional protection layers.
"""

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.utils import timezone
import logging

security_logger = logging.getLogger('feedback.security')


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to all responses.
    """
    
    def process_response(self, request, response):
    # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
        )
        
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (formerly Feature Policy)
        response['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'accelerometer=()'
        )
        
        # HSTS (only if using HTTPS in production)
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response


class FeedbackRateLimitMiddleware(MiddlewareMixin):
    """
    Additional rate limiting specifically for feedback endpoint.
    Works alongside the view-level rate limiting.
    """
    
    def process_request(self, request):
        # Only apply to feedback submission endpoint
        if request.path == '/feedback/api/submit/' and request.method == 'POST':
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
            
            # Rate limit key
            cache_key = f'feedback_ratelimit_{ip}'
            
            # Get current request count
            request_count = cache.get(cache_key, 0)
            
            # Allow max 10 requests per minute (aggressive rate limiting)
            if request_count >= 10:
                security_logger.warning(f"Rate limit exceeded: {ip} - {request_count} requests")
                return JsonResponse({
                    'success': False,
                    'error': 'Too many requests. Please slow down.'
                }, status=429)
            
            # Increment counter
            cache.set(cache_key, request_count + 1, 60)  # 60 seconds timeout
        
        return None


class RequestSizeMiddleware(MiddlewareMixin):
    """
    Limit request body size to prevent DoS attacks.
    """
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
    
    def process_request(self, request):
        if request.method == 'POST':
            content_length = request.META.get('CONTENT_LENGTH')
            
            if content_length:
                try:
                    content_length = int(content_length)
                    if content_length > self.MAX_UPLOAD_SIZE:
                        security_logger.warning(
                            f"Request too large: {content_length} bytes from {request.META.get('REMOTE_ADDR')}"
                        )
                        return JsonResponse({
                            'success': False,
                            'error': 'Request size too large.'
                        }, status=413)
                except (ValueError, TypeError):
                    pass
        
        return None


class SuspiciousActivityMiddleware(MiddlewareMixin):
    """
    Monitor and block suspicious activity patterns.
    """
    
    def process_request(self, request):
        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        
        # Check if IP is blocked
        blocked_key = f'blocked_ip_{ip}'
        if cache.get(blocked_key):
            security_logger.warning(f"Blocked IP attempted access: {ip}")
            return JsonResponse({
                'success': False,
                'error': 'Access denied.'
            }, status=403)
        
        # Check for suspicious patterns in request
        suspicious_patterns = [
            '../',  # Path traversal
            '<script',  # XSS attempts
            'UNION SELECT',  # SQL injection
            'DROP TABLE',  # SQL injection
            '<?php',  # Code injection
            'eval(',  # Code execution
        ]
        
        # Check URL and query string
        full_path = request.get_full_path().lower()
        for pattern in suspicious_patterns:
            if pattern.lower() in full_path:
                security_logger.warning(f"Suspicious pattern in URL: {pattern} from {ip}")
                
                # Block IP for 1 hour
                cache.set(blocked_key, True, 3600)
                
                return JsonResponse({
                    'success': False,
                    'error': 'Suspicious activity detected.'
                }, status=403)
        
        return None