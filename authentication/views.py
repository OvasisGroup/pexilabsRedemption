from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import login, logout
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Group
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import (
    CustomUser, Country, PreferredCurrency, UserSession, RoleGroup, 
    EmailOTP, Merchant, MerchantCategory, MerchantDocument,
    WhitelabelPartner, AppKey, AppKeyUsageLog
)
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    ChangePasswordSerializer, CountrySerializer, PreferredCurrencySerializer,
    UserSessionSerializer, UserListSerializer, GroupSerializer, 
    RoleGroupSerializer, UserRoleManagementSerializer,
    UserRegistrationWithMerchantSerializer, OTPVerificationSerializer,
    ResendOTPSerializer, MerchantSerializer, MerchantCategorySerializer,
    MerchantStatusUpdateSerializer, MerchantDocumentSerializer,
    MerchantDocumentListSerializer, MerchantWithDocumentsSerializer,
    DocumentUploadSerializer, WhitelabelPartnerSerializer,
    WhitelabelPartnerCreateSerializer, AppKeySerializer, AppKeyCreateSerializer,
    AppKeyUpdateSerializer, AppKeyUsageLogSerializer, AppKeyStatsSerializer,
    AppKeyRegenerateSerializer, WebhookSecretRegenerateSerializer
)
from .utils import send_otp_email, send_merchant_creation_email


@extend_schema_view(
    post=extend_schema(
        tags=['Authentication'],
        summary='User Registration with Optional Merchant Account',
        description="""
        Register a new user with optional merchant account creation.
        
        **Features:**
        - User registration with email and password
        - Optional business name for automatic merchant account creation  
        - OTP generation and email sending for verification
        - Merchant account creation with business details
        - Support for multiple registration scenarios
        
        **Registration Scenarios:**
        1. **Simple Registration**: Basic user registration without merchant account
        2. **Business Registration**: Include business_name + create_merchant_account=true for automatic merchant creation
        3. **Detailed Merchant Registration**: Provide full merchant_data for comprehensive business account
        
        **Post-Registration Flow:**
        1. User receives OTP via email
        2. User verifies OTP using /verify-otp/ endpoint
        3. User gains access to authenticated endpoints
        4. Merchant account (if created) is pending approval
        """,
        request=UserRegistrationWithMerchantSerializer,
        responses={
            201: OpenApiExample(
                'Success Response',
                summary='Successful registration',
                description='User successfully registered with optional merchant account',
                value={
                    "message": "User registered successfully. Please check your email for OTP verification. Merchant account has been created and is pending review.",
                    "user": {
                        "id": "uuid-here",
                        "email": "user@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "is_verified": False,
                        "role": "user"
                    },
                    "email_verification_required": True,
                    "otp_sent": True,
                    "merchant_account_created": True,
                    "merchant_id": "merchant-uuid-here"
                }
            ),
            400: OpenApiExample(
                'Validation Error',
                summary='Invalid input data',
                description='Request contains validation errors',
                value={
                    "email": ["A user with this email already exists."],
                    "password": ["This password is too common."]
                }
            )
        },
        examples=[
            OpenApiExample(
                'Simple Registration',
                summary='Basic user registration',
                description='Register user without merchant account',
                value={
                    "email": "user@example.com",
                    "password": "SecurePassword123!",
                    "password_confirm": "SecurePassword123!",
                    "first_name": "John",
                    "last_name": "Doe",
                    "phone_number": "+1234567890"
                }
            ),
            OpenApiExample(
                'Business Registration',
                summary='Registration with business name',
                description='Register user with automatic merchant account creation',
                value={
                    "email": "business@example.com",
                    "password": "SecurePassword123!",
                    "password_confirm": "SecurePassword123!",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "phone_number": "+1234567890",
                    "business_name": "Jane's Coffee Shop",
                    "create_merchant_account": True
                }
            ),
            OpenApiExample(
                'Detailed Merchant Registration',
                summary='Registration with full merchant data',
                description='Register user with comprehensive merchant account details',
                value={
                    "email": "merchant@example.com",
                    "password": "SecurePassword123!",
                    "password_confirm": "SecurePassword123!",
                    "first_name": "Bob",
                    "last_name": "Wilson",
                    "phone_number": "+1234567890",
                    "create_merchant_account": True,
                    "merchant_data": {
                        "business_name": "Wilson's Premium Services",
                        "business_email": "contact@wilsonservices.com",
                        "business_phone": "+1234567890",
                        "business_address": "123 Business Ave, City, State 12345",
                        "description": "Premium business services provider",
                        "category": "category-uuid-here"
                    }
                }
            )
        ]
    )
)
class UserRegistrationView(APIView):
    """Enhanced user registration view with OTP verification and merchant onboarding"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationWithMerchantSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Prepare response data
            response_data = {
                'message': 'User registered successfully. Please check your email for OTP verification.',
                'user': UserProfileSerializer(user).data,
                'email_verification_required': True,
                'otp_sent': True
            }
            
            # Add merchant info if created
            if hasattr(user, '_merchant_created') and user._merchant_created:
                response_data['merchant_account_created'] = True
                response_data['merchant_id'] = str(user._merchant_id)
                response_data['message'] += ' Merchant account has been created and is pending review.'
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@extend_schema_view(
    post=extend_schema(
        tags=['Authentication'],
        summary='User Login',
        description="""
        Authenticate user with email and password.
        
        **Features:**
        - Email-based authentication
        - JWT token generation (access + refresh)
        - Session creation and tracking
        - Last login timestamp update
        - User profile information in response
        
        **Authentication Flow:**
        1. Provide email and password
        2. Receive JWT tokens (access + refresh)
        3. Use access token for authenticated requests
        4. Use refresh token to get new access tokens
        
        **Token Usage:**
        - Include access token in Authorization header: `Bearer <access_token>`
        - Access tokens expire in 60 minutes
        - Refresh tokens expire in 7 days
        """,
        request=UserLoginSerializer,
        responses={
            200: OpenApiExample(
                'Success Response',
                summary='Successful login',
                description='User successfully authenticated',
                value={
                    "message": "Login successful",
                    "user": {
                        "id": "uuid-here",
                        "email": "user@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "role": "user",
                        "is_verified": True,
                        "last_login_at": "2025-07-04T10:30:00Z"
                    },
                    "tokens": {
                        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                    },
                    "session": {
                        "id": "session-uuid",
                        "expires_at": "2025-07-18T10:30:00Z"
                    }
                }
            ),
            400: OpenApiExample(
                'Invalid Credentials',
                summary='Authentication failed',
                description='Invalid email or password provided',
                value={
                    "non_field_errors": ["Invalid email or password."]
                }
            ),
            401: OpenApiExample(
                'Unverified Account',
                summary='Account not verified',
                description='User account exists but email not verified',
                value={
                    "detail": "Please verify your email address before logging in."
                }
            )
        },
        examples=[
            OpenApiExample(
                'Login Request',
                summary='Standard login',
                description='Login with email and password',
                value={
                    "email": "user@example.com",
                    "password": "SecurePassword123!"
                }
            )
        ]
    )
)
class UserLoginView(APIView):
    """User login view"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Update last login
            user.last_login_at = timezone.now()
            user.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Store refresh token
            user.refresh_token = str(refresh)
            user.save()
            
            # Create session
            session = UserSession.objects.create(
                user=user,
                session_key=str(refresh),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                expires_at=timezone.now() + timezone.timedelta(days=7)
            )
            
            login(request, user)
            
            return Response({
                'message': 'Login successful',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh)
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserLogoutView(APIView):
    """User logout view"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Invalidate refresh token
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Clear user's refresh token
            request.user.refresh_token = None
            request.user.save()
            
            # Deactivate user sessions
            UserSession.objects.filter(user=request.user, is_active=True).update(is_active=False)
            
            logout(request)
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': 'Something went wrong during logout'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(RetrieveUpdateAPIView):
    """User profile view"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Change password view"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # Invalidate all existing sessions
            UserSession.objects.filter(user=user, is_active=True).update(is_active=False)
            
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CountryListView(ListAPIView):
    """List all countries"""
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [permissions.AllowAny]


class PreferredCurrencyListView(ListAPIView):
    """List all currencies"""
    queryset = PreferredCurrency.objects.filter(is_active=True)
    serializer_class = PreferredCurrencySerializer
    permission_classes = [permissions.AllowAny]


class UserSessionsView(ListAPIView):
    """List user sessions"""
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user).order_by('-created_at')


