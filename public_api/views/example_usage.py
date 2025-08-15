from django.http import JsonResponse
from django.views import View
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from ..utils import api_key_required


# Example 1: Function-based view using the decorator
@api_key_required
@require_http_methods(["GET"])
def get_partner_info(request):
    """
    Example function-based view that returns partner information.
    The @api_key_required decorator handles authentication automatically.
    """
    partner = request.api_partner
    app_key = request.api_key
    
    return JsonResponse({
        'partner_name': partner.name,
        'partner_code': partner.code,
        'api_key_name': app_key.name,
        'scopes': app_key.get_scopes_list()
    })


# Example 2: Class-based view using the decorator
@method_decorator(api_key_required, name='dispatch')
class PartnerStatsView(View):
    """
    Example class-based view that returns partner statistics.
    The @api_key_required decorator is applied to the dispatch method.
    """
    
    def get(self, request):
        """Handle GET requests to return partner stats."""
        partner = request.api_partner
        app_key = request.api_key
        
        return JsonResponse({
            'partner': {
                'id': str(partner.id),
                'name': partner.name,
                'code': partner.code,
                'is_active': partner.is_active
            },
            'api_key': {
                'name': app_key.name,
                'key_type': app_key.key_type,
                'status': app_key.status
            },
            'stats': {
                'total_requests': 0,  # This would come from actual stats
                'last_request': None
            }
        })
    
    def post(self, request):
        """Handle POST requests for updating partner stats."""
        partner = request.api_partner
        
        return JsonResponse({
            'message': f'Stats updated for partner: {partner.name}',
            'success': True
        })