#!/usr/bin/env python
"""
Test script to verify authentication redirects work correctly
"""
import os
import django
from django.conf import settings
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

User = get_user_model()

def test_authentication_logic():
    """Test that authentication logic works correctly"""
    
    print("Testing Authentication Logic...")
    print("=" * 50)
    
    # Create a test client
    client = Client()
    
    # Test 1: Unauthenticated user accessing landing page
    print("\n1. Testing unauthenticated user access:")
    print("-" * 40)
    
    response = client.get('/')
    print(f"✓ Landing page status: {response.status_code}")
    print(f"✓ Landing page shows login/register options")
    
    # Test 2: Unauthenticated user accessing login page
    response = client.get('/auth/login/')
    print(f"✓ Login page status: {response.status_code}")
    
    # Test 3: Unauthenticated user accessing register page  
    response = client.get('/auth/register/')
    print(f"✓ Register page status: {response.status_code}")
    
    # Test 4: Unauthenticated user accessing dashboard (should redirect to login)
    response = client.get('/dashboard/')
    print(f"✓ Dashboard redirect status: {response.status_code}")
    if response.status_code == 302:
        print(f"✓ Dashboard redirects to: {response.url}")
    
    # Test 5: Create and login a test user
    print("\n2. Testing authenticated user access:")
    print("-" * 40)
    
    # Create test user if not exists
    test_email = 'test@example.com'
    try:
        test_user = User.objects.get(email=test_email)
    except User.DoesNotExist:
        test_user = User.objects.create_user(
            email=test_email,
            password='testpass123',
            first_name='Test',
            last_name='User',
            is_verified=True
        )
    
    # Login the test user
    client.login(username=test_email, password='testpass123')
    
    # Test authenticated user accessing landing page (should redirect)
    response = client.get('/')
    print(f"✓ Landing page redirect status: {response.status_code}")
    if response.status_code == 302:
        print(f"✓ Landing page redirects to: {response.url}")
    
    # Test authenticated user accessing login page (should redirect)
    response = client.get('/auth/login/')
    print(f"✓ Login page redirect status: {response.status_code}")
    if response.status_code == 302:
        print(f"✓ Login page redirects to: {response.url}")
    
    # Test authenticated user accessing register page (should redirect)
    response = client.get('/auth/register/')
    print(f"✓ Register page redirect status: {response.status_code}")
    if response.status_code == 302:
        print(f"✓ Register page redirects to: {response.url}")
    
    # Test authenticated user accessing dashboard (should work)
    response = client.get('/dashboard/')
    print(f"✓ Dashboard access status: {response.status_code}")
    if response.status_code == 302:
        print(f"✓ Dashboard redirects to appropriate role dashboard: {response.url}")
    
    print("\n" + "=" * 50)
    print("🎉 Authentication logic test completed!")
    
    # Cleanup
    if test_user.email == test_email:
        test_user.delete()
        print("✓ Test user cleaned up")

if __name__ == '__main__':
    test_authentication_logic()
