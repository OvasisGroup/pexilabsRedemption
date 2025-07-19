# 🏢 Auto Merchant Account Creation - Feature Documentation

## Overview

The PexiLabs fintech platform now automatically creates merchant accounts when users become verified. This is implemented using Django signals that trigger when a user's `is_verified` status changes from `False` to `True`.

## 🎯 How It Works

### Signal Flow

1. **User Verification Event**: When a user's `is_verified` field is set to `True`
2. **Signal Triggered**: Django `post_save` signal fires for the `CustomUser` model
3. **Merchant Creation**: A new `Merchant` account is automatically created
4. **Logging**: The creation event is logged for auditing purposes

### Trigger Conditions

The merchant account is created when:

✅ **New verified user**: User is created with `is_verified=True` (e.g., superusers)  
✅ **User verification**: Existing unverified user becomes verified (`False` → `True`)  
❌ **Already verified**: User is already verified (no duplicate creation)  
❌ **Existing merchant**: User already has a merchant account  
❌ **Unverified user**: User remains unverified  

## 📋 Implementation Details

### Files Created/Modified

1. **`authentication/signals.py`** - Contains all signal handlers
2. **`authentication/apps.py`** - Connects signals when app starts
3. **`authentication/management/commands/demo_merchant_signals.py`** - Demo/testing command

### Signal Functions

#### `auto_create_merchant_on_verification()`
- **Trigger**: `post_save` signal on `CustomUser` model
- **Purpose**: Creates merchant account when user becomes verified
- **Features**:
  - Prevents duplicate merchant creation
  - Uses default merchant category
  - Sets merchant status to 'pending'
  - Logs creation events
  - Handles errors gracefully

#### `track_verification_change()`
- **Trigger**: `pre_save` signal on `CustomUser` model  
- **Purpose**: Tracks when verification status changes
- **Features**:
  - Compares old vs new verification status
  - Stores change information for `post_save` processing

#### `log_merchant_status_changes()`
- **Trigger**: `post_save` signal on `Merchant` model
- **Purpose**: Logs merchant status and verification changes
- **Features**:
  - Audit trail for merchant changes
  - Status change tracking
  - Verification change logging

## 🏗 Merchant Account Details

When auto-created, the merchant account has these properties:

```python
merchant = Merchant.objects.create(
    user=user,
    business_name=f"{user.get_full_name()}'s Business",
    business_email=user.email,
    business_phone=user.phone_number or '',
    business_address='',  # Empty - user needs to fill
    category=default_category,  # General Business if available
    description=f"Automatically created merchant account for {user.get_full_name()}",
    status='pending',  # Requires manual approval
    is_verified=False,  # Merchant verification is separate
)
```

### Default Values

| Field | Value | Notes |
|-------|-------|-------|
| `business_name` | `"{User's Full Name}'s Business"` | Can be changed by user |
| `business_email` | User's email address | Inherits from user |
| `business_phone` | User's phone number | Inherits from user |
| `business_address` | Empty string | User must fill this |
| `category` | Default category (General Business) | First available category |
| `status` | `'pending'` | Requires admin approval |
| `is_verified` | `False` | Separate from user verification |

## 🧪 Testing the Feature

### Management Command

Use the built-in management command to test the functionality:

```bash
# Create a test user
python manage.py demo_merchant_signals --create-test-user

# Verify the user (triggers merchant creation)
python manage.py demo_merchant_signals --verify-user user@example.com

# List all merchants
python manage.py demo_merchant_signals --list-merchants

# Clean up test data
python manage.py demo_merchant_signals --cleanup-test-data
```

### Automated Test Suite

Run the comprehensive test suite:

```bash
python test_merchant_signals.py
```

This tests:
- ✅ Auto merchant creation on verification
- ✅ No duplicate merchant creation
- ✅ No merchant for unverified users

## 📊 Real-World Usage

### OTP Verification Flow

The most common trigger is during OTP email verification:

```python
# In authentication/views.py - OTPVerificationView
if otp_instance.purpose == 'registration':
    user.is_verified = True  # 🔥 This triggers the signal
    user.save()
    
    # Signal automatically creates merchant account here
```

### Admin Verification

When admins manually verify users:

