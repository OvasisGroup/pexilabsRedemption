# TransVoucher Integration Guide

This document explains how to configure and use the TransVoucher payment integration in the PexiLabs system.

## Overview

The TransVoucher integration provides a comprehensive payment solution with support for:

- **Payment Creation**: Create payment intents with customer details and metadata
- **Payment Status Tracking**: Real-time payment status monitoring
- **Webhook Support**: Automatic payment status updates via webhooks
- **API Key Authentication**: Secure authentication using merchant API keys
- **Checkout Sessions**: Simplified payment flow for customers
- **Payment Listing**: Retrieve and filter payment history

## Features

- ✅ **API Key Authentication**: Secure authentication using TransVoucher API keys
- ✅ **Payment Creation**: Create payment intents with comprehensive customer data
- ✅ **Status Tracking**: Real-time payment status monitoring
- ✅ **Webhook Integration**: Automatic payment notifications
- ✅ **Checkout Sessions**: Simplified payment URLs for customers
- ✅ **Payment History**: List and filter payment transactions
- ✅ **Connection Testing**: Verify integration connectivity
- ✅ **Sandbox Support**: Test payments in sandbox environment

## Configuration

### 1. Environment Setup

Add the following configuration to your `.env` file:

```bash
# TransVoucher Configuration
TRANSVOUCHER_API_KEY=tv-your-api-key-here
TRANSVOUCHER_API_SECRET=your-api-secret-here
TRANSVOUCHER_API_BASE_URL=https://api.transvoucher.com
TRANSVOUCHER_SANDBOX_MODE=true
```

### 2. Global Integration Setup

Run the management command to set up the global TransVoucher integration:

```bash
python manage.py setup_transvoucher
```

This command will:
- Validate environment configuration
- Create the global TransVoucher integration record
- Set up default configuration
- Test the API connection

### 3. Merchant Integration Setup

Merchants can enable TransVoucher integration through:

#### Option A: API Endpoint

```bash
curl -X POST "http://your-domain/integrations/configure/{integration_id}/" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "configuration": {
      "webhook_url": "https://your-domain/webhooks/transvoucher/",
      "return_url": "https://your-domain/payment/success/",
      "failure_url": "https://your-domain/payment/failed/"
    },
    "credentials": {
      "api_secret": "your-transvoucher-api-secret"
    }
  }'
```

#### Option B: Management Command

```bash
python manage.py setup_transvoucher --merchant-id="merchant-uuid" --api-secret="your-api-secret"
```

## API Endpoints

### Authentication

All API requests require authentication using your merchant API key:

```bash
Authorization: Bearer pk_partner_xxx:sk_live_yyy
```

### 1. Create Payment

**Endpoint**: `POST /integrations/transvoucher/payment/`

**Request Body**:
```json
{
  "amount": 100.00,
  "currency": "USD",
  "title": "Product Purchase",
  "description": "Payment for product XYZ",
  "customer_email": "customer@example.com",
  "customer_name": "John Doe",
  "customer_phone": "+1234567890",
  "reference_id": "ORDER-123",
  "metadata": {
    "order_id": "ORDER-123",
    "product_id": "PROD-456",
    "user_id": "user_789"
  },
  "customer_commission_percentage": 5,
  "multiple_use": false
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "transaction_id": 123,
    "reference_id": "txn_abc123...",
    "payment_url": "https://transvoucher.com/pay/...",
    "expires_at": "2024-01-01T12:00:00Z",
    "amount": 100.00,
    "currency": "USD",
    "status": "pending"
  }
}
```

### 2. Get Payment Status

**Endpoint**: `GET /integrations/transvoucher/payment-status/{reference_id}/`

**Response**:
```json
{
  "success": true,
  "data": {
    "transaction_id": 123,
    "reference_id": "txn_abc123...",
    "amount": 100.00,
    "currency": "USD",
    "status": "completed",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:05:00Z",
    "paid_at": "2024-01-01T10:05:00Z"
  }
}
```

### 3. List Payments

**Endpoint**: `GET /integrations/transvoucher/payments/`

**Query Parameters**:
- `limit`: Number of results (1-100, default: 10)
- `page_token`: Token for pagination
- `status`: Filter by status (pending, completed, failed, expired)
- `from_date`: Filter from date (YYYY-MM-DD)
- `to_date`: Filter to date (YYYY-MM-DD)

### 4. Create Checkout Session

**Endpoint**: `POST /integrations/transvoucher/checkout-session/`

**Request Body**:
```json
{
  "amount": 50.00,
  "currency": "USD",
  "title": "Quick Checkout",
  "description": "Simple payment checkout",
  "customer_email": "customer@example.com",
  "customer_name": "Jane Doe",
  "metadata": {
    "session_id": "sess_abc123"
  }
}
```

### 5. Test Connection

**Endpoint**: `GET /integrations/transvoucher/test-connection/`

### 6. Get Integration Info

**Endpoint**: `GET /integrations/transvoucher/integration-info/`

## Webhook Events

TransVoucher sends webhook events to notify your application of payment status changes:

### Supported Events

- `payment_intent.created`: Payment intent created
- `payment_intent.succeeded`: Payment completed successfully
- `payment_intent.failed`: Payment failed or declined
- `payment_intent.cancelled`: Payment cancelled by user
- `payment_intent.expired`: Payment intent expired

### Webhook Endpoint

**URL**: `POST /integrations/transvoucher/webhook/`

**Headers**:
- `X-TransVoucher-Signature`: Webhook signature for verification

