# Uniwire Integration Module

This module provides integration with the Uniwire API for cryptocurrency payment processing in the PexiLabs Redemption platform.

## Overview

The Uniwire integration allows merchants to accept and process cryptocurrency payments through the Uniwire service. It supports various cryptocurrencies and tokens across multiple blockchain networks.

## Features

- Authentication with Uniwire API using HMAC-SHA256
- Support for multiple cryptocurrencies and tokens
- Helper functions for API requests
- Utility functions for cryptocurrency address validation and amount formatting
- Service layer for integration with the PexiLabs platform

## Module Structure

- `__init__.py` - Core functionality and module exports
- `service.py` - Service layer for integration with the PexiLabs platform
- `constants.py` - Constants including supported cryptocurrencies and tokens
- `utils.py` - Utility functions for working with the Uniwire API
- `examples.py` - Example usage of the Uniwire integration

## Usage

### Basic Usage

```python
from integrations.uniwire import UniwireClient, UniwireAPIException

# Initialize client with API credentials
client = UniwireClient(
    api_key='your_api_key',
    api_secret='your_api_secret'
)

try:
    # Get profiles
    profiles = client.get_profiles()
    print(profiles)
except UniwireAPIException as e:
    print(f"Error: {e.message}")
```

### Using the Service Layer

```python
from integrations.uniwire import UniwireService

# Initialize service (optionally with a merchant)
service = UniwireService(merchant=merchant)

# Get profiles
profiles = service.get_profiles()
```

### Checking Supported Cryptocurrencies

```python
from integrations.uniwire import is_supported_cryptocurrency, COIN_BTC, TOKEN_ETH_USDT

# Check if Bitcoin is supported
print(is_supported_cryptocurrency(COIN_BTC))  # True

# Check if Tether on Ethereum is supported
print(is_supported_cryptocurrency(TOKEN_ETH_USDT))  # True
```

## Configuration

The following settings can be configured in your Django settings:

```python
# Uniwire API Configuration
UNIWIRE_SANDBOX_MODE = True  # Set to False for production
UNIWIRE_API_URL = 'https://api.uniwire.com'  # Default API URL

# Sandbox credentials
UNIWIRE_SANDBOX_API_KEY = 'your_sandbox_api_key'
UNIWIRE_SANDBOX_API_SECRET = 'your_sandbox_api_secret'

# Production credentials
UNIWIRE_API_KEY = 'your_production_api_key'
UNIWIRE_API_SECRET = 'your_production_api_secret'
```

## API Documentation

For more information about the Uniwire API, refer to the official Uniwire API documentation.