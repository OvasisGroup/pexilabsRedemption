from django.urls import path
from django.http import HttpResponse

app_name = 'docs'

# Temporary placeholder view
def placeholder_view(request):
    return HttpResponse("Documentation coming soon!")

urlpatterns = [
    # Main API Documentation
    path('api/', placeholder_view, name='api_documentation'),
    
    # Integration Guides
    path('integration/', placeholder_view, name='integration_guides'),
    
    # SDK Documentation
    path('sdks/', placeholder_view, name='sdk_documentation'),
    
    # Webhook Testing
    path('webhooks/', placeholder_view, name='webhook_testing'),
    path('webhooks/test-endpoint/', placeholder_view, name='webhook_endpoint_test'),
    
    # API Explorer
    path('explorer/', placeholder_view, name='api_explorer'),
]
