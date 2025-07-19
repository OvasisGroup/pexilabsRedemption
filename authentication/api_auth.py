"""
API Key Authentication for Django REST Framework

This module provides authentication classes for API key-based authentication
specifically designed for merchant integrations.
"""

import logging
from rest_framework import authentication, exceptions
from rest_framework.request import Request
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import AppKey, AppKeyStatus, AppKeyUsageLog
from .backends import APIKeyBackend

logger = logging.getLogger(__name__)
User = get_user_model()


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    API Key authentication for merchants.
    
    Clients should authenticate by passing the API key in the HTTP Authorization header,
    prepended with the string "Bearer ".  For example:
    
        Authorization: Bearer pk_partner_abc123:sk_live_xyz789
    
    Alternatively, the API key can be passed in a custom header:
    
        X-API-Key: pk_partner_abc123:sk_live_xyz789
    """
    
    keyword = 'Bearer'
    header_name = 'X-API-Key'
    
    def authenticate(self, request: Request):
        """
        Authenticate the request using API key.
        
        Returns:
            tuple: (user, app_key) if authentication successful
            None: if authentication not attempted
            
        Raises:
            AuthenticationFailed: if authentication fails
        """
        api_key = self.get_api_key(request)
        if not api_key:
            return None
        
        return self.authenticate_credentials(api_key, request)
    
    def get_api_key(self, request: Request) -> str:
        """
        Extract API key from request headers.
        
        Args:
            request: The DRF request object
            
        Returns:
            str: The API key if found, None otherwise
        """
        # Try Authorization header first
        auth_header = authentication.get_authorization_header(request).split()
        
        if auth_header and auth_header[0].lower() == self.keyword.lower().encode():
            if len(auth_header) == 1:
                msg = _('Invalid token header. No credentials provided.')
                raise exceptions.AuthenticationFailed(msg)
            elif len(auth_header) > 2:
                msg = _('Invalid token header. Token string should not contain spaces.')
                raise exceptions.AuthenticationFailed(msg)
            
            try:
                api_key = auth_header[1].decode('utf-8')
            except UnicodeError:
                msg = _('Invalid token header. Token string should not contain invalid characters.')
                raise exceptions.AuthenticationFailed(msg)
            
            return api_key
        
        # Try custom header as fallback
        api_key = request.META.get(f'HTTP_{self.header_name.upper().replace("-", "_")}')
        if api_key:
            return api_key
        
        return None
    
    def authenticate_credentials(self, api_key: str, request: Request):
        """
        Authenticate the API key and return user and app_key.
        
        Args:
            api_key: The API key string
            request: The DRF request object
            
        Returns:
            tuple: (user, app_key) if successful
            
        Raises:
            AuthenticationFailed: if authentication fails
        """
        if ':' not in api_key:
            raise exceptions.AuthenticationFailed(_('Invalid API key format.'))
        
        try:
            public_key, secret_key = api_key.split(':', 1)
        except ValueError:
            raise exceptions.AuthenticationFailed(_('Invalid API key format.'))
        
        try:
            app_key = AppKey.objects.select_related('partner').get(
                public_key=public_key,
                status=AppKeyStatus.ACTIVE
            )
        except AppKey.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid API key.'))
        
        # Verify the secret key
        if not app_key.verify_secret(secret_key):
            logger.warning(f"Invalid secret for API key: {public_key} from IP: {self._get_client_ip(request)}")
            raise exceptions.AuthenticationFailed(_('Invalid API key.'))
        
        # Check if key is active and not expired
        if not app_key.is_active():
            logger.warning(f"Inactive/expired API key: {public_key} from IP: {self._get_client_ip(request)}")
            raise exceptions.AuthenticationFailed(_('API key is inactive or expired.'))
        
        # Check IP restrictions
        client_ip = self._get_client_ip(request)
        if not app_key.is_ip_allowed(client_ip):
            logger.warning(f"IP not allowed for API key: {public_key} from IP: {client_ip}")
            raise exceptions.AuthenticationFailed(_('API key not allowed from this IP address.'))
        
        # Check partner status
        if not app_key.partner.is_active:
            logger.warning(f"Inactive partner for API key: {public_key}")
            raise exceptions.AuthenticationFailed(_('Partner account is inactive.'))
        
        # Record usage
        app_key.record_usage()
        
        # Log the API call for analytics
        self.log_api_call(app_key, request)
        
        # For now, create a mock user object that represents the API key
        # In a real implementation, you might want to associate API keys with actual user accounts
        user = self.get_or_create_api_user(app_key)
        
        logger.info(f"Successful API key authentication: {public_key} from IP: {client_ip}")
        
        return (user, app_key)
    
    def get_or_create_api_user(self, app_key: AppKey):
        """
        Get or create a user object for API key authentication.
        
        Args:
            app_key: The authenticated AppKey instance
            
        Returns:
            User: A user object representing the API key
        """
        # For API key authentication, we'll create a special user that represents the partner
        # This allows us to use the standard Django/DRF authentication and permission systems
        
        try:
            # Try to find an existing API user for this partner
            user = User.objects.get(
                email=f"api.{app_key.partner.code}@partner.api",
                is_active=True
            )
        except User.DoesNotExist:
            # Create a new API user for this partner
            user = User.objects.create(
                email=f"api.{app_key.partner.code}@partner.api",
                first_name=app_key.partner.name,
                last_name="API",
                is_active=True,
                is_verified=True,
                role='user',
                is_api_user=True  # This field might need to be added to your User model
            )
        
        # Store the app_key in the user object for later use in views
        user._api_key = app_key
        user._partner = app_key.partner
        
        return user
    
    def log_api_call(self, app_key: AppKey, request: Request):
        """
        Log the API call for analytics and monitoring.
        
        Args:
            app_key: The authenticated AppKey instance
            request: The DRF request object
        """
        try:
            # Extract request information
            endpoint = request.path
            method = request.method
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Create usage log entry
            AppKeyUsageLog.objects.create(
                app_key=app_key,
                endpoint=endpoint,
                method=method,
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=200,  # Will be updated by middleware if available
                response_time_ms=0,  # Will be updated by middleware if available
                request_id=getattr(request, 'id', ''),
            )
        except Exception as e:
            # Don't fail authentication if logging fails
            logger.error(f"Failed to log API call: {str(e)}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def authenticate_header(self, request: Request) -> str:
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        return f'{self.keyword} realm="API Key Required"'


class APIKeyOrTokenAuthentication(APIKeyAuthentication):
    """
    Authentication class that supports both API keys and JWT tokens.
    
    This allows endpoints to accept either form of authentication,
    which is useful during migration periods or for different client types.
    """
    
    def authenticate(self, request: Request):
        """
        Try API key authentication first, then fall back to token authentication.
        """
        # First try API key authentication
        result = super().authenticate(request)
        if result is not None:
            return result
        
        # If API key auth didn't work, we could try other authentication methods
        # For now, just return None to let other authentication classes try
        return None


class APIKeyPermission:
    """
    Permission class for API key-based access control.
    """
    
    def has_permission(self, request, view):
        """
        Check if the request has the required API key permissions.
        """
        if not hasattr(request.user, '_api_key'):
            return False
        
        app_key = request.user._api_key
        
        # Check if the API key has the required scope for this operation
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            required_scope = 'read'
        elif request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            required_scope = 'write'
        else:
            required_scope = 'admin'
        
        return app_key.has_scope(required_scope)
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the request has permission to access a specific object.
        """
        # This can be customized based on your business logic
        # For example, you might want to ensure that merchants can only
        # access their own data
        return self.has_permission(request, view)
