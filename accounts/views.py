"""
Enhanced Secure Authentication Views for Snowfriend
Maximum security implementation with comprehensive validation and protection
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, timedelta
import json
import re
import hashlib
import logging
from .models import PasswordHistory

# Loggers
security_logger = logging.getLogger('accounts.security')
auth_logger = logging.getLogger('accounts.auth')

# Security patterns
MALICIOUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'on\w+\s*=',
    r'<iframe[^>]*>',
    r'<object[^>]*>',
    r'eval\s*\(',
    r'vbscript:',
    r'data:text/html',
]

SQL_PATTERNS = [
    r'(\bUNION\b.*\bSELECT\b)',
    r'(\bSELECT\b.*\bFROM\b)',
    r'(\bINSERT\b.*\bINTO\b)',
    r'(\bDELETE\b.*\bFROM\b)',
    r'(\bDROP\b.*\bTABLE\b)',
    r"('|\")(.*)(OR|AND)(.*)(=)",
]


def sanitize_input(text):
    """
    Sanitize user input to prevent XSS and injection attacks
    Returns: (cleaned_text, is_suspicious)
    """
    if not text:
        return "", False
    
    suspicious = False
    original_text = text
    
    # Check for malicious patterns
    for pattern in MALICIOUS_PATTERNS + SQL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            suspicious = True
            security_logger.warning(
                f"Malicious pattern detected: {pattern} in input: {text[:30]}..."
            )
    
    # Remove HTML tags
    text = re.sub(r'<[^>]*>', '', text)
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    # Remove non-printable characters
    text = ''.join(char for char in text if char.isprintable() or char.isspace())
    
    return text.strip(), suspicious


def validate_password_strength(password):
    """
    Validate password strength with comprehensive checks
    Returns: (is_valid, error_message)
    
    FIXED: Smart hybrid checking for common passwords
    """
    if not password:
        return False, "Password is required."
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    
    if len(password) > 128:
        return False, "Password is too long (max 128 characters)."
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number."
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character (!@#$%^&* etc.)."
    
    # FIXED: Smart common password checking
    password_lower = password.lower()
    
    # Very common base words - check as substring (catches variations)
    very_common_bases = ['password', 'qwerty', '12345678', 'letmein', 'welcome', 'monkey']
    for base in very_common_bases:
        if base in password_lower:
            return False, "This password is too common. Please choose a stronger password."
    
    # Specific weak patterns - exact match only
    weak_patterns = ['admin123', 'password1', 'password123']
    if password_lower in weak_patterns:
        return False, "This password is too common. Please choose a stronger password."

    # Only catches 4+ sequential chars (so 'Abc123456!' gets caught here, not above)
    if re.search(r'(0123|1234|2345|3456|4567|5678|6789|abcd|bcde|cdef)', password_lower):
        return False, "Password should not contain long sequential characters."
    
    # Check for repeated characters (3 or more in a row)
    if re.search(r'(.)\1{2,}', password):
        return False, "Password should not contain repeated characters (e.g., 'aaa', '111')."
    
    return True, ""


def get_client_ip(request):
    """Get client IP address securely"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            return ip
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def landing_page(request):
    """Landing page view"""
    return render(request, 'landing_page.html')


