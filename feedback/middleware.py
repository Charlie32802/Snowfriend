from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
import logging

security_logger = logging.getLogger('feedback.security')


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
        )
        response['X-Frame-Options'] = 'DENY'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
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
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        return response


class FeedbackRateLimitMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path == '/feedback/api/submit/' and request.method == 'POST':
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', '0.0.0.0')

            cache_key = f'feedback_ratelimit_{ip}'
            request_count = cache.get(cache_key, 0)

            if request_count >= 10:
                security_logger.warning(f"Rate limit exceeded: {ip} - {request_count} requests")
                return JsonResponse({
                    'success': False,
                    'error': 'Too many requests. Please slow down.'
                }, status=429)

            cache.set(cache_key, request_count + 1, 60)

        return None


class RequestSizeMiddleware(MiddlewareMixin):
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024

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
    def process_request(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')

        blocked_key = f'blocked_ip_{ip}'
        if cache.get(blocked_key):
            security_logger.warning(f"Blocked IP attempted access: {ip}")
            return JsonResponse({
                'success': False,
                'error': 'Access denied.'
            }, status=403)

        suspicious_patterns = [
            '../',
            '<script',
            'UNION SELECT',
            'DROP TABLE',
            '<?php',
            'eval(',
        ]

        full_path = request.get_full_path().lower()
        for pattern in suspicious_patterns:
            if pattern.lower() in full_path:
                security_logger.warning(f"Suspicious pattern in URL: {pattern} from {ip}")
                cache.set(blocked_key, True, 3600)
                return JsonResponse({
                    'success': False,
                    'error': 'Suspicious activity detected.'
                }, status=403)

        return None