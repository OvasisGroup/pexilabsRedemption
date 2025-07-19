# NoReverseMatch Error Fix - API Keys Template

## Issue Description
**Error**: `NoReverseMatch at /dashboard/merchant/api-keys/: Reverse for 'revoke_api_key_api' with keyword arguments '{'key_id': 'PLACEHOLDER'}' not found. 1 pattern(s) tried: ['dashboard/api/api\\-keys/(?P<key_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/revoke/\\Z']`

**Root Cause**: The template was using Django's `{% url %}` tag with a placeholder value ('PLACEHOLDER') for the `key_id` parameter. Django tries to validate URL parameters during template rendering, and 'PLACEHOLDER' doesn't match the required UUID format pattern, causing the NoReverseMatch error.

## Solution Implemented

### **Problem Code (Before)**
```django-html
const response = await fetch(`{% url "dashboard:revoke_api_key_api" key_id="PLACEHOLDER" %}`.replace('PLACEHOLDER', keyId), {
    method: 'DELETE',
    headers: {
        'X-CSRFToken': getCookie('csrftoken')
    }
});
```

The issue was that Django tried to reverse the URL with 'PLACEHOLDER' as the key_id during template rendering, but the URL pattern expects a valid UUID format.

### **Fixed Code (After)**
```django-html
const response = await fetch(`/dashboard/api/api-keys/${keyId}/revoke/`, {
    method: 'DELETE',
    headers: {
        'X-CSRFToken': getCookie('csrftoken')
    }
});
```

### **Changes Made**

#### File: `/templates/dashboard/merchant_api_keys.html`

1. **Revoke API Key Function**:
   - **Before**: `{% url "dashboard:revoke_api_key_api" key_id="PLACEHOLDER" %}`.replace('PLACEHOLDER', keyId)
   - **After**: `/dashboard/api/api-keys/${keyId}/revoke/`

2. **Regenerate API Key Function**:
   - **Before**: `{% url "dashboard:regenerate_api_key_api" key_id="PLACEHOLDER" %}`.replace('PLACEHOLDER', keyId)
   - **After**: `/dashboard/api/api-keys/${keyId}/regenerate/`

## Why This Fix Works

1. **No Template-Time URL Resolution**: By using direct URL paths instead of Django's `{% url %}` tag, we avoid Django trying to validate placeholder values during template rendering.

2. **Runtime URL Construction**: The URLs are now constructed at runtime in JavaScript using template literals, which allows dynamic insertion of actual UUID values.

3. **Matches URL Patterns**: The hardcoded paths exactly match the URL patterns defined in `dashboard_urls.py`:
   ```python
   path('api/api-keys/<uuid:key_id>/revoke/', dashboard_views.revoke_api_key_api, name='revoke_api_key_api'),
   path('api/api-keys/<uuid:key_id>/regenerate/', dashboard_views.regenerate_api_key_api, name='regenerate_api_key_api'),
   ```

4. **UUID Format Compatibility**: When actual API key UUIDs are substituted at runtime, they match the expected UUID regex pattern.

## Testing & Verification

### System Check Status
```bash
$ python manage.py check
System check identified no issues (0 silenced).
```

### Template Rendering Test
```bash
$ python test_template_fix.py
✅ API Keys page renders successfully!
✅ No NoReverseMatch error occurred
✅ Page contains expected UI elements
✅ JavaScript functions are present
✅ Fixed URLs are present in JavaScript
```

## Alternative Solutions Considered

1. **Using Valid UUID in Template**: Could have used a valid UUID format instead of 'PLACEHOLDER', but this would be misleading and could cause confusion.

2. **JavaScript URL Building**: Could have passed the base URLs as JavaScript variables, but the direct approach is simpler and more maintainable.

3. **Django URL Namespacing**: Could have used a different URL structure, but that would require larger changes to the URL patterns.

## Benefits of This Fix

1. **Immediate Resolution**: Eliminates the NoReverseMatch error completely
2. **Performance**: Slightly better performance as no Django URL resolution needed at template render time
3. **Simplicity**: Easier to understand and maintain - URLs are clearly visible in the JavaScript
4. **Reliability**: No dependency on Django template URL resolution for dynamic URLs
5. **Debugging**: Easier to debug URL issues in browser developer tools

## Files Modified

1. **`/templates/dashboard/merchant_api_keys.html`**
   - Updated `revokeApiKey()` function to use direct URL path
   - Updated `regenerateApiKey()` function to use direct URL path

## Status: ✅ FIXED

The NoReverseMatch error has been resolved. The API Keys management page now renders without errors and the JavaScript functions can properly construct URLs for API key operations at runtime using actual UUID values.
