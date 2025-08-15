from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ..utils import api_key_required


@api_key_required
@require_http_methods(["POST"])
def auth_verify(request):
    """
    Verify API key authentication.
    
    This endpoint validates the provided API key and returns authentication status
    along with associated partner information. The actual authentication is handled
    by the @api_key_required decorator.
    
    Returns:
        JsonResponse: Authentication status and partner details
    """
    # Authentication is already handled by the decorator
    # Access authenticated data via request attributes
    app_key = request.api_key
    partner = request.api_partner
    
    return JsonResponse({
        'authenticated': True,
        'message': 'Authentication successful',
        'data': {
            'partner': {
                'id': str(partner.id),
                'name': partner.name,
                'code': partner.code,
                'is_active': partner.is_active
            },
            'app_key': {
                'id': str(app_key.id),
                'name': app_key.name,
                'key_type': app_key.key_type,
                'scopes': app_key.get_scopes_list(),
                'status': app_key.status
            }
        }
    }, status=200)