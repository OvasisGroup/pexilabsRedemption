from django.urls import path
from . import views

urlpatterns = [
    # API endpoints
    path('api/payment-gateways/', views.PaymentGatewayListCreateView.as_view(), name='api-payment-gateway-list'),
    path('api/payment-gateways/<int:pk>/', views.PaymentGatewayDetailView.as_view(), name='api-payment-gateway-detail'),
    path('api/transactions/', views.TransactionListCreateView.as_view(), name='api-transaction-list'),
    path('api/transactions/<int:pk>/', views.TransactionDetailView.as_view(), name='api-transaction-detail'),
    path('api/transactions/<int:transaction_id>/refund/', views.create_refund, name='api-transaction-refund'),
    path('api/payment-links/', views.PaymentLinkListCreateView.as_view(), name='api-payment-link-list'),
    path('api/payment-links/<int:pk>/', views.PaymentLinkDetailView.as_view(), name='api-payment-link-detail'),
    path('api/transaction-stats/', views.transaction_stats, name='api-transaction-stats'),
    path('api/payment-method-choices/', views.payment_method_choices, name='api-payment-method-choices'),
    path('api/transaction-type-choices/', views.transaction_type_choices, name='api-transaction-type-choices'),
    path('api/transaction-status-choices/', views.transaction_status_choices, name='api-transaction-status-choices'),

    # Template endpoints
    path('transactions/', views.transaction_list_view, name='transaction-list'),
    path('transactions/<int:pk>/', views.transaction_detail_view, name='transaction-detail'),
    path('payment-links/', views.payment_link_list_view, name='payment-link-list'),
]
