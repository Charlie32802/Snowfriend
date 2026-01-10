from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime
import json
from .models import PasswordHistory

def landing_page(request):
    return render(request, 'landing_page.html')

def login_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email_or_username = request.POST.get('email')
        password = request.POST.get('password')
        
        # Try to authenticate with username first
        user = authenticate(request, username=email_or_username, password=password)
        
        # If that fails, try to find user by email
        if user is None:
            try:
                user_obj = User.objects.get(email=email_or_username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user is not None:
            login(request, user)
            messages.success(request, 'You have successfully logged in.')
            return redirect('dashboard')
        else:
            # Check if user exists and provide appropriate error message
            try:
                # Try by username
                user_obj = User.objects.filter(username=email_or_username).first()
                if not user_obj:
                    # Try by email
                    user_obj = User.objects.filter(email=email_or_username).first()
                
                if user_obj:
                    # User exists, so password is wrong
                    messages.error(request, 'Incorrect password. Please try again or reset your password.')
                else:
                    # User doesn't exist
                    messages.error(request, 'Account not found. Please check your credentials or create a new account.')
            except:
                messages.error(request, 'Invalid email/username or password.')
    
    return render(request, 'login.html')

def register_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmPassword')
        
        # Basic validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'register.html')
        
        # Create username from email
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Split fullname into first and last name
        name_parts = fullname.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
    
        PasswordHistory.objects.create(
            user=user,
            password_hash=user.password
        )
        
        # Redirect to login with success message
        messages.success(request, 'Your account has been successfully registered. Please log in.')
        return redirect('login')
    
    return render(request, 'register.html')

@login_required(login_url='login')
def dashboard(request):
    return render(request, 'dashboard.html')

@login_required(login_url='login')
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')

@login_required(login_url='login')
def chat_page(request):
    return render(request, 'chat.html')

@require_http_methods(["POST"])
def password_reset_request(request):
    """Handle password reset request from modal"""
    try:
        email = request.POST.get('email', '').strip()
        
        if not email:
            return JsonResponse({
                'success': False,
                'message': 'Please enter your email address'
            })
        
        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Return success even if user doesn't exist (security best practice)
            return JsonResponse({
                'success': True,
                'message': 'If an account with that email exists, you will receive a password reset link.'
            })
        
        # Generate password reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build password reset URL (production-ready)
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

If you did not request a password reset, please ignore this email. Your password will remain unchanged.

Stay well,
The Snowfriend Team
        """
        
        # HTML email with FIXED button styling
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
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #4a6b8a; padding: 30px 20px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">Reset Your Password</h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px; background-color: #f9f9f9;">
                            <p style="margin: 0 0 15px 0; color: #333; font-size: 16px;">Hello {user.first_name},</p>
                            <p style="margin: 0 0 15px 0; color: #333; font-size: 16px;">You recently requested to reset your password for your Snowfriend account.</p>
                            <p style="margin: 0 0 25px 0; color: #333; font-size: 16px;">Click the button below to reset it:</p>
                            
                            <!-- Button -->
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
                            <p style="margin: 0 0 15px 0; color: #333; font-size: 16px;">If you did not request a password reset, please ignore this email. Your password will remain unchanged.</p>
                            <p style="margin: 25px 0 0 0; color: #333; font-size: 16px;">Stay well,<br><strong>Marc Daryll Trinidad</strong></p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
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
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Email sending error: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Unable to send reset email. Please try again later.'
            })
        
        return JsonResponse({
            'success': True,
            'message': 'Password reset link has been sent to your email.'
        })
        
    except Exception as e:
        print(f"Password reset error: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again later.'
        })

def password_reset_confirm(request, uidb64, token):
    """Display password reset form with history validation"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # Check if token is valid
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Validation
            if not new_password or not confirm_password:
                messages.error(request, 'Please fill in all fields.')
                return render(request, 'password_update.html', {'valid_link': True})
            
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'password_update.html', {'valid_link': True})
            
            if len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
                return render(request, 'password_update.html', {'valid_link': True})
            
            # Check if new password is same as current password
            if check_password(new_password, user.password):
                messages.error(request, 'Your new password cannot be the same as your current password. Please choose a different password.')
                return render(request, 'password_update.html', {'valid_link': True})
            
            # Check if password matches previous password
            last_password = PasswordHistory.objects.filter(user=user).first()
            if last_password and check_password(new_password, last_password.password_hash):
                messages.error(request, 'You cannot reuse your previous password. Please choose a different password.')
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
            old_passwords = PasswordHistory.objects.filter(user=user)[3:]
            for old_pass in old_passwords:
                old_pass.delete()
            
            # Redirect to login with success message
            messages.success(request, 'Your password has been successfully updated. You may now log in with your new password.')
            return redirect('login')
        
        # Display password reset form
        return render(request, 'password_update.html', {'valid_link': True})
    else:
        # Invalid or expired token
        return render(request, 'password_update.html', {'valid_link': False})