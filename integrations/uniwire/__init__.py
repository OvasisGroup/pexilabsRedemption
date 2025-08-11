"""Uniwire Integration Module

This module provides integration with Uniwire API for cryptocurrency payment processing
and related services.
"""

# Import and expose key components will be done in the modules that need them
# Avoid circular imports by not importing here

import base64
import hashlib
import hmac
import json
import time
import requests
import logging
from typing import Dict, List, Optional, Union, Any
from django.conf import settings

logger = logging.getLogger(__name__)

# Default API URL
API_URL = getattr(settings, 'UNIWIRE_API_URL', 'https://api.uniwire.com')

# Supported cryptocurrency kinds
CRYPTO_KINDS = {
    # Bitcoin
    'BTC': 'Bitcoin On-chain',
    'BTC_P2SH': 'Bitcoin On-Chain (P2SH Segwit)',
    'BTC_BECH32': 'Bitcoin On-Chain (Bech32 / Native Segwit)',
    'BTC_LIGHTNING': 'Bitcoin Lightning Network invoice',
    
    # Other main cryptocurrencies
    'LTC': 'Litecoin',
    'XRP': 'Ripple',
    'DOGE': 'Dogecoin',
    'TON': 'The Open Network',
    'SOL': 'Solana',
    'ETH': 'Ethereum',
    'ETH-BASE': 'Ethereum on Base Network',
    'ETH-ARBITRUM': 'Ethereum on Arbitrum Network',
    'POL': 'Polygon POL',
    'BNB': 'Binance Coin (on BSC)',
    'TRX': 'Tron',
    'CELO': 'Celo main asset on Celo Network',
    
    # Ethereum ERC-20 tokens
    'ETH_USDT': 'Tether on Ethereum',
    'ETH_USDC': 'USD Coin on Ethereum',
    'ETH_TUSD': 'True USD on Ethereum',
    'ETH_PAX': 'Paxos Standard on Ethereum',
    'ETH_GUSD': 'Gemini Dollar on Ethereum',
    'ETH_SAND': 'The Sandbox on Ethereum',
    'ETH_SHIB': 'Shiba Inu on Ethereum',
    'ETH_BUSD': 'Binance USD on Ethereum',
    'ETH_SHFL': 'Shuffle on Ethereum',
    'ETH_cbBTC': 'Coinbase Wrapped BTC on Ethereum',
    'ETH_USD1': 'WLFI USD1 on Ethereum',
    
    # Polygon ERC-20 tokens
    'USDT-POLYGON': 'Tether on Polygon',
    'USDC-POLYGON': 'USD Coin on Polygon',
    'USDCE-POLYGON': 'USD Coin Bridged on Polygon',
    
    # Base Network ERC-20 tokens
    'USDC-BASE': 'USD Coin on Base',
    'cbBTC-BASE': 'Coinbase Wrapped BTC on Base',
    
    # Arbitrum ERC-20 tokens
    'USDT-ARBITRUM': 'Tether on Arbitrum',
    'USDC-ARBITRUM': 'USD Coin on Arbitrum',
    'USDCE-ARBITRUM': 'USD Coin Bridged on Arbitrum',
    
    # Celo ERC-20 tokens
    'CELO-CELO': 'Celo Token on Celo',
    'CUSD-CELO': 'Celo Dollar on Celo',
    'USDT-CELO': 'Tether on Celo',
    'USDC-CELO': 'USD Coin on Celo',
    
    # TRON Network TRC-20 Tokens
    'USDT-TRX': 'Tether on Tron',
    'USDC-TRX': 'USD Coin on Tron',
    
    # Solana Network SPL Tokens
    'USDT-SOL': 'Tether on Solana',
    'USDC-SOL': 'USD Coin on Solana',
    'WSOL-SOL': 'Wrapped Solana',
    'BONK-SOL': 'Bonk on Solana',
    'TRUMP-SOL': 'Official Trump on Solana',
    'JAMBO-SOL': 'Jambo on Solana',
    
    # Binance Smart Chain (BSC) BEP-20 Tokens
    'USDT-BSC': 'Tether on BSC',
    'USDC-BSC': 'USD Coin on BSC',
    'ETH-BSC': 'Binance-pegged Ethereum on BSC',
    'DAI-BSC': 'DAI on BSC',
    'SHIB-BSC': 'Shiba Inu on BSC',
    'BUSD': 'Binance USD on BSC',
    'WBNB': 'Wrapped BNB on BSC',
    'USD1-BSC': 'WLFI USD1 on BSC',
    
    # Liquid Network
    'L-BTC': 'Bitcoin on Liquid network',
    'L-USDT': 'Tether on Liquid network',
    
    # TON Jettons
    'USDT-TON': 'Tether Jetton on TON',
    'NOT-TON': 'Notcoin on TON',
}


