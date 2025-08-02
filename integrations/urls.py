from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    # Integration management
    path('', views.IntegrationListView.as_view(), name='integration-list'),
    path('<uuid:id>/', views.IntegrationDetailView.as_view(), name='integration-detail'),
    path('bank/<uuid:integration__id>/', views.BankIntegrationDetailView.as_view(), name='bank-integration-detail'),
    
    # Merchant integrations (ListCreateAPIView handles both list and create)
    path('merchant/', views.MerchantIntegrationListView.as_view(), name='merchant-integration-list-create'),
    path('merchant/<uuid:id>/', views.MerchantIntegrationDetailView.as_view(), name='merchant-integration-detail'),
    
    # UBA specific endpoints
    path('uba/payment-page/', views.uba_create_payment_page, name='uba-create-payment-page'),
    path('uba/payment-status/<str:payment_id>/', views.uba_get_payment_status, name='uba-payment-status'),
    path('uba/account-inquiry/', views.uba_account_inquiry, name='uba-account-inquiry'),
    path('uba/fund-transfer/', views.uba_fund_transfer, name='uba-fund-transfer'),
    path('uba/balance-inquiry/', views.uba_balance_inquiry, name='uba-balance-inquiry'),
    path('uba/transaction-history/', views.uba_transaction_history, name='uba-transaction-history'),
    path('uba/bill-payment/', views.uba_bill_payment, name='uba-bill-payment'),
    path('uba/webhook/', views.uba_webhook_handler, name='uba-webhook'),
    path('uba/test-connection/', views.uba_test_connection, name='uba-test-connection'),
    
    # UBA API Key endpoints (for merchant API key authentication)
    path('uba/api/checkout-intent/', views.uba_create_checkout_intent, name='uba-api-checkout-intent'),
    path('uba/api/payment-status/<str:payment_id>/', views.uba_get_payment_status_api, name='uba-api-payment-status'),
    path('uba/api/integration-info/', views.uba_integration_info, name='uba-api-integration-info'),
    path('api/checkout/session/', views.create_checkout_session, name='api-checkout-session'),
    
    # CyberSource specific endpoints
    path('cybersource/payment/', views.cybersource_create_payment, name='cybersource-create-payment'),
    path('cybersource/capture/', views.cybersource_capture_payment, name='cybersource-capture-payment'),
    path('cybersource/refund/', views.cybersource_refund_payment, name='cybersource-refund-payment'),
    path('cybersource/payment-status/<str:payment_id>/', views.cybersource_get_payment_status, name='cybersource-payment-status'),
    path('cybersource/customer/', views.cybersource_create_customer, name='cybersource-create-customer'),
    path('cybersource/token/', views.cybersource_create_token, name='cybersource-create-token'),
    path('cybersource/webhook/', views.cybersource_webhook_handler, name='cybersource-webhook'),
    path('cybersource/test-connection/', views.cybersource_test_connection, name='cybersource-test-connection'),
    
    # Corefy specific endpoints
    path('corefy/payment-intent/', views.corefy_create_payment_intent, name='corefy-create-payment-intent'),
    path('corefy/confirm-payment/', views.corefy_confirm_payment, name='corefy-confirm-payment'),
    path('corefy/payment-status/<str:payment_id>/', views.corefy_get_payment_status, name='corefy-payment-status'),
    path('corefy/refund/', views.corefy_create_refund, name='corefy-create-refund'),
    path('corefy/customer/', views.corefy_create_customer, name='corefy-create-customer'),
    path('corefy/customer/<str:customer_id>/', views.corefy_get_customer, name='corefy-get-customer'),
    path('corefy/payment-method/', views.corefy_create_payment_method, name='corefy-create-payment-method'),
    path('corefy/customer/<str:customer_id>/payment-methods/', views.corefy_get_payment_methods, name='corefy-get-payment-methods'),
    path('corefy/supported-methods/', views.corefy_get_supported_payment_methods, name='corefy-supported-methods'),
    path('corefy/webhook/', views.corefy_webhook_handler, name='corefy-webhook'),
    path('corefy/test-connection/', views.corefy_test_connection, name='corefy-test-connection'),
    
    # Statistics and monitoring
    path('stats/', views.integration_stats, name='integration-stats'),
    path('health/', views.integration_health, name='integration-health'),
    
    # Enhanced Integration Management
    path('providers/', views.integration_providers_list, name='integration-providers-list'),
    path('providers/<uuid:integration_id>/', views.integration_provider_detail, name='integration-provider-detail'),
    path('configure/<uuid:integration_id>/', views.configure_merchant_integration, name='configure-merchant-integration'),
    path('statistics/', views.integration_statistics, name='integration-statistics'),
    
    # Utility endpoints
    path('type-choices/', views.integration_type_choices, name='integration-type-choices'),
    path('status-choices/', views.integration_status_choices, name='integration-status-choices'),
    
    # API calls and webhooks
    path('api-calls/', views.IntegrationAPICallListView.as_view(), name='api-calls-list'),
    path('webhooks/', views.IntegrationWebhookListView.as_view(), name='webhooks-list'),
    
    # Settings and configuration
    path('settings/', views.integration_settings_view, name='integration-settings'),
    path('api/configure/', views.configure_integration_api, name='configure-integration-api'),
    path('api/toggle/<uuid:integration_id>/', views.toggle_integration_api, name='toggle-integration-api'),
    path('api/remove/<uuid:integration_id>/', views.remove_integration_api, name='remove-integration-api'),
]
