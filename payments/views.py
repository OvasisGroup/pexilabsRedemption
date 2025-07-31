from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django import forms
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.shortcuts import redirect
from django.db import transaction as db_transaction
from django.core.exceptions import PermissionDenied
import json
import uuid

try:
    from transactions.models import PaymentLink, Transaction, TransactionType, PaymentMethod, TransactionStatus
    from authentication.models import PreferredCurrency
    TRANSACTIONS_AVAILABLE = True
except ImportError:
    TRANSACTIONS_AVAILABLE = False


def payment_link_view(request, slug):
    """Handle payment link page"""
    if not TRANSACTIONS_AVAILABLE:
        return render(request, 'errors/503.html', {
            'error_message': 'Payment system is currently unavailable'
        })
    
    payment_link = get_object_or_404(
        PaymentLink.objects.select_related('merchant', 'currency'),
        slug=slug,
        is_active=True
    )
    
    # Check if payment link has expired
    if payment_link.expires_at and payment_link.expires_at < timezone.now():
        return render(request, 'payments/payment_expired.html', {
            'payment_link': payment_link
        })
    
    # Check if already paid (check if there's a related transaction)
    existing_transaction = Transaction.objects.filter(
        merchant=payment_link.merchant,
        metadata__payment_link_slug=payment_link.slug
    ).first()
    
    if existing_transaction:
        return render(request, 'payments/payment_completed.html', {
            'payment_link': payment_link,
            'transaction': existing_transaction
        })
    
    if request.method == 'POST':
        return process_payment_link(request, payment_link)
    
    context = {
        'payment_link': payment_link,
        'merchant': payment_link.merchant,
    }
    
    return render(request, 'payments/payment_link.html', context)


def process_payment_link(request, payment_link):
    """Process payment from payment link"""
    try:
        # Parse request data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Validate required fields
        customer_email = data.get('customer_email')
        payment_method = data.get('payment_method', 'card')
        
        if not customer_email:
            return JsonResponse({'error': 'Customer email is required'}, status=400)
        
        # Check max uses
        if payment_link.max_uses is not None and payment_link.current_uses >= payment_link.max_uses:
            return JsonResponse({'error': 'Maximum uses for this payment link have been reached.'}, status=403)
        
        # Generate unique reference
        reference = f"PAY_{uuid.uuid4().hex[:12].upper()}"
        
        with db_transaction.atomic():
            # Create transaction
            transaction = Transaction.objects.create(
                merchant=payment_link.merchant,
                reference=reference,
                transaction_type=TransactionType.PAYMENT,
                payment_method=payment_method,
                amount=payment_link.amount,
                currency=payment_link.currency,
                customer_email=customer_email,
                customer_phone=data.get('customer_phone', ''),
                description=f"Payment for: {payment_link.title}",
                status=TransactionStatus.COMPLETED,  # For demo purposes, set as completed
                net_amount=payment_link.amount,
                metadata={
                    'payment_link_id': str(payment_link.id),
                    'payment_link_slug': payment_link.slug
                }
            )
            
            # Update payment link usage atomically
            payment_link.current_uses = db_transaction.atomic(lambda: payment_link.current_uses + 1)
            payment_link.save()
        
        return JsonResponse({
            'success': True,
            'transaction_id': str(transaction.id),
            'reference': transaction.reference,
            'message': 'Payment processed successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


class PaymentLinkCreateForm(forms.Form):
    title = forms.CharField(max_length=255, required=True)
    amount = forms.DecimalField(max_digits=12, decimal_places=2, required=True)
    currency = forms.CharField(max_length=10, required=True)
    description = forms.CharField(widget=forms.Textarea, required=False)
    expires_at = forms.DateTimeField(required=False)
    max_uses = forms.IntegerField(required=False, min_value=1)

@login_required
def create_payment_link_view(request):
    if not TRANSACTIONS_AVAILABLE:
        return render(request, 'errors/503.html', {
            'error_message': 'Payment system is currently unavailable'
        })

    currencies = PreferredCurrency.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        form = PaymentLinkCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            payment_link = PaymentLink.objects.create(
                merchant=request.user.merchant_account,
                title=data['title'],
                amount=data['amount'],
                currency_id=data['currency'],  # This should be the UUID
                description=data.get('description', ''),
                expires_at=data.get('expires_at'),
                max_uses=data.get('max_uses') or 1,
                is_active=True,
            )
            return redirect(reverse('payments:payment_link_detail', args=[payment_link.slug]))
    else:
        form = PaymentLinkCreateForm()

    return render(request, 'payments/create_payment_link.html', {'form': form, 'currencies': currencies})

@csrf_exempt
@require_POST
def api_create_payment_link(request):
    try:
        data = json.loads(request.body)
        required_fields = ['title', 'amount', 'currency']
        for field in required_fields:
            if field not in data or not data[field]:
                return JsonResponse({'success': False, 'error': f'Missing required field: {field}'}, status=400)
        if not hasattr(request.user, 'merchant_account'):
            return JsonResponse({'success': False, 'error': 'User does not have a merchant account.'}, status=403)
        payment_link = PaymentLink.objects.create(
            merchant=request.user.merchant_account,
            title=data['title'],
            amount=data['amount'],
            currency_id=data['currency'],
            description=data.get('description', ''),
            expires_at=data.get('expires_at'),
            max_uses=data.get('max_uses') or 1,
            is_active=True,
        )
        return JsonResponse({'success': True, 'slug': payment_link.slug}, status=201)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

def api_payment_link_detail(request, slug):
    # TODO: Implement actual logic for retrieving payment link details
    return JsonResponse({'detail': f'API payment link detail for {slug}'})
