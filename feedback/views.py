from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
from django.utils.html import escape
from .models import Feedback
import re
import logging

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

try:
    from PIL import Image
    from io import BytesIO
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger('feedback.validation')
security_logger = logging.getLogger('feedback.security')

MALICIOUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'on\w+\s*=',
    r'<iframe[^>]*>.*?</iframe>',
    r'<object[^>]*>.*?</object>',
    r'<embed[^>]*>',
    r'eval\s*\(',
    r'expression\s*\(',
    r'vbscript:',
    r'data:text/html',
    r'<link[^>]*>',
    r'<meta[^>]*>',
    r'<base[^>]*>',
    r'<!--.*?-->',
]

SQL_PATTERNS = [
    r'(\bUNION\b.*\bSELECT\b)',
    r'(\bSELECT\b.*\bFROM\b)',
    r'(\bINSERT\b.*\bINTO\b)',
    r'(\bDELETE\b.*\bFROM\b)',
    r'(\bUPDATE\b.*\bSET\b)',
    r'(\bDROP\b.*\bTABLE\b)',
    r'(--|\#|\/\*)',
    r"('|\")(.*)(OR|AND)(.*)(=|LIKE)",
]

COMMAND_PATTERNS = [
    r'[;&|`$]',
    r'\$\(.*\)',
    r'`.*`',
]


def sanitize_input(text):
    if not text:
        return "", False

    suspicious = False

    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            suspicious = True
            security_logger.warning("Malicious pattern detected in feedback")

    for pattern in SQL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            suspicious = True
            security_logger.warning("SQL injection pattern detected in feedback")

    for pattern in COMMAND_PATTERNS:
        if re.search(pattern, text):
            suspicious = True
            security_logger.warning("Command injection pattern detected in feedback")

    text = re.sub(r'<[^>]*>', '', text)
    text = escape(text)
    text = text.replace('\x00', '')
    text = ' '.join(text.split())
    text = ''.join(char for char in text if char.isprintable() or char.isspace())

    return text.strip(), suspicious


def validate_image_content(image_file):
    if not HAS_PIL:
        security_logger.warning("PIL not available - using basic image validation")
        return True

    try:
        image_file.seek(0)

        if HAS_MAGIC:
            mime = magic.from_buffer(image_file.read(2048), mime=True)
            image_file.seek(0)

            allowed_mimes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if mime not in allowed_mimes:
                security_logger.warning(f"Invalid file type detected: {mime}")
                return False

        try:
            img = Image.open(image_file)
            img.verify()
            image_file.seek(0)

            img = Image.open(image_file)

            if img.size[0] * img.size[1] > 178956970:
                security_logger.warning(f"Image too large: {img.size}")
                return False

            image_file.seek(0)
            return True

        except Exception as e:
            security_logger.warning(f"Image validation failed: {str(e)}")
            return False

    except Exception as e:
        security_logger.warning(f"File validation error: {str(e)}")
        return False


def sanitize_filename(filename):
    if not filename:
        return "unnamed"

    filename = filename.split('/')[-1].split('\\')[-1]
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = filename.strip('. ')

    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:95] + ('.' + ext if ext else '')

    return filename or "unnamed"


def check_advanced_rate_limit(ip_hash):
    from django.utils import timezone
    from datetime import timedelta

    if not ip_hash:
        return False, None

    now = timezone.now()

    limits = [
        (1, 1/60, "Please wait at least 1 minute between submissions."),
        (5, 1, "Maximum 5 submissions per hour. Please try again later."),
        (3, 24, "Maximum 3 submissions per day. Please try again tomorrow."),
    ]

    for limit, hours, message in limits:
        time_threshold = now - timedelta(hours=hours)
        recent_count = Feedback.objects.filter(
            ip_address_hash=ip_hash,
            created_at__gte=time_threshold
        ).count()

        if recent_count >= limit:
            security_logger.warning(f"Rate limit exceeded: {recent_count} submissions in {hours} hours")
            return True, message

    return False, None