@csrf_protect
def login_page(request):
    """
    Enhanced secure login with comprehensive validation
    """
    # Redirect authenticated users
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email_or_username = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        # Input validation
        if not email_or_username or not password:
            messages.error(request, 'Please provide both email/username and password.')
            return render(request, 'login.html')
        
        # Sanitize inputs
        email_or_username_clean, suspicious_email = sanitize_input(email_or_username)
        _, suspicious_password = sanitize_input(password)
        
        if suspicious_email or suspicious_password:
            security_logger.critical(
                f"SUSPICIOUS LOGIN ATTEMPT from IP: {get_client_ip(request)[:10]}... "
                f"Email/Username: {email_or_username_clean[:10]}..."
            )
            messages.error(request, 'Invalid login attempt detected.')
            return render(request, 'login.html')
        
        # Length validation
        if len(email_or_username_clean) > 254:
            messages.error(request, 'Invalid email or username.')
            return render(request, 'login.html')
        
        if len(password) > 128:
            messages.error(request, 'Invalid password.')
            return render(request, 'login.html')
        
        # Try to authenticate with username first
        user = authenticate(request, username=email_or_username_clean, password=password)
        
        # If that fails, try to find user by email
        if user is None:
            try:
                user_obj = User.objects.get(email=email_or_username_clean)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user is not None:
            # Check if account is active
            if not user.is_active:
                security_logger.warning(
                    f"Login attempt for inactive account: {user.username} "
                    f"from IP: {get_client_ip(request)[:10]}..."
                )
                messages.error(request, 'This account has been deactivated. Please contact support.')
                return render(request, 'login.html')
            
            # Successful login
            login(request, user)
            
            # Clear failed login attempts
            ip_hash = hashlib.sha256(get_client_ip(request).encode()).hexdigest()
            cache.delete(f'login_attempts_ip_{ip_hash}')
            
            user_hash = hashlib.sha256(email_or_username_clean.lower().encode()).hexdigest()
            cache.delete(f'login_attempts_user_{user_hash}')
            
            auth_logger.info(
                f"Successful login: {user.username} from IP: {get_client_ip(request)[:10]}..."
            )
            
            messages.success(request, 'You have successfully logged in.')
            
            # Redirect to next parameter or dashboard
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            # Failed login - determine specific error message
            try:
                # Try by username
                user_obj = User.objects.filter(username=email_or_username_clean).first()
                if not user_obj:
                    # Try by email
                    user_obj = User.objects.filter(email=email_or_username_clean).first()
                
                if user_obj:
                    # User exists, so password is wrong
                    auth_logger.warning(
                        f"Failed login - incorrect password for: {email_or_username_clean[:3]}*** "
                        f"from IP: {get_client_ip(request)[:10]}..."
                    )
                    messages.error(request, 'Incorrect password. Please try again or reset your password.')
                else:
                    # User doesn't exist
                    auth_logger.warning(
                        f"Failed login - account not found: {email_or_username_clean[:3]}*** "
                        f"from IP: {get_client_ip(request)[:10]}..."
                    )
                    messages.error(request, 'Account not found. Please check your credentials or create a new account.')
            except Exception as e:
                security_logger.error(f"Error during login validation: {str(e)}")
                messages.error(request, 'Invalid email/username or password.')
    
    return render(request, 'login.html')


