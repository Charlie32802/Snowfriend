"""
Enhanced Security Middleware for Snowfriend Authentication System
FIXED VERSION - Less aggressive blocking, allows view-level sanitization
"""

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import logging
import re
import hashlib

security_logger = logging.getLogger('accounts.security')
auth_logger = logging.getLogger('accounts.auth')


class AuthenticationSecurityMiddleware(MiddlewareMixin):
    """
    Enhanced security headers and protection for authentication endpoints
    """
    
    def process_response(self, request, response):
        # Add security headers to authentication pages
        auth_paths = ['/login/', '/register/', '/password-reset/', '/password-update/']
        
        if any(request.path.startswith(path) for path in auth_paths):
            # Strict Content Security Policy for auth pages
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "form-action 'self'; "
                "base-uri 'self';"
            )
            
            # Additional security headers
            response['X-Frame-Options'] = 'DENY'
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Cache control for sensitive pages
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response


class LoginAttemptTrackingMiddleware(MiddlewareMixin):
    """
    Track failed login attempts and implement progressive delays
    """
    
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = 15 * 60  # 15 minutes in seconds
    
    def process_request(self, request):
        if request.path == '/login/' and request.method == 'POST':
            ip_address = self.get_client_ip(request)
            email_or_username = request.POST.get('email', '').lower().strip()
            
            # Check IP-based lockout
            ip_lockout_key = f'login_lockout_ip_{hashlib.sha256(ip_address.encode()).hexdigest()}'
            if cache.get(ip_lockout_key):
                lockout_time = cache.get(ip_lockout_key + '_time')
                remaining = self.LOCKOUT_DURATION - (timezone.now().timestamp() - lockout_time)
                
                security_logger.warning(
                    f"Login attempt from locked out IP: {ip_address[:10]}... "
                    f"({int(remaining/60)} minutes remaining)"
                )
                
                from django.contrib import messages
                messages.error(
                    request, 
                    f'Too many failed login attempts. Please try again in {int(remaining/60)} minutes.'
                )
                from django.shortcuts import redirect
                return redirect('login')
            
            # Check username/email-based lockout
            if email_or_username:
                user_lockout_key = f'login_lockout_user_{hashlib.sha256(email_or_username.encode()).hexdigest()}'
                if cache.get(user_lockout_key):
                    lockout_time = cache.get(user_lockout_key + '_time')
                    remaining = self.LOCKOUT_DURATION - (timezone.now().timestamp() - lockout_time)
                    
                    security_logger.warning(
                        f"Login attempt for locked account: {email_or_username[:3]}***"
                    )
                    
                    from django.contrib import messages
                    messages.error(
                        request, 
                        f'This account is temporarily locked. Please try again in {int(remaining/60)} minutes or reset your password.'
                    )
                    from django.shortcuts import redirect
                    return redirect('login')
        
        return None
    
    def process_response(self, request, response):
        """Track failed login attempts"""
        if request.path == '/login/' and request.method == 'POST':
            # Check if login was successful by looking at messages
            from django.contrib.messages import get_messages
            messages = get_messages(request)
            
            login_failed = False
            for message in messages:
                if 'incorrect password' in str(message).lower() or 'invalid' in str(message).lower() or 'not found' in str(message).lower():
                    login_failed = True
                    break
            
            if login_failed:
                ip_address = self.get_client_ip(request)
                email_or_username = request.POST.get('email', '').lower().strip()
                
                # Track IP-based attempts
                ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
                ip_attempts_key = f'login_attempts_ip_{ip_hash}'
                ip_attempts = cache.get(ip_attempts_key, 0) + 1
                cache.set(ip_attempts_key, ip_attempts, 3600)  # Track for 1 hour
                
                # Track user-based attempts
                if email_or_username:
                    user_hash = hashlib.sha256(email_or_username.encode()).hexdigest()
                    user_attempts_key = f'login_attempts_user_{user_hash}'
                    user_attempts = cache.get(user_attempts_key, 0) + 1
                    cache.set(user_attempts_key, user_attempts, 3600)
                    
                    # Lock account if too many attempts
                    if user_attempts >= self.MAX_FAILED_ATTEMPTS:
                        lockout_key = f'login_lockout_user_{user_hash}'
                        cache.set(lockout_key, True, self.LOCKOUT_DURATION)
                        cache.set(lockout_key + '_time', timezone.now().timestamp(), self.LOCKOUT_DURATION)
                        
                        security_logger.warning(
                            f"Account locked due to failed attempts: {email_or_username[:3]}*** "
                            f"({user_attempts} attempts)"
                        )
                
                # Lock IP if too many attempts
                if ip_attempts >= self.MAX_FAILED_ATTEMPTS:
                    lockout_key = f'login_lockout_ip_{ip_hash}'
                    cache.set(lockout_key, True, self.LOCKOUT_DURATION)
                    cache.set(lockout_key + '_time', timezone.now().timestamp(), self.LOCKOUT_DURATION)
                    
                    security_logger.warning(
                        f"IP locked due to failed attempts: {ip_address[:10]}... "
                        f"({ip_attempts} attempts)"
                    )
                
                auth_logger.info(
                    f"Failed login attempt {ip_attempts} from IP: {ip_address[:10]}..."
                )
        
        return response
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address securely"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                return ip
        return request.META.get('REMOTE_ADDR', '0.0.0.0')


