from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# URL patterns for transactions app
urlpatterns = [
    # Payment Gateway URLs
    path('gateways/', views.PaymentGatewayListCreateView.as_view(), name='gateway-list-create'),
    path('gateways/<uuid:pk>/', views.PaymentGatewayDetailView.as_view(), name='gateway-detail'),
    
    # Transaction URLs
    path('transactions/', views.TransactionListCreateView.as_view(), name='transaction-list-create'),
    path('transactions/<uuid:pk>/', views.TransactionDetailView.as_view(), name='transaction-detail'),
    path('transactions/<uuid:transaction_id>/refund/', views.create_refund, name='transaction-refund'),
    
    # Payment Link URLs
    path('payment-links/', views.PaymentLinkListCreateView.as_view(), name='paymentlink-list-create'),
    path('payment-links/<uuid:pk>/', views.PaymentLinkDetailView.as_view(), name='paymentlink-detail'),
    
    # Statistics and Analytics
    path('stats/', views.transaction_stats, name='transaction-stats'),
    
    # Choice endpoints for API documentation
    path('choices/payment-methods/', views.payment_method_choices, name='payment-method-choices'),
    path('choices/transaction-types/', views.transaction_type_choices, name='transaction-type-choices'),
    path('choices/transaction-statuses/', views.transaction_status_choices, name='transaction-status-choices'),
]