**Payload Example**:
```json
{
  "event_type": "payment_intent.succeeded",
  "data": {
    "transaction_id": 123,
    "reference_id": "txn_abc123...",
    "amount": 100.00,
    "currency": "USD",
    "status": "completed",
    "customer_details": {
      "full_name": "John Doe",
      "email": "customer@example.com"
    },
    "metadata": {
      "order_id": "ORDER-123"
    }
  },
  "created_at": "2024-01-01T10:05:00Z"
}
```

## Usage Examples

### Python Example

See `integrations/transvoucher_api_example.py` for a complete Python client example.

```python
from integrations.transvoucher_api_example import TransVoucherAPIClient

# Initialize client
client = TransVoucherAPIClient("pk_partner_xxx:sk_live_yyy")

# Create payment
payment_result = client.create_payment({
    'amount': 100.00,
    'currency': 'USD',
    'title': 'Test Payment',
    'customer_email': 'customer@example.com'
})

# Check status
if payment_result.get('success'):
    reference_id = payment_result['data']['reference_id']
    status = client.get_payment_status(reference_id)
    print(f"Payment status: {status}")
```

### JavaScript Example

```javascript
// Using the TransVoucher JavaScript SDK
const transvoucher = new TransVoucher({
  apiKey: 'your-api-key',
  environment: 'sandbox' // or 'production'
});

// Create payment
const payment = await transvoucher.payments.create({
  amount: 100.00,
  currency: 'USD',
  title: 'Product Purchase',
  customer_details: {
    full_name: 'John Doe',
    email: 'customer@example.com'
  },
  metadata: {
    order_id: 'ORDER-123'
  }
});

// Redirect to payment page
window.location.href = payment.payment_url;
```

### cURL Example

```bash
# Create payment
curl -X POST "http://localhost:8001/integrations/transvoucher/payment/" \
  -H "Authorization: Bearer pk_partner_xxx:sk_live_yyy" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100.00,
    "currency": "USD",
    "title": "Test Payment",
    "customer_email": "customer@example.com"
  }'

# Check payment status
curl -X GET "http://localhost:8001/integrations/transvoucher/payment-status/txn_abc123/" \
  -H "Authorization: Bearer pk_partner_xxx:sk_live_yyy"
```

## Error Handling

### Common Error Responses

```json
{
  "error": "Invalid API key format",
  "error_code": "INVALID_API_KEY",
  "status_code": 401
}
```

```json
{
  "error": "Payment not found",
  "error_code": "PAYMENT_NOT_FOUND",
  "status_code": 404
}
```

### Error Codes

- `INVALID_API_KEY`: API key is invalid or malformed
- `INSUFFICIENT_FUNDS`: Insufficient funds for payment
- `PAYMENT_NOT_FOUND`: Payment reference not found
- `INVALID_AMOUNT`: Payment amount is invalid
- `CURRENCY_NOT_SUPPORTED`: Currency not supported
- `RATE_LIMIT_EXCEEDED`: API rate limit exceeded

## Testing

### 1. Run Integration Tests

```bash
# Test the integration setup
python manage.py test integrations.tests.test_transvoucher

# Run the example client
python integrations/transvoucher_api_example.py
```

### 2. Test in Dashboard

1. Login to your merchant dashboard
2. Navigate to "Integration Testing" section
3. Find TransVoucher integration
4. Click "Test Integration" button
5. Review test results

### 3. Sandbox Testing

Use sandbox mode for testing:

```bash
TRANSVOUCHER_SANDBOX_MODE=true
```

Sandbox payments will not charge real money and can be used for testing payment flows.

## Security Best Practices

1. **API Key Security**: Never expose API keys in client-side code
2. **HTTPS Only**: Always use HTTPS in production
3. **Webhook Verification**: Verify webhook signatures
4. **IP Restrictions**: Configure IP restrictions for API keys
5. **Rate Limiting**: Implement appropriate rate limiting
6. **Credential Rotation**: Regularly rotate API credentials

## Troubleshooting

### Common Issues

1. **Invalid API Key**
   - Ensure API key format is correct: `tv-xxx`
   - Verify API secret is provided
   - Check environment variables are loaded

2. **Connection Timeout**
   - Verify base URL is correct
   - Check network connectivity
   - Ensure firewall allows outbound HTTPS

3. **Webhook Not Received**
   - Verify webhook URL is accessible
   - Check webhook signature verification
   - Review webhook logs in admin panel

4. **Payment Creation Failed**
   - Validate required fields (amount, title)
   - Check currency is supported
   - Verify merchant integration is enabled

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('integrations.transvoucher').setLevel(logging.DEBUG)
```

### Support

For technical support:

1. Check Django logs for error details
2. Verify integration configuration
3. Test API connectivity
4. Review webhook delivery logs
5. Contact development team with specific error messages

## Files Structure

```
integrations/
├── transvoucher/
│   ├── __init__.py
│   ├── service.py              # Core TransVoucher service
│   └── usage.py                # Simplified usage interface
├── views/
│   └── transvoucher.py         # API endpoints
├── management/commands/
│   └── setup_transvoucher.py   # Setup command
├── transvoucher_api_example.py # Example client
└── TRANSVOUCHER_INTEGRATION_README.md # This documentation
```

## API Documentation

For complete API documentation, visit: [TransVoucher API Docs](https://transvoucher.com/api-documentation)

## Changelog

### v1.0.0 (Initial Release)
- ✅ Basic payment creation and status tracking
- ✅ Webhook support for payment events
- ✅ API key authentication
- ✅ Checkout session management
- ✅ Payment listing and filtering
- ✅ Connection testing and health monitoring
- ✅ Sandbox mode support
- ✅ Comprehensive error handling
- ✅ Management command for setup
- ✅ Example client implementation

---

**Note**: This integration is production-ready and follows PexiLabs integration standards. For questions or feature requests, please contact the development team.