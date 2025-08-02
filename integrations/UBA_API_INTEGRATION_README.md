# UBA Integration with API Key Authentication

This document explains how to use the UBA (United Bank for Africa) Kenya Pay integration with API key authentication for merchants.

## Overview

The UBA integration provides a simplified interface for merchants to create checkout intents and process payments using their API keys. This implementation mirrors the TypeScript checkout service functionality while providing secure API key-based authentication.

## Features

- **API Key Authentication**: Secure authentication using merchant API keys
- **Checkout Intent Creation**: Create payment intents similar to the TypeScript implementation
- **Payment Status Tracking**: Check payment status using payment IDs
- **Integration Information**: Get details about UBA integration availability
- **Checkout Session Management**: Create checkout sessions with URLs

## API Endpoints

### 1. Create Checkout Intent

**Endpoint**: `POST /integrations/uba/api/checkout-intent/`

**Authentication**: Bearer token (API Key)

**Request Body**:

```json
{
  "currency": "KES",
  "amount": 1000.0,
  "reference": "ORDER123456",
  "reference2": "ORDER123452",
  "customer": {
    "billing_address": {
      "first_name": "John",
      "last_name": "Doe",
      "address_line1": "123 Main Street",
      "address_line2": "Apt 4B",
      "address_city": "Nairobi",
      "address_state": "Nairobi",
      "address_country": "KE",
      "address_postcode": "00100"
    },
    "email": "john.doe@example.com",
    "phone": "+254700000000"
  },
  "version": 1
}
```

**Response**:

```json
{
  "status": 200,
  "error": null,
  "resource": {
    "type": "checkout",
    "data": {
      "_id": "payment_id_123",
      "version": 1,
      "status": "active",
      "reason": null,
      "amount": 1000.0,
      "currency": "KES",
      "reference": "ORDER123456",
      "journey": [],
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "token": "checkout_token_or_url"
    }
  }
}
```

### 2. Get Payment Status

**Endpoint**: `GET /integrations/uba/api/payment-status/{payment_id}/`

**Authentication**: Bearer token (API Key)

**Response**:

```json
{
  "success": true,
  "data": {
    "payment_id": "payment_id_123",
    "status": "completed",
    "amount": 1000.0,
    "currency": "KES",
    "reference": "ORDER123456"
  }
}
```

### 3. Get Integration Information

**Endpoint**: `GET /integrations/uba/api/integration-info/`

**Authentication**: Bearer token (API Key)

**Response**:

```json
{
  "success": true,
  "data": {
    "integration_name": "UBA Kenya Pay",
    "provider_name": "United Bank for Africa (Kenya)",
    "is_available": true,
    "is_sandbox": true,
    "supported_currencies": ["KES", "USD"],
    "supported_operations": [
      "create_checkout_intent",
      "get_payment_status",
      "account_inquiry",
      "fund_transfer",
      "balance_inquiry"
    ],
    "merchant_integration": {
      "is_enabled": true,
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z",
      "last_used_at": "2024-01-15T10:30:00Z"
    }
  }
}
```

### 4. Create Checkout Session

**Endpoint**: `POST /integrations/api/checkout/session/`

**Authentication**: Bearer token (API Key)

**Request Body**:

```json
{
  "merchantId": "merchant_123",
  "amount": 1500.0,
  "currency": "KES",
  "successUrl": "https://example.com/success",
  "cancelUrl": "https://example.com/cancel",
  "customer": {
    "billing_address": {
      "first_name": "Jane",
      "last_name": "Smith",
      "address_line1": "456 Oak Avenue",
      "address_city": "Mombasa",
      "address_state": "Mombasa",
      "address_country": "KE",
      "address_postcode": "80100"
    },
    "email": "jane.smith@example.com",
    "phone": "+254711000000"
  },
  "cardNumber": "4111111111111111",
  "expiryDate": "12/25",
  "cvv": "123",
  "first_name": "Jane",
  "last_name": "Smith"
}
```

**Response**:

```json
{
  "sessionId": "session_uuid_123",
  "checkoutUrl": "https://api.example.com/api/payments/checkout/session_uuid_123?first_name=Jane&last_name=Smith&...",
  "ubaResponse": {
    "status": 200,
    "resource": {
      "type": "checkout",
      "data": {
        "_id": "payment_id_456",
        "token": "checkout_token"
      }
    }
  }
}
```

## Authentication

All API endpoints require authentication using API keys in the following format:

```
Authorization: Bearer pk_partner_abc123:sk_live_xyz789
```