```python
# Admin panel or API
user.is_verified = True
user.save()  # 🔥 Signal triggers merchant creation
```

### Superuser Creation

When creating superusers:

```python
python manage.py createsuperuser
# OR
CustomUser.objects.create_superuser(
    email='admin@example.com',
    password='password',
    is_verified=True  # 🔥 Signal triggers merchant creation
)
```

## 🔧 Configuration Options

### Default Category Setup

Ensure you have a default merchant category:

```python
from authentication.models import MerchantCategory

# Create default category
MerchantCategory.objects.get_or_create(
    code='general',
    defaults={
        'name': 'General Business',
        'description': 'Default category for new merchants',
        'is_active': True
    }
)
```

### Logging Configuration

The signals use Django's logging system. Configure in `settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'merchant_signals.log',
        },
    },
    'loggers': {
        'authentication.signals': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🚨 Error Handling

The signals handle errors gracefully:

```python
try:
    # Create merchant account
    merchant = Merchant.objects.create(...)
    logger.info(f"✅ Auto-created merchant for {user.email}")
except Exception as e:
    logger.error(f"❌ Failed to create merchant for {user.email}: {e}")
    # Signal fails silently - doesn't break user verification
```

## 📈 Monitoring & Auditing

### Log Messages

The signals generate these log messages:

```
INFO: ✅ Auto-created merchant account for verified user: user@example.com (Merchant ID: abc-123)
INFO: 📝 New merchant account created: User's Business (ID: abc-123) for user user@example.com
INFO: 🔄 Merchant status changed for User's Business: pending → approved
INFO: ✅ Merchant verification changed for User's Business: now verified
WARNING: ⚠️ Merchant account suspended due to user deactivation: User's Business (was approved)
```

### Database Queries

Monitor merchant creation:

```sql
-- Recently auto-created merchants
SELECT m.*, u.email, u.is_verified
FROM authentication_merchant m
JOIN authentication_customuser u ON m.user_id = u.id
WHERE m.created_at >= NOW() - INTERVAL '24 HOURS'
ORDER BY m.created_at DESC;

-- Users without merchant accounts
SELECT u.email, u.is_verified, u.created_at
FROM authentication_customuser u
LEFT JOIN authentication_merchant m ON u.id = m.user_id
WHERE u.is_verified = true AND m.id IS NULL;
```

## 🔐 Security Considerations

### User Verification Security

- User verification should be properly validated (OTP, email confirmation, etc.)
- Signals only trigger after verification is confirmed
- Merchant accounts start with 'pending' status (require admin approval)

### Merchant Verification

- Auto-created merchant accounts are **not automatically verified**
- `merchant.is_verified = False` by default
- Requires separate merchant verification process
- Admin approval needed for merchant activation

## 🎯 Benefits

### For Users
- ✅ **Seamless Experience**: Merchant account ready immediately after verification
- ✅ **No Extra Steps**: No need to manually create merchant profile
- ✅ **Pre-filled Data**: Business info populated from user profile

### For Platform
- ✅ **Higher Conversion**: Reduces friction in merchant onboarding
- ✅ **Consistent Data**: Standardized merchant account structure
- ✅ **Audit Trail**: Complete logging of account creation events

### for Admins
- ✅ **Automated Process**: Reduces manual merchant creation tasks
- ✅ **Monitoring**: Clear logs and audit trail
- ✅ **Control**: Merchants still require admin approval before activation

## 🔄 Future Enhancements

### Notification System
```python
def send_merchant_account_created_notification(merchant):
    # Send welcome email
    # Notify admin team
    # Create admin dashboard task
    pass
```

### Customizable Templates
```python
# Custom business name templates
business_name_template = "{first_name} {last_name} Business"
# OR
business_name_template = "{first_name}'s {category} Company"
```

### Integration Webhooks
```python
# Trigger external integrations when merchant is created
def trigger_external_webhooks(merchant):
    # Notify payment processors
    # Update CRM systems
    # Send to analytics platforms
    pass
```

---

## ✅ **Feature Status: PRODUCTION READY**

The auto merchant creation feature is fully implemented, tested, and ready for production use. It provides a seamless user experience while maintaining security and admin control over the merchant approval process.