class DeactivateSessionView(APIView):
    """Deactivate a specific session"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, session_id):
        session = get_object_or_404(
            UserSession, 
            id=session_id, 
            user=request.user
        )
        session.is_active = False
        session.save()
        
        return Response({
            'message': 'Session deactivated successfully'
        }, status=status.HTTP_200_OK)


class UserListView(ListAPIView):
    """List all users (admin only)"""
    queryset = CustomUser.objects.all().select_related('country', 'preferred_currency')
    serializer_class = UserListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Only allow admin users to view all users
        if self.request.user.role in ['admin', 'staff']:
            return super().get_queryset()
        return CustomUser.objects.none()


class GroupListView(ListAPIView):
    """List all groups"""
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Only allow admin/staff users to view groups
        if self.request.user.role in ['admin', 'staff']:
            return super().get_queryset()
        return Group.objects.none()


class RoleGroupListView(ListAPIView):
    """List role group mappings"""
    queryset = RoleGroup.objects.all().prefetch_related('groups')
    serializer_class = RoleGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Only allow admin/staff users to view role mappings
        if self.request.user.role in ['admin', 'staff']:
            return super().get_queryset()
        return RoleGroup.objects.none()


class UserRoleManagementView(RetrieveUpdateAPIView):
    """Manage user roles (admin only)"""
    serializer_class = UserRoleManagementSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        # Only allow admin users to manage roles
        if self.request.user.role == 'admin':
            return CustomUser.objects.all()
        elif self.request.user.role == 'staff':
            # Staff can only manage users and moderators
            return CustomUser.objects.filter(role__in=['user', 'moderator'])
        return CustomUser.objects.none()
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Check if current user can manage the target user's role
        if not request.user.can_manage_role(instance.role):
            return Response({
                'error': 'You do not have permission to manage this user\'s role'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if current user can assign the new role
        new_role = request.data.get('role')
        if new_role and not request.user.can_manage_role(new_role):
            return Response({
                'error': f'You do not have permission to assign the role: {new_role}'
            }, status=status.HTTP_403_FORBIDDEN)
        
        return super().update(request, *args, **kwargs)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_email(request):
    """Verify user email (placeholder for email verification logic)"""
    # In a real implementation, you would verify a token sent via email
    user = request.user
    user.is_verified = True
    user.save()
    
    return Response({
        'message': 'Email verified successfully'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def resend_verification_email(request):
    """Resend verification email (placeholder)"""
    # In a real implementation, you would send a verification email
    return Response({
        'message': 'Verification email sent'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """Get user statistics (admin only)"""
    if request.user.role not in ['admin', 'staff']:
        return Response({
            'error': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    stats = {
        'total_users': CustomUser.objects.count(),
        'verified_users': CustomUser.objects.filter(is_verified=True).count(),
        'active_users': CustomUser.objects.filter(is_active=True).count(),
        'users_by_role': {},
        'active_sessions': UserSession.objects.filter(is_active=True).count(),
    }
    
    # Get users by role
    from django.db.models import Count
    role_stats = CustomUser.objects.values('role').annotate(count=Count('id'))
    for stat in role_stats:
        stats['users_by_role'][stat['role']] = stat['count']
    
    return Response(stats, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_permissions(request):
    """Get current user's permissions"""
    user = request.user
    
    # Get all permissions through groups and direct assignments
    permissions_data = []
    
    # Get permissions from groups
    for group in user.groups.all():
        for perm in group.permissions.all():
            permissions_data.append({
                'name': perm.name,
                'codename': perm.codename,
                'source': f'Group: {group.name}',
                'content_type': perm.content_type.model
            })
    
    # Get direct user permissions
    for perm in user.user_permissions.all():
        permissions_data.append({
            'name': perm.name,
            'codename': perm.codename,
            'source': 'Direct assignment',
            'content_type': perm.content_type.model
        })
    
    return Response({
        'user': {
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'groups': [group.name for group in user.groups.all()]
        },
        'permissions': permissions_data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def assign_user_role(request, user_id):
    """Assign role to a user (admin only)"""
    if request.user.role not in ['admin', 'staff']:
        return Response({
            'error': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        target_user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    new_role = request.data.get('role')
    if not new_role:
        return Response({
            'error': 'Role is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if current user can manage the target user and assign the new role
    if not request.user.can_manage_role(target_user.role) or not request.user.can_manage_role(new_role):
        return Response({
            'error': 'You do not have permission to perform this action'
        }, status=status.HTTP_403_FORBIDDEN)
    
    old_role = target_user.role
    target_user.role = new_role
    target_user.save()  # This will trigger group reassignment
    
    return Response({
        'message': f'User role changed from {old_role} to {new_role}',
        'user': UserRoleManagementSerializer(target_user).data
    }, status=status.HTTP_200_OK)


# New OTP and Merchant Views

@extend_schema_view(
    post=extend_schema(
        tags=['OTP Verification'],
        summary='Verify Email OTP',
        description="""
        Verify the OTP code sent to user's email address.
        
        **Features:**
        - Email OTP verification for registration
        - Automatic user verification on successful OTP validation
        - JWT token generation after verification
        - Session creation for authenticated access
        
        **Verification Flow:**
        1. User receives OTP via email after registration
        2. User submits email and OTP code to this endpoint
        3. System validates OTP (6-digit code, not expired, not used)
        4. User account is marked as verified
        5. JWT tokens are generated for immediate access
        6. User session is created
        
        **OTP Validation Rules:**
        - Must be exactly 6 digits
        - Must not be expired (valid for 10 minutes)
        - Must not be already used
        - Must match the email address
        """,
        request=OTPVerificationSerializer,
        responses={
            200: OpenApiExample(
                'Success Response',
                summary='OTP verified successfully',
                description='Email verified and user logged in',
                value={
                    "message": "Email verified successfully. You are now logged in.",
                    "user": {
                        "id": "uuid-here",
                        "email": "user@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "is_verified": True,
                        "role": "user"
                    },
                    "tokens": {
                        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                    },
                    "session": {
                        "id": "session-uuid",
                        "expires_at": "2025-07-18T10:30:00Z"
                    }
                }
            ),
            400: OpenApiExample(
                'Invalid OTP',
                summary='OTP validation failed',
                description='Invalid, expired, or already used OTP',
                value={
                    "non_field_errors": ["Invalid or expired OTP code."]
                }
            ),
            404: OpenApiExample(
                'User Not Found',
                summary='Email not found',
                description='No user found with provided email',
                value={
                    "email": ["User with this email does not exist."]
                }
            )
        },
        examples=[
            OpenApiExample(
                'OTP Verification',
                summary='Verify OTP code',
                description='Submit email and 6-digit OTP code',
                value={
                    "email": "user@example.com",
                    "otp_code": "123456"
                }
            )
        ]
    )
)
class OTPVerificationView(APIView):
    """Verify OTP for email verification"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            otp_instance = serializer.validated_data['otp_instance']
            
            # Mark user as verified for registration OTP
            if otp_instance.purpose == 'registration':
                user.is_verified = True
                user.save()
                
                # Generate tokens after successful verification
                refresh = RefreshToken.for_user(user)
                access_token = refresh.access_token
                
                # Store refresh token
                user.refresh_token = str(refresh)
                user.save()
                
                # Create session
                session = UserSession.objects.create(
                    user=user,
                    session_key=str(refresh),
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    expires_at=timezone.now() + timezone.timedelta(days=7)
                )
                
                return Response({
                    'message': 'Email verified successfully. You are now logged in.',
                    'user': UserProfileSerializer(user).data,
                    'tokens': {
                        'access': str(access_token),
                        'refresh': str(refresh)
                    }
                }, status=status.HTTP_200_OK)
            
            return Response({
                'message': 'OTP verified successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ResendOTPView(APIView):
    """Resend OTP for email verification"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.user
            purpose = serializer.validated_data.get('purpose', 'registration')
            
            # Generate new OTP
            otp_instance = EmailOTP.generate_otp(user, purpose=purpose)
            
            # Send email
            if send_otp_email(user, otp_instance, purpose=purpose):
                return Response({
                    'message': 'OTP sent successfully to your email address'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Failed to send OTP email'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=extend_schema(
        tags=['Reference Data'],
        summary='List Merchant Categories',
        description="""
        Retrieve all active merchant categories available for business registration.
        
        **Features:**
        - Lists all active merchant categories
        - No authentication required
        - Supports pagination
        - Used for merchant account creation during registration
        
        **Usage:**
        - Call this endpoint to get available categories
        - Use category ID when creating merchant accounts
        - Categories include retail, healthcare, technology, etc.
        
        **Categories Include:**
        - Retail, Food & Beverage, Healthcare, Technology
        - Professional Services, Education, Entertainment
        - Transportation, Hospitality, Beauty & Wellness
        - E-commerce, Non-profit, and more
        """,
        responses={
            200: OpenApiExample(
                'Success Response',
                summary='List of merchant categories',
                description='Paginated list of active merchant categories',
                value={
                    "count": 13,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": "uuid-here",
                            "name": "Technology",
                            "code": "technology",
                            "description": "Software, hardware, and technology services",
                            "is_active": True,
                            "created_at": "2025-07-04T00:00:00Z",
                            "updated_at": "2025-07-04T00:00:00Z"
                        },
                        {
                            "id": "uuid-here",
                            "name": "Retail",
                            "code": "retail", 
                            "description": "Physical and online retail stores",
                            "is_active": True,
                            "created_at": "2025-07-04T00:00:00Z",
                            "updated_at": "2025-07-04T00:00:00Z"
                        }
                    ]
                }
            )
        }
    )
)
class MerchantCategoryListView(ListAPIView):
    """List all merchant categories"""
    queryset = MerchantCategory.objects.filter(is_active=True)
    serializer_class = MerchantCategorySerializer
    permission_classes = [permissions.AllowAny]


@extend_schema_view(
    get=extend_schema(
        tags=['Merchant Management'],
        summary='Get Merchant Account',
        description="""
        Retrieve the authenticated user's merchant account information.
        
        **Authentication Required:** Yes (Bearer token)
        
        **Features:**
        - Get complete merchant account details
        - Includes business information, status, and verification details
        - Shows bank account information (if provided)
        - Displays category and contact information
        
        **Access Control:**
        - Only the merchant account owner can access their data
        - Admin users can access any merchant account via admin endpoints
        """,
        responses={
            200: OpenApiExample(
                'Success Response',
                summary='Merchant account details',
                description='Complete merchant account information',
                value={
                    "id": "merchant-uuid",
                    "user": {
                        "id": "user-uuid",
                        "email": "merchant@example.com",
                        "first_name": "John",
                        "last_name": "Doe"
                    },
                    "business_name": "John's Coffee Shop",
                    "business_email": "contact@johnscoffee.com",
                    "business_phone": "+1234567890",
                    "business_address": "123 Main St, City, State 12345",
                    "category": {
                        "id": "category-uuid",
                        "name": "Food & Beverage",
                        "code": "food_beverage"
                    },
                    "status": "approved",
                    "is_verified": True,
                    "created_at": "2025-07-04T00:00:00Z"
                }
            ),
            401: OpenApiExample(
                'Unauthorized',
                summary='Authentication required',
                description='Valid JWT token required',
                value={
                    "detail": "Authentication credentials were not provided."
                }
            ),
            404: OpenApiExample(
                'Not Found',
                summary='No merchant account',
                description='User does not have a merchant account',
                value={
                    "detail": "Merchant account not found"
                }
            )
        }
    ),
    put=extend_schema(
        tags=['Merchant Management'],
        summary='Update Merchant Account',
        description="""
        Update the authenticated user's merchant account information.
        
        **Authentication Required:** Yes (Bearer token)
        
        **Updatable Fields:**
        - Business name, email, phone, address
        - Website URL and description
        - Bank account information
        - Business registration number
        
        **Restrictions:**
        - Cannot change verification status
        - Cannot change category (contact admin)
        - Some fields may require re-verification
        """,
        request=MerchantSerializer,
        responses={
            200: OpenApiExample(
                'Success Response',
                summary='Merchant account updated',
                description='Updated merchant account information',
                value={
                    "id": "merchant-uuid",
                    "business_name": "John's Premium Coffee",
                    "business_email": "premium@johnscoffee.com",
                    "website_url": "https://johnscoffee.com",
                    "status": "approved",
                    "updated_at": "2025-07-04T10:30:00Z"
                }
            ),
            400: OpenApiExample(
                'Validation Error',
                summary='Invalid data',
                description='Request contains validation errors',
                value={
                    "business_email": ["Enter a valid email address."]
                }
            )
        }
    ),
    patch=extend_schema(
        tags=['Merchant Management'],
        summary='Partially Update Merchant Account',
        description="""
        Partially update specific fields of the merchant account.
        
        **Authentication Required:** Yes (Bearer token)
        
        **Features:**
        - Update only the fields you want to change
        - Useful for single field updates
        - Same validation rules as full update
        """,
        request=MerchantSerializer,
        responses={
            200: OpenApiExample(
                'Success Response', 
                summary='Merchant account updated',
                description='Partially updated merchant account',
                value={
                    "id": "merchant-uuid",
                    "business_name": "Updated Business Name",
                    "updated_at": "2025-07-04T10:30:00Z"
                }
            )
        }
    )
)
class MerchantAccountView(RetrieveUpdateAPIView):
    """Get or update merchant account"""
    serializer_class = MerchantSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        try:
            return self.request.user.merchant_account
        except Merchant.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Merchant account not found")
    
    def get(self, request, *args, **kwargs):
        """Get merchant account details"""
        try:
            return super().get(request, *args, **kwargs)
        except Exception:
            return Response({
                'error': 'No merchant account found for this user'
            }, status=status.HTTP_404_NOT_FOUND)


class CreateMerchantAccountView(APIView):
    """Create merchant account for existing user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Check if user already has merchant account
        if hasattr(request.user, 'merchant_account'):
            return Response({
                'error': 'User already has a merchant account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = MerchantSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            merchant = serializer.save()
            
            # Send merchant creation email
            send_merchant_creation_email(request.user, merchant)
            
            return Response({
                'message': 'Merchant account created successfully',
                'merchant': MerchantSerializer(merchant).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MerchantListView(ListAPIView):
    """List all merchants (admin/staff only)"""
    serializer_class = MerchantSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role in ['admin', 'staff']:
            return Merchant.objects.all().select_related('user', 'category')
        return Merchant.objects.none()


class MerchantStatusUpdateView(APIView):
    """Update merchant status (admin/staff only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def patch(self, request, merchant_id):
        if request.user.role not in ['admin', 'staff']:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({
                'error': 'Merchant not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = MerchantStatusUpdateSerializer(
            merchant, 
            data=request.data, 
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            updated_merchant = serializer.save()
            return Response({
                'message': 'Merchant status updated successfully',
                'merchant': MerchantSerializer(updated_merchant).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def merchant_stats(request):
    """Get merchant statistics (admin/staff only)"""
    if request.user.role not in ['admin', 'staff']:
        return Response({
            'error': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    from django.db.models import Count
    
    stats = {
        'total_merchants': Merchant.objects.count(),
        'merchants_by_status': {},
        'verified_merchants': Merchant.objects.filter(is_verified=True).count(),
        'pending_verification': Merchant.objects.filter(status='pending').count(),
    }
    
    # Get merchants by status
    status_stats = Merchant.objects.values('status').annotate(count=Count('id'))
    for stat in status_stats:
        stats['merchants_by_status'][stat['status']] = stat['count']
    
    return Response(stats, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        tags=['App Key Management'],
        summary='List whitelabel partners',
        description='Get a list of all whitelabel partners with pagination and filtering.',
        parameters=[
            OpenApiParameter('is_active', OpenApiTypes.BOOL, description='Filter by active status'),
            OpenApiParameter('is_verified', OpenApiTypes.BOOL, description='Filter by verification status'),
            OpenApiParameter('search', OpenApiTypes.STR, description='Search by name, code, or email'),
        ]
    ),
    post=extend_schema(
        tags=['App Key Management'],
        summary='Create whitelabel partner',
        description='Create a new whitelabel partner account.',
    )
)
class WhitelabelPartnerListCreateView(APIView):
    """List and create whitelabel partners"""
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        """Get list of whitelabel partners"""
        queryset = WhitelabelPartner.objects.all()
        
        # Apply filters
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        is_verified = request.query_params.get('is_verified')
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == 'true')
        
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                name__icontains=search
            ) | queryset.filter(
                code__icontains=search
            ) | queryset.filter(
                contact_email__icontains=search
            )
        
        # Order by creation date
        queryset = queryset.order_by('-created_at')
        
        serializer = WhitelabelPartnerSerializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': queryset.count()
        })

    def post(self, request):
        """Create new whitelabel partner"""
        serializer = WhitelabelPartnerCreateSerializer(data=request.data)
        if serializer.is_valid():
            partner = serializer.save()
            response_serializer = WhitelabelPartnerSerializer(partner)
            return Response({
                'success': True,
                'message': 'Whitelabel partner created successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=extend_schema(
        tags=['App Key Management'],
        summary='Get whitelabel partner details',
        description='Get detailed information about a specific whitelabel partner.',
    ),
    put=extend_schema(
        tags=['App Key Management'],
        summary='Update whitelabel partner',
        description='Update whitelabel partner information.',
    ),
    patch=extend_schema(
        tags=['App Key Management'],
        summary='Partially update whitelabel partner',
        description='Partially update whitelabel partner information.',
    ),
    delete=extend_schema(
        tags=['App Key Management'],
        summary='Delete whitelabel partner',
        description='Delete a whitelabel partner (admin only).',
    )
)
class WhitelabelPartnerDetailView(APIView):
    """Retrieve, update and delete whitelabel partner"""
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_object(self, pk):
        return get_object_or_404(WhitelabelPartner, pk=pk)

    def get(self, request, pk):
        """Get whitelabel partner details"""
        partner = self.get_object(pk)
        serializer = WhitelabelPartnerSerializer(partner)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def put(self, request, pk):
        """Update whitelabel partner"""
        partner = self.get_object(pk)
        serializer = WhitelabelPartnerCreateSerializer(partner, data=request.data)
        if serializer.is_valid():
            partner = serializer.save()
            response_serializer = WhitelabelPartnerSerializer(partner)
            return Response({
                'success': True,
                'message': 'Partner updated successfully',
                'data': response_serializer.data
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """Partially update whitelabel partner"""
        partner = self.get_object(pk)
        serializer = WhitelabelPartnerCreateSerializer(partner, data=request.data, partial=True)
        if serializer.is_valid():
            partner = serializer.save()
            response_serializer = WhitelabelPartnerSerializer(partner)
            return Response({
                'success': True,
                'message': 'Partner updated successfully',
                'data': response_serializer.data
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Delete whitelabel partner"""
        partner = self.get_object(pk)
        partner.delete()
        return Response({
            'success': True,
            'message': 'Partner deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['App Key Management'],
    summary='Generate webhook secret',
    description='Generate a new webhook secret for a whitelabel partner.',
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def generate_webhook_secret(request, partner_pk):
    """Generate new webhook secret for partner"""
    partner = get_object_or_404(WhitelabelPartner, pk=partner_pk)
    
    serializer = WebhookSecretRegenerateSerializer(data=request.data)
    if serializer.is_valid():
        new_secret = partner.generate_webhook_secret()
        return Response({
            'success': True,
            'message': 'Webhook secret regenerated successfully',
            'data': {
                'new_webhook_secret': new_secret,
                'warning': 'This secret will not be shown again. Please store it securely.'
            }
        })
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=extend_schema(
        tags=['App Key Management'],
        summary='List app keys',
        description='Get a list of API keys for a specific partner or all partners.',
        parameters=[
            OpenApiParameter('partner', OpenApiTypes.UUID, description='Filter by partner ID'),
            OpenApiParameter('key_type', OpenApiTypes.STR, description='Filter by key type'),
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status'),
        ]
    ),
    post=extend_schema(
        tags=['App Key Management'],
        summary='Create app key',
        description='Create a new API key for a whitelabel partner.',
    )
)
class AppKeyListCreateView(APIView):
    """List and create app keys"""
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        """Get list of app keys"""
        queryset = AppKey.objects.select_related('partner').all()
        
        # Apply filters
        partner_id = request.query_params.get('partner')
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        
        key_type = request.query_params.get('key_type')
        if key_type:
            queryset = queryset.filter(key_type=key_type)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Order by creation date
        queryset = queryset.order_by('-created_at')
        
        serializer = AppKeySerializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': queryset.count()
        })

    def post(self, request):
        """Create new app key"""
        serializer = AppKeyCreateSerializer(data=request.data)
        if serializer.is_valid():
            app_key = serializer.save()
            return Response({
                'success': True,
                'message': 'API key created successfully',
                'data': serializer.data,
                'warning': 'The secret key will not be shown again. Please store it securely.'
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=extend_schema(
        tags=['App Key Management'],
        summary='Get app key details',
        description='Get detailed information about a specific API key.',
    ),
    put=extend_schema(
        tags=['App Key Management'],
        summary='Update app key',
        description='Update API key configuration.',
    ),
    patch=extend_schema(
        tags=['App Key Management'],
        summary='Partially update app key',
        description='Partially update API key configuration.',
    ),
    delete=extend_schema(
        tags=['App Key Management'],
        summary='Delete app key',
        description='Delete an API key (revokes the key).',
    )
)
class AppKeyDetailView(APIView):
    """Retrieve, update and delete app key"""
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_object(self, pk):
        return get_object_or_404(AppKey.objects.select_related('partner'), pk=pk)

    def get(self, request, pk):
        """Get app key details"""
        app_key = self.get_object(pk)
        serializer = AppKeySerializer(app_key)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def put(self, request, pk):
        """Update app key"""
        app_key = self.get_object(pk)
        serializer = AppKeyUpdateSerializer(app_key, data=request.data)
        if serializer.is_valid():
            app_key = serializer.save()
            response_serializer = AppKeySerializer(app_key)
            return Response({
                'success': True,
                'message': 'API key updated successfully',
                'data': response_serializer.data
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """Partially update app key"""
        app_key = self.get_object(pk)
        serializer = AppKeyUpdateSerializer(app_key, data=request.data, partial=True)
        if serializer.is_valid():
            app_key = serializer.save()
            response_serializer = AppKeySerializer(app_key)
            return Response({
                'success': True,
                'message': 'API key updated successfully',
                'data': response_serializer.data
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Revoke app key"""
        app_key = self.get_object(pk)
        app_key.revoke(revoked_by=request.user)
        return Response({
            'success': True,
            'message': 'API key revoked successfully'
        })


@extend_schema(
    tags=['App Key Management'],
    summary='Regenerate app key secret',
    description='Regenerate the secret portion of an API key.',
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def regenerate_app_key_secret(request, key_pk):
    """Regenerate app key secret"""
    app_key = get_object_or_404(AppKey, pk=key_pk)
    
    serializer = AppKeyRegenerateSerializer(data=request.data)
    if serializer.is_valid():
        # Generate new keys
        app_key._generate_keys()
        app_key.save()
        
        return Response({
            'success': True,
            'message': 'API key secret regenerated successfully',
            'data': {
                'public_key': app_key.public_key,
                'new_secret': getattr(app_key, '_raw_secret', None),
                'warning': 'This secret will not be shown again. Please store it securely.'
            }
        })
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['App Key Management'],
    summary='Get app key usage statistics',
    description='Get usage statistics for an API key within a date range.',
    parameters=[
        OpenApiParameter('start_date', OpenApiTypes.DATE, description='Start date (YYYY-MM-DD)'),
        OpenApiParameter('end_date', OpenApiTypes.DATE, description='End date (YYYY-MM-DD)'),
    ]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def app_key_usage_stats(request, key_pk):
    """Get app key usage statistics"""
    app_key = get_object_or_404(AppKey, pk=key_pk)
    
    from datetime import datetime, timedelta
    from django.utils.dateparse import parse_date
    
    # Parse date parameters
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    
    if start_date_str:
        start_date = parse_date(start_date_str)
    else:
        start_date = (timezone.now() - timedelta(days=30)).date()
    
    if end_date_str:
        end_date = parse_date(end_date_str)
    else:
        end_date = timezone.now().date()
    
    if not start_date or not end_date:
        return Response({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get usage statistics
    stats = AppKeyUsageLog.get_usage_stats(app_key, start_date, end_date)
    stats.update({
        'start_date': start_date,
        'end_date': end_date
    })
    
    serializer = AppKeyStatsSerializer(stats)
    return Response({
        'success': True,
        'data': serializer.data
    })


@extend_schema_view(
    get=extend_schema(
        tags=['App Key Management'],
        summary='List app key usage logs',
        description='Get usage logs for a specific API key.',
        parameters=[
            OpenApiParameter('limit', OpenApiTypes.INT, description='Number of logs to return (default: 100)'),
            OpenApiParameter('offset', OpenApiTypes.INT, description='Number of logs to skip'),
            OpenApiParameter('method', OpenApiTypes.STR, description='Filter by HTTP method'),
            OpenApiParameter('status_code', OpenApiTypes.INT, description='Filter by status code'),
        ]
    )
)
class AppKeyUsageLogListView(APIView):
    """List app key usage logs"""
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request, key_pk):
        """Get app key usage logs"""
        app_key = get_object_or_404(AppKey, pk=key_pk)
        queryset = AppKeyUsageLog.objects.filter(app_key=app_key)
        
        # Apply filters
        method = request.query_params.get('method')
        if method:
            queryset = queryset.filter(method=method.upper())
        
        status_code = request.query_params.get('status_code')
        if status_code:
            try:
                queryset = queryset.filter(status_code=int(status_code))
            except ValueError:
                pass
        
        # Apply pagination
        limit = int(request.query_params.get('limit', 100))
        offset = int(request.query_params.get('offset', 0))
        
        total_count = queryset.count()
        queryset = queryset.order_by('-created_at')[offset:offset + limit]
        
        serializer = AppKeyUsageLogSerializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_next': offset + limit < total_count
            }
        })


@extend_schema(
    tags=['App Key Management'],
    summary='Get partner app keys',
    description='Get all API keys for a specific whitelabel partner.',
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def partner_app_keys(request, partner_pk):
    """Get app keys for a specific partner"""
    partner = get_object_or_404(WhitelabelPartner, pk=partner_pk)
    app_keys = AppKey.objects.filter(partner=partner).order_by('-created_at')
    
    serializer = AppKeySerializer(app_keys, many=True)
    return Response({
        'success': True,
        'data': serializer.data,
        'partner': {
            'id': partner.id,
            'name': partner.name,
            'code': partner.code
        }
    })


@extend_schema(
    tags=['App Key Management'],
    summary='Verify API key',
    description='Verify an API key and return key information (for integration testing).',
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])  # Public endpoint for key verification
def verify_api_key(request):
    """Verify API key (public endpoint for testing)"""
    public_key = request.data.get('public_key')
    secret_key = request.data.get('secret_key')
    
    if not public_key or not secret_key:
        return Response({
            'success': False,
            'error': 'Both public_key and secret_key are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        app_key = AppKey.objects.select_related('partner').get(public_key=public_key)
        
        if not app_key.verify_secret(secret_key):
            return Response({
                'success': False,
                'error': 'Invalid secret key'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not app_key.is_active():
            return Response({
                'success': False,
                'error': 'API key is not active'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response({
            'success': True,
            'message': 'API key is valid',
            'data': {
                'key_id': app_key.id,
                'partner_name': app_key.partner.name,
                'key_type': app_key.key_type,
                'scopes': app_key.get_scopes_list(),
                'expires_at': app_key.expires_at
            }
        })
        
    except AppKey.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid public key'
        }, status=status.HTTP_401_UNAUTHORIZED)


# HTML Form Views (for web interface)
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as django_login
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from django.views.generic import View
from django import forms


class LoginForm(forms.Form):
    """Form for user login"""
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white/50 backdrop-blur-sm',
            'placeholder': 'Enter your email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white/50 backdrop-blur-sm pr-12',
            'placeholder': 'Enter your password'
        })
    )


class RegistrationForm(forms.ModelForm):
    """Form for user registration"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white/50 backdrop-blur-sm pr-12',
            'placeholder': 'Create a strong password'
        })
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white/50 backdrop-blur-sm pr-12',
            'placeholder': 'Confirm your password'
        })
    )
    terms = forms.BooleanField(required=True)
    marketing = forms.BooleanField(required=False)

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white/50 backdrop-blur-sm',
                'placeholder': 'John'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white/50 backdrop-blur-sm',
                'placeholder': 'Doe'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white/50 backdrop-blur-sm',
                'placeholder': 'john@example.com'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white/50 backdrop-blur-sm',
                'placeholder': '+1 (555) 123-4567'
            }),
        }

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")
        return password_confirm

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


@method_decorator([sensitive_post_parameters(), csrf_protect, never_cache], name='dispatch')
class LoginView(View):
    """HTML form-based login view"""
    template_name = 'authentication/login.html'
    form_class = LoginForm

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('auth:dashboard')  # Redirect to dashboard if already logged in
        
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            # Authenticate user
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                if user.is_active:
                    django_login(request, user)
                    
                    # Update last login
                    user.last_login = timezone.now()
                    user.save(update_fields=['last_login'])
                    
                    messages.success(request, f'Welcome back, {user.get_full_name()}!')
                    
                    # Redirect to next URL or dashboard
                    next_url = request.GET.get('next', 'auth:dashboard')
                    return redirect(next_url)
                else:
                    messages.error(request, 'Your account is deactivated. Please contact support.')
            else:
                messages.error(request, 'Invalid email or password.')
        
        return render(request, self.template_name, {'form': form})


@method_decorator([csrf_protect, never_cache], name='dispatch')
class RegisterView(View):
    """HTML form-based registration view"""
    template_name = 'authentication/register.html'
    form_class = RegistrationForm

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('auth:dashboard')  # Redirect to dashboard if already logged in
        
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        
        if form.is_valid():
            try:
                # Get country and currency defaults
                default_country = Country.objects.filter(code='US').first()
                if not default_country:
                    default_country = Country.objects.create(
                        name='United States',
                        code='US',
                        phone_code='+1'
                    )
                
                default_currency = PreferredCurrency.objects.filter(code='USD').first()
                if not default_currency:
                    default_currency = PreferredCurrency.objects.create(
                        name='US Dollar',
                        code='USD',
                        symbol='$',
                        is_active=True
                    )
                
                # Create user
                user = CustomUser.objects.create_user(
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    phone_number=form.cleaned_data.get('phone_number', ''),
                    country=default_country,
                    preferred_currency=default_currency,
                    is_verified=False,  # User will need to verify email
                    marketing_consent=form.cleaned_data.get('marketing', False)
                )
                
                # Generate and send OTP
                try:
                    send_otp_email(user)
                    messages.success(
                        request, 
                        f'Account created successfully! Please check your email ({user.email}) '
                        'for a verification code to activate your account.'
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        'Account created but we had trouble sending the verification email. '
                        'Please contact support if you need help verifying your account.'
                    )
                
                # Redirect to login page with success message
                return redirect('auth:login')
                
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
        
        return render(request, self.template_name, {'form': form})


def dashboard_view(request):
    """Simple dashboard view"""
    if not request.user.is_authenticated:
        return redirect('auth:login')
    
    return render(request, 'authentication/dashboard.html', {
        'user': request.user
    })


# ...existing API code below...
