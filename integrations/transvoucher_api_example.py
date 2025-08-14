#!/usr/bin/env python3
"""
TransVoucher Integration API Example

This script demonstrates how to use the TransVoucher integration with API key authentication.
It shows how to create payments, check payment status, and manage the integration.
"""

import requests
import json
from typing import Dict, Optional


class TransVoucherAPIClient:
    """
    Example client for TransVoucher integration using API key authentication.
    """
    
    def __init__(self, api_key: str, base_url: str = "http://127.0.0.1:8001"):
        """
        Initialize the TransVoucher API client.
        
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

    def create_payment(self, payment_data: Dict) -> Dict:
        """
        Create a TransVoucher payment.
        
        Args:
            payment_data: Payment information including amount, currency, title, etc.
            
        Returns:
            Dict: Payment creation response
        """
        url = f"{self.base_url}/integrations/transvoucher/payment/"
        
        try:
            response = self.session.post(url, json=payment_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}',
                'status_code': getattr(e.response, 'status_code', None)
            }

    def get_payment_status(self, reference_id: str) -> Dict:
        """
        Get TransVoucher payment status.
        
        Args:
            reference_id: Payment reference ID
            
        Returns:
            Dict: Payment status information
        """
        url = f"{self.base_url}/integrations/transvoucher/payment-status/{reference_id}/"
        
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

    def list_payments(self, **params) -> Dict:
        """
        List TransVoucher payments with optional filtering.
        
        Args:
            **params: Query parameters (limit, page_token, status, from_date, to_date)
            
        Returns:
            Dict: List of payments
        """
        url = f"{self.base_url}/integrations/transvoucher/payments/"
        
        try:
            response = self.session.get(url, params=params)
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
        Create a TransVoucher checkout session.
        
        Args:
            session_data: Checkout session information
            
        Returns:
            Dict: Checkout session response
        """
        url = f"{self.base_url}/integrations/transvoucher/checkout-session/"
        
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

    def get_integration_info(self) -> Dict:
        """
        Get TransVoucher integration information for the authenticated merchant.
        
        Returns:
            Dict: Integration information
        """
        url = f"{self.base_url}/integrations/transvoucher/integration-info/"
        
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

    def test_connection(self) -> Dict:
        """
        Test TransVoucher integration connection.
        
        Returns:
            Dict: Connection test result
        """
        url = f"{self.base_url}/integrations/transvoucher/test-connection/"
        
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


def main():
    """
    Example usage of the TransVoucher API client.
    """
    # Replace with your actual API key
    API_KEY = "pk_partner_example:sk_live_example"
    
    # Initialize the client
    client = TransVoucherAPIClient(API_KEY)
    
    print("🔗 TransVoucher Integration API Example")
    print("=" * 50)
    
    # Test connection
    print("\n1. Testing connection...")
    connection_result = client.test_connection()
    print(f"Connection test: {connection_result}")
    
    # Get integration info
    print("\n2. Getting integration info...")
    integration_info = client.get_integration_info()
    print(f"Integration info: {integration_info}")
    
    # Create a payment
    print("\n3. Creating a payment...")
    payment_data = {
        'amount': 100.00,
        'currency': 'USD',
        'title': 'Test Payment',
        'description': 'This is a test payment',
        'customer_email': 'customer@example.com',
        'customer_name': 'John Doe',
        'metadata': {
            'order_id': 'ORDER-123',
            'product_id': 'PROD-456'
        }
    }
    
    payment_result = client.create_payment(payment_data)
    print(f"Payment creation: {payment_result}")
    
    if payment_result.get('success') and payment_result.get('data'):
        reference_id = payment_result['data'].get('reference_id')
        
        if reference_id:
            # Check payment status
            print(f"\n4. Checking payment status for {reference_id}...")
            status_result = client.get_payment_status(reference_id)
            print(f"Payment status: {status_result}")
    
    # List payments
    print("\n5. Listing payments...")
    payments_list = client.list_payments(limit=5)
    print(f"Payments list: {payments_list}")
    
    # Create checkout session
    print("\n6. Creating checkout session...")
    session_data = {
        'amount': 50.00,
        'currency': 'USD',
        'title': 'Checkout Session Test',
        'description': 'Test checkout session',
        'customer_email': 'test@example.com',
        'customer_name': 'Jane Doe'
    }
    
    session_result = client.create_checkout_session(session_data)
    print(f"Checkout session: {session_result}")
    
    print("\n✅ TransVoucher API example completed!")


if __name__ == '__main__':
    main()