from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
import hashlib
import logging
from django.utils import timezone
from .models import AppKey, AppKeyStatus

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailBackend(BaseBackend):
    """
    Custom authentication backend that allows users to log in using their email address.
    """
    
    def authenticate(self, request, email=None, password=None, **kwargs):
        """
        Authenticate a user based on email and password.
        """
        if email is None or password is None:
            return None
        
        try:
            # Try to get user by email
            user = User.objects.get(
                Q(email__iexact=email) & Q(is_active=True)
            )
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            User().set_password(password)
            return None
        
        # Check password and return user if valid
        if user.check_password(password):
            return user
        
        return None
    
    def get_user(self, user_id):
        """
        Get a user by their ID.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class PhoneBackend(BaseBackend):
    """
    Custom authentication backend that allows users to log in using their phone number.
    """
    
    def authenticate(self, request, phone_number=None, password=None, **kwargs):
        """
        Authenticate a user based on phone number and password.
        """
        if phone_number is None or password is None:
            return None
        
        try:
            # Try to get user by phone number
            user = User.objects.get(
                Q(phone_number=phone_number) & Q(is_active=True)
            )
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            User().set_password(password)
            return None
        
        # Check password and return user if valid
        if user.check_password(password):
            return user
        
        return None
    
    def get_user(self, user_id):
        """
        Get a user by their ID.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class APIKeyBackend(BaseBackend):
    """
    Custom authentication backend that allows merchants to authenticate using API keys.
    This backend validates API keys and associates them with merchant accounts.
    """
    
    def authenticate(self, request, api_key=None, **kwargs):
        """
        Authenticate a merchant based on API key.
        
        Args:
            request: The HTTP request object
            api_key: The API key string in format "public_key:secret_key"
        
        Returns:
            User object if authentication successful, None otherwise
        """
        if not api_key:
            return None
        
        try:
            # Parse API key (expected format: public_key:secret_key)
            if ':' not in api_key:
                logger.warning(f"Invalid API key format from IP: {self._get_client_ip(request)}")
                return None
            
            public_key, secret_key = api_key.split(':', 1)
            
            # Find the app key by public key
            try:
                app_key = AppKey.objects.select_related('partner').get(
                    public_key=public_key,
                    status=AppKeyStatus.ACTIVE
                )
            except AppKey.DoesNotExist:
                logger.warning(f"API key not found: {public_key} from IP: {self._get_client_ip(request)}")
                return None
            
            # Verify the secret key
            if not app_key.verify_secret(secret_key):
                logger.warning(f"Invalid secret for API key: {public_key} from IP: {self._get_client_ip(request)}")
                return None
            
            # Check if key is active and not expired
            if not app_key.is_active():
                logger.warning(f"Inactive/expired API key: {public_key} from IP: {self._get_client_ip(request)}")
                return None
            
            # Check IP restrictions
            client_ip = self._get_client_ip(request)
            if not app_key.is_ip_allowed(client_ip):
                logger.warning(f"IP not allowed for API key: {public_key} from IP: {client_ip}")
                return None
            
            # Check partner status
            if not app_key.partner.is_active:
                logger.warning(f"Inactive partner for API key: {public_key}")
                return None
            
            # Record usage
            app_key.record_usage()
            
            # Log successful authentication
            logger.info(f"Successful API key authentication: {public_key} from IP: {client_ip}")
            
            # Return a user object - we'll need to create a way to associate API keys with users
            # For now, let's try to find a merchant account associated with this partner
            try:
                # This assumes there's a relationship between partners and merchants
                # You might need to adjust this based on your business logic
                merchant = app_key.partner.merchants.filter(status='active').first()
                if merchant:
                    # Store the app_key in the user object for later use
                    merchant.user._api_key = app_key
                    return merchant.user
                else:
                    logger.warning(f"No active merchant found for partner: {app_key.partner.name}")
                    return None
            except AttributeError:
                # If there's no direct relationship, we might need to create a different approach
                logger.error(f"No merchant relationship found for partner: {app_key.partner.name}")
                return None
                
        except Exception as e:
            logger.error(f"API key authentication error: {str(e)}")
            return None
    
    def get_user(self, user_id):
        """
        Get a user by their ID.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    
    def _get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
