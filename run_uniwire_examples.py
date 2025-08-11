#!/usr/bin/env python

"""
Uniwire Examples

This script demonstrates how to use the Uniwire client for cryptocurrency operations.
"""

import json
import sys
import time
import os
import logging
import base64
import hmac
import hashlib
from dotenv import load_dotenv

from pexilabs import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('uniwire_examples')

# Load environment variables from .env file
load_dotenv()

class MockSettings:
    pass

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


# Create a mock settings module with values from environment variables
settings =  MockSettings()
settings.UNIWIRE_API_URL = os.getenv('UNIWIRE_API_BASE_URL', 'https://api.uniwire.com')
settings.UNIWIRE_API_KEY = os.getenv('UNIWIRE_API_KEY', 'test_api_key')
settings.UNIWIRE_API_SECRET = os.getenv('UNIWIRE_API_SECRET', 'test_api_secret')
settings.UNIWIRE_PROFILE_ID = os.getenv('UNIWIRE_PROFILE_ID', 'test_profile_id')
settings.UNIWIRE_SANDBOX_MODE = os.getenv('UNIWIRE_SANDBOX_MODE', 'True')
# Create the django.conf module if it doesn't exist
if 'django.conf' not in sys.modules:
    sys.modules['django.conf'] = type('module', (), {})()

# Assign our settings to django.conf.settings
sys.modules['django.conf'].settings = settings

print(f"UNIWIRE_API_BASE_URL: {settings.UNIWIRE_API_URL}")
print(f"UNIWIRE_API_KEY: {settings.UNIWIRE_API_KEY}")
print(f"UNIWIRE_API_SECRET: {settings.UNIWIRE_API_SECRET}")
print(f"UNIWIRE_PROFILE_ID: {settings.UNIWIRE_PROFILE_ID}")
print(f"UNIWIRE_SANDBOX_MODE: {settings.UNIWIRE_SANDBOX_MODE}")

# Create a custom requests session to log HTTP requests
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class LoggingHTTPAdapter(HTTPAdapter):
    def send(self, request, **kwargs):
        logger.info(f"Request: {request.method} {request.url}")
        logger.info(f"Request Headers: {request.headers}")
        if request.body:
            logger.info(f"Request Body: {request.body}")
        response = super().send(request, **kwargs)
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Headers: {response.headers}")
        if response.text:
            logger.info(f"Response Body: {response.text[:500]}{'...' if len(response.text) > 500 else ''}")
        return response

# Monkey patch requests to use our logging adapter
original_request = requests.request
def logging_request(method, url, **kwargs):
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5)
    adapter = LoggingHTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session.request(method, url, **kwargs)

requests.request = logging_request

