# App Key Generation Module (Whitelabel Integration) - API Documentation

## Overview

The App Key Generation Module provides a comprehensive solution for managing API keys for whitelabel partners. This module enables secure API key generation, management, and monitoring for third-party integrations.

## Features

- ✅ **Whitelabel Partner Management**: Complete partner lifecycle management
- ✅ **Multi-Type API Keys**: Production, Sandbox, and Development environments
- ✅ **Security Features**: IP restrictions, scopes, expiration dates
- ✅ **Usage Analytics**: Comprehensive logging and statistics
- ✅ **Admin Interface**: Full Django admin integration with bulk actions
- ✅ **Webhook Management**: Secure webhook secret generation
- ✅ **Rate Limiting**: Configurable API quotas and limits

## Models

### WhitelabelPartner
Represents a whitelabel partner that can have multiple API keys.

**Key Fields:**
- `name`: Partner company name
- `code`: Unique partner identifier (alphanumeric)
- `contact_email`: Primary contact email
- `allowed_domains`: Comma-separated list of allowed domains for CORS
- `webhook_url`: URL for webhook notifications
- `daily_api_limit`: Daily API request limit
- `monthly_api_limit`: Monthly API request limit
- `is_active`: Whether the partner is active
- `is_verified`: Whether the partner is verified

### AppKey
Represents an API key for a whitelabel partner.

**Key Fields:**
- `partner`: Foreign key to WhitelabelPartner
- `name`: Descriptive name for the API key
- `key_type`: Type (production, sandbox, development)
- `public_key`: Public portion of the API key
- `secret_key`: Hashed secret key
- `scopes`: Comma-separated list of API scopes
- `allowed_ips`: Comma-separated list of allowed IP addresses
- `status`: Key status (active, inactive, suspended, revoked)
- `expires_at`: Optional expiration date

### AppKeyUsageLog
Tracks API key usage for analytics and monitoring.

**Key Fields:**
- `app_key`: Foreign key to AppKey
- `endpoint`: API endpoint accessed
- `method`: HTTP method
- `ip_address`: Client IP address
- `status_code`: HTTP response status
- `response_time_ms`: Response time in milliseconds

## API Endpoints

### Base URL
All endpoints are prefixed with `/api/auth/`

### Authentication
All admin endpoints require authentication with admin privileges.

### 1. Whitelabel Partner Endpoints

#### List/Create Partners
```
GET /api/auth/partners/
POST /api/auth/partners/
```

**Query Parameters (GET):**
- `is_active`: Filter by active status (true/false)
- `is_verified`: Filter by verification status (true/false)
- `search`: Search by name, code, or email