@csrf_protect
def register_page(request):
    """
    Enhanced secure registration with comprehensive validation
    """
    # Redirect authenticated users
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        fullname = request.POST.get('fullname', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirmPassword', '')
        
        # Input validation
        if not all([fullname, email, password, confirm_password]):
            messages.error(request, 'All fields are required.')
            return render(request, 'register.html')
        
        # Sanitize inputs
        fullname_clean, suspicious_name = sanitize_input(fullname)
        email_clean, suspicious_email = sanitize_input(email)
        
        if suspicious_name or suspicious_email:
            security_logger.critical(
                f"SUSPICIOUS REGISTRATION ATTEMPT from IP: {get_client_ip(request)[:10]}... "
                f"Email: {email_clean[:10]}..."
            )
            messages.error(request, 'Invalid registration data detected.')
            return render(request, 'register.html')
        
        # Validate email format
        try:
            validate_email(email_clean)
        except ValidationError:
            messages.error(request, 'Please enter a valid email address.')
            return render(request, 'register.html')
        
        # Length validations
        if len(fullname_clean) < 2:
            messages.error(request, 'Full name must be at least 2 characters long.')
            return render(request, 'register.html')
        
        if len(fullname_clean) > 150:
            messages.error(request, 'Full name is too long (max 150 characters).')
            return render(request, 'register.html')
        
        if len(email_clean) > 254:
            messages.error(request, 'Email address is too long.')
            return render(request, 'register.html')
        
        # Validate full name contains only letters and spaces
        if not re.match(r'^[a-zA-Z\s\'-]+$', fullname_clean):
            messages.error(request, 'Full name should only contain letters, spaces, hyphens, and apostrophes.')
            return render(request, 'register.html')
        
        # Password validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'register.html')
        
        # Strong password validation
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            messages.error(request, error_msg)
            return render(request, 'register.html')
        
        # Check if email already exists
        if User.objects.filter(email=email_clean).exists():
            auth_logger.warning(
                f"Registration attempt with existing email: {email_clean[:3]}*** "
                f"from IP: {get_client_ip(request)[:10]}..."
            )
            messages.error(request, 'An account with this email already exists. Please login instead.')
            return render(request, 'register.html')
        
        # Check for disposable email domains (optional but recommended)
        disposable_domains = [
            'tempmail.com', 'throwaway.email', '10minutemail.com',
            'guerrillamail.com', 'mailinator.com', 'trashmail.com'
        ]
        email_domain = email_clean.split('@')[-1]
        if email_domain in disposable_domains:
            security_logger.warning(
                f"Registration attempt with disposable email: {email_clean[:3]}*** "
                f"from IP: {get_client_ip(request)[:10]}..."
            )
            messages.error(request, 'Please use a valid, non-disposable email address.')
            return render(request, 'register.html')
        
        # Create username from email
        username = email_clean.split('@')[0]
        # Remove any non-alphanumeric characters
        username = re.sub(r'[^a-zA-Z0-9]', '', username)
        
        if not username:
            username = 'user'
        
        base_username = username[:30]  # Limit to 30 chars
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
            if counter > 1000:  # Prevent infinite loop
                security_logger.error("Username generation exceeded limit")
                messages.error(request, 'Unable to create account. Please try again.')
                return render(request, 'register.html')
        
        # Split fullname into first and last name
        name_parts = fullname_clean.strip().split(' ', 1)
        first_name = name_parts[0][:30]  # Limit to 30 chars
        last_name = name_parts[1][:150] if len(name_parts) > 1 else ''
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email_clean,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Store initial password in history
            PasswordHistory.objects.create(
                user=user,
                password_hash=user.password
            )
            
            auth_logger.info(
                f"New user registered: {username} ({email_clean[:3]}***) "
                f"from IP: {get_client_ip(request)[:10]}..."
            )
            
            # Send welcome email (optional)
            try:
                send_mail(
                    subject='Welcome to Snowfriend!',
                    message=f'Hello {first_name},\n\nWelcome to Snowfriend! Your account has been successfully created.\n\nStay well,\nThe Snowfriend Team',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email_clean],
                    fail_silently=True,
                )
            except Exception as e:
                security_logger.error(f"Failed to send welcome email: {str(e)}")
            
            # Redirect to login with success message
            messages.success(request, 'Your account has been successfully created! Please log in.')
            return redirect('login')
            
        except Exception as e:
            security_logger.error(f"Registration error: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred during registration. Please try again.')
            return render(request, 'register.html')
    
    return render(request, 'register.html')


@login_required(login_url='login')
def dashboard(request):
    """Dashboard view"""
    return render(request, 'dashboard.html')


@login_required(login_url='login')
def logout_view(request):
    """
    Secure logout with session cleanup
    """
    username = request.user.username
    
    # Clear session data
    request.session.flush()
    
    # Logout user
    logout(request)
    
    auth_logger.info(f"User logged out: {username}")
    
    messages.info(request, 'You have been securely logged out.')
    return redirect('login')


@login_required(login_url='login')
def chat_page(request):
    """Chat page view"""
    return render(request, 'chat.html')


@require_http_methods(["POST"])
@csrf_protect
def password_reset_request(request):
    """
    Enhanced secure password reset request
    """
    try:
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            return JsonResponse({
                'success': False,
                'message': 'Please enter your email address'
            })
        
        # Sanitize email
        email_clean, suspicious = sanitize_input(email)
        
        if suspicious:
            security_logger.critical(
                f"SUSPICIOUS PASSWORD RESET REQUEST from IP: {get_client_ip(request)[:10]}... "
                f"Email: {email_clean[:10]}..."
            )
            return JsonResponse({
                'success': False,
                'message': 'Invalid request detected.'
            }, status=400)
        
        # Validate email format
        try:
            validate_email(email_clean)
        except ValidationError:
            return JsonResponse({
                'success': False,
                'message': 'Please enter a valid email address'
            })
        
        # Check if user exists
        try:
            user = User.objects.get(email=email_clean)
        except User.DoesNotExist:
            # Return success even if user doesn't exist (security best practice)
            auth_logger.warning(
                f"Password reset requested for non-existent email: {email_clean[:3]}*** "
                f"from IP: {get_client_ip(request)[:10]}..."
            )
            return JsonResponse({
                'success': True,
                'message': 'If an account with that email exists, you will receive a password reset link.'
            })
        
        # Check if account is active
        if not user.is_active:
            security_logger.warning(
                f"Password reset requested for inactive account: {user.username} "
                f"from IP: {get_client_ip(request)[:10]}..."
            )
            return JsonResponse({
                'success': True,
                'message': 'If an account with that email exists, you will receive a password reset link.'
            })
        
        # Generate password reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build password reset URL
        reset_url = request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )
        
        # Send password reset email
        subject = 'Reset Your Snowfriend Password'
        message = f"""
Hello {user.first_name},

You recently requested to reset your password for your Snowfriend account. Click the link below to reset it:

{reset_url}

This link will expire in 24 hours for security reasons.

If you did not request a password reset, please ignore this email or contact support if you're concerned about your account security.

Stay well,
The Snowfriend Team
        """
        
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="background-color: #4a6b8a; padding: 30px 20px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">Reset Your Password</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 30px; background-color: #f9f9f9;">
                            <p style="margin: 0 0 15px 0; color: #333; font-size: 16px;">Hello {user.first_name},</p>
                            <p style="margin: 0 0 15px 0; color: #333; font-size: 16px;">You recently requested to reset your password for your Snowfriend account.</p>
                            <p style="margin: 0 0 25px 0; color: #333; font-size: 16px;">Click the button below to reset it:</p>
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding: 20px 0;">
                                        <a href="{reset_url}" style="display: inline-block; padding: 14px 40px; background-color: #4a6b8a; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-size: 16px; font-weight: 600; text-align: center;">Reset Password</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin: 25px 0 15px 0; color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
                            <p style="margin: 0 0 25px 0; word-break: break-all; color: #4a6b8a; font-size: 14px;">{reset_url}</p>
                            <p style="margin: 0 0 15px 0; color: #333; font-size: 16px;">This link will expire in 24 hours for security reasons.</p>
                            <p style="margin: 0 0 15px 0; color: #333; font-size: 16px;">If you did not request a password reset, please ignore this email or contact support if you're concerned about your account security.</p>
                            <p style="margin: 25px 0 0 0; color: #333; font-size: 16px;">Stay well,<br><strong>The Snowfriend Team</strong></p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 20px; text-align: center; background-color: #f4f4f4; border-top: 1px solid #e0e0e0;">
                            <p style="margin: 0; color: #999; font-size: 12px;">This is an automated message from Snowfriend. Please do not reply to this email.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_clean],
                html_message=html_message,
                fail_silently=False,
            )
            
            auth_logger.info(
                f"Password reset email sent to: {email_clean[:3]}*** "
                f"from IP: {get_client_ip(request)[:10]}..."
            )
            
        except Exception as e:
            security_logger.error(f"Email sending error: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': 'Unable to send reset email. Please try again later.'
            })
        
        return JsonResponse({
            'success': True,
            'message': 'Password reset link has been sent to your email.'
        })
        
    except Exception as e:
        security_logger.error(f"Password reset error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again later.'
        })


