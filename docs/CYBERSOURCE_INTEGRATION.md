# CyberSource Integration Documentation

## Overview

This document describes the CyberSource payment integration that has been added to the PexiLabs Django application. CyberSource is a leading payment management platform that provides secure payment processing capabilities.

## Integration Details

### Configuration

The following CyberSource settings have been added to `settings.py`:

```python
# CyberSource Integration Configuration
CYBERSOURCE_MERCHANT_ID = 'e6d04dd3-6695-4ab2-a8a8-78cadaac9108'
CYBERSOURCE_SHARED_SECRET = '7QruQKZ56AXtBe1kZXFN9tYzd7SjUFE3rEHoH88NvlU='
CYBERSOURCE_BASE_URL = 'https://apitest.cybersource.com'  # Sandbox URL
```

### API Endpoints

The following CyberSource endpoints are available at `/api/integrations/cybersource/`:

#### Payment Operations
- **POST** `/payment/` - Create a new payment
- **POST** `/capture/` - Capture an authorized payment
- **POST** `/refund/` - Refund a processed payment
- **GET** `/payment-status/<payment_id>/` - Get payment status

#### Customer Management
- **POST** `/customer/` - Create a new customer
- **POST** `/token/` - Create a payment token for a customer

#### Utility Endpoints
- **POST** `/webhook/` - Handle CyberSource webhooks
- **GET** `/test-connection/` - Test CyberSource API connection

### Authentication

All endpoints require API key authentication in the format:
```
Authorization: Bearer pk_test_partner_xxx:secret_key_xxx
```

### Service Implementation

The `CyberSourceService` class in `integrations/services.py` provides:

- Payment processing (authorize, capture, refund)
- Customer management
- Token creation for secure payment storage
- Webhook handling for payment notifications
- Connection testing and validation

### Key Features

1. **Secure Payment Processing**: Utilizes CyberSource's secure payment gateway
2. **Token-based Payments**: Support for tokenized payments for returning customers
3. **Webhook Support**: Real-time payment status updates via webhooks
4. **Comprehensive Error Handling**: Detailed error responses and logging
5. **API Key Authentication**: Secure merchant-specific access control

### Example Usage

#### Create a Payment

```bash
curl -X POST http://localhost:8000/api/integrations/cybersource/payment/ \
  -H "Authorization: Bearer pk_test_partner_xxx:secret_key_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "100.00",
    "currency": "USD",
    "card_number": "4111111111111111",
    "expiry_month": "12",
    "expiry_year": "2025",
    "cvv": "123",
    "cardholder_name": "John Doe",
    "billing_first_name": "John",
    "billing_last_name": "Doe",
    "billing_address1": "123 Main St",
    "billing_city": "New York",
    "billing_state": "NY",
    "billing_postal_code": "10001",
    "billing_country": "US",
    "billing_email": "john.doe@example.com"
  }'
```

#### Test Connection

```bash
curl -X GET http://localhost:8000/api/integrations/cybersource/test-connection/ \
  -H "Authorization: Bearer pk_test_partner_xxx:secret_key_xxx"
```

### Response Format

All endpoints return standardized JSON responses:

```json
{
  "success": true/false,
  "data": {...},
  "message": "Description of the result",
  "error_code": "Error code if applicable"
}
```

### Error Handling

The integration includes comprehensive error handling for:
- Invalid payment data
- Network connectivity issues
- CyberSource API errors
- Authentication failures
- Invalid API keys

### Testing

A test script `test_cybersource_integration.py` is provided to verify all endpoints:

```bash
python test_cybersource_integration.py
```

## Security Considerations

1. **API Keys**: API keys are securely hashed and stored
2. **HTTPS**: All production communication should use HTTPS
3. **IP Restrictions**: API keys can be restricted to specific IP addresses
4. **Webhook Verification**: Webhook signatures should be verified for security
5. **PCI Compliance**: Follow PCI DSS guidelines for handling card data

## Production Deployment

For production deployment:

1. Update `CYBERSOURCE_BASE_URL` to production endpoint
2. Use production merchant credentials
3. Enable HTTPS for all API communication
4. Configure proper webhook endpoints
5. Implement comprehensive logging and monitoring

## Support

For technical support or questions about the integration:
- Check the Django logs for detailed error messages
- Review the CyberSource API documentation
- Use the test connection endpoint to verify configuration
