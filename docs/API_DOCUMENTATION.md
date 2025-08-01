# API Documentation

## Authentication Endpoints

### Register User
**POST** `/auth/register/`

**Request Body:**
```json
{
    "email": "user@example.com",
    "password": "securepassword",
    "firstName": "John",
    "lastName": "Doe",
    "phoneNumber": "+1234567890",
    "countryId": 1,
    "prefferedCurrencyId": 1,
    "role": "USER"
}
```

**Response:**
```json
{
    "user": {
        "id": "uuid",
        "email": "user@example.com",
        "firstName": "John",
        "lastName": "Doe",
        "role": "USER",
        "isVerified": false,
        "isActive": true
    },
    "message": "User registered successfully. Please check your email to verify your account."
}
```

### Login User
**POST** `/auth/login/`

**Request Body:**
```json
{
    "email": "user@example.com",
    "password": "securepassword"
}
```

**Response:**
```json
{
    "access": "jwt_access_token",
    "refresh": "jwt_refresh_token",
    "user": {
        "id": "uuid",
        "email": "user@example.com",
        "firstName": "John",
        "lastName": "Doe",
        "role": "USER",
        "isVerified": true,
        "lastLoginAt": "2023-01-01T12:00:00Z"
    }
}
```

### Get User Profile
**GET** `/auth/profile/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "id": "uuid",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "phoneNumber": "+1234567890",
    "role": "USER",
    "isVerified": true,
    "isActive": true,
    "lastLoginAt": "2023-01-01T12:00:00Z",
    "country": {
        "id": 1,
        "name": "United States",
        "code": "US"
    },
    "prefferedCurrency": {
        "id": 1,
        "name": "US Dollar",
        "code": "USD",
        "symbol": "$"
    },
    "createdAt": "2023-01-01T10:00:00Z",
    "updatedAt": "2023-01-01T12:00:00Z"
}
```

### Update User Profile
**PUT** `/auth/profile/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
    "firstName": "Jane",
    "lastName": "Smith",
    "phoneNumber": "+1987654321",
    "countryId": 2,
    "prefferedCurrencyId": 2
}
```

## Role Management Endpoints

### Get User Role
**GET** `/auth/users/{user_id}/role/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "user_id": "uuid",
    "role": "USER",
    "groups": [
        {
            "id": 1,
            "name": "User",
            "permissions": ["view_profile", "change_password"]
        }
    ]
}
```

### Assign User Role
**POST** `/auth/users/{user_id}/assign-role/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
    "role": "MANAGER"
}
```

**Response:**
```json
{
    "message": "Role updated successfully",
    "user": {
        "id": "uuid",
        "role": "MANAGER",
        "groups": [
            {
                "id": 1,
                "name": "User"
            },
            {
                "id": 2,
                "name": "Manager"
            }
        ]
    }
}
```

## Reference Data Endpoints

### Get Countries
**GET** `/auth/countries/`

**Response:**
```json
[
    {
        "id": 1,
        "name": "United States",
        "code": "US"
    },
    {
        "id": 2,
        "name": "Canada",
        "code": "CA"
    }
]
```

### Get Currencies
**GET** `/auth/currencies/`

**Response:**
```json
[
    {
        "id": 1,
        "name": "US Dollar",
        "code": "USD",
        "symbol": "$"
    },
    {
        "id": 2,
        "name": "Euro",
        "code": "EUR",
        "symbol": "€"
    }
]
```

## Admin Endpoints

### Get User Statistics
**GET** `/auth/stats/`

**Headers:**
```
Authorization: Bearer <admin_access_token>
```

**Response:**
```json
{
    "total_users": 150,
    "verified_users": 120,
    "active_users": 140,
    "users_by_role": {
        "ADMIN": 2,
        "MANAGER": 8,
        "USER": 135,
        "GUEST": 5
    },
    "users_by_country": {
        "US": 80,
        "CA": 30,
        "UK": 25,
        "Other": 15
    }
}
```

### List All Users
**GET** `/auth/users/`

**Headers:**
```
Authorization: Bearer <admin_access_token>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)
- `role`: Filter by role
- `is_active`: Filter by active status
- `is_verified`: Filter by verification status

**Response:**
```json
{
    "count": 150,
    "next": "http://localhost:8000/auth/users/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "email": "user@example.com",
            "firstName": "John",
            "lastName": "Doe",
            "role": "USER",
            "isVerified": true,
            "isActive": true,
            "lastLoginAt": "2023-01-01T12:00:00Z",
            "createdAt": "2023-01-01T10:00:00Z"
        }
    ]
}
```

## Session Management

### Get User Sessions
**GET** `/auth/sessions/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
[
    {
        "id": "session_uuid",
        "device": "Chrome on macOS",
        "ip_address": "192.168.1.1",
        "location": "New York, US",
        "isActive": true,
        "lastActivity": "2023-01-01T12:00:00Z",
        "createdAt": "2023-01-01T10:00:00Z"
    }
]
```

### Deactivate Session
**POST** `/auth/sessions/{session_id}/deactivate/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "message": "Session deactivated successfully"
}
```

## Error Responses

### Validation Error (400)
```json
{
    "error": "Validation failed",
    "details": {
        "email": ["This field is required."],
        "password": ["Password must be at least 8 characters long."]
    }
}
```

### Authentication Error (401)
```json
{
    "error": "Authentication failed",
    "message": "Invalid credentials"
}
```

### Permission Error (403)
```json
{
    "error": "Permission denied",
    "message": "You do not have permission to perform this action"
}
```

### Not Found Error (404)
```json
{
    "error": "Not found",
    "message": "User not found"
}
```

## Role-Based Access Control

### User Roles and Permissions

#### ADMIN
- Full access to all endpoints
- Can manage all users and their roles
- Access to admin statistics and user management

#### MANAGER
- Can view and manage users in their scope
- Access to user statistics
- Cannot modify admin users

#### USER
- Can access their own profile and update it
- Can change their password
- Can manage their sessions

#### GUEST
- Limited read-only access
- Cannot modify any data
- Temporary access level

### Group Inheritance

- **ADMIN**: Inherits Admin + Manager + User groups
- **MANAGER**: Inherits Manager + User groups  
- **USER**: Gets User group only
- **GUEST**: Gets Guest group only

This inheritance can be customized through the RoleGroup model in the admin interface.
