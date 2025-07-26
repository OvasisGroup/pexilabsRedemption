from django.urls import path
from . import auth_views

app_name = 'auth'

urlpatterns = [
    # Web-based authentication pages
    path('register/', auth_views.register_page, name='register_page'),
    path('login/', auth_views.login_page, name='login_page'),
    path('logout/', auth_views.logout_page, name='logout_page'),
    
    # OTP verification
    path('verify/<uuid:user_id>/', auth_views.verify_otp, name='verify_otp'),
    path('resend-otp/<uuid:user_id>/', auth_views.resend_otp, name='resend_otp'),
    path('verification-help/', auth_views.verification_help, name='verification_help'),
]
