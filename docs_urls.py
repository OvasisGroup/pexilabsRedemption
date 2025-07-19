from django.urls import path
import docs_views

app_name = 'docs'

urlpatterns = [
    # Main API Documentation
    path('api/', docs_views.api_documentation, name='api_documentation'),
    
    # Integration Guides
    path('integration/', docs_views.integration_guides, name='integration_guides'),
    
    # SDK Documentation
    path('sdks/', docs_views.sdk_documentation, name='sdk_documentation'),
    
    # Webhook Testing
    path('webhooks/', docs_views.webhook_testing, name='webhook_testing'),
    path('webhooks/test-endpoint/', docs_views.webhook_endpoint_test, name='webhook_endpoint_test'),
    
    # API Explorer
    path('explorer/', docs_views.api_explorer, name='api_explorer'),
]
