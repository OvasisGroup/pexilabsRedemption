#!/usr/bin/env python
"""
Test script to verify Django admin functionality
"""
import os
import django
from django.conf import settings
from django.urls import reverse, NoReverseMatch
from django.contrib import admin
from django.apps import apps

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

def test_django_admin():
    """Test that Django admin is properly configured"""
    
    print("Testing Django Admin Configuration...")
    print("=" * 50)
    
    # Test admin URL
    try:
        admin_url = reverse('admin:index')
        print(f"✓ Admin index URL: {admin_url}")
    except NoReverseMatch as e:
        print(f"✗ Admin index URL failed: {e}")
        return False
    
    # Test admin site
    try:
        admin_site = admin.site
        print(f"✓ Admin site: {admin_site}")
    except Exception as e:
        print(f"✗ Admin site error: {e}")
        return False
    
    # Test registered models
    print("\nRegistered Models:")
    print("-" * 30)
    
    registered_models = admin.site._registry
    if not registered_models:
        print("✗ No models registered in admin")
        return False
    
    for model, model_admin in registered_models.items():
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        print(f"✓ {app_label}.{model_name} -> {model_admin.__class__.__name__}")
    
    # Test model admin URLs
    print("\nModel Admin URLs:")
    print("-" * 30)
    
    success_count = 0
    fail_count = 0
    
    for model in registered_models.keys():
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        
        try:
            # Test changelist URL
            changelist_url = reverse(f'admin:{app_label}_{model_name}_changelist')
            print(f"✓ {app_label}.{model_name} changelist -> {changelist_url}")
            success_count += 1
            
            # Test add URL
            add_url = reverse(f'admin:{app_label}_{model_name}_add')
            print(f"✓ {app_label}.{model_name} add -> {add_url}")
            success_count += 1
            
        except NoReverseMatch as e:
            print(f"✗ {app_label}.{model_name} URL error: {e}")
            fail_count += 1
        except Exception as e:
            print(f"✗ {app_label}.{model_name} unexpected error: {e}")
            fail_count += 1
    
    print("=" * 50)
    print(f"Total models registered: {len(registered_models)}")
    print(f"URL tests: {success_count} success, {fail_count} failed")
    
    if fail_count == 0:
        print("🎉 Django Admin is working correctly!")
        return True
    else:
        print("⚠️  Some admin URLs have issues!")
        return False

if __name__ == '__main__':
    test_django_admin()
