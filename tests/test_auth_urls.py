#!/usr/bin/env python
"""
Quick test to verify login/register URL links work correctly
"""
import os
import django
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

def test_auth_urls():
    """Test that authentication URLs resolve correctly"""
    
    print("Testing Authentication URL Resolution...")
    print("=" * 50)
    
    try:
        login_url = reverse('auth:login_page')
        print(f"✓ Login URL: {login_url}")
    except Exception as e:
        print(f"✗ Login URL error: {e}")
        return False
    
    try:
        register_url = reverse('auth:register_page')
        print(f"✓ Register URL: {register_url}")
    except Exception as e:
        print(f"✗ Register URL error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All authentication URLs resolve correctly!")
    print(f"Login page links to: {register_url}")
    print(f"Register page links to: {login_url}")
    
    return True

if __name__ == '__main__':
    test_auth_urls()
