from rest_framework import generics, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from ..models import (
    Integration,
    BankIntegration,
    IntegrationAPICall,
    IntegrationWebhook
)
from ..serializers import (
    IntegrationListSerializer,
    IntegrationDetailSerializer,
    BankIntegrationSerializer,
    IntegrationAPICallSerializer,
    IntegrationWebhookSerializer
)
from authentication.api_auth import APIKeyOrTokenAuthentication
from .base import APIKeyPermission, StandardResultsSetPagination


class IntegrationListView(generics.ListAPIView):
    """List all available integrations"""
    serializer_class = IntegrationListSerializer
    authentication_classes = [APIKeyOrTokenAuthentication]
    permission_classes = [APIKeyPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['integration_type', 'status', 'is_sandbox', 'is_global']
    search_fields = ['name', 'provider_name', 'code']
    ordering_fields = ['name', 'provider_name', 'created_at']
    ordering = ['provider_name', 'name']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Get integrations available to the user"""
        # For API key users, show all global integrations
        if hasattr(self.request.user, '_api_key'):
            return Integration.objects.filter(is_global=True)
        
        # For regular users, show integrations they have access to
        user = self.request.user
        if hasattr(user, 'merchant_account'):
            queryset = Integration.objects.filter(
                Q(is_global=True) | Q(merchant_configurations__merchant=user.merchant_account)
            ).distinct()
        else:
            queryset = Integration.objects.filter(is_global=True)
        return queryset


class IntegrationDetailView(generics.RetrieveAPIView):
    """Get integration details"""
    serializer_class = IntegrationDetailSerializer
    authentication_classes = [APIKeyOrTokenAuthentication]
    permission_classes = [APIKeyPermission]
    lookup_field = 'id'

    def get_queryset(self):
        """Get integrations available to the user"""
        # For API key users, show all global integrations
        if hasattr(self.request.user, '_api_key'):
            return Integration.objects.filter(is_global=True)
        
        # For regular users, show integrations they have access to
        user = self.request.user
        if hasattr(user, 'merchant_account'):
            return Integration.objects.filter(
                Q(is_global=True) | Q(merchant_configurations__merchant=user.merchant_account)
            ).distinct()
        else:
            return Integration.objects.filter(is_global=True)


class BankIntegrationDetailView(generics.RetrieveAPIView):
    """Get bank integration details"""
    serializer_class = BankIntegrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'integration__id'

    def get_queryset(self):
        """Get bank integrations available to the user"""
        user = self.request.user
        return BankIntegration.objects.filter(
            Q(integration__is_global=True) | 
            Q(integration__merchant_configurations__merchant=user.merchant)
        ).distinct()


class IntegrationAPICallListView(generics.ListAPIView):
    """List integration API calls"""
    serializer_class = IntegrationAPICallSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_successful', 'method', 'operation_type']
    ordering_fields = ['created_at', 'response_time_ms']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Get API calls for merchant's integrations"""
        return IntegrationAPICall.objects.filter(
            merchant_integration__merchant=self.request.user.merchant
        ).select_related('merchant_integration__integration')


class IntegrationWebhookListView(generics.ListAPIView):
    """List integration webhooks"""
    serializer_class = IntegrationWebhookSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_processed', 'is_verified', 'event_type']
    ordering_fields = ['created_at', 'processed_at']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Get webhooks for merchant's integrations"""
        return IntegrationWebhook.objects.filter(
            integration__merchant_configurations__merchant=self.request.user.merchant
        ).select_related('integration')