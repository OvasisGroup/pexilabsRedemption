from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

def landing_page(request):
    """Landing page view - redirect authenticated users to dashboard"""
    # Check if user is logged in
    if request.user.is_authenticated:
        # Use the comprehensive dashboard redirect logic
        return redirect('dashboard:dashboard_redirect')
    
    # Show landing page for unauthenticated users
    context = {
        'page_title': 'PexiLabs - Advanced Payment Processing Platform',
        'meta_description': 'Streamline your payment operations with PexiLabs comprehensive payment processing platform. Integrate multiple payment gateways, manage transactions, and scale your business globally.',
        'integrations_count': 15,
        'merchants_served': 1200,
        'transactions_processed': 250000,
        'countries_supported': 45,
    }
    return render(request, 'landing/index.html', context)

def features_page(request):
    """Features page view"""
    context = {
        'page_title': 'Features - PexiLabs Payment Platform',
        'meta_description': 'Discover powerful features including multi-gateway integration, real-time analytics, fraud detection, and comprehensive API documentation.',
    }
    return render(request, 'landing/features.html', context)

def pricing_page(request):
    """Pricing page view"""
    context = {
        'page_title': 'Pricing - PexiLabs Payment Solutions',
        'meta_description': 'Transparent pricing for businesses of all sizes. Start free and scale as you grow with our flexible payment processing plans.',
    }
    return render(request, 'landing/pricing.html', context)

def contact_page(request):
    """Contact page view"""
    context = {
        'page_title': 'Contact Us - PexiLabs Support',
        'meta_description': 'Get in touch with our payment experts. We\'re here to help you integrate and optimize your payment processing.',
    }
    return render(request, 'landing/contact.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def contact_form_submit(request):
    """Handle contact form submissions"""
    try:
        data = json.loads(request.body)
        
        # Basic validation
        required_fields = ['name', 'email', 'message']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'error': f'{field.title()} is required'
                }, status=400)
        
        # Here you would typically save to database or send email
        # For now, we'll just return success
        
        return JsonResponse({
            'success': True,
            'message': 'Thank you for your message. We\'ll get back to you soon!'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An error occurred processing your request'
        }, status=500)