Or using the custom header:

```
X-API-Key: pk_partner_abc123:sk_live_xyz789
```

## Usage Examples

### Python Example

See `uba_api_example.py` for a complete Python client implementation.

```python
from integrations.uba_api_example import UBAAPIClient

# Initialize client with your API key
client = UBAAPIClient("pk_partner_abc123:sk_live_xyz789")

# Create checkout intent
checkout_data = {
    "currency": "KES",
    "amount": 1000.00,
    "reference": "ORDER123",
    "customer": {
        "billing_address": {
            "first_name": "John",
            "last_name": "Doe",
            "address_line1": "123 Main St",
            "address_city": "Nairobi",
            "address_state": "Nairobi",
            "address_country": "KE",
            "address_postcode": "00100"
        },
        "email": "john@example.com",
        "phone": "+254700000000"
    }
}

result = client.create_checkout_intent(checkout_data)
print(result)
```

### JavaScript/TypeScript Example

```typescript
import axios from "axios";

const apiKey = "pk_partner_abc123:sk_live_xyz789";
const baseURL = "http://127.0.0.1:8001";

const client = axios.create({
  baseURL,
  headers: {
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
  },
});

// Create checkout intent
const checkoutData = {
  currency: "KES",
  amount: 1000.0,
  reference: "ORDER123",
  customer: {
    billing_address: {
      first_name: "John",
      last_name: "Doe",
      address_line1: "123 Main St",
      address_city: "Nairobi",
      address_state: "Nairobi",
      address_country: "KE",
      address_postcode: "00100",
    },
    email: "john@example.com",
    phone: "+254700000000",
  },
};

try {
  const response = await client.post(
    "/integrations/uba/api/checkout-intent/",
    checkoutData
  );
  console.log("Checkout intent created:", response.data);
} catch (error) {
  console.error("Error:", error.response?.data || error.message);
}
```

### cURL Example

```bash
# Create checkout intent
curl -X POST http://127.0.0.1:8001/integrations/uba/api/checkout-intent/ \
  -H "Authorization: Bearer pk_partner_abc123:sk_live_xyz789" \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "KES",
    "amount": 1000.00,
    "reference": "ORDER123",
    "customer": {
      "billing_address": {
        "first_name": "John",
        "last_name": "Doe",
        "address_line1": "123 Main St",
        "address_city": "Nairobi",
        "address_state": "Nairobi",
        "address_country": "KE",
        "address_postcode": "00100"
      },
      "email": "john@example.com",
      "phone": "+254700000000"
    }
  }'

# Get payment status
curl -X GET http://127.0.0.1:8001/integrations/uba/api/payment-status/payment_id_123/ \
  -H "Authorization: Bearer pk_partner_abc123:sk_live_xyz789"

# Get integration info
curl -X GET http://127.0.0.1:8001/integrations/uba/api/integration-info/ \
  -H "Authorization: Bearer pk_partner_abc123:sk_live_xyz789"
```

## Error Handling

The API returns standard HTTP status codes and JSON error responses:

```json
{
  "success": false,
  "message": "Error description",
  "error_code": "SPECIFIC_ERROR_CODE"
}
```

Common error codes:

- `401 Unauthorized`: Invalid or missing API key
- `403 Forbidden`: Insufficient permissions or inactive API key
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Security Considerations

1. **API Key Security**: Keep your API keys secure and never expose them in client-side code
2. **HTTPS**: Always use HTTPS in production
3. **IP Restrictions**: Configure IP restrictions for your API keys if needed
4. **Rate Limiting**: Be aware of rate limits and implement appropriate retry logic
5. **Webhook Verification**: Verify webhook signatures when processing webhook events

## Testing

To test the integration:

1. Ensure the Django server is running: `python manage.py runserver 127.0.0.1:8001`
2. Create an API key through the admin interface or API
3. Use the provided example scripts or make direct API calls
4. Monitor the logs for any errors or issues

## Support

For issues or questions about the UBA integration:

1. Check the Django logs for error details
2. Verify your API key permissions and status
3. Ensure the UBA integration is properly configured
4. Contact the development team for technical support

## Files Created/Modified

- `integrations/uba_usage.py` - Main UBA usage service
- `integrations/views.py` - Added new API endpoints
- `integrations/urls.py` - Added URL patterns for new endpoints
- `integrations/uba_api_example.py` - Example client implementation
- `integrations/UBA_API_INTEGRATION_README.md` - This documentation
