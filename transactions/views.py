from rest_framework import generics, status, filters, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.shortcuts import render, get_object_or_404
from checkout.models import CheckoutSession

from .models import (
    PaymentGateway,
    Transaction,
    PaymentLink,
    TransactionEvent,
    Webhook,
    PaymentMethod,
    TransactionType,
    TransactionStatus
)
from .serializers import (
    PaymentGatewaySerializer,
    TransactionListSerializer,
    TransactionDetailSerializer,
    TransactionCreateSerializer,
    TransactionUpdateSerializer,
    RefundCreateSerializer,
    PaymentLinkSerializer,
    PaymentLinkCreateSerializer,
    TransactionEventSerializer,
    WebhookSerializer,
    TransactionStatsSerializer,
    PaymentMethodChoiceSerializer,
    TransactionTypeChoiceSerializer,
    TransactionStatusChoiceSerializer
)
from authentication.models import Merchant


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for transactions"""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


# Payment Gateway Views
class PaymentGatewayListCreateView(generics.ListCreateAPIView):
    """List and create payment gateways"""
    queryset = PaymentGateway.objects.all()
    serializer_class = PaymentGatewaySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_sandbox', 'supports_payments', 'supports_refunds']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'priority', 'created_at']
    ordering = ['priority', 'name']

    @extend_schema(
        summary="List payment gateways",
        description="Retrieve a list of payment gateways with filtering and search capabilities"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create payment gateway",
        description="Create a new payment gateway configuration"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PaymentGatewayDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a payment gateway"""
    queryset = PaymentGateway.objects.all()
    serializer_class = PaymentGatewaySerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get payment gateway details",
        description="Retrieve detailed information about a specific payment gateway"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update payment gateway",
        description="Update a payment gateway configuration"
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update payment gateway",
        description="Partially update a payment gateway configuration"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete payment gateway",
        description="Delete a payment gateway (if no transactions exist)"
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# Transaction Views
class TransactionListCreateView(generics.ListCreateAPIView):
    """List and create transactions"""
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'status', 'transaction_type', 'payment_method', 'gateway',
        'merchant', 'is_settled', 'is_flagged'
    ]
    search_fields = ['reference', 'external_reference', 'customer__email', 'customer_email', 'description']
    ordering_fields = ['created_at', 'amount', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter transactions based on user permissions"""
        user = self.request.user
        queryset = Transaction.objects.select_related(
            'merchant', 'customer', 'currency', 'gateway'
        ).prefetch_related('events', 'webhooks')

        # Filter by merchant if user is a merchant
        if hasattr(user, 'merchant_profile'):
            queryset = queryset.filter(merchant=user.merchant_profile)
        elif not user.is_staff:
            # Non-staff users can only see their own transactions
            queryset = queryset.filter(customer=user)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.request.method == 'POST':
            return TransactionCreateSerializer
        return TransactionListSerializer

    @extend_schema(
        summary="List transactions",
        description="Retrieve a paginated list of transactions with filtering and search capabilities",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                description='Filter by transaction status'
            ),
            OpenApiParameter(
                name='transaction_type',
                type=OpenApiTypes.STR,
                description='Filter by transaction type'
            ),
            OpenApiParameter(
                name='payment_method',
                type=OpenApiTypes.STR,
                description='Filter by payment method'
            ),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create transaction",
        description="Create a new payment transaction"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TransactionDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve and update transaction details"""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter transactions based on user permissions"""
        user = self.request.user
        queryset = Transaction.objects.select_related(
            'merchant', 'customer', 'currency', 'gateway', 'parent_transaction'
        ).prefetch_related(
            'events__user', 'webhooks', 'child_transactions'
        )

        # Filter by merchant if user is a merchant
        if hasattr(user, 'merchant_profile'):
            queryset = queryset.filter(merchant=user.merchant_profile)
        elif not user.is_staff:
            # Non-staff users can only see their own transactions
            queryset = queryset.filter(customer=user)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.request.method in ['PUT', 'PATCH']:
            return TransactionUpdateSerializer
        return TransactionDetailSerializer

    @extend_schema(
        summary="Get transaction details",
        description="Retrieve detailed information about a specific transaction including events and webhooks"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update transaction",
        description="Update transaction details (limited fields only)"
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update transaction",
        description="Partially update transaction details"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


@extend_schema(
    summary="Create refund",
    description="Create a refund for a completed transaction",
    request=RefundCreateSerializer,
    responses={201: TransactionDetailSerializer}
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_refund(request, transaction_id):
    """Create a refund for a transaction"""
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        
        # Check permissions
        user = request.user
        if hasattr(user, 'merchant_profile'):
            if transaction.merchant != user.merchant_profile:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif not user.is_staff and transaction.customer != user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = RefundCreateSerializer(
            data=request.data,
            context={'transaction': transaction}
        )
        
        if serializer.is_valid():
            refund_amount = serializer.validated_data['amount']
            reason = serializer.validated_data.get('reason', '')
            
            try:
                refund = transaction.create_refund(
                    amount=refund_amount,
                    reason=reason,
                    created_by=request.user
                )
                
                # Create transaction event
                TransactionEvent.objects.create(
                    transaction=refund,
                    event_type='refund_created',
                    description=f"Refund created for {refund_amount}",
                    source='api',
                    user=request.user
                )
                
                refund_serializer = TransactionDetailSerializer(refund)
                return Response(refund_serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Transaction.DoesNotExist:
        return Response(
            {'error': 'Transaction not found'},
            status=status.HTTP_404_NOT_FOUND
        )


# Payment Link Views
class PaymentLinkListCreateView(generics.ListCreateAPIView):
    """List and create payment links"""
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_amount_flexible', 'merchant']
    search_fields = ['title', 'description', 'slug']
    ordering_fields = ['created_at', 'title', 'amount']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter payment links based on user permissions"""
        user = self.request.user
        queryset = PaymentLink.objects.select_related('merchant', 'currency')

        # Filter by merchant if user is a merchant
        if hasattr(user, 'merchant_profile'):
            queryset = queryset.filter(merchant=user.merchant_profile)
        elif not user.is_staff:
            # Non-staff users cannot create/view payment links
            queryset = queryset.none()

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.request.method == 'POST':
            return PaymentLinkCreateSerializer
        return PaymentLinkSerializer

    @extend_schema(
        summary="List payment links",
        description="Retrieve a list of payment links for the merchant"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create payment link",
        description="Create a new payment link"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PaymentLinkDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a payment link"""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter payment links based on user permissions"""
        user = self.request.user
        queryset = PaymentLink.objects.select_related('merchant', 'currency')

        # Filter by merchant if user is a merchant
        if hasattr(user, 'merchant_profile'):
            queryset = queryset.filter(merchant=user.merchant_profile)
        elif not user.is_staff:
            queryset = queryset.none()

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.request.method in ['PUT', 'PATCH']:
            return PaymentLinkCreateSerializer
        return PaymentLinkSerializer

    @extend_schema(
        summary="Get payment link details",
        description="Retrieve detailed information about a specific payment link"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update payment link",
        description="Update a payment link"
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update payment link",
        description="Partially update a payment link"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete payment link",
        description="Delete a payment link"
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# Statistics and Analytics Views
@extend_schema(
    summary="Get transaction statistics",
    description="Get transaction statistics for a merchant within a date range",
    parameters=[
        OpenApiParameter(
            name='start_date',
            type=OpenApiTypes.DATE,
            description='Start date for statistics (YYYY-MM-DD)'
        ),
        OpenApiParameter(
            name='end_date',
            type=OpenApiTypes.DATE,
            description='End date for statistics (YYYY-MM-DD)'
        ),
        OpenApiParameter(
            name='merchant_id',
            type=OpenApiTypes.UUID,
            description='Merchant ID (for staff users only)'
        ),
    ],
    responses={200: TransactionStatsSerializer}
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def transaction_stats(request):
    """Get transaction statistics"""
    user = request.user
    
    # Get query parameters
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    merchant_id = request.query_params.get('merchant_id')
    
    # Parse dates
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid start_date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid end_date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Determine merchant
    if merchant_id and user.is_staff:
        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response(
                {'error': 'Merchant not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif hasattr(user, 'merchant_profile'):
        merchant = user.merchant_profile
    else:
        return Response(
            {'error': 'No merchant specified'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get statistics
    stats = Transaction.get_merchant_stats(
        merchant=merchant,
        start_date=start_date,
        end_date=end_date
    )
    
    serializer = TransactionStatsSerializer(stats)
    return Response(serializer.data)


# Choice endpoints for API documentation
@extend_schema(
    summary="Get payment method choices",
    description="Get available payment method choices",
    responses={200: PaymentMethodChoiceSerializer(many=True)}
)
@api_view(['GET'])
def payment_method_choices(request):
    """Get payment method choices"""
    choices = [
        {'value': choice[0], 'display': choice[1]}
        for choice in PaymentMethod.choices
    ]
    return Response(choices)


@extend_schema(
    summary="Get transaction type choices",
    description="Get available transaction type choices",
    responses={200: TransactionTypeChoiceSerializer(many=True)}
)
@api_view(['GET'])
def transaction_type_choices(request):
    """Get transaction type choices"""
    choices = [
        {'value': choice[0], 'display': choice[1]}
        for choice in TransactionType.choices
    ]
    return Response(choices)


@extend_schema(
    summary="Get transaction status choices",
    description="Get available transaction status choices",
    responses={200: TransactionStatusChoiceSerializer(many=True)}
)
@api_view(['GET'])
def transaction_status_choices(request):
    """Get available transaction status choices"""
    choices = [
        {'value': choice[0], 'label': choice[1]}
        for choice in TransactionStatus.choices
    ]
    return Response(choices)


@extend_schema(
    summary="Update transaction status",
    description="Update transaction status based on payment events (success, failure, expiration)",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'session_id': {'type': 'string', 'description': 'Payment session ID'},
                'status': {'type': 'string', 'enum': ['completed', 'failed', 'expired'], 'description': 'New transaction status'},
                'failure_reason': {'type': 'string', 'description': 'Reason for failure (optional)'},
                'payment_reference': {'type': 'string', 'description': 'Payment gateway reference (optional)'}
            },
            'required': ['session_id', 'status']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'message': {'type': 'string'},
                'transaction_id': {'type': 'string'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'message': {'type': 'string'}
            }
        }
    }
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])  # Allow anonymous access for payment callbacks
def update_transaction_status(request):
    """Update transaction status based on payment events"""
    try:
        data = request.data
        session_id = data.get('session_id')
        new_status = data.get('status')
        failure_reason = data.get('failure_reason', '')
        payment_reference = data.get('payment_reference', '')
        
        if not session_id or not new_status:
            return Response({
                'error': 'Missing required fields',
                'message': 'session_id and status are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_status not in ['completed', 'failed', 'expired']:
            return Response({
                'error': 'Invalid status',
                'message': 'Status must be one of: completed, failed, expired'
            }, status=status.HTTP_400_BAD_REQUEST)
        
     
        
        # Find the checkout session
        try:
            checkout_session = CheckoutSession.objects.get(session_token=session_id)
        except CheckoutSession.DoesNotExist:
            return Response({
                'error': 'Session not found',
                'message': f'No checkout session found with ID: {session_id}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if session is already completed
        if checkout_session.status in ['completed', 'failed', 'expired']:
            return Response({
                'error': 'Session already processed',
                'message': f'Session is already in {checkout_session.status} status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update checkout session status
        checkout_session.status = new_status
        if new_status == 'completed':
            checkout_session.completed_at = timezone.now()
        if payment_reference:
            checkout_session.payment_reference = payment_reference
        checkout_session.save()
        
        # Try to find or create a corresponding transaction
        transaction = None
        try:
            # Look for existing transaction with this session reference
            transaction = Transaction.objects.filter(
                metadata__session_id=session_id
            ).first()
            
            if not transaction:
                # Create a new transaction if none exists
                from authentication.models import PreferredCurrency
                
                # Get currency object
                currency_obj = checkout_session.currency
                
                transaction = Transaction.objects.create(
                    merchant=checkout_session.checkout_page.merchant,
                    customer_email=checkout_session.customer_email,
                    transaction_type=TransactionType.PAYMENT,
                    status=TransactionStatus.PENDING,
                    payment_method=PaymentMethod.CARD,  # Default to card
                    currency=currency_obj,
                    amount=checkout_session.amount,
                    net_amount=checkout_session.amount,  # Simplified for now
                    description=f"Payment for {checkout_session.checkout_page.name}",
                    metadata={
                        'session_id': session_id,
                        'checkout_page_id': str(checkout_session.checkout_page.id)
                    },
                    external_reference=payment_reference
                )
            
            # Update transaction status based on checkout session status
            if new_status == 'completed':
                transaction.mark_as_completed()
            elif new_status == 'failed':
                transaction.mark_as_failed(reason=failure_reason)
            elif new_status == 'expired':
                transaction.status = TransactionStatus.EXPIRED
                transaction.failed_at = timezone.now()
                transaction.failure_reason = 'Payment session expired'
                transaction.save()
            
            # Create transaction event
            TransactionEvent.objects.create(
                transaction=transaction,
                event_type='status_update',
                old_status=TransactionStatus.PENDING,
                new_status=transaction.status,
                description=f'Status updated via payment widget callback',
                source='payment_widget',
                metadata={
                    'session_id': session_id,
                    'payment_reference': payment_reference,
                    'failure_reason': failure_reason
                }
            )
            
        except Exception as e:
            # Log the error but don't fail the status update
            print(f"Error creating/updating transaction: {str(e)}")
        
        return Response({
            'success': True,
            'message': f'Transaction status updated to {new_status}',
            'transaction_id': str(transaction.id) if transaction else None,
            'session_id': session_id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Template Views for Transactions

def transaction_list_view(request):
    """Render a list of transactions for template consumption"""
    user = request.user
    queryset = Transaction.objects.select_related(
        'merchant', 'customer', 'currency', 'gateway'
    ).prefetch_related('events', 'webhooks')

    if hasattr(user, 'merchant_profile'):
        queryset = queryset.filter(merchant=user.merchant_profile)
    elif not user.is_staff:
        queryset = queryset.filter(customer=user)

    transactions = queryset.order_by('-created_at')[:50]  # Limit for template
    return render(request, 'transactions/transaction_list.html', {'transactions': transactions})


def transaction_detail_view(request, pk):
    """Render transaction detail for template consumption"""
    user = request.user
    transaction = get_object_or_404(Transaction, pk=pk)

    # Permission check
    if hasattr(user, 'merchant_profile'):
        if transaction.merchant != user.merchant_profile:
            return render(request, 'transactions/permission_denied.html')
    elif not user.is_staff and transaction.customer != user:
        return render(request, 'transactions/permission_denied.html')

    return render(request, 'transactions/transaction_detail.html', {'transaction': transaction})


def payment_link_list_view(request):
    """Render a list of payment links for template consumption"""
    user = request.user
    queryset = PaymentLink.objects.select_related('merchant', 'currency')

    if hasattr(user, 'merchant_profile'):
        queryset = queryset.filter(merchant=user.merchant_profile)
    elif not user.is_staff:
        queryset = queryset.none()

    payment_links = queryset.order_by('-created_at')[:50]
    return render(request, 'transactions/payment_link_list.html', {'payment_links': payment_links})
