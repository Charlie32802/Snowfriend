from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Feedback


@require_http_methods(["POST"])
def submit_feedback(request):
    """
    Handle feedback submission from the landing page.
    Accepts: rating (1-5), message (text), and optional image upload.
    All submissions are anonymous with privacy-friendly IP hashing.
    Rate limit: 3 submissions per day
    """
    try:
        # Get client IP and hash it for privacy
        client_ip = get_client_ip(request)
        ip_hash = Feedback.hash_ip_address(client_ip)
        
        # Check rate limit (3 submissions per day)
        if Feedback.check_rate_limit(ip_hash, limit=3, hours=24):
            return JsonResponse({
                'success': False,
                'error': 'You have reached the daily feedback limit (3 per day). Please try again tomorrow.'
            }, status=429)
        
        # Get form data
        rating = request.POST.get('rating')
        message = request.POST.get('message')
        image = request.FILES.get('image')

        # Validate required fields
        if not rating or not message:
            return JsonResponse({
                'success': False,
                'error': 'Rating and message are required.'
            }, status=400)

        # Validate rating
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Rating must be a number between 1 and 5.'
            }, status=400)

        # Validate message
        message = message.strip()
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'Message cannot be empty.'
            }, status=400)
            
        if len(message) > 1000:
            return JsonResponse({
                'success': False,
                'error': 'Message must be 1000 characters or less.'
            }, status=400)

        # Validate image if present
        if image:
            # Validate image size (5MB limit)
            if image.size > 5 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'error': 'Image size must be less than 5MB.'
                }, status=400)

            # Validate image type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if image.content_type not in allowed_types:
                return JsonResponse({
                    'success': False,
                    'error': 'Only PNG, JPG, GIF, and WebP images are allowed.'
                }, status=400)

        # Create feedback entry - let Django handle the image upload
        feedback = Feedback.objects.create(
            rating=rating,
            message=message,
            image=image if image else None,  # Pass the file object directly
            ip_address_hash=ip_hash  # Store hashed IP, not the actual IP
        )

        return JsonResponse({
            'success': True,
            'message': 'Thank you for your feedback!'
        })

    except Exception as e:
        # Log the error
        print(f"Error submitting feedback: {str(e)}")
        
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.'
        }, status=500)

        
def get_client_ip(request):
    """
    Get the client's IP address from the request.
    Handles both direct connections and proxied requests.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get the first IP in the chain (client's real IP)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip