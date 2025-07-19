from django.urls import path
from .views import landing_page

urlpatterns = [
    # Authentication endpoints
    path('', landing_page, name='home'),
    ]