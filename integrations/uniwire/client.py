"""Uniwire Client Module

This module provides a client for interacting with the Uniwire API.
"""

import base64
import hashlib
import hmac
import json
import time
import requests
from typing import Dict, List, Optional, Union, Any

from django.conf import settings

# Default API URL
API_URL = getattr(settings, 'UNIWIRE_API_URL', 'https://api.uniwire.com')


class UniwireAPIException(Exception):
    """Custom exception for Uniwire API errors"""
    def __init__(self, message: str, status_code: int = None, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class UniwireClient:
    """Client for interacting with the Uniwire API"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, api_url: str = None, sandbox_mode: bool = None):
        """Initialize the Uniwire client
        
        Args:
            api_key: Uniwire API key (default: from settings)
            api_secret: Uniwire API secret (default: from settings)
            api_url: Uniwire API URL (default: from settings or API_URL)
            sandbox_mode: Whether to use sandbox mode (default: from settings)
        """
        self.api_key = api_key or getattr(settings, 'UNIWIRE_API_KEY', None)
        self.api_secret = api_secret or getattr(settings, 'UNIWIRE_API_SECRET', None)
        self.api_url = api_url or getattr(settings, 'UNIWIRE_API_URL', API_URL)
        self.sandbox_mode = sandbox_mode if sandbox_mode is not None else getattr(settings, 'UNIWIRE_SANDBOX_MODE', False)
        
        # If sandbox mode is enabled and API URL is the default, use sandbox URL
        if self.sandbox_mode and self.api_url == API_URL:
            self.api_url = self.api_url.replace('api.uniwire.com', 'api-sandbox.uniwire.com')
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret are required for Uniwire API client")
    
    def _encode_hmac(self, msg, digestmod=hashlib.sha256) -> str:
        """Create HMAC signature using the API secret
        
        Args:
            msg: The message to sign
            digestmod: The hash function to use (default: SHA-256)
            
        Returns:
            str: Hexadecimal digest of the HMAC
        """
        return hmac.new(self.api_secret.encode(), msg=msg, digestmod=digestmod).hexdigest()
    
    def _make_request(self, endpoint: str, payload: Optional[Dict] = None, method: str = 'GET') -> Dict:
        """Make an authenticated request to the Uniwire API
        
        Args:
            endpoint: API endpoint to call (without the /v1/ prefix)
            payload: Request payload (default: None)
            method: HTTP method (default: 'GET')
            
        Returns:
            Dict: JSON response from the API
            
        Raises:
            UniwireAPIException: If the API returns an error
            requests.RequestException: If the request fails
        """
        # Prepare request
        payload_nonce = str(int(time.time() * 1000))
        request_path = '/v1/%s/' % endpoint
        payload = payload or {}
        payload.update({'request': request_path, 'nonce': payload_nonce})
        
        # Encode payload to base64 format and create signature
        encoded_payload = json.dumps(payload).encode()
        b64 = base64.b64encode(encoded_payload)
        signature = self._encode_hmac(b64)
        
        # Add API key, encoded payload and signature to headers
        request_headers = {
            'X-CC-KEY': self.api_key,
            'X-CC-PAYLOAD': b64,
            'X-CC-SIGNATURE': signature,
        }
        
        try:
            # Make request
            response = requests.request(method, self.api_url + request_path, headers=request_headers)
            
            # Handle HTTP errors
            if response.status_code >= 400:
                error_data = response.json() if response.text else {}
                error_message = error_data.get('error', 'Unknown error')
                error_code = error_data.get('error_code')
                raise UniwireAPIException(
                    message=error_message,
                    status_code=response.status_code,
                    error_code=error_code
                )
            
            # Parse and return JSON response
            return response.json()
        except requests.RequestException as e:
            raise UniwireAPIException(f"Request failed: {str(e)}")
        except json.JSONDecodeError:
            raise UniwireAPIException("Invalid JSON response from API")
    
    # Profile methods
    def get_profiles(self) -> Dict:
        """Get list of profiles
        
        Returns:
            Dict: Response containing profiles list
        """
        return self._make_request('profiles')
    
    def get_profile(self, profile_id: str) -> Dict:
        """Get details of a specific profile
        
        Args:
            profile_id: ID of the profile to retrieve
            
        Returns:
            Dict: Profile details
        """
        return self._make_request(f'profiles/{profile_id}')
    
    # Deposit methods
    def create_deposit_address(self, profile_id: str, kind: str) -> Dict:
        """Create a new deposit address for a specific cryptocurrency
        
        Args:
            profile_id: ID of the profile to create address for
            kind: Type of cryptocurrency
            
        Returns:
            Dict: Deposit address details
        """
        payload = {
            'profile_id': profile_id,
            'kind': kind
        }
        
        return self._make_request('deposit/address', payload=payload, method='POST')
    
    def get_deposit_addresses(self, profile_id: str, kind: Optional[str] = None) -> Dict:
        """Get deposit addresses for a profile
        
        Args:
            profile_id: ID of the profile to get addresses for
            kind: Type of cryptocurrency (optional)
            
        Returns:
            Dict: Response containing addresses list
        """
        payload = {'profile_id': profile_id}
        if kind:
            payload['kind'] = kind
        
        return self._make_request('deposit/addresses', payload=payload, method='POST')
    
    def get_deposit_history(self, profile_id: str, kind: Optional[str] = None, limit: int = 100) -> Dict:
        """Get deposit history for a profile
        
        Args:
            profile_id: ID of the profile to get history for
            kind: Type of cryptocurrency (optional)
            limit: Maximum number of records to return (default: 100)
            
        Returns:
            Dict: Response containing deposits list
        """
        payload = {'profile_id': profile_id, 'limit': limit}
        if kind:
            payload['kind'] = kind
        
        return self._make_request('deposit/history', payload=payload, method='POST')
    
    # Withdrawal methods
    def create_withdrawal(self, profile_id: str, kind: str, address: str, amount: str) -> Dict:
        """Create a withdrawal request
        
        Args:
            profile_id: ID of the profile to withdraw from
            kind: Type of cryptocurrency
            address: Destination address
            amount: Amount to withdraw
            
        Returns:
            Dict: Withdrawal request details
        """
        payload = {
            'profile_id': profile_id,
            'kind': kind,
            'address': address,
            'amount': amount
        }
        
        return self._make_request('withdrawal/create', payload=payload, method='POST')
    
    def get_withdrawal_history(self, profile_id: str, kind: Optional[str] = None, limit: int = 100) -> Dict:
        """Get withdrawal history for a profile
        
        Args:
            profile_id: ID of the profile to get history for
            kind: Type of cryptocurrency (optional)
            limit: Maximum number of records to return (default: 100)
            
        Returns:
            Dict: Response containing withdrawals list
        """
        payload = {'profile_id': profile_id, 'limit': limit}
        if kind:
            payload['kind'] = kind
        
        return self._make_request('withdrawal/history', payload=payload, method='POST')
    
    # Balance methods
    def get_balance(self, profile_id: str, kind: Optional[str] = None) -> Dict:
        """Get balance for a profile
        
        Args:
            profile_id: ID of the profile to get balance for
            kind: Type of cryptocurrency (optional)
            
        Returns:
            Dict: Balance information
        """
        payload = {'profile_id': profile_id}
        if kind:
            payload['kind'] = kind
        
        return self._make_request('balance', payload=payload, method='POST')
    
    # Invoice methods
    def get_invoices(self, page: int = 1, txid: Optional[str] = None, address: Optional[str] = None, 
                    status: Optional[str] = None, profile_id: Optional[str] = None) -> Dict:
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
        payload = {}
        if page > 1:
            payload['p'] = page
        if txid:
            payload['txid'] = txid
        if address:
            payload['address'] = address
        if status:
            payload['status'] = status
        if profile_id:
            payload['profile_id'] = profile_id
        
        return self._make_request('invoices', payload=payload)
    
    def get_invoice(self, invoice_id: str) -> Dict:
        """Get details of a specific invoice
        
        Args:
            invoice_id: ID of the invoice to retrieve
            
        Returns:
            Dict: Invoice details
        """
        return self._make_request(f'invoices/{invoice_id}')
    
    def create_invoice(self, profile_id: str, kind: str, amount: Optional[str] = None, 
                      currency: str = 'USD', passthrough: Optional[str] = None, 
                      min_confirmations: Optional[int] = None, 
                      zero_conf_enabled: Optional[bool] = None,
                      notes: Optional[str] = None,
                      fee_amount: Optional[str] = None,
                      exchange_rate_limit: Optional[str] = None) -> Dict:
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
        payload = {
            'profile_id': profile_id,
            'kind': kind,
            'currency': currency
        }
        
        if amount:
            payload['amount'] = amount
        if passthrough:
            payload['passthrough'] = passthrough
        if min_confirmations is not None:
            payload['min_confirmations'] = min_confirmations
        if zero_conf_enabled is not None:
            payload['zero_conf_enabled'] = zero_conf_enabled
        if notes:
            payload['notes'] = notes
        if fee_amount:
            payload['fee_amount'] = fee_amount
        if exchange_rate_limit:
            payload['exchange_rate_limit'] = exchange_rate_limit
        
        return self._make_request('invoices', payload=payload, method='POST')