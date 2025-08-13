import logging
import os 
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from ..models import Integration
from ..serializers import (
    UniwireInvoiceSerializer,
    UniwireInvoiceStatusSerializer,
    UniwireInvoiceCancelSerializer,
    UniwireWebhookSerializer
)
from ..uniwire.client import UniwireClient, UniwireAPIException
from authentication.api_auth import APIKeyOrTokenAuthentication
from .base import APIKeyPermission

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Create Uniwire invoice",
    description="Create a new invoice using Uniwire API",
    request=UniwireInvoiceSerializer,
    responses={201: OpenApiResponse(description="Invoice created successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uniwire_create_invoice(request):
    """Create a new Uniwire invoice"""
    try:
        # Initialize Uniwire client
        client = UniwireClient()
        
        # Extract parameters from request
        profile_id = os.getenv('UNIWIRE_PROFILE_ID', 'UNIWIER_PROFILE_ID_NOW')
        kind = request.data.get('kind')
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'USD')
        passthrough = request.data.get('passthrough')
        min_confirmations = request.data.get('min_confirmations')
        zero_conf_enabled = request.data.get('zero_conf_enabled')
        notes = request.data.get('notes')
        fee_amount = request.data.get('fee_amount')
        exchange_rate_limit = request.data.get('exchange_rate_limit')
        
        # Validate required parameters
        if not profile_id or not kind:
            return Response(
                {"error": "Missing required parameters: profile_id and kind are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create invoice
        response = client.create_invoice(
            profile_id=profile_id,
            kind=kind,
            amount=amount,
            currency=currency,
            passthrough=passthrough,
            min_confirmations=min_confirmations,
            zero_conf_enabled=zero_conf_enabled,
            notes=notes,
            fee_amount=fee_amount,
            exchange_rate_limit=exchange_rate_limit
        )


        #  Now crreate a transactions on our end 
        
        return Response(response, status=status.HTTP_201_CREATED)
    
    except UniwireAPIException as e:
        logger.error(f"Uniwire API error: {e.message}")
        return Response(
            {"error": e.message, "error_code": e.error_code},
            status=e.status_code or status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.error(f"Unexpected error creating Uniwire invoice: {str(e)}")
        return Response(
            {"error": "Unexpected error occurred"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Get Uniwire invoice",
    description="Get details of a specific Uniwire invoice",
    responses={200: OpenApiResponse(description="Invoice details retrieved successfully")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uniwire_get_invoice(request, invoice_id):
    """Get details of a specific Uniwire invoice"""
    try:
        # Initialize Uniwire client
        client = UniwireClient()
        
        # Get invoice details
        response = client.get_invoice(invoice_id=invoice_id)
        
        return Response(response, status=status.HTTP_200_OK)
    
    except UniwireAPIException as e:
        logger.error(f"Uniwire API error: {e.message}")
        return Response(
            {"error": e.message, "error_code": e.error_code},
            status=e.status_code or status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.error(f"Unexpected error getting Uniwire invoice: {str(e)}")
        return Response(
            {"error": "Unexpected error occurred"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="List Uniwire invoices",
    description="Get a list of Uniwire invoices with optional filtering",
    responses={200: OpenApiResponse(description="Invoices list retrieved successfully")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uniwire_list_invoices(request):
    """List Uniwire invoices with optional filtering"""
    try:
        # Initialize Uniwire client
        client = UniwireClient()
        
        # Extract filter parameters from request
        page = int(request.query_params.get('page', 1))
        txid = request.query_params.get('txid')
        address = request.query_params.get('address')
        status_filter = request.query_params.get('status')
        profile_id = request.query_params.get('profile_id')
        
        # Get invoices list
        response = client.get_invoices(
            page=page,
            txid=txid,
            address=address,
            status=status_filter,
            profile_id=profile_id
        )
        
        return Response(response, status=status.HTTP_200_OK)
    
    except UniwireAPIException as e:
        logger.error(f"Uniwire API error: {e.message}")
        return Response(
            {"error": e.message, "error_code": e.error_code},
            status=e.status_code or status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.error(f"Unexpected error listing Uniwire invoices: {str(e)}")
        return Response(
            {"error": "Unexpected error occurred"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Create Uniwire network invoice",
    description="Create a reusable deposit address using Uniwire API",
    request=UniwireInvoiceSerializer,
    responses={201: OpenApiResponse(description="Network invoice created successfully")}
)
@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def uniwire_create_network_invoice(request):
    """Create a reusable deposit address (network invoice)"""
    try:
        # Initialize Uniwire client
        client = UniwireClient()
        
        # Extract parameters from request
        profile_id = os.getenv('UNIWIRE_PROFILE_ID', 'UNIWIER_PROFILE_ID_NOW')
        kind = request.data.get('kind')
        passthrough = request.data.get('passthrough')
        notes = request.data.get('notes')
        
        # Validate required parameters
        if not profile_id or not kind:
            return Response(
                {"error": "Missing required parameters: profile_id and kind are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create network invoice (reusable address)
        response = client.create_invoice(
            profile_id=profile_id,
            kind=kind,
            passthrough=passthrough,
            notes=notes
        )
        
        return Response(response, status=status.HTTP_201_CREATED)
    
    except UniwireAPIException as e:
        logger.error(f"Uniwire API error: {e.message}")
        return Response(
            {"error": e.message, "error_code": e.error_code},
            status=e.status_code or status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.error(f"Unexpected error creating Uniwire network invoice: {str(e)}")
        return Response(
            {"error": "Unexpected error occurred"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )