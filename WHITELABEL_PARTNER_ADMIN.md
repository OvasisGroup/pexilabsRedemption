# WhitelabelPartner Django Admin Documentation

## Overview

The WhitelabelPartner model is now fully integrated into the Django admin interface with comprehensive management features. This document outlines the admin interface capabilities and how to use them.

## Admin Interface Features

### List View

The WhitelabelPartner admin list view displays:

| Column | Description |
|--------|-------------|
| **Name** | Partner company name |
| **Code** | Unique partner code |
| **Contact Email** | Primary contact email |
| **Is Active** | Active status (✓/✗) |
| **Is Verified** | Verification status (✓/✗) |
| **Active Keys** | Number of active API keys |
| **Daily API Limit** | Daily API call limit |
| **Today's Usage** | Current day API usage with percentage |
| **Created At** | Registration date |

### Enhanced Features

#### 1. **Real-time API Usage Tracking**
- Shows today's API usage vs. daily limit
- Color-coded indicators:
  - 🟢 Green: < 60% usage
  - 🟠 Orange: 60-80% usage  
  - 🔴 Red: > 80% usage

#### 2. **Comprehensive Filtering**
- Filter by active status
- Filter by verification status
- Filter by creation date
- Filter by verification date

#### 3. **Advanced Search**
Search across:
- Partner name
- Partner code
- Contact email
- Business registration number

## Detail View

### Organized Fieldsets

#### **Basic Information**
- Name, Code, Contact Email
- Contact Phone, Website URL

#### **Business Details** (Collapsible)
- Business Address
- Business Registration Number
- Tax ID

#### **Integration Settings**
- Allowed Domains
- Webhook URL (clickable link)
- Webhook Secret

#### **API Limits & Quotas**
- Daily API Limit
- Monthly API Limit
- Concurrent Connections Limit

#### **Status & Verification**
- Active Status
- Verification Status
- Verification Notes
- Verified By (admin user)
- Verification Date

#### **Statistics** (Collapsible)
- Active API Keys Count
- Today's API Usage

#### **Timestamps** (Collapsible)
- Created At
- Updated At

### Inline Management

#### **App Keys Inline**
Manage API keys directly from the partner page:
- View all associated API keys
- See key details (public key, masked secret)
- Monitor usage statistics
- Check expiration dates
- View today's usage per key

## Admin Actions

### Available Actions

1. **Verify Partners**
   - Bulk verify selected partners
   - Sets verification timestamp
   - Records admin user who verified

2. **Activate Partners**
   - Bulk activate selected partners
   - Enables API access

3. **Deactivate Partners**
   - Bulk deactivate selected partners
   - Suspends API access

4. **Generate Webhook Secrets**
   - Generate new webhook secrets
   - Updates all selected partners

5. **View API Statistics** ⭐ *New*
   - Shows comprehensive usage statistics
   - Displays active keys count
   - Shows total API calls today

### Using Admin Actions

1. Select partners using checkboxes
2. Choose action from dropdown
3. Click "Go" button
4. Confirm action if prompted

## Security Features

### Read-only Fields
- Creation timestamp
- Update timestamp
- Verification timestamp
- API keys count
- Today's usage statistics

### Masked Sensitive Data
- API key secrets are masked (•••••••••)
- Only shows necessary characters for identification

### Audit Trail
- Tracks who verified partners
- Records verification timestamps
- Logs all admin actions

## Quick Access

### From Partner List
- Click partner name to edit details
- Use filters to find specific partners
- Use search to locate by email/code

### From Partner Detail
- View/edit all partner information
- Manage API keys inline
- Generate new webhook secrets
- View usage statistics

## Usage Scenarios

### 1. **Partner Onboarding**
1. Navigate to WhitelabelPartner admin
2. Click "Add whitelabel partner"
3. Fill required information
4. Save partner
5. Use "Verify Partners" action
6. Partner can now generate API keys

### 2. **Monitoring API Usage**
1. View "Today's Usage" column
2. Check color indicators for high usage
3. Use "View API Statistics" action for details
4. Monitor individual key usage in inline

### 3. **Partner Management**
1. Use filters to find partners by status
2. Bulk activate/deactivate as needed
3. Update limits and quotas
4. Manage webhook configurations

### 4. **Troubleshooting**
1. Check partner verification status
2. Verify API limits and usage
3. Check webhook configuration
4. Review API key status in inline

## Integration with API Keys

### Automatic Management
- API keys appear in inline when partner is selected
- Real-time usage statistics
- Status indicators for expired/revoked keys

### Key Operations
- View public keys
- Monitor usage patterns
- Check expiration dates
- Track last usage

## Best Practices

### 1. **Regular Monitoring**
- Check daily usage patterns
- Monitor for unusual activity
- Review partner verification status

### 2. **Security Management**
- Regularly rotate webhook secrets
- Verify partner details before activation
- Monitor API usage for abuse

### 3. **Partner Communication**
- Keep contact information updated
- Document verification notes
- Maintain webhook URLs

## API Integration

The admin interface integrates with:
- API key authentication system
- Usage logging and statistics
- Webhook management
- Rate limiting system

## Access Control

### Required Permissions
- `authentication.view_whitelabelpartner` - View partners
- `authentication.add_whitelabelpartner` - Add partners
- `authentication.change_whitelabelpartner` - Edit partners
- `authentication.delete_whitelabelpartner` - Delete partners

### Staff Access
- Django admin staff status required
- Appropriate permissions must be assigned
- Superusers have full access

The WhitelabelPartner admin interface provides comprehensive partner management with real-time monitoring, security features, and streamlined workflows for efficient partner administration.