class RegistrationRateLimitMiddleware(MiddlewareMixin):
    """
    Rate limit registration attempts to prevent abuse
    """
    
    MAX_REGISTRATIONS_PER_IP_PER_HOUR = 3
    MAX_REGISTRATIONS_PER_IP_PER_DAY = 5
    
    def process_request(self, request):
        if request.path == '/register/' and request.method == 'POST':
            ip_address = LoginAttemptTrackingMiddleware.get_client_ip(request)
            ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
            
            # Check hourly limit
            hourly_key = f'registration_hourly_{ip_hash}'
            hourly_count = cache.get(hourly_key, 0)
            
            if hourly_count >= self.MAX_REGISTRATIONS_PER_IP_PER_HOUR:
                security_logger.warning(
                    f"Registration rate limit exceeded (hourly): {ip_address[:10]}..."
                )
                
                from django.contrib import messages
                messages.error(
                    request,
                    'Too many registration attempts. Please try again in an hour.'
                )
                from django.shortcuts import redirect
                return redirect('register')
            
            # Check daily limit
            daily_key = f'registration_daily_{ip_hash}'
            daily_count = cache.get(daily_key, 0)
            
            if daily_count >= self.MAX_REGISTRATIONS_PER_IP_PER_DAY:
                security_logger.warning(
                    f"Registration rate limit exceeded (daily): {ip_address[:10]}..."
                )
                
                from django.contrib import messages
                messages.error(
                    request,
                    'Daily registration limit reached. Please try again tomorrow.'
                )
                from django.shortcuts import redirect
                return redirect('register')
        
        return None
    
    def process_response(self, request, response):
        """Track successful registrations"""
        if request.path == '/register/' and request.method == 'POST':
            # Check if registration was successful
            if response.status_code == 302 and '/login/' in response.url:
                ip_address = LoginAttemptTrackingMiddleware.get_client_ip(request)
                ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
                
                # Increment hourly counter
                hourly_key = f'registration_hourly_{ip_hash}'
                hourly_count = cache.get(hourly_key, 0) + 1
                cache.set(hourly_key, hourly_count, 3600)  # 1 hour
                
                # Increment daily counter
                daily_key = f'registration_daily_{ip_hash}'
                daily_count = cache.get(daily_key, 0) + 1
                cache.set(daily_key, daily_count, 86400)  # 24 hours
                
                auth_logger.info(
                    f"Registration completed from IP: {ip_address[:10]}... "
                    f"(hourly: {hourly_count}, daily: {daily_count})"
                )
        
        return response


