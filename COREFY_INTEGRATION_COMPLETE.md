# Corefy Payment Orchestration Integration

## Overview

The Corefy integration provides a comprehensive payment orchestration platform that allows merchants to accept payments through multiple payment providers and methods via a single API. This integration supports payment intents, confirmations, refunds, customer management, and webhook notifications.

## Features

- **Payment Intents**: Create and manage payment intents with multiple payment methods
- **Payment Confirmation**: Confirm payments with card details or saved payment methods
- **Refunds**: Process full or partial refunds for completed payments
- **Customer Management**: Create and manage customer profiles with saved payment methods
- **Payment Methods**: Support for cards, digital wallets, and alternative payment methods
- **Webhooks**: Real-time notifications for payment events
- **Multi-currency Support**: Process payments in multiple currencies
- **Fraud Protection**: Built-in fraud detection and risk management

## Installation and Setup

### 1. Configure Settings

Add the following configuration to your `settings.py`:

```python
# Corefy Integration Configuration
COREFY_API_KEY = 'your_api_key_here'  # Your Corefy API key
COREFY_SECRET_KEY = 'your_secret_key_here'  # Your Corefy secret key
COREFY_CLIENT_KEY = 'your_client_key_here'  # Your Corefy client key
COREFY_BASE_URL = 'https://api.corefy.com'  # Production URL
COREFY_WEBHOOK_SECRET = 'your_webhook_secret_here'  # Webhook signature verification
COREFY_TIMEOUT_SECONDS = 30  # API request timeout
COREFY_RETRY_COUNT = 3  # Number of retries for failed requests
COREFY_RATE_LIMIT_PER_MINUTE = 600  # Rate limiting
COREFY_SANDBOX_MODE = False  # Set to True for testing
```

For sandbox/testing, use:
```python
COREFY_BASE_URL = 'https://api.sandbox.corefy.com'
COREFY_SANDBOX_MODE = True
```

### 2. API Authentication

The Corefy integration uses API key authentication. Create an API key using the management command:

```bash
python manage.py create_api_key --partner-name "Your Partner Name" --key-name "Corefy Integration Key"
```

This will generate a public and secret key pair. Use both keys in the format:
```
Authorization: Bearer pk_partner_xxx:sk_secret_xxx
```

### 3. Webhook Setup

Configure your webhook endpoint in the Corefy dashboard:
- URL: `https://yourdomain.com/api/integrations/corefy/webhook/`
- Events: All payment events
- Secret: Use the value from `COREFY_WEBHOOK_SECRET`

## API Endpoints

### Payment Intents

#### Create Payment Intent
```http
POST /api/integrations/corefy/payment-intent/
Authorization: Bearer pk_partner_xxx:sk_secret_xxx
Content-Type: application/json

{
    "amount": "100.00",
    "currency": "USD",
    "payment_method": "card",
    "customer_email": "customer@example.com",
    "customer_name": "John Doe",
    "description": "Test payment",
    "reference_id": "order_123",
    "return_url": "https://yoursite.com/success",
    "failure_url": "https://yoursite.com/failure",
    "billing_first_name": "John",
    "billing_last_name": "Doe",
    "billing_address_line1": "123 Main St",
    "billing_city": "Anytown",
    "billing_state": "NY",
    "billing_postal_code": "12345",
    "billing_country": "US"
}
```

#### Confirm Payment
```http
POST /api/integrations/corefy/confirm-payment/
Authorization: Bearer pk_partner_xxx:sk_secret_xxx
Content-Type: application/json

{
    "payment_intent_id": "pi_xxx",
    "card_number": "4111111111111111",
    "card_expiry_month": "12",
    "card_expiry_year": "2025",
    "card_cvv": "123",
    "card_holder_name": "John Doe"
}
```

#### Get Payment Status
```http
GET /api/integrations/corefy/payment-status/{payment_id}/
Authorization: Bearer pk_partner_xxx:sk_secret_xxx
```

### Refunds

#### Create Refund
```http
POST /api/integrations/corefy/refund/
Authorization: Bearer pk_partner_xxx:sk_secret_xxx
Content-Type: application/json

{
    "payment_id": "pay_xxx",
    "amount": "50.00",  // Optional: partial refund
    "reason": "Customer requested refund",
    "reference_id": "refund_123"
}
```

### Customer Management

