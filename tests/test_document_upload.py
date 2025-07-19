#!/usr/bin/env python3
"""
Test script for document upload functionality
"""

import requests
import json
import os
from io import BytesIO

BASE_URL = "http://127.0.0.1:9000/api/auth"

def test_document_upload():
    """Test the complete document upload workflow"""
    
    print("=== Testing Document Upload Functionality ===\n")
    
    # Step 1: Register a user with merchant account
    print("1. Registering user with merchant account...")
    registration_data = {
        "email": "merchant_test@example.com",
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "Test",
        "last_name": "Merchant",
        "business_name": "Test Business Solutions",
        "create_merchant_account": True
    }
    
    response = requests.post(f"{BASE_URL}/register/", json=registration_data)
    if response.status_code == 201:
        user_data = response.json()
        print(f"✅ User registered successfully")
        print(f"   - User ID: {user_data['user']['id']}")
        print(f"   - Merchant ID: {user_data.get('merchant_id', 'N/A')}")
    else:
        print(f"❌ Registration failed: {response.text}")
        return
    
    # Step 2: Login to get authentication token
    print("\n2. Logging in to get authentication token...")
    login_data = {
        "email": "merchant_test@example.com",
        "password": "TestPassword123!"
    }
    
    response = requests.post(f"{BASE_URL}/login/", json=login_data)
    if response.status_code == 200:
        login_response = response.json()
        access_token = login_response['access_token']
        print(f"✅ Login successful")
        headers = {"Authorization": f"Bearer {access_token}"}
    else:
        print(f"❌ Login failed: {response.text}")
        return
    
    # Step 3: Check merchant account documents
    print("\n3. Checking merchant document status...")
    response = requests.get(f"{BASE_URL}/documents/", headers=headers)
    if response.status_code == 200:
        doc_data = response.json()
        print(f"✅ Retrieved document status")
        print(f"   - Current documents: {len(doc_data['documents'])}")
        print(f"   - Verification progress: {doc_data['verification_progress']}")
        print(f"   - Required documents: {doc_data['required_documents']}")
    else:
        print(f"❌ Failed to get documents: {response.text}")
        return
    
    # Step 4: Create a test document file
    print("\n4. Creating test document file...")
    test_content = b"This is a test business license document for merchant verification."
    test_file = BytesIO(test_content)
    test_file.name = "business_license.pdf"
    
    # Step 5: Upload document
    print("\n5. Uploading business license document...")
    files = {
        'document_file': ('business_license.pdf', test_file, 'application/pdf')
    }
    data = {
        'document_type': 'business_license',
        'title': 'Business License Certificate',
        'description': 'Official business license for verification',
        'is_required': True
    }
    
    response = requests.post(f"{BASE_URL}/documents/", headers=headers, files=files, data=data)
    if response.status_code == 201:
        upload_response = response.json()
        document_id = upload_response['document']['id']
        print(f"✅ Document uploaded successfully")
        print(f"   - Document ID: {document_id}")
        print(f"   - File size: {upload_response['document']['file_size_display']}")
        print(f"   - Status: {upload_response['document']['status']}")
    else:
        print(f"❌ Document upload failed: {response.text}")
        return
    
    # Step 6: Check updated document status
    print("\n6. Checking updated document status...")
    response = requests.get(f"{BASE_URL}/documents/", headers=headers)
    if response.status_code == 200:
        doc_data = response.json()
        print(f"✅ Updated document status retrieved")
        print(f"   - Current documents: {len(doc_data['documents'])}")
        print(f"   - Verification progress: {doc_data['verification_progress']}")
    
    # Step 7: Get document details
    print("\n7. Getting document details...")
    response = requests.get(f"{BASE_URL}/documents/{document_id}/", headers=headers)
    if response.status_code == 200:
        doc_detail = response.json()
        print(f"✅ Document details retrieved")
        print(f"   - Title: {doc_detail['title']}")
        print(f"   - Type: {doc_detail['document_type']}")
        print(f"   - Status: {doc_detail['status']}")
        print(f"   - Uploaded: {doc_detail['uploaded_at']}")
    
    print("\n=== Document Upload Test Completed Successfully! ===")

if __name__ == "__main__":
    try:
        test_document_upload()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
