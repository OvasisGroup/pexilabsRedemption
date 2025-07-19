# PexiLabs API Documentation System

A comprehensive API documentation and integration system built for third-party developers to easily integrate with the PexiLabs payment platform.

## Overview

The API documentation system provides:

- **Interactive API Documentation** - Complete API reference with live examples
- **Integration Guides** - Step-by-step tutorials for popular frameworks
- **SDK Documentation** - Official SDKs for JavaScript, Python, and PHP
- **Webhook Testing Tool** - Real-time webhook endpoint testing
- **API Explorer** - Interactive tool for testing API endpoints

## Features

### 📚 API Documentation (`/docs/api/`)
- Complete API reference with all endpoints
- Interactive code examples with copy-to-clipboard
- Authentication and error handling guides
- Response schemas and status codes
- Rate limiting and best practices

### 🔧 Integration Guides (`/docs/integration/`)
- Quick start guide (5 minutes to first payment)
- Framework-specific guides:
  - React.js integration
  - Vue.js integration
  - Angular integration
  - Laravel (PHP) integration
  - Django (Python) integration
  - Node.js/Express integration
- Common integration patterns
- Security best practices

### 📦 SDK Documentation (`/docs/sdks/`)
- **JavaScript SDK** - Client-side payment processing
- **Python SDK** - Server-side integration with Django examples
- **PHP SDK** - Server-side integration with Laravel examples
- Installation instructions and quick start
- Feature comparison table
- Code examples and best practices

### 🔌 Webhook Testing Tool (`/docs/webhooks/`)
- Test webhook endpoints in real-time
- Sample event types (payment.completed, payment.failed, etc.)
- Custom event payload editor
- Response logging and debugging
- Connection testing and validation

### 🧪 API Explorer (`/docs/explorer/`)
- Interactive API testing interface
- Real-time endpoint testing
- Parameter configuration
- Request/response inspection
- Authentication testing

## File Structure

```
/docs/
├── views.py              # Django views for documentation pages
├── urls.py               # URL routing for docs section
└── templates/docs/
    ├── api_documentation.html    # Main API docs page
    ├── integration_guides.html   # Framework integration guides
    ├── sdk_documentation.html    # SDK documentation
    ├── webhook_testing.html      # Webhook testing tool
    └── api_explorer.html         # Interactive API explorer
```

## Setup and Installation

### 1. URL Configuration
The documentation URLs are included in the main project:

```python
# pexilabs/urls.py
urlpatterns = [
    # ... other URLs
    path('docs/', include('docs_urls')),
]
```

### 2. Navigation Integration
Documentation links are added to the dashboard sidebar under "Developer Tools":

- API Documentation
- Integration Guides  
- SDK Documentation
- Webhook Testing
- API Explorer

### 3. Access Control
All documentation pages are accessible without authentication to allow third-party developers to explore the API.

## Usage Examples

### Creating a Payment (JavaScript)
```javascript
import PexiLabs from '@pexilabs/js-sdk';

const pexilabs = new PexiLabs({
    apiKey: 'pk_test_...',
    environment: 'sandbox'
});

const payment = await pexilabs.createPayment({
    amount: 1000, // $10.00
    currency: 'USD',
    description: 'Test payment'
});

window.location.href = payment.checkout_url;
```

### Creating a Payment (Python/Django)
```python
import pexilabs

client = pexilabs.Client(
    api_key='sk_test_...',
    environment='sandbox'
)

payment = client.payments.create({
    'amount': 1000,
    'currency': 'USD',
    'description': 'Test payment',
    'return_url': 'https://example.com/success',
    'cancel_url': 'https://example.com/cancel'
})
```

### Webhook Handling (Python/Django)
```python
@csrf_exempt
def webhook_view(request):
    payload = request.body
    sig_header = request.META.get('HTTP_PEXILABS_SIGNATURE')
    
    try:
        event = pexilabs.Webhook.construct_event(
            payload, sig_header, 'webhook_secret'
        )
        
        if event.type == 'payment.completed':
            # Handle successful payment
            payment = event.data.object
            # Update your database
            
    except Exception as e:
        return HttpResponse(status=400)
        
    return HttpResponse(status=200)
```

## Key Components

### Interactive Features
- **Copy-to-clipboard** for all code examples
- **Tabbed code examples** for multiple languages/frameworks
- **Live API testing** with real responses
- **Webhook simulation** with custom payloads
- **Parameter validation** and error handling

### Developer Experience
- **Search functionality** across all documentation
- **Responsive design** for desktop and mobile
- **Syntax highlighting** for code blocks
- **Error explanations** with solutions
- **Rate limiting information** and guidelines

### Testing Tools
- **Sandbox environment** for safe testing
- **Mock data generation** for realistic examples
- **Response validation** and debugging
- **Connection testing** for webhooks
- **Performance metrics** (response times)

## API Endpoints Covered

### Payments
- `POST /api/payments` - Create payment
- `GET /api/payments/{id}` - Get payment
- `GET /api/payments` - List payments
- `POST /api/payments/{id}/refund` - Refund payment

### Payment Links
- `POST /api/payment-links` - Create payment link
- `GET /api/payment-links/{id}` - Get payment link

### Transactions
- `GET /api/transactions` - List transactions
- `GET /api/transactions/{id}` - Get transaction

### Webhooks
- `POST /webhook-endpoint` - Test webhook endpoint

## Security Features

### Authentication
- API key management and rotation
- Environment separation (sandbox/production)
- Request signing and verification
- Rate limiting and throttling

### Best Practices
- HTTPS enforcement
- Webhook signature verification
- Proper error handling
- Data validation and sanitization

## Contributing

To add new documentation sections:

1. Create new template in `templates/docs/`
2. Add view function in `docs_views.py`
3. Add URL pattern in `docs_urls.py`
4. Update navigation in `base_dashboard.html`

## Support

For developer support:
- Email: developers@pexilabs.com
- Documentation: https://docs.pexilabs.com
- GitHub: https://github.com/pexilabs/api-docs
- Discord: https://discord.gg/pexilabs

## License

This documentation system is part of the PexiLabs platform and is subject to the platform's terms of service.
