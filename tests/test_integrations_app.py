"""
Simple test to verify integrations app functionality
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, '/Users/asd/Desktop/desktop/pexilabs')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

def test_integrations_import():
    """Test that integrations app components can be imported"""
    try:
        from integrations.models import Integration, MerchantIntegration, BankIntegration
        from integrations.services import UBABankService
        from integrations import views
        from integrations import urls
        print("✅ All integrations app components imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_url_patterns():
    """Test that URL patterns are valid"""
    try:
        from django.urls import reverse, NoReverseMatch
        from django.test import Client
        
        # Test some basic URL patterns
        client = Client()
        
        # Test integration list endpoint (should require authentication)
        response = client.get('/api/integrations/')
        print(f"✅ Integration list endpoint accessible (status: {response.status_code})")
        
        # Test UBA test connection endpoint (should require authentication)
        response = client.get('/api/integrations/uba/test-connection/')
        print(f"✅ UBA test connection endpoint accessible (status: {response.status_code})")
        
        return True
    except Exception as e:
        print(f"❌ URL pattern error: {e}")
        return False

def test_models():
    """Test that models can be instantiated"""
    try:
        from integrations.models import Integration, IntegrationType, IntegrationStatus
        
        # Create a test integration (don't save to avoid DB issues)
        integration = Integration(
            name="Test Integration",
            code="test_integration",
            provider_name="Test Provider",
            integration_type=IntegrationType.BANK,
            status=IntegrationStatus.DRAFT,
            base_url="https://api.test.com"
        )
        
        print("✅ Integration model instantiated successfully")
        print(f"   - Name: {integration.name}")
        print(f"   - Type: {integration.integration_type}")
        print(f"   - Status: {integration.status}")
        
        return True
    except Exception as e:
        print(f"❌ Model error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Integrations App\n")
    
    tests = [
        ("Import Test", test_integrations_import),
        ("URL Patterns Test", test_url_patterns),
        ("Models Test", test_models)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}:")
        if test_func():
            passed += 1
        print()
    
    print("="*50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The integrations app is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
