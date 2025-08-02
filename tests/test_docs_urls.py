"""
URL Testing for Documentation System
"""
from django.test import TestCase, Client
from django.urls import reverse

class DocumentationURLTests(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_api_documentation_url(self):
        """Test that API documentation URL works"""
        response = self.client.get('/docs/api/')
        self.assertEqual(response.status_code, 200)
    
    def test_integration_guides_url(self):
        """Test that integration guides URL works"""
        response = self.client.get('/docs/integration/')
        self.assertEqual(response.status_code, 200)
    
    def test_sdk_documentation_url(self):
        """Test that SDK documentation URL works"""
        response = self.client.get('/docs/sdks/')
        self.assertEqual(response.status_code, 200)
    
    def test_webhook_testing_url(self):
        """Test that webhook testing URL works"""
        response = self.client.get('/docs/webhooks/')
        self.assertEqual(response.status_code, 200)
    
    def test_api_explorer_url(self):
        """Test that API explorer URL works"""
        response = self.client.get('/docs/explorer/')
        self.assertEqual(response.status_code, 200)