**Example Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Test Partner Inc",
      "code": "test_partner",
      "contact_email": "contact@testpartner.com",
      "allowed_domains": "testpartner.com,api.testpartner.com",
      "webhook_url": "https://testpartner.com/webhooks",
      "daily_api_limit": 5000,
      "monthly_api_limit": 150000,
      "is_active": true,
      "is_verified": false,
      "app_keys_count": 3,
      "created_at": "2025-07-04T05:00:00Z"
    }
  ],
  "count": 1
}
```

#### Partner Details
```
GET /api/auth/partners/{partner_id}/
PUT /api/auth/partners/{partner_id}/
PATCH /api/auth/partners/{partner_id}/
DELETE /api/auth/partners/{partner_id}/
```

#### Generate Webhook Secret
```
POST /api/auth/partners/{partner_id}/webhook-secret/
```

**Request Body:**
```json
{
  "confirm": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Webhook secret regenerated successfully",
  "data": {
    "new_webhook_secret": "E5AGInp3NZx8QJ2X...",
    "warning": "This secret will not be shown again. Please store it securely."
  }
}
```

### 2. App Key Endpoints

#### List/Create App Keys
```
GET /api/auth/app-keys/
POST /api/auth/app-keys/
```

**Query Parameters (GET):**
- `partner`: Filter by partner ID
- `key_type`: Filter by key type (production, sandbox, development)
- `status`: Filter by status (active, inactive, suspended, revoked)

**Create Request Body:**
```json
{
  "partner": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Production API Key",
  "key_type": "production",
  "scopes": "read,write",
  "allowed_ips": "192.168.1.100,10.0.0.1",
  "daily_request_limit": 1000,
  "expires_at": "2026-07-04T00:00:00Z"
}
```

**Create Response:**
```json
{
  "success": true,
  "message": "API key created successfully",
  "data": {
    "id": "456e7890-e89b-12d3-a456-426614174001",
    "public_key": "pk_test_partner_sfX_acAc98w8Bz-9",
    "raw_secret": "raw_secret_value_here",
    "partner": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Production API Key",
    "key_type": "production",
    "scopes": "read,write",
    "status": "active"
  },
  "warning": "The secret key will not be shown again. Please store it securely."
}
```

#### App Key Details
```
GET /api/auth/app-keys/{key_id}/
PUT /api/auth/app-keys/{key_id}/
PATCH /api/auth/app-keys/{key_id}/
DELETE /api/auth/app-keys/{key_id}/
```

#### Regenerate App Key Secret
```
POST /api/auth/app-keys/{key_id}/regenerate/
```

**Request Body:**
```json
{
  "confirm": true
}
```

#### App Key Usage Statistics
```
GET /api/auth/app-keys/{key_id}/stats/?start_date=2025-07-01&end_date=2025-07-04
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_requests": 1250,
    "successful_requests": 1200,
    "error_requests": 50,
    "success_rate": 96.0,
    "avg_response_time_ms": 125.5,
    "start_date": "2025-07-01",
    "end_date": "2025-07-04"
  }
}
```

#### App Key Usage Logs
```
GET /api/auth/app-keys/{key_id}/logs/?limit=100&offset=0
```

**Query Parameters:**
- `limit`: Number of logs to return (default: 100)
- `offset`: Number of logs to skip
- `method`: Filter by HTTP method
- `status_code`: Filter by status code

### 3. Utility Endpoints

#### Get Partner's App Keys
```
GET /api/auth/partners/{partner_id}/app-keys/
```

#### Verify API Key (Public Endpoint)
```
POST /api/auth/verify-api-key/
```

**Request Body:**
```json
{
  "public_key": "pk_test_partner_sfX_acAc98w8Bz-9",
  "secret_key": "your_secret_key_here"
}
```

**Response:**
```json
{
  "success": true,
  "message": "API key is valid",
  "data": {
    "key_id": "456e7890-e89b-12d3-a456-426614174001",
    "partner_name": "Test Partner Inc",
    "key_type": "production",
    "scopes": ["read", "write"],
    "expires_at": "2026-07-04T00:00:00Z"
  }
}
```

## Django Admin Interface

### WhitelabelPartner Admin
- **List View**: Name, code, email, status, verification, app keys count
- **Filters**: Active status, verification status, creation date
- **Search**: Name, code, email, registration number
- **Bulk Actions**: Verify partners, activate/deactivate, generate webhook secrets
- **Inline**: App keys management

### AppKey Admin
- **List View**: Partner, name, type, public key, status, scopes, usage
- **Filters**: Key type, status, creation date, expiration
- **Search**: Partner name, key name, public key
- **Bulk Actions**: Revoke, suspend, activate, extend expiry
- **Security**: Masked secret display

### AppKeyUsageLog Admin
- **List View**: Partner, key, method, endpoint, status, response time
- **Filters**: Method, status code, creation date, partner, key type
- **Search**: Key name, partner, endpoint, IP address
- **Read-Only**: All fields (logs are immutable)

## Security Features

### 1. API Key Security
- **Hashed Storage**: Secret keys are stored as SHA-256 hashes
- **Masked Display**: Secrets are never displayed in full in admin
- **Expiration**: Optional expiration dates for keys
- **Revocation**: Immediate key revocation capability

### 2. Access Control
- **IP Restrictions**: Restrict API access to specific IP addresses
- **Scopes**: Granular permission control (read, write, admin)
- **Domain Restrictions**: CORS protection with allowed domains
- **Rate Limiting**: Daily and monthly API quotas

### 3. Monitoring
- **Usage Logging**: Comprehensive request/response logging
- **Analytics**: Usage statistics and success rates
- **Audit Trail**: Track key creation, modification, and revocation

## Implementation Examples

### 1. Creating a Whitelabel Partner
```python
from authentication.models import WhitelabelPartner

