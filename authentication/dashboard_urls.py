from django.urls import path
from . import dashboard_views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard routing
    path('', dashboard_views.dashboard_redirect, name='dashboard_redirect'),
    
    # Role-based dashboards
    path('admin/', dashboard_views.admin_dashboard, name='admin_dashboard'),
    path('merchant/', dashboard_views.merchant_dashboard, name='merchant_dashboard'),
    path('user/', dashboard_views.user_dashboard, name='user_dashboard'),
    path('staff/', dashboard_views.staff_dashboard, name='staff_dashboard'),
    path('moderator/', dashboard_views.moderator_dashboard, name='moderator_dashboard'),
    
    # Merchant verification
    path('merchant-verifier/', dashboard_views.merchant_verifier_dashboard, name='merchant_verifier_dashboard'),
    path('merchant-verifier/<uuid:merchant_id>/', dashboard_views.merchant_verification_detail, name='merchant_verification_detail'),
    
    # Merchant transactions
    path('merchant/transactions/', dashboard_views.merchant_transactions_view, name='merchant_transactions'),
    
    # Merchant documents
    path('merchant/documents/', dashboard_views.merchant_documents_view, name='merchant_documents'),
    
    # Merchant bank details
    path('merchant/bank-details/', dashboard_views.merchant_bank_details_view, name='merchant_bank_details'),
    
    # Transaction API endpoints
    path('api/transactions/', dashboard_views.create_transaction_api, name='create_transaction_api'),
    path('api/transactions/<uuid:transaction_id>/', dashboard_views.transaction_detail_api, name='transaction_detail_api'),
    path('api/transactions/<uuid:transaction_id>/refund/', dashboard_views.refund_transaction_api, name='refund_transaction_api'),
    path('api/payment-links/', dashboard_views.create_payment_link_api, name='create_payment_link_api'),
    
    # Document API endpoints
    path('api/documents/', dashboard_views.upload_document_api, name='upload_document_api'),
    path('api/documents/<uuid:document_id>/', dashboard_views.delete_document_api, name='delete_document_api'),
    
    # Profile management
    path('merchant/profile/', dashboard_views.merchant_profile_view, name='merchant_profile'),
    
    # Profile API endpoints
    path('api/profile/personal/', dashboard_views.update_personal_info_api, name='update_personal_info_api'),
    path('api/profile/business/', dashboard_views.update_business_info_api, name='update_business_info_api'),
    path('api/profile/password/', dashboard_views.change_password_api, name='change_password_api'),
    
    # API Key management
    path('merchant/api-keys/', dashboard_views.merchant_api_keys_view, name='merchant_api_keys'),
    
    # API Key API endpoints
    path('api/api-keys/', dashboard_views.create_api_key_api, name='create_api_key_api'),
    path('api/api-keys/list/', dashboard_views.list_api_keys_api, name='list_api_keys_api'),
    
    # Integration Testing API endpoints
    path('api/test-integration/', dashboard_views.test_integration_api, name='test_integration_api'),
    path('api/create-test-checkout/', dashboard_views.create_test_checkout_api, name='create_test_checkout_api'),
    path('api/integration-health/', dashboard_views.integration_health_check_api, name='integration_health_check_api'),
    path('api/api-keys/<uuid:key_id>/revoke/', dashboard_views.revoke_api_key_api, name='revoke_api_key_api'),
    path('api/api-keys/<uuid:key_id>/regenerate/', dashboard_views.regenerate_api_key_api, name='regenerate_api_key_api'),
    
    # Bank Details API endpoints
    path('api/bank-details/', dashboard_views.update_bank_details_api, name='update_bank_details_api'),
    
    # Notification API endpoints
    path('api/notifications/', dashboard_views.get_notifications_api, name='get_notifications_api'),
    path('api/notifications/<uuid:notification_id>/read/', dashboard_views.mark_notification_read_api, name='mark_notification_read_api'),
    path('api/notifications/<uuid:notification_id>/dismiss/', dashboard_views.dismiss_notification_api, name='dismiss_notification_api'),
    path('api/notifications/mark-all-read/', dashboard_views.mark_all_notifications_read_api, name='mark_all_notifications_read_api'),
]
