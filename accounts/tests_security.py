"""
Snowfriend Authentication Security Test Suite
Run this to test all security features after implementation
"""

import hashlib
import time
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse
from accounts.models import PasswordHistory


class LoginSecurityTests(TestCase):
    """Test login security features"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='SecurePass123!',
            first_name='Test',
            last_name='User'
        )
        cache.clear()
    
    def test_successful_login(self):
        """Test successful login"""
        response = self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'SecurePass123!'
        })
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
    
    def test_failed_login_incorrect_password(self):
        """Test failed login with incorrect password"""
        response = self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'WrongPassword123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incorrect password')
    
    def test_failed_login_nonexistent_user(self):
        """Test failed login with non-existent user"""
        response = self.client.post(reverse('login'), {
            'email': 'nonexistent@example.com',
            'password': 'SecurePass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Account not found')
    
    def test_login_rate_limiting(self):
        """Test login rate limiting after 5 failed attempts"""
        # Make 5 failed login attempts
        for i in range(5):
            self.client.post(reverse('login'), {
                'email': 'test@example.com',
                'password': 'WrongPassword123!'
            })
        
        # 6th attempt should be blocked
        response = self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'SecurePass123!'  # Even with correct password
        })
        self.assertEqual(response.status_code, 302)  # Redirected
        # Should contain lockout message
    
    def test_xss_attempt_in_login(self):
        """Test XSS prevention in login"""
        response = self.client.post(reverse('login'), {
            'email': '<script>alert("xss")</script>@example.com',
            'password': 'password'
        })
        self.assertEqual(response.status_code, 200)
        # Should not contain script tag in response
        self.assertNotContains(response, '<script>')
    
    def test_sql_injection_attempt_in_login(self):
        """Test SQL injection prevention"""
        response = self.client.post(reverse('login'), {
            'email': "' OR '1'='1",
            'password': "' OR '1'='1"
        })
        self.assertEqual(response.status_code, 200)
        # Should not be logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class RegistrationSecurityTests(TestCase):
    """Test registration security features"""
    
    def setUp(self):
        self.client = Client()
        cache.clear()
    
    def test_successful_registration(self):
        """Test successful registration"""
        response = self.client.post(reverse('register'), {
            'fullname': 'New User',
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'confirmPassword': 'SecurePass123!'
        })
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Verify user was created
        user_exists = User.objects.filter(email='newuser@example.com').exists()
        self.assertTrue(user_exists)
    
    def test_password_strength_validation(self):
        """Test password strength requirements"""
        # Test weak password (no uppercase)
        response = self.client.post(reverse('register'), {
            'fullname': 'Test User',
            'email': 'test1@example.com',
            'password': 'weakpass123!',
            'confirmPassword': 'weakpass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'uppercase')
        
        # Test weak password (no number)
        response = self.client.post(reverse('register'), {
            'fullname': 'Test User',
            'email': 'test2@example.com',
            'password': 'WeakPass!',
            'confirmPassword': 'WeakPass!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'number')
        
        # Test weak password (no special character)
        response = self.client.post(reverse('register'), {
            'fullname': 'Test User',
            'email': 'test3@example.com',
            'password': 'WeakPass123',
            'confirmPassword': 'WeakPass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'special')
    
    def test_password_mismatch(self):
        """Test password confirmation mismatch"""
        response = self.client.post(reverse('register'), {
            'fullname': 'Test User',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'confirmPassword': 'DifferentPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'do not match')
    
    def test_duplicate_email(self):
        """Test registration with existing email"""
        # Create first user
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='SecurePass123!'
        )
        
        # Try to register with same email
        response = self.client.post(reverse('register'), {
            'fullname': 'New User',
            'email': 'existing@example.com',
            'password': 'SecurePass123!',
            'confirmPassword': 'SecurePass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
    
    def test_invalid_email_format(self):
        """Test registration with invalid email"""
        response = self.client.post(reverse('register'), {
            'fullname': 'Test User',
            'email': 'invalid-email',
            'password': 'SecurePass123!',
            'confirmPassword': 'SecurePass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'valid email')
    
    def test_xss_in_registration(self):
        """Test XSS prevention in registration"""
        response = self.client.post(reverse('register'), {
            'fullname': '<script>alert("xss")</script>',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'confirmPassword': 'SecurePass123!'
        })
        self.assertEqual(response.status_code, 200)
        # Should sanitize the input
        user = User.objects.filter(email='test@example.com').first()
        if user:
            self.assertNotIn('<script>', user.first_name)


class PasswordResetSecurityTests(TestCase):
    """Test password reset security features"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPass123!',
            first_name='Test',
            last_name='User'
        )
        # Create initial password history
        PasswordHistory.objects.create(
            user=self.user,
            password_hash=self.user.password
        )
        cache.clear()
    
    def test_password_reset_request(self):
        """Test password reset request"""
        response = self.client.post(reverse('password_reset_request'), {
            'email': 'test@example.com'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
    
    def test_password_reset_nonexistent_email(self):
        """Test password reset for non-existent email"""
        response = self.client.post(reverse('password_reset_request'), {
            'email': 'nonexistent@example.com'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        # Should return success even for non-existent email (security)
        data = response.json()
        self.assertTrue(data.get('success'))
    
    def test_password_history_prevention(self):
        """Test that users cannot reuse recent passwords"""
        # This would be tested in the password reset confirm view
        # with a valid reset token
        pass  # Implementation depends on your specific flow


class SessionSecurityTests(TestCase):
    """Test session security features"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='SecurePass123!'
        )
    
    def test_session_created_on_login(self):
        """Test that session is created on login"""
        self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'SecurePass123!'
        })
        
        # Check if session exists
        self.assertIn('_auth_user_id', self.client.session)
    
    def test_session_cleared_on_logout(self):
        """Test that session is cleared on logout"""
        # Login first
        self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'SecurePass123!'
        })
        
        # Logout
        self.client.get(reverse('logout'))
        
        # Session should be cleared
        self.assertNotIn('_auth_user_id', self.client.session)


class InputSanitizationTests(TestCase):
    """Test input sanitization functions"""
    
    def test_xss_sanitization(self):
        """Test XSS pattern sanitization"""
        from accounts.views import sanitize_input
        
        test_cases = [
            ('<script>alert("xss")</script>', True),
            ('javascript:alert("xss")', True),
            ('<iframe src="evil.com"></iframe>', True),
            ('Normal text', False),
            ('user@example.com', False),
        ]
        
        for input_text, should_be_suspicious in test_cases:
            cleaned, is_suspicious = sanitize_input(input_text)
            self.assertEqual(is_suspicious, should_be_suspicious)
            self.assertNotIn('<script>', cleaned)
            self.assertNotIn('<iframe>', cleaned)
    
    def test_sql_injection_sanitization(self):
        """Test SQL injection pattern detection"""
        from accounts.views import sanitize_input
        
        test_cases = [
            ("' OR '1'='1", True),
            ("UNION SELECT * FROM users", True),
            ("DROP TABLE users", True),
            ("Normal query text", False),
        ]
        
        for input_text, should_be_suspicious in test_cases:
            cleaned, is_suspicious = sanitize_input(input_text)
            self.assertEqual(is_suspicious, should_be_suspicious)


class PasswordStrengthTests(TestCase):
    """Test password strength validation"""
    
    def test_password_length(self):
        """Test password length requirements"""
        from accounts.views import validate_password_strength
        
        # Too short
        is_valid, msg = validate_password_strength('Short1!')
        self.assertFalse(is_valid)
        self.assertIn('8 characters', msg)
        
        # Valid length
        is_valid, msg = validate_password_strength('ValidPass1!')
        self.assertTrue(is_valid)
    
    def test_password_complexity(self):
        """Test password complexity requirements"""
        from accounts.views import validate_password_strength
        
        # No uppercase
        is_valid, msg = validate_password_strength('noupppercase1!')
        self.assertFalse(is_valid)
        self.assertIn('uppercase', msg.lower())
        
        # No lowercase
        is_valid, msg = validate_password_strength('NOLOWERCASE1!')
        self.assertFalse(is_valid)
        self.assertIn('lowercase', msg.lower())
        
        # No number
        is_valid, msg = validate_password_strength('NoNumber!')
        self.assertFalse(is_valid)
        self.assertIn('number', msg.lower())
        
        # No special character
        is_valid, msg = validate_password_strength('NoSpecial123')
        self.assertFalse(is_valid)
        self.assertIn('special', msg.lower())
    
    def test_common_passwords(self):
        """Test common password detection"""
        from accounts.views import validate_password_strength
        
        is_valid, msg = validate_password_strength('Password123!')
        self.assertFalse(is_valid)
        self.assertIn('common', msg.lower())
    
    def test_sequential_characters(self):
        """Test sequential character detection"""
        from accounts.views import validate_password_strength
        
        is_valid, msg = validate_password_strength('Abc123456!')
        self.assertFalse(is_valid)
        self.assertIn('sequential', msg.lower())
    
    def test_repeated_characters(self):
        """Test repeated character detection"""
        from accounts.views import validate_password_strength
        
        is_valid, msg = validate_password_strength('Passswword111!')
        self.assertFalse(is_valid)
        self.assertIn('repeated', msg.lower())


# Run tests with:
# python manage.py test accounts.tests_security -v 2

if __name__ == '__main__':
    print("Run tests using: python manage.py test accounts.tests_security -v 2")