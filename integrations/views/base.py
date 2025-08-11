from rest_framework import permissions
from rest_framework.pagination import PageNumberPagination


class APIKeyPermission(permissions.BasePermission):
    """
    Custom permission class for API key authentication.
    Allows access to users authenticated via API key or regular authentication.
    """
    
    def has_permission(self, request, view):
        """
        Check if the request has permission to access the view.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # If user is authenticated via API key, check scopes
        if hasattr(request.user, '_api_key'):
            app_key = request.user._api_key
            
            # Check if the API key has the required scope for this operation
            if request.method in ['GET', 'HEAD', 'OPTIONS']:
                required_scope = 'read'
            elif request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                required_scope = 'write'
            else:
                required_scope = 'admin'
            
            return app_key.has_scope(required_scope)
        
        # For regular authenticated users, allow access
        return True


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for integrations API"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100