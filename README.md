# PexiLabs Fintech Platform

A comprehensive Django-based fintech platform featuring authentication, payment processing, merchant onboarding, and multi-gateway payment integrations. This system provides a complete solution for payment processing with support for UBA Bank, CyberSource, and Corefy payment gateways.

## 🚀 Features

### 🔐 Authentication System
- **Email-based authentication** with JWT tokens
- **Custom user model** with comprehensive profile management
- **Role-based access control** (admin, staff, moderator, user)
- **Email OTP verification** for secure account activation
- **Session management** with IP tracking and device monitoring
- **Business name integration** for merchant account creation

### 💳 Payment Processing
- **Multi-gateway support**: UBA Bank, CyberSource, Corefy
- **Transaction management** with comprehensive tracking
- **Refund processing** and payment reversals
- **Payment links** for easy customer payments
- **Webhook handling** for real-time payment notifications
- **Checkout system** with customizable payment forms

### 🏢 Merchant Management
- **Automatic merchant account creation** during registration
- **Merchant verification** and document upload
- **Business profile management** with category classification
- **Bank details management** for payouts
- **Merchant dashboard** with analytics and reporting

### 🌍 Multi-Currency & Localization
- **51 countries** with ISO codes and phone prefixes
- **30 currencies** with symbols and exchange rates
- **Merchant categories** for business classification
- **Localization support** for international operations

### 📊 Admin & Analytics
- **Comprehensive Django admin** with advanced filtering
- **User statistics** and merchant analytics
- **Transaction reporting** and financial insights
- **System health monitoring** and integration status

### 🔗 API Documentation
- **Interactive Swagger UI** at `/api/docs/`
- **ReDoc documentation** at `/api/redoc/`
- **OpenAPI 3.0 schema** with comprehensive endpoint documentation
- **Authentication examples** and code samples

## 🏗️ Project Architecture

### Directory Structure
```
pexilabsRedemption/
├── authentication/          # User authentication & management
│   ├── models.py            # CustomUser, Country, Currency models
│   ├── serializers.py       # API serializers
│   ├── views.py             # Authentication endpoints
│   ├── backends.py          # Custom auth backends
│   └── management/commands/ # Data seeding commands
├── transactions/            # Payment processing
│   ├── models.py            # Transaction, Refund models
│   ├── views.py             # Payment endpoints
│   └── serializers.py       # Transaction serializers
├── integrations/            # Payment gateway integrations
│   ├── models.py            # Integration models
│   ├── services.py          # Gateway service classes
│   └── views.py             # Integration endpoints
├── checkout/                # Checkout system
│   ├── models.py            # Checkout models
│   ├── views.py             # Checkout endpoints
│   └── templates/           # Checkout templates
├── shop/                    # E-commerce functionality
│   ├── models.py            # Product, Cart models
│   └── management/commands/ # Product seeding
├── payments/                # Payment processing logic
├── templates/               # HTML templates
│   ├── auth/                # Authentication templates
│   ├── dashboard/           # Dashboard templates
│   └── landing/             # Landing page templates
├── static/                  # Static files (CSS, JS, images)
├── docs/                    # Project documentation
├── tests/                   # Test scripts and utilities
└── pexilabs/               # Django project settings
    ├── settings.py          # Main configuration
    ├── urls.py              # URL routing
    └── wsgi.py              # WSGI configuration
```

### Core Components

#### 1. Authentication System (`authentication/`)
- **CustomUser Model**: Extended user model with business fields
- **JWT Authentication**: Token-based API authentication
- **Email OTP**: Secure email verification system
- **Role Management**: Admin, staff, moderator, user roles
- **Session Tracking**: IP and device monitoring

#### 2. Payment Processing (`transactions/`)
- **Transaction Management**: Payment tracking and processing
- **Multi-Gateway Support**: UBA, CyberSource, Corefy
- **Refund System**: Automated refund processing
- **Payment Links**: Shareable payment URLs
- **Webhook Handling**: Real-time payment notifications

#### 3. Integration Layer (`integrations/`)
- **UBA Bank Service**: Kenya banking integration
- **CyberSource Service**: Global payment processing
- **Corefy Service**: Payment orchestration platform
- **Webhook Management**: Secure webhook processing
- **API Rate Limiting**: Request throttling and retry logic

#### 4. Merchant Management
- **Automatic Onboarding**: Business registration with merchant creation
- **Document Upload**: KYC and verification documents
- **Bank Details**: Payout account management
- **Category Classification**: Business type categorization
- **Verification Workflow**: Multi-step merchant approval

### Database Schema Overview

#### Core Tables
- `authentication_customuser`: User accounts and profiles
- `authentication_country`: Country reference data (51 countries)
- `authentication_preferredcurrency`: Currency data (30 currencies)
- `transactions_transaction`: Payment transactions
- `integrations_merchant`: Merchant accounts
- `integrations_merchantcategory`: Business categories

