"""
URL configuration for pexilabs project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Landing pages (root)
    # path('', include('website.urls')),
    
    # Web authentication pages
    path('', include('authentication.auth_urls')),
    
    # Dashboard pages
    path('dashboard/', include('authentication.dashboard_urls')),
    
    # Checkout pages
    path('checkout/', include('checkout.urls')),
    
    # Payment processing
    path('', include('payments.urls')),
    path('payments/', include('payments.urls', namespace='payments')),  # Add this line
    
    # Shop functionality
    path('shop/', include('shop.urls')),
    
    # Django Admin (default)
    path('admin/', admin.site.urls),
    
    # Developer Documentation
    path('docs/', include('docs_urls')),
    
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
