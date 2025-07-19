from rest_framework import generics, status, filters, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
import logging

from .models import (
    Integration,
    MerchantIntegration,
    BankIntegration,
    IntegrationAPICall,
    IntegrationWebhook,
    IntegrationStatus,
    IntegrationType
)
from .serializers import (
    IntegrationListSerializer,
    IntegrationDetailSerializer,
    BankIntegrationSerializer,
    MerchantIntegrationListSerializer,
    MerchantIntegrationDetailSerializer,
    MerchantIntegrationCreateSerializer,
    MerchantIntegrationUpdateSerializer,
    IntegrationAPICallSerializer,
    IntegrationWebhookSerializer,
    UBAPaymentPageSerializer,
    UBAAccountInquirySerializer,
    UBAFundTransferSerializer,
    UBABalanceInquirySerializer,
    UBATransactionHistorySerializer,
    UBABillPaymentSerializer,
    UBAWebhookSerializer,
    CyberSourcePaymentSerializer,
    CyberSourceCaptureSerializer,
    CyberSourceRefundSerializer,
    CyberSourceCustomerSerializer,
    CyberSourceTokenSerializer,
    CyberSourceWebhookSerializer,
    CorefyPaymentIntentSerializer,
    CorefyConfirmPaymentSerializer,
    CorefyRefundSerializer,
    CorefyCustomerSerializer,
    CorefyPaymentMethodSerializer,
    CorefyWebhookSerializer,
    IntegrationChoiceSerializer,
    IntegrationStatsSerializer,
    IntegrationHealthSerializer
)
from .services import UBABankService, UBAAPIException, CyberSourceService, CyberSourceAPIException, CorefyService, CorefyAPIException
from authentication.models import Merchant
from authentication.api_auth import APIKeyAuthentication, APIKeyOrTokenAuthentication

logger = logging.getLogger(__name__)


class APIKeyPermission(permissions.BasePermission):
    """
    Custom permission class for API key authentication.
    Allows access to users authenticated via API key or regular authentication.
    """
    
    def has_permission(self, request, view):
        """
        Check if the request has permission to access the view.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # If user is authenticated via API key, check scopes
        if hasattr(request.user, '_api_key'):
            app_key = request.user._api_key
            
            # Check if the API key has the required scope for this operation
            if request.method in ['GET', 'HEAD', 'OPTIONS']:
                required_scope = 'read'
            elif request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                required_scope = 'write'
            else:
                required_scope = 'admin'
            
            return app_key.has_scope(required_scope)
        
        # For regular authenticated users, allow access
        return True


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for integrations API"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# Integration Views

class IntegrationListView(generics.ListAPIView):
    """List all available integrations"""
    serializer_class = IntegrationListSerializer
    authentication_classes = [APIKeyOrTokenAuthentication]
    permission_classes = [APIKeyPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['integration_type', 'status', 'is_sandbox', 'is_global']
    search_fields = ['name', 'provider_name', 'code']
    ordering_fields = ['name', 'provider_name', 'created_at']
    ordering = ['provider_name', 'name']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Get integrations available to the user"""
        # For API key users, show all global integrations
        if hasattr(self.request.user, '_api_key'):
            return Integration.objects.filter(is_global=True)
        
        # For regular users, show integrations they have access to
        user = self.request.user
        if hasattr(user, 'merchant_account'):
            queryset = Integration.objects.filter(
                Q(is_global=True) | Q(merchant_configurations__merchant=user.merchant_account)
            ).distinct()
        else:
            queryset = Integration.objects.filter(is_global=True)
        return queryset


class IntegrationDetailView(generics.RetrieveAPIView):
    """Get integration details"""
    serializer_class = IntegrationDetailSerializer
    authentication_classes = [APIKeyOrTokenAuthentication]
    permission_classes = [APIKeyPermission]
    lookup_field = 'id'

    def get_queryset(self):
        """Get integrations available to the user"""
        # For API key users, show all global integrations
        if hasattr(self.request.user, '_api_key'):
            return Integration.objects.filter(is_global=True)
        
        # For regular users, show integrations they have access to
        user = self.request.user
        if hasattr(user, 'merchant_account'):
            return Integration.objects.filter(
                Q(is_global=True) | Q(merchant_configurations__merchant=user.merchant_account)
            ).distinct()
        else:
            return Integration.objects.filter(is_global=True)


class BankIntegrationDetailView(generics.RetrieveAPIView):
    """Get bank integration details"""
    serializer_class = BankIntegrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'integration__id'

    def get_queryset(self):
        """Get bank integrations available to the user"""
        user = self.request.user
        return BankIntegration.objects.filter(
            Q(integration__is_global=True) | 
            Q(integration__merchant_configurations__merchant=user.merchant)
        ).distinct()


# Merchant Integration Views

class MerchantIntegrationListView(generics.ListCreateAPIView):
    """List and create merchant integrations"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_enabled', 'status', 'integration__integration_type']
    search_fields = ['integration__name', 'integration__provider_name']
    ordering_fields = ['created_at', 'last_used_at', 'total_requests']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MerchantIntegrationCreateSerializer
        return MerchantIntegrationListSerializer

    def get_queryset(self):
        """Get merchant's integrations"""
        return MerchantIntegration.objects.filter(
            merchant=self.request.user.merchant
        ).select_related('integration', 'merchant')


class MerchantIntegrationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete merchant integration"""
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return MerchantIntegrationUpdateSerializer
        return MerchantIntegrationDetailSerializer

    def get_queryset(self):
        """Get merchant's integrations"""
        return MerchantIntegration.objects.filter(
            merchant=self.request.user.merchant
        ).select_related('integration', 'merchant')


# API Call Views

class IntegrationAPICallListView(generics.ListAPIView):
    """List integration API calls"""
    serializer_class = IntegrationAPICallSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_successful', 'method', 'operation_type']
    ordering_fields = ['created_at', 'response_time_ms']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Get API calls for merchant's integrations"""
        return IntegrationAPICall.objects.filter(
            merchant_integration__merchant=self.request.user.merchant
        ).select_related('merchant_integration__integration')


# Webhook Views

class IntegrationWebhookListView(generics.ListAPIView):
    """List integration webhooks"""
    serializer_class = IntegrationWebhookSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_processed', 'is_verified', 'event_type']
    ordering_fields = ['created_at', 'processed_at']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Get webhooks for merchant's integrations"""
        return IntegrationWebhook.objects.filter(
            integration__merchant_configurations__merchant=self.request.user.merchant
        ).select_related('integration')


# UBA Bank Integration Views

@extend_schema(
    summary="Create UBA payment page",
    description="Create a payment page using UBA Kenya Pay integration",
    request=UBAPaymentPageSerializer,
    responses={201: OpenApiResponse(description="Payment page created successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uba_create_payment_page(request):
    """Create UBA payment page"""
    serializer = UBAPaymentPageSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # For API key users, we need to handle merchant differently
            merchant = None
            if hasattr(request.user, '_api_key'):
                # For API key authentication, we might need to create a virtual merchant
                # or use a default merchant associated with the partner
                # This depends on your business logic
                merchant = None  # You'll need to implement this based on your needs
            elif hasattr(request.user, 'merchant_account'):
                merchant = request.user.merchant_account
            
            uba_service = UBABankService(merchant=merchant)
            result = uba_service.create_payment_page(**serializer.validated_data)
            
            return Response({
                'success': True,
                'message': 'Payment page created successfully',
                'data': result
            }, status=status.HTTP_201_CREATED)
            
        except UBAAPIException as e:
            return Response({
                'success': False,
                'message': e.message,
                'error_code': e.error_code
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"UBA payment page creation error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get payment status",
    description="Get payment status from UBA",
    responses={200: OpenApiResponse(description="Payment status retrieved")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uba_get_payment_status(request, payment_id):
    """Get UBA payment status"""
    try:
        # Handle both API key and regular authentication
        merchant = None
        if hasattr(request.user, '_api_key'):
            merchant = None  # API key users can access without specific merchant
        elif hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        uba_service = UBABankService(merchant=merchant)
        result = uba_service.get_payment_status(payment_id)
        
        return Response({
            'success': True,
            'data': result
        }, status=status.HTTP_200_OK)
        
    except UBAAPIException as e:
        return Response({
            'success': False,
            'message': e.message,
            'error_code': e.error_code
        }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"UBA payment status error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Account inquiry",
    description="Perform account name inquiry using UBA",
    request=UBAAccountInquirySerializer,
    responses={200: OpenApiResponse(description="Account information retrieved")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uba_account_inquiry(request):
    """UBA account inquiry"""
    serializer = UBAAccountInquirySerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Handle both API key and regular authentication
            merchant = None
            if hasattr(request.user, '_api_key'):
                merchant = None  # API key users can access without specific merchant
            elif hasattr(request.user, 'merchant_account'):
                merchant = request.user.merchant_account
            
            uba_service = UBABankService(merchant=merchant)
            result = uba_service.account_inquiry(**serializer.validated_data)
            
            return Response({
                'success': True,
                'data': result
            }, status=status.HTTP_200_OK)
            
        except UBAAPIException as e:
            return Response({
                'success': False,
                'message': e.message,
                'error_code': e.error_code
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"UBA account inquiry error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Fund transfer",
    description="Perform fund transfer using UBA",
    request=UBAFundTransferSerializer,
    responses={201: OpenApiResponse(description="Fund transfer initiated")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uba_fund_transfer(request):
    """UBA fund transfer"""
    serializer = UBAFundTransferSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Handle both API key and regular authentication
            merchant = None
            if hasattr(request.user, '_api_key'):
                merchant = None  # API key users can access without specific merchant
            elif hasattr(request.user, 'merchant_account'):
                merchant = request.user.merchant_account
            
            uba_service = UBABankService(merchant=merchant)
            result = uba_service.fund_transfer(**serializer.validated_data)
            
            return Response({
                'success': True,
                'message': 'Fund transfer initiated successfully',
                'data': result
            }, status=status.HTTP_201_CREATED)
            
        except UBAAPIException as e:
            return Response({
                'success': False,
                'message': e.message,
                'error_code': e.error_code
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"UBA fund transfer error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Balance inquiry",
    description="Check account balance using UBA",
    request=UBABalanceInquirySerializer,
    responses={200: OpenApiResponse(description="Account balance retrieved")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uba_balance_inquiry(request):
    """UBA balance inquiry"""
    serializer = UBABalanceInquirySerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Handle both API key and regular authentication
            merchant = None
            if hasattr(request.user, '_api_key'):
                merchant = None  # API key users can access without specific merchant
            elif hasattr(request.user, 'merchant_account'):
                merchant = request.user.merchant_account
            
            uba_service = UBABankService(merchant=merchant)
            result = uba_service.balance_inquiry(**serializer.validated_data)
            
            return Response({
                'success': True,
                'data': result
            }, status=status.HTTP_200_OK)
            
        except UBAAPIException as e:
            return Response({
                'success': False,
                'message': e.message,
                'error_code': e.error_code
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"UBA balance inquiry error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Transaction history",
    description="Get transaction history using UBA",
    request=UBATransactionHistorySerializer,
    responses={200: OpenApiResponse(description="Transaction history retrieved")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uba_transaction_history(request):
    """UBA transaction history"""
    serializer = UBATransactionHistorySerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Handle both API key and regular authentication
            merchant = None
            if hasattr(request.user, '_api_key'):
                merchant = None  # API key users can access without specific merchant
            elif hasattr(request.user, 'merchant_account'):
                merchant = request.user.merchant_account
            
            uba_service = UBABankService(merchant=merchant)
            result = uba_service.get_transaction_history(**serializer.validated_data)
            
            return Response({
                'success': True,
                'data': result
            }, status=status.HTTP_200_OK)
            
        except UBAAPIException as e:
            return Response({
                'success': False,
                'message': e.message,
                'error_code': e.error_code
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"UBA transaction history error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Bill payment",
    description="Pay bills using UBA",
    request=UBABillPaymentSerializer,
    responses={201: OpenApiResponse(description="Bill payment initiated")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uba_bill_payment(request):
    """UBA bill payment"""
    serializer = UBABillPaymentSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Handle both API key and regular authentication
            merchant = None
            if hasattr(request.user, '_api_key'):
                merchant = None  # API key users can access without specific merchant
            elif hasattr(request.user, 'merchant_account'):
                merchant = request.user.merchant_account
            
            uba_service = UBABankService(merchant=merchant)
            result = uba_service.bill_payment(**serializer.validated_data)
            
            return Response({
                'success': True,
                'message': 'Bill payment initiated successfully',
                'data': result
            }, status=status.HTTP_201_CREATED)
            
        except UBAAPIException as e:
            return Response({
                'success': False,
                'message': e.message,
                'error_code': e.error_code
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"UBA bill payment error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="UBA webhook handler",
    description="Handle webhooks from UBA",
    request=UBAWebhookSerializer,
    responses={200: OpenApiResponse(description="Webhook processed")}
)
@api_view(['POST'])
@permission_classes([])  # No authentication for webhooks
def uba_webhook_handler(request):
    """Handle UBA webhooks"""
    try:
        # Get UBA integration
        uba_integration = Integration.objects.get(code='uba_kenya')
        
        # Create webhook record
        webhook = IntegrationWebhook.objects.create(
            integration=uba_integration,
            event_type=request.data.get('event_type', 'unknown'),
            payload=request.data,
            headers=dict(request.headers),
            source_ip=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Validate webhook signature if provided
        signature = request.headers.get('X-UBA-Signature')
        if signature:
            uba_service = UBABankService()
            is_valid = uba_service.validate_webhook(request.data, signature)
            webhook.is_verified = is_valid
            webhook.verification_method = 'signature'
            webhook.save()
            
            if not is_valid:
                return Response({
                    'success': False,
                    'message': 'Invalid webhook signature'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process webhook (implement your business logic here)
        # For now, just mark as processed
        webhook.mark_as_processed()
        
        return Response({
            'success': True,
            'message': 'Webhook processed successfully'
        }, status=status.HTTP_200_OK)
        
    except Integration.DoesNotExist:
        return Response({
            'success': False,
            'message': 'UBA integration not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"UBA webhook processing error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Webhook processing failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Test UBA connection",
    description="Test connection to UBA API",
    responses={200: OpenApiResponse(description="Connection test result")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uba_test_connection(request):
    """Test UBA API connection"""
    try:
        # Handle both API key and regular authentication
        merchant = None
        if hasattr(request.user, '_api_key'):
            merchant = None  # API key users can access without specific merchant
        elif hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        uba_service = UBABankService(merchant=merchant)
        result = uba_service.test_connection()
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"UBA connection test error: {str(e)}")
        return Response({
            'success': False,
            'message': f'Connection test failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# CyberSource Views

@extend_schema(
    summary="Create CyberSource payment",
    description="Process a payment through CyberSource",
    request=CyberSourcePaymentSerializer,
    responses={201: OpenApiResponse(description="Payment processed successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def cybersource_create_payment(request):
    """Create CyberSource payment"""
    serializer = CyberSourcePaymentSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # For API key users, we need to handle merchant differently
            merchant = None
            if hasattr(request.user, '_api_key'):
                merchant = None  # You'll need to implement this based on your needs
            elif hasattr(request.user, 'merchant_account'):
                merchant = request.user.merchant_account
            
            cybersource_service = CyberSourceService(merchant=merchant)
            result = cybersource_service.create_payment(**serializer.validated_data)
            
            return Response({
                'success': True,
                'message': 'Payment processed successfully',
                'data': result
            }, status=status.HTTP_201_CREATED)
            
        except CyberSourceAPIException as e:
            return Response({
                'success': False,
                'message': e.message,
                'error_code': e.error_code
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"CyberSource payment error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Capture CyberSource payment",
    description="Capture a previously authorized payment",
    request=CyberSourceCaptureSerializer,
    responses={200: OpenApiResponse(description="Payment captured successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def cybersource_capture_payment(request):
    """Capture CyberSource payment"""
    serializer = CyberSourceCaptureSerializer(data=request.data)
    if serializer.is_valid():
        try:
            merchant = None
            if hasattr(request.user, '_api_key'):
                merchant = None
            elif hasattr(request.user, 'merchant_account'):
                merchant = request.user.merchant_account
            
            cybersource_service = CyberSourceService(merchant=merchant)
            result = cybersource_service.capture_payment(
                payment_id=serializer.validated_data['payment_id'],
                amount=serializer.validated_data.get('amount'),
                currency=serializer.validated_data.get('currency', 'USD')
            )
            
            return Response({
                'success': True,
                'message': 'Payment captured successfully',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except CyberSourceAPIException as e:
            return Response({
                'success': False,
                'message': e.message,
                'error_code': e.error_code
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"CyberSource capture error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Refund CyberSource payment",
    description="Refund a processed payment",
    request=CyberSourceRefundSerializer,
    responses={200: OpenApiResponse(description="Payment refunded successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def cybersource_refund_payment(request):
    """Refund CyberSource payment"""
    serializer = CyberSourceRefundSerializer(data=request.data)
    if serializer.is_valid():
        try:
            merchant = None
            if hasattr(request.user, '_api_key'):
                merchant = None
            elif hasattr(request.user, 'merchant_account'):
                merchant = request.user.merchant_account
            
            cybersource_service = CyberSourceService(merchant=merchant)
            result = cybersource_service.refund_payment(
                payment_id=serializer.validated_data['payment_id'],
                amount=serializer.validated_data.get('amount'),
                currency=serializer.validated_data.get('currency', 'USD'),
                reason=serializer.validated_data.get('reason', '')
            )
            
            return Response({
                'success': True,
                'message': 'Payment refunded successfully',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except CyberSourceAPIException as e:
            return Response({
                'success': False,
                'message': e.message,
                'error_code': e.error_code
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"CyberSource refund error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get CyberSource payment status",
    description="Get payment status from CyberSource",
    responses={200: OpenApiResponse(description="Payment status retrieved")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def cybersource_get_payment_status(request, payment_id):
    """Get CyberSource payment status"""
    try:
        merchant = None
        if hasattr(request.user, '_api_key'):
            merchant = None
        elif hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        cybersource_service = CyberSourceService(merchant=merchant)
        result = cybersource_service.get_payment_status(payment_id)
        
        return Response({
            'success': True,
            'data': result
        }, status=status.HTTP_200_OK)
        
    except CyberSourceAPIException as e:
        return Response({
            'success': False,
            'message': e.message,
            'error_code': e.error_code
        }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"CyberSource payment status error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Create CyberSource customer profile",
    description="Create a customer profile for tokenization",
    request=CyberSourceCustomerSerializer,
    responses={201: OpenApiResponse(description="Customer profile created successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def cybersource_create_customer(request):
    """Create CyberSource customer profile"""
    serializer = CyberSourceCustomerSerializer(data=request.data)
    if serializer.is_valid():
        try:
            merchant = None
            if hasattr(request.user, '_api_key'):
                merchant = None
            elif hasattr(request.user, 'merchant_account'):
                merchant = request.user.merchant_account
            
            cybersource_service = CyberSourceService(merchant=merchant)
            
            # Build billing address from serializer data
            billing_address = {}
            for field, value in serializer.validated_data.items():
                if field.startswith('billing_'):
                    billing_address[field.replace('billing_', '')] = value
            
            result = cybersource_service.create_customer_profile(
                customer_id=serializer.validated_data['customer_id'],
                email=serializer.validated_data.get('email'),
                phone=serializer.validated_data.get('phone'),
                billing_address=billing_address if billing_address else None
            )
            
            return Response({
                'success': True,
                'message': 'Customer profile created successfully',
                'data': result
            }, status=status.HTTP_201_CREATED)
            
        except CyberSourceAPIException as e:
            return Response({
                'success': False,
                'message': e.message,
                'error_code': e.error_code
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"CyberSource customer creation error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Create CyberSource payment token",
    description="Create a payment token for card storage",
    request=CyberSourceTokenSerializer,
    responses={201: OpenApiResponse(description="Payment token created successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def cybersource_create_token(request):
    """Create CyberSource payment token"""
    serializer = CyberSourceTokenSerializer(data=request.data)
    if serializer.is_valid():
        try:
            merchant = None
            if hasattr(request.user, '_api_key'):
                merchant = None
            elif hasattr(request.user, 'merchant_account'):
                merchant = request.user.merchant_account
            
            cybersource_service = CyberSourceService(merchant=merchant)
            result = cybersource_service.create_payment_token(**serializer.validated_data)
            
            return Response({
                'success': True,
                'message': 'Payment token created successfully',
                'data': result
            }, status=status.HTTP_201_CREATED)
            
        except CyberSourceAPIException as e:
            return Response({
                'success': False,
                'message': e.message,
                'error_code': e.error_code
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"CyberSource token creation error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="CyberSource webhook handler",
    description="Handle webhook notifications from CyberSource",
    request=CyberSourceWebhookSerializer,
    responses={200: OpenApiResponse(description="Webhook processed successfully")}
)
@api_view(['POST'])
@permission_classes([])  # No authentication required for webhooks
def cybersource_webhook_handler(request):
    """Handle CyberSource webhook notifications"""
    serializer = CyberSourceWebhookSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Process webhook data
            event_type = serializer.validated_data['eventType']
            event_id = serializer.validated_data['eventId']
            payload = serializer.validated_data['payload']
            
            logger.info(f"CyberSource webhook received: {event_type} - {event_id}")
            
            # Here you would implement your webhook processing logic
            # For example, updating payment status, sending notifications, etc.
            
            return Response({
                'success': True,
                'message': 'Webhook processed successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"CyberSource webhook error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Webhook processing failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Test CyberSource connection",
    description="Test connection to CyberSource API",
    responses={200: OpenApiResponse(description="Connection test result")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def cybersource_test_connection(request):
    """Test CyberSource API connection"""
    try:
        merchant = None
        if hasattr(request.user, '_api_key'):
            merchant = None
        elif hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        cybersource_service = CyberSourceService(merchant=merchant)
        result = cybersource_service.test_connection()
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"CyberSource connection test error: {str(e)}")
        return Response({
            'success': False,
            'message': f'Connection test failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Statistics and Analytics

@extend_schema(
    summary="Get integration statistics",
    description="Get statistics for merchant's integrations",
    responses={200: IntegrationStatsSerializer}
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def integration_stats(request):
    """Get integration statistics for merchant"""
    merchant = request.user.merchant
    today = timezone.now().date()
    
    # Basic counts
    total_integrations = Integration.objects.filter(
        Q(is_global=True) | Q(merchant_configurations__merchant=merchant)
    ).distinct().count()
    
    active_integrations = Integration.objects.filter(
        Q(is_global=True) | Q(merchant_configurations__merchant=merchant),
        status=IntegrationStatus.ACTIVE
    ).distinct().count()
    
    enabled_merchant_integrations = MerchantIntegration.objects.filter(
        merchant=merchant,
        is_enabled=True
    ).count()
    
    # API call statistics for today
    api_calls_today = IntegrationAPICall.objects.filter(
        merchant_integration__merchant=merchant,
        created_at__date=today
    )
    
    total_api_calls_today = api_calls_today.count()
    successful_api_calls_today = api_calls_today.filter(is_successful=True).count()
    failed_api_calls_today = api_calls_today.filter(is_successful=False).count()
    
    success_rate_today = 0
    if total_api_calls_today > 0:
        success_rate_today = (successful_api_calls_today / total_api_calls_today) * 100
    
    # Average response time
    avg_response_time = api_calls_today.filter(
        response_time_ms__isnull=False
    ).aggregate(avg=Avg('response_time_ms'))['avg'] or 0
    
    # Most used integration and operation
    most_used_integration = api_calls_today.values(
        'merchant_integration__integration__name'
    ).annotate(count=Count('id')).order_by('-count').first()
    
    most_used_operation = api_calls_today.values(
        'operation_type'
    ).annotate(count=Count('id')).order_by('-count').first()
    
    stats = {
        'total_integrations': total_integrations,
        'active_integrations': active_integrations,
        'enabled_merchant_integrations': enabled_merchant_integrations,
        'total_api_calls_today': total_api_calls_today,
        'successful_api_calls_today': successful_api_calls_today,
        'failed_api_calls_today': failed_api_calls_today,
        'success_rate_today': round(success_rate_today, 2),
        'avg_response_time_ms': round(avg_response_time, 2),
        'most_used_integration': most_used_integration['merchant_integration__integration__name'] if most_used_integration else 'None',
        'most_used_operation': most_used_operation['operation_type'] if most_used_operation else 'None'
    }
    
    serializer = IntegrationStatsSerializer(stats)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get integration health status",
    description="Get health status for merchant's integrations",
    responses={200: IntegrationHealthSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def integration_health(request):
    """Get health status for merchant's integrations"""
    merchant = request.user.merchant
    
    merchant_integrations = MerchantIntegration.objects.filter(
        merchant=merchant
    ).select_related('integration')
    
    health_data = []
    for mi in merchant_integrations:
        health_data.append({
            'integration_id': mi.integration.id,
            'integration_name': mi.integration.name,
            'provider_name': mi.integration.provider_name,
            'is_healthy': mi.is_healthy(),
            'last_health_check': mi.integration.last_health_check,
            'health_error_message': mi.integration.health_error_message,
            'status': mi.status,
            'consecutive_failures': mi.consecutive_failures,
            'success_rate': mi.get_success_rate()
        })
    
    serializer = IntegrationHealthSerializer(health_data, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Choice endpoints

@extend_schema(
    summary="Get integration type choices",
    description="Get available integration type choices",
    responses={200: IntegrationChoiceSerializer(many=True)}
)
@api_view(['GET'])
def integration_type_choices(request):
    """Get integration type choices"""
    choices = [
        {'value': choice[0], 'display': choice[1]}
        for choice in IntegrationType.choices
    ]
    return Response(choices)


@extend_schema(
    summary="Get integration status choices",
    description="Get available integration status choices",
    responses={200: IntegrationChoiceSerializer(many=True)}
)
@api_view(['GET'])
def integration_status_choices(request):
    """Get integration status choices"""
    choices = [
        {'value': choice[0], 'display': choice[1]}
        for choice in IntegrationStatus.choices
    ]
    return Response(choices)


# Corefy Views

@extend_schema(
    summary="Create Corefy payment intent",
    description="Create a payment intent with Corefy",
    request=CorefyPaymentIntentSerializer,
    responses={
        200: OpenApiResponse(description="Payment intent created successfully"),
        400: OpenApiResponse(description="Invalid request data"),
        500: OpenApiResponse(description="Internal server error")
    }
)
@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def corefy_create_payment_intent(request):
    """Create Corefy payment intent"""
    serializer = CorefyPaymentIntentSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'error': 'Invalid request data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get merchant from API key
        merchant = getattr(request.user, 'merchant', None)
        if not merchant:
            return Response({
                'error': 'Merchant not found for this API key'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Corefy service
        corefy_service = CorefyService(merchant=merchant)
        
        # Extract validated data
        validated_data = serializer.validated_data
        
        # Build metadata from request
        metadata = validated_data.get('metadata', {})
        if validated_data.get('billing_first_name'):
            metadata.update({
                'billing_address': {
                    'first_name': validated_data.get('billing_first_name'),
                    'last_name': validated_data.get('billing_last_name'),
                    'address_line1': validated_data.get('billing_address_line1'),
                    'address_line2': validated_data.get('billing_address_line2'),
                    'city': validated_data.get('billing_city'),
                    'state': validated_data.get('billing_state'),
                    'postal_code': validated_data.get('billing_postal_code'),
                    'country': validated_data.get('billing_country'),
                }
            })
        
        # Create payment intent
        result = corefy_service.create_payment_intent(
            amount=validated_data['amount'],
            currency=validated_data['currency'],
            payment_method=validated_data.get('payment_method', 'card'),
            customer_id=validated_data.get('customer_id'),
            description=validated_data.get('description'),
            metadata=metadata,
            return_url=validated_data.get('return_url'),
            failure_url=validated_data.get('failure_url'),
            reference_id=validated_data.get('reference_id')
        )
        
        return Response({
            'status': 'success',
            'message': 'Payment intent created successfully',
            'data': result
        })
        
    except CorefyAPIException as e:
        logger.error(f"Corefy payment intent error: {str(e)}")
        return Response({
            'error': str(e),
            'error_code': getattr(e, 'error_code', 'corefy_error')
        }, status=getattr(e, 'status_code', 500))
    
    except Exception as e:
        logger.error(f"Corefy payment intent error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Confirm Corefy payment",
    description="Confirm a payment intent with payment details",
    request=CorefyConfirmPaymentSerializer,
    responses={
        200: OpenApiResponse(description="Payment confirmed successfully"),
        400: OpenApiResponse(description="Invalid request data"),
        500: OpenApiResponse(description="Internal server error")
    }
)
@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def corefy_confirm_payment(request):
    """Confirm Corefy payment"""
    serializer = CorefyConfirmPaymentSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'error': 'Invalid request data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get merchant from API key
        merchant = getattr(request.user, 'merchant', None)
        if not merchant:
            return Response({
                'error': 'Merchant not found for this API key'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Corefy service
        corefy_service = CorefyService(merchant=merchant)
        
        # Extract validated data
        validated_data = serializer.validated_data
        payment_intent_id = validated_data.pop('payment_intent_id')
        
        # Confirm payment intent
        result = corefy_service.confirm_payment_intent(
            payment_intent_id=payment_intent_id,
            payment_data=validated_data
        )
        
        return Response({
            'status': 'success',
            'message': 'Payment confirmed successfully',
            'data': result
        })
        
    except CorefyAPIException as e:
        logger.error(f"Corefy payment confirmation error: {str(e)}")
        return Response({
            'error': str(e),
            'error_code': getattr(e, 'error_code', 'corefy_error')
        }, status=getattr(e, 'status_code', 500))
    
    except Exception as e:
        logger.error(f"Corefy payment confirmation error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get Corefy payment status",
    description="Get the status of a Corefy payment",
    responses={
        200: OpenApiResponse(description="Payment status retrieved successfully"),
        404: OpenApiResponse(description="Payment not found"),
        500: OpenApiResponse(description="Internal server error")
    }
)
@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def corefy_get_payment_status(request, payment_id):
    """Get Corefy payment status"""
    try:
        # Get merchant from API key
        merchant = getattr(request.user, 'merchant', None)
        if not merchant:
            return Response({
                'error': 'Merchant not found for this API key'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Corefy service
        corefy_service = CorefyService(merchant=merchant)
        
        # Get payment status
        result = corefy_service.get_payment_status(payment_id)
        
        return Response({
            'status': 'success',
            'message': 'Payment status retrieved successfully',
            'data': result
        })
        
    except CorefyAPIException as e:
        logger.error(f"Corefy payment status error: {str(e)}")
        return Response({
            'error': str(e),
            'error_code': getattr(e, 'error_code', 'corefy_error')
        }, status=getattr(e, 'status_code', 500))
    
    except Exception as e:
        logger.error(f"Corefy payment status error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Create Corefy refund",
    description="Create a refund for a Corefy payment",
    request=CorefyRefundSerializer,
    responses={
        200: OpenApiResponse(description="Refund created successfully"),
        400: OpenApiResponse(description="Invalid request data"),
        500: OpenApiResponse(description="Internal server error")
    }
)
@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def corefy_create_refund(request):
    """Create Corefy refund"""
    serializer = CorefyRefundSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'error': 'Invalid request data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get merchant from API key
        merchant = getattr(request.user, 'merchant', None)
        if not merchant:
            return Response({
                'error': 'Merchant not found for this API key'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Corefy service
        corefy_service = CorefyService(merchant=merchant)
        
        # Create refund
        result = corefy_service.create_refund(**serializer.validated_data)
        
        return Response({
            'status': 'success',
            'message': 'Refund created successfully',
            'data': result
        })
        
    except CorefyAPIException as e:
        logger.error(f"Corefy refund error: {str(e)}")
        return Response({
            'error': str(e),
            'error_code': getattr(e, 'error_code', 'corefy_error')
        }, status=getattr(e, 'status_code', 500))
    
    except Exception as e:
        logger.error(f"Corefy refund error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Create Corefy customer",
    description="Create a customer profile in Corefy",
    request=CorefyCustomerSerializer,
    responses={
        200: OpenApiResponse(description="Customer created successfully"),
        400: OpenApiResponse(description="Invalid request data"),
        500: OpenApiResponse(description="Internal server error")
    }
)
@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def corefy_create_customer(request):
    """Create Corefy customer"""
    serializer = CorefyCustomerSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'error': 'Invalid request data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get merchant from API key
        merchant = getattr(request.user, 'merchant', None)
        if not merchant:
            return Response({
                'error': 'Merchant not found for this API key'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Corefy service
        corefy_service = CorefyService(merchant=merchant)
        
        # Extract validated data
        validated_data = serializer.validated_data
        
        # Build metadata from address fields
        metadata = validated_data.get('metadata', {})
        if validated_data.get('address_line1'):
            metadata['address'] = {
                'line1': validated_data.get('address_line1'),
                'line2': validated_data.get('address_line2'),
                'city': validated_data.get('city'),
                'state': validated_data.get('state'),
                'postal_code': validated_data.get('postal_code'),
                'country': validated_data.get('country'),
            }
        
        # Create customer
        result = corefy_service.create_customer(
            email=validated_data['email'],
            name=validated_data.get('name'),
            phone=validated_data.get('phone'),
            metadata=metadata,
            reference_id=validated_data.get('reference_id')
        )
        
        return Response({
            'status': 'success',
            'message': 'Customer created successfully',
            'data': result
        })
        
    except CorefyAPIException as e:
        logger.error(f"Corefy customer creation error: {str(e)}")
        return Response({
            'error': str(e),
            'error_code': getattr(e, 'error_code', 'corefy_error')
        }, status=getattr(e, 'status_code', 500))
    
    except Exception as e:
        logger.error(f"Corefy customer creation error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get Corefy customer",
    description="Get customer details from Corefy",
    responses={
        200: OpenApiResponse(description="Customer retrieved successfully"),
        404: OpenApiResponse(description="Customer not found"),
        500: OpenApiResponse(description="Internal server error")
    }
)
@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def corefy_get_customer(request, customer_id):
    """Get Corefy customer"""
    try:
        # Get merchant from API key
        merchant = getattr(request.user, 'merchant', None)
        if not merchant:
            return Response({
                'error': 'Merchant not found for this API key'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Corefy service
        corefy_service = CorefyService(merchant=merchant)
        
        # Get customer
        result = corefy_service.get_customer(customer_id)
        
        return Response({
            'status': 'success',
            'message': 'Customer retrieved successfully',
            'data': result
        })
        
    except CorefyAPIException as e:
        logger.error(f"Corefy get customer error: {str(e)}")
        return Response({
            'error': str(e),
            'error_code': getattr(e, 'error_code', 'corefy_error')
        }, status=getattr(e, 'status_code', 500))
    
    except Exception as e:
        logger.error(f"Corefy get customer error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Create Corefy payment method",
    description="Create a payment method for a customer",
    request=CorefyPaymentMethodSerializer,
    responses={
        200: OpenApiResponse(description="Payment method created successfully"),
        400: OpenApiResponse(description="Invalid request data"),
        500: OpenApiResponse(description="Internal server error")
    }
)
@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def corefy_create_payment_method(request):
    """Create Corefy payment method"""
    serializer = CorefyPaymentMethodSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'error': 'Invalid request data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get merchant from API key
        merchant = getattr(request.user, 'merchant', None)
        if not merchant:
            return Response({
                'error': 'Merchant not found for this API key'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Corefy service
        corefy_service = CorefyService(merchant=merchant)
        
        # Extract validated data
        validated_data = serializer.validated_data
        customer_id = validated_data.pop('customer_id')
        payment_method_type = validated_data.pop('payment_method_type', 'card')
        
        # Build payment method data
        payment_method_data = validated_data.get('payment_method_data', {})
        if payment_method_type == 'card' and validated_data.get('card_number'):
            payment_method_data = {
                'card_number': validated_data['card_number'],
                'expiry_month': validated_data['card_expiry_month'],
                'expiry_year': validated_data['card_expiry_year'],
                'holder_name': validated_data.get('card_holder_name')
            }
        
        # Create payment method
        result = corefy_service.create_payment_method(
            customer_id=customer_id,
            payment_method_type=payment_method_type,
            payment_method_data=payment_method_data
        )
        
        return Response({
            'status': 'success',
            'message': 'Payment method created successfully',
            'data': result
        })
        
    except CorefyAPIException as e:
        logger.error(f"Corefy payment method creation error: {str(e)}")
        return Response({
            'error': str(e),
            'error_code': getattr(e, 'error_code', 'corefy_error')
        }, status=getattr(e, 'status_code', 500))
    
    except Exception as e:
        logger.error(f"Corefy payment method creation error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get Corefy payment methods",
    description="Get payment methods for a customer",
    responses={
        200: OpenApiResponse(description="Payment methods retrieved successfully"),
        404: OpenApiResponse(description="Customer not found"),
        500: OpenApiResponse(description="Internal server error")
    }
)
@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def corefy_get_payment_methods(request, customer_id):
    """Get Corefy payment methods for customer"""
    try:
        # Get merchant from API key
        merchant = getattr(request.user, 'merchant', None)
        if not merchant:
            return Response({
                'error': 'Merchant not found for this API key'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Corefy service
        corefy_service = CorefyService(merchant=merchant)
        
        # Get payment methods
        result = corefy_service.get_payment_methods(customer_id)
        
        return Response({
            'status': 'success',
            'message': 'Payment methods retrieved successfully',
            'data': result
        })
        
    except CorefyAPIException as e:
        logger.error(f"Corefy get payment methods error: {str(e)}")
        return Response({
            'error': str(e),
            'error_code': getattr(e, 'error_code', 'corefy_error')
        }, status=getattr(e, 'status_code', 500))
    
    except Exception as e:
        logger.error(f"Corefy get payment methods error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get supported payment methods",
    description="Get list of supported payment methods from Corefy",
    responses={
        200: OpenApiResponse(description="Supported payment methods retrieved successfully"),
        500: OpenApiResponse(description="Internal server error")
    }
)
@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def corefy_get_supported_payment_methods(request):
    """Get supported payment methods"""
    try:
        # Get merchant from API key
        merchant = getattr(request.user, 'merchant', None)
        if not merchant:
            return Response({
                'error': 'Merchant not found for this API key'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Corefy service
        corefy_service = CorefyService(merchant=merchant)
        
        # Get supported payment methods
        result = corefy_service.get_supported_payment_methods()
        
        return Response({
            'status': 'success',
            'message': 'Supported payment methods retrieved successfully',
            'data': result
        })
        
    except CorefyAPIException as e:
        logger.error(f"Corefy get supported methods error: {str(e)}")
        return Response({
            'error': str(e),
            'error_code': getattr(e, 'error_code', 'corefy_error')
        }, status=getattr(e, 'status_code', 500))
    
    except Exception as e:
        logger.error(f"Corefy get supported methods error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Handle Corefy webhook",
    description="Process webhook notifications from Corefy",
    request=CorefyWebhookSerializer,
    responses={
        200: OpenApiResponse(description="Webhook processed successfully"),
        400: OpenApiResponse(description="Invalid webhook data"),
        500: OpenApiResponse(description="Internal server error")
    }
)
@api_view(['POST'])
@csrf_exempt
def corefy_webhook_handler(request):
    """Handle Corefy webhook notifications"""
    try:
        # Get raw payload and signature
        payload = request.body.decode('utf-8')
        signature = request.headers.get('X-Signature', '')
        
        if not signature:
            return Response({
                'error': 'Missing webhook signature'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Corefy service (without merchant for webhook validation)
        corefy_service = CorefyService()
        
        # Process webhook
        webhook_data = corefy_service.process_webhook(payload, signature)
        
        logger.info(f"Processed Corefy webhook: {webhook_data.get('event_type')}")
        
        return Response({
            'status': 'success',
            'message': 'Webhook processed successfully'
        })
        
    except CorefyAPIException as e:
        logger.error(f"Corefy webhook error: {str(e)}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Corefy webhook processing error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Test Corefy connection",
    description="Test the connection to Corefy API",
    responses={
        200: OpenApiResponse(description="Connection test successful"),
        500: OpenApiResponse(description="Connection test failed")
    }
)
@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def corefy_test_connection(request):
    """Test Corefy API connection"""
    try:
        # Get merchant from API key
        merchant = getattr(request.user, 'merchant', None)
        if not merchant:
            return Response({
                'error': 'Merchant not found for this API key'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Corefy service
        corefy_service = CorefyService(merchant=merchant)
        
        # Test connection
        result = corefy_service.test_connection()
        
        if result['success']:
            return Response({
                'status': 'success',
                'message': 'Corefy connection test successful',
                'data': result
            })
        else:
            return Response({
                'status': 'failed',
                'message': 'Corefy connection test failed',
                'error': result.get('error'),
                'data': result
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Corefy connection test error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Alias for backward compatibility (if something is trying to import MerchantIntegrationCreateView)
MerchantIntegrationCreateView = MerchantIntegrationListView