#### Key Relationships
- Users → Countries (many-to-one)
- Users → Currencies (many-to-one)
- Users → Merchants (one-to-one, optional)
- Transactions → Users (many-to-one)
- Transactions → Merchants (many-to-one)

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

## 📋 Prerequisites

Before installing the PexiLabs platform, ensure you have the following installed:

- **Python 3.8+** (recommended: Python 3.9 or 3.10)
- **pip** (Python package manager)
- **PostgreSQL 12+** (recommended) or SQLite for development
- **Git** for version control
- **Virtual environment** tool (venv, virtualenv, or conda)

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd pexilabsRedemption
```

### 2. Create Virtual Environment
```bash
# Using venv (recommended)
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment Configuration

#### 4.1 Create Environment File
```bash
cp .env.example .env
```

#### 4.2 Configure Database (Choose One)

**Option A: PostgreSQL (Recommended for Production)**
```bash
# Install PostgreSQL and create database
createdb pexilabs

# Update .env file:
DB_ENGINE=django.db.backends.postgresql
DB_NAME=pexilabs
DB_USER=your_postgres_user
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
```

**Option B: SQLite (Development Only)**
```bash
# Update .env file:
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

#### 4.3 Configure Essential Settings
```bash
# Generate a secure secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Update .env file with generated key:
SECRET_KEY=your-generated-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 5. Database Setup

#### 5.1 Apply Migrations
```bash
python manage.py migrate
```

#### 5.2 Seed Reference Data (Required)
```bash
# Create countries (51 countries with ISO codes)
python manage.py create_countries

# Create currencies (30 major currencies)
python manage.py create_currencies

# Create merchant categories (13 business categories)
python manage.py create_merchant_categories

# Setup user role groups
python manage.py setup_role_groups
```

#### 5.3 Alternative: Use Seed Script
```bash
# Make script executable
chmod +x scripts/seed.sh

# Run all seeding commands
./scripts/seed.sh
```

### 6. Create Superuser
```bash
python manage.py createsuperuser
# Follow prompts to create admin account
```

### 7. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 8. Run Development Server
```bash
python manage.py runserver
# Server will start at http://127.0.0.1:8000/
```

## 🔧 Post-Installation Verification

### 1. Verify System Health
```bash
# Run system checks
python manage.py check

# Test database connectivity
python manage.py shell -c "from django.db import connection; print('Database connected:', connection.ensure_connection() is None)"
```

### 2. Access Key URLs
- **Main Application**: http://127.0.0.1:8000/
- **Django Admin**: http://127.0.0.1:8000/admin/
- **API Documentation**: http://127.0.0.1:8000/api/docs/
- **ReDoc Documentation**: http://127.0.0.1:8000/api/redoc/
- **API Schema**: http://127.0.0.1:8000/api/schema/

### 3. Verify Reference Data
```bash
# Check countries
curl http://127.0.0.1:8000/api/auth/countries/ | jq '.count'
# Should return: 51

# Check currencies
curl http://127.0.0.1:8000/api/auth/currencies/ | jq '.count'
# Should return: 30

# Check merchant categories
curl http://127.0.0.1:8000/api/integrations/merchant-categories/ | jq '.count'
# Should return: 13
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

## 🚀 Production Deployment

### 1. Production Environment Setup

#### 1.1 Environment Variables
```bash
# Security Settings
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (PostgreSQL recommended)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=pexilabs_prod
DB_USER=pexilabs_user
DB_PASSWORD=secure_password
DB_HOST=your-db-host
DB_PORT=5432

# Email Configuration
EMAIL_HOST=smtp.yourdomain.com
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=your-email-password

# Security Headers
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
```

#### 1.2 Production Checklist
```bash
# Run production checks
python manage.py check --deploy

# Collect static files
python manage.py collectstatic --noinput

# Apply migrations
python manage.py migrate

# Create cache tables (if using database cache)
python manage.py createcachetable
```

### 2. Payment Gateway Configuration

#### 2.1 UBA Bank Integration
```bash
UBA_BASE_URL=https://api.uba-kenya.com
UBA_ACCESS_TOKEN=your-production-token
UBA_SANDBOX_MODE=False
```

#### 2.2 CyberSource Integration
```bash
CYBERSOURCE_BASE_URL=https://api.cybersource.com
CYBERSOURCE_MERCHANT_ID=your-merchant-id
CYBERSOURCE_SANDBOX_MODE=False
```

#### 2.3 Corefy Integration
```bash
COREFY_BASE_URL=https://api.corefy.com
COREFY_API_KEY=your-production-api-key
COREFY_SANDBOX_MODE=False
```

## 🔧 Development Guidelines

### 1. Code Style & Standards
- Follow **PEP 8** Python style guidelines
- Use **Black** for code formatting: `black .`
- Use **isort** for import sorting: `isort .`
- Run **flake8** for linting: `flake8 .`

### 2. Testing
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test authentication
python manage.py test transactions
python manage.py test integrations

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### 3. Database Migrations
```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Check migration status
python manage.py showmigrations

