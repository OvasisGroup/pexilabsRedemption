"""UBA Integration Usage Service

This module provides a simplified interface for UBA integration
specifically designed for API key authenticated merchants.
"""

import uuid
import logging
from decimal import Decimal
from typing import Dict, Optional
from django.conf import settings
from django.utils import timezone

from .services import UBABankService, UBAAPIException
from .models import MerchantIntegration, Integration
from authentication.models import Merchant, AppKey

logger = logging.getLogger(__name__)


class UBAUsageService:
    """
    Simplified UBA service for API key authenticated merchants.
    Provides checkout functionality similar to the TypeScript implementation.
    """
    
    def __init__(self, app_key: AppKey = None, merchant: Merchant = None):
        """
        Initialize UBA usage service.
        
        Args:
            app_key: The authenticated API key
            merchant: Optional merchant instance (for direct merchant access)
        """
        self.app_key = app_key
        self.merchant = merchant
        
        # If we have an app_key but no merchant, try to find associated merchant
        if app_key and not merchant:
            self.merchant = self._get_merchant_from_app_key(app_key)
        
        # Initialize the underlying UBA service
        self.uba_service = UBABankService(merchant=self.merchant)
        
        # Get UBA configuration from merchant integration or defaults
        self.config = self._get_uba_config()
    
    def _get_merchant_from_app_key(self, app_key: AppKey) -> Optional[Merchant]:
        """
        Get merchant associated with the API key.
        For now, we'll use a simple approach - you may need to modify this
        based on your business logic.
        """
        try:
            # Option 1: If you have a direct relationship between partner and merchant
            # This assumes you have a way to link partners to merchants
            # You might need to add this relationship to your models
            
            # Option 2: Use the first merchant that has UBA integration
            # This is a simplified approach for demo purposes
            uba_integration = Integration.objects.get(code='uba_kenya')
            merchant_integration = MerchantIntegration.objects.filter(
                integration=uba_integration,
                is_enabled=True
            ).first()
            
            if merchant_integration:
                return merchant_integration.merchant
            
            return None
        except Exception as e:
            logger.warning(f"Could not find merchant for app_key {app_key.public_key}: {str(e)}")
            return None
    
    def _get_uba_config(self) -> Dict:
        """
        Get UBA configuration from merchant integration or use defaults.
        """
        config = {
            'access_token': settings.UBA_ACCESS_TOKEN,
            'base_url': settings.UBA_BASE_URL,
            'configuration_template_id': settings.UBA_CONFIGURATION_TEMPLATE_ID,
            'customization_template_id': settings.UBA_CUSTOMIZATION_TEMPLATE_ID,
        }
        
        # If we have a merchant with UBA integration, use their specific config
        if self.merchant:
            try:
                uba_integration = Integration.objects.get(code='uba_kenya')
                merchant_integration = MerchantIntegration.objects.get(
                    merchant=self.merchant,
                    integration=uba_integration,
                    is_enabled=True
                )
                
                # Override with merchant-specific configuration if available
                merchant_config = merchant_integration.configuration or {}
                if 'access_token' in merchant_config:
                    config['access_token'] = merchant_config['access_token']
                if 'configuration_template_id' in merchant_config:
                    config['configuration_template_id'] = merchant_config['configuration_template_id']
                if 'customization_template_id' in merchant_config:
                    config['customization_template_id'] = merchant_config['customization_template_id']
                    
            except (Integration.DoesNotExist, MerchantIntegration.DoesNotExist):
                logger.info(f"Using default UBA config for merchant {self.merchant.id}")
        
        return config
    
    def create_checkout_intent(self, payload: Dict) -> Dict:
        """
        Create a checkout intent similar to the TypeScript implementation.
        
        Args:
            payload: Checkout payload containing:
                - currency: Payment currency (e.g., 'KES')
                - amount: Payment amount
                - reference: Merchant reference
                - customer: Customer information with billing_address, email, phone
                - version: Optional version number (defaults to 1)
        
        Returns:
            Dict: Checkout response with status, resource data, and token
        """
        try:
            # Validate required fields
            required_fields = ['currency', 'amount', 'reference', 'customer']
            for field in required_fields:
                if field not in payload:
                    raise ValueError(f"Missing required field: {field}")
            
            customer = payload['customer']
            if 'billing_address' not in customer or 'email' not in customer or 'phone' not in customer:
                raise ValueError("Customer must include billing_address, email, and phone")
            
            # Generate additional references similar to TypeScript implementation
            reference2 = self._generate_reference()
            external_id = f"{payload['reference']}-{self._generate_reference().replace('REF', '')}"
            
            # Prepare checkout data
            checkout_data = {
                'currency': payload['currency'],
                'amount': Decimal(str(payload['amount'])),
                'reference': payload['reference'],
                'reference2': reference2,
                'external_id': external_id,
                'customer': {
                    'billing_address': payload['customer']['billing_address'],
                    'email': payload['customer']['email'],
                    'phone': payload['customer']['phone']
                },
                'configuration': {
                    'template_id': self.config['configuration_template_id']
                },
                'customisation': {
                    'template_id': self.config['customization_template_id']
                },
                'version': payload.get('version', 1)
            }
            
            # Create the payment page using the UBA service
            result = self.uba_service.create_payment_page(
                amount=checkout_data['amount'],
                currency=checkout_data['currency'],
                customer_email=checkout_data['customer']['email'],
                customer_phone=checkout_data['customer']['phone'],
                description=f"Payment for {checkout_data['reference']}",
                reference=checkout_data['reference']
            )
            
            # Format response to match TypeScript interface
            response = {
                'status': 200 if result.get('success', False) else 400,
                'error': None if result.get('success', False) else result.get('message', 'Unknown error'),
                'resource': {
                    'type': 'checkout',
                    'data': {
                        '_id': result.get('payment_id', str(uuid.uuid4())),
                        'version': checkout_data['version'],
                        'status': 'active' if result.get('success', False) else 'inactive',
                        'reason': result.get('message') if not result.get('success', False) else None,
                        'amount': float(checkout_data['amount']),
                        'currency': checkout_data['currency'],
                        'reference': checkout_data['reference'],
                        'journey': [],  # UBA specific journey data would go here
                        'created_at': timezone.now().isoformat(),
                        'updated_at': timezone.now().isoformat(),
                        'token': result.get('payment_token', result.get('checkout_url', ''))
                    }
                }
            }
            
            return response
            
        except UBAAPIException as e:
            logger.error(f"UBA API error in checkout intent: {str(e)}")
            return {
                'status': e.status_code or 400,
                'error': e.message,
                'resource': None
            }
        except Exception as e:
            logger.error(f"Error creating checkout intent: {str(e)}")
            return {
                'status': 500,
                'error': f"Checkout failed: {str(e)}",
                'resource': None
            }
    
    def get_payment_status(self, payment_id: str) -> Dict:
        """
        Get payment status for a given payment ID.
        
        Args:
            payment_id: The payment ID to check
            
        Returns:
            Dict: Payment status information
        """
        try:
            result = self.uba_service.get_payment_status(payment_id)
            return {
                'success': True,
                'data': result
            }
        except UBAAPIException as e:
            logger.error(f"UBA API error getting payment status: {str(e)}")
            return {
                'success': False,
                'error': e.message,
                'error_code': e.error_code
            }
        except Exception as e:
            logger.error(f"Error getting payment status: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_reference(self) -> str:
        """
        Generate a reference similar to the TypeScript implementation.
        """
        return f"PEXI-REF-{uuid.uuid4().hex[:8].upper()}"
    
    def validate_merchant_access(self) -> bool:
        """
        Validate that the current API key has access to UBA integration.
        
        Returns:
            bool: True if access is valid, False otherwise
        """
        if not self.app_key:
            return False
        
        # Check if the API key has the required scopes
        if not self.app_key.has_scope('write'):
            return False
        
        # Check if the partner is active
        if not self.app_key.partner.is_active:
            return False
        
        # Check if we have UBA integration available
        try:
            Integration.objects.get(code='uba_kenya', is_global=True)
            return True
        except Integration.DoesNotExist:
            return False
    
    def get_integration_info(self) -> Dict:
        """
        Get information about the UBA integration for this merchant.
        
        Returns:
            Dict: Integration information
        """
        try:
            uba_integration = Integration.objects.get(code='uba_kenya')
            
            info = {
                'integration_name': uba_integration.name,
                'provider_name': uba_integration.provider_name,
                'is_available': True,
                'is_sandbox': uba_integration.is_sandbox,
                'supported_currencies': ['KES', 'USD'],  # UBA Kenya supported currencies
                'supported_operations': [
                    'create_checkout_intent',
                    'get_payment_status',
                    'account_inquiry',
                    'fund_transfer',
                    'balance_inquiry'
                ]
            }
            
            if self.merchant:
                try:
                    merchant_integration = MerchantIntegration.objects.get(
                        merchant=self.merchant,
                        integration=uba_integration
                    )
                    info['merchant_integration'] = {
                        'is_enabled': merchant_integration.is_enabled,
                        'status': merchant_integration.status,
                        'created_at': merchant_integration.created_at.isoformat(),
                        'last_used_at': merchant_integration.last_used_at.isoformat() if merchant_integration.last_used_at else None
                    }
                except MerchantIntegration.DoesNotExist:
                    info['merchant_integration'] = {
                        'is_enabled': False,
                        'status': 'not_configured',
                        'message': 'Merchant has not configured UBA integration'
                    }
            
            return info
            
        except Integration.DoesNotExist:
            return {
                'integration_name': 'UBA Kenya Pay',
                'is_available': False,
                'error': 'UBA integration not found'
            }