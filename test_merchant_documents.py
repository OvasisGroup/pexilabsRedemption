#!/usr/bin/env python
"""
Test script for merchant documents functionality
"""

import os
import sys
import django
from datetime import datetime, timedelta
import json

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from authentication.models import CustomUser, Merchant, MerchantDocument, DocumentType, DocumentStatus
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class MerchantDocumentsTest:
    def __init__(self):
        self.client = Client()
        self.merchant_user = None
        self.merchant = None
        
    def setup_test_data(self):
        """Create test merchant"""
        print("Setting up test data...")
        
        # Clean up any existing test data first
        try:
            existing_user = CustomUser.objects.filter(email='merchant@test.com').first()
            if existing_user:
                if hasattr(existing_user, 'merchant_account'):
                    existing_user.merchant_account.delete()
                existing_user.delete()
        except Exception as e:
            print(f"Warning: {e}")
        
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
            business_name='Test Business Documents',
            business_registration_number='REG123456',
            business_address='123 Test Street, Test City, Test State 12345',
            business_phone='+1234567890',
            business_email='contact@testbusiness.com',
            website_url='https://testbusiness.com',
            description='Test business for documents functionality',
            status='approved',
            is_verified=True
        )
        
        print(f"Created merchant: {self.merchant_user.email}")
        print(f"Created business: {self.merchant.business_name}")
        
    def test_merchant_login(self):
        """Test merchant authentication"""
        print("\\n1. Testing merchant login...")
        
        login_successful = self.client.login(
            username='merchant@test.com',
            password='testpass123'
        )
        
        if login_successful:
            print("✓ Merchant login successful")
            return True
        else:
            print("✗ Merchant login failed")
            return False
            
    def test_dashboard_access(self):
        """Test merchant dashboard access"""
        print("\\n2. Testing dashboard access...")
        
        url = reverse('dashboard:merchant_dashboard')
        response = self.client.get(url)
        
        if response.status_code == 200:
            print("✓ Dashboard accessible")
            # Check if documents section exists in response
            if 'Business Documents' in response.content.decode():
                print("✓ Documents section found in dashboard")
                return True
            else:
                print("✗ Documents section not found in dashboard")
                return False
        else:
            print(f"✗ Dashboard access failed: {response.status_code}")
            return False
            
    def test_document_upload_api(self):
        """Test document upload API"""
        print("\\n3. Testing document upload API...")
        
        # Create a test file
        test_file_content = b"Test document content - this is a dummy PDF file for testing"
        test_file = SimpleUploadedFile(
            "test_business_license.pdf",
            test_file_content,
            content_type="application/pdf"
        )
        
        url = reverse('dashboard:upload_document_api')
        data = {
            'document_type': DocumentType.BUSINESS_LICENSE,
            'title': 'Test Business License',
            'description': 'Test document upload via API',
            'document_file': test_file
        }
        
        response = self.client.post(url, data, format='multipart')
        
        if response.status_code == 200:
            response_data = json.loads(response.content)
            print(f"✓ Document uploaded successfully")
            print(f"  Document ID: {response_data.get('document_id')}")
            return response_data.get('document_id')
        else:
            print(f"✗ Document upload failed: {response.status_code}")
            if response.content:
                try:
                    error_data = json.loads(response.content)
                    print(f"  Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"  Response: {response.content.decode()}")
            return None
            
    def test_documents_in_dashboard(self):
        """Test that uploaded documents appear in dashboard"""
        print("\\n4. Testing documents display in dashboard...")
        
        # First check if documents exist in database
        document_count = MerchantDocument.objects.filter(merchant=self.merchant).count()
        print(f"  Documents in database: {document_count}")
        
        if document_count > 0:
            doc = MerchantDocument.objects.filter(merchant=self.merchant).first()
            print(f"  Document title: {doc.title}")
            print(f"  Document type: {doc.document_type}")
            print(f"  Document status: {doc.status}")
        
        url = reverse('dashboard:merchant_dashboard')
        response = self.client.get(url)
        
        if response.status_code == 200:
            content = response.content.decode()
            if 'Test Business License' in content:
                print("✓ Uploaded document appears in dashboard")
                return True
            else:
                print("✗ Uploaded document not found in dashboard")
                # Debug: check what's actually in the response
                if 'Business Documents' in content:
                    print("  - Documents section exists")
                    if 'No documents uploaded yet' in content:
                        print("  - Shows 'no documents' message")
                    else:
                        print("  - Documents section has content but not our test document")
                return False
        else:
            print(f"✗ Dashboard access failed: {response.status_code}")
            return False
            
    def test_document_delete_api(self, document_id):
        """Test document deletion API"""
        print(f"\\n5. Testing document deletion API...")
        
        if not document_id:
            print("✗ No document ID provided for deletion test")
            return False
            
        url = reverse('dashboard:delete_document_api', kwargs={'document_id': document_id})
        response = self.client.delete(url)
        
        if response.status_code == 200:
            print("✓ Document deleted successfully")
            return True
        else:
            print(f"✗ Document deletion failed: {response.status_code}")
            if response.content:
                try:
                    error_data = json.loads(response.content)
                    print(f"  Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"  Response: {response.content.decode()}")
            return False
            
    def test_document_statistics(self):
        """Test document statistics in dashboard"""
        print("\\n6. Testing document statistics...")
        
        # Create some test documents with different statuses
        MerchantDocument.objects.create(
            merchant=self.merchant,
            document_type=DocumentType.TAX_CERTIFICATE,
            title='Test Tax Certificate',
            description='Approved document',
            status=DocumentStatus.APPROVED,
            original_filename='tax_cert.pdf'
        )
        
        MerchantDocument.objects.create(
            merchant=self.merchant,
            document_type=DocumentType.BANK_STATEMENT,
            title='Test Bank Statement',
            description='Pending document',
            status=DocumentStatus.PENDING,
            original_filename='bank_statement.pdf'
        )
        
        MerchantDocument.objects.create(
            merchant=self.merchant,
            document_type=DocumentType.IDENTITY_DOCUMENT,
            title='Test ID Document',
            description='Rejected document',
            status=DocumentStatus.REJECTED,
            original_filename='id_document.pdf'
        )
        
        url = reverse('dashboard:merchant_dashboard')
        response = self.client.get(url)
        
        if response.status_code == 200:
            print("✓ Document statistics test completed")
            print("✓ Created documents with different statuses")
            return True
        else:
            print(f"✗ Dashboard access failed: {response.status_code}")
            return False
            
    def cleanup(self):
        """Clean up test data"""
        print("\\n7. Cleaning up test data...")
        
        try:
            # Delete documents
            MerchantDocument.objects.filter(merchant=self.merchant).delete()
            
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
        """Run all document tests"""
        print("Starting Merchant Documents Test...")
        print("=" * 60)
        print("MERCHANT DOCUMENTS FUNCTIONALITY TEST")
        print("=" * 60)
        
        tests_passed = 0
        total_tests = 6
        
        try:
            self.setup_test_data()
            
            if self.test_merchant_login():
                tests_passed += 1
                
            if self.test_dashboard_access():
                tests_passed += 1
                
            document_id = self.test_document_upload_api()
            if document_id:
                tests_passed += 1
                
                # Test dashboard display immediately after upload
                if self.test_documents_in_dashboard():
                    tests_passed += 1
                
                # Then test deletion
                if self.test_document_delete_api(document_id):
                    tests_passed += 1
            else:
                # Skip dependent tests if upload failed
                tests_passed += 0  # Skip dashboard display test
                tests_passed += 0  # Skip deletion test
                
            if self.test_document_statistics():
                tests_passed += 1
                
        except Exception as e:
            print(f"\\n✗ Test execution failed: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()
            
        print("=" * 60)
        print(f"TEST RESULTS: {tests_passed}/{total_tests} tests passed")
        print("=" * 60)
        
        if tests_passed == total_tests:
            print("🎉 All tests passed! Documents functionality is working correctly.")
        else:
            print("❌ Some tests failed. Please check the output above.")


if __name__ == '__main__':
    test = MerchantDocumentsTest()
    test.run_all_tests()
