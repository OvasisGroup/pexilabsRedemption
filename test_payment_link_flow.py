#!/usr/bin/env python
"""
Comprehensive end-to-end test for the payment link flow.
This script tests:
1. Merchant authentication
2. Payment link creation
3. Payment link access and processing
4. Payment completion flow
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
import json

# Add the project directory to the path
project_root = '/Users/asd/Desktop/desktop/pexilabs'
sys.path.insert(0, project_root)
os.chdir(project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

# Import models after Django setup
from authentication.models import CustomUser, Merchant, PreferredCurrency
from transactions.models import Transaction, PaymentLink

User = get_user_model()

class PaymentLinkFlowTest:
    def __init__(self):
        self.client = Client()
        self.merchant_user = None
        self.merchant = None
        
    def setup_test_data(self):
        """Create test merchant and business"""
        print("Setting up test data...")
        
        # Clean up any existing test data first
        try:
            existing_user = CustomUser.objects.filter(email='merchant@test.com').first()
            if existing_user:
                # Delete associated merchant if exists
                if hasattr(existing_user, 'merchant_account'):
                    existing_user.merchant_account.delete()
                existing_user.delete()
                print("Cleaned up existing test user")
        except Exception as e:
            print(f"Warning: {e}")
        
        # Create or get USD currency
        usd_currency, _ = PreferredCurrency.objects.get_or_create(
            code='USD',
            defaults={
                'name': 'US Dollar',
                'symbol': '$',
                'is_active': True
            }
        )
        
        # Create merchant user
        self.merchant_user = CustomUser.objects.create_user(
            email='merchant@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Merchant',
            phone_number='+1234567890',
            role='merchant'
        )
        
        # Create merchant profile
        self.merchant = Merchant.objects.create(
            user=self.merchant_user,
            business_name='Test Business',
            business_registration_number='REG123456',
            business_address='123 Test Street, Test City, Test State 12345',
            business_phone='+1234567890',
            business_email='contact@testbusiness.com',
            website_url='https://testbusiness.com',
            description='Test business for payment links',
            status='approved',
            is_verified=True
        )
        
        print(f"Created merchant: {self.merchant_user.email}")
        print(f"Created business: {self.merchant.business_name}")
        
    def test_merchant_login(self):
        """Test merchant authentication"""
        print("\n1. Testing merchant login...")
        
        login_successful = self.client.login(
            username='merchant@test.com',  # Use email as username
            password='testpass123'
        )
        
        if login_successful:
            print("✓ Merchant login successful")
            return True
        else:
            print("✗ Merchant login failed")
            return False
            
    def test_payment_link_creation_api(self):
        """Test payment link creation via API"""
        print("\n2. Testing payment link creation API...")
        
        # Get USD currency
        usd_currency = PreferredCurrency.objects.get(code='USD')
        
        # Test payment link creation API
        url = reverse('dashboard:create_payment_link_api')
        data = {
            'amount': 100.00,
            'currency': str(usd_currency.id),  # Use currency ID, not code
            'description': 'Test Payment Link',
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            response_data = json.loads(response.content)
            print(f"✓ Payment link created successfully")
            print(f"  Link slug: {response_data.get('slug')}")
            print(f"  Link URL: {response_data.get('link_url')}")
            return response_data.get('slug')
        else:
            print(f"✗ Payment link creation failed: {response.status_code}")
            print(f"  Response: {response.content.decode()}")
            return None
            
    def test_payment_link_access(self, slug):
        """Test accessing the payment link"""
        print(f"\n3. Testing payment link access...")
        
        if not slug:
            print("✗ No slug provided for testing")
            return False
            
        # Logout to test public access
        self.client.logout()
        
        # Access payment link
        url = reverse('payments:payment_link', kwargs={'slug': slug})
        response = self.client.get(url)
        
        if response.status_code == 200:
            print("✓ Payment link accessible")
            print(f"  URL: {url}")
            return True
        else:
            print(f"✗ Payment link access failed: {response.status_code}")
            return False
            
    def test_payment_processing(self, slug):
        """Test payment processing"""
        print(f"\n4. Testing payment processing...")
        
        if not slug:
            print("✗ No slug provided for testing")
            return False
            
        # Process payment by POSTing to the same payment link URL
        url = reverse('payments:payment_link', kwargs={'slug': slug})
        data = {
            'payment_method': 'card',
            'customer_email': 'customer@test.com',
            'customer_name': 'Test Customer',
            'customer_phone': '+1234567890',
            'customer_address': '123 Customer St, Customer City'
        }
        
        response = self.client.post(url, data)
        
        # Should redirect to success or completion page or return success
        if response.status_code in [200, 302]:
            print("✓ Payment processing initiated")
            if response.status_code == 302:
                print(f"  Redirected to: {response.url}")
            else:
                print("  Payment form processed successfully")
            return True
        else:
            print(f"✗ Payment processing failed: {response.status_code}")
            print(f"  Response: {response.content.decode()}")
            return False
            
    def test_merchant_transaction_view(self):
        """Test merchant transaction management view"""
        print("\n5. Testing merchant transaction view...")
        
        # Login as merchant
        self.client.login(username='merchant@test.com', password='testpass123')
        
        # Access merchant transactions page
        url = reverse('dashboard:merchant_transactions')
        response = self.client.get(url)
        
        if response.status_code == 200:
            print("✓ Merchant transactions page accessible")
            return True
        else:
            print(f"✗ Merchant transactions page failed: {response.status_code}")
            return False
            
    def test_transaction_creation_api(self):
        """Test transaction creation API"""
        print("\n6. Testing transaction creation API...")
        
        # Get USD currency
        usd_currency = PreferredCurrency.objects.get(code='USD')
        
        url = reverse('dashboard:create_transaction_api')
        data = {
            'transaction_type': 'payment',
            'payment_method': 'card',
            'amount': 250.00,
            'currency': str(usd_currency.id),  # Use currency ID
            'customer_email': 'customer@test.com',
            'customer_phone': '+1234567890',
            'description': 'API Test Transaction'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            response_data = json.loads(response.content)
            print("✓ Transaction created via API")
            print(f"  Transaction ID: {response_data.get('transaction_id')}")
            return response_data.get('transaction_id')
        else:
            print(f"✗ Transaction creation failed: {response.status_code}")
            print(f"  Response: {response.content.decode()}")
            return None
            
    def cleanup(self):
        """Clean up test data"""
        print("\n7. Cleaning up test data...")
        
        try:
            # Delete payment links
            PaymentLink.objects.filter(merchant=self.merchant).delete()
            
            # Delete transactions
            Transaction.objects.filter(merchant=self.merchant).delete()
            
            # Delete merchant
            if self.merchant:
                self.merchant.delete()
                
            # Delete user
            if self.merchant_user:
                self.merchant_user.delete()
                
            print("✓ Test data cleaned up")
        except Exception as e:
            print(f"✗ Cleanup failed: {str(e)}")
            
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("="*60)
        print("PAYMENT LINK FLOW - END-TO-END TEST")
        print("="*60)
        
        success_count = 0
        total_tests = 6
        
        try:
            # Setup
            self.setup_test_data()
            
            # Test 1: Merchant login
            if self.test_merchant_login():
                success_count += 1
                
            # Test 2: Payment link creation
            payment_link_slug = self.test_payment_link_creation_api()
            if payment_link_slug:
                success_count += 1
                
            # Test 3: Payment link access
            if self.test_payment_link_access(payment_link_slug):
                success_count += 1
                
            # Test 4: Payment processing
            if self.test_payment_processing(payment_link_slug):
                success_count += 1
                
            # Test 5: Merchant transaction view
            if self.test_merchant_transaction_view():
                success_count += 1
                
            # Test 6: Transaction creation API
            if self.test_transaction_creation_api():
                success_count += 1
                
        except Exception as e:
            print(f"\n✗ Test execution failed: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # Always cleanup
            self.cleanup()
            
        print("\n" + "="*60)
        print(f"TEST RESULTS: {success_count}/{total_tests} tests passed")
        print("="*60)
        
        return success_count == total_tests

def main():
    """Main test runner"""
    print("Starting Payment Link Flow Test...")
    
    test_runner = PaymentLinkFlowTest()
    success = test_runner.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Payment link flow is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
