from django.urls import path
from . import views

app_name = 'documentation'

urlpatterns = [
    # Main API Documentation
    path('api/', views.api_documentation, name='api_documentation'),
    
    # Integration Guides
    path('integration/', views.integration_guides, name='integration_guides'),
    
    # SDK Documentation
    path('sdks/', views.sdk_documentation, name='sdk_documentation'),
    
    # Webhook Testing
    path('webhooks/', views.webhook_testing, name='webhook_testing'),
    path('webhooks/test-endpoint/', views.webhook_endpoint_test, name='webhook_endpoint_test'),
    
    # API Explorer
    path('explorer/', views.api_explorer, name='api_explorer'),
    
    # Placeholder for other documentation pages
    path('', views.placeholder_view, name='documentation_home'),
]