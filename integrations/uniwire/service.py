"""Uniwire Integration Service

This module provides a service class for integrating with Uniwire API
for cryptocurrency payment processing and management.
"""

import logging
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone

from . import UniwireClient, UniwireAPIException
from integrations.models import Integration, MerchantIntegration, IntegrationAPICall, IntegrationStatus
from authentication.models import Merchant

logger = logging.getLogger(__name__)


class UniwireService:
    """Service class for Uniwire API integration"""
    
    def __init__(self, merchant: Optional[Merchant] = None):
        """Initialize the Uniwire service
        
        Args:
            merchant: The merchant using the service (optional)
        """
        self.merchant = merchant
        self._client = None
        
        # Use sandbox mode by default in development
        self.sandbox_mode = getattr(settings, 'UNIWIRE_SANDBOX_MODE', True)
        
        # Initialize API credentials
        if self.sandbox_mode:
            self.api_key = getattr(settings, 'UNIWIRE_API_KEY', '')
            self.api_secret = getattr(settings, 'UNIWIRE_API_SECRET', '')
            self.api_profile_id =getattr(settings, 'UNIWIRE_PROFILE_ID')
            self.api_callback_token =  getattr(settings, 'UNIWIRE_API_CALLBACK_TOKEN')
            self.api_url = getattr(settings, 'UNIWIRE_API_BASE_URL', 'https://api.uniwire.com')
        else:
            self.api_key = getattr(settings, 'UNIWIRE_API_KEY', '')
            self.api_secret = getattr(settings, 'UNIWIRE_API_SECRET', '')
            self.api_profile_id =getattr(settings, 'UNIWIRE_PROFILE_ID')
            self.api_callback_token =  getattr(settings, 'UNIWIRE_API_CALLBACK_TOKEN')
            self.api_url = getattr(settings, 'UNIWIRE_API_BASE_URL', 'https://api.uniwire.com')
        
        # If merchant is provided, try to get their specific credentials
        if merchant:
            self._load_merchant_credentials()
    
    def _load_merchant_credentials(self):
        """Load merchant-specific credentials if available"""
        try:
            # Try to get merchant's Uniwire integration
            integration = Integration.objects.get(integration_type='uniwire')
            merchant_integration = MerchantIntegration.objects.get(
                merchant=self.merchant,
                integration=integration,
                status=IntegrationStatus.ACTIVE
            )
            
            # Use merchant-specific credentials if available
            if merchant_integration.credentials:
                credentials = merchant_integration.get_decrypted_credentials()
                self.api_key = credentials.get('api_key', self.api_key)
                self.api_secret = credentials.get('api_secret', self.api_secret)
                self.api_url = credentials.get('api_url', self.api_url)
                
                # Override sandbox mode if specified in merchant integration
                if 'sandbox_mode' in credentials:
                    self.sandbox_mode = credentials.get('sandbox_mode')
        
        except (Integration.DoesNotExist, MerchantIntegration.DoesNotExist):
            # Use default credentials if merchant integration not found
            pass
        except Exception as e:
            logger.error(f"Error loading Uniwire merchant credentials: {str(e)}")
    
    @property
    def client(self) -> UniwireClient:
        """Get or create the Uniwire API client
        
        Returns:
            UniwireClient instance
        """
        if not self._client:
            self._client = UniwireClient(
                api_key=self.api_key,
                api_secret=self.api_secret,
                api_url=self.api_url,
                sandbox_mode=self.sandbox_mode
            )
        return self._client
    
    def _log_api_call(self, endpoint: str, request_data: Dict[str, Any], 
                     response_data: Dict[str, Any], status: str, error: Optional[str] = None):
        """Log API call to database
        
        Args:
            endpoint: API endpoint called
            request_data: Request data sent to API
            response_data: Response data received from API
            status: Status of the API call (success/error)
            error: Error message if applicable
        """
        try:
            # Get Uniwire integration
            integration = Integration.objects.get(integration_type='uniwire')
            
            # Create API call log
            IntegrationAPICall.objects.create(
                integration=integration,
                merchant=self.merchant,
                endpoint=endpoint,
                request_data=request_data,
                response_data=response_data,
                status=status,
                error_message=error,
                timestamp=timezone.now()
            )
        except Exception as e:
            logger.error(f"Error logging Uniwire API call: {str(e)}")
    
    def get_profiles(self) -> Dict[str, Any]:
        """Get profiles from Uniwire API
        
        Returns:
            Profiles data
        """
        endpoint = 'profiles'
        request_data = {}
        
        try:
            response = self.client.get_profiles()
            self._log_api_call(endpoint, request_data, response, 'success')
            return response
        except UniwireAPIException as e:
            self._log_api_call(endpoint, request_data, {}, 'error', str(e))
            raise
    
    def get_profile(self, profile_id: str) -> Dict[str, Any]:
        """Get a specific profile from Uniwire API
        
        Args:
            profile_id: ID of the profile to retrieve
            
        Returns:
            Profile data
        """
        endpoint = f'profiles/{profile_id}'
        request_data = {'profile_id': profile_id}
        
        try:
            response = self.client.get_profile(profile_id)
            self._log_api_call(endpoint, request_data, response, 'success')
            return response
        except UniwireAPIException as e:
            self._log_api_call(endpoint, request_data, {}, 'error', str(e))
            raise
    
    def create_deposit_address(self, profile_id: str, kind: str) -> Dict[str, Any]:
        """Create a new deposit address for a specific cryptocurrency
        
        Args:
            profile_id: ID of the profile to create address for
            kind: Type of cryptocurrency (see CRYPTO_KINDS)
            
        Returns:
            Deposit address details
        """
        endpoint = 'deposit/address'
        request_data = {'profile_id': profile_id, 'kind': kind}
        
        try:
            response = self.client.create_deposit_address(profile_id, kind)
            self._log_api_call(endpoint, request_data, response, 'success')
            return response
        except UniwireAPIException as e:
            self._log_api_call(endpoint, request_data, {}, 'error', str(e))
            raise
    
    def get_deposit_addresses(self, profile_id: str, kind: Optional[str] = None) -> Dict[str, Any]:
        """Get deposit addresses for a profile
        
        Args:
            profile_id: ID of the profile to get addresses for
            kind: Type of cryptocurrency (optional, see CRYPTO_KINDS)
            
        Returns:
            List of deposit addresses
        """
        endpoint = 'deposit/addresses'
        request_data = {'profile_id': profile_id}
        if kind:
            request_data['kind'] = kind
        
        try:
            response = self.client.get_deposit_addresses(profile_id, kind)
            self._log_api_call(endpoint, request_data, response, 'success')
            return response
        except UniwireAPIException as e:
            self._log_api_call(endpoint, request_data, {}, 'error', str(e))
            raise
    
    def get_deposit_history(self, profile_id: str, kind: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """Get deposit history for a profile
        
        Args:
            profile_id: ID of the profile to get history for
            kind: Type of cryptocurrency (optional, see CRYPTO_KINDS)
            limit: Maximum number of records to return (default: 100)
            
        Returns:
            List of deposit transactions
        """
        endpoint = 'deposit/history'
        request_data = {'profile_id': profile_id, 'limit': limit}
        if kind:
            request_data['kind'] = kind
        
        try:
            response = self.client.get_deposit_history(profile_id, kind, limit)
            self._log_api_call(endpoint, request_data, response, 'success')
            return response
        except UniwireAPIException as e:
            self._log_api_call(endpoint, request_data, {}, 'error', str(e))
            raise
    
    def create_withdrawal(self, profile_id: str, kind: str, address: str, amount: str) -> Dict[str, Any]:
        """Create a withdrawal request
        
        Args:
            profile_id: ID of the profile to withdraw from
            kind: Type of cryptocurrency (see CRYPTO_KINDS)
            address: Destination address
            amount: Amount to withdraw
            
        Returns:
            Withdrawal request details
        """
        endpoint = 'withdrawal/create'
        request_data = {
            'profile_id': profile_id,
            'kind': kind,
            'address': address,
            'amount': amount
        }
        
        try:
            response = self.client.create_withdrawal(profile_id, kind, address, amount)
            self._log_api_call(endpoint, request_data, response, 'success')
            return response
        except UniwireAPIException as e:
            self._log_api_call(endpoint, request_data, {}, 'error', str(e))
            raise
    
    def get_withdrawal_history(self, profile_id: str, kind: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """Get withdrawal history for a profile
        
        Args:
            profile_id: ID of the profile to get history for
            kind: Type of cryptocurrency (optional, see CRYPTO_KINDS)
            limit: Maximum number of records to return (default: 100)
            
        Returns:
            List of withdrawal transactions
        """
        endpoint = 'withdrawal/history'
        request_data = {'profile_id': profile_id, 'limit': limit}
        if kind:
            request_data['kind'] = kind
        
        try:
            response = self.client.get_withdrawal_history(profile_id, kind, limit)
            self._log_api_call(endpoint, request_data, response, 'success')
            return response
        except UniwireAPIException as e:
            self._log_api_call(endpoint, request_data, {}, 'error', str(e))
            raise
    
    def get_balance(self, profile_id: str, kind: Optional[str] = None) -> Dict[str, Any]:
        """Get balance for a profile
        
        Args:
            profile_id: ID of the profile to get balance for
            kind: Type of cryptocurrency (optional, see CRYPTO_KINDS)
            
        Returns:
            Balance information
        """
        endpoint = 'balance'
        request_data = {'profile_id': profile_id}
        if kind:
            request_data['kind'] = kind
        
        try:
            response = self.client.get_balance(profile_id, kind)
            self._log_api_call(endpoint, request_data, response, 'success')
            return response
        except UniwireAPIException as e:
            self._log_api_call(endpoint, request_data, {}, 'error', str(e))
            raise
    
    def get_invoices(self, page: int = 1, txid: Optional[str] = None, address: Optional[str] = None, 
                    status: Optional[str] = None, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Get list of invoices with optional filtering
        
        Args:
            page: Page number for pagination (default: 1)
            txid: Filter invoices by transaction ID (optional)
            address: Filter invoices by receiving address (optional)
            status: Filter invoices by status (optional, values: "new", "pending", "complete", "expired")
            profile_id: Filter invoices by Profile ID (optional)
            
        Returns:
            Dict: Response containing invoices list with pagination
        """
        endpoint = 'invoices'
        request_data = {}
        if page > 1:
            request_data['p'] = page
        if txid:
            request_data['txid'] = txid
        if address:
            request_data['address'] = address
        if status:
            request_data['status'] = status
        if profile_id:
            request_data['profile_id'] = profile_id
        
        try:
            response = self.client.get_invoices(page, txid, address, status, profile_id)
            self._log_api_call(endpoint, request_data, response, 'success')
            return response
        except UniwireAPIException as e:
            self._log_api_call(endpoint, request_data, {}, 'error', str(e))
            raise
    
    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Get details of a specific invoice
        
        Args:
            invoice_id: ID of the invoice to retrieve
            
        Returns:
            Dict: Invoice details
        """
        endpoint = f'invoices/{invoice_id}'
        request_data = {'invoice_id': invoice_id}
        
        try:
            response = self.client.get_invoice(invoice_id)
            self._log_api_call(endpoint, request_data, response, 'success')
            return response
        except UniwireAPIException as e:
            self._log_api_call(endpoint, request_data, {}, 'error', str(e))
            raise
    
    def create_invoice(self, profile_id: str, kind: str, amount: Optional[str] = None, 
                      currency: str = 'USD', passthrough: Optional[str] = None, 
                      min_confirmations: Optional[int] = None, 
                      zero_conf_enabled: Optional[bool] = None,
                      notes: Optional[str] = None,
                      fee_amount: Optional[str] = None,
                      exchange_rate_limit: Optional[str] = None) -> Dict[str, Any]:
        """Create a new invoice
        
        Args:
            profile_id: Profile ID to use for settings, callback and wallet address generation
            kind: Invoice kind and chain (e.g., 'BTC', 'ETH')
            amount: Payment amount as decimal string (optional, leave blank for reusable addresses)
            currency: Currency for the specified payment amount (default: 'USD')
            passthrough: JSON string with custom data to pass through to callbacks (optional)
            min_confirmations: Minimum number of confirmations required (optional)
            zero_conf_enabled: Whether to enable zero-confirmation transactions (optional)
            notes: Additional notes for the invoice (optional)
            fee_amount: Fee amount as decimal string (optional)
            exchange_rate_limit: Minimum exchange rate limit as decimal string (optional)
            
        Returns:
            Dict: Created invoice details
        """
        endpoint = 'invoices'
        request_data = {
            'profile_id': profile_id,
            'kind': kind,
            'currency': currency
        }
        
        if amount:
            request_data['amount'] = amount
        if passthrough:
            request_data['passthrough'] = passthrough
        if min_confirmations is not None:
            request_data['min_confirmations'] = min_confirmations
        if zero_conf_enabled is not None:
            request_data['zero_conf_enabled'] = zero_conf_enabled
        if notes:
            request_data['notes'] = notes
        if fee_amount:
            request_data['fee_amount'] = fee_amount
        if exchange_rate_limit:
            request_data['exchange_rate_limit'] = exchange_rate_limit
        
        try:
            response = self.client.create_invoice(
                profile_id, kind, amount, currency, passthrough,
                min_confirmations, zero_conf_enabled, notes,
                fee_amount, exchange_rate_limit
            )
            self._log_api_call(endpoint, request_data, response, 'success')
            return response
        except UniwireAPIException as e:
            self._log_api_call(endpoint, request_data, {}, 'error', str(e))
            raise