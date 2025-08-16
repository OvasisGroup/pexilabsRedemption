# Public Transaction API Documentation

This document provides comprehensive documentation for the Public Transaction API endpoints. These APIs allow merchants to retrieve transaction data using API key authentication.

## Authentication

All transaction endpoints require API key authentication using the same process as other public APIs.

### API Key Format
```
X-API-Key: pk_merchant_<uuid>_<public_key>:<secret_key>
```

### Authentication Headers
You can provide the API key in either of these headers:
- `X-API-Key: <api_key>`
- `Authorization: Bearer <api_key>`

### Example
```bash
curl -H "X-API-Key: pk_merchant_552ca963-c8f7-478f-9973-255c4339aab2_Ma8Fxfe4wvgLwV2X:1mC73EuZ0S2aZ89MnlIfQmQPxzMNcBdYe0PT3ro0PMk" \
     http://localhost:8000/api/transactions/
```

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/transactions/` | List all transactions with pagination and filtering |
| GET | `/api/transactions/{id}/` | Get a specific transaction by ID |
| GET | `/api/transactions/reference/{reference}/` | Get a transaction by reference |
| GET | `/api/transactions/stats/` | Get transaction statistics |
| GET | `/api/transactions/choices/` | Get available transaction choices |

## 1. List Transactions

### Endpoint
```
GET /api/transactions/
```

### Description
Retrieve a paginated list of transactions for the authenticated merchant.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Number of items per page (default: 20, max: 100) |
| `status` | string | No | Filter by transaction status |
| `transaction_type` | string | No | Filter by transaction type |
| `payment_method` | string | No | Filter by payment method |
| `currency` | string | No | Filter by currency code |
| `date_from` | date | No | Filter transactions from this date (YYYY-MM-DD) |
| `date_to` | date | No | Filter transactions to this date (YYYY-MM-DD) |
| `amount_min` | decimal | No | Filter by minimum amount |
| `amount_max` | decimal | No | Filter by maximum amount |
| `search` | string | No | Search in reference, external_reference, or description |

### Example Request
```bash
curl -H "X-API-Key: your_api_key" \
     "http://localhost:8000/api/transactions/?page=1&page_size=10&status=completed&date_from=2024-01-01"
```

### Example Response
```json
{
    "count": 150,
    "next": "http://localhost:8000/api/transactions/?page=2&page_size=10&status=completed&date_from=2024-01-01",
    "previous": null,
    "results": [
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "reference": "TXN-2024-001",
            "external_reference": "EXT-REF-001",
            "transaction_type": "payment",
            "status": "completed",
            "payment_method": "card",
            "currency": "USD",
            "amount": "100.00",
            "fee_amount": "2.50",
            "net_amount": "97.50",
            "description": "Payment for order #12345",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:35:00Z",
            "completed_at": "2024-01-15T10:35:00Z"
        }
    ]
}
```

## 2. Get Transaction by ID

### Endpoint
```
GET /api/transactions/{transaction_id}/
```

### Description
Retrieve a specific transaction by its UUID.

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `transaction_id` | UUID | Yes | The unique identifier of the transaction |

### Example Request
```bash
curl -H "X-API-Key: your_api_key" \
     "http://localhost:8000/api/transactions/123e4567-e89b-12d3-a456-426614174000/"
```

### Example Response
```json
{
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "reference": "TXN-2024-001",
    "external_reference": "EXT-REF-001",
    "merchant": {
        "id": "456e7890-e89b-12d3-a456-426614174001",
        "business_name": "Example Business",
        "email": "business@example.com"
    },
    "customer": {
        "id": "789e0123-e89b-12d3-a456-426614174002",
        "email": "customer@example.com",
        "first_name": "John",
        "last_name": "Doe"
    },
    "transaction_type": "payment",
    "status": "completed",
    "payment_method": "card",
    "gateway": "stripe",
    "currency": "USD",
    "amount": "100.00",
    "fee_amount": "2.50",
    "net_amount": "97.50",
    "description": "Payment for order #12345",
    "metadata": {
        "order_id": "12345",
        "customer_ip": "192.168.1.1"
    },
    "payment_details": {
        "card_last_four": "1234",
        "card_brand": "visa"
    },
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z",
    "completed_at": "2024-01-15T10:35:00Z",
    "failed_at": null,
    "cancelled_at": null
}
```

## 3. Get Transaction by Reference

### Endpoint
```
GET /api/transactions/reference/{reference}/
```

### Description
Retrieve a transaction by its reference string.

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `reference` | string | Yes | The reference identifier of the transaction |

### Example Request
```bash
curl -H "X-API-Key: your_api_key" \
     "http://localhost:8000/api/transactions/reference/TXN-2024-001/"
```

### Example Response
Same format as "Get Transaction by ID" endpoint.

## 4. Get Transaction Statistics

### Endpoint
```
GET /api/transactions/stats/
```

### Description
Retrieve transaction statistics for the authenticated merchant.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date_from` | date | No | Start date for statistics (YYYY-MM-DD) |
| `date_to` | date | No | End date for statistics (YYYY-MM-DD) |
| `period` | string | No | Grouping period: 'day', 'week', 'month', 'year' |
| `currency` | string | No | Filter by currency code |

### Example Request
```bash
curl -H "X-API-Key: your_api_key" \
     "http://localhost:8000/api/transactions/stats/?date_from=2024-01-01&date_to=2024-01-31&period=day"
```

