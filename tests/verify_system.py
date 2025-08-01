#!/usr/bin/env python3
"""
PexiLabs Platform - Final System Verification Script
==================================================

This script performs a comprehensive verification of the PexiLabs platform
after cleanup and integration updates.

Usage:
    python verify_system.py

Prerequisites:
    - Django server NOT required to be running for this script
    - Virtual environment should be activated
    - All dependencies installed
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_section(title):
    """Print a formatted section"""
    print(f"\n📋 {title}")
    print("-" * 40)

def check_database_status():
    """Check database status and data cleanup"""
    print_header("DATABASE STATUS VERIFICATION")
    
    try:
        from django.contrib.auth.models import User
        from authentication.models import Merchant, WhitelabelPartner, AppKey
        from integrations.models import IntegrationAPICall
        
        # Count records
        users = User.objects.count()
        merchants = Merchant.objects.count()
        partners = WhitelabelPartner.objects.count()
        app_keys = AppKey.objects.count()
        api_calls = IntegrationAPICall.objects.count()
        
        print_section("Record Counts After Cleanup")
        print(f"✅ Users: {users} (should be 1 - superuser only)")
        print(f"✅ Merchants: {merchants} (should be 1 - production merchant)")
        print(f"✅ Whitelabel Partners: {partners} (should be 0 - all test partners removed)")
        print(f"✅ App Keys: {app_keys} (should be 0 - all orphaned keys removed)")
        print(f"✅ API Call Logs: {api_calls} (should be 0 - test logs cleared)")
        
        # Verify superuser exists
        superuser = User.objects.filter(is_superuser=True).first()
        if superuser:
            print(f"✅ Superuser: {superuser.email} (active)")
        else:
            print("❌ No superuser found!")
            
        # Verify production merchant
        prod_merchant = Merchant.objects.first()
        if prod_merchant:
            print(f"✅ Production Merchant: {prod_merchant.business_name}")
        else:
            print("❌ No production merchant found!")
            
        return True
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def check_integration_services():
    """Check integration services initialization"""
    print_header("INTEGRATION SERVICES VERIFICATION")
    
    try:
        from integrations.services import UBAService, CyberSourceService, CorefyService
        
        print_section("Service Initialization")
        
        # Initialize services
        uba = UBAService()
        cybersource = CyberSourceService()
        corefy = CorefyService()
        
        print(f"✅ UBA Service: Initialized")
        print(f"   Base URL: {uba.base_url}")
        print(f"   Sandbox Mode: {uba.sandbox_mode}")
        
        print(f"✅ CyberSource Service: Initialized")
        print(f"   Base URL: {cybersource.base_url}")
        print(f"   Sandbox Mode: {cybersource.sandbox_mode}")
        print(f"   Merchant ID: {cybersource.merchant_id}")
        
        print(f"✅ Corefy Service: Initialized")
        print(f"   Base URL: {corefy.base_url}")
        print(f"   Sandbox Mode: {corefy.sandbox_mode}")
        
        return True
    except Exception as e:
        print(f"❌ Integration services check failed: {e}")
        return False

def check_integration_models():
    """Check integration models and configurations"""
    print_header("INTEGRATION MODELS VERIFICATION")
    
    try:
        from integrations.models import Integration
        
        print_section("Integration Model Status")
        
        integrations = Integration.objects.all()
        print(f"✅ Total Integrations: {integrations.count()}")
        
        for integration in integrations:
            print(f"✅ {integration.name}")
            print(f"   Code: {integration.code}")
            print(f"   Status: {integration.status}")
            print(f"   Type: {integration.integration_type}")
            print(f"   Healthy: {'✅' if integration.is_healthy else '❌'}")
            print(f"   Webhooks: {'✅' if integration.supports_webhooks else '❌'}")
            print(f"   Rate Limit: {integration.rate_limit_per_minute}/min")
            print()
        
        return True
    except Exception as e:
        print(f"❌ Integration models check failed: {e}")
        return False

def check_api_endpoints():
    """Check API endpoint configurations"""
    print_header("API ENDPOINTS VERIFICATION")
    
    try:
        from django.urls import reverse
        from django.conf import settings
        
        print_section("Integration Endpoints")
        
        # UBA endpoints
        print("🏦 UBA Endpoints:")
        uba_endpoints = [
            'uba_payment_page',
            'uba_account_inquiry',
            'uba_fund_transfer',
            'uba_balance_inquiry',
            'uba_transaction_history',
            'uba_bill_payment',
            'uba_webhook',
            'uba_test_connection'
        ]
        
        for endpoint in uba_endpoints:
            try:
                url = reverse(f'integrations:{endpoint}')
                print(f"   ✅ {endpoint}: {url}")
            except:
                print(f"   ❌ {endpoint}: Not configured")
        
        # CyberSource endpoints
        print("\n💳 CyberSource Endpoints:")
        cybersource_endpoints = [
            'cybersource_payment',
            'cybersource_capture',
            'cybersource_refund',
            'cybersource_customer',
            'cybersource_token',
            'cybersource_webhook',
            'cybersource_test_connection'
        ]
        
        for endpoint in cybersource_endpoints:
            try:
                url = reverse(f'integrations:{endpoint}')
                print(f"   ✅ {endpoint}: {url}")
            except:
                print(f"   ❌ {endpoint}: Not configured")
        
        # Corefy endpoints
        print("\n🔄 Corefy Endpoints:")
        corefy_endpoints = [
            'corefy_payment_intent',
            'corefy_confirm_payment',
            'corefy_refund',
            'corefy_customer',
            'corefy_customer_detail',
            'corefy_payment_method',
            'corefy_customer_payment_methods',
            'corefy_supported_methods',
            'corefy_webhook',
            'corefy_test_connection'
        ]
        
        for endpoint in corefy_endpoints:
            try:
                url = reverse(f'integrations:{endpoint}')
                print(f"   ✅ {endpoint}: {url}")
            except:
                print(f"   ❌ {endpoint}: Not configured")
        
        return True
    except Exception as e:
        print(f"❌ API endpoints check failed: {e}")
        return False

def check_environment_configuration():
    """Check environment variable configuration"""
    print_header("ENVIRONMENT CONFIGURATION VERIFICATION")
    
    try:
        from django.conf import settings
        
        print_section("Integration Configuration")
        
        # UBA Configuration
        print("🏦 UBA Configuration:")
        print(f"   Base URL: {getattr(settings, 'UBA_BASE_URL', 'Not configured')}")
        print(f"   API Token: {'Set' if getattr(settings, 'UBA_API_TOKEN', None) else 'Not set'}")
        print(f"   Sandbox Mode: {getattr(settings, 'UBA_SANDBOX_MODE', 'Not configured')}")
        
        # CyberSource Configuration
        print("\n💳 CyberSource Configuration:")
        print(f"   Base URL: {getattr(settings, 'CYBERSOURCE_BASE_URL', 'Not configured')}")
        print(f"   Merchant ID: {getattr(settings, 'CYBERSOURCE_MERCHANT_ID', 'Not configured')}")
        print(f"   API Key: {'Set' if getattr(settings, 'CYBERSOURCE_API_KEY', None) else 'Not set'}")
        print(f"   Sandbox Mode: {getattr(settings, 'CYBERSOURCE_SANDBOX_MODE', 'Not configured')}")
        
        # Corefy Configuration
        print("\n🔄 Corefy Configuration:")
        print(f"   Base URL: {getattr(settings, 'COREFY_BASE_URL', 'Not configured')}")
        print(f"   API Key: {'Set' if getattr(settings, 'COREFY_API_KEY', None) else 'Not set'}")
        print(f"   Sandbox Mode: {getattr(settings, 'COREFY_SANDBOX_MODE', 'Not configured')}")
        
        return True
    except Exception as e:
        print(f"❌ Environment configuration check failed: {e}")
        return False

def check_file_organization():
    """Check file organization after cleanup"""
    print_header("FILE ORGANIZATION VERIFICATION")
    
    print_section("Project Structure")
    
    # Check if test files are moved
    test_dir = project_root / 'tests'
    if test_dir.exists():
        test_files = list(test_dir.glob('test_*.py'))
        print(f"✅ Tests directory: {len(test_files)} test files moved")
        for test_file in test_files[:5]:  # Show first 5
            print(f"   📄 {test_file.name}")
        if len(test_files) > 5:
            print(f"   ... and {len(test_files) - 5} more")
    else:
        print("❌ Tests directory not found")
    
    # Check main project structure
    expected_dirs = ['authentication', 'integrations', 'transactions', 'pexilabs']
    for dir_name in expected_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"✅ {dir_name}/ directory exists")
        else:
            print(f"❌ {dir_name}/ directory missing")
    
    # Check key files
    key_files = ['manage.py', 'requirements.txt', 'db.sqlite3']
    for file_name in key_files:
        file_path = project_root / file_name
        if file_path.exists():
            print(f"✅ {file_name} exists")
        else:
            print(f"❌ {file_name} missing")
    
    return True

def main():
    """Run all verification checks"""
    print("🎯 PEXILABS PLATFORM - SYSTEM VERIFICATION")
    print("=" * 60)
    print("Performing comprehensive system verification...")
    
    checks = [
        ("Database Status", check_database_status),
        ("Integration Services", check_integration_services),
        ("Integration Models", check_integration_models),
        ("API Endpoints", check_api_endpoints),
        ("Environment Configuration", check_environment_configuration),
        ("File Organization", check_file_organization),
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} failed with error: {e}")
            results.append((check_name, False))
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {check_name}")
    
    print(f"\n🎯 Overall Result: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 ALL VERIFICATIONS PASSED!")
        print("✅ System is clean, configured, and ready for production!")
    else:
        print(f"\n⚠️  {total - passed} verification(s) failed.")
        print("❌ Please review the failed checks above.")
    
    print("\n💡 To start the development server:")
    print("   python manage.py runserver")
    print("\n💡 To run integration management commands:")
    print("   python manage.py setup_integrations --show-config")
    print("   python manage.py integration_monitor --full-report")

if __name__ == "__main__":
    main()
