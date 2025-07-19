# User Role-Based Dashboard System

## Overview
Implemented a comprehensive user role-based dashboard system that automatically redirects users to their appropriate dashboard based on their role and permissions upon login.

## User Roles & Dashboard Mapping

### 1. **Superuser** 
- **Role**: Django superuser (`is_superuser=True`)
- **Dashboard**: Django Admin (`/admin/`)
- **Access**: Full system access, highest priority

### 2. **Admin User**
- **Role**: `UserRole.ADMIN` (with or without `is_staff=True`)
- **Dashboard**: Admin Dashboard (`/dashboard/admin/`)
- **Access**: Comprehensive system overview, user management, merchant management

### 3. **Staff User**
- **Role**: `UserRole.STAFF` with `is_staff=True`
- **Dashboard**: Staff Dashboard (`/dashboard/staff/`)
- **Access**: Merchant management, integration monitoring

### 4. **Moderator User**
- **Role**: `UserRole.MODERATOR`
- **Dashboard**: Moderator Dashboard (`/dashboard/moderator/`)
- **Access**: Content moderation, user verification, limited admin functions

### 5. **Merchant User**
- **Role**: Any role with associated merchant account (`hasattr(user, 'merchant_account')`)
- **Dashboard**: Merchant Dashboard (`/dashboard/merchant/`)
- **Access**: Business-specific analytics, transaction management, integration status

### 6. **Regular User**
- **Role**: `UserRole.USER` (default)
- **Dashboard**: User Dashboard (`/dashboard/user/`)
- **Access**: Personal account management, merchant account creation

## Redirect Logic Implementation

### Enhanced Dashboard Redirect Function
Located in `authentication/dashboard_views.py`:

```python
@login_required
def dashboard_redirect(request):
    """Redirect to appropriate dashboard based on user role and permissions"""
    user = request.user
    
    # Priority-based routing:
    # 1. Superuser → Django Admin
    # 2. Staff users → Role-specific dashboards
    # 3. Merchant users → Merchant Dashboard
    # 4. Role-specific dashboards for non-staff
    # 5. Default → User Dashboard
```

### Login Redirect Integration
Updated `authentication/auth_views.py` to use the centralized redirect logic:

```python
# After successful login
return redirect('dashboard:dashboard_redirect')
```

### Landing Page Integration
Updated `authentication/landing_views.py` to redirect authenticated users:

```python
if request.user.is_authenticated:
    return redirect('dashboard:dashboard_redirect')
```

## Access Control

### Dashboard-Level Protection
Each dashboard view includes role-based access control:

- **Admin Dashboard**: Requires superuser OR admin role OR staff+admin
- **Staff Dashboard**: Requires staff role OR admin/staff roles
- **Moderator Dashboard**: Requires moderator role OR higher privileges
- **Merchant Dashboard**: Requires associated merchant account
- **User Dashboard**: Available to all authenticated users

### Security Features
- ✅ **@login_required** decorators on all dashboard views
- ✅ **Role verification** before granting access
- ✅ **Graceful error handling** with redirects to appropriate dashboards
- ✅ **Centralized redirect logic** for consistency

## URL Structure

```
/dashboard/                 → Automatic role-based redirect
/dashboard/admin/          → Admin Dashboard
/dashboard/staff/          → Staff Dashboard  
/dashboard/moderator/      → Moderator Dashboard
/dashboard/merchant/       → Merchant Dashboard
/dashboard/user/           → User Dashboard
```

## Templates Available

All dashboard templates are located in `templates/dashboard/`:
- `admin_dashboard.html` - Admin interface
- `staff_dashboard.html` - Staff management interface
- `moderator_dashboard.html` - Moderation interface
- `merchant_dashboard.html` - Business analytics interface
- `user_dashboard.html` - Personal account interface
- `base_dashboard.html` - Shared dashboard layout

## Benefits

### 1. **Automatic Role-Based Routing**
Users are automatically directed to their appropriate dashboard without manual navigation.

### 2. **Improved Security**
Role-based access control prevents unauthorized access to privileged dashboards.

### 3. **Better User Experience**
- No confusion about which interface to use
- Appropriate tools and information for each user type
- Seamless login-to-dashboard flow

### 4. **Scalable Architecture**
- Easy to add new roles and dashboards
- Centralized redirect logic simplifies maintenance
- Consistent access control patterns

### 5. **Flexible Permission System**
- Supports multiple ways to grant admin access (superuser, staff+admin role, admin role)
- Handles merchant users across different roles
- Graceful fallback to user dashboard

## Testing Results

✅ All dashboard URLs resolve correctly:
- Dashboard Redirect: `/dashboard/`
- Admin Dashboard: `/dashboard/admin/`
- Staff Dashboard: `/dashboard/staff/`
- Moderator Dashboard: `/dashboard/moderator/`
- Merchant Dashboard: `/dashboard/merchant/`
- User Dashboard: `/dashboard/user/`

✅ Role-based access control working
✅ Login redirects functional
✅ Landing page redirects functional
✅ Security controls in place

The system now provides a comprehensive, secure, and user-friendly dashboard experience tailored to each user's role and permissions.
