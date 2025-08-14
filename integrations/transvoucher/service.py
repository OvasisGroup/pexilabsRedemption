"""TransVoucher Integration Service

This module provides integration with TransVoucher API for payment processing.
"""

import requests
import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Union
from django.conf import settings
from django.utils import timezone

from ..models import (
    Integration, MerchantIntegration, IntegrationAPICall, IntegrationStatus, IntegrationType, AuthenticationType
)
from authentication.models import Merchant

logger = logging.getLogger(__name__)


class TransVoucherAPIException(Exception):
    """Custom exception for TransVoucher API errors"""
    def __init__(self, message: str, status_code: int = None, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class TransVoucherService:
    """Service class for TransVoucher API integration"""
    
    def __init__(self, merchant: Merchant = None):
        self.merchant = merchant
        
        # Get configuration from settings
        self.api_key = getattr(settings, 'TRANSVOUCHER_API_KEY', '')
        self.api_secret = getattr(settings, 'TRANSVOUCHER_API_SECRET', '')
        self.base_url = getattr(settings, 'TRANSVOUCHER_API_BASE_URL', 'https://api.transvoucher.com')
        self.is_sandbox = getattr(settings, 'TRANSVOUCHER_SANDBOX_MODE', True)
        
        # Get or create TransVoucher integration
        self.integration = self._get_or_create_integration()
        
        # Get merchant integration if merchant is provided
        self.merchant_integration = None
        if merchant:
            self.merchant_integration = self._get_merchant_integration()
    
    def _get_or_create_integration(self) -> Integration:
        """Get or create TransVoucher integration configuration"""
        integration, created = Integration.objects.get_or_create(
            code='transvoucher',
            defaults={
                'name': 'TransVoucher Payment Gateway',
                'provider_name': 'TransVoucher',
                'description': 'TransVoucher payment processing and voucher services',
                'integration_type': IntegrationType.PAYMENT_GATEWAY,
                'base_url': self.base_url,
                'is_sandbox': self.is_sandbox,
                'version': 'v1.0',
                'authentication_type': AuthenticationType.API_KEY,
                'supports_webhooks': True,
                'supports_bulk_operations': False,
                'supports_real_time': True,
                'rate_limit_per_minute': 60,
                'rate_limit_per_hour': 1000,
                'rate_limit_per_day': 10000,
                'status': IntegrationStatus.ACTIVE,
                'is_global': True,
                'provider_website': 'https://transvoucher.com/',
                'provider_documentation': 'https://transvoucher.com/api-documentation',
            }
        )
        
        if created:
            logger.info(f"Created new TransVoucher integration: {integration.id}")
        
        return integration
    
    def _get_merchant_integration(self) -> Optional[MerchantIntegration]:
        """Get merchant-specific integration configuration"""
        try:
            return MerchantIntegration.objects.get(
                merchant=self.merchant,
                integration=self.integration,
                is_enabled=True
            )
        except MerchantIntegration.DoesNotExist:
            return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key,
            'X-API-Secret' :  self.api_secret
        }
        
        # Add API secret if available from merchant integration
        if self.merchant_integration and self.merchant_integration.configuration:
            print("Merchant Integration Configuration:", self.merchant_integration.configuration)
            pass
            # api_secret = self.merchant_integration.configuration.get('api_secret')
            # if api_secret:
            #     headers['X-API-Secret'] = api_secret
        
        return headers
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        operation_type: str = 'general',
        reference_id: str = None
    ) -> Dict:
        """Make HTTP request to TransVoucher API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        # Log the API call (only if merchant integration exists)
        api_call = None
        if self.merchant_integration:
            api_call = IntegrationAPICall.objects.create(
                merchant_integration=self.merchant_integration,
                method=method.upper(),
                endpoint=endpoint,
                request_headers=headers,
                request_body=json.dumps(data or {}),
                operation_type=operation_type,
                reference_id=reference_id or str(uuid.uuid4())
            )
        
        try:
            # Make the request
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=data if data else None,
                timeout=30
            )
            
            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                response_data = {'raw_response': response.text}
            
            # Update API call record
            if api_call:
                api_call.status_code = response.status_code
                api_call.response_headers = dict(response.headers)
                api_call.response_body = json.dumps(response_data)
                api_call.is_successful = True
                api_call.save()
            
            # Check for errors
            if not response.ok:
                error_message = response_data.get('message', f'HTTP {response.status_code} error')
                if api_call:
                    api_call.error_message = error_message
                    api_call.is_successful = False
                    api_call.save()
                
                raise TransVoucherAPIException(
                    message=error_message,
                    status_code=response.status_code,
                    error_code=response_data.get('error_code')
                )
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            error_message = f"Request failed: {str(e)}"
            if api_call:
                api_call.error_message = error_message
                api_call.is_successful = False
                api_call.save()
            
            raise TransVoucherAPIException(message=error_message)
    
    def create_payment(
        self,
        amount: Decimal,
        currency: str = 'USD',
        title: str = '',
        description: str = '',
        reference_id: str = None,
        customer_details: Dict = None,
        metadata: Dict = None,
        redirect_url: str = None,
        customer_commission_percentage: float = None,
        multiple_use: bool = False,
        theme: Dict = None,
        lang: str = 'en'
    ) -> Dict:
        """Create a new payment session"""
        
        payment_data = {
            'amount': float(amount),
            'currency': currency,
            'title': title,
            'description': description,
            'multiple_use': multiple_use,
            'lang': lang
        }
        
        # Add optional fields
        if reference_id:
            payment_data['reference_id'] = reference_id
        if customer_details:
            payment_data['customer_details'] = customer_details
        if metadata:
            payment_data['metadata'] = metadata
        if redirect_url:
            payment_data['redirect_url'] = redirect_url
        if customer_commission_percentage is not None:
            payment_data['customer_commission_percentage'] = customer_commission_percentage
        if theme:
            payment_data['theme'] = theme
        
        return self._make_request(
            method='POST',
            endpoint='v1.0/payment/create',
            data=payment_data,
            operation_type='create_payment',
            reference_id=reference_id
        )
    
    def get_payment_status(self, reference_id: str) -> Dict:
        """Get payment status by reference ID"""
        return self._make_request(
            method='GET',
            endpoint=f'v1.0/payment/status/{reference_id}',
            operation_type='get_payment_status',
            reference_id=reference_id
        )
    
    def list_payments(
        self,
        limit: int = 10,
        page_token: str = None,
        status: str = None,
        from_date: str = None,
        to_date: str = None
    ) -> Dict:
        """List payments with pagination and filtering"""
        
        params = {'limit': limit}
        if page_token:
            params['page_token'] = page_token
        if status:
            params['status'] = status
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        
        # Convert params to query string
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        endpoint = f"v1.0/payment/list?{query_string}"
        
        return self._make_request(
            method='GET',
            endpoint=endpoint,
            operation_type='list_payments'
        )
    
    def setup_merchant_integration(
        self,
        merchant: Merchant,
        api_secret: str,
        configuration: Dict = None
    ) -> MerchantIntegration:
        """Setup TransVoucher integration for a merchant"""
        
        config = {
            'api_secret': api_secret,
            'webhook_url': configuration.get('webhook_url', '') if configuration else '',
            'return_url': configuration.get('return_url', '') if configuration else '',
            'failure_url': configuration.get('failure_url', '') if configuration else '',
        }
        
        if configuration:
            config.update(configuration)
        
        merchant_integration, created = MerchantIntegration.objects.get_or_create(
            merchant=merchant,
            integration=self.integration,
            defaults={
                'is_enabled': True,
                'status': IntegrationStatus.ACTIVE,
                'configuration': config
            }
        )
        
        if not created:
            merchant_integration.configuration = config
            merchant_integration.is_enabled = True
            merchant_integration.status = IntegrationStatus.ACTIVE
            merchant_integration.save()
        
        return merchant_integration
    
    def test_connection(self) -> Dict:
        """Test connection to TransVoucher API"""
        try:
            # Try to list payments with minimal parameters to test connection
            response = self.list_payments(limit=1)
            
            return {
                'success': True,
                'message': 'Connection successful',
                'response': response
            }
        except TransVoucherAPIException as e:
            return {
                'success': False,
                'message': f'Connection failed: {e.message}',
                'error_code': e.error_code,
                'status_code': e.status_code
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}'
            }
    
    def validate_webhook(self, payload: str, signature: str, secret: str) -> bool:
        """Validate webhook signature"""
        import hmac
        import hashlib
        
        try:
            computed_signature = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, computed_signature)
        except Exception as e:
            logger.error(f"Webhook validation error: {str(e)}")
            return False


def get_transvoucher_service(merchant: Merchant = None) -> TransVoucherService:
    """Get TransVoucher service instance"""
    return TransVoucherService(merchant=merchant)


def validate_transvoucher_credentials(api_key: str, api_secret: str = None) -> Dict:
    """Validate TransVoucher credentials"""
    if not api_key:
        return {
            'valid': False,
            'message': 'API key is required'
        }
    
    if not api_key.startswith('tv'):
        return {    
            'valid': False,
            'message': 'Invalid API key format. Should start with "tv-"'
        }
    if not api_secret:
        return {
            'valid': False,
            'message': 'API secret is required'
        }
    if not api_secret.startswith('tvcs'):
        return {
            'valid': False,
            'message': 'Invalid API secret format. Should start with "tvcs-"'
        }
    
    if len(api_key) < 20:
        return {
            'valid': False,
            'message': 'API key appears to be too short'
        }

    if len(api_secret) < 20:
        return {
            'valid': False,
            'message': 'API secret appears to be too short'
        }
    
    return {
        'valid': True,
        'message': 'Credentials format is valid'
    }