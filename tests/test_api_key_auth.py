"""
Test script for API Key Authentication

This script demonstrates how to use API key authentication with the integrations API.
"""

import requests
import json
import sys


def test_api_key_authentication(base_url, api_key):
    """
    Test API key authentication with various endpoints.
    
    Args:
        base_url (str): Base URL of the API (e.g., 'http://localhost:8000')
        api_key (str): API key in format 'public_key:secret_key'
    """
    
    print("🧪 Testing API Key Authentication")
    print("=" * 50)
    
    # Test endpoints
    endpoints = [
        {
            'name': 'Integration List',
            'method': 'GET',
            'url': f'{base_url}/api/integrations/',
            'headers': {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
        },
        {
            'name': 'Integration Stats',
            'method': 'GET',
            'url': f'{base_url}/api/integrations/stats/',
            'headers': {
                'X-API-Key': api_key,
                'Content-Type': 'application/json'
            }
        },
        {
            'name': 'UBA Test Connection',
            'method': 'GET',
            'url': f'{base_url}/api/integrations/uba/test-connection/',
            'headers': {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
        }
    ]
    
    results = []
    
    for endpoint in endpoints:
        print(f"\n📡 Testing: {endpoint['name']}")
        print(f"   Method: {endpoint['method']}")
        print(f"   URL: {endpoint['url']}")
        
        try:
            response = requests.request(
                method=endpoint['method'],
                url=endpoint['url'],
                headers=endpoint['headers'],
                timeout=10
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Success!")
                try:
                    data = response.json()
                    if isinstance(data, dict) and 'data' in data:
                        print(f"   📄 Response: {len(data.get('data', []))} items")
                    else:
                        print(f"   📄 Response length: {len(str(data))}")
                except:
                    print(f"   📄 Response length: {len(response.text)}")
            elif response.status_code == 401:
                print("   ❌ Authentication failed")
                try:
                    error_data = response.json()
                    print(f"   📄 Error: {error_data}")
                except:
                    print(f"   📄 Error: {response.text}")
            elif response.status_code == 403:
                print("   ⚠️  Permission denied")
            else:
                print(f"   ⚠️  Unexpected status: {response.status_code}")
                
            results.append({
                'endpoint': endpoint['name'],
                'status': response.status_code,
                'success': response.status_code == 200
            })
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {str(e)}")
            results.append({
                'endpoint': endpoint['name'],
                'status': 'error',
                'success': False
            })
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        status_icon = "✅" if result['success'] else "❌"
        print(f"   {status_icon} {result['endpoint']}: {result['status']}")
    
    print(f"\n🎯 Success Rate: {successful}/{total} ({(successful/total)*100:.1f}%)")
    
    if successful == total:
        print("🎉 All tests passed! API key authentication is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the configuration and try again.")
    
    return results


def main():
    """Main function to run the test."""
    if len(sys.argv) != 3:
        print("Usage: python test_api_key.py <base_url> <api_key>")
        print("Example: python test_api_key.py http://localhost:8000 pk_test_abc123:sk_test_xyz789")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    api_key = sys.argv[2]
    
    print(f"🌐 Base URL: {base_url}")
    print(f"🔑 API Key: {api_key[:20]}...")
    
    test_api_key_authentication(base_url, api_key)


if __name__ == "__main__":
    main()