@csrf_protect
def password_reset_confirm(request, uidb64, token):
    """
    Enhanced secure password reset confirmation with history validation
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # Check if token is valid
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            # Validation
            if not new_password or not confirm_password:
                messages.error(request, 'Please fill in all fields.')
                return render(request, 'password_update.html', {'valid_link': True})
            
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'password_update.html', {'valid_link': True})
            
            # Strong password validation
            is_valid, error_msg = validate_password_strength(new_password)
            if not is_valid:
                messages.error(request, error_msg)
                return render(request, 'password_update.html', {'valid_link': True})
            
            # Check if new password is same as current password
            if check_password(new_password, user.password):
                messages.error(request, 'Your new password cannot be the same as your current password. Please choose a different password.')
                return render(request, 'password_update.html', {'valid_link': True})
            
            # Check password history (prevent reuse of last 3 passwords)
            password_history = PasswordHistory.objects.filter(user=user).order_by('-created_at')[:3]
            for old_password in password_history:
                if check_password(new_password, old_password.password_hash):
                    messages.error(request, 'You cannot reuse any of your last 3 passwords. Please choose a different password.')
                    return render(request, 'password_update.html', {'valid_link': True})
            
            # Store old password hash before updating
            old_password_hash = user.password
            
            # Update password
            user.set_password(new_password)
            user.save()
            
            # Store password history
            PasswordHistory.objects.create(
                user=user,
                password_hash=old_password_hash
            )
            
            # Clean up old password history (keep only last 3)
            old_passwords = PasswordHistory.objects.filter(user=user).order_by('-created_at')[3:]
            for old_pass in old_passwords:
                old_pass.delete()
            
            auth_logger.info(
                f"Password reset completed for user: {user.username} "
                f"from IP: {get_client_ip(request)[:10]}..."
            )
            
            # Invalidate all sessions for this user (force re-login)
            from django.contrib.sessions.models import Session
            from django.utils import timezone as django_timezone
            
            for session in Session.objects.filter(expire_date__gte=django_timezone.now()):
                session_data = session.get_decoded()
                if session_data.get('_auth_user_id') == str(user.id):
                    session.delete()
            
            # Redirect to login with success message
            messages.success(request, 'Your password has been successfully updated. Please log in with your new password.')
            return redirect('login')
        
        # Display password reset form
        return render(request, 'password_update.html', {'valid_link': True})
    else:
        # Invalid or expired token
        security_logger.warning(
            f"Invalid password reset token attempted from IP: {get_client_ip(request)[:10]}..."
        )
        return render(request, 'password_update.html', {'valid_link': False})