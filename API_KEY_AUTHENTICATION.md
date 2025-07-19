# Merchant Authentication via API Key

## Overview

This document describes the implementation of API key authentication for merchants in the PexiLabs integrations platform. This allows external applications and services to authenticate and access the integrations API using API keys instead of traditional user credentials.

## Architecture

### Components

1. **WhitelabelPartner Model**: Represents API key partners/clients
2. **AppKey Model**: Stores API key credentials and configuration
3. **APIKeyAuthentication**: DRF authentication class for API key validation
4. **APIKeyPermission**: Permission class for scope-based access control
5. **APIKeyBackend**: Django authentication backend for API keys

### Key Features

- **Secure Key Storage**: Secret keys are hashed using SHA-256
- **Scope-based Permissions**: API keys can have read, write, or admin scopes
- **IP Restrictions**: Optional IP address whitelisting
- **Rate Limiting**: Per-key and per-partner request limits
- **Usage Tracking**: Comprehensive logging of API calls
- **Expiration Support**: Optional key expiration dates
- **Partner Management**: Multi-tenant support via whitelabel partners

## API Key Format

API keys consist of two parts separated by a colon:
```
public_key:secret_key
```

Example:
```
pk_demo_FLzHA7kOwUIFMKCB:phl0ZUfZ_LgJZ95zjWNILf34OIUdIBOMkdHL4bM2_EE
```

### Key Components

- **Public Key**: Visible identifier in format `{prefix}{partner_code}_{random}`
- **Secret Key**: Private key for authentication (32 characters, URL-safe base64)

## Authentication Methods

### 1. Authorization Header (Preferred)

```http
Authorization: Bearer pk_demo_FLzHA7kOwUIFMKCB:phl0ZUfZ_LgJZ95zjWNILf34OIUdIBOMkdHL4bM2_EE
```

### 2. Custom Header

```http
X-API-Key: pk_demo_FLzHA7kOwUIFMKCB:phl0ZUfZ_LgJZ95zjWNILf34OIUdIBOMkdHL4bM2_EE
```

## Supported Endpoints

All integrations API endpoints now support API key authentication:

### Integration Management
- `GET /api/integrations/` - List available integrations
- `GET /api/integrations/{id}/` - Get integration details
- `GET /api/integrations/bank/{id}/` - Get bank integration details

### UBA Banking Operations
- `POST /api/integrations/uba/payment-page/` - Create payment page
- `GET /api/integrations/uba/payment-status/{id}/` - Get payment status
- `POST /api/integrations/uba/account-inquiry/` - Account inquiry
- `POST /api/integrations/uba/fund-transfer/` - Fund transfer
- `POST /api/integrations/uba/balance-inquiry/` - Balance inquiry
- `POST /api/integrations/uba/transaction-history/` - Transaction history
- `POST /api/integrations/uba/bill-payment/` - Bill payment
- `GET /api/integrations/uba/test-connection/` - Test connection

### Monitoring & Analytics
- `GET /api/integrations/stats/` - Integration statistics
- `GET /api/integrations/health/` - Health checks
- `GET /api/integrations/api-calls/` - API call logs

## API Key Management

### Creating API Keys

Use the management command to create API keys:

```bash
python manage.py create_api_key \\
  --partner-name "Your Company" \\
  --partner-code "your_company" \\
  --key-name "Production API Key" \\
  --key-type "production" \\
  --scopes "read,write"
```

### Key Types

- **sandbox**: For testing and development
- **production**: For live/production use
- **development**: For internal development

### Scopes

- **read**: GET operations (view data)
- **write**: POST, PUT, PATCH operations (modify data)
- **admin**: DELETE operations and admin functions

## Security Features

### 1. Hashed Storage
Secret keys are hashed using SHA-256 before storage, making them irreversible.

### 2. IP Restrictions
Configure allowed IP addresses per API key:
```python
app_key.allowed_ips = "192.168.1.1,10.0.0.0/24"
```

### 3. Rate Limiting
- Daily request limits per key
- Monthly request limits per partner
- Concurrent connection limits

### 4. Audit Logging
All API calls are logged with:
- Endpoint accessed
- HTTP method
- IP address
- User agent
- Response status
- Response time
- Request/response sizes

### 5. Key Lifecycle Management
- Activation/deactivation
- Suspension for violations
- Expiration dates
- Revocation with audit trail

## Usage Examples

### Python with Requests

```python
import requests

# Using Authorization header
headers = {
    'Authorization': 'Bearer pk_demo_FLzHA7kOwUIFMKCB:phl0ZUfZ_LgJZ95zjWNILf34OIUdIBOMkdHL4bM2_EE',
    'Content-Type': 'application/json'
}

response = requests.get(
    'http://localhost:8000/api/integrations/',
    headers=headers
)

print(response.json())
```

### cURL

```bash
# List integrations
curl -H "Authorization: Bearer pk_demo_FLzHA7kOwUIFMKCB:phl0ZUfZ_LgJZ95zjWNILf34OIUdIBOMkdHL4bM2_EE" \\
     http://localhost:8000/api/integrations/

# Create UBA payment page
curl -X POST \\
     -H "X-API-Key: pk_demo_FLzHA7kOwUIFMKCB:phl0ZUfZ_LgJZ95zjWNILf34OIUdIBOMkdHL4bM2_EE" \\
     -H "Content-Type: application/json" \\
     -d '{"amount": 1000, "currency": "KES", "description": "Test payment"}' \\
     http://localhost:8000/api/integrations/uba/payment-page/
```

### JavaScript (Fetch)