### Example Response
```json
{
    "total_transactions": 150,
    "total_amount": "15000.00",
    "total_fees": "375.00",
    "total_net_amount": "14625.00",
    "average_transaction_amount": "100.00",
    "currency": "USD",
    "period_stats": [
        {
            "period": "2024-01-01",
            "transaction_count": 5,
            "total_amount": "500.00",
            "average_amount": "100.00"
        },
        {
            "period": "2024-01-02",
            "transaction_count": 8,
            "total_amount": "800.00",
            "average_amount": "100.00"
        }
    ],
    "status_breakdown": {
        "completed": 120,
        "pending": 15,
        "failed": 10,
        "cancelled": 5
    },
    "payment_method_breakdown": {
        "card": 100,
        "bank_transfer": 30,
        "mobile_money": 20
    }
}
```

## 5. Get Transaction Choices

### Endpoint
```
GET /api/transactions/choices/
```

### Description
Retrieve available choices for transaction fields (status, type, payment methods, etc.).

### Example Request
```bash
curl -H "X-API-Key: your_api_key" \
     "http://localhost:8000/api/transactions/choices/"
```

### Example Response
```json
{
    "transaction_types": [
        {"value": "payment", "label": "Payment"},
        {"value": "refund", "label": "Refund"},
        {"value": "transfer", "label": "Transfer"}
    ],
    "statuses": [
        {"value": "pending", "label": "Pending"},
        {"value": "completed", "label": "Completed"},
        {"value": "failed", "label": "Failed"},
        {"value": "cancelled", "label": "Cancelled"}
    ],
    "payment_methods": [
        {"value": "card", "label": "Credit/Debit Card"},
        {"value": "bank_transfer", "label": "Bank Transfer"},
        {"value": "mobile_money", "label": "Mobile Money"}
    ]
}
```

## Error Responses

### Authentication Errors

#### 401 Unauthorized
```json
{
    "error": "Authentication required",
    "message": "Please provide a valid API key in Authorization header or X-API-Key header",
    "authenticated": false
}
```

### Validation Errors

#### 400 Bad Request
```json
{
    "error": "Validation error",
    "details": {
        "page_size": ["Ensure this value is less than or equal to 100."]
    }
}
```

### Not Found Errors

#### 404 Not Found
```json
{
    "error": "Transaction not found",
    "message": "No transaction found with the provided ID or reference"
}
```

### Server Errors

#### 500 Internal Server Error
```json
{
    "error": "Internal server error",
    "message": "An unexpected error occurred. Please try again later."
}
```

## Rate Limiting

API requests are subject to rate limiting:
- **Rate Limit**: 1000 requests per hour per API key
- **Burst Limit**: 100 requests per minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Best Practices

### 1. Pagination
- Always use pagination for list endpoints
- Keep page_size reasonable (≤ 100)
- Use the `next` and `previous` URLs for navigation

### 2. Filtering
- Use date filters to limit data ranges
- Combine filters to get specific data sets
- Use search parameter for text-based filtering

### 3. Error Handling
- Always check the HTTP status code
- Parse error messages for debugging
- Implement retry logic for 5xx errors

### 4. Security
- Keep API keys secure and never expose them in client-side code
- Use HTTPS for all API requests
- Rotate API keys regularly

### 5. Performance
- Cache responses when appropriate
- Use appropriate filters to reduce data transfer
- Monitor rate limits and implement backoff strategies

## SDK Examples

### Python
```python
import requests

api_key = "your_api_key_here"
base_url = "http://localhost:8000/api"

headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

# List transactions
response = requests.get(f"{base_url}/transactions/", headers=headers)
transactions = response.json()

# Get specific transaction
transaction_id = "123e4567-e89b-12d3-a456-426614174000"
response = requests.get(f"{base_url}/transactions/{transaction_id}/", headers=headers)
transaction = response.json()
```

### JavaScript
```javascript
const apiKey = 'your_api_key_here';
const baseUrl = 'http://localhost:8000/api';

const headers = {
    'X-API-Key': apiKey,
    'Content-Type': 'application/json'
};

// List transactions
fetch(`${baseUrl}/transactions/`, { headers })
    .then(response => response.json())
    .then(data => console.log(data));

// Get specific transaction
const transactionId = '123e4567-e89b-12d3-a456-426614174000';
fetch(`${baseUrl}/transactions/${transactionId}/`, { headers })
    .then(response => response.json())
    .then(data => console.log(data));
```

### cURL
```bash
# List transactions with filters
curl -H "X-API-Key: your_api_key" \
     "http://localhost:8000/api/transactions/?status=completed&page_size=50"

# Get transaction by ID
curl -H "X-API-Key: your_api_key" \
     "http://localhost:8000/api/transactions/123e4567-e89b-12d3-a456-426614174000/"

# Get transaction statistics
curl -H "X-API-Key: your_api_key" \
     "http://localhost:8000/api/transactions/stats/?period=month"
```

## Testing

You can test these endpoints using the provided examples or through the interactive API documentation at:
- Swagger UI: `http://localhost:8000/api/docs/`
- ReDoc: `http://localhost:8000/api/redoc/`

## Support

For additional support or questions about the Transaction API:
- Email: developers@pexilabs.com
- Documentation: http://localhost:8000/api/docs/
- GitHub: [PexiLabs Repository]

---

**Last Updated**: January 2024  
**API Version**: v1.0