#!/usr/bin/env python3
"""
UBA Integration API Example

This script demonstrates how to use the UBA integration with API key authentication.
It shows how to create checkout intents and check payment status using the merchant's API key.
"""

import requests
import json
from typing import Dict, Optional


class UBAAPIClient:
    """
    Example client for UBA integration using API key authentication.
    """
    
    def __init__(self, api_key: str, base_url: str = "http://127.0.0.1:8001"):
        """
        Initialize the UBA API client.
        
        Args:
            api_key: The merchant's API key in format "pk_partner_xxx:sk_live_yyy"
            base_url: Base URL of the API server
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def create_checkout_intent(self, checkout_data: Dict) -> Dict:
        """
        Create a checkout intent using UBA integration.
        
        Args:
            checkout_data: Checkout payload containing currency, amount, reference, customer info
            
        Returns:
            Dict: API response with checkout intent details
        """
        url = f"{self.base_url}/integrations/uba/api/checkout-intent/"
        
        try:
            response = self.session.post(url, json=checkout_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}',
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def get_payment_status(self, payment_id: str) -> Dict:
        """
        Get payment status for a given payment ID.
        
        Args:
            payment_id: The payment ID to check
            
        Returns:
            Dict: Payment status information
        """
        url = f"{self.base_url}/integrations/uba/api/payment-status/{payment_id}/"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}',
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def get_integration_info(self) -> Dict:
        """
        Get UBA integration information for the authenticated merchant.
        
        Returns:
            Dict: Integration information
        """
        url = f"{self.base_url}/integrations/uba/api/integration-info/"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}',
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def create_checkout_session(self, session_data: Dict) -> Dict:
        """
        Create a checkout session similar to the TypeScript implementation.
        
        Args:
            session_data: Session payload with merchant ID, amount, currency, customer info
            
        Returns:
            Dict: API response with session ID and checkout URL
        """
        url = f"{self.base_url}/integrations/api/checkout/session/"
        
        try:
            response = self.session.post(url, json=session_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}',
                'status_code': getattr(e.response, 'status_code', None)
            }


def example_usage():
    """
    Example usage of the UBA API client.
    """
    # Replace with your actual API key
    api_key = "pk_partner_example:sk_live_example123"
    
    # Initialize client
    client = UBAAPIClient(api_key)
    
    print("=== UBA Integration API Example ===")
    
    # 1. Get integration info
    print("\n1. Getting integration info...")
    info_result = client.get_integration_info()
    print(f"Integration info: {json.dumps(info_result, indent=2)}")
    
    # 2. Create checkout intent
    print("\n2. Creating checkout intent...")
    checkout_data = {
        "currency": "KES",
        "amount": 1000.00,
        "reference": "ORDER123456",
        "customer": {
            "billing_address": {
                "first_name": "John",
                "last_name": "Doe",
                "address_line1": "123 Main Street",
                "address_city": "Nairobi",
                "address_state": "Nairobi",
                "address_country": "KE",
                "address_postcode": "00100"
            },
            "email": "john.doe@example.com",
            "phone": "+254700000000"
        },
        "version": 1
    }
    
    checkout_result = client.create_checkout_intent(checkout_data)
    print(f"Checkout result: {json.dumps(checkout_result, indent=2)}")
    
    # 3. Create checkout session (TypeScript-style)
    print("\n3. Creating checkout session...")
    session_data = {
        "merchantId": "merchant_123",
        "amount": 1500.00,
        "currency": "KES",
        "successUrl": "https://example.com/success",
        "cancelUrl": "https://example.com/cancel",
        "customer": {
            "billing_address": {
                "first_name": "Jane",
                "last_name": "Smith",
                "address_line1": "456 Oak Avenue",
                "address_city": "Mombasa",
                "address_state": "Mombasa",
                "address_country": "KE",
                "address_postcode": "80100"
            },
            "email": "jane.smith@example.com",
            "phone": "+254711000000"
        },
        "cardNumber": "4111111111111111",
        "expiryDate": "12/25",
        "cvv": "123",
        "first_name": "Jane",
        "last_name": "Smith"
    }
    
    session_result = client.create_checkout_session(session_data)
    print(f"Session result: {json.dumps(session_result, indent=2)}")
    
    # 4. Check payment status (if we have a payment ID)
    if checkout_result.get('success') and checkout_result.get('resource', {}).get('data', {}).get('_id'):
        payment_id = checkout_result['resource']['data']['_id']
        print(f"\n4. Checking payment status for ID: {payment_id}")
        status_result = client.get_payment_status(payment_id)
        print(f"Payment status: {json.dumps(status_result, indent=2)}")
    else:
        print("\n4. Skipping payment status check (no payment ID available)")


if __name__ == "__main__":
    example_usage()