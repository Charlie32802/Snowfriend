#timezone_utils.py
"""
Timezone utilities for Snowfriend
Provides current time awareness based on user's location
"""

from datetime import datetime
from django.utils import timezone
import pytz

def get_user_current_time(user_timezone='Asia/Manila'):
    """
    Get current time in user's timezone
    
    Args:
        user_timezone: IANA timezone string (e.g., 'Asia/Manila', 'America/New_York')
    
    Returns:
        datetime object in user's timezone
    """
    # Get current UTC time
    utc_now = timezone.now()
    
    # Convert to user's timezone
    user_tz = pytz.timezone(user_timezone)
    user_time = utc_now.astimezone(user_tz)
    
    return user_time

def format_time_for_user(user_timezone='Asia/Manila'):
    """
    Format current time in user-friendly way
    
    Returns:
        String like "2:45 PM" or "10:30 AM"
    """
    user_time = get_user_current_time(user_timezone)
    # Remove leading zero from hour
    return user_time.strftime('%I:%M %p').lstrip('0')  # "2:45 PM" not "02:45 PM"

def format_datetime_for_user(user_timezone='Asia/Manila'):
    """
    Format current date and time
    
    Returns:
        String like "Monday, December 23, 2025 at 2:45 PM"
    """
    user_time = get_user_current_time(user_timezone)
    time_str = user_time.strftime('%I:%M %p').lstrip('0')
    date_str = user_time.strftime('%A, %B %d, %Y')
    return f"{date_str} at {time_str}"

def get_time_context(user_timezone='Asia/Manila'):
    """
    Get contextual time info for system prompt
    
    Returns:
        Dict with time info:
        - current_time: "2:45 PM"
        - current_date: "Monday, December 23, 2025"
        - time_of_day: "afternoon"
        - hour: 14
        - datetime_full: "Monday, December 23, 2025 at 2:45 PM"
    """
    user_time = get_user_current_time(user_timezone)
    
    hour = user_time.hour
    
    # Determine time of day
    if 5 <= hour < 12:
        time_of_day = 'morning'
    elif 12 <= hour < 17:
        time_of_day = 'afternoon'
    elif 17 <= hour < 21:
        time_of_day = 'evening'
    else:
        time_of_day = 'night'
    
    return {
        'current_time': format_time_for_user(user_timezone),
        'current_date': user_time.strftime('%A, %B %d, %Y'),
        'time_of_day': time_of_day,
        'hour': hour,
        'datetime_full': format_datetime_for_user(user_timezone)
    }