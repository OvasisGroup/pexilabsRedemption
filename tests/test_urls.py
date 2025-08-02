#!/usr/bin/env python
"""
Test script to verify URL patterns are working correctly
"""
import os
import django
from django.conf import settings
from django.urls import reverse, NoReverseMatch

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

def test_url_patterns():
    """Test that all URL patterns resolve correctly"""
    
    # Test authentication URLs
    auth_urls = [
        'auth:register_page',
        'auth:login_page', 
        'auth:logout_page',
        'auth:verify_otp',
        'auth:resend_otp',
        'auth:verification_help',
    ]
    
    # Test dashboard URLs
    dashboard_urls = [
        'dashboard:admin_dashboard',
        'dashboard:user_dashboard',
        'dashboard:merchant_dashboard',
        'dashboard:staff_dashboard',
        'dashboard:moderator_dashboard',
        'dashboard:dashboard_redirect',
    ]
    
    # Test landing URLs
    landing_urls = [
        'landing:home',
        'landing:features',
        'landing:pricing',
        'landing:contact',
    ]
    
    all_urls = auth_urls + dashboard_urls + landing_urls
    
    print("Testing URL patterns...")
    print("=" * 50)
    
    success_count = 0
    fail_count = 0
    
    for url_name in all_urls:
        try:
            # For URLs that need parameters, provide dummy ones
            if 'verify_otp' in url_name or 'resend_otp' in url_name:
                url = reverse(url_name, kwargs={'user_id': 1})
            else:
                url = reverse(url_name)
            print(f"✓ {url_name:30} -> {url}")
            success_count += 1
        except NoReverseMatch as e:
            print(f"✗ {url_name:30} -> ERROR: {e}")
            fail_count += 1
        except Exception as e:
            print(f"✗ {url_name:30} -> UNEXPECTED ERROR: {e}")
            fail_count += 1
    
    print("=" * 50)
    print(f"Results: {success_count} success, {fail_count} failed")
    
    if fail_count == 0:
        print("🎉 All URL patterns are working correctly!")
    else:
        print("⚠️  Some URL patterns have issues!")
    
    return fail_count == 0

if __name__ == '__main__':
    test_url_patterns()
