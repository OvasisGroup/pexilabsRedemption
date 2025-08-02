# Integration Testing Guide

## Overview

The merchant dashboard now includes a comprehensive integration testing interface that allows merchants to test their active integrations directly from the dashboard. This feature helps merchants verify that their integrations are working efficiently and troubleshoot any issues.

## Features

### 1. Integration Testing Dashboard

The merchant dashboard (`/dashboard/merchant/`) now includes an "Integration Testing" section that displays:

- **Active Integrations**: Shows all enabled integrations with their current status
- **Real-time Testing**: Allows merchants to test integrations with a single click
- **Test Results**: Displays detailed test results with success/failure status
- **Integration Statistics**: Shows request counts, success rates, and last usage
- **Health Monitoring**: Visual indicators for integration health status

### 2. Supported Integration Tests

#### UBA Bank Integration
- **Checkout Intent Test**: Creates a test payment intent to verify the integration
- **Connection Test**: Verifies the API connection and authentication
- **Payment Flow Test**: Tests the complete payment workflow

#### Other Integrations
- **CyberSource**: Basic connectivity and configuration tests
- **Corefy**: Service availability and authentication tests
- **Custom Integrations**: Extensible framework for additional integration tests

## How to Use

### Accessing Integration Testing

1. **Login** to your merchant account
2. **Navigate** to the merchant dashboard (`/dashboard/merchant/`)
3. **Scroll down** to the "Integration Testing" section
4. **View** your active integrations

### Testing an Integration

1. **Locate** the integration you want to test
2. **Click** the "Test Checkout" button (for UBA Bank) or relevant test button
3. **Wait** for the test to complete (usually 2-5 seconds)
4. **Review** the test results in the "Test Results" section below

### Understanding Test Results

#### Success Indicators
- ✅ **Green status**: Test passed successfully
- 📊 **Response data**: Detailed API response information
- 🔗 **Payment URL**: Generated payment link (for checkout tests)

#### Failure Indicators
- ❌ **Red status**: Test failed
- 🚨 **Error details**: Specific error messages and troubleshooting information
- 📋 **Debug info**: Technical details for developers

## API Endpoints

### Test Integration API

**Endpoint**: `POST /dashboard/api/test-integration/`

**Request Body**:
```json
{
  "integration_type": "uba_bank",
  "test_type": "checkout",
  "amount": 100.00,
  "currency": "USD",
  "customer_email": "test@example.com",
  "description": "Integration Test Payment"
}
```

**Response (Success)**:
```json
{
  "success": true,
  "message": "UBA checkout test completed successfully",
  "data": {
    "payment_url": "https://uba.example.com/pay/abc123",
    "reference": "TEST_REF_123",
    "status": "test_passed"
  }
}
```

**Response (Error)**:
```json
{
  "success": false,
  "error": "UBA checkout test failed",
  "details": {
    "error_code": "INVALID_CREDENTIALS",
    "message": "Authentication failed"
  }
}
```

### Integration Health Check API

**Endpoint**: `GET /dashboard/api/integration-health/`

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "integration-uuid",
      "name": "UBA Kenya Pay",
      "provider": "UBA Bank",
      "type": "uba_bank",
      "is_healthy": true,
      "success_rate": 98.5,
      "total_requests": 1250,
      "successful_requests": 1231,
      "last_used": "2024-12-19T08:45:00Z",
      "status": "active"
    }
  ],
  "summary": {
    "total_integrations": 3,
    "healthy_integrations": 2,
    "average_success_rate": 96.7
  }
}
```

## Integration Testing Features

### 1. Real-time Status Updates
- Integration status updates automatically
- Visual indicators show current health
- Success rates calculated in real-time

### 2. Test History
- Last 5 test results are displayed
- Timestamps for each test
- Detailed success/failure information

### 3. Auto-refresh
- Integration status refreshes every 5 minutes
- Manual refresh button available
- Real-time health monitoring

### 4. Error Handling
- Comprehensive error messages
- Troubleshooting guidance
- Debug information for developers

## Troubleshooting

### Common Issues

#### 1. "No active integration found"
- **Cause**: Integration is not enabled or configured
- **Solution**: Go to Integration Settings and enable the integration

#### 2. "Authentication failed"
- **Cause**: Invalid API credentials
- **Solution**: Check and update API keys in integration settings

#### 3. "Connection timeout"
- **Cause**: Network issues or service unavailability
- **Solution**: Check internet connection and try again later

#### 4. "Test failed with unknown error"
- **Cause**: Various technical issues
- **Solution**: Contact support with the error details

### Getting Help

1. **Check Error Details**: Click on error details in test results
2. **Review Integration Settings**: Ensure all configurations are correct
3. **Contact Support**: Use the support channels with test result details
4. **Check Documentation**: Review integration-specific documentation

## Security Considerations

### Test Data
- All tests use sandbox/test environments
- No real money transactions are processed
- Test data is automatically cleaned up

### API Security
- All API calls require authentication
- CSRF protection enabled
- Rate limiting applied

### Data Privacy
- Test results are only visible to the merchant
- Sensitive data is masked in logs
- Test data is not stored permanently

## Development Notes

### Adding New Integration Tests

1. **Update Service Class**: Add test methods to the integration service
2. **Update API Handler**: Add test logic in `test_integration_api` view
3. **Update Frontend**: Add test buttons and result handling
4. **Update Documentation**: Document the new test capabilities

### File Structure

```
├── authentication/
│   ├── dashboard_views.py          # Integration testing API endpoints
│   └── dashboard_urls.py           # URL patterns for testing APIs
├── templates/dashboard/
│   └── merchant_dashboard.html     # Integration testing UI
├── integrations/
│   ├── services.py                 # Integration service classes
│   ├── uba_usage.py               # UBA-specific testing logic
│   └── views.py                    # Integration management views
└── INTEGRATION_TESTING_GUIDE.md   # This documentation
```

### JavaScript Functions

- `testUBACheckout(integrationId)`: Tests UBA checkout functionality
- `showTestResult(result)`: Displays test results
- `refreshIntegrationStatus()`: Refreshes integration status

## Future Enhancements

### Planned Features

1. **Automated Testing**: Schedule regular integration tests
2. **Performance Monitoring**: Track response times and performance metrics
3. **Alert System**: Notifications for integration failures
4. **Batch Testing**: Test multiple integrations simultaneously
5. **Historical Analytics**: Long-term integration performance tracking

### Integration Roadmap

1. **Enhanced UBA Testing**: More comprehensive test scenarios
2. **CyberSource Testing**: Full payment flow testing
3. **Corefy Testing**: Complete integration test suite
4. **Custom Integration Support**: Framework for third-party integrations

## Conclusion

The integration testing functionality provides merchants with powerful tools to ensure their payment integrations are working correctly. This helps reduce payment failures, improve customer experience, and maintain high service reliability.

For technical support or feature requests, please contact the development team or submit an issue through the appropriate channels.