# Create a simple example that doesn't rely on Django
def run_simple_example():
    logger.info("Starting Uniwire example")
    print("=== Simple Uniwire Example ===\n")
    
    # Import the client directly
    from integrations.uniwire.client import UniwireClient, UniwireAPIException
    from integrations.uniwire.utils import format_amount, is_supported_cryptocurrency, get_network_for_token, validate_address
    from integrations.uniwire.constants import COIN_BTC, COIN_ETH, TOKEN_ETH_USDT
    
    # Create a client instance with credentials from environment variables
    logger.info("Initializing Uniwire client with credentials from environment variables")
    client = UniwireClient(
         api_key=settings.UNIWIRE_API_KEY,
         api_secret=settings.UNIWIRE_API_SECRET,
         api_url=settings.UNIWIRE_API_URL
     )
    
    # Print client configuration
    print(f"Client configured with:")
    print(f"  API Key: {client.api_key[:4]}{'*' * (len(client.api_key) - 4) if len(client.api_key) > 4 else ''}")
    print(f"  API URL: {client.api_url}")
    print(f"  Sandbox Mode: {client.sandbox_mode}")
    logger.info(f"Client configured with API URL: {client.api_url}, Sandbox Mode: {client.sandbox_mode}")
    
    # Show how to construct a request
    endpoint = "profiles"
    method = "GET"
    timestamp = str(int(time.time()))
    nonce = "test_nonce"
    
    print(f"\nExample request construction:")
    print(f"  Endpoint: {endpoint}")
    print(f"  Method: {method}")
    print(f"  Timestamp: {timestamp}")
    print(f"  Nonce: {nonce}")
    
    # Show utility functions
    print("\n=== Utility Functions ===\n")
    
    # Format amounts
    btc_amount = 1.23456789
    eth_amount = 0.123456789012345678
    usdt_amount = 100.123456
    
    print(f"Formatted BTC amount: {format_amount(btc_amount, COIN_BTC, precision=8)}")
    print(f"Formatted ETH amount: {format_amount(eth_amount, COIN_ETH, precision=18)}")
    print(f"Formatted USDT amount: {format_amount(usdt_amount, TOKEN_ETH_USDT, precision=6)}")
    
    # Check supported cryptocurrencies
    print(f"\nIs BTC supported? {is_supported_cryptocurrency(COIN_BTC)}")
    print(f"Is ETH_USDT supported? {is_supported_cryptocurrency(TOKEN_ETH_USDT)}")
    print(f"Is INVALID_COIN supported? {is_supported_cryptocurrency('INVALID_COIN')}")
    
    # Get network for token
    print(f"\nNetwork for ETH_USDT: {get_network_for_token(TOKEN_ETH_USDT)}")
    
    # Validate addresses (example)
    btc_address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
    eth_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    
    print(f"\nIs {btc_address} a valid BTC address? {validate_address(btc_address, COIN_BTC)}")
    print(f"Is {eth_address} a valid ETH address? {validate_address(eth_address, COIN_ETH)}")
    
    # Show invoice creation payload structure
    print("\n=== Invoice Creation Example ===\n")
    
    profile_id = settings.UNIWIRE_PROFILE_ID
    invoice_payload = {
        "profile_id": profile_id,
        "kind": COIN_BTC,
        "amount": "10.00",
        "currency": "USD",
        "passthrough": json.dumps({"user_id": 123, "order_id": "ORD-12345"}),
        "notes": "Example invoice for product purchase",
        "fee_amount": "0.50",
        "exchange_rate_limit": "20000.00"
    }
    
    print("Invoice creation payload:")
    print(json.dumps(invoice_payload, indent=2))
    
    # Show reusable invoice address creation (network invoice without amount)
    print("\n=== Reusable Invoice Address Creation Example ===\n")
    print("# Using the API, create an invoice with the amount left blank (indicating a reusable address).")
    print("# The best approach is to create a network invoice without specifying a token.")
    print("# This way, regardless of which supported token the user deposits, you will receive the amount")
    print("# and currency in the callback body.")
    
    reusable_invoice_payload = {
        "profile_id": profile_id,
        "kind": COIN_ETH,  # Network coin (ETH) without specifying a token
        # No amount specified - makes this a reusable address
        "passthrough": json.dumps({"user_id": 123, "customer_reference": "CUST-456"}),
        "notes": "Reusable deposit address for user 123"
    }
    
    print("Reusable invoice address creation payload:")
    print(json.dumps(reusable_invoice_payload, indent=2))
    print("\n# After receiving the address, assign it to your user.")
    print("# This address can be reused for deposits of ETH as well as any supported tokens on Ethereum.")
    print("# Example: The same address can receive ETH, USDT, USDC, etc. on the Ethereum network.")
    
    # Function to create a network invoice
    def create_network_invoice(client, profile_id, passthrough_data):
        logger.info("Creating network invoice for reusable deposits")
        print("\n=== Creating Network Invoice ===\n")
        
        # Prepare payload
        payload = {
            "profile_id": profile_id,
            "kind": COIN_ETH,  # Use ETH instead of 'network' which is not a valid kind value
            "passthrough": json.dumps(passthrough_data),
            "notes": "Reusable deposit address"
        }
        
        print("Network invoice creation payload:")
        print(json.dumps(payload, indent=2))
        
        try:
            # Make the actual API call to create a network invoice
            logger.info("Making API call for network invoice creation")
            response = client.create_invoice(
                profile_id=profile_id,
                kind=COIN_ETH,  # Using ETH as the network coin
                passthrough=json.dumps(passthrough_data),
                notes="Reusable deposit address"
            )
            print("\nNetwork Invoice API Response:")
            print(json.dumps(response, indent=2))
            logger.info("Network invoice created successfully")
            return response.get('data')
        except UniwireAPIException as e:
            logger.error(f"API Error creating network invoice: {e.message}")
            print(f"\nAPI Error creating network invoice: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error creating network invoice: {str(e)}")
            print(f"\nUnexpected error creating network invoice: {str(e)}")
    
    # Demonstrate listing invoices
    def demonstrate_list_invoices(client, profile_id):
        logger.info("Demonstrating listing invoices")
        print("\n=== List Invoices Example ===\n")
        print("Fetching invoices for profile...")
        
        try:
            # Make the actual API call to list invoices
            logger.info("Making API call for listing invoices")
            response = client.get_invoices(profile_id=profile_id)
            print("Invoices List API Response:")
            print(json.dumps(response, indent=2))
            
            # Display the invoice information
            invoices = response.get('result', [])
            logger.info(f"Retrieved {len(invoices)} invoices")
            
            print("\nInvoice Summary:")
            if not invoices:
                print("  No invoices found")
            else:
                for i, invoice in enumerate(invoices, 1):
                    print(f"\n  Invoice #{i}:")
                    print(f"    ID: {invoice.get('id')}")
                    print(f"    Kind: {invoice.get('kind')}")
                    print(f"    Amount: {invoice.get('amount')}")
                    print(f"    Status: {invoice.get('status')}")
                    print(f"    Address: {invoice.get('address')}")
                    print(f"    Created At: {invoice.get('created_at')}")
            
            # Display pagination information if available
            if 'pagination' in response:
                print(f"\nPagination Information:")
                print(f"  Current Page: {response['pagination'].get('current_page', 1)}")
                print(f"  Total Pages: {response['pagination'].get('total_pages', 1)}")
                print(f"  Total Items: {response['pagination'].get('pagination_total', len(invoices))}")
            
            return invoices
        except UniwireAPIException as e:
            logger.error(f"API Error listing invoices: {e.message}")
            print(f"\nAPI Error listing invoices: {e.message}")
            
            # Fallback to mock data if API call fails
            logger.info("Using mock data for invoice listing demonstration")
            mock_response = {
                "result": [
                    {
                        "id": "mock_invoice_123",
                        "profile_id": profile_id,
                        "kind": COIN_ETH,
                        "amount": "0.1",
                        "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
                        "status": "pending",
                        "created_at": "2023-01-01T00:00:00Z"
                    }
                ]
            }
            
            print("Invoice List Response (Mock Fallback):")
            print(json.dumps(mock_response, indent=2))
            
            # Display the invoice information
            invoices = mock_response['result']
            logger.info(f"Retrieved {len(invoices)} invoices (mock)")
            
            print("\nInvoice Summary (Mock):")
            for i, invoice in enumerate(invoices, 1):
                print(f"\n  Invoice #{i}:")
                print(f"    ID: {invoice.get('id')}")
                print(f"    Kind: {invoice.get('kind')}")
                print(f"    Amount: {invoice.get('amount')}")
                print(f"    Status: {invoice.get('status')}")
                print(f"    Address: {invoice.get('address')}")
                print(f"    Created At: {invoice.get('created_at')}")
            
            return invoices
        except Exception as e:
            logger.error(f"Unexpected error listing invoices: {str(e)}")
            print(f"\nUnexpected error listing invoices: {str(e)}")
    
 
    # Call the new functions
    create_network_invoice(client, profile_id, passthrough_data={"user_id": 456, "type": "reusable_deposit"})
    demonstrate_list_invoices(client, profile_id)

    
    # Try to make an actual API call if credentials are provided
    print("\n=== Authentication Demonstration ===\n")
    
    # Demonstrate authentication process with detailed logging
    def demonstrate_auth_process(client):
        logger.info("Demonstrating authentication process")
        
        # Generate authentication headers for a sample request
        endpoint = "profiles"
        request_path = f"/v1/{endpoint}/"
        payload_nonce = str(int(time.time() * 1000))
        payload = {"request": request_path, "nonce": payload_nonce}
        
        # Log the authentication process
        logger.info(f"Preparing authentication for endpoint: {endpoint}")
        logger.info(f"Request path: {request_path}")
        logger.info(f"Nonce: {payload_nonce}")
        
        # Encode payload to base64 format
        encoded_payload = json.dumps(payload).encode()
        b64 = base64.b64encode(encoded_payload)
        logger.info(f"Base64 encoded payload: {b64}")
        
        # Create signature
        signature = hmac.new(client.api_secret.encode(), msg=b64, digestmod=hashlib.sha256).hexdigest()
        logger.info(f"Generated HMAC signature: {signature}")
        
        # Create headers
        headers = {
            'X-CC-KEY': client.api_key,
            'X-CC-PAYLOAD': b64,
            'X-CC-SIGNATURE': signature,
        }
        
        print("Authentication headers generated:")
        print(f"  API Key: {client.api_key[:4]}{'*' * (len(client.api_key) - 4) if len(client.api_key) > 4 else ''}")
        print(f"  Signature: {signature[:10]}...{signature[-10:]}")
        print(f"  Payload contains: request path and nonce")
        
        return headers
    
    # Generate and display authentication headers
    auth_headers = demonstrate_auth_process(client)
    
    # Try to make an actual API call if credentials are provided
    if settings.UNIWIRE_API_KEY != 'test_api_key' and settings.UNIWIRE_API_SECRET != 'test_api_secret':
        try:
            logger.info("Attempting to fetch profiles from Uniwire API")
            print("\n=== Live API Call ===\n")
            print("Fetching profiles...")
            
            # Test DNS resolution before making the API call
            import socket
            try:
                host = client.api_url.replace('https://', '').replace('http://', '').split('/')[0]
                logger.info(f"Testing DNS resolution for {host}")
                socket.gethostbyname(host)
                logger.info(f"DNS resolution successful for {host}")
            except socket.gaierror as e:
                logger.error(f"DNS resolution failed for {host}: {str(e)}")
                print(f"\nDNS resolution failed for {host}")
                print("This could be due to:")
                print("1. No internet connection")
                print("2. The API domain doesn't exist or is misspelled")
                print("3. DNS server issues")
                print("\nTrying to continue anyway...")
            
            # Proceed with API call
            profiles = client.get_profiles()
            print(f"Success! Received {len(profiles.get('data', []))} profiles")
            print(json.dumps(profiles, indent=2)[:500] + "..." if len(json.dumps(profiles)) > 500 else json.dumps(profiles, indent=2))
            
        except UniwireAPIException as e:
            logger.error(f"API Error: {e.message}, Status: {e.status_code}, Error Code: {e.error_code}")
            print(f"\nAPI Error: {e.message}")
            print(f"Status Code: {e.status_code}")
            print(f"Error Code: {e.error_code}")
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error: {str(e)}")
            print(f"\nConnection Error: Unable to connect to {client.api_url}")
            print("This could be due to:")
            print("1. No internet connection")
            print("2. The API server is down")
            print("3. Incorrect API URL")
            print(f"\nError details: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            print(f"\nUnexpected error: {str(e)}")
    else:
        # Show mock API response for demonstration
        print("\n=== Mock API Response ===\n")
        print("Using mock data since real credentials are not provided")
        
        mock_response = {
            "success": True,
            "data": [
                {
                    "id": "mock_profile_1",
                    "name": "Test Profile",
                    "created_at": "2023-01-01T00:00:00Z",
                    "balances": {
                        "BTC": "1.23456789",
                        "ETH": "10.123456789012345678",
                        "ETH_USDT": "1000.123456"
                    }
                }
            ]
        }
        
        print(json.dumps(mock_response, indent=2))
            
    print("\nAuthentication process completed with detailed logging.")
    print("Check the log output above for request/response details.")

if __name__ == "__main__":
    # Import time here to avoid circular imports
    import time
    
    try:
        run_simple_example()
        print("\nExample completed successfully!")
    except Exception as e:
        print(f"\nError running example: {str(e)}")