from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
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
    
    try:
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
        
    except PaymentLink.DoesNotExist:
        return render(request, 'errors/404.html', {
            'error_message': 'Payment link not found or has expired'
        })


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
        
        # Generate unique reference
        reference = f"PAY_{uuid.uuid4().hex[:12].upper()}"
        
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
        
        # Update payment link usage
        payment_link.current_uses += 1
        payment_link.save()
        
        return JsonResponse({
            'success': True,
            'transaction_id': str(transaction.id),
            'reference': transaction.reference,
            'message': 'Payment processed successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