# Rollback migrations (if needed)
python manage.py migrate app_name migration_name
```

### 4. Adding New Features

#### 4.1 Creating New Apps
```bash
python manage.py startapp new_app_name

# Add to INSTALLED_APPS in settings.py
# Create models, views, serializers
# Add URL patterns
# Create and run migrations
```

#### 4.2 API Development
- Use **Django REST Framework** serializers
- Implement proper **authentication** and **permissions**
- Add **API documentation** with drf-spectacular
- Follow **RESTful** conventions

## 🐛 Troubleshooting

### Common Issues

#### 1. Installation Issues
```bash
# ModuleNotFoundError
pip install --upgrade pip
pip install -r requirements.txt

# Permission errors on macOS/Linux
sudo chown -R $(whoami) /path/to/project

# Virtual environment issues
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. Database Issues
```bash
# Migration conflicts
python manage.py migrate --fake-initial

# Reset migrations (development only)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
python manage.py makemigrations
python manage.py migrate

# Database connection errors
# Check database credentials in .env
# Ensure database server is running
# Test connection: python manage.py dbshell
```

#### 3. API Issues
```bash
# CORS errors
# Update CORS_ALLOWED_ORIGINS in .env
# Check CORS middleware in settings.py

# JWT token errors
# Check token expiration
# Verify Authorization header format: "Bearer <token>"
# Regenerate tokens if needed

# 404 errors
# Check URL patterns in urls.py
# Verify app is in INSTALLED_APPS
# Check for trailing slashes in URLs
```

#### 4. Payment Integration Issues
```bash
# Test integration connectivity
python manage.py shell
>>> from integrations.services import UBAService
>>> service = UBAService()
>>> service.test_connection()

# Check webhook endpoints
curl -X POST http://127.0.0.1:8000/api/webhooks/uba/ \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Verify API credentials
# Check sandbox vs production URLs
# Validate webhook signatures
```

### 5. Performance Issues
```bash
# Database query optimization
# Use select_related() and prefetch_related()
# Add database indexes
# Monitor slow queries

# Memory usage
# Check for memory leaks
# Optimize large data processing
# Use pagination for large datasets
```

### Debugging Tools

#### 1. Django Debug Toolbar (Development)
```bash
pip install django-debug-toolbar
# Add to INSTALLED_APPS and MIDDLEWARE
# Access at /__debug__/
```

#### 2. Logging Configuration
```python
# Add to settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🔮 Future Enhancements

### Planned Features
- **Two-factor authentication (2FA)** with SMS/TOTP
- **Social media login** (Google, Facebook, Apple)
- **Advanced fraud detection** and risk scoring
- **Multi-tenant architecture** for white-label solutions
- **Real-time notifications** with WebSocket support
- **Advanced analytics** and business intelligence
- **Mobile SDK** for iOS and Android
- **Blockchain integration** for cryptocurrency payments

### Technical Improvements
- **Microservices architecture** migration
- **Redis caching** for improved performance
- **Elasticsearch** for advanced search capabilities
- **Docker containerization** for easier deployment
- **Kubernetes orchestration** for scalability
- **GraphQL API** alongside REST
- **Automated testing** with CI/CD pipelines
- **Security auditing** and compliance tools

## 🔒 Security & Compliance

### Security Features
- **JWT Token Authentication** with automatic refresh
- **Password Validation** with strength requirements
- **Email Verification** for account activation
- **Session Management** with IP tracking
- **CORS Protection** for API access control
- **CSRF Protection** for form submissions
- **SQL Injection Prevention** through Django ORM
- **XSS Protection** with template escaping

### Data Protection
- **Encryption at Rest** for sensitive data
- **HTTPS Enforcement** in production
- **Secure Cookie Settings** for session management
- **Input Validation** and sanitization
- **Rate Limiting** for API endpoints
- **Audit Logging** for security events

### Compliance Considerations
- **PCI DSS** compliance for payment processing
- **GDPR** compliance for EU users
- **Data Retention** policies
- **Privacy Controls** and user consent
- **Financial Regulations** compliance

## 📞 Support & Documentation

### Getting Help
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive API docs at `/api/docs/`
- **Code Examples**: Sample implementations in `/tests/`
- **Integration Guides**: Payment gateway setup instructions

### Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes and add tests
4. Run the test suite: `python manage.py test`
5. Submit a pull request with detailed description

### Development Team
- **Backend**: Django REST Framework, PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript
- **Integrations**: Payment gateways and banking APIs
- **DevOps**: Docker, CI/CD, monitoring

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Django Community** for the excellent framework
- **Django REST Framework** for powerful API tools
- **Payment Gateway Partners** for integration support
- **Open Source Contributors** for various packages used

---

**PexiLabs Fintech Platform** - Empowering businesses with seamless payment solutions.

For more information, visit our [documentation](http://127.0.0.1:8000/api/docs/) or contact our development team.
