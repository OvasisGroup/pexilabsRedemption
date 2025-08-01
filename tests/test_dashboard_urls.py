#!/usr/bin/env python
"""
Simple test to verify dashboard URLs resolve correctly
"""
import os
import django
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

def test_dashboard_urls():
    """Test that all dashboard URLs resolve correctly"""
    
    print("Testing Dashboard URL Resolution...")
    print("=" * 50)
    
    # Test dashboard URLs
    dashboard_urls = [
        ('dashboard:dashboard_redirect', 'Dashboard Redirect'),
        ('dashboard:admin_dashboard', 'Admin Dashboard'),
        ('dashboard:staff_dashboard', 'Staff Dashboard'),
        ('dashboard:moderator_dashboard', 'Moderator Dashboard'),
        ('dashboard:merchant_dashboard', 'Merchant Dashboard'),
        ('dashboard:user_dashboard', 'User Dashboard'),
    ]
    
    for url_name, description in dashboard_urls:
        try:
            url = reverse(url_name)
            print(f"✓ {description}: {url}")
        except Exception as e:
            print(f"✗ {description}: ERROR - {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Dashboard URL testing completed!")

if __name__ == '__main__':
    test_dashboard_urls()
