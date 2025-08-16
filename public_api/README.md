# Public API - API Key Authentication Decorator

This module provides a reusable decorator for API key authentication that can be used with both function-based and class-based Django views.

## Features

- **Universal Compatibility**: Works with both function-based views and class-based views
- **Automatic Authentication**: Handles API key validation using the existing `APIKeyAuthentication` system
- **Request Enhancement**: Adds `api_key` and `api_partner` attributes to the request object
- **Comprehensive Error Handling**: Returns appropriate JSON error responses for authentication failures
- **CSRF Exempt**: Automatically exempts decorated views from CSRF protection
- **Consistent Response Format**: Standardized JSON error responses

## Installation

The decorator is located in `public_api/utils.py` and can be imported as:

```python
from public_api.utils import api_key_required
```

## Usage

### Function-Based Views

```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from public_api.utils import api_key_required

@api_key_required
@require_http_methods(["GET"])
def get_partner_info(request):
    """
    Example function-based view that returns partner information.
    """
    partner = request.api_partner
    app_key = request.api_key
    
    return JsonResponse({
        'partner_name': partner.name,
        'partner_code': partner.code,
        'api_key_name': app_key.name,
        'scopes': app_key.get_scopes_list()
    })
```

### Class-Based Views

```python
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from public_api.utils import api_key_required

@method_decorator(api_key_required, name='dispatch')
class PartnerStatsView(View):
    """
    Example class-based view with API key authentication.
    """
    
    def get(self, request):
        partner = request.api_partner
        app_key = request.api_key
        
        return JsonResponse({
            'partner': {
                'id': str(partner.id),
                'name': partner.name,
                'code': partner.code,
                'is_active': partner.is_active
            },
            'api_key': {
                'name': app_key.name,
                'key_type': app_key.key_type,
                'status': app_key.status
            }
        })
```

## API Key Format

The decorator expects API keys in the following format:

- **Header**: `X-API-Key` or `Authorization: Bearer <api_key>`
- **Format**: `pk_merchant_<uuid>_<public_key>:<secret_key>`

Example:
```
X-API-Key: pk_merchant_552ca963-c8f7-478f-9973-255c4339aab2_Ma8Fxfe4wvgLwV2X:1mC73EuZ0S2aZ89MnlIfQmQPxzMNcBdYe0PT3ro0PMk
```

## Request Attributes

After successful authentication, the decorator adds the following attributes to the request object:

- `request.api_key`: The `AppKey` model instance
- `request.api_partner`: The `WhitelabelPartner` model instance associated with the API key

## Error Responses

The decorator returns standardized JSON error responses:

### Authentication Required (401)
```json
{
    "error": "Authentication required",
    "message": "Please provide a valid API key in Authorization header or X-API-Key header",
    "authenticated": false
}
```

### Internal Server Error (500)
```json
{
    "error": "Internal server error",
    "message": "An error occurred during authentication verification",
    "authenticated": false
}
```

## Helper Functions

### `get_api_context(request)`

A helper function that extracts authentication context from a request:

```python
from public_api.utils import get_api_context

def my_view(request):
    context = get_api_context(request)
    if context:
        app_key, partner = context
        # Use app_key and partner
    else:
        # Handle unauthenticated request
```

## Implementation Details

### Decorator Logic

1. **CSRF Exemption**: Automatically applies `@csrf_exempt`
2. **Authentication**: Uses `APIKeyAuthentication().authenticate(request)`
3. **Request Enhancement**: Adds `api_key` and `api_partner` attributes
4. **Error Handling**: Catches exceptions and returns appropriate JSON responses
5. **View Execution**: Calls the original view function with enhanced request

### Compatibility

- **Django Version**: Compatible with Django 4.2+
- **Python Version**: Compatible with Python 3.8+
- **View Types**: Function-based views and class-based views
- **HTTP Methods**: All HTTP methods supported

## Testing

To test the decorator:

```bash
# Test with valid API key
curl -X POST http://localhost:8000/api/auth/verify/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pk_merchant_<uuid>_<public_key>:<secret_key>"

# Test with invalid API key
curl -X POST http://localhost:8000/api/auth/verify/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: invalid_key"
```

## Best Practices

1. **Always use HTTPS** in production to protect API keys in transit
2. **Log authentication failures** for security monitoring
3. **Rate limit** API endpoints to prevent abuse
4. **Validate input data** even after authentication
5. **Use appropriate HTTP status codes** in your responses

## Security Considerations

- API keys are validated against the database on every request
- Invalid API keys are logged for security monitoring
- The decorator automatically handles CSRF exemption for API endpoints
- All authentication errors are logged with appropriate detail levels

## Examples

See `public_api/views/example_usage.py` for complete working examples of both function-based and class-based views using the decorator.