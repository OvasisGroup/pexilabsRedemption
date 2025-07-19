from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
import json
import uuid

from .models import CheckoutPage, PaymentMethodConfig, CheckoutSession
from .serializers import (
    CheckoutPageSerializer, CheckoutPageCreateSerializer,
    PaymentMethodConfigSerializer, CheckoutSessionSerializer,
    CreateCheckoutSessionSerializer, ProcessPaymentSerializer
)


class CheckoutPageListCreateView(generics.ListCreateAPIView):
    """List all checkout pages or create a new one."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CheckoutPageCreateSerializer
        return CheckoutPageSerializer
    
    def get_queryset(self):
        if hasattr(self.request.user, 'merchant_account'):
            return CheckoutPage.objects.filter(merchant=self.request.user.merchant_account)
        return CheckoutPage.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(merchant=self.request.user.merchant_account)


class CheckoutPageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a checkout page"""
    serializer_class = CheckoutPageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'merchant_account'):
            return CheckoutPage.objects.filter(merchant=self.request.user.merchant_account)
        return CheckoutPage.objects.none()


def manage_checkout_pages(request):
    """Merchant interface for managing checkout pages"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    if not hasattr(request.user, 'merchant_account'):
        return render(request, 'checkout/no_merchant_access.html', status=403)
    
    checkout_pages = CheckoutPage.objects.filter(
        merchant=request.user.merchant_account
    ).order_by('-created_at')
    
    context = {
        'checkout_pages': checkout_pages,
        'merchant': request.user.merchant_account
    }
    
    return render(request, 'checkout/manage_checkout_pages.html', context)


@api_view(['GET'])
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
    
    return Response({
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


# Simplified URL configuration requires these views
class PaymentMethodConfigListView(generics.ListCreateAPIView):
    serializer_class = PaymentMethodConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        checkout_page_id = self.kwargs.get('checkout_page_id')
        return PaymentMethodConfig.objects.filter(checkout_page_id=checkout_page_id)


class PaymentMethodConfigDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PaymentMethodConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = PaymentMethodConfig.objects.all()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_checkout_session(request):
    """Create a checkout session for a customer"""
    serializer = CreateCheckoutSessionSerializer(data=request.data)
    if serializer.is_valid():
        checkout_page = serializer.validated_data['checkout_page']
        
        # Create the checkout session
        session = CheckoutSession.objects.create(
            checkout_page=checkout_page,
            session_id=str(uuid.uuid4()),
            amount=serializer.validated_data.get('amount', checkout_page.amount),
            currency=serializer.validated_data.get('currency', checkout_page.currency),
            customer_email=serializer.validated_data.get('customer_email'),
            customer_data=serializer.validated_data.get('customer_data', {}),
            expires_at=timezone.now() + timezone.timedelta(hours=24)
        )
        
        return Response(CheckoutSessionSerializer(session).data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_checkout_session(request, session_token):
    """Get checkout session details"""
    try:
        session = get_object_or_404(CheckoutSession, session_id=session_token)
        return Response(CheckoutSessionSerializer(session).data)
    except CheckoutSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@csrf_exempt
def process_payment(request):
    """Process payment for a checkout session"""
    try:
        session_id = request.data.get('session_id')
        if not session_id:
            return Response(
                {'error': 'Session ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        session = get_object_or_404(CheckoutSession, session_id=session_id)
        
        # Check if session has expired
        if session.expires_at < timezone.now():
            return Response(
                {'error': 'Checkout session has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if session is already completed
        if session.status == 'completed':
            return Response(
                {'error': 'Payment has already been processed for this session'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Simulate payment processing
        session.status = 'completed'
        session.payment_method_used = request.data.get('payment_method', 'card')
        session.payment_data = {
            'transaction_id': str(uuid.uuid4()),
            'payment_method': request.data.get('payment_method', 'card'),
            'processed_at': timezone.now().isoformat(),
        }
        session.save()
        
        return Response({
            'success': True,
            'transaction_id': session.payment_data['transaction_id'],
            'redirect_url': session.checkout_page.success_url or '/payment/success/',
            'message': 'Payment processed successfully'
        })
        
    except Exception as e:
        return Response(
            {'error': f'Payment processing failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_checkout_page_info(request, slug):
    """Get checkout page information for API"""
    try:
        checkout_page = get_object_or_404(CheckoutPage, slug=slug, is_active=True)
        serializer = CheckoutPageSerializer(checkout_page)
        return Response(serializer.data)
    except CheckoutPage.DoesNotExist:
        return Response({'error': 'Checkout page not found'}, status=status.HTTP_404_NOT_FOUND)
