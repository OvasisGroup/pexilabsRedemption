from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Template-based (non-API) views
    path('create/', views.create_payment_link_view, name='create_payment_link'),
    path('link/<slug:slug>/', views.payment_link_view, name='payment_link_detail'),

    # API endpoints
    path('api/payment-links/', views.api_create_payment_link, name='api_create_payment_link'),
    path('api/payment-links/<slug:slug>/', views.api_payment_link_detail, name='api_payment_link_detail'),
]