#### Create Customer
```http
POST /api/integrations/corefy/customer/
Authorization: Bearer pk_partner_xxx:sk_secret_xxx
Content-Type: application/json

{
    "email": "customer@example.com",
    "name": "John Doe",
    "phone": "+1234567890",
    "address_line1": "123 Main St",
    "city": "Anytown",
    "state": "NY",
    "postal_code": "12345",
    "country": "US",
    "reference_id": "cust_123"
}
```

#### Get Customer
```http
GET /api/integrations/corefy/customer/{customer_id}/
Authorization: Bearer pk_partner_xxx:sk_secret_xxx
```

#### Create Payment Method
```http
POST /api/integrations/corefy/payment-method/
Authorization: Bearer pk_partner_xxx:sk_secret_xxx
Content-Type: application/json

{
    "customer_id": "cust_xxx",
    "payment_method_type": "card",
    "card_number": "4111111111111111",
    "card_expiry_month": "12",
    "card_expiry_year": "2025",
    "card_holder_name": "John Doe"
}
```

#### Get Payment Methods
```http
GET /api/integrations/corefy/customer/{customer_id}/payment-methods/
Authorization: Bearer pk_partner_xxx:sk_secret_xxx
```

### Utility Endpoints

#### Get Supported Payment Methods
```http
GET /api/integrations/corefy/supported-methods/
Authorization: Bearer pk_partner_xxx:sk_secret_xxx
```

#### Test Connection
```http
GET /api/integrations/corefy/test-connection/
Authorization: Bearer pk_partner_xxx:sk_secret_xxx
```

## Service Layer Usage

You can also use the Corefy service directly in your Python code:

```python
from integrations.services import CorefyService
from authentication.models import Merchant

# Initialize service
merchant = Merchant.objects.get(business_name='Your Business')
corefy = CorefyService(merchant=merchant)

# Create payment intent
payment_intent = corefy.create_payment_intent(
    amount=Decimal('100.00'),
    currency='USD',
    customer_email='customer@example.com',
    description='Test payment'
)

# Confirm payment
confirmation = corefy.confirm_payment_intent(
    payment_intent_id=payment_intent['id'],
    payment_data={
        'card_number': '4111111111111111',
        'card_expiry_month': '12',
        'card_expiry_year': '2025',
        'card_cvv': '123',
        'card_holder_name': 'John Doe'
    }
)

# Check payment status
status = corefy.get_payment_status(payment_intent['id'])

# Create refund
refund = corefy.create_refund(
    payment_id=payment_intent['id'],
    amount=Decimal('50.00'),
    reason='Customer requested refund'
)
```

## Webhook Handling

Webhooks are automatically processed and validated. The webhook endpoint handles:

- Payment succeeded/failed events
- Refund completed events
- Customer creation events
- Payment method updates

Webhook data is logged in the `IntegrationWebhook` model for audit purposes.

## Error Handling

The integration includes comprehensive error handling:

- **Network Errors**: Automatic retry with exponential backoff
- **Authentication Errors**: Clear error messages for invalid credentials
- **Validation Errors**: Detailed field-level error information
- **Rate Limiting**: Automatic rate limit compliance
- **Webhook Validation**: Signature verification for security

## Monitoring and Analytics

All API calls are logged in the `IntegrationAPICall` model, including:

- Request/response data
- Response times
- Success/failure rates
- Error details

## Testing

Run the comprehensive test suite:

```bash
python test_corefy_integration.py
```

This tests:
- Service initialization
- API connectivity
- Authentication
- All endpoint functionality
- Webhook processing
- Error handling

## Production Considerations

1. **Security**:
   - Store API credentials in environment variables
   - Use HTTPS for all webhook endpoints
   - Implement proper IP whitelisting if needed

2. **Performance**:
   - Monitor API response times
   - Implement appropriate caching strategies
   - Set up proper rate limiting

3. **Reliability**:
   - Set up monitoring for webhook delivery
   - Implement retry mechanisms for failed operations
   - Monitor API health status

4. **Compliance**:
   - Ensure PCI DSS compliance for card data handling
   - Implement proper data retention policies
   - Follow regional privacy regulations

## Support

For integration issues:
1. Check the logs in Django admin under Integration API Calls
2. Verify credentials and configuration
3. Test connectivity with the test endpoint
4. Review Corefy's official documentation

## Migration from Other Providers

The Corefy integration follows the same patterns as other payment integrations in this system, making it easy to migrate from UBA or CyberSource integrations with minimal code changes.
