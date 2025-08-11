import json
import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status

from integrations.uniwire.client import UniwireClient, UniwireAPIException

User = get_user_model()


class UniwireEndpointsTestCase(TestCase):
    """Test case for Uniwire API endpoints"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.client.login(username='testuser', password='testpassword')
        
        # Mock data
        self.invoice_data = {
            'profile_id': 'test_profile_id',
            'kind': 'BTC',
            'amount': '100.00',
            'currency': 'USD',
            'passthrough': json.dumps({'user_id': 123, 'order_id': 'ORD-12345'}),
            'notes': 'Test invoice',
            'fee_amount': '0.50',
            'exchange_rate_limit': '20000.00'
        }
        
        self.network_invoice_data = {
            'profile_id': 'test_profile_id',
            'kind': 'ETH',
            'passthrough': json.dumps({'user_id': 456, 'type': 'reusable_deposit'}),
            'notes': 'Test reusable address'
        }
        
        self.mock_invoice_response = {
            'success': True,
            'data': {
                'id': 'test_invoice_id',
                'profile_id': 'test_profile_id',
                'kind': 'BTC',
                'amount': '100.00',
                'currency': 'USD',
                'address': 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                'status': 'new',
                'created_at': '2023-01-01T00:00:00Z'
            }
        }
        
        self.mock_invoices_list_response = {
            'success': True,
            'result': [
                {
                    'id': 'test_invoice_id_1',
                    'profile_id': 'test_profile_id',
                    'kind': 'BTC',
                    'amount': '100.00',
                    'currency': 'USD',
                    'address': 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                    'status': 'new',
                    'created_at': '2023-01-01T00:00:00Z'
                },
                {
                    'id': 'test_invoice_id_2',
                    'profile_id': 'test_profile_id',
                    'kind': 'ETH',
                    'amount': '1.00',
                    'currency': 'USD',
                    'address': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
                    'status': 'pending',
                    'created_at': '2023-01-02T00:00:00Z'
                }
            ],
            'pagination': {
                'current_page': 1,
                'total_pages': 1,
                'pagination_total': 2
            }
        }
    
    @patch.object(UniwireClient, 'create_invoice')
    def test_create_invoice(self, mock_create_invoice):
        """Test creating an invoice"""
        # Set up mock
        mock_create_invoice.return_value = self.mock_invoice_response
        
        # Make request
        url = reverse('integrations:uniwire-create-invoice')
        response = self.client.post(url, self.invoice_data, content_type='application/json')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json(), self.mock_invoice_response)
        
        # Check mock was called with correct arguments
        mock_create_invoice.assert_called_once_with(
            profile_id=self.invoice_data['profile_id'],
            kind=self.invoice_data['kind'],
            amount=self.invoice_data['amount'],
            currency=self.invoice_data['currency'],
            passthrough=self.invoice_data['passthrough'],
            min_confirmations=None,
            zero_conf_enabled=None,
            notes=self.invoice_data['notes'],
            fee_amount=self.invoice_data['fee_amount'],
            exchange_rate_limit=self.invoice_data['exchange_rate_limit']
        )
    
    @patch.object(UniwireClient, 'get_invoice')
    def test_get_invoice(self, mock_get_invoice):
        """Test getting an invoice"""
        # Set up mock
        mock_get_invoice.return_value = self.mock_invoice_response
        
        # Make request
        url = reverse('integrations:uniwire-get-invoice', args=['test_invoice_id'])
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), self.mock_invoice_response)
        
        # Check mock was called with correct arguments
        mock_get_invoice.assert_called_once_with(invoice_id='test_invoice_id')
    
    @patch.object(UniwireClient, 'get_invoices')
    def test_list_invoices(self, mock_get_invoices):
        """Test listing invoices"""
        # Set up mock
        mock_get_invoices.return_value = self.mock_invoices_list_response
        
        # Make request
        url = reverse('integrations:uniwire-list-invoices')
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), self.mock_invoices_list_response)
        
        # Check mock was called with correct arguments
        mock_get_invoices.assert_called_once_with(
            page=1,
            txid=None,
            address=None,
            status=None,
            profile_id=None
        )
    
    @patch.object(UniwireClient, 'create_invoice')
    def test_create_network_invoice(self, mock_create_invoice):
        """Test creating a network invoice (reusable address)"""
        # Set up mock
        mock_create_invoice.return_value = self.mock_invoice_response
        
        # Make request
        url = reverse('integrations:uniwire-create-network-invoice')
        response = self.client.post(url, self.network_invoice_data, content_type='application/json')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json(), self.mock_invoice_response)
        
        # Check mock was called with correct arguments
        mock_create_invoice.assert_called_once_with(
            profile_id=self.network_invoice_data['profile_id'],
            kind=self.network_invoice_data['kind'],
            passthrough=self.network_invoice_data['passthrough'],
            notes=self.network_invoice_data['notes']
        )
    
    @patch.object(UniwireClient, 'create_invoice')
    def test_create_invoice_api_error(self, mock_create_invoice):
        """Test handling API errors when creating an invoice"""
        # Set up mock to raise an exception
        mock_create_invoice.side_effect = UniwireAPIException(
            message="Invalid request",
            status_code=400,
            error_code="INVALID_REQUEST"
        )
        
        # Make request
        url = reverse('integrations:uniwire-create-invoice')
        response = self.client.post(url, self.invoice_data, content_type='application/json')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {
            "error": "Invalid request",
            "error_code": "INVALID_REQUEST"
        })


if __name__ == '__main__':
    unittest.main()