class PasswordResetRateLimitMiddleware(MiddlewareMixin):
    """
    Rate limit password reset requests to prevent abuse
    """
    
    MAX_RESETS_PER_IP_PER_HOUR = 3
    MAX_RESETS_PER_EMAIL_PER_DAY = 5
    
    def process_request(self, request):
        if request.path == '/password-reset-request/' and request.method == 'POST':
            ip_address = LoginAttemptTrackingMiddleware.get_client_ip(request)
            ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
            
            # Check IP-based hourly limit
            hourly_key = f'password_reset_hourly_{ip_hash}'
            hourly_count = cache.get(hourly_key, 0)
            
            if hourly_count >= self.MAX_RESETS_PER_IP_PER_HOUR:
                security_logger.warning(
                    f"Password reset rate limit exceeded: {ip_address[:10]}..."
                )
                
                return JsonResponse({
                    'success': False,
                    'message': 'Too many password reset requests. Please try again in an hour.'
                }, status=429)
            
            # Check email-based daily limit
            email = request.POST.get('email', '').lower().strip()
            if email:
                email_hash = hashlib.sha256(email.encode()).hexdigest()
                daily_key = f'password_reset_daily_{email_hash}'
                daily_count = cache.get(daily_key, 0)
                
                if daily_count >= self.MAX_RESETS_PER_EMAIL_PER_DAY:
                    security_logger.warning(
                        f"Password reset daily limit exceeded for: {email[:3]}***"
                    )
                    
                    return JsonResponse({
                        'success': False,
                        'message': 'Daily password reset limit reached. Please contact support.'
                    }, status=429)
        
        return None
    
    def process_response(self, request, response):
        """Track password reset requests"""
        if request.path == '/password-reset-request/' and request.method == 'POST':
            # Check if response was successful
            try:
                if hasattr(response, 'content'):
                    import json
                    data = json.loads(response.content)
                    if data.get('success'):
                        ip_address = LoginAttemptTrackingMiddleware.get_client_ip(request)
                        ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
                        
                        # Increment IP-based counter
                        hourly_key = f'password_reset_hourly_{ip_hash}'
                        hourly_count = cache.get(hourly_key, 0) + 1
                        cache.set(hourly_key, hourly_count, 3600)
                        
                        # Increment email-based counter
                        email = request.POST.get('email', '').lower().strip()
                        if email:
                            email_hash = hashlib.sha256(email.encode()).hexdigest()
                            daily_key = f'password_reset_daily_{email_hash}'
                            daily_count = cache.get(daily_key, 0) + 1
                            cache.set(daily_key, daily_count, 86400)
                            
                            auth_logger.info(
                                f"Password reset requested for: {email[:3]}*** "
                                f"from IP: {ip_address[:10]}..."
                            )
            except:
                pass
        
        return response


class SuspiciousAuthActivityMiddleware(MiddlewareMixin):
    """
    Detect and LOG suspicious authentication activity
    FIXED: Only logs, does NOT block - lets views handle sanitization
    """
    
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>',
        r'javascript:',
        r'on\w+=',
        r'<iframe',
        r'\.\./\.\.',
        r'UNION\s+SELECT',
        r'DROP\s+TABLE',
        r'eval\(',
        # Removed 'base64' and '<!--' as they're too common in legitimate use
    ]
    
    def process_request(self, request):
        auth_paths = ['/login/', '/register/', '/password-reset-request/']
        
        if request.path in auth_paths and request.method == 'POST':
            # Check all POST data for suspicious patterns
            suspicious_count = 0
            
            for key, value in request.POST.items():
                if isinstance(value, str):
                    for pattern in self.SUSPICIOUS_PATTERNS:
                        if re.search(pattern, value, re.IGNORECASE):
                            suspicious_count += 1
                            security_logger.critical(
                                f"SUSPICIOUS AUTH ACTIVITY DETECTED! "
                                f"Pattern: {pattern} in field: {key} "
                                f"from IP: {LoginAttemptTrackingMiddleware.get_client_ip(request)[:10]}... "
                                f"Path: {request.path}"
                            )
                            break
            
            # FIXED: Only block after MULTIPLE suspicious patterns (very severe cases)
            # Single suspicious pattern is logged but allowed (view will sanitize)
            if suspicious_count >= 3:
                ip_address = LoginAttemptTrackingMiddleware.get_client_ip(request)
                ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
                
                # Block IP for 1 hour only for severe cases
                block_key = f'blocked_ip_{ip_hash}'
                cache.set(block_key, True, 3600)
                
                if request.path in ['/password-reset-request/']:
                    return JsonResponse({
                        'success': False,
                        'error': 'Suspicious activity detected. Request blocked.'
                    }, status=403)
                else:
                    from django.contrib import messages
                    from django.shortcuts import redirect
                    messages.error(request, 'Suspicious activity detected. Request blocked.')
                    return redirect('login')
        
        return None