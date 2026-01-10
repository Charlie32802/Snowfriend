# Security-Enhanced Settings for Snowfriend
# Add these configurations to your existing settings.py

from pathlib import Path
import os
import dj_database_url 
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY') 

DEBUG = os.getenv('DEBUG') == 'True'

ALLOWED_HOSTS = ['*'] if DEBUG else os.getenv('ALLOWED_HOSTS', '').split(',')

CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',  
    'https://*.ngrok.io',       
]

# ========================================
# ENHANCED AUTHENTICATION SECURITY
# ========================================

# Password Validation - MAXIMUM STRENGTH
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,  # Can increase to 12 for higher security
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Session Security - MAXIMUM PROTECTION
SESSION_COOKIE_SECURE = not DEBUG  # True in production (HTTPS only)
SESSION_COOKIE_HTTPONLY = True  # Prevents JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict'  # Prevents CSRF
SESSION_COOKIE_AGE = 3600  # 1 hour session timeout
SESSION_SAVE_EVERY_REQUEST = True  # Refresh session on each request
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Clear on browser close
SESSION_COOKIE_NAME = 'snowfriend_sessionid'  # Custom session cookie name

# Force session regeneration after login (add to LOGIN view)
# request.session.cycle_key()

# CSRF Security - MAXIMUM PROTECTION
CSRF_COOKIE_SECURE = not DEBUG  # True in production (HTTPS only)
CSRF_COOKIE_HTTPONLY = True  # Prevents JavaScript access
CSRF_COOKIE_SAMESITE = 'Strict'  # Prevents CSRF attacks
CSRF_USE_SESSIONS = True  # Store CSRF token in session instead of cookie
CSRF_FAILURE_VIEW = 'django.views.csrf.csrf_failure'
CSRF_COOKIE_NAME = 'snowfriend_csrftoken'  # Custom CSRF cookie name

# Additional CSRF Protection
CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS if DEBUG else []

# Security Headers - MAXIMUM PROTECTION
SECURE_BROWSER_XSS_FILTER = True  # Enable XSS filter
SECURE_CONTENT_TYPE_NOSNIFF = True  # Prevent MIME sniffing
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking

# HTTPS/SSL Security (Production Only)
if not DEBUG:
    SECURE_SSL_REDIRECT = True  # Redirect HTTP to HTTPS
    SECURE_HSTS_SECONDS = 31536000  # 1 year HSTS
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Additional production security
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Password Hashing - Use Argon2 for maximum security
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',  # Most secure
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',  # Fallback
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Note: Install argon2-cffi: pip install argon2-cffi

# Login/Logout URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'  # Changed from 'landing' for security

# File Upload Security
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Allowed file extensions for uploads
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

# ========================================
# MIDDLEWARE CONFIGURATION (SECURITY ENHANCED)
# ========================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Feedback Security Middleware
    'feedback.middleware.SecurityHeadersMiddleware',
    'feedback.middleware.FeedbackRateLimitMiddleware',
    'feedback.middleware.RequestSizeMiddleware',
    'feedback.middleware.SuspiciousActivityMiddleware',
    
    # Authentication Security Middleware
    'accounts.middleware.AuthenticationSecurityMiddleware',
    'accounts.middleware.LoginAttemptTrackingMiddleware',
    'accounts.middleware.RegistrationRateLimitMiddleware',
    'accounts.middleware.PasswordResetRateLimitMiddleware',
    'accounts.middleware.SuspiciousAuthActivityMiddleware',
    
    # Admin IP Whitelist Middleware
    'accounts.admin_ip_whitelist_middleware.AdminIPWhitelistMiddleware',
]

# ========================================
# CACHING CONFIGURATION
# ========================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'snowfriend-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
            'CULL_FREQUENCY': 4,  # Delete 1/4 of entries when max reached
        }
    }
}

# Cache timeout settings
CACHE_MIDDLEWARE_SECONDS = 0  # Disable caching for authenticated pages
CACHE_MIDDLEWARE_KEY_PREFIX = 'snowfriend'

# ========================================
# LOGGING CONFIGURATION (ENHANCED)
# ========================================

