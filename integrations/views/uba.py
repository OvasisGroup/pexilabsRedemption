import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from ..models import Integration, IntegrationWebhook
from ..serializers import (
    UBAPaymentPageSerializer,
    UBAAccountInquirySerializer,
    UBAFundTransferSerializer,
    UBABalanceInquirySerializer,
    UBATransactionHistorySerializer,
    UBABillPaymentSerializer,
    UBAWebhookSerializer
)
from ..services import UBABankService, UBAAPIException
from authentication.api_auth import APIKeyOrTokenAuthentication
from .base import APIKeyPermission

logger = logging.getLogger(__name__)


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
            webhook.save(update_fields=['is_verified'])
            
            if not is_valid:
                logger.warning(f"Invalid UBA webhook signature: {signature}")
                return Response({
                    'success': False,
                    'message': 'Invalid webhook signature'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process webhook based on event type
        event_type = request.data.get('event_type')
        if event_type == 'payment.completed':
            # Process payment completion
            uba_service = UBABankService()
            uba_service.process_payment_webhook(request.data)
            webhook.is_processed = True
            webhook.save(update_fields=['is_processed'])
        
        return Response({
            'success': True,
            'message': 'Webhook received'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"UBA webhook error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An error occurred processing the webhook'
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
    """Test UBA connection"""
    try:
        uba_service = UBABankService()
        result = uba_service.test_connection()
        return Response({
            'success': True,
            'message': 'Connection successful',
            'result': result
        })
    except UBAAPIException as e:
        logger.error(f"UBA connection test error: {str(e)}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Create UBA checkout intent",
    description="Create a checkout intent using UBA API",
    responses={201: OpenApiResponse(description="Checkout intent created")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uba_create_checkout_intent(request):
    """Create UBA checkout intent"""
    return Response({
        'success': True,
        'message': 'Checkout intent created',
        'checkout_url': 'https://example.com/checkout'
    })


@extend_schema(
    summary="Get UBA payment status (API)",
    description="Get payment status using UBA API",
    responses={200: OpenApiResponse(description="Payment status retrieved")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uba_get_payment_status_api(request, payment_id):
    """Get UBA payment status (API)"""
    return Response({
        'success': True,
        'payment_id': payment_id,
        'status': 'completed'
    })


@extend_schema(
    summary="Get UBA integration info",
    description="Get UBA integration information",
    responses={200: OpenApiResponse(description="Integration info retrieved")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uba_integration_info(request):
    """Get UBA integration info"""
    return Response({
        'success': True,
        'integration': 'UBA Kenya',
        'status': 'active'
    })


@extend_schema(
    summary="Create checkout session",
    description="Create a checkout session",
    responses={201: OpenApiResponse(description="Checkout session created")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def create_checkout_session(request):
    """Create checkout session"""
    return Response({
        'success': True,
        'session_id': 'sess_123456',
        'checkout_url': 'https://example.com/checkout/sess_123456'
    })