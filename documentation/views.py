from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json


def api_documentation(request):
    """Main API Documentation page"""
    return render(request, 'documentation/api_docs.html')


def integration_guides(request):
    """Integration guides and tutorials"""
    return render(request, 'documentation/integration_guides.html')


def sdk_documentation(request):
    """SDK Documentation and examples"""
    return render(request, 'documentation/sdk_docs.html')


def webhook_testing(request):
    """Webhook testing interface"""
    return render(request, 'documentation/webhook_testing.html')


@csrf_exempt
def webhook_endpoint_test(request):
    """Test endpoint for webhook testing"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            return JsonResponse({
                'success': True,
                'received_data': data,
                'message': 'Webhook received successfully'
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
    
    return JsonResponse({
        'success': True,
        'message': 'Webhook endpoint is ready to receive POST requests'
    })


def api_explorer(request):
    """Interactive API Explorer"""
    return render(request, 'documentation/api_explorer.html')


# Temporary placeholder view for development
def placeholder_view(request):
    """Temporary placeholder for documentation pages under development"""
    return HttpResponse("Documentation coming soon!")
