from rest_framework import generics, status, filters, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, filters, permissions, status
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
import logging
import uuid

from .models import (
    Integration,
    MerchantIntegration,
    BankIntegration,
    IntegrationProvider,
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
from .uba_usage import UBAUsageService
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


# Dashboard Settings Views
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


@login_required
def integration_settings_view(request):
    """Integration settings page for merchants"""
    # Check if user has merchant account
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        messages.error(request, "Access denied. Merchant account required.")
        return redirect('dashboard:dashboard_redirect')
    
    merchant = request.user.merchant_account
    
    # Get available integrations
    available_integrations = Integration.objects.filter(
        Q(is_global=True) | Q(status=IntegrationStatus.ACTIVE)
    ).order_by('integration_type', 'provider_name')
    
    # Get merchant's current integrations
    merchant_integrations = MerchantIntegration.objects.filter(
        merchant=merchant
    ).select_related('integration').order_by('-updated_at')
    
    # Get integration statistics
    integration_stats = {
        'total_available': available_integrations.count(),
        'total_configured': merchant_integrations.count(),
        'active_integrations': merchant_integrations.filter(is_enabled=True).count(),
        'by_type': available_integrations.values('integration_type').annotate(
            count=Count('id')
        ).order_by('integration_type')
    }
    
    # Add validation status for integrations
    from django.conf import settings
    import os
    
    validation_status = {
        'uba_bank': {
            'configured': bool(os.getenv('UBA_BASE_URL') and os.getenv('UBA_ACCESS_TOKEN')),
            'feature_enabled': getattr(settings, 'ENABLE_UBA_INTEGRATION', False),
            'api_key_set': bool(os.getenv('UBA_ACCESS_TOKEN')),
            'base_url_set': bool(os.getenv('UBA_BASE_URL')),
            'sandbox_mode': getattr(settings, 'UBA_SANDBOX', True),
        },
        'cybersource': {
            'configured': bool(os.getenv('CYBERSOURCE_MERCHANT_ID') and os.getenv('CYBERSOURCE_API_KEY')),
            'feature_enabled': getattr(settings, 'ENABLE_CYBERSOURCE_INTEGRATION', False),
            'merchant_id_set': bool(os.getenv('CYBERSOURCE_MERCHANT_ID')),
            'api_key_set': bool(os.getenv('CYBERSOURCE_API_KEY')),
            'sandbox_mode': getattr(settings, 'CYBERSOURCE_SANDBOX', True),
        },
        'corefy': {
            'configured': bool(os.getenv('COREFY_API_KEY') and os.getenv('COREFY_SECRET_KEY')),
            'feature_enabled': getattr(settings, 'ENABLE_COREFY_INTEGRATION', False),
            'api_key_set': bool(os.getenv('COREFY_API_KEY')),
            'secret_key_set': bool(os.getenv('COREFY_SECRET_KEY')),
            'sandbox_mode': getattr(settings, 'COREFY_SANDBOX', True),
        },
        'global_settings': {
            'health_check_enabled': bool(os.getenv('INTEGRATION_HEALTH_CHECK_INTERVAL')),
            'request_logging': getattr(settings, 'INTEGRATION_LOG_REQUESTS', False),
            'response_logging': getattr(settings, 'INTEGRATION_LOG_RESPONSES', False),
        }
    }
    
    context = {
        'page_title': 'Integration Settings',
        'available_integrations': available_integrations,
        'merchant_integrations': merchant_integrations,
        'integration_stats': integration_stats,
        'integration_types': IntegrationType.choices,
        'integration_statuses': IntegrationStatus.choices,
        'merchant': merchant,
        'validation_status': validation_status,
    }
    
    return render(request, 'integrations/settings.html', context)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def configure_integration_api(request):
    """API endpoint to configure a new integration for merchant"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        data = json.loads(request.body)
        integration_id = data.get('integration_id')
        configuration = data.get('configuration', {})
        credentials = data.get('credentials', {})
        
        if not integration_id:
            return JsonResponse({'error': 'Integration ID is required'}, status=400)
        
        # Get the integration
        try:
            integration = Integration.objects.get(id=integration_id)
        except Integration.DoesNotExist:
            return JsonResponse({'error': 'Integration not found'}, status=404)
        
        merchant = request.user.merchant_account
        
        # Create or update merchant integration
        merchant_integration, created = MerchantIntegration.objects.get_or_create(
            merchant=merchant,
            integration=integration,
            defaults={
                'configuration': configuration,
                'is_enabled': False,
                'status': IntegrationStatus.DRAFT
            }
        )
        
        if not created:
            # Update existing integration
            merchant_integration.configuration.update(configuration)
            merchant_integration.save()
        
        # Encrypt and store credentials if provided
        if credentials:
            # Handle UBA-specific credentials
            if integration.code == 'uba_kenya_pay':
                uba_credentials = {
                    'access_token': credentials.get('access_token'),
                    'configuration_id': credentials.get('configuration_id'),
                    'customization_id': credentials.get('customization_id')
                }
                merchant_integration.encrypt_credentials(uba_credentials)
            else:
                # Handle generic credentials
                merchant_integration.encrypt_credentials(credentials)
            merchant_integration.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Integration {integration.name} configured successfully',
            'integration_id': str(merchant_integration.id),
            'created': created
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error configuring integration: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def toggle_integration_api(request, integration_id):
    """API endpoint to enable/disable an integration"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        merchant = request.user.merchant_account
        merchant_integration = MerchantIntegration.objects.get(
            id=integration_id,
            merchant=merchant
        )
        
        # Toggle enabled status
        merchant_integration.is_enabled = not merchant_integration.is_enabled
        merchant_integration.status = IntegrationStatus.ACTIVE if merchant_integration.is_enabled else IntegrationStatus.INACTIVE
        merchant_integration.save()
        
        return JsonResponse({
            'success': True,
            'enabled': merchant_integration.is_enabled,
            'status': merchant_integration.status,
            'message': f'Integration {"enabled" if merchant_integration.is_enabled else "disabled"} successfully'
        })
        
    except MerchantIntegration.DoesNotExist:
        return JsonResponse({'error': 'Integration not found'}, status=404)
    except Exception as e:
        logger.error(f"Corefy webhook processing error: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


# Enhanced Integration Management Views

@extend_schema(
    summary="List integration providers",
    description="Get list of available integration providers with their configurations",
    responses={200: OpenApiResponse(description="List of integration providers")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_providers_list(request):
    """List all available integration providers"""
    try:
        # Get integrations with their provider configurations
        integrations = Integration.objects.filter(
            status=IntegrationStatus.ACTIVE,
            is_global=True
        ).select_related('provider_config').order_by('provider_name', 'name')
        
        providers_data = []
        for integration in integrations:
            provider_data = {
                'id': str(integration.id),
                'name': integration.name,
                'code': integration.code,
                'provider_name': integration.provider_name,
                'integration_type': integration.integration_type,
                'description': integration.description,
                'supports_webhooks': integration.supports_webhooks,
                'supports_bulk_operations': integration.supports_bulk_operations,
                'supports_real_time': integration.supports_real_time,
                'is_sandbox': integration.is_sandbox,
                'version': integration.version,
                'authentication_type': integration.authentication_type,
            }
            
            # Add provider-specific configuration if available
            if hasattr(integration, 'provider_config'):
                provider_config = integration.provider_config
                provider_data.update({
                    'supported_operations': provider_config.supported_operations,
                    'endpoints': provider_config.endpoints,
                    'fee_structure': provider_config.fee_structure,
                    'limits': provider_config.limits,
                    'webhook_config': provider_config.webhook_config,
                })
            
            providers_data.append(provider_data)
        
        return Response({
            'success': True,
            'count': len(providers_data),
            'data': providers_data
        })
        
    except Exception as e:
        logger.error(f"Integration providers list error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get integration provider details",
    description="Get detailed information about a specific integration provider",
    responses={200: OpenApiResponse(description="Integration provider details")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_provider_detail(request, integration_id):
    """Get detailed information about a specific integration provider"""
    try:
        integration = Integration.objects.select_related('provider_config').get(
            id=integration_id,
            status=IntegrationStatus.ACTIVE,
            is_global=True
        )
        
        provider_data = {
            'id': str(integration.id),
            'name': integration.name,
            'code': integration.code,
            'provider_name': integration.provider_name,
            'integration_type': integration.integration_type,
            'description': integration.description,
            'provider_website': integration.provider_website,
            'provider_documentation': integration.provider_documentation,
            'base_url': integration.base_url,
            'is_sandbox': integration.is_sandbox,
            'version': integration.version,
            'authentication_type': integration.authentication_type,
            'supports_webhooks': integration.supports_webhooks,
            'supports_bulk_operations': integration.supports_bulk_operations,
            'supports_real_time': integration.supports_real_time,
            'rate_limits': {
                'per_minute': integration.rate_limit_per_minute,
                'per_hour': integration.rate_limit_per_hour,
                'per_day': integration.rate_limit_per_day,
            },
            'health_status': {
                'is_healthy': integration.is_healthy,
                'last_health_check': integration.last_health_check,
                'health_error_message': integration.health_error_message,
            },
            'created_at': integration.created_at,
            'updated_at': integration.updated_at,
        }
        
        # Add provider-specific configuration if available
        if hasattr(integration, 'provider_config'):
            provider_config = integration.provider_config
            provider_data.update({
                'provider_configuration': {
                    'supported_operations': provider_config.supported_operations,
                    'endpoints': provider_config.endpoints,
                    'fee_structure': provider_config.fee_structure,
                    'limits': provider_config.limits,
                    'webhook_config': provider_config.webhook_config,
                    'sandbox_config': provider_config.sandbox_config,
                    'production_config': provider_config.production_config,
                }
            })
        
        # Add bank-specific details if it's a bank integration
        if hasattr(integration, 'bank_details'):
            bank_details = integration.bank_details
            provider_data['bank_details'] = {
                'bank_name': bank_details.bank_name,
                'bank_code': bank_details.bank_code,
                'country_code': bank_details.country_code,
                'swift_code': bank_details.swift_code,
                'supported_services': {
                    'account_inquiry': bank_details.supports_account_inquiry,
                    'balance_inquiry': bank_details.supports_balance_inquiry,
                    'transaction_history': bank_details.supports_transaction_history,
                    'fund_transfer': bank_details.supports_fund_transfer,
                    'bill_payment': bank_details.supports_bill_payment,
                    'standing_orders': bank_details.supports_standing_orders,
                    'direct_debit': bank_details.supports_direct_debit,
                },
                'transaction_limits': {
                    'min_transfer_amount': str(bank_details.min_transfer_amount),
                    'max_transfer_amount': str(bank_details.max_transfer_amount),
                    'daily_transfer_limit': str(bank_details.daily_transfer_limit) if bank_details.daily_transfer_limit else None,
                },
                'operating_hours': {
                    'start': bank_details.operating_hours_start,
                    'end': bank_details.operating_hours_end,
                    'operates_weekends': bank_details.operates_weekends,
                    'operates_holidays': bank_details.operates_holidays,
                },
                'settlement_time': bank_details.settlement_time,
            }
        
        return Response({
            'success': True,
            'data': provider_data
        })
        
    except Integration.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Integration provider not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Integration provider detail error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Configure merchant integration",
    description="Configure a specific integration for a merchant with provider-specific settings",
    responses={201: OpenApiResponse(description="Integration configured successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def configure_merchant_integration(request, integration_id):
    """Configure a specific integration for a merchant"""
    try:
        # Get the integration
        integration = Integration.objects.get(
            id=integration_id,
            status=IntegrationStatus.ACTIVE,
            is_global=True
        )
        
        # Get merchant
        merchant = None
        if hasattr(request.user, '_api_key'):
            # For API key users, you might need to implement merchant resolution
            # This depends on your business logic
            merchant = None  # Implement based on your needs
        elif hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        if not merchant:
            return Response({
                'success': False,
                'message': 'Merchant not found or not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get configuration data from request
        configuration = request.data.get('configuration', {})
        credentials = request.data.get('credentials', {})
        
        # Create or update merchant integration
        merchant_integration, created = MerchantIntegration.objects.get_or_create(
            merchant=merchant,
            integration=integration,
            defaults={
                'configuration': configuration,
                'status': IntegrationStatus.DRAFT,
                'is_enabled': False,
            }
        )
        
        if not created:
            # Update existing configuration
            merchant_integration.configuration.update(configuration)
            merchant_integration.save()
        
        # Encrypt and store credentials if provided
        if credentials:
            merchant_integration.encrypt_credentials(credentials)
        
        return Response({
            'success': True,
            'message': 'Integration configured successfully',
            'data': {
                'id': str(merchant_integration.id),
                'integration_name': integration.name,
                'provider_name': integration.provider_name,
                'status': merchant_integration.status,
                'is_enabled': merchant_integration.is_enabled,
                'created': created,
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except Integration.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Integration not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Configure merchant integration error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get integration statistics",
    description="Get usage statistics for merchant integrations",
    responses={200: OpenApiResponse(description="Integration statistics")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_statistics(request):
    """Get integration usage statistics"""
    try:
        # Get merchant
        merchant = None
        if hasattr(request.user, '_api_key'):
            # For API key users, implement merchant resolution
            merchant = None  # Implement based on your needs
        elif hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        if not merchant:
            return Response({
                'success': False,
                'message': 'Merchant not found or not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get time range from query parameters
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get merchant integrations
        merchant_integrations = MerchantIntegration.objects.filter(
            merchant=merchant
        ).select_related('integration')
        
        # Calculate statistics
        total_integrations = merchant_integrations.count()
        active_integrations = merchant_integrations.filter(is_enabled=True).count()
        
        # Get API call statistics
        api_calls = IntegrationAPICall.objects.filter(
            merchant_integration__merchant=merchant,
            created_at__gte=start_date
        )
        
        total_api_calls = api_calls.count()
        successful_calls = api_calls.filter(is_successful=True).count()
        failed_calls = api_calls.filter(is_successful=False).count()
        
        # Calculate success rate
        success_rate = (successful_calls / total_api_calls * 100) if total_api_calls > 0 else 0
        
        # Get integration-wise statistics
        integration_stats = []
        for mi in merchant_integrations:
            integration_calls = api_calls.filter(merchant_integration=mi)
            integration_stats.append({
                'integration_name': mi.integration.name,
                'provider_name': mi.integration.provider_name,
                'integration_type': mi.integration.integration_type,
                'is_enabled': mi.is_enabled,
                'total_requests': mi.total_requests,
                'successful_requests': mi.successful_requests,
                'failed_requests': mi.failed_requests,
                'success_rate': mi.get_success_rate(),
                'last_used_at': mi.last_used_at,
                'recent_calls': integration_calls.count(),
            })
        
        return Response({
            'success': True,
            'data': {
                'summary': {
                    'total_integrations': total_integrations,
                    'active_integrations': active_integrations,
                    'total_api_calls': total_api_calls,
                    'successful_calls': successful_calls,
                    'failed_calls': failed_calls,
                    'success_rate': round(success_rate, 2),
                    'period_days': days,
                },
                'integrations': integration_stats,
            }
        })
        
    except Exception as e:
        logger.error(f"Integration statistics error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        logger.error(f"Error toggling integration: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["DELETE"])
def remove_integration_api(request, integration_id):
    """API endpoint to remove an integration"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        merchant = request.user.merchant_account
        merchant_integration = MerchantIntegration.objects.get(
            id=integration_id,
            merchant=merchant
        )
        
        integration_name = merchant_integration.integration.name
        merchant_integration.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Integration {integration_name} removed successfully'
        })
        
    except MerchantIntegration.DoesNotExist:
        return JsonResponse({'error': 'Integration not found'}, status=404)
    except Exception as e:
        logger.error(f"Error removing integration: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


# UBA Checkout API Endpoints for API Key Authentication

@extend_schema(
    summary="Create UBA checkout intent",
    description="Create a checkout intent using UBA Kenya Pay integration with API key authentication",
    request={
        'type': 'object',
        'properties': {
            'currency': {'type': 'string', 'example': 'KES'},
            'amount': {'type': 'number', 'example': 1000.00},
            'reference': {'type': 'string', 'example': 'ORDER123'},
            'customer': {
                'type': 'object',
                'properties': {
                    'billing_address': {
                        'type': 'object',
                        'properties': {
                            'first_name': {'type': 'string'},
                            'last_name': {'type': 'string'},
                            'address_line1': {'type': 'string'},
                            'address_line2': {'type': 'string'},
                            'address_city': {'type': 'string'},
                            'address_state': {'type': 'string'},
                            'address_country': {'type': 'string'},
                            'address_postcode': {'type': 'string'}
                        }
                    },
                    'email': {'type': 'string', 'format': 'email'},
                    'phone': {'type': 'string'}
                }
            },
            'version': {'type': 'integer', 'default': 1}
        },
        'required': ['currency', 'amount', 'reference', 'customer']
    },
    responses={201: OpenApiResponse(description="Checkout intent created successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([APIKeyPermission])
def uba_create_checkout_intent(request):
    """Create UBA checkout intent for API key authenticated merchants"""
    try:
        # Get the API key from the authenticated user
        app_key = getattr(request.user, '_api_key', None)
        if not app_key:
            return Response({
                'success': False,
                'message': 'API key authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Initialize UBA usage service
        uba_usage = UBAUsageService(app_key=app_key)
        
        # Validate merchant access
        if not uba_usage.validate_merchant_access():
            return Response({
                'success': False,
                'message': 'Access denied: Invalid API key or insufficient permissions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Create checkout intent
        result = uba_usage.create_checkout_intent(request.data)
        
        if result['status'] == 200:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=result['status'])
            
    except Exception as e:
        logger.error(f"UBA checkout intent creation error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get UBA payment status",
    description="Get payment status from UBA using API key authentication",
    responses={200: OpenApiResponse(description="Payment status retrieved")}
)
@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([APIKeyPermission])
def uba_get_payment_status_api(request, payment_id):
    """Get UBA payment status for API key authenticated merchants"""
    try:
        # Get the API key from the authenticated user
        app_key = getattr(request.user, '_api_key', None)
        if not app_key:
            return Response({
                'success': False,
                'message': 'API key authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Initialize UBA usage service
        uba_usage = UBAUsageService(app_key=app_key)
        
        # Validate merchant access
        if not uba_usage.validate_merchant_access():
            return Response({
                'success': False,
                'message': 'Access denied: Invalid API key or insufficient permissions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get payment status
        result = uba_usage.get_payment_status(payment_id)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"UBA payment status error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get UBA integration info",
    description="Get UBA integration information for the authenticated merchant",
    responses={200: OpenApiResponse(description="Integration information retrieved")}
)
@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([APIKeyPermission])
def uba_integration_info(request):
    """Get UBA integration info for API key authenticated merchants"""
    try:
        # Get the API key from the authenticated user
        app_key = getattr(request.user, '_api_key', None)
        if not app_key:
            return Response({
                'success': False,
                'message': 'API key authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Initialize UBA usage service
        uba_usage = UBAUsageService(app_key=app_key)
        
        # Get integration info
        info = uba_usage.get_integration_info()
        
        return Response({
            'success': True,
            'data': info
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"UBA integration info error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Create checkout session",
    description="Create a checkout session similar to the TypeScript controller implementation",
    request={
        'type': 'object',
        'properties': {
            'merchantId': {'type': 'string'},
            'amount': {'type': 'number'},
            'currency': {'type': 'string', 'example': 'KES'},
            'successUrl': {'type': 'string', 'format': 'uri'},
            'cancelUrl': {'type': 'string', 'format': 'uri'},
            'customer': {
                'type': 'object',
                'properties': {
                    'billing_address': {
                        'type': 'object',
                        'properties': {
                            'first_name': {'type': 'string'},
                            'last_name': {'type': 'string'},
                            'address_line1': {'type': 'string'},
                            'address_city': {'type': 'string'},
                            'address_state': {'type': 'string'},
                            'address_country': {'type': 'string'},
                            'address_postcode': {'type': 'string'}
                        }
                    },
                    'email': {'type': 'string', 'format': 'email'},
                    'phone': {'type': 'string'}
                }
            },
            'cardNumber': {'type': 'string'},
            'expiryDate': {'type': 'string'},
            'cvv': {'type': 'string'},
            'first_name': {'type': 'string'},
            'last_name': {'type': 'string'}
        },
        'required': ['merchantId', 'amount', 'currency', 'customer']
    },
    responses={201: OpenApiResponse(description="Checkout session created successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([APIKeyPermission])
def create_checkout_session(request):
    """Create checkout session similar to TypeScript controller"""
    try:
        # Get the API key from the authenticated user
        app_key = getattr(request.user, '_api_key', None)
        if not app_key:
            return Response({
                'message': 'API key authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Validate required fields
        required_fields = ['merchantId', 'amount', 'currency', 'customer']
        for field in required_fields:
            if field not in request.data:
                return Response({
                    'message': 'Invalid request parameters',
                    'errors': [{'field': field, 'message': f'{field} is required'}]
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize UBA usage service
        uba_usage = UBAUsageService(app_key=app_key)
        
        # Validate merchant access
        if not uba_usage.validate_merchant_access():
            return Response({
                'message': 'Access denied: Invalid API key or insufficient permissions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Prepare checkout payload
        checkout_payload = {
            'currency': request.data['currency'],
            'amount': float(request.data['amount']),
            'reference': f"SESSION_{session_id[:8]}",
            'customer': request.data['customer']
        }
        
        # Create checkout intent
        result = uba_usage.create_checkout_intent(checkout_payload)
        
        if result['status'] == 200:
            # Construct checkout URL similar to TypeScript implementation
            protocol = 'https' if request.is_secure() else 'http'
            host = request.get_host()
            
            # Build query parameters
            customer = request.data['customer']
            billing_address = customer.get('billing_address', {})
            
            query_params = {
                'first_name': billing_address.get('first_name', ''),
                'last_name': billing_address.get('last_name', ''),
                'address_line1': billing_address.get('address_line1', ''),
                'address_city': billing_address.get('address_city', ''),
                'address_state': billing_address.get('address_state', ''),
                'address_country': billing_address.get('address_country', ''),
                'address_postcode': billing_address.get('address_postcode', ''),
                'email': customer.get('email', ''),
                'phone': customer.get('phone', ''),
                'currency': request.data['currency'],
                'amount': request.data['amount'],
                'merchantId': request.data['merchantId']
            }
            
            # Add optional card details if provided
            if 'cardNumber' in request.data:
                query_params['cardNumber'] = request.data['cardNumber']
            if 'expiryDate' in request.data:
                query_params['expiryDate'] = request.data['expiryDate']
            if 'cvv' in request.data:
                query_params['cvv'] = request.data['cvv']
            if 'first_name' in request.data and 'last_name' in request.data:
                query_params['cardholderName'] = f"{request.data['first_name']} {request.data['last_name']}"
            
            # Build query string
            query_string = '&'.join([f"{k}={v}" for k, v in query_params.items() if v])
            checkout_url = f"{protocol}://{host}/api/payments/checkout/{session_id}?{query_string}"
            
            return Response({
                'sessionId': session_id,
                'checkoutUrl': checkout_url,
                'ubaResponse': result
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'message': 'Error creating the session',
                'error': result.get('error', 'Unknown error')
            }, status=result['status'])
            
    except Exception as e:
        logger.error(f"Checkout session creation error: {str(e)}")
        return Response({
            'message': 'Error creating the session',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework import generics, status, filters, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, filters, permissions, status
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
import logging
import uuid

from .models import (
    Integration,
    MerchantIntegration,
    BankIntegration,
    IntegrationProvider,
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
from .uba_usage import UBAUsageService
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


# Dashboard Settings Views
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


@login_required
def integration_settings_view(request):
    """Integration settings page for merchants"""
    # Check if user has merchant account
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        messages.error(request, "Access denied. Merchant account required.")
        return redirect('dashboard:dashboard_redirect')
    
    merchant = request.user.merchant_account
    
    # Get available integrations
    available_integrations = Integration.objects.filter(
        Q(is_global=True) | Q(status=IntegrationStatus.ACTIVE)
    ).order_by('integration_type', 'provider_name')
    
    # Get merchant's current integrations
    merchant_integrations = MerchantIntegration.objects.filter(
        merchant=merchant
    ).select_related('integration').order_by('-updated_at')
    
    # Get integration statistics
    integration_stats = {
        'total_available': available_integrations.count(),
        'total_configured': merchant_integrations.count(),
        'active_integrations': merchant_integrations.filter(is_enabled=True).count(),
        'by_type': available_integrations.values('integration_type').annotate(
            count=Count('id')
        ).order_by('integration_type')
    }
    
    # Add validation status for integrations
    from django.conf import settings
    import os
    
    validation_status = {
        'uba_bank': {
            'configured': bool(os.getenv('UBA_BASE_URL') and os.getenv('UBA_ACCESS_TOKEN')),
            'feature_enabled': getattr(settings, 'ENABLE_UBA_INTEGRATION', False),
            'api_key_set': bool(os.getenv('UBA_ACCESS_TOKEN')),
            'base_url_set': bool(os.getenv('UBA_BASE_URL')),
            'sandbox_mode': getattr(settings, 'UBA_SANDBOX', True),
        },
        'cybersource': {
            'configured': bool(os.getenv('CYBERSOURCE_MERCHANT_ID') and os.getenv('CYBERSOURCE_API_KEY')),
            'feature_enabled': getattr(settings, 'ENABLE_CYBERSOURCE_INTEGRATION', False),
            'merchant_id_set': bool(os.getenv('CYBERSOURCE_MERCHANT_ID')),
            'api_key_set': bool(os.getenv('CYBERSOURCE_API_KEY')),
            'sandbox_mode': getattr(settings, 'CYBERSOURCE_SANDBOX', True),
        },
        'corefy': {
            'configured': bool(os.getenv('COREFY_API_KEY') and os.getenv('COREFY_SECRET_KEY')),
            'feature_enabled': getattr(settings, 'ENABLE_COREFY_INTEGRATION', False),
            'api_key_set': bool(os.getenv('COREFY_API_KEY')),
            'secret_key_set': bool(os.getenv('COREFY_SECRET_KEY')),
            'sandbox_mode': getattr(settings, 'COREFY_SANDBOX', True),
        },
        'global_settings': {
            'health_check_enabled': bool(os.getenv('INTEGRATION_HEALTH_CHECK_INTERVAL')),
            'request_logging': getattr(settings, 'INTEGRATION_LOG_REQUESTS', False),
            'response_logging': getattr(settings, 'INTEGRATION_LOG_RESPONSES', False),
        }
    }
    
    context = {
        'page_title': 'Integration Settings',
        'available_integrations': available_integrations,
        'merchant_integrations': merchant_integrations,
        'integration_stats': integration_stats,
        'integration_types': IntegrationType.choices,
        'integration_statuses': IntegrationStatus.choices,
        'merchant': merchant,
        'validation_status': validation_status,
    }
    
    return render(request, 'integrations/settings.html', context)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def configure_integration_api(request):
    """API endpoint to configure a new integration for merchant"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        data = json.loads(request.body)
        integration_id = data.get('integration_id')
        configuration = data.get('configuration', {})
        credentials = data.get('credentials', {})
        
        if not integration_id:
            return JsonResponse({'error': 'Integration ID is required'}, status=400)
        
        # Get the integration
        try:
            integration = Integration.objects.get(id=integration_id)
        except Integration.DoesNotExist:
            return JsonResponse({'error': 'Integration not found'}, status=404)
        
        merchant = request.user.merchant_account
        
        # Create or update merchant integration
        merchant_integration, created = MerchantIntegration.objects.get_or_create(
            merchant=merchant,
            integration=integration,
            defaults={
                'configuration': configuration,
                'is_enabled': False,
                'status': IntegrationStatus.DRAFT
            }
        )
        
        if not created:
            # Update existing integration
            merchant_integration.configuration.update(configuration)
            merchant_integration.save()
        
        # Encrypt and store credentials if provided
        if credentials:
            # Handle UBA-specific credentials
            if integration.code == 'uba_kenya_pay':
                uba_credentials = {
                    'access_token': credentials.get('access_token'),
                    'configuration_id': credentials.get('configuration_id'),
                    'customization_id': credentials.get('customization_id')
                }
                merchant_integration.encrypt_credentials(uba_credentials)
            else:
                # Handle generic credentials
                merchant_integration.encrypt_credentials(credentials)
            merchant_integration.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Integration {integration.name} configured successfully',
            'integration_id': str(merchant_integration.id),
            'created': created
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error configuring integration: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def toggle_integration_api(request, integration_id):
    """API endpoint to enable/disable an integration"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        merchant = request.user.merchant_account
        merchant_integration = MerchantIntegration.objects.get(
            id=integration_id,
            merchant=merchant
        )
        
        # Toggle enabled status
        merchant_integration.is_enabled = not merchant_integration.is_enabled
        merchant_integration.status = IntegrationStatus.ACTIVE if merchant_integration.is_enabled else IntegrationStatus.INACTIVE
        merchant_integration.save()
        
        return JsonResponse({
            'success': True,
            'enabled': merchant_integration.is_enabled,
            'status': merchant_integration.status,
            'message': f'Integration {"enabled" if merchant_integration.is_enabled else "disabled"} successfully'
        })
        
    except MerchantIntegration.DoesNotExist:
        return JsonResponse({'error': 'Integration not found'}, status=404)
    except Exception as e:
        logger.error(f"Corefy webhook processing error: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


# Enhanced Integration Management Views

@extend_schema(
    summary="List integration providers",
    description="Get list of available integration providers with their configurations",
    responses={200: OpenApiResponse(description="List of integration providers")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_providers_list(request):
    """List all available integration providers"""
    try:
        # Get integrations with their provider configurations
        integrations = Integration.objects.filter(
            status=IntegrationStatus.ACTIVE,
            is_global=True
        ).select_related('provider_config').order_by('provider_name', 'name')
        
        providers_data = []
        for integration in integrations:
            provider_data = {
                'id': str(integration.id),
                'name': integration.name,
                'code': integration.code,
                'provider_name': integration.provider_name,
                'integration_type': integration.integration_type,
                'description': integration.description,
                'supports_webhooks': integration.supports_webhooks,
                'supports_bulk_operations': integration.supports_bulk_operations,
                'supports_real_time': integration.supports_real_time,
                'is_sandbox': integration.is_sandbox,
                'version': integration.version,
                'authentication_type': integration.authentication_type,
            }
            
            # Add provider-specific configuration if available
            if hasattr(integration, 'provider_config'):
                provider_config = integration.provider_config
                provider_data.update({
                    'supported_operations': provider_config.supported_operations,
                    'endpoints': provider_config.endpoints,
                    'fee_structure': provider_config.fee_structure,
                    'limits': provider_config.limits,
                    'webhook_config': provider_config.webhook_config,
                })
            
            providers_data.append(provider_data)
        
        return Response({
            'success': True,
            'count': len(providers_data),
            'data': providers_data
        })
        
    except Exception as e:
        logger.error(f"Integration providers list error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get integration provider details",
    description="Get detailed information about a specific integration provider",
    responses={200: OpenApiResponse(description="Integration provider details")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_provider_detail(request, integration_id):
    """Get detailed information about a specific integration provider"""
    try:
        integration = Integration.objects.select_related('provider_config').get(
            id=integration_id,
            status=IntegrationStatus.ACTIVE,
            is_global=True
        )
        
        provider_data = {
            'id': str(integration.id),
            'name': integration.name,
            'code': integration.code,
            'provider_name': integration.provider_name,
            'integration_type': integration.integration_type,
            'description': integration.description,
            'provider_website': integration.provider_website,
            'provider_documentation': integration.provider_documentation,
            'base_url': integration.base_url,
            'is_sandbox': integration.is_sandbox,
            'version': integration.version,
            'authentication_type': integration.authentication_type,
            'supports_webhooks': integration.supports_webhooks,
            'supports_bulk_operations': integration.supports_bulk_operations,
            'supports_real_time': integration.supports_real_time,
            'rate_limits': {
                'per_minute': integration.rate_limit_per_minute,
                'per_hour': integration.rate_limit_per_hour,
                'per_day': integration.rate_limit_per_day,
            },
            'health_status': {
                'is_healthy': integration.is_healthy,
                'last_health_check': integration.last_health_check,
                'health_error_message': integration.health_error_message,
            },
            'created_at': integration.created_at,
            'updated_at': integration.updated_at,
        }
        
        # Add provider-specific configuration if available
        if hasattr(integration, 'provider_config'):
            provider_config = integration.provider_config
            provider_data.update({
                'provider_configuration': {
                    'supported_operations': provider_config.supported_operations,
                    'endpoints': provider_config.endpoints,
                    'fee_structure': provider_config.fee_structure,
                    'limits': provider_config.limits,
                    'webhook_config': provider_config.webhook_config,
                    'sandbox_config': provider_config.sandbox_config,
                    'production_config': provider_config.production_config,
                }
            })
        
        # Add bank-specific details if it's a bank integration
        if hasattr(integration, 'bank_details'):
            bank_details = integration.bank_details
            provider_data['bank_details'] = {
                'bank_name': bank_details.bank_name,
                'bank_code': bank_details.bank_code,
                'country_code': bank_details.country_code,
                'swift_code': bank_details.swift_code,
                'supported_services': {
                    'account_inquiry': bank_details.supports_account_inquiry,
                    'balance_inquiry': bank_details.supports_balance_inquiry,
                    'transaction_history': bank_details.supports_transaction_history,
                    'fund_transfer': bank_details.supports_fund_transfer,
                    'bill_payment': bank_details.supports_bill_payment,
                    'standing_orders': bank_details.supports_standing_orders,
                    'direct_debit': bank_details.supports_direct_debit,
                },
                'transaction_limits': {
                    'min_transfer_amount': str(bank_details.min_transfer_amount),
                    'max_transfer_amount': str(bank_details.max_transfer_amount),
                    'daily_transfer_limit': str(bank_details.daily_transfer_limit) if bank_details.daily_transfer_limit else None,
                },
                'operating_hours': {
                    'start': bank_details.operating_hours_start,
                    'end': bank_details.operating_hours_end,
                    'operates_weekends': bank_details.operates_weekends,
                    'operates_holidays': bank_details.operates_holidays,
                },
                'settlement_time': bank_details.settlement_time,
            }
        
        return Response({
            'success': True,
            'data': provider_data
        })
        
    except Integration.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Integration provider not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Integration provider detail error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Configure merchant integration",
    description="Configure a specific integration for a merchant with provider-specific settings",
    responses={201: OpenApiResponse(description="Integration configured successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def configure_merchant_integration(request, integration_id):
    """Configure a specific integration for a merchant"""
    try:
        # Get the integration
        integration = Integration.objects.get(
            id=integration_id,
            status=IntegrationStatus.ACTIVE,
            is_global=True
        )
        
        # Get merchant
        merchant = None
        if hasattr(request.user, '_api_key'):
            # For API key users, you might need to implement merchant resolution
            # This depends on your business logic
            merchant = None  # Implement based on your needs
        elif hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        if not merchant:
            return Response({
                'success': False,
                'message': 'Merchant not found or not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get configuration data from request
        configuration = request.data.get('configuration', {})
        credentials = request.data.get('credentials', {})
        
        # Create or update merchant integration
        merchant_integration, created = MerchantIntegration.objects.get_or_create(
            merchant=merchant,
            integration=integration,
            defaults={
                'configuration': configuration,
                'status': IntegrationStatus.DRAFT,
                'is_enabled': False,
            }
        )
        
        if not created:
            # Update existing configuration
            merchant_integration.configuration.update(configuration)
            merchant_integration.save()
        
        # Encrypt and store credentials if provided
        if credentials:
            merchant_integration.encrypt_credentials(credentials)
        
        return Response({
            'success': True,
            'message': 'Integration configured successfully',
            'data': {
                'id': str(merchant_integration.id),
                'integration_name': integration.name,
                'provider_name': integration.provider_name,
                'status': merchant_integration.status,
                'is_enabled': merchant_integration.is_enabled,
                'created': created,
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except Integration.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Integration not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Configure merchant integration error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get integration statistics",
    description="Get usage statistics for merchant integrations",
    responses={200: OpenApiResponse(description="Integration statistics")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_statistics(request):
    """Get integration usage statistics"""
    try:
        # Get merchant
        merchant = None
        if hasattr(request.user, '_api_key'):
            # For API key users, implement merchant resolution
            merchant = None  # Implement based on your needs
        elif hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        if not merchant:
            return Response({
                'success': False,
                'message': 'Merchant not found or not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get time range from query parameters
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get merchant integrations
        merchant_integrations = MerchantIntegration.objects.filter(
            merchant=merchant
        ).select_related('integration')
        
        # Calculate statistics
        total_integrations = merchant_integrations.count()
        active_integrations = merchant_integrations.filter(is_enabled=True).count()
        
        # Get API call statistics
        api_calls = IntegrationAPICall.objects.filter(
            merchant_integration__merchant=merchant,
            created_at__gte=start_date
        )
        
        total_api_calls = api_calls.count()
        successful_calls = api_calls.filter(is_successful=True).count()
        failed_calls = api_calls.filter(is_successful=False).count()
        
        # Calculate success rate
        success_rate = (successful_calls / total_api_calls * 100) if total_api_calls > 0 else 0
        
        # Get integration-wise statistics
        integration_stats = []
        for mi in merchant_integrations:
            integration_calls = api_calls.filter(merchant_integration=mi)
            integration_stats.append({
                'integration_name': mi.integration.name,
                'provider_name': mi.integration.provider_name,
                'integration_type': mi.integration.integration_type,
                'is_enabled': mi.is_enabled,
                'total_requests': mi.total_requests,
                'successful_requests': mi.successful_requests,
                'failed_requests': mi.failed_requests,
                'success_rate': mi.get_success_rate(),
                'last_used_at': mi.last_used_at,
                'recent_calls': integration_calls.count(),
            })
        
        return Response({
            'success': True,
            'data': {
                'summary': {
                    'total_integrations': total_integrations,
                    'active_integrations': active_integrations,
                    'total_api_calls': total_api_calls,
                    'successful_calls': successful_calls,
                    'failed_calls': failed_calls,
                    'success_rate': round(success_rate, 2),
                    'period_days': days,
                },
                'integrations': integration_stats,
            }
        })
        
    except Exception as e:
        logger.error(f"Integration statistics error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        logger.error(f"Error toggling integration: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["DELETE"])
def remove_integration_api(request, integration_id):
    """API endpoint to remove an integration"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        merchant = request.user.merchant_account
        merchant_integration = MerchantIntegration.objects.get(
            id=integration_id,
            merchant=merchant
        )
        
        integration_name = merchant_integration.integration.name
        merchant_integration.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Integration {integration_name} removed successfully'
        })
        
    except MerchantIntegration.DoesNotExist:
        return JsonResponse({'error': 'Integration not found'}, status=404)
    except Exception as e:
        logger.error(f"Error removing integration: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


# UBA Checkout API Endpoints for API Key Authentication

@extend_schema(
    summary="Create UBA checkout intent",
    description="Create a checkout intent using UBA Kenya Pay integration with API key authentication",
    request={
        'type': 'object',
        'properties': {
            'currency': {'type': 'string', 'example': 'KES'},
            'amount': {'type': 'number', 'example': 1000.00},
            'reference': {'type': 'string', 'example': 'ORDER123'},
            'customer': {
                'type': 'object',
                'properties': {
                    'billing_address': {
                        'type': 'object',
                        'properties': {
                            'first_name': {'type': 'string'},
                            'last_name': {'type': 'string'},
                            'address_line1': {'type': 'string'},
                            'address_line2': {'type': 'string'},
                            'address_city': {'type': 'string'},
                            'address_state': {'type': 'string'},
                            'address_country': {'type': 'string'},
                            'address_postcode': {'type': 'string'}
                        }
                    },
                    'email': {'type': 'string', 'format': 'email'},
                    'phone': {'type': 'string'}
                }
            },
            'version': {'type': 'integer', 'default': 1}
        },
        'required': ['currency', 'amount', 'reference', 'customer']
    },
    responses={201: OpenApiResponse(description="Checkout intent created successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([APIKeyPermission])
def uba_create_checkout_intent(request):
    """Create UBA checkout intent for API key authenticated merchants"""
    try:
        # Get the API key from the authenticated user
        app_key = getattr(request.user, '_api_key', None)
        if not app_key:
            return Response({
                'success': False,
                'message': 'API key authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Initialize UBA usage service
        uba_usage = UBAUsageService(app_key=app_key)
        
        # Validate merchant access
        if not uba_usage.validate_merchant_access():
            return Response({
                'success': False,
                'message': 'Access denied: Invalid API key or insufficient permissions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Create checkout intent
        result = uba_usage.create_checkout_intent(request.data)
        
        if result['status'] == 200:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=result['status'])
            
    except Exception as e:
        logger.error(f"UBA checkout intent creation error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get UBA payment status",
    description="Get payment status from UBA using API key authentication",
    responses={200: OpenApiResponse(description="Payment status retrieved")}
)
@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([APIKeyPermission])
def uba_get_payment_status_api(request, payment_id):
    """Get UBA payment status for API key authenticated merchants"""
    try:
        # Get the API key from the authenticated user
        app_key = getattr(request.user, '_api_key', None)
        if not app_key:
            return Response({
                'success': False,
                'message': 'API key authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Initialize UBA usage service
        uba_usage = UBAUsageService(app_key=app_key)
        
        # Validate merchant access
        if not uba_usage.validate_merchant_access():
            return Response({
                'success': False,
                'message': 'Access denied: Invalid API key or insufficient permissions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get payment status
        result = uba_usage.get_payment_status(payment_id)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"UBA payment status error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get UBA integration info",
    description="Get UBA integration information for the authenticated merchant",
    responses={200: OpenApiResponse(description="Integration information retrieved")}
)
@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([APIKeyPermission])
def uba_integration_info(request):
    """Get UBA integration info for API key authenticated merchants"""
    try:
        # Get the API key from the authenticated user
        app_key = getattr(request.user, '_api_key', None)
        if not app_key:
            return Response({
                'success': False,
                'message': 'API key authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Initialize UBA usage service
        uba_usage = UBAUsageService(app_key=app_key)
        
        # Get integration info
        info = uba_usage.get_integration_info()
        
        return Response({
            'success': True,
            'data': info
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"UBA integration info error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Create checkout session",
    description="Create a checkout session similar to the TypeScript controller implementation",
    request={
        'type': 'object',
        'properties': {
            'merchantId': {'type': 'string'},
            'amount': {'type': 'number'},
            'currency': {'type': 'string', 'example': 'KES'},
            'successUrl': {'type': 'string', 'format': 'uri'},
            'cancelUrl': {'type': 'string', 'format': 'uri'},
            'customer': {
                'type': 'object',
                'properties': {
                    'billing_address': {
                        'type': 'object',
                        'properties': {
                            'first_name': {'type': 'string'},
                            'last_name': {'type': 'string'},
                            'address_line1': {'type': 'string'},
                            'address_city': {'type': 'string'},
                            'address_state': {'type': 'string'},
                            'address_country': {'type': 'string'},
                            'address_postcode': {'type': 'string'}
                        }
                    },
                    'email': {'type': 'string', 'format': 'email'},
                    'phone': {'type': 'string'}
                }
            },
            'cardNumber': {'type': 'string'},
            'expiryDate': {'type': 'string'},
            'cvv': {'type': 'string'},
            'first_name': {'type': 'string'},
            'last_name': {'type': 'string'}
        },
        'required': ['merchantId', 'amount', 'currency', 'customer']
    },
    responses={201: OpenApiResponse(description="Checkout session created successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([APIKeyPermission])
def create_checkout_session(request):
    """Create checkout session similar to TypeScript controller"""
    try:
        # Get the API key from the authenticated user
        app_key = getattr(request.user, '_api_key', None)
        if not app_key:
            return Response({
                'message': 'API key authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Validate required fields
        required_fields = ['merchantId', 'amount', 'currency', 'customer']
        for field in required_fields:
            if field not in request.data:
                return Response({
                    'message': 'Invalid request parameters',
                    'errors': [{'field': field, 'message': f'{field} is required'}]
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize UBA usage service
        uba_usage = UBAUsageService(app_key=app_key)
        
        # Validate merchant access
        if not uba_usage.validate_merchant_access():
            return Response({
                'message': 'Access denied: Invalid API key or insufficient permissions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Prepare checkout payload
        checkout_payload = {
            'currency': request.data['currency'],
            'amount': float(request.data['amount']),
            'reference': f"SESSION_{session_id[:8]}",
            'customer': request.data['customer']
        }
        
        # Create checkout intent
        result = uba_usage.create_checkout_intent(checkout_payload)
        
        if result['status'] == 200:
            # Construct checkout URL similar to TypeScript implementation
            protocol = 'https' if request.is_secure() else 'http'
            host = request.get_host()
            
            # Build query parameters
            customer = request.data['customer']
            billing_address = customer.get('billing_address', {})
            
            query_params = {
                'first_name': billing_address.get('first_name', ''),
                'last_name': billing_address.get('last_name', ''),
                'address_line1': billing_address.get('address_line1', ''),
                'address_city': billing_address.get('address_city', ''),
                'address_state': billing_address.get('address_state', ''),
                'address_country': billing_address.get('address_country', ''),
                'address_postcode': billing_address.get('address_postcode', ''),
                'email': customer.get('email', ''),
                'phone': customer.get('phone', ''),
                'currency': request.data['currency'],
                'amount': request.data['amount'],
                'merchantId': request.data['merchantId']
            }
            
            # Add optional card details if provided
            if 'cardNumber' in request.data:
                query_params['cardNumber'] = request.data['cardNumber']
            if 'expiryDate' in request.data:
                query_params['expiryDate'] = request.data['expiryDate']
            if 'cvv' in request.data:
                query_params['cvv'] = request.data['cvv']
            if 'first_name' in request.data and 'last_name' in request.data:
                query_params['cardholderName'] = f"{request.data['first_name']} {request.data['last_name']}"
            
            # Build query string
            query_string = '&'.join([f"{k}={v}" for k, v in query_params.items() if v])
            checkout_url = f"{protocol}://{host}/api/payments/checkout/{session_id}?{query_string}"
            
            return Response({
                'sessionId': session_id,
                'checkoutUrl': checkout_url,
                'ubaResponse': result
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'message': 'Error creating the session',
                'error': result.get('error', 'Unknown error')
            }, status=result['status'])
            
    except Exception as e:
        logger.error(f"Checkout session creation error: {str(e)}")
        return Response({
            'message': 'Error creating the session',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)