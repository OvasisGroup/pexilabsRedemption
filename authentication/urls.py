from django.urls import path
from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView, UserProfileView,
    ChangePasswordView, CountryListView, PreferredCurrencyListView,
    UserSessionsView, DeactivateSessionView, UserListView,
    GroupListView, RoleGroupListView, UserRoleManagementView,
    verify_email, resend_verification_email, user_stats,
    user_permissions, assign_user_role,
    # New OTP and Merchant views
    OTPVerificationView, ResendOTPView, MerchantCategoryListView,
    MerchantAccountView, CreateMerchantAccountView, MerchantListView,
    MerchantStatusUpdateView, merchant_stats,
    # App Key Generation views
    WhitelabelPartnerListCreateView, WhitelabelPartnerDetailView,
    generate_webhook_secret, AppKeyListCreateView, AppKeyDetailView,
    regenerate_app_key_secret, app_key_usage_stats, AppKeyUsageLogListView,
    partner_app_keys, verify_api_key
)

app_name = 'authentication'

urlpatterns = [
    # Authentication endpoints
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    
    # User profile endpoints
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Email verification endpoints
    path('verify-email/', verify_email, name='verify_email'),
    path('resend-verification/', resend_verification_email, name='resend_verification'),
    
    # Reference data endpoints
    path('countries/', CountryListView.as_view(), name='countries'),
    path('currencies/', PreferredCurrencyListView.as_view(), name='currencies'),
    
    # Session management endpoints
    path('sessions/', UserSessionsView.as_view(), name='user_sessions'),
    path('sessions/<uuid:session_id>/deactivate/', DeactivateSessionView.as_view(), name='deactivate_session'),
    
    # Admin endpoints
    path('users/', UserListView.as_view(), name='user_list'),
    path('stats/', user_stats, name='user_stats'),
    
    # Role and Group management endpoints
    path('groups/', GroupListView.as_view(), name='groups'),
    path('role-groups/', RoleGroupListView.as_view(), name='role_groups'),
    path('users/<uuid:id>/role/', UserRoleManagementView.as_view(), name='user_role_management'),
    path('users/<uuid:user_id>/assign-role/', assign_user_role, name='assign_user_role'),
    path('permissions/', user_permissions, name='user_permissions'),
    
    # OTP verification endpoints
    path('verify-otp/', OTPVerificationView.as_view(), name='verify_otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend_otp'),
    
    # Merchant endpoints
    path('merchant-categories/', MerchantCategoryListView.as_view(), name='merchant_categories'),
    path('merchant-account/', MerchantAccountView.as_view(), name='merchant_account'),
    path('create-merchant/', CreateMerchantAccountView.as_view(), name='create_merchant'),
    
    # Admin merchant endpoints
    path('merchants/', MerchantListView.as_view(), name='merchants_list'),
    path('merchants/<uuid:merchant_id>/status/', MerchantStatusUpdateView.as_view(), name='merchant_status_update'),
    path('merchant-stats/', merchant_stats, name='merchant_stats'),
    
    # === App Key Generation Module URLs ===
    
    # Whitelabel Partner endpoints
    path('partners/', WhitelabelPartnerListCreateView.as_view(), name='whitelabel_partners'),
    path('partners/<uuid:pk>/', WhitelabelPartnerDetailView.as_view(), name='whitelabel_partner_detail'),
    path('partners/<uuid:partner_pk>/webhook-secret/', generate_webhook_secret, name='generate_webhook_secret'),
    path('partners/<uuid:partner_pk>/app-keys/', partner_app_keys, name='partner_app_keys'),
    
    # App Key endpoints
    path('app-keys/', AppKeyListCreateView.as_view(), name='app_keys'),
    path('app-keys/<uuid:pk>/', AppKeyDetailView.as_view(), name='app_key_detail'),
    path('app-keys/<uuid:key_pk>/regenerate/', regenerate_app_key_secret, name='regenerate_app_key_secret'),
    path('app-keys/<uuid:key_pk>/stats/', app_key_usage_stats, name='app_key_usage_stats'),
    path('app-keys/<uuid:key_pk>/logs/', AppKeyUsageLogListView.as_view(), name='app_key_usage_logs'),
    
    # Public endpoint for API key verification
    path('verify-api-key/', verify_api_key, name='verify_api_key'),
]
