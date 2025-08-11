"""Uniwire Utility Functions

This module provides utility functions for working with the Uniwire API.
"""

import re
from decimal import Decimal
from typing import Union, Dict, Optional

# Import CRYPTO_KINDS for validation
from . import CRYPTO_KINDS


def is_supported_cryptocurrency(kind: str) -> bool:
    """Check if a cryptocurrency kind is supported by Uniwire
    
    Args:
        kind: The cryptocurrency kind to check
        
    Returns:
        bool: True if supported, False otherwise
    """
    return kind in CRYPTO_KINDS


def format_amount(amount: Union[float, Decimal, str], kind: str, precision: int = None) -> str:
    """Format an amount with the appropriate precision for the cryptocurrency
    
    Args:
        amount: The amount to format
        kind: The cryptocurrency kind
        precision: Custom precision (optional)
        
    Returns:
        str: Formatted amount as string
    """
    # Default precision by cryptocurrency type
    default_precisions = {
        # Main cryptocurrencies
        'BTC': 8,
        'ETH': 18,
        'SOL': 9,
        'LTC': 8,
        'XRP': 6,
        'DOGE': 8,
        'TON': 9,
        'POL': 18,  # Polygon
        'BNB': 18,
        'TRX': 6,
        'CELO': 18,
        
        # Stablecoins and tokens (generally 6 decimals)
        'ETH_USDT': 6,
        'ETH_USDC': 6,
        'ETH_TUSD': 6,
        'ETH_PAX': 6,
        'ETH_GUSD': 6,
        'ETH_BUSD': 6,
        'USDT-POLYGON': 6,
        'USDC-POLYGON': 6,
        'USDC-BASE': 6,
        'USDT-ARBITRUM': 6,
        'USDC-ARBITRUM': 6,
        'USDT-TRX': 6,
        'USDC-TRX': 6,
        'USDT-SOL': 6,
        'USDC-SOL': 6,
        'USDT-BSC': 6,
        'USDC-BSC': 6,
        'L-USDT': 6,
        'USDT-TON': 6,
    }
    
    # Convert to Decimal for precise calculation
    if isinstance(amount, str):
        amount = Decimal(amount)
    else:
        amount = Decimal(str(amount))
    
    # Get precision for the cryptocurrency
    if precision is None:
        # Check if kind is in default precisions
        if kind in default_precisions:
            precision = default_precisions[kind]
        else:
            # Extract base cryptocurrency from token
            base_crypto = kind.split('_')[0] if '_' in kind else kind.split('-')[0] if '-' in kind else kind
            precision = default_precisions.get(base_crypto, 8)  # Default to 8 if not found
    
    # Format the amount with the appropriate precision
    return f"{amount:.{precision}f}".rstrip('0').rstrip('.') if '.' in f"{amount:.{precision}f}" else f"{amount:.{precision}f}"


def get_network_for_token(kind: str) -> str:
    """Get the network for a token
    
    Args:
        kind: The token kind
        
    Returns:
        str: Network name or empty string if not a token
    """
    if '-' in kind:
        parts = kind.split('-')
        if len(parts) == 2:
            return parts[1]  # Return the network part
    elif '_' in kind and kind.startswith('ETH_'):
        return 'ETH'  # Ethereum network for ETH_ tokens
    
    return ""  # Not a token or unknown format


def validate_address(address: str, kind: str) -> bool:
    """Validate a cryptocurrency address format
    
    Args:
        address: The address to validate
        kind: The cryptocurrency kind
        
    Returns:
        bool: True if valid format, False otherwise
    """
    # Basic validation patterns for different cryptocurrencies
    validation_patterns = {
        'BTC': r'^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$',  # Bitcoin addresses
        'ETH': r'^0x[a-fA-F0-9]{40}$',  # Ethereum addresses
        'SOL': r'^[1-9A-HJ-NP-Za-km-z]{32,44}$',  # Solana addresses
        'LTC': r'^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$',  # Litecoin addresses
        'XRP': r'^r[0-9a-zA-Z]{24,34}$',  # XRP addresses
        'DOGE': r'^D{1}[5-9A-HJ-NP-U]{1}[1-9A-HJ-NP-Za-km-z]{32}$',  # Dogecoin addresses
        'TON': r'^[\-_0-9a-zA-Z]{48}$',  # TON addresses
        'TRX': r'^T[0-9a-zA-Z]{33}$',  # TRON addresses
        'BNB': r'^0x[a-fA-F0-9]{40}$',  # BNB (BSC) addresses (same as ETH)
    }
    
    # For tokens, use the base network's validation pattern
    if kind.startswith('ETH_') or kind.endswith('-ETH') or kind.endswith('-ARBITRUM') or kind.endswith('-BASE'):
        kind = 'ETH'  # Use Ethereum validation for all ERC-20 tokens
    elif kind.endswith('-POLYGON') or kind.startswith('POL'):
        kind = 'ETH'  # Polygon uses Ethereum address format
    elif kind.endswith('-BSC') or kind.startswith('BNB'):
        kind = 'BNB'  # BSC tokens
    elif kind.endswith('-SOL'):
        kind = 'SOL'  # Solana tokens
    elif kind.endswith('-TRX'):
        kind = 'TRX'  # TRON tokens
    elif kind.endswith('-TON'):
        kind = 'TON'  # TON tokens
    
    # Get the validation pattern for the cryptocurrency
    pattern = validation_patterns.get(kind)
    if not pattern:
        return True  # If no pattern is defined, assume valid
    
    # Validate the address against the pattern
    return bool(re.match(pattern, address))


def parse_uniwire_error(error_data: dict) -> dict:
    """Parse Uniwire API error response
    
    Args:
        error_data: Error data from API response
        
    Returns:
        dict: Parsed error information with message, code, and user-friendly message
    """
    error_message = error_data.get('error', 'Unknown error')
    error_code = error_data.get('error_code')
    
    # Map error codes to user-friendly messages
    user_messages = {
        'INVALID_ADDRESS': 'The cryptocurrency address provided is not valid.',
        'INSUFFICIENT_FUNDS': 'There are not enough funds to complete this transaction.',
        'INVALID_AMOUNT': 'The amount specified is not valid for this transaction.',
        'RATE_LIMIT_EXCEEDED': 'Too many requests. Please try again later.',
        'UNAUTHORIZED': 'Authentication failed. Please check your API credentials.',
        'INVALID_PROFILE': 'The specified profile does not exist or is not accessible.',
        'INVALID_KIND': 'The cryptocurrency type is not supported or invalid.',
    }
    
    # Get user-friendly message or use a generic one
    user_message = user_messages.get(error_code, 'An error occurred while processing your request.')
    
    return {
        'message': error_message,
        'code': error_code,
        'user_message': user_message
    }