partner = WhitelabelPartner.objects.create(
    name="Acme Corp",
    code="acme_corp",
    contact_email="dev@acme.com",
    allowed_domains="acme.com,api.acme.com",
    webhook_url="https://api.acme.com/webhooks",
    daily_api_limit=10000,
    monthly_api_limit=300000
)
```

### 2. Creating an API Key
```python
from authentication.models import AppKey, AppKeyType

api_key = AppKey.objects.create(
    partner=partner,
    name="Production Key",
    key_type=AppKeyType.PRODUCTION,
    scopes="read,write",
    daily_request_limit=5000
)

# Access the generated keys
public_key = api_key.public_key
raw_secret = api_key._raw_secret  # Only available during creation
```

### 3. Verifying an API Key
```python
from authentication.models import AppKey

try:
    app_key = AppKey.objects.get(public_key=public_key)
    if app_key.verify_secret(provided_secret) and app_key.is_active():
        # Key is valid
        app_key.record_usage()
    else:
        # Invalid or inactive key
        pass
except AppKey.DoesNotExist:
    # Key not found
    pass
```

### 4. Logging API Usage
```python
from authentication.models import AppKeyUsageLog

AppKeyUsageLog.objects.create(
    app_key=api_key,
    endpoint="/api/v1/users",
    method="GET",
    ip_address="192.168.1.100",
    status_code=200,
    response_time_ms=150,
    request_size_bytes=1024,
    response_size_bytes=2048
)
```

## Rate Limiting Implementation

The module provides quota management but doesn't implement rate limiting middleware. Here's a sample implementation:

```python
from django.http import JsonResponse
from authentication.models import AppKey, AppKeyUsageLog
from django.utils import timezone
from datetime import timedelta

def api_key_middleware(get_response):
    def middleware(request):
        if request.path.startswith('/api/'):
            # Extract API key from headers
            public_key = request.META.get('HTTP_X_API_KEY')
            secret_key = request.META.get('HTTP_X_API_SECRET')
            
            if not public_key or not secret_key:
                return JsonResponse({'error': 'API key required'}, status=401)
            
            try:
                app_key = AppKey.objects.get(public_key=public_key)
                
                # Verify key
                if not app_key.verify_secret(secret_key) or not app_key.is_active():
                    return JsonResponse({'error': 'Invalid API key'}, status=401)
                
                # Check daily quota
                today = timezone.now().date()
                daily_usage = AppKeyUsageLog.objects.filter(
                    app_key=app_key,
                    created_at__date=today
                ).count()
                
                if daily_usage >= app_key.get_daily_request_limit():
                    return JsonResponse({'error': 'Daily quota exceeded'}, status=429)
                
                # Add key to request
                request.app_key = app_key
                
            except AppKey.DoesNotExist:
                return JsonResponse({'error': 'Invalid API key'}, status=401)
        
        response = get_response(request)
        
        # Log usage
        if hasattr(request, 'app_key'):
            AppKeyUsageLog.objects.create(
                app_key=request.app_key,
                endpoint=request.path,
                method=request.method,
                ip_address=request.META.get('REMOTE_ADDR'),
                status_code=response.status_code
            )
            request.app_key.record_usage()
        
        return response
    
    return middleware
```

## Best Practices

1. **Key Management**:
   - Use different key types for different environments
   - Regularly rotate production keys
   - Set appropriate expiration dates
   - Monitor key usage patterns

2. **Security**:
   - Always use HTTPS for API key transmission
   - Implement proper IP whitelisting
   - Use minimal required scopes
   - Store secrets securely on client side

3. **Monitoring**:
   - Set up alerts for unusual usage patterns
   - Monitor error rates and response times
   - Track quota utilization
   - Regular security audits

4. **Documentation**:
   - Provide clear integration guides for partners
   - Document all available scopes and endpoints
   - Include rate limiting information
   - Provide SDK examples

## Deployment Considerations

1. **Database**:
   - Add indexes for frequently queried fields
   - Consider partitioning usage logs by date
   - Implement log retention policies

2. **Performance**:
   - Cache frequently accessed keys
   - Use connection pooling for database
   - Implement proper pagination for large datasets

3. **Security**:
   - Use environment variables for sensitive settings
   - Implement proper backup and recovery
   - Regular security updates and patches

## Conclusion

The App Key Generation Module provides a production-ready solution for managing API keys for whitelabel partners. It includes comprehensive security features, usage monitoring, and a full admin interface for easy management.

For support and questions, please refer to the Django admin interface or contact the development team.