def encode_hmac(key: str, msg, digestmod=hashlib.sha256) -> str:
    """
    Create HMAC signature using the provided key and message
    
    Args:
        key: The secret key for HMAC generation
        msg: The message to sign
        digestmod: The hash function to use (default: SHA-256)
        
    Returns:
        str: Hexadecimal digest of the HMAC
    """
    return hmac.new(key.encode(), msg=msg, digestmod=digestmod).hexdigest()


def uniwire_api_request(endpoint: str, payload: Optional[Dict] = None, method: str = 'GET',
                       api_key: Optional[str] = None, api_secret: Optional[str] = None,
                       api_url: Optional[str] = None) -> Dict:
    """
    Make an authenticated request to the Uniwire API
    
    Args:
        endpoint: API endpoint to call (without the /v1/ prefix)
        payload: Request payload (default: None)
        method: HTTP method (default: 'GET')
        api_key: Uniwire API key (default: from settings)
        api_secret: Uniwire API secret (default: from settings)
        api_url: Uniwire API URL (default: from settings or API_URL)
        
    Returns:
        Dict: JSON response from the API
        
    Raises:
        requests.RequestException: If the request fails
    """
    # Use provided credentials or fall back to settings
    api_key = api_key or getattr(settings, 'UNIWIRE_API_KEY', None)
    api_secret = api_secret or getattr(settings, 'UNIWIRE_API_SECRET', None)
    api_url = api_url or getattr(settings, 'UNIWIRE_API_URL', API_URL)
    
    if not api_key or not api_secret:
        raise ValueError("API key and secret are required for Uniwire API requests")
    
    # Prepare request
    payload_nonce = str(int(time.time() * 1000))
    request_path = '/v1/%s/' % endpoint
    payload = payload or {}
    payload.update({'request': request_path, 'nonce': payload_nonce})
    
    # Encode payload to base64 format and create signature
    encoded_payload = json.dumps(payload).encode()
    b64 = base64.b64encode(encoded_payload)
    signature = encode_hmac(api_secret, b64)
    
    # Add API key, encoded payload and signature to headers
    request_headers = {
        'X-CC-KEY': api_key,
        'X-CC-PAYLOAD': b64,
        'X-CC-SIGNATURE': signature,
    }
    
    # Make request
    response = requests.request(method, api_url + request_path, headers=request_headers)
    response.raise_for_status()  # Raise exception for HTTP errors
    
    return response.json()


def get_profiles(api_key: Optional[str] = None, api_secret: Optional[str] = None) -> List[Dict]:
    """
    Get list of profiles from Uniwire API
    
    Args:
        api_key: Uniwire API key (default: from settings)
        api_secret: Uniwire API secret (default: from settings)
        
    Returns:
        List[Dict]: List of profile objects
    """
    response = uniwire_api_request('profiles', api_key=api_key, api_secret=api_secret)
    return response.get('profiles', [])


def get_profile(profile_id: str, api_key: Optional[str] = None, api_secret: Optional[str] = None) -> Dict:
    """
    Get details of a specific profile
    
    Args:
        profile_id: ID of the profile to retrieve
        api_key: Uniwire API key (default: from settings)
        api_secret: Uniwire API secret (default: from settings)
        
    Returns:
        Dict: Profile details
    """
    return uniwire_api_request(f'profiles/{profile_id}', api_key=api_key, api_secret=api_secret)


def create_deposit_address(profile_id: str, kind: str, api_key: Optional[str] = None, 
                          api_secret: Optional[str] = None) -> Dict:
    """
    Create a new deposit address for a specific cryptocurrency
    
    Args:
        profile_id: ID of the profile to create address for
        kind: Type of cryptocurrency (see CRYPTO_KINDS)
        api_key: Uniwire API key (default: from settings)
        api_secret: Uniwire API secret (default: from settings)
        
    Returns:
        Dict: Deposit address details
    """
    if kind not in CRYPTO_KINDS:
        raise ValueError(f"Unsupported cryptocurrency kind: {kind}")
        
    payload = {
        'profile_id': profile_id,
        'kind': kind
    }
    
    return uniwire_api_request('deposit/address', payload=payload, method='POST',
                             api_key=api_key, api_secret=api_secret)


