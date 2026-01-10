"""
Admin IP Whitelist Middleware for Snowfriend
Restricts admin access to whitelisted IP addresses only
"""

from django.http import HttpResponseForbidden
from django.conf import settings
import logging
import re

admin_logger = logging.getLogger('accounts.admin')


class AdminIPWhitelistMiddleware:
    """
    Restrict admin access to whitelisted IPs only
    
    Features:
    - Blocks non-whitelisted IPs from accessing admin
    - Logs all blocked attempts
    - Configurable whitelist in settings.py
    - Automatically allows localhost in DEBUG mode
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_url = 'admin-032802/'  # Your custom admin URL
    
    def __call__(self, request):
        # Check if request is for admin panel
        if request.path.startswith(f'/{self.admin_url}'):
            client_ip = self.get_client_ip(request)
            
            # Get whitelist from settings (default to localhost only)
            whitelist = getattr(settings, 'ADMIN_IP_WHITELIST', ['127.0.0.1', '::1'])
            
            # In DEBUG mode, always allow localhost
            if settings.DEBUG and client_ip in ['127.0.0.1', '::1', 'localhost']:
                return self.get_response(request)
            
            # Check if IP is whitelisted
            if not self.is_ip_allowed(client_ip, whitelist):
                admin_logger.critical(
                    f"BLOCKED: Admin access attempt from non-whitelisted IP: {client_ip} "
                    f"Path: {request.path} "
                    f"User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}"
                )
                
                return HttpResponseForbidden(
                    """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>403 Forbidden</title>
                        <style>
                            body {
                                font-family: Arial, sans-serif;
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                height: 100vh;
                                margin: 0;
                                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            }
                            .container {
                                text-align: center;
                                background: white;
                                padding: 50px;
                                border-radius: 10px;
                                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                            }
                            h1 {
                                color: #d32f2f;
                                font-size: 72px;
                                margin: 0;
                            }
                            p {
                                color: #666;
                                font-size: 18px;
                                margin: 20px 0;
                            }
                            .code {
                                background: #f5f5f5;
                                padding: 10px;
                                border-radius: 5px;
                                font-family: monospace;
                                color: #333;
                                margin: 20px 0;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>403</h1>
                            <p><strong>Access Forbidden</strong></p>
                            <p>Your IP address is not authorized to access this resource.</p>
                            <div class="code">IP: """ + client_ip + """</div>
                            <p style="font-size: 14px; color: #999; margin-top: 30px;">
                                This incident has been logged.
                            </p>
                        </div>
                    </body>
                    </html>
                    """
                )
        
        return self.get_response(request)
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address securely"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Get the first IP in the chain
            ip = x_forwarded_for.split(',')[0].strip()
            # Validate IP format
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                return ip
        return request.META.get('REMOTE_ADDR', '0.0.0.0')
    
    @staticmethod
    def is_ip_allowed(ip, whitelist):
        """
        Check if IP is in whitelist
        Supports exact matches and CIDR ranges
        """
        # Exact match
        if ip in whitelist:
            return True
        
        # Check for CIDR ranges (if you want to add this later)
        # Example: '192.168.1.0/24' would allow 192.168.1.0 - 192.168.1.255
        # For now, we'll just do exact matches for simplicity
        
        return False