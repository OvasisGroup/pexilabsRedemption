from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib.auth.decorators import login_required
import json
import uuid

from .models import CheckoutPage, PaymentMethodConfig, CheckoutSession


def manage_checkout_pages(request):
    """Merchant interface for managing checkout pages"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Check if user has merchant account
    if not hasattr(request.user, 'merchant_account'):
        return JsonResponse({'error': 'No merchant account found'}, status=403)
    
    checkout_pages = CheckoutPage.objects.filter(
        merchant=request.user.merchant_account
    ).order_by('-created_at')
    
    context = {
        'checkout_pages': checkout_pages,
        'merchant': request.user.merchant_account
    }
    
    return render(request, 'checkout/manage_checkout_pages.html', context)


def get_currencies(request):
    """Get available currencies for checkout pages"""
    currencies = [
        {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'},
        {'code': 'EUR', 'name': 'Euro', 'symbol': '€'},
        {'code': 'GBP', 'name': 'British Pound', 'symbol': '£'},
        {'code': 'JPY', 'name': 'Japanese Yen', 'symbol': '¥'},
        {'code': 'CAD', 'name': 'Canadian Dollar', 'symbol': 'C$'},
        {'code': 'AUD', 'name': 'Australian Dollar', 'symbol': 'A$'},
        {'code': 'CHF', 'name': 'Swiss Franc', 'symbol': 'CHF'},
        {'code': 'CNY', 'name': 'Chinese Yuan', 'symbol': '¥'},
        {'code': 'SEK', 'name': 'Swedish Krona', 'symbol': 'kr'},
        {'code': 'NZD', 'name': 'New Zealand Dollar', 'symbol': 'NZ$'},
    ]
    
    return JsonResponse({
        'currencies': currencies,
        'default': 'USD'
    })


def checkout_page_view(request, slug):
    """Render the customer-facing checkout page"""
    try:
        checkout_page = get_object_or_404(CheckoutPage, slug=slug, is_active=True)
        
        # Get enabled payment methods for this checkout page
        payment_methods = PaymentMethodConfig.objects.filter(
            checkout_page=checkout_page,
            is_enabled=True
        ).order_by('display_order')
        
        # Create a checkout session if needed
        session_id = request.GET.get('session_id')
        if not session_id:
            session = CheckoutSession.objects.create(
                checkout_page=checkout_page,
                session_id=str(uuid.uuid4()),
                amount=checkout_page.amount,
                currency=checkout_page.currency,
                expires_at=timezone.now() + timezone.timedelta(hours=24)
            )
            session_id = session.session_id
        else:
            session = get_object_or_404(CheckoutSession, session_id=session_id)
        
        context = {
            'checkout_page': checkout_page,
            'session': session,
            'payment_methods': payment_methods,
            'session_id': session_id,
        }
        
        return render(request, 'checkout/checkout_page.html', context)
        
    except CheckoutPage.DoesNotExist:
        return render(request, 'checkout/page_not_found.html', status=404)


@login_required
@require_http_methods(["GET", "POST"])
def create_checkout_page(request):
    """Create a new checkout page"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            checkout_page = CheckoutPage.objects.create(
                merchant=request.user.merchant_account,
                name=data.get('name'),
                description=data.get('description', ''),
                amount=data.get('amount'),
                currency=data.get('currency', 'USD'),
                logo_url=data.get('logo_url', ''),
                primary_color=data.get('primary_color', '#007bff'),
                secondary_color=data.get('secondary_color', '#6c757d'),
                background_color=data.get('background_color', '#ffffff'),
                success_url=data.get('success_url', ''),
                cancel_url=data.get('cancel_url', ''),
                collect_customer_info=data.get('collect_customer_info', True),
                custom_css=data.get('custom_css', ''),
                is_active=data.get('is_active', True)
            )
            
            # Create payment method configurations
            payment_methods = data.get('payment_methods', [])
            for pm in payment_methods:
                PaymentMethodConfig.objects.create(
                    checkout_page=checkout_page,
                    payment_method=pm.get('payment_method'),
                    display_name=pm.get('display_name'),
                    icon_url=pm.get('icon_url', ''),
                    is_enabled=pm.get('is_enabled', True),
                    display_order=pm.get('display_order', 0),
                    config_data=pm.get('config_data', {})
                )
            
            return JsonResponse({
                'success': True,
                'checkout_page_id': str(checkout_page.id),
                'slug': checkout_page.slug,
                'message': 'Checkout page created successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    # GET request - show form
    return render(request, 'checkout/create_checkout_page.html')


@csrf_exempt
def process_payment(request):
    """Process payment for a checkout session"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if not session_id:
            return JsonResponse({'error': 'Session ID is required'}, status=400)
            
        session = get_object_or_404(CheckoutSession, session_id=session_id)
        
        # Check if session has expired
        if session.expires_at < timezone.now():
            return JsonResponse({'error': 'Checkout session has expired'}, status=400)
        
        # Check if session is already completed
        if session.status == 'completed':
            return JsonResponse({'error': 'Payment has already been processed'}, status=400)
        
        # Simulate payment processing
        session.status = 'completed'
        session.payment_method_used = data.get('payment_method', 'card')
        session.payment_data = {
            'transaction_id': str(uuid.uuid4()),
            'payment_method': data.get('payment_method', 'card'),
            'processed_at': timezone.now().isoformat(),
        }
        session.save()
        
        return JsonResponse({
            'success': True,
            'transaction_id': session.payment_data['transaction_id'],
            'redirect_url': session.checkout_page.success_url or '/payment/success/',
            'message': 'Payment processed successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Payment processing failed: {str(e)}'}, status=500)


def get_checkout_page_info(request, slug):
    """Get checkout page information for API"""
    try:
        checkout_page = get_object_or_404(CheckoutPage, slug=slug, is_active=True)
        
        # Get payment methods
        payment_methods = PaymentMethodConfig.objects.filter(
            checkout_page=checkout_page,
            is_enabled=True
        ).order_by('display_order')
        
        payment_methods_data = [
            {
                'payment_method': pm.payment_method,
                'display_name': pm.display_name,
                'icon_url': pm.icon_url,
                'display_order': pm.display_order
            }
            for pm in payment_methods
        ]
        
        return JsonResponse({
            'id': str(checkout_page.id),
            'name': checkout_page.name,
            'description': checkout_page.description,
            'amount': str(checkout_page.amount),
            'currency': checkout_page.currency,
            'logo_url': checkout_page.logo_url,
            'primary_color': checkout_page.primary_color,
            'secondary_color': checkout_page.secondary_color,
            'background_color': checkout_page.background_color,
            'collect_customer_info': checkout_page.collect_customer_info,
            'payment_methods': payment_methods_data
        })
        
    except CheckoutPage.DoesNotExist:
        return JsonResponse({'error': 'Checkout page not found'}, status=404)


def get_checkout_session(request, session_token):
    """Get checkout session details"""
    try:
        session = get_object_or_404(CheckoutSession, session_id=session_token)
        
        return JsonResponse({
            'session_id': session.session_id,
            'checkout_page': {
                'name': session.checkout_page.name,
                'slug': session.checkout_page.slug
            },
            'amount': str(session.amount),
            'currency': session.currency,
            'status': session.status,
            'customer_email': session.customer_email,
            'expires_at': session.expires_at.isoformat(),
            'created_at': session.created_at.isoformat()
        })
        
    except CheckoutSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)


@login_required
def create_checkout_session(request):
    """Create a checkout session for a customer"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        checkout_page_id = data.get('checkout_page_id')
        
        if not checkout_page_id:
            return JsonResponse({'error': 'Checkout page ID is required'}, status=400)
            
        checkout_page = get_object_or_404(CheckoutPage, id=checkout_page_id)
        
        # Verify the merchant owns this checkout page
        if hasattr(request.user, 'merchant_account') and checkout_page.merchant != request.user.merchant_account:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Create the checkout session
        session = CheckoutSession.objects.create(
            checkout_page=checkout_page,
            session_id=str(uuid.uuid4()),
            amount=data.get('amount', checkout_page.amount),
            currency=data.get('currency', checkout_page.currency),
            customer_email=data.get('customer_email'),
            customer_data=data.get('customer_data', {}),
            expires_at=timezone.now() + timezone.timedelta(hours=24)
        )
        
        return JsonResponse({
            'session_id': session.session_id,
            'checkout_url': f'/checkout/{checkout_page.slug}/?session_id={session.session_id}',
            'expires_at': session.expires_at.isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