```javascript
const apiKey = 'pk_demo_FLzHA7kOwUIFMKCB:phl0ZUfZ_LgJZ95zjWNILf34OIUdIBOMkdHL4bM2_EE';

// Get integrations
fetch('http://localhost:8000/api/integrations/', {
    headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
    }
})
.then(response => response.json())
.then(data => console.log(data));
```

## Testing

### Running the Test Script

```bash
python test_api_key_auth.py http://localhost:8000 pk_demo_FLzHA7kOwUIFMKCB:phl0ZUfZ_LgJZ95zjWNILf34OIUdIBOMkdHL4bM2_EE
```

### Expected Response

```
🧪 Testing API Key Authentication
==================================================

📡 Testing: Integration List
   Method: GET
   URL: http://localhost:8000/api/integrations/
   Status: 200
   ✅ Success!
   📄 Response: 1 items

📡 Testing: Integration Stats
   Method: GET
   URL: http://localhost:8000/api/integrations/stats/
   Status: 200
   ✅ Success!

📡 Testing: UBA Test Connection
   Method: GET
   URL: http://localhost:8000/api/integrations/uba/test-connection/
   Status: 200
   ✅ Success!

==================================================
📊 Test Summary
==================================================
   ✅ Integration List: 200
   ✅ Integration Stats: 200
   ✅ UBA Test Connection: 200

🎯 Success Rate: 3/3 (100.0%)
🎉 All tests passed! API key authentication is working correctly.
```

## Error Handling

### Common Error Responses

#### 401 Unauthorized - Invalid API Key
```json
{
    "detail": "Invalid API key."
}
```

#### 401 Unauthorized - Missing API Key
```json
{
    "detail": "Authentication credentials were not provided."
}
```

#### 403 Forbidden - Insufficient Scope
```json
{
    "detail": "You do not have permission to perform this action."
}
```

#### 401 Unauthorized - Expired Key
```json
{
    "detail": "API key is inactive or expired."
}
```

#### 401 Unauthorized - IP Restriction
```json
{
    "detail": "API key not allowed from this IP address."
}
```

## Database Schema

### WhitelabelPartner Table
- `id`: UUID primary key
- `name`: Partner company name
- `code`: Unique partner identifier
- `contact_email`: Primary contact
- `is_active`: Partner status
- `daily_api_limit`: Request limit per day
- `monthly_api_limit`: Request limit per month

### AppKey Table
- `id`: UUID primary key
- `partner_id`: Foreign key to WhitelabelPartner
- `name`: Descriptive key name
- `public_key`: Public portion (visible)
- `secret_key`: Hashed secret key
- `key_type`: sandbox/production/development
- `scopes`: Comma-separated permissions
- `status`: active/inactive/suspended/revoked
- `expires_at`: Optional expiration date

### AppKeyUsageLog Table
- `id`: UUID primary key
- `app_key_id`: Foreign key to AppKey
- `endpoint`: API endpoint accessed
- `method`: HTTP method
- `ip_address`: Client IP
- `status_code`: Response status
- `response_time_ms`: Response time
- `created_at`: Timestamp

## Configuration

### Django Settings

Add to your `AUTHENTICATION_BACKENDS`:

```python
AUTHENTICATION_BACKENDS = [
    'authentication.backends.APIKeyBackend',
    'authentication.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]
```

### DRF Settings

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'authentication.api_auth.APIKeyOrTokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'authentication.api_auth.APIKeyPermission',
    ],
}
```

## Best Practices

### 1. Key Security
- Never expose secret keys in client-side code
- Use environment variables for key storage
- Rotate keys regularly
- Monitor usage patterns for anomalies

### 2. Access Control
- Use minimal required scopes
- Implement IP restrictions for sensitive operations
- Set appropriate expiration dates
- Monitor and audit key usage

### 3. Error Handling
- Implement retry logic with exponential backoff
- Log authentication failures
- Handle rate limiting gracefully
- Provide clear error messages

### 4. Performance
- Cache authentication results when appropriate
- Use connection pooling for high-volume applications
- Monitor response times and optimize accordingly

## Troubleshooting

### Common Issues

1. **"Invalid API key format"**
   - Ensure key includes both public and secret parts with colon separator
   - Check for extra spaces or characters

2. **"API key is inactive or expired"**
   - Verify key status in admin panel
   - Check expiration date
   - Ensure partner account is active

3. **"IP not allowed"**
   - Check IP restrictions configuration
   - Verify client IP address
   - Consider proxy/load balancer IP forwarding

4. **Rate limiting errors**
   - Check daily/monthly limits
   - Implement backoff and retry logic
   - Consider upgrading limits if needed

### Debugging

Enable debug logging:

```python
LOGGING = {
    'loggers': {
        'authentication.api_auth': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
        'authentication.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

## Migration Guide

### From JWT to API Keys

1. Create API keys for existing clients
2. Update client applications to use API key authentication
3. Test thoroughly in sandbox environment
4. Gradually migrate production traffic
5. Deprecate old JWT tokens after migration period

### Backward Compatibility

The implementation supports both API keys and JWT tokens simultaneously, allowing for gradual migration without breaking existing integrations.

## Support

For issues with API key authentication:

1. Check the troubleshooting section
2. Review audit logs in the admin panel
3. Enable debug logging for detailed error information
4. Contact the development team with specific error messages and request IDs

## Future Enhancements

- **Rate limiting middleware**: More sophisticated rate limiting
- **Key rotation**: Automatic key rotation capabilities
- **Advanced scoping**: More granular permission controls
- **Webhook signatures**: API key-based webhook verification
- **Analytics dashboard**: Real-time usage analytics and monitoring
