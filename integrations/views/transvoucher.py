import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.utils import timezone
import json

from ..models import Integration, IntegrationWebhook
from ..transvoucher.service import TransVoucherService, TransVoucherAPIException
from ..transvoucher.usage import TransVoucherUsageService
from authentication.api_auth import APIKeyOrTokenAuthentication
from authentication.models import Merchant
from .base import APIKeyPermission

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Create TransVoucher payment",
    description="Create a payment using TransVoucher integration",
    request={
        'type': 'object',
        'properties': {
            'amount': {'type': 'number', 'description': 'Payment amount'},
            'currency': {'type': 'string', 'default': 'USD', 'description': 'Currency code'},
            'title': {'type': 'string', 'description': 'Payment title'},
            'description': {'type': 'string', 'description': 'Payment description'},
            'customer_email': {'type': 'string', 'description': 'Customer email'},
            'customer_name': {'type': 'string', 'description': 'Customer full name'},
            'customer_phone': {'type': 'string', 'description': 'Customer phone'},
            'reference_id': {'type': 'string', 'description': 'Optional reference ID'},
            'metadata': {'type': 'object', 'description': 'Additional metadata'},
            'customer_commission_percentage': {'type': 'number', 'description': 'Commission percentage'},
            'multiple_use': {'type': 'boolean', 'default': False, 'description': 'Multiple use flag'}
        },
        'required': ['amount', 'title']
    },
    responses={201: OpenApiResponse(description="Payment created successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def transvoucher_create_payment(request):
    """Create TransVoucher payment"""
    try:
        # Get merchant from request
        merchant = None
        app_key = None
        
        if hasattr(request.user, '_api_key'):
            app_key = request.user._api_key
            # Try to get merchant from API key
            # This depends on your business logic for associating API keys with merchants
        elif hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        # Initialize TransVoucher usage service
        transvoucher_service = TransVoucherUsageService(app_key=app_key, merchant=merchant)
        
        # Extract payment data from request
        payment_data = {
            'amount': request.data.get('amount'),
            'currency': request.data.get('currency', 'USD'),
            'title': request.data.get('title'),
            'description': request.data.get('description', ''),
            'customer_email': request.data.get('customer_email'),
            'customer_name': request.data.get('customer_name'),
            'customer_phone': request.data.get('customer_phone'),
            'reference_id': request.data.get('reference_id'),
            'metadata': request.data.get('metadata', {}),
            'customer_commission_percentage': request.data.get('customer_commission_percentage'),
            'multiple_use': request.data.get('multiple_use', False)
        }
        
        # Validate required fields
        if not payment_data['amount']:
            return Response(
                {'error': 'Amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not payment_data['title']:
            return Response(
                {'error': 'Title is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create checkout session
        result = transvoucher_service.create_checkout_session(**payment_data)
        
        if result.get('success'):
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'error': result.get('error', 'Payment creation failed')},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except TransVoucherAPIException as e:
        logger.error(f"TransVoucher API error: {e.message}")
        return Response(
            {
                'error': e.message,
                'error_code': e.error_code,
                'status_code': e.status_code
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Unexpected error in TransVoucher payment creation: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Get TransVoucher payment status",
    description="Get payment status from TransVoucher",
    responses={200: OpenApiResponse(description="Payment status retrieved")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def transvoucher_get_payment_status(request, reference_id):
    """Get TransVoucher payment status"""
    try:
        # Get merchant from request
        merchant = None
        app_key = None
        
        if hasattr(request.user, '_api_key'):
            app_key = request.user._api_key
        elif hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        # Initialize TransVoucher usage service
        transvoucher_service = TransVoucherUsageService(app_key=app_key, merchant=merchant)
        
        # Get payment status
        result = transvoucher_service.get_payment_status(reference_id)
        
        if result.get('success'):
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': result.get('error', 'Failed to get payment status')},
                status=status.HTTP_404_NOT_FOUND
            )
            
    except TransVoucherAPIException as e:
        logger.error(f"TransVoucher API error: {e.message}")
        return Response(
            {
                'error': e.message,
                'error_code': e.error_code,
                'status_code': e.status_code
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Unexpected error getting TransVoucher payment status: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="List TransVoucher payments",
    description="List payments with pagination and filtering",
    responses={200: OpenApiResponse(description="Payments list retrieved")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def transvoucher_list_payments(request):
    """List TransVoucher payments"""
    try:
        # Get merchant from request
        merchant = None
        if hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        # Initialize TransVoucher service
        transvoucher_service = TransVoucherService(merchant=merchant)
        
        # Get query parameters
        limit = int(request.GET.get('limit', 10))
        page_token = request.GET.get('page_token')
        status_filter = request.GET.get('status')
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        
        # List payments
        result = transvoucher_service.list_payments(
            limit=limit,
            page_token=page_token,
            status=status_filter,
            from_date=from_date,
            to_date=to_date
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except TransVoucherAPIException as e:
        logger.error(f"TransVoucher API error: {e.message}")
        return Response(
            {
                'error': e.message,
                'error_code': e.error_code,
                'status_code': e.status_code
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Unexpected error listing TransVoucher payments: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="TransVoucher webhook handler",
    description="Handle webhooks from TransVoucher",
    responses={200: OpenApiResponse(description="Webhook processed")}
)
@api_view(['POST'])
@permission_classes([])  # No authentication for webhooks
@csrf_exempt
def transvoucher_webhook_handler(request):
    """Handle TransVoucher webhooks"""
    try:
        # Get webhook signature from headers
        signature = request.META.get('HTTP_X_TRANSVOUCHER_SIGNATURE', '')
        
        # Parse webhook payload
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return Response(
                {'error': 'Invalid JSON payload'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Log webhook receipt
        logger.info(f"Received TransVoucher webhook: {payload.get('event_type', 'unknown')}")
        
        # Get integration for webhook validation
        try:
            integration = Integration.objects.get(code='transvoucher')
        except Integration.DoesNotExist:
            logger.error("TransVoucher integration not found")
            return Response(
                {'error': 'Integration not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Store webhook for processing
        webhook = IntegrationWebhook.objects.create(
            integration=integration,
            event_type=payload.get('event_type', 'unknown'),
            payload=payload,
            signature=signature,
            source_ip=request.META.get('REMOTE_ADDR', ''),
            headers=dict(request.META)
        )
        
        # Process webhook based on event type
        event_type = payload.get('event_type')
        
        if event_type == 'payment_intent.succeeded':
            # Handle successful payment
            payment_data = payload.get('data', {})
            reference_id = payment_data.get('reference_id')
            
            logger.info(f"Payment succeeded: {reference_id}")
            
            # Here you would typically:
            # 1. Update your local transaction records
            # 2. Send notifications to the merchant
            # 3. Trigger any post-payment workflows
            
        elif event_type == 'payment_intent.failed':
            # Handle failed payment
            payment_data = payload.get('data', {})
            reference_id = payment_data.get('reference_id')
            
            logger.info(f"Payment failed: {reference_id}")
            
        elif event_type == 'payment_intent.cancelled':
            # Handle cancelled payment
            payment_data = payload.get('data', {})
            reference_id = payment_data.get('reference_id')
            
            logger.info(f"Payment cancelled: {reference_id}")
            
        elif event_type == 'payment_intent.expired':
            # Handle expired payment
            payment_data = payload.get('data', {})
            reference_id = payment_data.get('reference_id')
            
            logger.info(f"Payment expired: {reference_id}")
        
        # Mark webhook as processed
        webhook.processed = True
        webhook.processed_at = timezone.now()
        webhook.save()
        
        return Response({'status': 'success'}, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error processing TransVoucher webhook: {str(e)}")
        return Response(
            {'error': 'Webhook processing failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Test TransVoucher connection",
    description="Test connection to TransVoucher API",
    responses={200: OpenApiResponse(description="Connection test result")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def transvoucher_test_connection(request):
    """Test TransVoucher connection"""
    try:
        # Get merchant from request
        merchant = None
        if hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        # Initialize TransVoucher service
        transvoucher_service = TransVoucherService(merchant=merchant)
        
        # Test connection
        result = transvoucher_service.test_connection()
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error testing TransVoucher connection: {str(e)}")
        return Response(
            {
                'success': False,
                'error': f'Connection test failed: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Get TransVoucher integration info",
    description="Get TransVoucher integration information",
    responses={200: OpenApiResponse(description="Integration info retrieved")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def transvoucher_integration_info(request):
    """Get TransVoucher integration info"""
    try:
        # Get integration
        integration = Integration.objects.get(code='transvoucher')
        
        # Get merchant integration if available
        merchant_integration = None
        if hasattr(request.user, 'merchant_account'):
            try:
                from ..models import MerchantIntegration
                merchant_integration = MerchantIntegration.objects.get(
                    merchant=request.user.merchant_account,
                    integration=integration,
                    is_enabled=True
                )
            except MerchantIntegration.DoesNotExist:
                pass
        
        info = {
            'integration': {
                'id': str(integration.id),
                'name': integration.name,
                'provider_name': integration.provider_name,
                'status': integration.status,
                'is_sandbox': integration.is_sandbox,
                'version': integration.version,
                'supports_webhooks': integration.supports_webhooks,
                'is_healthy': integration.is_healthy
            },
            'merchant_integration': None
        }
        
        if merchant_integration:
            info['merchant_integration'] = {
                'id': str(merchant_integration.id),
                'is_enabled': merchant_integration.is_enabled,
                'status': merchant_integration.status,
                'configuration': {
                    'webhook_url': merchant_integration.configuration.get('webhook_url', ''),
                    'return_url': merchant_integration.configuration.get('return_url', ''),
                    'failure_url': merchant_integration.configuration.get('failure_url', '')
                }
            }
        
        return Response(info, status=status.HTTP_200_OK)
        
    except Integration.DoesNotExist:
        return Response(
            {'error': 'TransVoucher integration not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error getting TransVoucher integration info: {str(e)}")
        return Response(
            {'error': 'Failed to get integration info'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Create TransVoucher checkout session",
    description="Create a checkout session for simplified payment flow",
    request={
        'type': 'object',
        'properties': {
            'amount': {'type': 'number', 'description': 'Payment amount'},
            'currency': {'type': 'string', 'default': 'USD', 'description': 'Currency code'},
            'title': {'type': 'string', 'description': 'Payment title'},
            'description': {'type': 'string', 'description': 'Payment description'},
            'customer_email': {'type': 'string', 'description': 'Customer email'},
            'customer_name': {'type': 'string', 'description': 'Customer name'},
            'metadata': {'type': 'object', 'description': 'Additional metadata'}
        },
        'required': ['amount', 'title']
    },
    responses={201: OpenApiResponse(description="Checkout session created")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def transvoucher_create_checkout_session(request):
    """Create TransVoucher checkout session"""
    try:
        # Get merchant and API key from request
        merchant = None
        app_key = None
        
        if hasattr(request.user, '_api_key'):
            app_key = request.user._api_key
        elif hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        # Initialize TransVoucher usage service
        transvoucher_service = TransVoucherUsageService(app_key=app_key, merchant=merchant)
        
        # Test integration first
        test_result = transvoucher_service.test_integration()
        if not test_result.get('success'):
            return Response(
                {
                    'error': 'TransVoucher integration not properly configured',
                    'details': test_result
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create checkout session
        result = transvoucher_service.create_checkout_session(
            amount=request.data.get('amount'),
            currency=request.data.get('currency', 'USD'),
            title=request.data.get('title'),
            description=request.data.get('description', ''),
            customer_email=request.data.get('customer_email'),
            customer_name=request.data.get('customer_name'),
            metadata=request.data.get('metadata', {})
        )
        
        if result.get('success'):
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'error': result.get('error', 'Checkout session creation failed')},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Error creating TransVoucher checkout session: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )