"""Uniwire Integration Examples

This module provides examples of how to use the Uniwire integration.
"""

import json
from typing import Dict, Any
from django.conf import settings

from . import UniwireClient, UniwireAPIException
from .service import UniwireService
from .constants import COIN_BTC, TOKEN_ETH_USDT
from .utils import format_amount, is_supported_cryptocurrency, get_network_for_token, validate_address, parse_uniwire_error


def example_get_profiles():
    """Example: Get profiles from Uniwire API"""
    # Using the client directly
    try:
        # Initialize client with API credentials
        client = UniwireClient(
            api_key=settings.UNIWIRE_API_KEY,
            api_secret=settings.UNIWIRE_API_SECRET
        )
        
        # Make API request
        profiles = client.get_profiles()
        print(json.dumps(profiles, indent=2))
        
        return profiles
        
    except UniwireAPIException as e:
        print(f"Error: {e.message}")
        if e.status_code:
            print(f"Status code: {e.status_code}")
        if e.error_code:
            print(f"Error code: {e.error_code}")
        return None


def example_token_operations():
    """Example: Working with ERC-20 tokens"""
    # Initialize the service
    service = UniwireService()
    
    try:
        # Get profiles
        profiles = service.get_profiles()
        
        # Get the first profile ID
        if profiles.get('profiles') and len(profiles.get('profiles', [])) > 0:
            profile_id = profiles['profiles'][0]['id']
            
            # Create a deposit address for USDT on Ethereum
            deposit_address = service.create_deposit_address(profile_id, TOKEN_ETH_USDT)
            print("Created USDT deposit address on Ethereum:")
            print(json.dumps(deposit_address, indent=2))
            
            # Get balance for USDT on Ethereum
            balance = service.get_balance(profile_id, TOKEN_ETH_USDT)
            print("\nUSDT Balance on Ethereum:")
            print(json.dumps(balance, indent=2))
            
            # Get deposit history for USDT on Ethereum
            deposit_history = service.get_deposit_history(profile_id, TOKEN_ETH_USDT, limit=5)
            print("\nRecent USDT deposit history on Ethereum:")
            print(json.dumps(deposit_history, indent=2))
            
            return deposit_address
        else:
            print("No profiles found")
            return None
    except UniwireAPIException as e:
        print(f"Error: {e.message}")
        if e.status_code:
            print(f"Status code: {e.status_code}")
        if e.error_code:
            print(f"Error code: {e.error_code}")
        return None


def example_utility_functions():
    """Example: Using utility functions"""
    # Check if a cryptocurrency is supported
    print(f"Is BTC supported? {is_supported_cryptocurrency('BTC')}")
    print(f"Is ETH_USDT supported? {is_supported_cryptocurrency('ETH_USDT')}")
    print(f"Is INVALID_COIN supported? {is_supported_cryptocurrency('INVALID_COIN')}")
    
    # Format amounts with proper precision
    btc_amount = 1.23456789
    eth_amount = 10.123456789
    usdt_amount = 100.123456
    
    print(f"\nFormatted BTC amount: {format_amount(btc_amount, 'BTC')}")
    print(f"Formatted ETH amount: {format_amount(eth_amount, 'ETH')}")
    print(f"Formatted USDT amount: {format_amount(usdt_amount, 'ETH_USDT')}")
    
    # Get network for token
    print(f"\nNetwork for ETH_USDT: {get_network_for_token('ETH_USDT')}")
    print(f"Network for USDC-POLYGON: {get_network_for_token('USDC-POLYGON')}")
    
    # Validate addresses (example)
    btc_address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
    eth_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    
    print(f"\nIs {btc_address} a valid BTC address? {validate_address(btc_address, 'BTC')}")
    print(f"Is {eth_address} a valid ETH address? {validate_address(eth_address, 'ETH')}")
    
    # Parse Uniwire error (example)
    error_json = '{"error": "Invalid address", "error_code": "INVALID_ADDRESS"}'  
    error_data = json.loads(error_json)
    error_info = parse_uniwire_error(error_data)
    
    print(f"\nParsed error: {error_info['message']}")
    print(f"Error code: {error_info['code']}")
    print(f"User-friendly message: {error_info['user_message']}")


def example_invoice_operations():
    """Example: Working with Uniwire Invoices"""
    # Initialize the service
    service = UniwireService()
    
    try:
        # Get profiles
        profiles = service.get_profiles()
        
        # Get the first profile ID
        if profiles.get('profiles') and len(profiles.get('profiles', [])) > 0:
            profile_id = profiles['profiles'][0]['id']
            
            # List invoices (first page)
            invoices = service.get_invoices(page=1)
            print("Invoices (first page):")
            print(json.dumps(invoices, indent=2))
            
            # Create a new invoice for Bitcoin payment
            # Using a small amount for the example
            invoice = service.create_invoice(
                profile_id=profile_id,
                kind=COIN_BTC,
                amount="10.00",  # $10.00 USD
                currency="USD",
                passthrough=json.dumps({"user_id": 123, "order_id": "ORD-12345"}),
                notes="Example invoice for product purchase",
                fee_amount="0.50",  # $0.50 USD fee
                exchange_rate_limit="20000.00"  # Minimum exchange rate limit
            )
            print("\nCreated invoice:")
            print(json.dumps(invoice, indent=2))
            
            # Get the created invoice by ID
            invoice_id = invoice['result']['id']
            retrieved_invoice = service.get_invoice(invoice_id)
            print(f"\nRetrieved invoice {invoice_id}:")
            print(json.dumps(retrieved_invoice, indent=2))
            
            # Filter invoices by status
            new_invoices = service.get_invoices(status="new")
            print("\nNew invoices:")
            print(json.dumps(new_invoices, indent=2))
            
            # Create a reusable address (invoice without amount)
            reusable_invoice = service.create_invoice(
                profile_id=profile_id,
                kind=COIN_BTC,
                currency="USD"
            )
            print("\nCreated reusable address (invoice without amount):")
            print(json.dumps(reusable_invoice, indent=2))
            
            return invoice
        else:
            print("No profiles found")
            return None
    except UniwireAPIException as e:
        print(f"Error: {e.message}")
        if e.status_code:
            print(f"Status code: {e.status_code}")
        if e.error_code:
            print(f"Error code: {e.error_code}")
        return None


if __name__ == "__main__":
    # Run examples
    print("=== Example: Get Profiles ===\n")
    example_get_profiles()
    
    print("\n=== Example: Using Service ===\n")
    example_using_service()
    
    print("\n=== Example: Token Operations ===\n")
    example_token_operations()
    
    print("\n=== Example: Utility Functions ===\n")
    example_utility_functions()
    
    print("\n=== Example: Invoice Operations ===\n")
    example_invoice_operations()
    
    print("\n=== Example: Check Supported Cryptocurrencies ===\n")
    example_check_supported_cryptocurrencies()
    
    print("\n=== Example: Format Amounts ===\n")
    example_format_amounts()


def example_using_service():
    """Example: Using the UniwireService"""
    # Initialize the service
    service = UniwireService()
    
    try:
        # Get profiles using the service
        profiles = service.get_profiles()
        print("Profiles:")
        print(json.dumps(profiles, indent=2))
        
        # Get the first profile ID
        if profiles.get('profiles') and len(profiles.get('profiles', [])) > 0:
            profile_id = profiles['profiles'][0]['id']
            
            # Get specific profile details
            profile = service.get_profile(profile_id)
            print(f"\nProfile {profile_id} details:")
            print(json.dumps(profile, indent=2))
            
            # Create a deposit address for Bitcoin
            deposit_address = service.create_deposit_address(profile_id, COIN_BTC)
            print("\nCreated Bitcoin deposit address:")
            print(json.dumps(deposit_address, indent=2))
            
            # Get all deposit addresses
            addresses = service.get_deposit_addresses(profile_id)
            print("\nAll deposit addresses:")
            print(json.dumps(addresses, indent=2))
            
            # Get deposit history
            deposit_history = service.get_deposit_history(profile_id, limit=5)
            print("\nRecent deposit history:")
            print(json.dumps(deposit_history, indent=2))
            
            # Get balance
            balance = service.get_balance(profile_id)
            print("\nBalance:")
            print(json.dumps(balance, indent=2))
            
            # Example of creating a withdrawal (commented out for safety)
            # withdrawal = service.create_withdrawal(
            #     profile_id=profile_id,
            #     kind=COIN_BTC,
            #     address="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",  # Example address
            #     amount="0.001"
            # )
            # print("\nWithdrawal created:")
            # print(json.dumps(withdrawal, indent=2))
            
            # Get withdrawal history
            withdrawal_history = service.get_withdrawal_history(profile_id, limit=5)
            print("\nRecent withdrawal history:")
            print(json.dumps(withdrawal_history, indent=2))
        else:
            print("No profiles found")
            
        return profiles
    except UniwireAPIException as e:
        print(f"Error: {e.message}")
        return None


def example_check_supported_cryptocurrencies():
    """Example: Check if cryptocurrencies are supported"""
    # Check Bitcoin
    print(f"Is {COIN_BTC} supported? {is_supported_cryptocurrency(COIN_BTC)}")
    
    # Check Tether on Ethereum
    print(f"Is {TOKEN_ETH_USDT} supported? {is_supported_cryptocurrency(TOKEN_ETH_USDT)}")
    
    # Check an unsupported cryptocurrency
    print(f"Is UNKNOWN_COIN supported? {is_supported_cryptocurrency('UNKNOWN_COIN')}")


def example_format_amounts():
    """Example: Format amounts for API requests"""
    # Format a Bitcoin amount (8 decimals)
    btc_amount = 1.23456789
    btc_formatted = format_amount(btc_amount, COIN_BTC)
    print(f"Formatted BTC {btc_amount}: {btc_formatted}")
    
    # Format an Ethereum amount (18 decimals)
    eth_amount = 0.123456789012345678
    eth_formatted = format_amount(eth_amount, COIN_ETH)
    print(f"Formatted ETH {eth_amount}: {eth_formatted}")
    
    # Format a USDT amount (6 decimals)
    usdt_amount = 100.123456
    usdt_formatted = format_amount(usdt_amount, TOKEN_ETH_USDT)
    print(f"Formatted USDT {usdt_amount}: {usdt_formatted}")
    
    # Format with custom precision
    custom_amount = 0.123456789
    custom_formatted = format_amount(custom_amount, COIN_BTC, precision=4)
    print(f"Formatted BTC {custom_amount} with precision 4: {custom_formatted}")


# The main execution block is at the top of the file