def get_deposit_addresses(profile_id: str, kind: Optional[str] = None, 
                         api_key: Optional[str] = None, api_secret: Optional[str] = None) -> List[Dict]:
    """
    Get deposit addresses for a profile
    
    Args:
        profile_id: ID of the profile to get addresses for
        kind: Type of cryptocurrency (optional, see CRYPTO_KINDS)
        api_key: Uniwire API key (default: from settings)
        api_secret: Uniwire API secret (default: from settings)
        
    Returns:
        List[Dict]: List of deposit addresses
    """
    payload = {'profile_id': profile_id}
    if kind:
        if kind not in CRYPTO_KINDS:
            raise ValueError(f"Unsupported cryptocurrency kind: {kind}")
        payload['kind'] = kind
    
    response = uniwire_api_request('deposit/addresses', payload=payload, method='POST',
                                 api_key=api_key, api_secret=api_secret)
    return response.get('addresses', [])


def get_deposit_history(profile_id: str, kind: Optional[str] = None, limit: int = 100,
                       api_key: Optional[str] = None, api_secret: Optional[str] = None) -> List[Dict]:
    """
    Get deposit history for a profile
    
    Args:
        profile_id: ID of the profile to get history for
        kind: Type of cryptocurrency (optional, see CRYPTO_KINDS)
        limit: Maximum number of records to return (default: 100)
        api_key: Uniwire API key (default: from settings)
        api_secret: Uniwire API secret (default: from settings)
        
    Returns:
        List[Dict]: List of deposit transactions
    """
    payload = {'profile_id': profile_id, 'limit': limit}
    if kind:
        if kind not in CRYPTO_KINDS:
            raise ValueError(f"Unsupported cryptocurrency kind: {kind}")
        payload['kind'] = kind
    
    response = uniwire_api_request('deposit/history', payload=payload, method='POST',
                                 api_key=api_key, api_secret=api_secret)
    return response.get('deposits', [])


def create_withdrawal(profile_id: str, kind: str, address: str, amount: str,
                     api_key: Optional[str] = None, api_secret: Optional[str] = None) -> Dict:
    """
    Create a withdrawal request
    
    Args:
        profile_id: ID of the profile to withdraw from
        kind: Type of cryptocurrency (see CRYPTO_KINDS)
        address: Destination address
        amount: Amount to withdraw
        api_key: Uniwire API key (default: from settings)
        api_secret: Uniwire API secret (default: from settings)
        
    Returns:
        Dict: Withdrawal request details
    """
    if kind not in CRYPTO_KINDS:
        raise ValueError(f"Unsupported cryptocurrency kind: {kind}")
        
    payload = {
        'profile_id': profile_id,
        'kind': kind,
        'address': address,
        'amount': amount
    }
    
    return uniwire_api_request('withdrawal/create', payload=payload, method='POST',
                             api_key=api_key, api_secret=api_secret)


def get_withdrawal_history(profile_id: str, kind: Optional[str] = None, limit: int = 100,
                          api_key: Optional[str] = None, api_secret: Optional[str] = None) -> List[Dict]:
    """
    Get withdrawal history for a profile
    
    Args:
        profile_id: ID of the profile to get history for
        kind: Type of cryptocurrency (optional, see CRYPTO_KINDS)
        limit: Maximum number of records to return (default: 100)
        api_key: Uniwire API key (default: from settings)
        api_secret: Uniwire API secret (default: from settings)
        
    Returns:
        List[Dict]: List of withdrawal transactions
    """
    payload = {'profile_id': profile_id, 'limit': limit}
    if kind:
        if kind not in CRYPTO_KINDS:
            raise ValueError(f"Unsupported cryptocurrency kind: {kind}")
        payload['kind'] = kind
    
    response = uniwire_api_request('withdrawal/history', payload=payload, method='POST',
                                 api_key=api_key, api_secret=api_secret)
    return response.get('withdrawals', [])


def get_balance(profile_id: str, kind: Optional[str] = None,
               api_key: Optional[str] = None, api_secret: Optional[str] = None) -> Dict:
    """
    Get balance for a profile
    
    Args:
        profile_id: ID of the profile to get balance for
        kind: Type of cryptocurrency (optional, see CRYPTO_KINDS)
        api_key: Uniwire API key (default: from settings)
        api_secret: Uniwire API secret (default: from settings)
        
    Returns:
        Dict: Balance information
    """
    payload = {'profile_id': profile_id}
    if kind:
        if kind not in CRYPTO_KINDS:
            raise ValueError(f"Unsupported cryptocurrency kind: {kind}")
        payload['kind'] = kind
    
    return uniwire_api_request('balance', payload=payload, method='POST',
                             api_key=api_key, api_secret=api_secret)