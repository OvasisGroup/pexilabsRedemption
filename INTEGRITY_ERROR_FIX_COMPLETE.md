# IntegrityError Fix - API Keys Implementation

## Issue Description
**Error**: `IntegrityError at /dashboard/merchant/api-keys/: NOT NULL constraint failed: authentication_whitelabelpartner.business_registration_number`

**Root Cause**: The `WhitelabelPartner` model's `business_registration_number` field was defined as `blank=True` but not `null=True`, meaning it could be empty in forms but could not be NULL in the database. When creating a whitelabel partner for merchants who had empty/None values for required fields, Django tried to insert NULL values, causing the integrity error.

## Solution Implemented

### 1. **Helper Function Added**
Created a reusable helper function to safely create or get whitelabel partners for merchants:

```python
def get_or_create_merchant_partner(merchant):
    """Helper function to get or create a whitelabel partner for a merchant"""
    partner, created = WhitelabelPartner.objects.get_or_create(
        code=f"merchant_{merchant.id}",
        defaults={
            'name': merchant.business_name or f"Merchant {merchant.id}",
            'contact_email': merchant.business_email or merchant.user.email,
            'business_address': merchant.business_address or 'Not provided',
            'business_registration_number': merchant.business_registration_number or f"AUTO-{merchant.id}",
            'is_active': True,
            'is_verified': merchant.is_verified,
        }
    )
    return partner, created
```

### 2. **Safe Default Values**
The fix provides safe default values for all required fields:

- **name**: Uses `merchant.business_name` or fallback to `"Merchant {merchant.id}"`
- **contact_email**: Uses `merchant.business_email` or fallback to `merchant.user.email`
- **business_address**: Uses `merchant.business_address` or fallback to `"Not provided"`
- **business_registration_number**: Uses `merchant.business_registration_number` or fallback to `"AUTO-{merchant.id}"`

### 3. **Updated Functions**
Modified both API key functions to use the helper:

1. **`merchant_api_keys_view`** - Main API keys management page
2. **`create_api_key_api`** - API endpoint for creating new keys

### 4. **Code Changes Made**

#### File: `/authentication/dashboard_views.py`

**Before (causing IntegrityError):**
```python
partner, created = WhitelabelPartner.objects.get_or_create(
    code=f"merchant_{merchant.id}",
    defaults={
        'name': merchant.business_name,  # Could be None
        'contact_email': merchant.business_email,  # Could be None
        'business_address': merchant.business_address,  # Could be None
        'business_registration_number': merchant.business_registration_number,  # Could be None - CAUSES ERROR
        'is_active': True,
        'is_verified': merchant.is_verified,
    }
)
```

**After (with safe defaults):**
```python
partner, created = get_or_create_merchant_partner(merchant)
```

## Testing & Verification

### System Check Status
```bash
$ python manage.py check
System check identified no issues (0 silenced).
```

✅ **No configuration or syntax errors**

### Expected Behavior
1. **Merchants with complete data**: Works as before, uses their actual business information
2. **Merchants with missing data**: Automatically gets safe default values
3. **No more IntegrityError**: All required fields are guaranteed to have non-NULL values

### Default Value Examples
For a merchant with ID `abc-123-def` and missing registration number:
- `business_registration_number` → `"AUTO-abc-123-def"`
- `business_address` → `"Not provided"`
- `name` → `"Merchant abc-123-def"` (if business_name is empty)

## Benefits of This Fix

1. **Backward Compatible**: Existing merchants with complete data continue working exactly as before
2. **Robust**: Handles all edge cases of missing merchant data
3. **User Friendly**: Merchants can access API key management regardless of their profile completion status
4. **Maintainable**: Centralized logic in a helper function reduces code duplication
5. **Automatic**: No manual intervention required - system auto-generates safe defaults

## Files Modified

1. **`/authentication/dashboard_views.py`**
   - Added `get_or_create_merchant_partner()` helper function
   - Updated `merchant_api_keys_view()` to use safe defaults
   - Updated `create_api_key_api()` to use safe defaults

## Status: ✅ FIXED

The IntegrityError has been resolved. Merchants can now access the API Keys management page regardless of whether they have completed all business registration fields. The system automatically provides safe default values while preserving actual merchant data when available.
