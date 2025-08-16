import logging
from functools import wraps
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from authentication.api_auth import APIKeyAuthentication

logger = logging.getLogger(__name__)

def api_key_required(view_func=None, *, require_write_permission=False):
    """
    Decorator that enforces API key authentication for views.
    
    This decorator can be used on both function-based views and class-based views
    to ensure that requests are authenticated using valid API keys. It extracts
    the authentication logic and provides a consistent way to handle API key
    validation across the application.
    
    Args:
        view_func: The view function to be decorated (when used without parameters)
        require_write_permission (bool): Whether to require write permissions for the API key
    
    Returns:
        For authenticated requests: Calls the original view with additional context
        For unauthenticated requests: Returns JSON error response with 401 status
        For server errors: Returns JSON error response with 500 status
    
    Usage:
        Function-based views:
        
        @api_key_required
        def my_view(request):
            # Access authenticated user and app_key via request attributes
            user = request.api_user
            app_key = request.api_key
            return JsonResponse({'message': 'Success'})
        
        @api_key_required(require_write_permission=True)
        def my_protected_view(request):
            # This view requires write permissions
            return JsonResponse({'message': 'Write access granted'})
        
        Class-based views:
        
        @method_decorator(api_key_required, name='dispatch')
        class MyAPIView(View):
            def post(self, request):
                user = request.api_user
                app_key = request.api_key
                return JsonResponse({'message': 'Success'})
        
        Or for individual methods:
        
        class MyAPIView(View):
            @method_decorator(api_key_required)
            def post(self, request):
                return JsonResponse({'message': 'Success'})
    
    Attributes added to request:
        request.api_user: The authenticated user object
        request.api_key: The AppKey instance used for authentication
        request.api_partner: The WhitelabelPartner associated with the API key
    
    Error Responses:
        401 Unauthorized: When API key is missing, invalid, or lacks required permissions
        500 Internal Server Error: When an unexpected error occurs during authentication
    
    Note:
        This decorator automatically applies @csrf_exempt to the decorated view
        since API key authentication is used instead of CSRF tokens.
    """
    def decorator(func):
        @wraps(func)
        @csrf_exempt
        def wrapper(request, *args, **kwargs):
            try:
                # Initialize API key authentication
                auth = APIKeyAuthentication()
                auth_result = auth.authenticate(request)
                
                if not auth_result:
                    return JsonResponse({
                        'error': 'Authentication required',
                        'message': 'Please provide a valid API key in Authorization header or X-API-Key header',
                        'authenticated': False
                    }, status=401)
                
                user, app_key = auth_result
                
                # Check write permissions if required
                if require_write_permission and not app_key.has_scope('write'):
                    return JsonResponse({
                        'error': 'Insufficient permissions',
                        'message': 'This endpoint requires write permissions',
                        'authenticated': True
                    }, status=403)
                
                # Add authentication context to request
                request.api_user = user
                request.api_key = app_key
                request.api_partner = app_key.partner
                
                # Call the original view function
                return func(request, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"API key authentication error: {str(e)}")
                return JsonResponse({
                    'error': 'Internal server error',
                    'message': 'An error occurred during authentication verification',
                    'authenticated': False
                }, status=500)
        
        return wrapper
    
    # Handle both @api_key_required and @api_key_required() usage
    if view_func is None:
        return decorator
    else:
        return decorator(view_func)


def get_api_context(request):
    """
    Helper function to extract API authentication context from request.
    
    This function can be used within views decorated with @api_key_required
    to easily access authentication information.
    
    Args:
        request: Django HttpRequest object (must be decorated with @api_key_required)
    
    Returns:
        dict: Dictionary containing authentication context with keys:
            - 'user': The authenticated user object
            - 'app_key': The AppKey instance
            - 'partner': The WhitelabelPartner instance
            - 'scopes': List of API key scopes
    
    Raises:
        AttributeError: If the request doesn't have API authentication context
                       (view not decorated with @api_key_required)
    
    Usage:
        @api_key_required
        def my_view(request):
            context = get_api_context(request)
            user = context['user']
            partner = context['partner']
            scopes = context['scopes']
            return JsonResponse({'partner_name': partner.name})
    """
    try:
        return {
            'user': request.api_user,
            'app_key': request.api_key,
            'partner': request.api_partner,
            'scopes': request.api_key.get_scopes_list()
        }
    except AttributeError as e:
        raise AttributeError(
            "Request does not have API authentication context. "
            "Make sure the view is decorated with @api_key_required."
        ) from e