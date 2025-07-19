# PexiLabs Custom Authentication Service

A comprehensive Django-based authentication system with JWT tokens, email-based authentication, and support for user profiles with country and currency preferences.

## Features

### User Model
- **Email-based authentication** (no username required)
- **Custom user fields**:
  - `email` (unique, required)
  - `first_name` (required)
  - `last_name` (required)
  - `phone_number` (optional)
  - `role` (admin, user, moderator, staff)
  - `is_verified` (email verification status)
  - `is_active` (account status)
  - `last_login_at` (timestamp of last login)
  - `refresh_token` (JWT refresh token storage)
  - `country` (foreign key to Country model)
  - `preferred_currency` (foreign key to PreferredCurrency model)
  - `created_at` and `updated_at` (timestamps)

### Related Models
- **Country**: Stores country information with ISO codes and phone codes
- **PreferredCurrency**: Stores currency information with ISO codes and symbols
- **UserSession**: Tracks user sessions with IP addresses and user agents

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout

### User Profile
- `GET /api/auth/profile/` - Get user profile
- `PUT /api/auth/profile/` - Update user profile
- `PATCH /api/auth/profile/` - Partial update user profile
- `POST /api/auth/change-password/` - Change password

### Email Verification
- `POST /api/auth/verify-email/` - Verify email
- `POST /api/auth/resend-verification/` - Resend verification email

### Reference Data
- `GET /api/auth/countries/` - List all countries
- `GET /api/auth/currencies/` - List all active currencies

### Session Management
- `GET /api/auth/sessions/` - List user sessions
- `POST /api/auth/sessions/<uuid:session_id>/deactivate/` - Deactivate session

### Admin Only
- `GET /api/auth/users/` - List all users (admin/staff only)
- `GET /api/auth/stats/` - User statistics (admin/staff only)

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Apply Migrations
```bash
python manage.py migrate
```

### 3. Create Initial Data
```bash
python manage.py create_countries
python manage.py create_currencies
```

### 4. Create Superuser
```bash
python manage.py createsuperuser
```

### 5. Run Server
```bash
python manage.py runserver
```

## API Usage Examples

### User Registration
```bash
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "password": "securepassword123",
    "password_confirm": "securepassword123"
  }'
```

### User Login
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

### Get User Profile
```bash
curl -X GET http://127.0.0.1:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update User Profile
```bash
curl -X PUT http://127.0.0.1:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane",
    "last_name": "Smith",
    "phone_number": "+1987654321",
    "country_id": "country-uuid-here",
    "preferred_currency_id": "currency-uuid-here"
  }'
```

### Change Password
```bash
curl -X POST http://127.0.0.1:8000/api/auth/change-password/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "oldpassword123",
    "new_password": "newpassword123",
    "new_password_confirm": "newpassword123"
  }'
```

### List Countries
```bash
curl -X GET http://127.0.0.1:8000/api/auth/countries/
```

### List Currencies
```bash
curl -X GET http://127.0.0.1:8000/api/auth/currencies/
```

## Configuration

### Settings.py Configuration
The following settings are automatically configured:

```python
# Custom User Model
AUTH_USER_MODEL = 'authentication.CustomUser'

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'authentication.backends.EmailBackend',
    'authentication.backends.PhoneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}
```

## Authentication Backends

The system includes two custom authentication backends:

1. **EmailBackend**: Allows login with email and password
2. **PhoneBackend**: Allows login with phone number and password

## User Roles

The system supports the following user roles:
- `admin`: Full system access
- `staff`: Administrative access
- `moderator`: Content moderation access
- `user`: Regular user access (default)

## Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Validation**: Strong password requirements
- **Session Tracking**: Monitor user sessions and IP addresses
- **Email Verification**: Verify user email addresses
- **Role-based Access**: Control access based on user roles
- **CORS Protection**: Configure allowed origins for API access

## Database Schema

### CustomUser Table
- `id` (UUID, Primary Key)
- `email` (EmailField, Unique)
- `first_name` (CharField)
- `last_name` (CharField)
- `phone_number` (CharField, Optional)
- `role` (CharField with choices)
- `is_verified` (BooleanField)
- `is_active` (BooleanField)
- `is_staff` (BooleanField)
- `is_superuser` (BooleanField)
- `last_login_at` (DateTimeField, Optional)
- `refresh_token` (TextField, Optional)
- `country_id` (ForeignKey to Country, Optional)
- `preferred_currency_id` (ForeignKey to PreferredCurrency, Optional)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)

### Country Table
- `id` (UUID, Primary Key)
- `name` (CharField)
- `code` (CharField, ISO 3-letter code)
- `phone_code` (CharField, Optional)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)

### PreferredCurrency Table
- `id` (UUID, Primary Key)
- `name` (CharField)
- `code` (CharField, ISO 3-letter code)
- `symbol` (CharField)
- `is_active` (BooleanField)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)

### UserSession Table
- `id` (UUID, Primary Key)
- `user_id` (ForeignKey to CustomUser)
- `session_key` (CharField)
- `ip_address` (GenericIPAddressField, Optional)
- `user_agent` (TextField, Optional)
- `is_active` (BooleanField)
- `created_at` (DateTimeField)
- `expires_at` (DateTimeField)

## Admin Interface

The Django admin interface is fully configured for managing:
- Users with custom forms and fields
- Countries with search and filtering
- Currencies with status management
- User sessions with monitoring capabilities

Access the admin at: `http://127.0.0.1:8000/admin/`

## Testing

You can test the authentication system using:
- Django admin interface
- API endpoints with curl or Postman
- Frontend applications via CORS-enabled requests

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Ensure all packages from requirements.txt are installed
2. **Migration errors**: Run `python manage.py migrate` after making model changes
3. **CORS errors**: Update `CORS_ALLOWED_ORIGINS` in settings.py
4. **JWT errors**: Check token expiration and ensure proper Authorization header format

### Logs and Debugging

- Enable Django debug mode by setting `DEBUG = True` in settings.py
- Check console output for detailed error messages
- Use Django's built-in logging for production debugging

## Future Enhancements

Potential improvements for the authentication system:
- Two-factor authentication (2FA)
- Social media login integration
- Password reset via email
- Account lockout after failed attempts
- Audit logging for security events
- OAuth2 provider capabilities