# Create logs directory
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] {levelname} {asctime} - {message}',
            'style': '{',
        },
        'auth': {
            'format': '[AUTH] {levelname} {asctime} - {message}',
            'style': '{',
        },
        'admin': {
            'format': '[ADMIN] {levelname} {asctime} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'feedback_security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'feedback_security.log',
            'formatter': 'security',
        },
        'feedback_validation_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'feedback_validation.log',
            'formatter': 'verbose',
        },
        'crisis_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'chatbot_crisis.log',
            'formatter': 'verbose',
        },
        'auth_security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'auth_security.log',
            'formatter': 'security',
        },
        'auth_activity_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'auth_activity.log',
            'formatter': 'auth',
        },
        'admin_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'admin_activity.log',
            'formatter': 'admin',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'feedback.security': {
            'handlers': ['feedback_security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'feedback.validation': {
            'handlers': ['feedback_validation_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'snowfriend.crisis': {
            'handlers': ['crisis_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'accounts.security': {
            'handlers': ['auth_security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'accounts.auth': {
            'handlers': ['auth_activity_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },

        'accounts.admin': {
            'handlers': ['admin_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ========================================
# EMAIL SECURITY
# ========================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'charlie.soniac.spencer@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'Snowfriend <no-reply@snowfriend.com>'

# Email security
EMAIL_TIMEOUT = 10  # Timeout for email sending (seconds)
EMAIL_USE_LOCALTIME = True

# ========================================
# ADDITIONAL SECURITY SETTINGS
# ========================================

# IP Hash Salt for rate limiting
FEEDBACK_IP_SALT = os.getenv('FEEDBACK_IP_SALT', 'snowfriend_feedback_salt_2025')

# Data retention
FEEDBACK_RETENTION_DAYS = 90
PASSWORD_HISTORY_RETENTION_COUNT = 3  # Keep last 3 passwords

# Rate limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Feedback rate limits (existing)
FEEDBACK_RATE_LIMIT_PER_MINUTE = 1
FEEDBACK_RATE_LIMIT_PER_HOUR = 5
FEEDBACK_RATE_LIMIT_PER_DAY = 3

# Authentication rate limits (NEW)
AUTH_MAX_LOGIN_ATTEMPTS = 5
AUTH_LOCKOUT_DURATION = 900  # 15 minutes in seconds
AUTH_MAX_REGISTRATION_PER_IP_HOUR = 3
AUTH_MAX_REGISTRATION_PER_IP_DAY = 5
AUTH_MAX_PASSWORD_RESET_PER_IP_HOUR = 3
AUTH_MAX_PASSWORD_RESET_PER_EMAIL_DAY = 5

# Trusted proxy configuration
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Content Security Policy (can be customized per view)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "data:")
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)

# Suspicious content detection
SUSPICIOUS_CONTENT_REVIEW_REQUIRED = True

# Custom admin URL (keep this secret!)
ADMIN_URL = 'admin-032802/'  # Your birthday: March 28, 2002

# Admin IP Whitelist - IMPORTANT: Update this for production!
ADMIN_IP_WHITELIST = [
    '127.0.0.1',      # Localhost IPv4
    '::1',            # Localhost IPv6
    # Add your production IPs here when deploying:
    # '203.0.113.45',   # Your office IP
    # '198.51.100.67',  # Your home IP
    # '192.168.1.100',  # Your VPN IP
]

# Admin session timeout (15 minutes - stricter than regular users)
ADMIN_SESSION_TIMEOUT = 900  # seconds

# ========================================
# INSTALLED APPS
# ========================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'accounts.apps.AccountsConfig', 
    'chatbot.apps.ChatbotConfig', 
    'feedback.apps.FeedbackConfig', 
]

# ========================================
# DATABASE
# ========================================

DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600
    )
}

# Database connection pooling for production
if not DEBUG:
    DATABASES['default']['CONN_MAX_AGE'] = 600
    DATABASES['default']['OPTIONS'] = {
        'connect_timeout': 10,
    }

# ========================================
# STATIC/MEDIA FILES
# ========================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ========================================
# INTERNATIONALIZATION
# ========================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ========================================
# TEMPLATES
# ========================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
            ],
        },
    },
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'