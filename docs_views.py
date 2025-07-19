from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json

def api_documentation(request):
    """
    API Documentation page - accessible to all users
    """
    context = {
        'page_title': 'API Documentation - PexiLabs',
    }
    return render(request, 'docs/api_documentation.html', context)

def integration_guides(request):
    """
    Integration guides page
    """
    context = {
        'page_title': 'Integration Guides - PexiLabs',
    }
    return render(request, 'docs/integration_guides.html', context)

def sdk_documentation(request):
    """
    SDK documentation page
    """
    context = {
        'page_title': 'SDK Documentation - PexiLabs',
    }
    return render(request, 'docs/sdk_documentation.html', context)

def webhook_testing(request):
    """
    Webhook testing tool
    """
    context = {
        'page_title': 'Webhook Testing - PexiLabs',
    }
    return render(request, 'docs/webhook_testing.html', context)

def api_explorer(request):
    """
    Interactive API explorer
    """
    context = {
        'page_title': 'API Explorer - PexiLabs',
    }
    return render(request, 'docs/api_explorer.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def webhook_endpoint_test(request):
    """
    Test webhook endpoint for developers
    """
    try:
        # Parse the incoming webhook data
        payload = json.loads(request.body)
        
        # Log the webhook for testing purposes
        webhook_data = {
            'headers': dict(request.headers),
            'payload': payload,
            'method': request.method,
            'timestamp': request.META.get('HTTP_DATE'),
        }
        
        # In a real implementation, you would process the webhook
        # For testing, just return success
        return JsonResponse({
            'status': 'success',
            'message': 'Webhook received successfully',
            'received_data': webhook_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON payload'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
