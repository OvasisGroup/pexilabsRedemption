"""TransVoucher Integration Usage Service

This module provides a simplified interface for TransVoucher integration
specifically designed for API key authenticated merchants.
"""

import uuid
import logging
from decimal import Decimal
from typing import Dict, Optional
from django.conf import settings
from django.utils import timezone

from .service import TransVoucherService, TransVoucherAPIException
from ..models import MerchantIntegration, Integration
from authentication.models import Merchant, AppKey

logger = logging.getLogger(__name__)


class TransVoucherUsageService:
    """
    Simplified TransVoucher service for API key authenticated merchants.
    Provides checkout functionality similar to the TypeScript implementation.
    """
    
    def __init__(self,  merchant: Merchant = None):
        """
        Initialize TransVoucher usage service.
        
        Args:
            merchant: Optional merchant instance (for direct merchant access)
        """
        self.merchant = merchant
        
        # Initialize the underlying TransVoucher service
        self.transvoucher_service = TransVoucherService(merchant=self.merchant)
        
        # Get TransVoucher configuration from merchant integration or defaults
        self.config = self._get_transvoucher_config()
    
    def _get_transvoucher_config(self) -> Dict:
        """
        Get TransVoucher configuration from merchant integration or use defaults.
        """
        config = {
            'api_key': settings.TRANSVOUCHER_API_KEY,
            'api_secret': settings.TRANSVOUCHER_API_SECRET,
            'base_url': settings.TRANSVOUCHER_API_BASE_URL,
            'sandbox_mode': getattr(settings, 'TRANSVOUCHER_SANDBOX_MODE', True),
        }
        
        # If we have a merchant with TransVoucher integration, use their specific config
        if self.merchant:
            try:
                transvoucher_integration = Integration.objects.get(code='transvoucher')
                merchant_integration = MerchantIntegration.objects.get(
                    merchant=self.merchant,
                    integration=transvoucher_integration,
                    is_enabled=True
                )
                
                # Override with merchant-specific configuration if available
                merchant_config = merchant_integration.configuration or {}
                if 'api_secret' in merchant_config:
                    config['api_secret'] = merchant_config['api_secret']
                if 'webhook_url' in merchant_config:
                    config['webhook_url'] = merchant_config['webhook_url']
                if 'return_url' in merchant_config:
                    config['return_url'] = merchant_config['return_url']
                if 'failure_url' in merchant_config:
                    config['failure_url'] = merchant_config['failure_url']
                    
            except (Integration.DoesNotExist, MerchantIntegration.DoesNotExist):
                logger.info(f"No TransVoucher integration found for merchant {self.merchant.id}")
        
        return config
    
    def create_checkout_session(
        self,
        amount: Decimal,
        currency: str = 'USD',
        title: str = 'Payment',
        description: str = '',
        customer_email: str = None,
        customer_name: str = None,
        customer_phone: str = None,
        reference_id: str = None,
        metadata: Dict = None,
        customer_commission_percentage: float = None,
        multiple_use: bool = False
    ) -> Dict:
        """
        Create a checkout session for payment processing.
        
        This method provides a simplified interface similar to other payment gateways.
        
        Args:
            amount: Payment amount
            currency: Currency code (default: USD)
            title: Payment title
            description: Payment description
            customer_email: Customer email address
            customer_name: Customer full name
            customer_phone: Customer phone number
            reference_id: Optional reference ID
            metadata: Additional metadata
            customer_commission_percentage: Commission percentage for customer
            multiple_use: Whether payment link can be used multiple times
        
        Returns:
            Dict containing payment session details
        """
        try:
            # Prepare customer details if provided
            customer_details = None
            if customer_name or customer_email or customer_phone:
                customer_details = {}
                if customer_name:
                    customer_details['full_name'] = customer_name
                if customer_email:
                    customer_details['email'] = customer_email
                if customer_phone:
                    customer_details['phone'] = customer_phone
            
            # Generate reference ID if not provided
            if not reference_id:
                reference_id = f"txn_{uuid.uuid4().hex[:12]}"
            
            # Add merchant info to metadata
            if not metadata:
                metadata = {}
            
            if self.merchant:
                metadata.update({
                    'merchant_id': str(self.merchant.id),
                    'merchant_name': self.merchant.business_name or self.merchant.user.username
                })
        
            
            # Get return URL from config if available
            redirect_url = self.config.get('return_url')
            
            # Create payment using the service
            response = self.transvoucher_service.create_payment(
                amount=amount,
                currency=currency,
                title=title,
                description=description,
                reference_id=reference_id,
                customer_details=customer_details,
                metadata=metadata,
                redirect_url=redirect_url,
                customer_commission_percentage=customer_commission_percentage,
                multiple_use=multiple_use
            )
            
            # Transform response to match expected format
            if response.get('success') and response.get('data'):
                data = response['data']
                return {
                    'success': True,
                    'session_id': data.get('reference_id'),
                    'payment_url': data.get('payment_url'),
                    'transaction_id': data.get('transaction_id'),
                    'amount': data.get('amount'),
                    'currency': data.get('currency'),
                    'status': data.get('status', 'pending'),
                    'expires_at': data.get('expires_at'),
                    'reference_id': reference_id,
                    'metadata': metadata
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create payment session',
                    'details': response
                }
                
        except TransVoucherAPIException as e:
            logger.error(f"TransVoucher API error: {e.message}")
            return {
                'success': False,
                'error': e.message,
                'error_code': e.error_code,
                'status_code': e.status_code
            }
        except Exception as e:
            logger.error(f"Unexpected error creating checkout session: {str(e)}")
            return {
                'success': False,
                'error': f"Internal error: {str(e)}"
            }
    
    def get_payment_status(self, reference_id: str) -> Dict:
        """
        Get payment status by reference ID.
        
        Args:
            reference_id: Payment reference ID
        
        Returns:
            Dict containing payment status information
        """
        try:
            response = self.transvoucher_service.get_payment_status(reference_id)
            
            if response.get('success') and response.get('data'):
                data = response['data']
                return {
                    'success': True,
                    'transaction_id': data.get('transaction_id'),
                    'reference_id': data.get('reference_id'),
                    'amount': data.get('amount'),
                    'currency': data.get('currency'),
                    'status': data.get('status'),
                    'created_at': data.get('created_at'),
                    'updated_at': data.get('updated_at'),
                    'paid_at': data.get('paid_at'),
                    'payment_details': data.get('payment_details', {})
                }
            else:
                return {
                    'success': False,
                    'error': 'Payment not found or invalid response',
                    'details': response
                }
                
        except TransVoucherAPIException as e:
            logger.error(f"TransVoucher API error: {e.message}")
            return {
                'success': False,
                'error': e.message,
                'error_code': e.error_code,
                'status_code': e.status_code
            }
        except Exception as e:
            logger.error(f"Unexpected error getting payment status: {str(e)}")
            return {
                'success': False,
                'error': f"Internal error: {str(e)}"
            }
    
    def is_payment_completed(self, payment_data: Dict) -> bool:
        """
        Check if a payment is completed.
        
        Args:
            payment_data: Payment data from get_payment_status or create_checkout_session
        
        Returns:
            bool: True if payment is completed
        """
        if not payment_data.get('success'):
            return False
        
        status = payment_data.get('status', '').lower()
        return status in ['completed', 'succeeded', 'paid']
    
    def is_payment_failed(self, payment_data: Dict) -> bool:
        """
        Check if a payment has failed.
        
        Args:
            payment_data: Payment data from get_payment_status or create_checkout_session
        
        Returns:
            bool: True if payment has failed
        """
        if not payment_data.get('success'):
            return True
        
        status = payment_data.get('status', '').lower()
        return status in ['failed', 'declined', 'cancelled', 'expired']
    
    def test_integration(self) -> Dict:
        """
        Test the TransVoucher integration.
        
        Returns:
            Dict containing test results
        """
        try:
            # Test connection
            connection_test = self.transvoucher_service.test_connection()
            
            if connection_test['success']:
                return {
                    'success': True,
                    'message': 'TransVoucher integration is working correctly',
                    'merchant': self.merchant.business_name if self.merchant else 'No merchant',
                    'config': {
                        'api_key_configured': bool(self.config.get('api_key')),
                        'api_secret_configured': bool(self.config.get('api_secret')),
                        'webhook_url': self.config.get('webhook_url', 'Not configured'),
                        'sandbox_mode': self.config.get('sandbox_mode', True)
                    }
                }
            else:
                return {
                    'success': False,
                    'message': f"Integration test failed: {connection_test['message']}",
                    'details': connection_test
                }
                
        except Exception as e:
            logger.error(f"Integration test error: {str(e)}")
            return {
                'success': False,
                'message': f"Integration test error: {str(e)}"
            }


def get_transvoucher_usage_service(merchant: Merchant = None) -> TransVoucherUsageService:
    """Get TransVoucher usage service instance"""
    return TransVoucherUsageService( merchant=merchant)