@require_http_methods(["POST"])
@csrf_protect
def submit_feedback(request):
    try:
        content_length = request.META.get('CONTENT_LENGTH')
        if content_length:
            try:
                content_length = int(content_length)
                if content_length > 10 * 1024 * 1024:
                    security_logger.warning(f"Request size too large: {content_length} bytes")
                    return JsonResponse({
                        'success': False,
                        'error': 'Request size too large.'
                    }, status=400)
            except (ValueError, TypeError):
                pass

        client_ip = get_client_ip(request)
        ip_hash = Feedback.hash_ip_address(client_ip)

        is_limited, limit_message = check_advanced_rate_limit(ip_hash)
        if is_limited:
            return JsonResponse({
                'success': False,
                'error': limit_message
            }, status=429)

        rating = request.POST.get('rating', '').strip()
        message = request.POST.get('message', '').strip()
        image = request.FILES.get('image')

        if not rating or not message:
            return JsonResponse({
                'success': False,
                'error': 'Rating and message are required.'
            }, status=400)

        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError("Rating out of range")
        except (ValueError, TypeError):
            security_logger.warning(f"Invalid rating: {rating}")
            return JsonResponse({
                'success': False,
                'error': 'Rating must be between 1 and 5.'
            }, status=400)

        if len(message) > 1000:
            return JsonResponse({
                'success': False,
                'error': 'Message must be 1000 characters or less.'
            }, status=400)

        if not message:
            return JsonResponse({
                'success': False,
                'error': 'Message cannot be empty.'
            }, status=400)

        clean_message, is_suspicious = sanitize_input(message)

        if not clean_message:
            return JsonResponse({
                'success': False,
                'error': 'Invalid message content.'
            }, status=400)

        if is_suspicious:
            security_logger.warning(f"Suspicious content detected from IP hash: {ip_hash[:8]}...")

        if image:
            if image.size > 5 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'error': 'Image size must be less than 5MB.'
                }, status=400)

            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if image.content_type not in allowed_types:
                return JsonResponse({
                    'success': False,
                    'error': 'Only PNG, JPG, GIF, and WebP images are allowed.'
                }, status=400)

            if not validate_image_content(image):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid or corrupted image file.'
                }, status=400)

            image.name = sanitize_filename(image.name)

            if HAS_PIL:
                try:
                    img = Image.open(image)

                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background

                    output = BytesIO()
                    img.save(output, format='JPEG', quality=85, optimize=True)
                    output.seek(0)

                    from django.core.files.uploadedfile import InMemoryUploadedFile
                    image = InMemoryUploadedFile(
                        output,
                        'ImageField',
                        f"{sanitize_filename(image.name.rsplit('.', 1)[0])}.jpg",
                        'image/jpeg',
                        output.getbuffer().nbytes,
                        None
                    )

                except Exception as e:
                    security_logger.warning(f"Image processing failed: {str(e)}")
                    return JsonResponse({
                        'success': False,
                        'error': 'Failed to process image.'
                    }, status=400)

        feedback = Feedback.objects.create(
            rating=rating,
            message=clean_message,
            image=image if image else None,
            ip_address_hash=ip_hash,
            is_suspicious=is_suspicious
        )

        logger.info(f"Feedback submitted: ID {feedback.feedback_id}, Rating: {rating}, Suspicious: {is_suspicious}")

        return JsonResponse({
            'success': True,
            'message': 'Thank you for your feedback!'
        })

    except ValidationError as e:
        security_logger.warning(f"Validation error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Invalid data submitted.'
        }, status=400)

    except Exception as e:
        security_logger.error(f"Unexpected error in feedback submission: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred. Please try again later.'
        }, status=500)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            return ip
    return request.META.get('REMOTE_ADDR', '0.0.0.0')