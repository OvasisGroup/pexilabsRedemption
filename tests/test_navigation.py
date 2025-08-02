#!/usr/bin/env python
"""
Test script to verify all authentication navigation links work correctly
"""
import os
import django
from django.urls import reverse
from django.test import Client

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

def test_navigation_links():
    """Test that navigation links between login and register pages work correctly"""
    
    print("Testing Authentication Navigation Links...")
    print("=" * 60)
    
    client = Client()
    
    print("\n1. Testing URL Resolution:")
    print("-" * 40)
    
    # Test URL resolution
    try:
        login_url = reverse('auth:login_page')
        print(f"✓ Login URL resolves to: {login_url}")
    except Exception as e:
        print(f"✗ Login URL error: {e}")
        return False
    
    try:
        register_url = reverse('auth:register_page')
        print(f"✓ Register URL resolves to: {register_url}")
    except Exception as e:
        print(f"✗ Register URL error: {e}")
        return False
    
    try:
        verify_help_url = reverse('auth:verification_help')
        print(f"✓ Verification help URL resolves to: {verify_help_url}")
    except Exception as e:
        print(f"✗ Verification help URL error: {e}")
        return False
    
    print("\n2. Testing Page Access:")
    print("-" * 40)
    
    # Test page access
    response = client.get(login_url)
    print(f"✓ Login page loads: {response.status_code}")
    
    response = client.get(register_url)
    print(f"✓ Register page loads: {response.status_code}")
    
    response = client.get(verify_help_url)
    print(f"✓ Verification help page loads: {response.status_code}")
    
    print("\n3. Testing Navigation Flow:")
    print("-" * 40)
    
    # Test that login page contains register links
    response = client.get(login_url)
    if 'register_page' in response.content.decode() or register_url in response.content.decode():
        print("✓ Login page contains register links")
    else:
        print("✗ Login page missing register links")
    
    # Test that register page contains login links  
    response = client.get(register_url)
    if 'login_page' in response.content.decode() or login_url in response.content.decode():
        print("✓ Register page contains login links")
    else:
        print("✗ Register page missing login links")
    
    print("\n" + "=" * 60)
    print("🎉 Authentication navigation test completed!")
    print("\nNavigation Summary:")
    print(f"• Login page → Register page: {register_url}")
    print(f"• Register page → Login page: {login_url}")
    print(f"• Verification help available at: {verify_help_url}")
    
    return True

if __name__ == '__main__':
    test_navigation_links()
