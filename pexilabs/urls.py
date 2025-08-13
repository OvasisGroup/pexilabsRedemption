
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from authentication.dashboard_views import dashboard_redirect
# from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Root redirect - redirect to user profile if logged in, /admin for admin users, else to login page
    path('', dashboard_redirect, name='root_redirect'),
    
    # Web authentication pages
    path('auth/', include('authentication.auth_urls')),
    
    # Dashboard pages
    path('dashboard/', include('authentication.dashboard_urls')),
    
    # Checkout pages
    path('checkout/', include('checkout.urls')),
    
    # Payment processing
    path('payments/', include('payments.urls', namespace='payments')),
    
    # Shop functionality
    path('shop/', include('shop.urls')),
    
    # Django Admin (default)
    path('admin/', admin.site.urls),
    
    # Developer Documentation
    path('docs/', include('documentation.urls')),
    
    # API endpoints - commented out temporarily
    # path('api/auth/', include('authentication.urls')),
    # path('api/transactions/', include('transactions.urls')),
    path('integrations/', include('integrations.urls')),
    
    # API Documentation URLs (commented out temporarily)
    # path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
